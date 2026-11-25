from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from google.auth.exceptions import RefreshError
from requests.exceptions import Timeout
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.community.models import Comment, Event, Follow, Publication, Reaction


class CommunityTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            "pixel.club@sait.ac.in", "test", username="pixel", profile_completed=True
        )
        self.alice = User.objects.create_user(
            "alice@sait.ac.in",
            "test",
            username="alice",
            email_verified=True,
            profile_completed=True,
        )
        self.bob = User.objects.create_user(
            "bob@sait.ac.in", "test", username="bob", email_verified=True, profile_completed=True
        )
        self.event = Event.objects.create(
            title="Campus sports",
            tag="Sports",
            description="Finals",
            venue="Court",
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(hours=2),
            cover_url="https://example.org/cover.jpg",
            published=True,
        )
        self.post = Publication.objects.create(
            kind="post",
            author=self.admin,
            event=self.event,
            title="Final",
            tag="Sports",
            cover_url="https://example.org/c.jpg",
            preview_url="https://example.org/p.jpg",
            original_url="https://example.org/o.jpg",
            published=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.alice)

    def test_follow_request_stays_in_recipient_inbox_until_accepted_or_declined(self):
        self.client.put("/api/v1/members/bob/follow/")
        self.client.put("/api/v1/members/bob/follow/")
        relation = Follow.objects.get(follower=self.alice, target=self.bob)
        self.assertFalse(relation.accepted)
        self.assertEqual(self.client.get("/api/v1/connections/?kind=requests").data["count"], 0)
        recipient = APIClient()
        recipient.force_authenticate(self.bob)
        for _ in range(2):
            inbox = recipient.get("/api/v1/connections/?kind=requests")
            self.assertEqual(inbox.data["count"], 1)
            self.assertEqual(inbox.data["results"][0]["user"]["username"], "alice")
        self.assertEqual(recipient.put(f"/api/v1/connections/{relation.pk}/").status_code, 200)
        self.assertEqual(recipient.get("/api/v1/connections/?kind=requests").data["count"], 0)
        self.assertEqual(recipient.get("/api/v1/connections/?kind=followers").data["count"], 1)
        self.client.delete("/api/v1/members/bob/follow/")
        self.client.put("/api/v1/members/bob/follow/")
        relation = Follow.objects.get(follower=self.alice, target=self.bob)
        self.assertEqual(recipient.delete(f"/api/v1/connections/{relation.pk}/").status_code, 204)
        self.assertEqual(recipient.get("/api/v1/connections/?kind=requests").data["count"], 0)

    def test_anonymous_and_drafts_are_hidden(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get("/api/v1/feed/").status_code, [401, 403])
        self.client.force_authenticate(self.alice)
        self.post.published = False
        self.post.save()
        self.assertEqual(self.client.get("/api/v1/feed/").data["count"], 0)
        self.assertEqual(
            self.client.put(f"/api/v1/publications/{self.post.pk}/like/").status_code, 404
        )

    def test_reactions_persist_and_are_idempotent(self):
        url = f"/api/v1/publications/{self.post.pk}/like/"
        self.client.put(url)
        self.client.put(url)
        self.assertEqual(Reaction.objects.count(), 1)
        self.assertEqual(self.client.get("/api/v1/feed/").data["results"][0]["like_count"], 1)
        self.client.delete(url)
        self.assertEqual(Reaction.objects.count(), 0)

    def test_comment_replies_likes_and_moderation(self):
        url = f"/api/v1/publications/{self.post.pk}/comments/"
        root = self.client.post(url, {"text": "Hello"}, format="json").data
        reply = self.client.post(url, {"text": "Reply", "parent_id": root["id"]}, format="json")
        self.assertEqual(reply.status_code, 201)
        self.client.put(f"/api/v1/comments/{root['id']}/")
        self.assertEqual(Comment.objects.get(pk=root["id"]).likes.count(), 1)
        listed = {item["id"]: item for item in self.client.get(url).data["results"]}
        self.assertEqual(listed[root["id"]]["like_count"], 1)
        self.assertTrue(listed[root["id"]]["liked"])
        self.client.force_authenticate(self.bob)
        listed = {item["id"]: item for item in self.client.get(url).data["results"]}
        self.assertFalse(listed[root["id"]]["liked"])
        self.assertEqual(self.client.delete(f"/api/v1/comments/{root['id']}/").status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(f"/api/v1/comments/{root['id']}/").status_code, 204)
        self.assertEqual(Comment.objects.count(), 0)

    def test_parent_cannot_reference_another_publication(self):
        other = Publication.objects.create(
            kind="post", author=self.admin, event=self.event, title="Other", published=True
        )
        parent = Comment.objects.create(publication=other, author=self.alice, text="Other")
        self.assertEqual(
            self.client.post(
                f"/api/v1/publications/{self.post.pk}/comments/",
                {"text": "Reply", "parent_id": parent.pk},
                format="json",
            ).status_code,
            404,
        )

    def test_saved_pictures_require_accepted_follow_and_revoke_immediately(self):
        self.post.kind = "photo"
        self.post.save()
        Reaction.objects.create(user=self.bob, publication=self.post, action="save")
        url = "/api/v1/members/bob/saved/?kind=photo"
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.put("/api/v1/members/bob/follow/")
        self.assertEqual(self.client.get(url).status_code, 403)
        follow = Follow.objects.get(follower=self.alice, target=self.bob)
        self.assertEqual(self.client.put(f"/api/v1/connections/{follow.pk}/").status_code, 404)
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.put(f"/api/v1/connections/{follow.pk}/").status_code, 200)
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.get(url).data["count"], 1)
        self.client.delete("/api/v1/members/bob/follow/")
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_saved_posts_are_visible_and_pixel_follow_is_mandatory(self):
        Reaction.objects.create(user=self.bob, publication=self.post, action="save")
        self.assertEqual(self.client.get("/api/v1/members/bob/saved/?kind=post").data["count"], 1)
        self.client.get("/api/v1/feed/")
        self.assertTrue(Follow.objects.get(follower=self.alice, target=self.admin).mandatory)
        self.assertEqual(self.client.delete("/api/v1/members/pixel/follow/").status_code, 400)

    def test_member_cannot_publish_or_edit_email(self):
        self.assertEqual(self.client.post("/api/v1/feed/", {"title": "bad"}).status_code, 405)
        self.assertEqual(
            self.client.put(
                "/api/v1/me/profile/",
                {"display_name": "Alice", "department": "CS", "email": "changed@sait.ac.in"},
                format="json",
            ).status_code,
            400,
        )

    def test_username_changes_remain_unique(self):
        self.assertEqual(
            self.client.post(
                "/api/v1/me/username/", {"username": "ALICE.NEW"}, format="json"
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/me/username/", {"username": "BOB"}, format="json"
            ).status_code,
            400,
        )

    def test_signed_download_is_revoked_when_unpublished(self):
        url = self.client.get(f"/api/v1/publications/{self.post.pk}/download/").data["url"]
        path = url.split("8000")[1]
        self.assertEqual(self.client.get(path).status_code, 302)
        self.post.published = False
        self.post.save()
        self.assertEqual(self.client.get(path).status_code, 404)

    @patch("apps.community.media.drive_read_session")
    def test_drive_download_keeps_original_bytes_and_has_readable_filename(self, drive):
        self.post.post_media = ["first", "second"]
        self.post.drive_file_id = "first"
        self.post.save(update_fields=["post_media", "drive_file_id"])
        link = self.client.get(f"/api/v1/publications/{self.post.pk}/download/?image=1")
        path = link.data["url"].split("8000")[1]
        session = drive.return_value
        upstream = session.get.return_value
        upstream.status_code = 200
        upstream.headers = {"Content-Type": "image/jpeg"}
        upstream.iter_content.return_value = iter([b"original-photo"])

        response = self.client.get(path)
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="final-2.jpg"')
        self.assertEqual(b"".join(response.streaming_content), b"original-photo")
        self.assertTrue(session.get.call_args.args[0].endswith("/second"))

        session.get.side_effect = Timeout()
        self.assertEqual(self.client.get(path).status_code, 503)
        self.assertEqual(session.close.call_count, 2)

    @patch("apps.community.media.drive_read_session")
    def test_expired_drive_authorization_returns_safe_media_error(self, drive):
        from urllib.parse import urlsplit

        from apps.community.media import delivery_url

        self.post.drive_file_id = "original"
        self.post.save(update_fields=["drive_file_id"])
        session = drive.return_value
        session.get.side_effect = RefreshError("invalid_grant: Token has been expired or revoked.")
        for variant in ("thumbnail", "preview", "original"):
            url = delivery_url(self.post, self.alice, variant)
            response = self.client.get(urlsplit(url).path)
            self.assertEqual(response.status_code, 503)
            self.assertIn("Please try again later", str(response.data))
            self.assertNotIn("invalid_grant", str(response.data))
        self.assertEqual(session.close.call_count, 3)

    def test_gallery_counts_only_available_published_photos(self):
        for published, available in [(True, True), (True, False), (False, True)]:
            Publication.objects.create(
                kind="photo",
                author=self.admin,
                event=self.event,
                title="Photo",
                published=published,
                available=available,
            )
        gallery = self.client.get("/api/v1/events/?q=campus&tag=sports")
        self.assertEqual(gallery.data["results"][0]["photo_count"], 1)

    def test_partial_drive_listing_does_not_hide_photos(self):
        from apps.community.drive import sync_event

        self.post.kind = "photo"
        self.post.drive_file_id = "known"
        self.post.save()
        self.event.drive_folder_id = "folder"
        with patch("apps.community.drive.drive_read_session") as provider:
            provider.return_value.__enter__.return_value.get.side_effect = TimeoutError()
            with self.assertRaises(TimeoutError):
                sync_event(self.event, self.admin)
        self.post.refresh_from_db()
        self.assertTrue(self.post.available)
