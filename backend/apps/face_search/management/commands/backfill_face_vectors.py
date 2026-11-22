from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Count, F, Sum

from apps.face_search.models import PhotoFaceIndex
from apps.face_search.vectors import replace_embeddings


class Command(BaseCommand):
    help = "Move cached gallery features into vector rows without downloading originals again."

    def add_arguments(self, parser):
        parser.add_argument("--clear-legacy", action="store_true")
        parser.add_argument("--rebuild-local", action="store_true")

    def handle(self, *args, **options):
        if options["clear_legacy"] and connection.vendor != "postgresql":
            raise CommandError("Legacy cache removal is only supported on PostgreSQL.")
        if options["rebuild_local"] and connection.vendor != "sqlite":
            raise CommandError("Local rebuilding requires the SQLite legacy feature cache.")
        pending = PhotoFaceIndex.objects.all()
        if not options["rebuild_local"]:
            pending = pending.filter(vectorized=False)
        for pk in list(pending.values_list("pk", flat=True)):
            with transaction.atomic():
                index = PhotoFaceIndex.objects.select_for_update().get(pk=pk)
                if not index.vectorized or options["rebuild_local"]:
                    if not replace_embeddings(index, index.faces):
                        raise CommandError("A photograph changed while being converted; retry.")
        if (
            PhotoFaceIndex.objects.annotate(actual=Count("embeddings"))
            .exclude(actual=F("face_count"))
            .exists()
        ):
            raise CommandError("Vector count mismatch; conversion stopped.")
        if options["clear_legacy"]:
            PhotoFaceIndex.objects.filter(vectorized=True).exclude(faces=[]).update(faces=[])
        processed = PhotoFaceIndex.objects.count()
        faces = PhotoFaceIndex.objects.aggregate(total=Sum("face_count"))["total"] or 0
        self.stdout.write(f"Verified {faces} vector rows across {processed} photograph indexes.")
