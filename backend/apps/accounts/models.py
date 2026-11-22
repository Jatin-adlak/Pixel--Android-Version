import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower

from .validators import college_email, validate_username


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        user = self.model(email=college_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.update(
            role=User.Role.ADMINISTRATOR, is_staff=True, is_superuser=True, email_verified=True
        )
        return self.create_user(email, password, **extra)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMINISTRATOR = "Administrator"
        FACULTY = "Faculty"
        STUDENT = "Student"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=30, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    email_verified = models.BooleanField(default=False)
    display_name = models.CharField(max_length=80, blank=True)
    department = models.CharField(max_length=80, blank=True)
    year = models.CharField(max_length=30, blank=True)
    bio = models.CharField(max_length=150, blank=True)
    profile_completed = models.BooleanField(default=False)
    tour_completed = models.BooleanField(default=False)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="unique_email_casefold"),
            models.UniqueConstraint(Lower("username"), name="unique_username_casefold"),
            models.CheckConstraint(
                condition=models.Q(role__in=["Administrator", "Faculty", "Student"]),
                name="three_roles_only",
            ),
            models.CheckConstraint(
                condition=models.Q(is_staff=False, is_superuser=False)
                | models.Q(role="Administrator"),
                name="admin_flags_require_role",
            ),
        ]

    def clean(self):
        super().clean()
        self.email = college_email(self.email)
        if self.username:
            self.username = self.username.lower()
            validate_username(self.username, allow_reserved=self.role == self.Role.ADMINISTRATOR)
        if self.role != self.Role.ADMINISTRATOR and (self.is_staff or self.is_superuser):
            raise ValidationError("Only Administrators can have administrative flags.")

    def save(self, *args, **kwargs):
        self.email = college_email(self.email)
        if self.username:
            self.username = self.username.lower()
        else:
            self.username = None
        if self.role != self.Role.ADMINISTRATOR:
            self.is_staff = self.is_superuser = False
        super().save(*args, **kwargs)


class AuthSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    refresh_jti = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class EmailVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class PolicyAcceptance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    privacy_version = models.CharField(max_length=30)
    terms_version = models.CharField(max_length=30)
    action = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)


class AuditLog(models.Model):
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=60)
    created_at = models.DateTimeField(auto_now_add=True)


class GoogleIdentity(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=255, unique=True)


class OAuthAttempt(models.Model):
    state_digest = models.CharField(max_length=64, unique=True)
    nonce = models.CharField(max_length=100)
    provider_verifier = models.CharField(max_length=100)
    app_challenge = models.CharField(max_length=100)
    client = models.CharField(max_length=10)
    privacy_version = models.CharField(max_length=30)
    terms_version = models.CharField(max_length=30)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)


class OAuthTicket(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    digest = models.CharField(max_length=64, unique=True)
    app_challenge = models.CharField(max_length=100)
    client = models.CharField(max_length=10)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)


class Moment(models.Model):
    title = models.CharField(max_length=100)
    caption = models.CharField(max_length=300, blank=True)
    video_url = models.URLField(max_length=1000)
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        from urllib.parse import urlparse

        if urlparse(self.video_url).scheme != "https":
            raise ValidationError({"video_url": "Use an HTTPS video delivery URL."})

    def __str__(self):
        return self.title
