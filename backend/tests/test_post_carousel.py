import io
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlsplit

from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from PIL import Image
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.community.models import DriveFolder, Event, Publication, Reaction


class PostCarouselTests(TestCase):
    @patch("apps.community.management.commands.backfill_post_dimensions.drive_read_session")
    def test_older_posts_get_dimensions_without_changing_originals_or_saves(self, session):
        post = Publication.objects.create(
            author=self.admin,
            event=self.event,
            kind="post",
            title="Existing",
            drive_file_id="old",
            post_media=["old"],
            published=True,
        )
        Reaction.objects.create(user=self.viewer, publication=post, action="save")
        response = session.return_value.__enter__.return_value.get.return_value
        response.json.return_value = {
            "imageMediaMetadata": {"width": 120, "height": 80, "rotation": 1}
        }
        call_command("backfill_post_dimensions", stdout=io.StringIO())
        post.refresh_from_db()
        self.assertEqual(post.image_dimensions["old"], {"width": 80, "height": 120})
        self.assertEqual(post.post_media, ["old"])
        self.assertEqual(post.reactions.count(), 1)

    def test_image_dimensions_honor_orientation_without_modifying_original(self):
        from apps.community.image_dimensions import image_dimensions

        buffer = io.BytesIO()
        exif = Image.Exif()
        exif[274] = 6
        Image.new("RGB", (120, 80)).save(buffer, format="JPEG", exif=exif)
        data = buffer.getvalue()
        upload = SimpleUploadedFile("portrait.jpg", data, "image/jpeg")
        upload.seek(5)
        self.assertEqual(image_dimensions(upload), {"width": 80, "height": 120})
        self.assertEqual(upload.tell(), 5)
        upload.seek(0)
        self.assertEqual(upload.read(), data)

    @patch("apps.community.management_api.check_publication_media")
    @patch("apps.community.management_api.upload", return_value="portrait")
    def test_dimensions_are_published_with_carousel_metadata(self, upload, check):
        buffer = io.BytesIO()
        Image.new("RGB", (80, 120)).save(buffer, format="JPEG")
        form = self.form(1)
        form["original_uploads"] = [
            SimpleUploadedFile("portrait.jpg", buffer.getvalue(), "image/jpeg")
        ]
        response = self.client.post(self.path, form, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        self.client.force_authenticate(self.viewer)
        image = self.client.get("/api/v1/feed/?kind=post").data["results"][0]["images"][0]
        self.assertEqual((image["width"], image["height"]), (80, 120))

    def setUp(self):
        self.admin = User.objects.create_superuser(
            "pixel.club@sait.ac.in", "test", username="pixel", profile_completed=True
        )
        self.viewer = User.objects.create_user(
            "viewer@sait.ac.in",
            "test",
            username="viewer",
            email_verified=True,
            profile_completed=True,
        )
        self.event = Event.objects.create(
            title="Gallery",
            tag="Cultural",
            starts_at=timezone.now() - timedelta(days=1),
            ends_at=timezone.now(),
            published=True,
            drive_folder_id="event-folder",
        )
        DriveFolder.objects.update_or_create(kind="post", defaults={"folder_id": "post-folder"})
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.path = "/api/v1/management/publications/"

    def form(self, count=10, **extra):
        return {
            "kind": "post",
            "event": str(self.event.pk),
            "title": "Ten frames",
            "tag": "Cultural",
            "published": "true",
            "original_uploads": [
                SimpleUploadedFile(f"{i}.jpg", b"image", "image/jpeg") for i in range(count)
            ],
            **extra,
        }

    @patch("apps.community.management_api.check_publication_media")
    @patch("apps.community.management_api.upload", side_effect=[f"drive-{i}" for i in range(10)])
    def test_ten_images_are_ordered_in_feed_and_share_one_reaction(self, upload, check):
        response = self.client.post(self.path, self.form(), format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        post = Publication.objects.get(pk=response.data["id"])
        self.assertEqual(post.post_media, [f"drive-{i}" for i in range(10)])
        self.assertEqual(check.call_count, 10)
        self.client.force_authenticate(self.viewer)
        feed = self.client.get("/api/v1/feed/?kind=post").data["results"][0]
        self.assertEqual([image["id"] for image in feed["images"]], [str(i) for i in range(10)])
        self.assertNotIn("drive-9", str(feed))
        self.client.put(f"/api/v1/publications/{post.pk}/save/")
        self.assertEqual(post.reactions.count(), 1)
        self.assertEqual(
            self.client.get("/api/v1/members/viewer/saved/?kind=post").data["count"], 1
        )
        url = self.client.get(f"/api/v1/publications/{post.pk}/download/?image=9").data["url"]
        token = urlsplit(url).path.rstrip("/").split("/")[-1]
        payload = signing.loads(token, salt="pixel-media", max_age=600)
        self.assertEqual(payload["media_index"], 9)
        post.published = False
        post.save()
        self.assertEqual(self.client.get(urlsplit(url).path).status_code, 404)

    @patch("apps.community.management_api.upload")
    def test_rejects_empty_over_limit_and_moment_albums_before_upload(self, upload):
        for form in [self.form(0), self.form(11), self.form(2, kind="moment")]:
            self.assertEqual(self.client.post(self.path, form, format="multipart").status_code, 400)
        upload.assert_not_called()

    @patch("apps.community.management_api.check_publication_media")
    @patch(
        "apps.community.management_api.upload",
        side_effect=[*[f"drive-{i}" for i in range(10)], "custom-cover"],
    )
    def test_cover_is_separate_from_the_ten_post_images(self, upload, check):
        form = self.form(10)
        form["cover_upload"] = SimpleUploadedFile("cover.jpg", b"cover", "image/jpeg")
        response = self.client.post(self.path, form, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        post = Publication.objects.get(pk=response.data["id"])
        self.assertEqual(len(post.post_media), 10)
        self.assertEqual(post.cover_drive_file_id, "custom-cover")
        self.assertNotIn("custom-cover", post.post_media)

    @patch("apps.community.management_api.change_drive_file")
    @patch(
        "apps.community.management_api.upload",
        side_effect=["first-file", ValueError("Drive unavailable")],
    )
    def test_failed_batch_never_publishes_a_partial_post(self, upload, trash):
        # The upload adapter normally wraps ValueError into a validation response.
        from apps.community.management_api import PublicationSerializer

        serializer = PublicationSerializer(
            data=self.form(2), context={"request": type("Request", (), {"user": self.admin})()}
        )
        serializer.is_valid(raise_exception=True)
        with self.assertRaises(ValueError):
            serializer.save()
        self.assertEqual(Publication.objects.count(), 0)
        trash.assert_called_with("first-file", trashed=True)

    def test_non_admin_cannot_publish_and_download_index_is_bounded(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(
            self.client.post(self.path, self.form(1), format="multipart").status_code, 403
        )
        post = Publication.objects.create(
            author=self.admin,
            event=self.event,
            kind="post",
            title="Post",
            published=True,
            post_media=["one"],
        )
        for index in ["-1", "1", "bad"]:
            self.assertEqual(
                self.client.get(
                    f"/api/v1/publications/{post.pk}/download/?image={index}"
                ).status_code,
                400,
            )

    @patch("apps.community.management_api.check_publication_media")
    def test_caption_edit_preserves_existing_media_and_rejects_injected_ids(self, check):
        post = Publication.objects.create(
            author=self.admin,
            event=self.event,
            kind="post",
            title="Post",
            published=True,
            drive_file_id="one",
            post_media=["one", "two"],
        )
        response = self.client.patch(
            f"{self.path}{post.pk}/", {"caption": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        post.refresh_from_db()
        self.assertEqual(post.post_media, ["one", "two"])
        self.assertEqual(
            self.client.patch(
                f"{self.path}{post.pk}/", {"post_media": ["other-users-file"]}, format="json"
            ).status_code,
            400,
        )

    @patch("apps.community.management_api.check_publication_media")
    @patch("apps.community.management_api.upload", side_effect=["new-one", "new-two"])
    def test_replacing_album_preserves_identity_and_saves(self, upload, check):
        post = Publication.objects.create(
            author=self.admin,
            event=self.event,
            kind="post",
            title="Original",
            published=True,
            drive_file_id="old",
            post_media=["old"],
        )
        Reaction.objects.create(user=self.viewer, publication=post, action="save")
        response = self.client.patch(f"{self.path}{post.pk}/", self.form(2), format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        post.refresh_from_db()
        self.assertEqual(post.post_media, ["new-one", "new-two"])
        self.assertEqual(post.reactions.count(), 1)

    @patch("apps.community.management_api.change_drive_file")
    @patch(
        "apps.community.management_api.check_publication_media",
        side_effect=ValidationError("Unavailable"),
    )
    @patch("apps.community.management_api.upload", side_effect=["new-one", "new-two"])
    def test_failed_replacement_retains_original_post(self, upload, check, trash):
        post = Publication.objects.create(
            author=self.admin,
            event=self.event,
            kind="post",
            title="Original",
            published=True,
            drive_file_id="old",
            post_media=["old"],
        )
        response = self.client.patch(f"{self.path}{post.pk}/", self.form(2), format="multipart")
        self.assertEqual(response.status_code, 400)
        post.refresh_from_db()
        self.assertEqual(post.post_media, ["old"])
        self.assertEqual(post.title, "Original")
        self.assertEqual(trash.call_count, 2)
