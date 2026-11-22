import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=160)
    tag = models.CharField(max_length=40)
    description = models.TextField()
    venue = models.CharField(max_length=200)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    cover_url = models.URLField(max_length=2000, blank=True)
    cover_drive_file_id = models.CharField(max_length=200, blank=True)
    drive_folder_id = models.CharField(max_length=200)
    form_url = models.URLField(max_length=2000, blank=True)
    published = models.BooleanField(default=False)
    spotlight = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if not self.drive_folder_id:
            raise ValidationError(
                {"drive_folder_id": "Connect the completed event’s Drive photo folder."}
            )
        if not self.cover_url and not self.cover_drive_file_id:
            raise ValidationError("Upload a cover photo or provide its HTTPS URL.")
        if self.starts_at and self.ends_at and self.ends_at < self.starts_at:
            raise ValidationError({"ends_at": "End must follow start."})

    def __str__(self):
        return self.title


class Spotlight(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=160)
    tag = models.CharField(max_length=40)
    description = models.TextField()
    venue = models.CharField(max_length=200)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    cover_url = models.URLField(max_length=2000, blank=True)
    cover_drive_file_id = models.CharField(max_length=200, blank=True)
    form_url = models.URLField(max_length=2000, blank=True)
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if not self.cover_url and not self.cover_drive_file_id:
            raise ValidationError("Choose an announcement cover photo.")
        if self.starts_at and self.ends_at and self.ends_at < self.starts_at:
            raise ValidationError({"ends_at": "End must follow start."})

    def __str__(self):
        return self.title


class Publication(models.Model):
    class Kind(models.TextChoices):
        POST = "post", "Post"
        PHOTO = "photo", "Gallery photograph"
        MOMENT = "moment", "Moment"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="publications")
    title = models.CharField(max_length=160)
    caption = models.TextField(blank=True, max_length=4000)
    tag = models.CharField(max_length=40)
    cover_url = models.URLField(max_length=2000, blank=True)
    cover_drive_file_id = models.CharField(max_length=200, blank=True)
    preview_url = models.URLField(max_length=2000, blank=True)
    original_url = models.URLField(max_length=2000, blank=True)
    drive_file_id = models.CharField(max_length=200, blank=True, db_index=True)
    # Ordered, server-created Drive IDs for post carousels. Legacy single-media
    # posts continue to use drive_file_id until explicitly replaced.
    post_media = models.JSONField(default=list, blank=True, editable=False)
    image_dimensions = models.JSONField(default=dict, blank=True, editable=False)
    source_revision = models.CharField(max_length=200, blank=True)
    available = models.BooleanField(default=True)
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "kind", "drive_file_id"],
                condition=~models.Q(drive_file_id=""),
                name="unique_event_drive_media",
            )
        ]

    def clean(self):
        if self.author_id and self.author.role != "Administrator":
            raise ValidationError({"author": "Only an administrator may publish."})
        if not self.original_url and not self.drive_file_id:
            raise ValidationError("Choose an original URL or Drive file ID.")
        if not self.drive_file_id and (
            not (self.cover_url or self.cover_drive_file_id) or not self.preview_url
        ):
            raise ValidationError("Non-Drive content requires cover and preview URLs.")

    def __str__(self):
        return f"{self.kind}: {self.title}"


class Reaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name="reactions")
    action = models.CharField(max_length=10, choices=[("like", "Like"), ("save", "Save")])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "publication", "action"], name="unique_publication_reaction"
            )
        ]


class Comment(models.Model):
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )
    text = models.CharField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class CommentLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="likes")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "comment"], name="unique_comment_like")
        ]


class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="outgoing_follows"
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="incoming_follows"
    )
    accepted = models.BooleanField(default=False)
    mandatory = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["follower", "target"], name="unique_follow"),
            models.CheckConstraint(
                condition=~models.Q(follower=models.F("target")), name="no_self_follow"
            ),
        ]


class ProfileImage(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile_image"
    )
    url = models.URLField(max_length=2000, blank=True)
    drive_file_id = models.CharField(max_length=200, blank=True)


class DriveFolder(models.Model):
    kind = models.CharField(
        max_length=10,
        choices=[
            ("post", "Posts"),
            ("moment", "Moments"),
            ("avatar", "Profile pictures"),
            ("spotlight", "Announcement covers"),
        ],
        unique=True,
    )
    folder_id = models.CharField(max_length=200)

    def __str__(self):
        return self.get_kind_display()


class EventSyncState(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="sync_state")
    next_run_at = models.DateTimeField()
    lease_until = models.DateTimeField(null=True, blank=True)
    lease_token = models.UUIDField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=300, blank=True)
    failures = models.PositiveIntegerField(default=0)
    photo_count = models.PositiveIntegerField(default=0)
