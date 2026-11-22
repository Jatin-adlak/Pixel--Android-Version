import json
from collections import defaultdict
from pathlib import Path

from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection


class Command(BaseCommand):
    help = "Compare imported IDs, fields and relationships against the private SQLite export."

    def add_arguments(self, parser):
        parser.add_argument("fixture")

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("Import verification requires PostgreSQL.")
        objects = list(
            serializers.deserialize("json", Path(options["fixture"]).read_text(encoding="utf-8"))
        )
        grouped = defaultdict(list)
        for item in objects:
            grouped[type(item.object)].append(item)
        for model, records in grouped.items():
            existing = model._base_manager.in_bulk()
            if len(existing) != len(records):
                raise CommandError(f"Row count mismatch in {model._meta.label_lower}.")
            for record in records:
                current = existing.get(record.object.pk)
                if current is None:
                    raise CommandError(f"An original ID is missing in {model._meta.label_lower}.")
                expected = serializers.serialize("python", [record.object])[0]
                actual = serializers.serialize("python", [current])[0]
                # The live database stores these features only in the vector table.
                if model._meta.label_lower == "face_search.photofaceindex":
                    expected["fields"].pop("faces", None)
                    actual["fields"].pop("faces", None)
                for name, values in (record.m2m_data or {}).items():
                    expected["fields"][name] = sorted(map(str, values))
                    actual["fields"][name] = sorted(
                        map(str, getattr(current, name).values_list("pk", flat=True))
                    )
                if json.dumps(expected, cls=DjangoJSONEncoder, sort_keys=True) != json.dumps(
                    actual, cls=DjangoJSONEncoder, sort_keys=True
                ):
                    raise CommandError(
                        f"Field comparison failed in {model._meta.label_lower}; no private values displayed."
                    )
        self.stdout.write(
            f"Verified all fields, IDs and relationships in {len(objects)} imported records."
        )
