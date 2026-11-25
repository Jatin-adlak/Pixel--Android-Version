from datetime import timedelta
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import AuditLog, AuthSession, User
from apps.accounts.services import create_session
from apps.community.models import Comment, Event, EventSyncState, Publication, Reaction
from apps.community.synchronization import synchronize


class ManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            "pixel.club@sait.ac.in", "test", username="pixel", profile_completed=True
        )
        self.member = User.objects.create_user(
            "member@sait.ac.in",
            "test",
            username="member",
            email_verified=True,
            profile_completed=True,
        )
        self.event = Event.objects.create(
            title="Sports",
            tag="Sports",
            description="Campus finals",
            venue="Court",
            starts_at=timezone.now() - timedelta(days=2),
            ends_at=timezone.now() - timedelta(days=1),
            cover_url="https://example.org/c.jpg",
            drive_folder_id="event-folder",
            published=True,
        )
        self.photo = Publication.objects.create(
            kind="photo",
            author=self.admin,
            event=self.event,
            title="original.jpg",
            tag="Sports",
            drive_file_id="photo-file",
            published=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_member_cannot_use_any_admin_activity(self):
        self.client.force_authenticate(self.member)
        for path in ["dashboard/", "storage/", "events/", "publications/", "members/", "comments/"]:
            self.assertEqual(self.client.get("/api/v1/management/" + path).status_code, 403)
        self.assertEqual(
            self.client.post("/api/v1/management/events/", {}, format="json").status_code, 403
        )

    def test_administrator_requires_active_verified_staff_account(self):
        url = "/api/v1/management/dashboard/"
        self.assertEqual(self.client.get(url).status_code, 200)
        for flag in ("email_verified", "is_staff", "is_active"):
            setattr(self.admin, flag, False)
            self.assertEqual(self.client.get(url).status_code, 403)
            setattr(self.admin, flag, True)

    def test_admin_can_set_and_replace_password_and_revoke_sessions(self):
        self.member.set_unusable_password()
        self.member.save(update_fields=["password"])
        url = f"/api/v1/management/members/{self.member.pk}/password/"
        self.assertFalse(self.client.get(url.removesuffix("password/")).data["has_password"])
        for password in ("River-canvas-lantern-62", "Silver-violet-penguin-87"):
            session = create_session(self.member, "native").data
            other_client = APIClient()
            self.assertEqual(
                other_client.get(
                    "/api/v1/me/", HTTP_AUTHORIZATION=f"Bearer {session['access']}"
                ).status_code,
                200,
            )
            result = self.client.put(url, {"password": password}, format="json")
            self.assertEqual(result.status_code, 200)
            self.assertTrue(result.data["has_password"])
            self.assertNotIn("password", result.data)
            self.assertNotIn(password, str(result.data))
            self.member.refresh_from_db()
            self.assertTrue(self.member.check_password(password))
            self.assertFalse(AuthSession.objects.filter(user=self.member, revoked=False).exists())
            self.assertEqual(
                other_client.get(
                    "/api/v1/me/", HTTP_AUTHORIZATION=f"Bearer {session['access']}"
                ).status_code,
                401,
            )
            self.assertEqual(
                other_client.post(
                    "/api/v1/auth/refresh/",
                    {"client": "native", "refresh": session["refresh"]},
                    format="json",
                ).status_code,
                401,
            )
        self.assertEqual(
            AuditLog.objects.filter(
                actor=self.admin, action=f"member_password_set:{self.member.pk}"
            ).count(),
            2,
        )

    def test_password_requires_admin_and_leaves_verification_unchanged(self):
        url = f"/api/v1/management/members/{self.member.pk}/password/"
        password = {"password": "River-canvas-lantern-62"}
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.put(url, password, format="json").status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.client.put(url, {"password": "123456789012"}, format="json").status_code, 400
        )
        self.member.email_verified = False
        self.member.save(update_fields=["email_verified"])
        self.assertEqual(self.client.put(url, password, format="json").status_code, 200)
        self.member.refresh_from_db()
        self.assertFalse(self.member.email_verified)

    def test_peer_admin_cannot_change_owner_or_other_admin_password(self):
        peer = User.objects.create_superuser("peer@sait.ac.in", "test", username="peer")
        other = User.objects.create_superuser("other@sait.ac.in", "test", username="other")
        self.client.force_authenticate(peer)
        for member in (self.admin, other):
            url = f"/api/v1/management/members/{member.pk}/"
            self.assertFalse(self.client.get(url).data["can_set_password"])
            self.assertEqual(
                self.client.put(
                    url + "password/", {"password": "River-canvas-lantern-62"}, format="json"
                ).status_code,
                403,
            )
            self.assertEqual(
                self.client.patch(url, {"role": "Student"}, format="json").status_code, 403
            )
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.client.put(
                f"/api/v1/management/members/{other.pk}/password/",
                {"password": "River-canvas-lantern-62"},
                format="json",
            ).status_code,
            200,
        )

    def test_role_without_staff_cannot_moderate_another_members_comment(self):
        comment = Comment.objects.create(publication=self.photo, author=self.member, text="Hello")
        self.admin.is_staff = False
        self.assertEqual(self.client.delete(f"/api/v1/comments/{comment.pk}/").status_code, 403)
        self.assertTrue(Comment.objects.filter(pk=comment.pk).exists())

    def test_comment_groups_and_content_search_are_scoped_and_paginated(self):
        other = Publication.objects.create(
            kind="post",
            author=self.admin,
            event=self.event,
            title="Another post",
            drive_file_id="other-file",
        )
        for index in range(23):
            Comment.objects.create(
                publication=self.photo, author=self.member, text=f"Campus photo {index}"
            )
        target = Comment.objects.create(
            publication=self.photo, author=self.member, text="Wonderful LIGHTING at the festival"
        )
        Comment.objects.create(publication=other, author=self.member, text="Lighting elsewhere")
        groups = self.client.get("/api/v1/management/comments/groups/")
        self.assertEqual(groups.status_code, 200)
        self.assertEqual(groups.data["count"], 2)
        counts = {row["id"]: row["comment_count"] for row in groups.data["results"]}
        self.assertEqual(counts[str(self.photo.pk)], 24)
        result = self.client.get(
            "/api/v1/management/comments/", {"publication": str(self.photo.pk), "q": "lighting"}
        )
        self.assertEqual(result.data["count"], 1)
        self.assertEqual(result.data["results"][0]["id"], target.pk)
        self.assertEqual(
            self.client.get(
                "/api/v1/management/comments/", {"publication": str(self.photo.pk), "q": "no match"}
            ).data["count"],
            0,
        )
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.get("/api/v1/management/comments/groups/").status_code, 403)

    def test_dashboard_reports_drafts_engagement_and_sync_health(self):
        Publication.objects.create(
            kind="post",
            author=self.admin,
            event=self.event,
            title="Draft",
            drive_file_id="draft-file",
            published=False,
        )
        Reaction.objects.create(user=self.member, publication=self.photo, action="like")
        EventSyncState.objects.create(
            event=self.event,
            next_run_at=timezone.now(),
            last_success_at=timezone.now(),
            last_error="Try again",
        )
        result = self.client.get("/api/v1/management/dashboard/")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["drafts"], 1)
        self.assertEqual(result.data["likes"], 1)
        self.assertEqual(result.data["sync"]["errors"], 1)
        self.assertEqual(result.data["recent"][0]["title"], "Draft")

    @patch("apps.community.management_api.check_event_folder")
    def test_completed_gallery_folder_requires_drive_and_is_separate_from_spotlight(self, check):
        payload = {
            "title": "Completed Festival",
            "tag": "Cultural",
            "description": "A campus festival",
            "venue": "Hall",
            "starts_at": (timezone.now() - timedelta(days=3)).isoformat(),
            "ends_at": (timezone.now() - timedelta(days=2)).isoformat(),
            "cover_url": "https://example.org/c.jpg",
            "drive_folder_id": "festival-folder",
            "published": False,
        }
        missing = dict(payload)
        missing.pop("drive_folder_id")
        self.assertEqual(
            self.client.post("/api/v1/management/events/", missing, format="json").status_code, 400
        )
        result = self.client.post("/api/v1/management/events/", payload, format="json")
        self.assertEqual(result.status_code, 201, result.data)
        check.assert_called_once_with("festival-folder")
        future = {
            **payload,
            "starts_at": (timezone.now() + timedelta(days=2)).isoformat(),
            "ends_at": (timezone.now() + timedelta(days=3)).isoformat(),
        }
        self.assertEqual(
            self.client.post("/api/v1/management/events/", future, format="json").status_code, 400
        )
        self.assertEqual(self.client.get("/api/v1/management/spotlights/").data["count"], 0)

    def test_spotlight_announcement_does_not_create_a_gallery_or_drive_folder(self):
        payload = {
            "title": "Upcoming Festival",
            "tag": "Cultural",
            "description": "Coming soon",
            "venue": "Hall",
            "starts_at": (timezone.now() + timedelta(days=2)).isoformat(),
            "ends_at": (timezone.now() + timedelta(days=3)).isoformat(),
            "cover_url": "https://example.org/c.jpg",
            "form_url": "https://example.org/form",
            "published": True,
        }
        with patch("apps.community.spotlight_api.drive_session") as provider:
            result = self.client.post("/api/v1/management/spotlights/", payload, format="json")
        self.assertEqual(result.status_code, 201, result.data)
        provider.assert_not_called()
        self.assertEqual(Event.objects.count(), 1)
        public = self.client.get("/api/v1/spotlights/")
        self.assertEqual(public.data["count"], 1)
        self.assertNotIn(
            result.data["id"],
            [str(row["id"]) for row in self.client.get("/api/v1/events/").data["results"]],
        )
        invalid = {**payload, "drive_folder_id": "unrelated"}
        self.assertEqual(
            self.client.post("/api/v1/management/spotlights/", invalid, format="json").status_code,
            400,
        )

    def test_admin_publication_cannot_spoof_author(self):
        response = self.client.post(
            "/api/v1/management/publications/",
            {
                "kind": "post",
                "event": str(self.event.pk),
                "title": "Post",
                "tag": "Sports",
                "drive_file_id": "file",
                "author": str(self.member.pk),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    @patch("apps.community.management_api.check_publication_media")
    def test_multipart_post_does_not_default_internal_availability_to_false(self, check):
        response = self.client.post(
            "/api/v1/management/publications/",
            {
                "kind": "post",
                "event": str(self.event.pk),
                "title": "Published multipart post",
                "caption": "Campus",
                "tag": "Sports",
                "drive_file_id": "post-file",
                "published": "true",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data["published"])
        self.assertTrue(response.data["available"])
        check.assert_called_once_with("post-file", "post")
        feed = self.client.get("/api/v1/feed/?kind=post").data["results"]
        self.assertIn(response.data["id"], [item["id"] for item in feed])

    def test_availability_is_not_a_client_editable_publication_field(self):
        response = self.client.patch(
            f"/api/v1/management/publications/{self.photo.pk}/", {"available": False}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.photo.refresh_from_db()
        self.assertTrue(self.photo.available)

    def test_main_admin_and_current_admin_access_cannot_be_removed(self):
        response = self.client.patch(
            f"/api/v1/management/members/{self.admin.pk}/", {"is_active": False}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(
            f"/api/v1/management/members/{self.member.pk}/", {"role": "Faculty"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.member.refresh_from_db()
        self.assertEqual(self.member.role, "Faculty")
        self.assertFalse(self.member.is_staff)

    @patch("apps.community.management_api.change_drive_file")
    def test_pixel_photo_rename_updates_drive(self, change):
        response = self.client.patch(
            f"/api/v1/management/publications/{self.photo.pk}/",
            {"title": "renamed.jpg"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        change.assert_called_once_with("photo-file", name="renamed.jpg")

    @patch("apps.community.management_api.change_drive_file")
    def test_removal_trashes_drive_and_retains_saves_for_restore(self, change):
        Reaction.objects.create(user=self.member, publication=self.photo, action="save")
        response = self.client.delete(f"/api/v1/management/publications/{self.photo.pk}/")
        self.assertEqual(response.status_code, 204)
        change.assert_called_once_with("photo-file", trashed=True)
        self.photo.refresh_from_db()
        self.assertFalse(self.photo.available)
        self.assertEqual(Reaction.objects.count(), 1)

    @patch("apps.community.management_api.upload", return_value="photo-file")
    def test_photo_replacement_keeps_original_file_identity(self, upload):
        file = SimpleUploadedFile("replacement.jpg", b"\xff\xd8\xff", content_type="image/jpeg")
        response = self.client.patch(
            f"/api/v1/management/publications/{self.photo.pk}/",
            {"original_upload": file},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(upload.call_args.kwargs["existing_id"], "photo-file")
        self.assertEqual(Publication.objects.count(), 1)

    def test_drive_changes_reconcile_only_gallery_media_and_preserve_saves(self):
        from apps.community.drive import sync_event

        post = Publication.objects.create(
            kind="post",
            author=self.admin,
            event=self.event,
            title="Post",
            tag="Sports",
            drive_file_id="post-file",
            published=True,
        )
        Reaction.objects.create(user=self.member, publication=self.photo, action="save")
        with patch("apps.community.drive.drive_read_session") as provider:
            response = Mock()
            response.json.return_value = {
                "files": [
                    {
                        "id": "photo-file",
                        "name": "Drive rename.jpg",
                        "mimeType": "image/jpeg",
                        "version": "2",
                    },
                    {"id": "new-file", "name": "New.jpg", "mimeType": "image/jpeg", "version": "1"},
                ]
            }
            folder_response = Mock()
            folder_response.json.return_value = {
                "mimeType": "application/vnd.google-apps.folder",
                "trashed": False,
            }
            provider.return_value.__enter__.return_value.get.side_effect = [
                folder_response,
                response,
            ]
            self.assertEqual(sync_event(self.event, self.admin), 2)
        self.photo.refresh_from_db()
        self.assertEqual(self.photo.title, "Drive rename.jpg")
        self.assertEqual(self.photo.source_revision, "2")
        post.refresh_from_db()
        self.assertTrue(post.available)
        self.assertEqual(Reaction.objects.count(), 1)

    def test_event_lease_rejects_conflicting_sync(self):
        EventSyncState.objects.create(
            event=self.event,
            next_run_at=timezone.now(),
            lease_until=timezone.now() + timedelta(minutes=5),
        )
        with self.assertRaises(ValidationError):
            synchronize(self.event, self.admin)

    def test_failed_sync_retries_without_removing_photos(self):
        with patch("apps.community.synchronization.sync_event", side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                synchronize(self.event, self.admin)
        state = EventSyncState.objects.get(event=self.event)
        self.assertEqual(state.failures, 1)
        self.assertIsNone(state.lease_until)
        self.assertGreater(state.next_run_at, timezone.now())
        self.photo.refresh_from_db()
        self.assertTrue(self.photo.available)
