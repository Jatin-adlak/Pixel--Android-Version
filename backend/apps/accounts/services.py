import base64
import hashlib
import logging
import secrets
from datetime import timedelta
from ipaddress import ip_address
from urllib.parse import urlencode, urlsplit

import httpx
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from rest_framework.exceptions import APIException, AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    AuditLog,
    AuthSession,
    EmailVerification,
    GoogleIdentity,
    OAuthAttempt,
    PolicyAcceptance,
    User,
)
from .serializers import user_data
from .validators import college_email

logger = logging.getLogger(__name__)
GOOGLE_CLOCK_SKEW_SECONDS = 10


class GoogleSignInUnavailable(APIException):
    status_code = 503
    default_detail = (
        "PIXEL couldn’t finish signing in with Google. Return to PIXEL and try again, "
        "or use your college email and PIXEL password."
    )


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def challenge(value):
    return base64.urlsafe_b64encode(hashlib.sha256(value.encode()).digest()).decode().rstrip("=")


def accept_policies(user, data, action):
    PolicyAcceptance.objects.create(
        user=user,
        privacy_version=data["privacy_version"],
        terms_version=data["terms_version"],
        action=action,
    )


def send_verification(user):
    token = secrets.token_urlsafe(32)
    with transaction.atomic():
        EmailVerification.objects.filter(user=user, used=False).update(used=True)
        EmailVerification.objects.create(
            user=user, digest=digest(token), expires_at=timezone.now() + timedelta(minutes=30)
        )
    link = settings.FRONTEND_URL + "/auth/verify?" + urlencode({"token": token})
    try:
        send_mail(
            "Verify your PIXEL college account",
            f"Verify your college email and choose your password:\n{link}\n\nThis link expires in 30 minutes. If you did not request an account, ignore it.",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
    except Exception:
        # Never log tokens, message bodies or SMTP credentials.
        logger.warning("Account verification delivery failed; resend is available.")


def make_refresh(user, session):
    token = RefreshToken.for_user(user)
    token["sid"] = str(session.id)
    session.refresh_jti = token["jti"]
    session.save(update_fields=["refresh_jti"])
    return token


def token_response(user, token, client):
    payload = {"access": str(token.access_token), "user": user_data(user)}
    if client == "native":
        payload["refresh"] = str(token)
    response = Response(payload)
    response["Cache-Control"] = "no-store"
    if client == "web":
        response.set_cookie(
            "pixel_refresh",
            str(token),
            max_age=7 * 86400,
            httponly=True,
            secure=settings.REFRESH_COOKIE_SECURE,
            samesite="Lax",
            path="/api/v1/auth/",
        )
    return response


def create_session(user, client):
    session = AuthSession.objects.create(
        user=user, refresh_jti="", expires_at=timezone.now() + timedelta(days=7)
    )
    token = make_refresh(user, session)
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
    AuditLog.objects.create(actor=user, action="login")
    return token_response(user, token, client)


def google_start(data):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise ValidationError(
            "Google sign-in is not configured yet. Use your college email and password."
        )
    callback = urlsplit(settings.GOOGLE_REDIRECT_URI)
    hostname = callback.hostname or ""
    try:
        address = ip_address(hostname)
    except ValueError:
        address = None
    loopback = hostname == "localhost" or (address is not None and address.is_loopback)
    if not loopback and (callback.scheme != "https" or address is not None or not hostname):
        raise ValidationError(
            "Google sign-in is unavailable at this address. Use your college email and "
            "PIXEL password, or open PIXEL at its configured HTTPS address."
        )
    state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
    OAuthAttempt.objects.create(
        state_digest=digest(state),
        nonce=nonce,
        provider_verifier=verifier,
        app_challenge=data["challenge"],
        client=data["client"],
        privacy_version=data["privacy_version"],
        terms_version=data["terms_version"],
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge(verifier),
            "code_challenge_method": "S256",
            "hd": settings.COLLEGE_DOMAIN,
            "prompt": "select_account",
        }
    )


def google_claims(code, attempt):
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                    "code_verifier": attempt.provider_verifier,
                },
            )
            response.raise_for_status()
            raw_token = response.json().get("id_token", "")
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Google sign-in failed during the token exchange (HTTP %s)", exc.response.status_code
        )
        raise GoogleSignInUnavailable() from exc
    except (httpx.RequestError, ValueError, AttributeError) as exc:
        logger.warning("Google sign-in could not read the token response (%s)", type(exc).__name__)
        raise GoogleSignInUnavailable() from exc
    try:
        claims = id_token.verify_oauth2_token(
            raw_token,
            GoogleRequest(),
            settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=GOOGLE_CLOCK_SKEW_SECONDS,
        )
    except (GoogleAuthError, ValueError) as exc:
        reason = type(exc).__name__
        if str(exc).startswith("Token used too early"):
            reason = "clock ahead of PIXEL"
        elif str(exc).startswith("Token expired"):
            reason = "token expired"
        logger.warning("Google sign-in could not validate the ID token (%s)", reason)
        raise GoogleSignInUnavailable() from exc
    if claims.get("nonce") != attempt.nonce:
        raise AuthenticationFailed(
            "Start a fresh Google sign-in from PIXEL.", code="invalid_oauth_request"
        )
    if claims.get("email_verified") is not True or claims.get("hd") != settings.COLLEGE_DOMAIN:
        raise AuthenticationFailed(
            "A verified @sait.ac.in Google Workspace account is required.",
            code="college_identity_required",
        )
    return claims


def google_user(claims):
    try:
        email = college_email(claims.get("email", ""))
    except Exception as exc:
        raise AuthenticationFailed("Use your @sait.ac.in Google account.") from exc
    subject = claims.get("sub")
    if not subject:
        raise AuthenticationFailed("Google identity could not be verified.")
    identity = GoogleIdentity.objects.select_related("user").filter(subject=subject).first()
    if identity:
        user = identity.user
        if user.email != email:
            raise AuthenticationFailed(
                "Your college identity has changed. Contact the administrator."
            )
    else:
        user = User.objects.select_for_update().filter(email=email).first()
        if not user:
            if email == settings.MAIN_ADMIN_EMAIL:
                raise AuthenticationFailed(
                    "This administrator account must be provisioned locally first."
                )
            user = User.objects.create_user(email=email, email_verified=True)
        elif not user.email_verified:
            # Discard any password set by a party that had not verified this mailbox.
            user.set_unusable_password()
            user.email_verified = True
            user.save(update_fields=["password", "email_verified"])
            EmailVerification.objects.filter(user=user).update(used=True)
        if GoogleIdentity.objects.filter(user=user).exists():
            raise AuthenticationFailed("A different Google identity is already linked.")
        GoogleIdentity.objects.create(user=user, subject=subject)
    if not user.is_active or not user.email_verified:
        raise AuthenticationFailed("This account is unavailable. Contact the administrator.")
    return user
