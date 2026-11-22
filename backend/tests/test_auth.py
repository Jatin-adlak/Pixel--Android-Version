import re
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import (
    EmailVerification,
    OAuthAttempt,
    PolicyAcceptance,
    User,
)
from apps.accounts.services import challenge, digest

PASSWORD = "Strong-test-passphrase-347!"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AuthTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        from rest_framework.throttling import ScopedRateThrottle

        cache.clear()
        rates = patch.dict(
            ScopedRateThrottle.THROTTLE_RATES,
            {"email": "1000/hour", "auth": "1000/hour", "anon": "1000/hour"},
        )
        rates.start()
        self.addCleanup(rates.stop)
        self.client = APIClient()
        self.policy = {
            "privacy_accepted": True,
            "terms_accepted": True,
            "privacy_version": settings.PRIVACY_VERSION,
            "terms_version": settings.TERMS_VERSION,
        }

    def user(self, email="student@sait.ac.in", **kwargs):
        return User.objects.create_user(email, PASSWORD, email_verified=True, **kwargs)

    def login(self, identifier="student@sait.ac.in", **kwargs):
        return self.client.post(
            "/api/v1/auth/login/",
            {
                **self.policy,
                "identifier": identifier,
                "password": PASSWORD,
                "client": "native",
                **kwargs,
            },
            format="json",
        )

    def authorize(self, user):
        response = self.login(user.email)
        self.assertEqual(response.status_code, 200, response.data)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
        return response

    def test_exact_college_domain_and_no_privileged_signup(self):
        for email in ["bad@gmail.com", "bad@sait.ac.in.evil.com", "bad@sub.sait.ac.in"]:
            response = self.client.post(
                "/api/v1/auth/register/",
                {**self.policy, "email": email, "password": PASSWORD},
                format="json",
            )
            self.assertEqual(response.status_code, 400)
        for field in ["role", "is_staff", "email_verified"]:
            response = self.client.post(
                "/api/v1/auth/register/",
                {
                    **self.policy,
                    "email": "member@sait.ac.in",
                    "password": PASSWORD,
                    field: "Administrator",
                },
                format="json",
            )
            self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    def test_verification_required_single_use_and_password_replaced(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/v1/auth/register/",
                {**self.policy, "email": "Student@SAIT.AC.IN", "password": PASSWORD},
                format="json",
            )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(self.login().status_code, 403)
        token = re.search(r"token=([\w-]+)", mail.outbox[0].body).group(1)
        self.assertFalse(EmailVerification.objects.filter(digest=token).exists())
        data = {"token": token, "password": "A-new-verified-passphrase-643!"}
        self.assertEqual(
            self.client.post("/api/v1/auth/verify/", data, format="json").status_code, 200
        )
        self.assertEqual(
            self.client.post("/api/v1/auth/verify/", data, format="json").status_code, 400
        )
        self.assertEqual(self.login().status_code, 401)
        self.assertEqual(self.login(password=data["password"]).status_code, 200)

    def test_policy_required_and_versioned(self):
        self.user()
        self.assertEqual(self.login(privacy_accepted=False).status_code, 400)
        self.assertEqual(self.login(terms_version="old").status_code, 400)
        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(PolicyAcceptance.objects.count(), 1)

    def test_username_or_email_login_and_onboarding_constraints(self):
        user = self.user()
        self.authorize(user)
        self.assertEqual(self.client.get("/api/v1/users/?q=ab").status_code, 403)
        self.assertEqual(
            self.client.put(
                "/api/v1/me/profile/", {"display_name": "Member", "department": "IT"}, format="json"
            ).status_code,
            400,
        )
        for name in ["a", ".hello", "hello.", "hello..world", "bad name", "admin", "12345"]:
            self.assertEqual(
                self.client.post(
                    "/api/v1/me/username/", {"username": name}, format="json"
                ).status_code,
                400,
            )
        self.assertEqual(
            self.client.post(
                "/api/v1/me/username/", {"username": "college.member_1"}, format="json"
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.put(
                "/api/v1/me/profile/",
                {"display_name": "Member", "department": "IT", "role": "Administrator"},
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.put(
                "/api/v1/me/profile/", {"display_name": "Member", "department": "IT"}, format="json"
            ).status_code,
            200,
        )
        self.assertEqual(self.client.post("/api/v1/me/tour/", {}, format="json").status_code, 200)
        self.client.credentials()
        self.assertEqual(self.login("college.member_1").status_code, 200)
        self.assertEqual(self.login("STUDENT@SAIT.AC.IN").status_code, 200)

    def test_username_is_unique_and_reserved_for_admin(self):
        self.user("other@sait.ac.in", username="taken.name")
        user = self.user()
        self.authorize(user)
        self.assertEqual(
            self.client.post(
                "/api/v1/me/username/", {"username": "TAKEN.NAME"}, format="json"
            ).status_code,
            400,
        )

    def test_refresh_rotates_and_logout_revokes_access_immediately(self):
        user = self.user()
        login = self.authorize(user)
        self.client.credentials()
        data = {"client": "native", "refresh": login.data["refresh"]}
        refreshed = self.client.post("/api/v1/auth/refresh/", data, format="json")
        self.assertEqual(refreshed.status_code, 200)
        self.assertNotEqual(refreshed.data["refresh"], data["refresh"])
        self.assertEqual(
            self.client.post("/api/v1/auth/refresh/", data, format="json").status_code, 401
        )
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + refreshed.data["access"])
        self.assertEqual(
            self.client.post("/api/v1/auth/logout/", {}, format="json").status_code, 200
        )
        self.assertEqual(self.client.get("/api/v1/me/").status_code, 401)

    def test_student_faculty_and_admin_permissions(self):
        for role in [User.Role.STUDENT, User.Role.FACULTY]:
            user = self.user(f"{role.lower()}@sait.ac.in", role=role)
            self.authorize(user)
            self.assertEqual(self.client.get("/api/v1/management/status/").status_code, 403)
            self.client.force_login(user)
            self.assertEqual(self.client.get("/admin/").status_code, 302)
            self.client.logout()
            self.client.credentials()
        admin = User.objects.create_superuser(settings.MAIN_ADMIN_EMAIL, PASSWORD)
        self.authorize(admin)
        self.assertEqual(self.client.get("/api/v1/management/status/").status_code, 200)
        self.client.force_login(admin)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_web_cookie_is_httponly_and_csrf_is_required(self):
        self.user()
        client = APIClient(enforce_csrf_checks=True)
        payload = {
            **self.policy,
            "identifier": "student@sait.ac.in",
            "password": PASSWORD,
            "client": "web",
        }
        self.assertEqual(
            client.post("/api/v1/auth/login/", payload, format="json").status_code, 403
        )
        csrf = client.get("/api/v1/auth/config/").data["csrf_token"]
        response = client.post("/api/v1/auth/login/", payload, format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn("refresh", response.data)
        self.assertTrue(response.cookies["pixel_refresh"]["httponly"])
        self.assertEqual(
            client.post("/api/v1/auth/refresh/", {"client": "web"}, format="json").status_code, 403
        )

    @override_settings(CSRF_TRUSTED_ORIGINS=["http://localhost:8082"])
    def test_web_refresh_recovers_with_a_fresh_csrf_token_and_rejects_foreign_origin(self):
        self.user()
        client = APIClient(enforce_csrf_checks=True)
        token = client.get("/api/v1/auth/config/").data["csrf_token"]
        payload = {
            **self.policy,
            "identifier": "student@sait.ac.in",
            "password": PASSWORD,
            "client": "web",
        }
        login = client.post(
            "/api/v1/auth/login/",
            payload,
            format="json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="http://localhost:8082",
        )
        self.assertEqual(login.status_code, 200, login.data)
        replacement = APIClient(enforce_csrf_checks=True)
        replacement.get("/api/v1/auth/config/")
        client.cookies[settings.CSRF_COOKIE_NAME] = replacement.cookies[
            settings.CSRF_COOKIE_NAME
        ].value
        stale = client.post(
            "/api/v1/auth/refresh/",
            {"client": "web"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="http://localhost:8082",
        )
        self.assertEqual(stale.status_code, 403)
        self.assertEqual(stale.data["code"], "csrf_failed")
        fresh = client.get("/api/v1/auth/config/").data["csrf_token"]
        rejected = client.post(
            "/api/v1/auth/refresh/",
            {"client": "web"},
            format="json",
            HTTP_X_CSRFTOKEN=fresh,
            HTTP_ORIGIN="http://foreign.example",
        )
        self.assertEqual(rejected.status_code, 403)
        accepted = client.post(
            "/api/v1/auth/refresh/",
            {"client": "web"},
            format="json",
            HTTP_X_CSRFTOKEN=fresh,
            HTTP_ORIGIN="http://localhost:8082",
        )
        self.assertEqual(accepted.status_code, 200, accepted.data)

    def test_search_is_private_and_hides_email(self):
        user = self.user(
            username="member.one", display_name="Campus Member", profile_completed=True
        )
        self.assertEqual(self.client.get("/api/v1/users/?q=member").status_code, 401)
        self.authorize(user)
        response = self.client.get("/api/v1/users/?q=member")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertNotIn("email", response.data["results"][0])
        self.assertNotIn("is_staff", response.data["results"][0])

    def test_reset_is_not_enabled(self):
        self.assertFalse(self.client.get("/api/v1/auth/config/").data["password_reset_enabled"])
        self.assertEqual(
            self.client.post("/api/v1/auth/password-reset/", {}, format="json").status_code, 404
        )

    def test_administrator_password_change_invalidates_existing_tokens(self):
        user = self.user()
        login = self.authorize(user)
        user.set_password("A-new-secure-password-851!")
        user.save(update_fields=["password"])
        self.assertEqual(self.client.get("/api/v1/me/").status_code, 401)
        self.client.credentials()
        response = self.client.post(
            "/api/v1/auth/refresh/",
            {"client": "native", "refresh": login.data["refresh"]},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_json_arrays_are_rejected_without_server_errors(self):
        for path in ["register", "login", "refresh", "google/start", "google/exchange"]:
            response = self.client.post(
                f"/api/v1/auth/{path}/", [{"role": "Administrator"}], format="json"
            )
            self.assertEqual(response.status_code, 400)

    def test_moments_are_published_read_only_and_paginated(self):
        from apps.accounts.models import Moment

        user = self.user(username="video.member", profile_completed=True)
        Moment.objects.create(title="Draft", video_url="https://example.com/draft.mp4")
        Moment.objects.create(
            title="Published", video_url="https://example.com/clip.mp4", published=True
        )
        self.assertEqual(self.client.get("/api/v1/moments/").status_code, 401)
        self.authorize(user)
        response = self.client.get("/api/v1/moments/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Published")
        self.assertEqual(self.client.post("/api/v1/moments/", {}, format="json").status_code, 405)

    def test_credentials_have_independent_rate_limits(self):
        from apps.accounts.throttles import CredentialThrottle

        self.user()
        with patch.dict(CredentialThrottle.THROTTLE_RATES, {"credential": "2/minute"}):
            self.assertEqual(self.login(password="wrong").status_code, 401)
            self.assertEqual(self.login(password="wrong").status_code, 401)
            self.assertEqual(self.login(password="wrong").status_code, 429)

    def test_expired_verification_is_rejected(self):
        user = User.objects.create_user("waiting@sait.ac.in", PASSWORD)
        EmailVerification.objects.create(
            user=user, digest=digest("expired"), expires_at=timezone.now() - timedelta(minutes=1)
        )
        response = self.client.post(
            "/api/v1/auth/verify/", {"token": "expired", "password": PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    @override_settings(GOOGLE_CLIENT_ID="test-client", GOOGLE_CLIENT_SECRET="test-secret")
    def test_google_state_pkce_nonce_and_one_time_exchange(self):
        verifier = "a" * 64
        started = self.client.post(
            "/api/v1/auth/google/start/",
            {**self.policy, "client": "native", "challenge": challenge(verifier)},
            format="json",
        )
        self.assertEqual(started.status_code, 200)
        params = parse_qs(urlparse(started.data["url"]).query)
        self.assertEqual(params["hd"], ["sait.ac.in"])
        self.assertEqual(params["code_challenge_method"], ["S256"])
        attempt = OAuthAttempt.objects.get(state_digest=digest(params["state"][0]))
        claims = {
            "sub": "college-google-subject",
            "email": "google@sait.ac.in",
            "email_verified": True,
            "hd": "sait.ac.in",
            "nonce": attempt.nonce,
        }
        with patch("apps.accounts.services.google_claims", return_value=claims):
            callback = self.client.get(
                "/api/v1/auth/google/callback/",
                {"state": params["state"][0], "code": "provider-code"},
            )
        self.assertEqual(callback.status_code, 302)
        ticket = parse_qs(urlparse(callback["Location"]).query)["ticket"][0]
        self.assertEqual(
            self.client.get(
                "/api/v1/auth/google/callback/", {"state": params["state"][0]}
            ).status_code,
            400,
        )
        data = {"ticket": ticket, "verifier": "b" * 64, "client": "native"}
        self.assertEqual(
            self.client.post("/api/v1/auth/google/exchange/", data, format="json").status_code, 401
        )
        data["verifier"] = verifier
        self.assertEqual(
            self.client.post("/api/v1/auth/google/exchange/", data, format="json").status_code, 200
        )
        self.assertEqual(
            self.client.post("/api/v1/auth/google/exchange/", data, format="json").status_code, 401
        )

    def test_google_verifier_rejects_domain_and_unverified_claims(self):
        from rest_framework.exceptions import AuthenticationFailed

        from apps.accounts.services import google_claims, google_user

        attempt = OAuthAttempt(nonce="expected", provider_verifier="value")
        for field, value in [("hd", "evil.com"), ("email_verified", False), ("nonce", "wrong")]:
            claims = {"nonce": "expected", "hd": "sait.ac.in", "email_verified": True, field: value}
            with (
                patch("apps.accounts.services.httpx.Client") as client,
                patch("apps.accounts.services.id_token.verify_oauth2_token", return_value=claims),
            ):
                client.return_value.__enter__.return_value.post.return_value.json.return_value = {
                    "id_token": "value"
                }
                with self.assertRaises(AuthenticationFailed):
                    google_claims("code", attempt)
        with self.assertRaises(AuthenticationFailed):
            google_user({"sub": "other", "email": "person@gmail.com"})

    def test_direct_google_callback_guides_browser_without_authenticating(self):
        from apps.accounts.models import AuthSession, OAuthTicket

        with patch("apps.accounts.services.google_claims") as provider:
            response = self.client.get("/api/v1/auth/google/callback/", HTTP_ACCEPT="text/html")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response["Location"],
                settings.OAUTH_APP_REDIRECTS["web"] + "?error=invalid_oauth_request",
            )
            self.assertEqual(response["Cache-Control"], "no-store")
            self.assertEqual(
                self.client.get(
                    "/api/v1/auth/google/callback/", HTTP_ACCEPT="application/json"
                ).status_code,
                400,
            )
            provider.assert_not_called()
        self.assertFalse(AuthSession.objects.exists())
        self.assertFalse(OAuthTicket.objects.exists())

    def test_expired_google_callback_cannot_create_a_session(self):
        from apps.accounts.models import AuthSession, OAuthTicket

        attempt = OAuthAttempt.objects.create(
            state_digest=digest("expired-state"),
            nonce="test-nonce",
            provider_verifier="p" * 64,
            app_challenge=challenge("a" * 64),
            client="web",
            privacy_version=settings.PRIVACY_VERSION,
            terms_version=settings.TERMS_VERSION,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        with patch("apps.accounts.services.google_claims") as provider:
            response = self.client.get(
                "/api/v1/auth/google/callback/",
                {"state": "expired-state", "code": "untrusted-code"},
                HTTP_ACCEPT="text/html",
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response["Location"],
                settings.OAUTH_APP_REDIRECTS["web"] + "?error=invalid_oauth_request",
            )
            provider.assert_not_called()
        attempt.refresh_from_db()
        self.assertFalse(attempt.used)
        self.assertFalse(AuthSession.objects.exists())
        self.assertFalse(OAuthTicket.objects.exists())

    def test_google_claiming_unverified_account_discards_old_password(self):
        from apps.accounts.services import google_user

        user = User.objects.create_user("google@sait.ac.in", PASSWORD)
        with transaction_for_test():
            signed_in = google_user({"sub": "new-sub", "email": user.email})
        self.assertTrue(signed_in.email_verified)
        self.assertFalse(signed_in.has_usable_password())
        self.assertEqual(signed_in.role, User.Role.STUDENT)


def transaction_for_test():
    from django.db import transaction

    return transaction.atomic()
