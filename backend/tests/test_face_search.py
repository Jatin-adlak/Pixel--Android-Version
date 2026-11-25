import io
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.core.cache.backends.locmem import LocMemCache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from face_recognition.app.engine import (
    DIMENSIONS,
    MODEL_VERSION,
    FaceInputError,
    batch_similarities,
    best_similarity,
    decode_image,
    get_engine,
)
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.community.models import Event, Publication
from apps.face_search.models import FaceSearchJob, FaceWorkerState, PhotoFaceIndex
from apps.face_search.storage import CONSENT_VERSION, query_path, source_key
from apps.face_search.vectors import replace_embeddings
from apps.face_search.worker import cleanup, process_job


def vector(axis=0):
    return [1.0 if i == axis else 0.0 for i in range(DIMENSIONS)]


class TestEngine:
    def extract(self, data, *, query=False):
        if data == b"unclear":
            raise FaceInputError("Choose a clearer photo.")
        return [{"vector": vector(1 if data == b"different" else 0), "box": [0, 0, 100, 100]}]


class FaceSearchTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings_override = override_settings(BASE_DIR=Path(self.directory.name))
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.admin = User.objects.create_superuser(
            "pixel.club@sait.ac.in", "test", username="pixel", profile_completed=True
        )
        self.user = User.objects.create_user(
            "alice@sait.ac.in",
            "test",
            username="alice",
            profile_completed=True,
            email_verified=True,
        )
        self.other = User.objects.create_user(
            "bob@sait.ac.in", "test", username="bob", profile_completed=True, email_verified=True
        )
        self.event = Event.objects.create(
            title="Completed event",
            starts_at=timezone.now() - timedelta(days=1),
            ends_at=timezone.now(),
            published=True,
            drive_folder_id="folder-id",
        )
        self.photo = Publication.objects.create(
            author=self.admin,
            event=self.event,
            kind="photo",
            title="Match",
            drive_file_id="matching",
            published=True,
            source_revision="1",
        )
        self.different = Publication.objects.create(
            author=self.admin,
            event=self.event,
            kind="photo",
            title="Other",
            drive_file_id="different",
            published=True,
            source_revision="1",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def job(self, data=b"query"):
        job = FaceSearchJob.objects.create(
            user=self.user,
            event=self.event,
            consent_version=CONSENT_VERSION,
            model_version=MODEL_VERSION,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        path = query_path(job.pk)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return job

    @override_settings(FACE_WORKER_NODE_ID="friend-pc")
    @patch("apps.face_search.worker.get_engine")
    def test_other_computer_cannot_claim_cancel_or_expire_local_job(self, engine):
        job = self.job()
        process_job(job.pk)
        engine.assert_not_called()
        job.refresh_from_db()
        self.assertEqual(job.status, "queued")
        self.assertTrue(query_path(job.pk).exists())
        self.assertEqual(self.client.get(f"/api/v1/face-search/{job.pk}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/v1/face-search/{job.pk}/").status_code, 404)
        job.expires_at = timezone.now() - timedelta(seconds=1)
        job.save(update_fields=["expires_at"])
        cleanup()
        job.refresh_from_db()
        self.assertEqual(job.status, "queued")
        self.assertTrue(query_path(job.pk).exists())

    @override_settings(FACE_WORKER_NODE_ID="friend-pc")
    def test_worker_readiness_is_specific_to_the_current_computer(self):
        from apps.face_search.views import worker_ready

        FaceWorkerState.objects.create(node_id="legacy", last_seen_at=timezone.now())
        self.assertFalse(worker_ready())
        FaceWorkerState.objects.create(node_id="friend-pc", last_seen_at=timezone.now())
        self.assertTrue(worker_ready())

    @override_settings(FACE_WORKER_NODE_ID="friend-pc")
    @patch("apps.face_search.management.commands.run_face_worker.get_engine")
    @patch("apps.face_search.management.commands.run_face_worker.cleanup")
    @patch("apps.face_search.management.commands.run_face_worker.index_next", return_value=False)
    def test_friend_worker_does_not_take_or_reset_the_owners_lease(self, index, clean, engine):
        from django.core.management import call_command

        original = FaceWorkerState.objects.create(
            node_id="legacy",
            lease_until=timezone.now() + timedelta(minutes=2),
            last_seen_at=timezone.now(),
        )
        lease = original.lease_until
        call_command("run_face_worker", once=True, stdout=io.StringIO())
        original.refresh_from_db()
        self.assertEqual(original.lease_until, lease)
        self.assertTrue(FaceWorkerState.objects.filter(node_id="friend-pc").exists())

    @override_settings(FACE_WORKER_NODE_ID="friend-pc")
    @patch("apps.face_search.views.worker_ready", return_value=True)
    def test_uploaded_job_is_assigned_to_this_computer(self, ready):
        buffer = io.BytesIO()
        Image.new("RGB", (320, 320)).save(buffer, "JPEG")
        response = self.client.post(
            f"/api/v1/events/{self.event.pk}/face-search/",
            {
                "photo": SimpleUploadedFile("selfie.jpg", buffer.getvalue(), "image/jpeg"),
                "consent": CONSENT_VERSION,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(FaceSearchJob.objects.get(pk=response.data["id"]).worker_node, "friend-pc")

    @patch("apps.face_search.views.worker_ready", return_value=True)
    def test_preflight_resumes_only_the_owners_active_search(self, ready):
        job = self.job()
        path = f"/api/v1/events/{self.event.pk}/face-search/"
        self.assertEqual(self.client.get(path).data["active_job"]["id"], str(job.pk))
        self.client.force_authenticate(self.other)
        self.assertIsNone(self.client.get(path).data["active_job"])
        self.client.force_authenticate(self.user)
        self.client.delete(f"/api/v1/face-search/{job.pk}/")
        self.assertIsNone(self.client.get(path).data["active_job"])

    @patch("apps.face_search.views.worker_ready", return_value=False)
    def test_reopening_event_recovers_completed_search_without_worker(self, ready):
        job = self.job()
        job.status = "complete"
        job.save(update_fields=["status"])
        path = f"/api/v1/events/{self.event.pk}/face-search/"
        state = self.client.get(path).data
        self.assertFalse(state["available"])
        self.assertIsNone(state["active_job"])
        self.assertEqual(state["recent_job"]["id"], str(job.pk))

        self.client.force_authenticate(self.other)
        self.assertIsNone(self.client.get(path).data["recent_job"])
        self.client.force_authenticate(self.user)
        with override_settings(FACE_WORKER_NODE_ID="friend-pc"):
            self.assertIsNone(self.client.get(path).data["recent_job"])

        job.expires_at = timezone.now() - timedelta(seconds=1)
        job.save(update_fields=["expires_at"])
        self.assertIsNone(self.client.get(path).data["recent_job"])

    @patch("apps.face_search.views.worker_ready", return_value=True)
    def test_reading_event_search_state_does_not_consume_submission_limit(self, ready):
        from rest_framework.throttling import ScopedRateThrottle

        path = f"/api/v1/events/{self.event.pk}/face-search/"
        cache = LocMemCache("face-search-test-limit", {})
        with (
            patch.object(ScopedRateThrottle, "cache", cache),
            patch.object(ScopedRateThrottle, "get_rate", return_value="1/hour"),
        ):
            self.assertEqual(self.client.get(path).status_code, 200)
            self.assertEqual(self.client.get(path).status_code, 200)
            self.assertEqual(self.client.post(path, {}, format="json").status_code, 400)
            blocked = self.client.post(path, {}, format="json")
            self.assertEqual(blocked.status_code, 429)
            self.assertIn("Try again in 60 minutes", blocked.data["detail"])
            self.assertTrue(blocked.has_header("Retry-After"))
            self.assertEqual(self.client.get(path).status_code, 200)

    @patch(
        "apps.face_search.worker.download_original", side_effect=lambda p: p.drive_file_id.encode()
    )
    @patch("apps.face_search.worker.get_engine", return_value=TestEngine())
    def test_job_filters_matches_persists_progress_and_reuses_index(self, engine, download):
        job = self.job()
        process_job(job.pk)
        job.refresh_from_db()
        self.assertEqual(job.status, "complete")
        self.assertEqual(job.processed, 2)
        self.assertEqual(job.total, 2)
        self.assertFalse(query_path(job.pk).exists())
        self.assertEqual([row["id"] for row in job.results], [str(self.photo.pk)])
        results = self.client.get(f"/api/v1/face-search/{job.pk}/results/")
        self.assertEqual(results.data["count"], 1)
        self.assertEqual(results.data["results"][0]["id"], str(self.photo.pk))
        process_job(self.job().pk)
        self.assertEqual(download.call_count, 2)

    @patch(
        "apps.face_search.worker.download_original", side_effect=lambda p: p.drive_file_id.encode()
    )
    @patch("apps.face_search.worker.get_engine", return_value=TestEngine())
    def test_results_are_private_event_scoped_and_rechecked_after_source_change(
        self, engine, download
    ):
        unrelated = Event.objects.create(
            title="Other event",
            starts_at=timezone.now(),
            ends_at=timezone.now(),
            published=True,
            drive_folder_id="other-folder",
        )
        Publication.objects.create(
            author=self.admin,
            event=unrelated,
            kind="photo",
            title="Also matching",
            drive_file_id="matching",
            published=True,
        )
        job = self.job()
        process_job(job.pk)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/v1/face-search/{job.pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/face-search/{job.pk}/results/").status_code, 404)
        self.client.force_authenticate(self.user)
        self.photo.source_revision = "2"
        self.photo.save(update_fields=["source_revision"])
        self.assertEqual(self.client.get(f"/api/v1/face-search/{job.pk}/results/").data["count"], 0)
        self.event.published = False
        self.event.save(update_fields=["published"])
        self.assertEqual(self.client.get(f"/api/v1/face-search/{job.pk}/results/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/v1/face-search/{job.pk}/").status_code, 204)

    @patch("apps.face_search.worker.get_engine", return_value=TestEngine())
    def test_quality_failure_and_cancellation_remove_uploaded_queries(self, engine):
        job = self.job(b"unclear")
        process_job(job.pk)
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertFalse(query_path(job.pk).exists())
        job = self.job()
        self.client.delete(f"/api/v1/face-search/{job.pk}/")
        process_job(job.pk)
        job.refresh_from_db()
        self.assertEqual(job.status, "cancelled")
        self.assertFalse(query_path(job.pk).exists())

    @patch("apps.face_search.views.worker_ready", return_value=True)
    def test_upload_requires_consent_and_rejects_duplicates(self, ready):
        buffer = io.BytesIO()
        Image.new("RGB", (128, 128)).save(buffer, "JPEG")

        def photo():
            return SimpleUploadedFile("selfie.jpg", buffer.getvalue(), content_type="image/jpeg")

        url = f"/api/v1/events/{self.event.pk}/face-search/"
        self.assertEqual(
            self.client.post(url, {"photo": photo()}, format="multipart").status_code, 400
        )
        first = self.client.post(
            url, {"photo": photo(), "consent": CONSENT_VERSION}, format="multipart"
        )
        self.assertEqual(first.status_code, 202, first.data)
        self.assertTrue(query_path(first.data["id"]).exists())
        self.assertEqual(
            self.client.post(
                url, {"photo": photo(), "consent": CONSENT_VERSION}, format="multipart"
            ).status_code,
            400,
        )
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(url).status_code, [401, 403])

    def test_expiry_and_unpublished_photos_remove_retained_data(self):
        job = self.job()
        job.expires_at = timezone.now() - timedelta(seconds=1)
        job.save(update_fields=["expires_at"])
        PhotoFaceIndex.objects.create(
            photo=self.photo,
            source_key=source_key(self.photo),
            model_version=MODEL_VERSION,
            faces=[{"vector": vector()}],
        )
        self.photo.available = False
        self.photo.save(update_fields=["available"])
        cleanup()
        self.assertFalse(query_path(job.pk).exists())
        self.assertFalse(PhotoFaceIndex.objects.exists())
        job.refresh_from_db()
        self.assertEqual(job.status, "expired")

    def test_matching_math_and_real_detector_reject_no_face(self):
        self.assertAlmostEqual(best_similarity(vector(), [{"vector": vector()}]), 1)
        self.assertAlmostEqual(best_similarity(vector(), [{"vector": vector(1)}]), 0)
        with self.assertRaises(FaceInputError):
            decode_image(b"not an image")
        buffer = io.BytesIO()
        Image.new("RGB", (320, 320)).save(buffer, "JPEG")
        # Actual pinned detector, not fabricated recognition results.
        with self.assertRaises(FaceInputError):
            get_engine().extract(buffer.getvalue(), query=True)
        # Event camera JPGs can be MPO containers: index their primary JPEG frame.
        mpo = io.BytesIO()
        Image.new("RGB", (320, 320)).save(
            mpo, format="MPO", save_all=True, append_images=[Image.new("RGB", (320, 320), "white")]
        )
        self.assertEqual(decode_image(mpo.getvalue()).shape[:2], (320, 320))

    @patch("apps.face_search.worker.download_original")
    @patch("apps.face_search.worker.get_engine", return_value=TestEngine())
    def test_warm_gallery_uses_bulk_reads_and_no_original_downloads(self, engine, download):
        Publication.objects.bulk_create(
            [
                Publication(
                    author=self.admin,
                    event=self.event,
                    kind="photo",
                    title=f"Photo {i}",
                    drive_file_id=f"cached-{i}",
                    published=True,
                )
                for i in range(178)
            ]
        )
        PhotoFaceIndex.objects.bulk_create(
            [
                PhotoFaceIndex(
                    photo=photo,
                    source_key=source_key(photo),
                    model_version=MODEL_VERSION,
                    faces=[{"vector": vector()}],
                )
                for photo in Publication.objects.filter(event=self.event)
            ]
        )
        job = self.job()
        if connection.vendor == "postgresql":
            for cached in PhotoFaceIndex.objects.all():
                replace_embeddings(cached, cached.faces)
        with CaptureQueriesContext(connection) as queries:
            process_job(job.pk)
        job.refresh_from_db()
        self.assertEqual(job.status, "complete")
        self.assertEqual(job.processed, 180)
        self.assertEqual(len(job.results), 180)
        download.assert_not_called()
        self.assertLess(
            len(queries), 35, "Warm matching must not issue database queries per photo."
        )

    def test_batched_scores_preserve_group_photo_maximum_and_threshold_decisions(self):
        import numpy as np

        random = np.random.default_rng(42)
        query = random.normal(size=DIMENSIONS).astype(np.float32)
        query /= np.linalg.norm(query)
        groups = [[], [{"vector": query.tolist()}]]
        for count in (1, 3, 12, 40):
            rows = random.normal(size=(count, DIMENSIONS)).astype(np.float32)
            rows /= np.linalg.norm(rows, axis=1, keepdims=True)
            groups.append([{"vector": row.tolist()} for row in rows])
        groups.append([{"vector": vector()}, {"vector": query.tolist()}])
        baseline = [best_similarity(query, faces) for faces in groups]
        batch = batch_similarities(query, groups)
        np.testing.assert_allclose(batch, baseline, atol=1e-6)
        self.assertEqual([s >= 0.5 for s in baseline], [s >= 0.5 for s in batch])
        boundary = best_similarity(query, groups[2])
        compatible = batch_similarities(query, groups, threshold=boundary)
        self.assertEqual(compatible[2], boundary)

    @patch("apps.face_search.worker.get_engine", return_value=TestEngine())
    def test_cancellation_during_matching_does_not_restore_results(self, engine):
        job = self.job()

        def cancel():
            FaceSearchJob.objects.filter(pk=job.pk).update(status="cancelled", results=[])

        process_job(job.pk, cancel)
        job.refresh_from_db()
        self.assertEqual(job.status, "cancelled")
        self.assertEqual(job.results, [])
        self.assertFalse(query_path(job.pk).exists())
