from unittest import skipUnless

from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.utils import timezone
from face_recognition.app.engine import MODEL_VERSION

from apps.accounts.models import User
from apps.community.models import Event, Publication
from apps.face_search.models import FaceEmbedding, PhotoFaceIndex
from apps.face_search.vectors import exact_scores, replace_embeddings


def axis(n):
    return [float(i == n) for i in range(128)]


class FaceVectorTests(TestCase):
    def setUp(self):
        admin = User.objects.create_superuser("pixel.club@sait.ac.in", "test")
        event = Event.objects.create(
            title="Vector test",
            starts_at=timezone.now(),
            ends_at=timezone.now(),
            published=True,
            drive_folder_id="vector-test",
        )
        self.photo = Publication.objects.create(
            kind="photo",
            author=admin,
            event=event,
            title="Vector photograph",
            published=True,
            drive_file_id="test-image",
        )
        self.index = PhotoFaceIndex.objects.create(
            photo=self.photo,
            source_key="source",
            model_version=MODEL_VERSION,
            faces=[{"vector": axis(0), "box": [1, 2, 80, 80]}],
        )

    def test_typed_vectors_round_trip_and_replace_atomically(self):
        replace_embeddings(self.index, self.index.faces)
        saved = FaceEmbedding.objects.get(index=self.index)
        self.assertEqual(saved.embedding.tolist(), axis(0))
        self.assertEqual(saved.box, [1, 2, 80, 80])
        self.assertTrue(self.index.vectorized)
        self.assertEqual(self.index.face_count, 1)
        with self.assertRaises(ValueError):
            replace_embeddings(self.index, [{"vector": [1.0]}])
        self.assertEqual(FaceEmbedding.objects.get(index=self.index).pk, saved.pk)
        replace_embeddings(self.index, [{"vector": axis(1)}])
        self.assertEqual(FaceEmbedding.objects.get(index=self.index).embedding.tolist(), axis(1))

    def test_source_change_prevents_stale_vector_replacement(self):
        PhotoFaceIndex.objects.filter(pk=self.index.pk).update(source_key="changed")
        self.assertFalse(replace_embeddings(self.index, self.index.faces))
        self.assertFalse(FaceEmbedding.objects.exists())

    def test_backfill_is_idempotent_and_features_cascade_on_delete(self):
        call_command("backfill_face_vectors", verbosity=0)
        call_command("backfill_face_vectors", verbosity=0)
        self.assertEqual(FaceEmbedding.objects.count(), 1)
        self.photo.delete()
        self.assertFalse(FaceEmbedding.objects.exists())

    @skipUnless(connection.vendor == "postgresql", "pgvector operators require PostgreSQL")
    def test_exact_database_search_returns_all_qualifying_photos_and_restricts_scope(self):
        indexes = []
        for n in range(14):
            photo = Publication.objects.create(
                kind="photo",
                author=self.photo.author,
                event=self.photo.event,
                title=f"Matching {n}",
                published=True,
            )
            index = PhotoFaceIndex.objects.create(
                photo=photo,
                source_key="source",
                model_version=MODEL_VERSION,
            )
            replace_embeddings(index, [{"vector": axis(0)}, {"vector": axis(1)}])
            indexes.append(index.pk)
        replace_embeddings(self.index, [{"vector": axis(1)}])
        self.assertEqual(set(exact_scores(axis(0), indexes, 0.5)), set(indexes))
        self.assertEqual(set(exact_scores(axis(0), indexes[:2], 0.5)), set(indexes[:2]))
        self.assertEqual(exact_scores(axis(0), [self.index.pk], 0.5), {})
        self.assertEqual(exact_scores(axis(0), [], 0.5), {})
        self.index.refresh_from_db()
        self.assertEqual(self.index.faces, [])
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT indexdef FROM pg_indexes WHERE indexname='face_embedding_hnsw_ip'"
            )
            self.assertIn("hnsw", cursor.fetchone()[0])
