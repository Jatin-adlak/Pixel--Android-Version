"""Atomic first import into a freshly migrated PostgreSQL database.

COPY preserves IDs and timestamps and avoids thousands of network round trips.
Existing application data always makes this command refuse the import.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

from django.apps import apps
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Import a private Django JSON export into an empty PostgreSQL database atomically."

    def add_arguments(self, parser):
        parser.add_argument("fixture")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("Initial import requires PostgreSQL.")
        path = Path(options["fixture"]).resolve()
        raw = path.read_text(encoding="utf-8")
        objects = list(serializers.deserialize("json", raw))
        if not objects or not any(
            row.object._meta.label_lower == "accounts.user" for row in objects
        ):
            raise CommandError("The export must contain the existing PIXEL users.")
        models = list(apps.get_models(include_auto_created=True))
        # Only Django defaults and the known Drive-folder data migration may exist.
        seeded = {"contenttypes.contenttype", "auth.permission", "community.drivefolder"}
        for model in models:
            if model._meta.label_lower not in seeded and model._base_manager.exists():
                raise CommandError("Target already contains application data; import refused.")
        grouped, m2m = defaultdict(list), defaultdict(list)
        for row in objects:
            model = type(row.object)
            if model._meta.label_lower == "face_search.faceworkerstate":
                raise CommandError("Do not import running worker leases.")
            grouped[model].append(row.object)
            for name, values in (row.m2m_data or {}).items():
                field = model._meta.get_field(name)
                through = field.remote_field.through
                columns = (
                    through._meta.get_field(field.m2m_field_name()).column,
                    through._meta.get_field(field.m2m_reverse_field_name()).column,
                )
                for value in values:
                    m2m[(through, columns)].append((row.object.pk, value))
        quote = connection.ops.quote_name
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET CONSTRAINTS ALL DEFERRED")
                cursor.execute(
                    "TRUNCATE " + ", ".join(quote(model._meta.db_table) for model in models)
                )
                for model, records in grouped.items():
                    fields = list(model._meta.concrete_fields)
                    sql = "COPY {} ({}) FROM STDIN".format(
                        quote(model._meta.db_table),
                        ", ".join(quote(field.column) for field in fields),
                    )
                    with cursor.cursor.copy(sql) as copy:
                        for record in records:
                            copy.write_row(
                                [
                                    field.get_db_prep_save(
                                        field.value_from_object(record), connection
                                    )
                                    for field in fields
                                ]
                            )
                for (through, columns), records in m2m.items():
                    sql = "COPY {} ({}) FROM STDIN".format(
                        quote(through._meta.db_table), ", ".join(map(quote, columns))
                    )
                    with cursor.cursor.copy(sql) as copy:
                        for record in records:
                            copy.write_row(record)
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
                for sql in connection.ops.sequence_reset_sql(no_style(), models):
                    cursor.execute(sql)
            for model, records in grouped.items():
                if model._base_manager.count() != len(records):
                    raise CommandError(
                        "Imported row counts did not match; transaction rolled back."
                    )
            if options["dry_run"]:
                transaction.set_rollback(True)
        self.stdout.write(
            json.dumps(
                {
                    "imported": len(objects),
                    "dry_run": options["dry_run"],
                    "models": dict(Counter(row.object._meta.label_lower for row in objects)),
                }
            )
        )
