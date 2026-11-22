import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User


class DriveAuthorizationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("pixel.club@sait.ac.in", "test")

    def test_null_origin_login_remains_blocked_with_recovery_message(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        client.get("/admin/login/")
        token = client.cookies["csrftoken"].value
        response = client.post(
            "/admin/login/",
            {"username": self.admin.email, "password": "test", "csrfmiddlewaretoken": token},
            HTTP_ORIGIN="null",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Chrome or Edge", status_code=403)

    def test_connection_requires_administrator_session(self):
        url = reverse("pixel_admin:connect_drive")
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_admin_login_preserves_same_origin_and_validates_csrf(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        page = client.get("/admin/login/")
        self.assertEqual(page.headers["Referrer-Policy"], "same-origin")
        token = client.cookies["csrftoken"].value
        response = client.post(
            "/admin/login/",
            {
                "username": self.admin.email,
                "password": "test",
                "csrfmiddlewaretoken": token,
                "next": "/admin/",
            },
            HTTP_ORIGIN="http://testserver",
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", client.session)
        user = User.objects.create_user("student@sait.ac.in", "test", email_verified=True)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("pixel_admin:connect_drive")).status_code, 302)

    @override_settings(GOOGLE_CLIENT_ID="test-client", GOOGLE_CLIENT_SECRET="test-secret")
    def test_offline_authorization_callback_is_bound_to_admin_session_and_one_use(self):
        with (
            TemporaryDirectory(dir=settings.BASE_DIR / ".local") as folder,
            override_settings(BASE_DIR=Path(folder)),
        ):
            self.client.force_login(self.admin)
            start = self.client.get(reverse("pixel_admin:connect_drive"))
            self.assertIn("code_challenge=", start.url)
            attempt = self.client.session["drive_oauth"]
            with patch("apps.community.drive_oauth.requests.post") as exchange:
                exchange.return_value = Mock()
                exchange.return_value.json.return_value = {"refresh_token": "test-refresh"}
                callback = self.client.get(
                    "/api/v1/auth/google/callback/",
                    {"state": attempt["state"], "code": "test-code"},
                )
            self.assertEqual(callback.status_code, 302, callback.content.decode())
            private = Path(folder) / ".local" / "drive-oauth.json"
            self.assertEqual(json.loads(private.read_text())["type"], "authorized_user")
            self.assertEqual(
                self.client.get(
                    "/api/v1/auth/google/callback/",
                    {"state": attempt["state"], "code": "test-code"},
                ).status_code,
                400,
            )

    @override_settings(GOOGLE_CLIENT_ID="test-client", GOOGLE_CLIENT_SECRET="test-secret")
    def test_cancelled_drive_authorization_does_not_create_credentials(self):
        self.client.force_login(self.admin)
        self.client.get(reverse("pixel_admin:connect_drive"))
        state = self.client.session["drive_oauth"]["state"]
        with patch("apps.community.drive_oauth.requests.post") as exchange:
            response = self.client.get(
                "/api/v1/auth/google/callback/", {"state": state, "error": "access_denied"}
            )
        self.assertEqual(response.status_code, 400)
        exchange.assert_not_called()

    def test_upload_without_pixel_account_authorization_is_actionable(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.community.drive import upload_media

        with (
            TemporaryDirectory(dir=settings.BASE_DIR / ".local") as folder,
            override_settings(BASE_DIR=Path(folder)),
        ):
            with self.assertRaisesMessage(ValueError, "Connect the Pixel Google account"):
                upload_media(SimpleUploadedFile("cover.jpg", b"\xff\xd8\xff"), "folder", "post")
