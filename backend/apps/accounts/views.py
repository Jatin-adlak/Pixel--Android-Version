import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.middleware.csrf import CsrfViewMiddleware, get_token
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.utils import get_md5_hash_password

from . import services
from .authentication import IsAdministrator, Onboarded
from .models import (
    AuditLog,
    AuthSession,
    EmailVerification,
    Moment,
    OAuthAttempt,
    OAuthTicket,
    User,
)
from .policies import PRIVACY, TERMS
from .serializers import (
    EmailSerializer,
    GoogleExchangeSerializer,
    GoogleStartSerializer,
    LoginSerializer,
    ProfileSerializer,
    RefreshSerializer,
    RegisterSerializer,
    UsernameSerializer,
    VerifySerializer,
    user_data,
)

GENERIC_EMAIL_MESSAGE = (
    "If this college account needs verification, a link will be sent. Check your college inbox."
)


def validated(schema, request):
    serializer = schema(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def csrf_check(request):
    def protected_view(request):
        return None

    reason = CsrfViewMiddleware(lambda r: None).process_view(
        request._request, protected_view, (), {}
    )
    if reason:
        raise PermissionDenied(
            {
                "detail": "Security check failed. Reload the page and try again.",
                "code": "csrf_failed",
            }
        )


def check_browser(request, client):
    if client == "web":
        csrf_check(request)


class PublicView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = "auth"

    def get_throttles(self):
        from .throttles import CredentialThrottle, EmailCredentialThrottle

        return super().get_throttles() + [
            EmailCredentialThrottle() if self.throttle_scope == "email" else CredentialThrottle()
        ]

    def get_authenticate_header(self, request):
        return "Bearer"

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response


class ConfigView(PublicView):
    throttle_scope = None

    def get(self, request):
        return Response(
            {
                "domain": settings.COLLEGE_DOMAIN,
                "google_enabled": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
                "password_reset_enabled": False,
                "privacy_version": settings.PRIVACY_VERSION,
                "terms_version": settings.TERMS_VERSION,
                "privacy": PRIVACY,
                "terms": TERMS,
                "csrf_token": get_token(request._request),
            }
        )


class RegisterView(PublicView):
    throttle_scope = "email"

    def post(self, request):
        data = validated(RegisterSerializer, request)
        if data["email"] != settings.MAIN_ADMIN_EMAIL:
            with transaction.atomic():
                user, created = User.objects.get_or_create(
                    email=data["email"], defaults={"password": make_password(data["password"])}
                )
                if created:
                    services.accept_policies(user, data, "signup")
                    AuditLog.objects.create(actor=user, action="signup")
                    transaction.on_commit(lambda: services.send_verification(user))
        return Response({"detail": GENERIC_EMAIL_MESSAGE}, status=status.HTTP_202_ACCEPTED)


class ResendVerificationView(PublicView):
    throttle_scope = "email"

    def post(self, request):
        data = validated(EmailSerializer, request)
        user = User.objects.filter(
            email=data["email"], email_verified=False, is_active=True
        ).first()
        if user and user.email != settings.MAIN_ADMIN_EMAIL:
            services.send_verification(user)
        return Response({"detail": GENERIC_EMAIL_MESSAGE}, status=status.HTTP_202_ACCEPTED)


class VerifyView(PublicView):
    def post(self, request):
        data = validated(VerifySerializer, request)
        with transaction.atomic():
            record = (
                EmailVerification.objects.select_for_update()
                .select_related("user")
                .filter(
                    digest=services.digest(data["token"]), used=False, expires_at__gt=timezone.now()
                )
                .first()
            )
            if not record or not record.user.is_active or record.user.email_verified:
                raise ValidationError(
                    "This verification link is invalid or expired. Request a new link."
                )
            user = record.user
            try:
                validate_password(data["password"], user)
            except DjangoValidationError as exc:
                raise ValidationError({"password": exc.messages}) from exc
            user.set_password(data["password"])
            user.email_verified = True
            user.save(update_fields=["password", "email_verified"])
            EmailVerification.objects.filter(user=user).update(used=True)
            AuditLog.objects.create(actor=user, action="email_verified")
        return Response({"detail": "College email verified. You can now sign in."})


class LoginView(PublicView):
    def post(self, request):
        data = validated(LoginSerializer, request)
        check_browser(request, data["client"])
        identifier = data["identifier"].strip().lower()
        if identifier.startswith("@") and identifier.count("@") == 1:
            identifier = identifier[1:]
        user = User.objects.filter(
            Q(email=identifier) if "@" in identifier else Q(username=identifier)
        ).first()
        if not user:
            make_password(data["password"])
            raise AuthenticationFailed("Email/username or password is incorrect.")
        if not check_password(data["password"], user.password) or not user.is_active:
            raise AuthenticationFailed("Email/username or password is incorrect.")
        if user.email.rsplit("@", 1)[-1] != settings.COLLEGE_DOMAIN:
            raise AuthenticationFailed("A college account is required.")
        if not user.email_verified:
            return Response(
                {
                    "detail": "Verify your college email before signing in.",
                    "code": "email_unverified",
                },
                status=403,
            )
        with transaction.atomic():
            services.accept_policies(user, data, "login")
            return services.create_session(user, data["client"])


class RefreshView(PublicView):
    throttle_scope = None

    def post(self, request):
        data = validated(RefreshSerializer, request)
        client = data["client"]
        check_browser(request, client)
        raw = request.COOKIES.get("pixel_refresh") if client == "web" else data.get("refresh")
        try:
            token = RefreshToken(raw or "")
        except (TokenError, TypeError) as exc:
            raise AuthenticationFailed("Please sign in again.") from exc
        with transaction.atomic():
            session = (
                AuthSession.objects.select_for_update()
                .select_related("user")
                .filter(id=token.get("sid"), revoked=False, expires_at__gt=timezone.now())
                .first()
            )
            if (
                not session
                or str(session.user_id) != str(token.get("user_id"))
                or session.refresh_jti != token["jti"]
            ):
                raise AuthenticationFailed("Please sign in again.")
            if (
                not session.user.is_active
                or not session.user.email_verified
                or session.user.email.rsplit("@", 1)[-1] != settings.COLLEGE_DOMAIN
            ):
                raise AuthenticationFailed("This account is unavailable.")
            if token.get(jwt_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(
                session.user.password
            ):
                raise AuthenticationFailed("Your password has changed. Please sign in again.")
            token.blacklist()
            new_token = services.make_refresh(session.user, session)
            return services.token_response(session.user, new_token, client)


class LogoutView(APIView):
    def post(self, request):
        AuthSession.objects.filter(id=request.auth.get("sid"), user=request.user).update(
            revoked=True
        )
        AuditLog.objects.create(actor=request.user, action="logout")
        response = Response({"detail": "Signed out."})
        response.delete_cookie("pixel_refresh", path="/api/v1/auth/", samesite="Lax")
        return response


class MeView(APIView):
    def get(self, request):
        return Response(user_data(request.user))


class UsernameView(APIView):
    def post(self, request):
        data = validated(UsernameSerializer, request)
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            if User.objects.filter(username=data["username"]).exclude(pk=user.pk).exists():
                raise ValidationError({"username": "This username is taken."})
            user.username = data["username"]
            try:
                with transaction.atomic():
                    user.save(update_fields=["username"])
            except IntegrityError as exc:
                raise ValidationError({"username": "This username is taken."}) from exc
            AuditLog.objects.create(actor=user, action="username_created")
        return Response(user_data(user))


class ProfileView(APIView):
    def put(self, request):
        if not request.user.username:
            raise ValidationError("Choose your username first.")
        data = validated(ProfileSerializer, request)
        for name, value in data.items():
            setattr(request.user, name, value)
        request.user.profile_completed = True
        request.user.save(update_fields=[*data, "profile_completed"])
        AuditLog.objects.create(actor=request.user, action="profile_updated")
        return Response(user_data(request.user))


class TourView(APIView):
    permission_classes = [IsAuthenticated, Onboarded]

    def post(self, request):
        request.user.tour_completed = True
        request.user.save(update_fields=["tour_completed"])
        return Response(user_data(request.user))


class UserSearchView(APIView):
    permission_classes = [IsAuthenticated, Onboarded]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "search"

    def get(self, request):
        query = request.query_params.get("q", "").strip()[:80]
        if len(query) < 2:
            return Response({"results": []})
        users = (
            User.objects.filter(is_active=True, email_verified=True, profile_completed=True)
            .exclude(username=None)
            .filter(Q(username__icontains=query) | Q(display_name__icontains=query))
            .order_by("username")[:20]
        )
        return Response({"results": [public_profile(u) for u in users]})


def public_profile(user):
    return {
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "department": user.department,
        "year": user.year,
        "bio": user.bio,
        "role": user.role,
    }


class PublicProfileView(APIView):
    permission_classes = [IsAuthenticated, Onboarded]

    def get(self, request, username):
        from django.shortcuts import get_object_or_404

        user = get_object_or_404(
            User,
            username=username.lower(),
            is_active=True,
            email_verified=True,
            profile_completed=True,
        )
        return Response(public_profile(user))


class MomentsView(APIView):
    permission_classes = [IsAuthenticated, Onboarded]

    def get(self, request):
        from rest_framework.pagination import PageNumberPagination

        paginator = PageNumberPagination()
        moments = paginator.paginate_queryset(
            Moment.objects.filter(published=True).order_by("-created_at", "-id"), request
        )
        return paginator.get_paginated_response(
            [
                {
                    "id": str(moment.id),
                    "title": moment.title,
                    "caption": moment.caption,
                    "video_url": moment.video_url,
                }
                for moment in moments
            ]
        )


class AdminStatusView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request):
        return Response({"administrator": True, "admin_url": settings.BACKEND_URL + "/admin/"})


class GoogleStartView(PublicView):
    def post(self, request):
        data = validated(GoogleStartSerializer, request)
        check_browser(request, data["client"])
        return Response({"url": services.google_start(data)})


class GoogleCallbackView(PublicView):
    throttle_scope = None

    def invalid_request(self, request):
        # The callback is a return destination, not a sign-in entry point. Keep
        # machine callers' 400 response, but send browser visitors to app recovery.
        if request.accepted_renderer.media_type == "text/html":
            return AppRedirect(settings.OAUTH_APP_REDIRECTS["web"] + "?error=invalid_oauth_request")
        raise ValidationError(
            "This Google sign-in request is invalid or expired. Return to PIXEL and try again."
        )

    def get(self, request):
        drive_attempt = request.session.get("drive_oauth")
        if drive_attempt and secrets.compare_digest(
            drive_attempt.get("state", ""), request.query_params.get("state", "")
        ):
            from apps.community.drive_oauth import finish

            return finish(request)
        with transaction.atomic():
            attempt = (
                OAuthAttempt.objects.select_for_update()
                .filter(
                    state_digest=services.digest(request.query_params.get("state", "")),
                    used=False,
                    expires_at__gt=timezone.now(),
                )
                .first()
            )
            if not attempt:
                return self.invalid_request(request)
            attempt.used = True
            attempt.save(update_fields=["used"])
        redirect_uri = settings.OAUTH_APP_REDIRECTS[attempt.client]
        if request.query_params.get("error"):
            return AppRedirect(redirect_uri + "?error=cancelled")
        if not request.query_params.get("code"):
            return self.invalid_request(request)
        try:
            claims = services.google_claims(request.query_params.get("code", ""), attempt)
            with transaction.atomic():
                user = services.google_user(claims)
                services.accept_policies(
                    user,
                    {
                        "privacy_version": attempt.privacy_version,
                        "terms_version": attempt.terms_version,
                    },
                    "google_login",
                )
                ticket = secrets.token_urlsafe(32)
                OAuthTicket.objects.create(
                    user=user,
                    digest=services.digest(ticket),
                    app_challenge=attempt.app_challenge,
                    client=attempt.client,
                    expires_at=timezone.now() + timedelta(minutes=2),
                )
        except Exception:
            # No provider payloads, authorization codes or identity tokens in responses/logs.
            return AppRedirect(redirect_uri + "?error=college_identity_required")
        response = AppRedirect(redirect_uri + "?" + urlencode({"ticket": ticket}))
        response["Cache-Control"] = "no-store"
        return response


class AppRedirect(HttpResponseRedirect):
    allowed_schemes = ["http", "https", "pixelmobile"]


class GoogleExchangeView(PublicView):
    def post(self, request):
        data = validated(GoogleExchangeSerializer, request)
        check_browser(request, data["client"])
        with transaction.atomic():
            ticket = (
                OAuthTicket.objects.select_for_update()
                .select_related("user")
                .filter(
                    digest=services.digest(data["ticket"]),
                    used=False,
                    expires_at__gt=timezone.now(),
                    client=data["client"],
                )
                .first()
            )
            if not ticket or not secrets.compare_digest(
                ticket.app_challenge, services.challenge(data["verifier"])
            ):
                raise AuthenticationFailed(
                    "Google sign-in expired or belongs to another device. Try again."
                )
            ticket.used = True
            ticket.save(update_fields=["used"])
            if not ticket.user.is_active or not ticket.user.email_verified:
                raise AuthenticationFailed("This account is unavailable.")
            return services.create_session(ticket.user, data["client"])
