import json

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from face_recognition.app.engine import MODEL_VERSION

from apps.accounts.models import User
from apps.community.models import Event, Publication
from apps.face_search.models import FaceEmbedding, PhotoFaceIndex


class Command(BaseCommand):
    help = (
        "Verify the live PostgreSQL vector schema without exposing credentials or biometric values."
    )

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("This check requires PostgreSQL; SQLite cannot verify pgvector.")
        if MigrationExecutor(connection).migration_plan(
            MigrationExecutor(connection).loader.graph.leaf_nodes()
        ):
            raise CommandError("Apply pending migrations before checking the live schema.")
        with connection.cursor() as cursor:
            cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            version = cursor.fetchone()
            # Neon terminates client TLS at its proxy/pooler. pg_stat_ssl describes
            # the internal proxy-to-compute leg, not our encrypted client socket.
            tls = connection.connection.pgconn.ssl_in_use
            cursor.execute(
                "SELECT indexdef FROM pg_indexes WHERE indexname = 'face_embedding_hnsw_ip'"
            )
            index = cursor.fetchone()
            cursor.execute(
                "SELECT format_type(atttypid, atttypmod) FROM pg_attribute WHERE attrelid = 'face_search_faceembedding'::regclass AND attname = 'embedding'"
            )
            dimensions = cursor.fetchone()
        if (
            not version
            or not tls
            or not index
            or "hnsw" not in index[0]
            or dimensions != ("vector(128)",)
        ):
            raise CommandError(
                "The vector extension, TLS connection, dimensions, or HNSW index is missing."
            )
        if PhotoFaceIndex.objects.filter(vectorized=False).exists():
            raise CommandError("Legacy indexes remain; run backfill_face_vectors --clear-legacy.")
        if PhotoFaceIndex.objects.exclude(faces=[]).exists():
            raise CommandError("Duplicate legacy JSON features remain in PostgreSQL.")
        self.stdout.write(
            json.dumps(
                {
                    "database": "PostgreSQL",
                    "tls": True,
                    "pgvector": version[0],
                    "embedding_dimensions": 128,
                    "hnsw_index": True,
                    "model_version": MODEL_VERSION,
                    "users": User.objects.count(),
                    "event_folders": Event.objects.count(),
                    "publications": Publication.objects.count(),
                    "photo_indexes": PhotoFaceIndex.objects.count(),
                    "face_embeddings": FaceEmbedding.objects.count(),
                }
            )
        )
