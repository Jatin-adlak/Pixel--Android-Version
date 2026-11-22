import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

RESERVED = {
    "admin",
    "administrator",
    "pixel",
    "pixel.club",
    "support",
    "help",
    "api",
    "auth",
    "login",
    "signup",
    "settings",
    "privacy",
    "terms",
    "root",
    "moderator",
    "official",
}


def college_email(value):
    value = value.strip().lower()
    validate_email(value)
    if value.rsplit("@", 1)[-1] != "sait.ac.in":
        raise ValidationError("Use your @sait.ac.in college email address.")
    return value


def validate_username(value, allow_reserved=False):
    if not re.fullmatch(r"[a-z0-9._]{3,30}", value):
        raise ValidationError("Use 3–30 lowercase letters, numbers, periods or underscores.")
    if value.startswith(".") or value.endswith(".") or ".." in value:
        raise ValidationError("Periods cannot be first, last or consecutive.")
    if not re.search(r"[a-z]", value):
        raise ValidationError("Include at least one letter.")
    if value in RESERVED and not allow_reserved:
        raise ValidationError("This username is reserved.")
