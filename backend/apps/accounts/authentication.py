from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import AuthSession, User
from .validators import college_email


class SessionJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        try:
            college_email(user.email)
        except Exception as exc:
            raise AuthenticationFailed("College membership is required.") from exc
        if (
            not user.email_verified
            or not AuthSession.objects.filter(
                id=validated_token.get("sid"),
                user=user,
                revoked=False,
                expires_at__gt=timezone.now(),
            ).exists()
        ):
            raise AuthenticationFailed("Your session has expired. Please sign in again.")
        return user


class IsAdministrator(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == User.Role.ADMINISTRATOR
            and request.user.is_staff
        )


class Onboarded(BasePermission):
    message = "Finish choosing your username and profile first."

    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated
            and request.user.username
            and request.user.profile_completed
        )
