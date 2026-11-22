from collections.abc import Mapping

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User
from .validators import college_email, validate_username


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            raise serializers.ValidationError({"non_field_errors": ["Expected a JSON object."]})
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {key: "This field is not accepted." for key in unknown}
            )
        return super().to_internal_value(data)


class PolicySerializer(StrictSerializer):
    privacy_accepted = serializers.BooleanField()
    terms_accepted = serializers.BooleanField()
    privacy_version = serializers.CharField(max_length=30)
    terms_version = serializers.CharField(max_length=30)

    def validate(self, attrs):
        if not attrs["privacy_accepted"] or not attrs["terms_accepted"]:
            raise serializers.ValidationError(
                "Read and accept the privacy policy and campus terms."
            )
        if (
            attrs["privacy_version"] != settings.PRIVACY_VERSION
            or attrs["terms_version"] != settings.TERMS_VERSION
        ):
            raise serializers.ValidationError(
                "The policies have changed. Reload and review them again."
            )
        return attrs


class RegisterSerializer(PolicySerializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(
        min_length=12, max_length=128, trim_whitespace=False, write_only=True
    )

    def validate_email(self, value):
        try:
            return college_email(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    def validate(self, attrs):
        attrs = super().validate(attrs)
        try:
            validate_password(attrs["password"], User(email=attrs["email"]))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs


class LoginSerializer(PolicySerializer):
    identifier = serializers.CharField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    client = serializers.ChoiceField(choices=["web", "native"])


class VerifySerializer(StrictSerializer):
    token = serializers.CharField(max_length=128, write_only=True)
    password = serializers.CharField(
        min_length=12, max_length=128, trim_whitespace=False, write_only=True
    )


class RefreshSerializer(StrictSerializer):
    client = serializers.ChoiceField(choices=["web", "native"], default="web")
    refresh = serializers.CharField(max_length=4096, required=False, write_only=True)


class EmailSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)

    def validate_email(self, value):
        try:
            return college_email(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc


class UsernameSerializer(StrictSerializer):
    username = serializers.CharField(max_length=30)

    def validate_username(self, value):
        value = value.lower().strip()
        try:
            validate_username(
                value, allow_reserved=self.context["request"].user.role == User.Role.ADMINISTRATOR
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value


class ProfileSerializer(StrictSerializer):
    display_name = serializers.CharField(max_length=80)
    department = serializers.CharField(max_length=80)
    year = serializers.CharField(max_length=30, allow_blank=True, default="")
    bio = serializers.CharField(max_length=150, allow_blank=True, default="")


class GoogleStartSerializer(PolicySerializer):
    client = serializers.ChoiceField(choices=["web", "native"])
    challenge = serializers.RegexField(r"^[A-Za-z0-9_-]{43}$", max_length=43)


class GoogleExchangeSerializer(StrictSerializer):
    ticket = serializers.CharField(max_length=128, write_only=True)
    verifier = serializers.RegexField(r"^[A-Za-z0-9._~-]{43,128}$", max_length=128, write_only=True)
    client = serializers.ChoiceField(choices=["web", "native"])


def user_data(user):
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "display_name": user.display_name,
        "department": user.department,
        "year": user.year,
        "bio": user.bio,
        "profile_completed": user.profile_completed,
        "tour_completed": user.tour_completed,
        "email_verified": user.email_verified,
        "onboarding_step": "username"
        if not user.username
        else "profile"
        if not user.profile_completed
        else "tour"
        if not user.tour_completed
        else "complete",
    }
