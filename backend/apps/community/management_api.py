"""Administrator API for the themed in-app publishing workspace."""

import re

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import IsAdministrator
from apps.accounts.models import AuditLog, User

from .drive import change_drive_file, upload_media
from .media import delivery_url, drive_session
from .models import Comment, DriveFolder, Event, EventSyncState, Publication, Reaction, Spotlight
from .synchronization import event_lock, synchronize


def folder_for(kind, event):
    if kind == "photo":
        if not event.drive_folder_id:
            raise ValidationError("Link the event’s Drive folder first.")
        return event.drive_folder_id
    folder = DriveFolder.objects.filter(kind=kind).first()
    if not folder:
        raise ValidationError("Configure the destination folder in Storage first.")
    return folder.folder_id


def check_event_folder(folder):
    if not re.fullmatch(r"[A-Za-z0-9_-]{5,200}", folder or ""):
        raise ValidationError(
            {
                "drive_folder_id": "Connect the existing Drive folder containing this event’s photographs."
            }
        )
    with drive_session() as session:
        response = session.get(
            f"https://www.googleapis.com/drive/v3/files/{folder}",
            params={"fields": "id,mimeType,trashed", "supportsAllDrives": "true"},
            timeout=20,
        )
        if (
            not response.ok
            or response.json().get("mimeType") != "application/vnd.google-apps.folder"
            or response.json().get("trashed")
        ):
            raise ValidationError(
                {
                    "drive_folder_id": "PIXEL cannot access this Drive folder. Check its link and account access."
                }
            )


def upload(file, folder, kind, existing_id=None):
    try:
        return upload_media(file, folder, kind, existing_id=existing_id)
    except (ValueError, RuntimeError) as exc:
        raise ValidationError(str(exc)) from exc


def check_publication_media(file_id, kind):
    with drive_session() as session:
        result = session.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            params={"fields": "mimeType,trashed", "supportsAllDrives": "true"},
            timeout=20,
        )
        if not result.ok or result.json().get("trashed"):
            raise ValidationError(
                "The original media is unavailable in Drive. Restore or replace it before publishing."
            )
        expected = "video/" if kind == "moment" else "image/"
        if not result.json().get("mimeType", "").startswith(expected):
            raise ValidationError("Choose an image for a post or a video for a moment.")


class StrictModelSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        readonly = {key for key in data if key in self.fields and self.fields[key].read_only}
        if unknown or readonly:
            raise ValidationError(
                {key: "This field cannot be changed." for key in unknown | readonly}
            )
        return super().to_internal_value(data)


class EventSerializer(StrictModelSerializer):
    sync = serializers.SerializerMethodField()
    cover_preview_url = serializers.CharField(read_only=True)
    cover_upload = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "tag",
            "description",
            "venue",
            "starts_at",
            "ends_at",
            "cover_url",
            "cover_drive_file_id",
            "drive_folder_id",
            "form_url",
            "published",
            "cover_upload",
            "cover_preview_url",
            "created_at",
            "sync",
        ]
        read_only_fields = ["id", "created_at"]

    def get_sync(self, instance):
        from .models import EventSyncState

        state = EventSyncState.objects.filter(event=instance).first()
        return (
            {
                "last_success_at": state.last_success_at,
                "error": state.last_error,
                "photos": state.photo_count,
            }
            if state
            else None
        )

    def validate(self, data):
        old = self.instance

        def value(key):
            return data.get(key, getattr(old, key, None))

        if value("ends_at") and value("starts_at") and value("ends_at") < value("starts_at"):
            raise ValidationError({"ends_at": "End must follow start."})
        if not (value("cover_url") or value("cover_drive_file_id") or data.get("cover_upload")):
            raise ValidationError({"cover_upload": "Choose an event cover photo."})
        folder = value("drive_folder_id")
        if not folder:
            raise ValidationError(
                {"drive_folder_id": "An event gallery must be connected to its Drive photo folder."}
            )
        from django.utils import timezone

        if value("ends_at") and value("ends_at") > timezone.now():
            raise ValidationError(
                {
                    "ends_at": "Gallery folders are for completed events. Use Spotlight for upcoming announcements."
                }
            )
        if not old or data.get("drive_folder_id", old.drive_folder_id) != old.drive_folder_id:
            check_event_folder(folder)
        return data

    def prepare(self, data):
        file = data.pop("cover_upload", None)
        folder = data.get("drive_folder_id", getattr(self.instance, "drive_folder_id", ""))
        if not folder:
            raise ValidationError({"drive_folder_id": "Connect the event’s Drive folder first."})
        if file:
            data["cover_drive_file_id"] = upload(file, folder, "photo")
            data["cover_url"] = ""
        return data

    def create(self, validated_data):
        return super().create(self.prepare(validated_data))

    def update(self, instance, validated_data):
        return super().update(instance, self.prepare(validated_data))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.cover_drive_file_id:
            data["cover_preview_url"] = delivery_url(
                instance, self.context["request"].user, "thumbnail"
            )
        return data


class PublicationSerializer(StrictModelSerializer):
    available = serializers.BooleanField(read_only=True)
    cover_preview_url = serializers.CharField(read_only=True)
    original_upload = serializers.FileField(write_only=True, required=False)
    original_uploads = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False, min_length=1, max_length=10
    )
    images = serializers.SerializerMethodField()
    cover_upload = serializers.FileField(write_only=True, required=False)
    event_title = serializers.CharField(source="event.title", read_only=True)

    class Meta:
        model = Publication
        fields = [
            "id",
            "kind",
            "event",
            "event_title",
            "title",
            "caption",
            "tag",
            "cover_url",
            "cover_drive_file_id",
            "preview_url",
            "original_url",
            "drive_file_id",
            "published",
            "available",
            "created_at",
            "original_upload",
            "original_uploads",
            "images",
            "cover_upload",
            "cover_preview_url",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        old = self.instance
        if old and data.get("kind", old.kind) != old.kind:
            raise ValidationError("A publication’s media type cannot be changed after creation.")

        def value(key):
            return data.get(key, getattr(old, key, None))

        if data.get("original_uploads"):
            if value("kind") != "post" or data.get("original_upload"):
                raise ValidationError(
                    "Multiple images are supported only for posts. Choose one upload method."
                )
            if sum(file.size for file in data["original_uploads"]) > 100 * 1024 * 1024:
                raise ValidationError("Keep the complete post below 100 MB.")
        if not (
            data.get("original_uploads")
            or data.get("original_upload")
            or value("drive_file_id")
            or value("original_url")
        ):
            raise ValidationError({"original_upload": "Choose the original image or video."})
        return data

    def prepare(self, data):
        originals = data.pop("original_uploads", None)
        from .image_dimensions import image_dimensions

        self._new_post_files = []
        original = data.pop("original_upload", None)
        cover = data.pop("cover_upload", None)
        event = data.get("event", self.instance.event if self.instance else None)
        kind = data.get("kind", self.instance.kind if self.instance else "post")
        if originals:
            uploaded = []
            sizes = {}
            folder = folder_for(kind, event)
            for file in originals:
                size = image_dimensions(file)
                file_id = upload(file, folder, "post")
                uploaded.append(file_id)
                sizes[file_id] = size
                self._new_post_files.append(file_id)
            data.update(
                post_media=uploaded,
                image_dimensions=sizes,
                drive_file_id=uploaded[0],
                available=True,
                original_url="",
                preview_url="",
            )
        elif original and kind == "post":
            data["post_media"] = []
        if original or cover:
            folder = folder_for(kind, event)
            if original:
                size = image_dimensions(original) if kind == "post" else {}
                data["drive_file_id"] = upload(
                    original,
                    folder,
                    kind,
                    existing_id=self.instance.drive_file_id
                    if self.instance and kind == "photo"
                    else None,
                )
                data["available"] = True
                if kind == "post":
                    self._new_post_files.append(data["drive_file_id"])
                    data["image_dimensions"] = {data["drive_file_id"]: size}
                if kind == "photo":
                    import uuid

                    data["source_revision"] = f"pixel-upload-{uuid.uuid4()}"
            if cover:
                data["cover_drive_file_id"] = upload(cover, folder, "photo")
                if kind == "post":
                    self._new_post_files.append(data["cover_drive_file_id"])
                data["cover_url"] = ""
        published = data.get("published", self.instance.published if self.instance else False)
        if kind in ["post", "moment"] and published:
            file_id = data.get(
                "drive_file_id", self.instance.drive_file_id if self.instance else ""
            )
            file_ids = (
                data.get("post_media", self.instance.post_media if self.instance else [])
                if kind == "post"
                else []
            )
            for media_id in file_ids or ([file_id] if file_id else []):
                check_publication_media(media_id, kind)
            data["available"] = True
        return data

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return super().create(
                    {**self.prepare(validated_data), "author": self.context["request"].user}
                )
        except Exception:
            self.cleanup_post_uploads()
            raise

    def cleanup_post_uploads(self):
        for file_id in getattr(self, "_new_post_files", []):
            try:
                change_drive_file(file_id, trashed=True)
            except Exception:
                # Preserve the original publishing failure if Drive is also down
                # during best-effort cleanup. The post remains unpublished.
                pass

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                return self.update_media(instance, validated_data)
        except Exception:
            self.cleanup_post_uploads()
            raise

    def update_media(self, instance, validated_data):
        validated_data = self.prepare(validated_data)
        if instance.kind == "photo" and instance.drive_file_id and "title" in validated_data:
            try:
                change_drive_file(instance.drive_file_id, name=validated_data["title"])
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.drive_file_id or instance.cover_drive_file_id:
            data["cover_preview_url"] = delivery_url(
                instance, self.context["request"].user, "thumbnail"
            )
        return data

    def get_images(self, instance):
        from .post_media import images

        return images(instance, self.context["request"].user)


class AdminContentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdministrator]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def perform_create(self, serializer):
        serializer.save()
        AuditLog.objects.create(
            actor=self.request.user, action=f"{serializer.Meta.model._meta.model_name}_created"
        )

    def perform_update(self, serializer):
        serializer.save()
        AuditLog.objects.create(
            actor=self.request.user, action=f"{serializer.Meta.model._meta.model_name}_updated"
        )

    def perform_destroy(self, instance):
        instance.published = False
        instance.save(update_fields=["published"])
        AuditLog.objects.create(
            actor=self.request.user, action=f"{instance._meta.model_name}_archived"
        )


class EventsViewSet(AdminContentViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.filter(spotlight=False).order_by("-created_at")


class PublicationsViewSet(AdminContentViewSet):
    serializer_class = PublicationSerializer
    queryset = Publication.objects.select_related("event", "author").order_by("-created_at", "-id")

    def perform_create(self, serializer):
        from contextlib import nullcontext

        data = serializer.validated_data
        with event_lock(data["event"]) if data.get("kind") == "photo" else nullcontext():
            super().perform_create(serializer)

    def perform_update(self, serializer):
        from contextlib import ExitStack

        instance = serializer.instance
        with ExitStack() as locks:
            if instance.kind == "photo":
                target = serializer.validated_data.get("event", instance.event)
                for event in sorted({instance.event, target}, key=lambda e: str(e.pk)):
                    locks.enter_context(event_lock(event))
                if target != instance.event and instance.drive_file_id:
                    from .drive import move_drive_file

                    try:
                        move_drive_file(
                            instance.drive_file_id,
                            instance.event.drive_folder_id,
                            target.drive_folder_id,
                        )
                    except ValueError as exc:
                        raise ValidationError(str(exc)) from exc
            super().perform_update(serializer)

    def perform_destroy(self, instance):
        if instance.kind != "photo" or not instance.drive_file_id:
            return super().perform_destroy(instance)
        with event_lock(instance.event):
            try:
                change_drive_file(instance.drive_file_id, trashed=True)
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
            instance.available = False
            instance.save(update_fields=["available"])
            AuditLog.objects.create(actor=self.request.user, action="event_photo_trashed")

    def get_queryset(self):
        items = super().get_queryset()
        for field in ["kind", "event_id"]:
            if self.request.query_params.get(field):
                items = items.filter(**{field: self.request.query_params[field]})
        return items


class DashboardView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request):
        return Response(
            {
                "events": Event.objects.filter(spotlight=False).count(),
                "posts": Publication.objects.filter(kind="post").count(),
                "moments": Publication.objects.filter(kind="moment").count(),
                "photos": Publication.objects.filter(kind="photo").count(),
                "members": User.objects.filter(is_active=True).count(),
                "comments": Comment.objects.count(),
                "spotlights": Spotlight.objects.count(),
                "published": Publication.objects.filter(
                    kind__in=["post", "moment"], published=True, available=True
                ).count(),
                "drafts": Publication.objects.filter(
                    kind__in=["post", "moment"], published=False
                ).count(),
                "unavailable": Publication.objects.filter(published=True, available=False).count(),
                "likes": Reaction.objects.filter(action="like").count(),
                "saves": Reaction.objects.filter(action="save").count(),
                "upcoming": Spotlight.objects.filter(
                    published=True, ends_at__gte=timezone.now()
                ).count(),
                "sync": {
                    "errors": EventSyncState.objects.filter(event__spotlight=False)
                    .exclude(last_error="")
                    .count(),
                    "last_success_at": EventSyncState.objects.filter(
                        event__spotlight=False
                    ).aggregate(latest=Max("last_success_at"))["latest"],
                },
                "recent": list(
                    Publication.objects.filter(kind__in=["post", "moment"])
                    .order_by("-created_at", "-id")
                    .values("id", "title", "kind", "published", "available", "created_at")[:5]
                ),
                "drive_connected": (settings.BASE_DIR / ".local" / "drive-oauth.json").exists(),
            }
        )


class SyncView(APIView):
    permission_classes = [IsAdministrator]

    def post(self, request, pk):
        from django.shortcuts import get_object_or_404

        event = get_object_or_404(Event, pk=pk)
        try:
            count = synchronize(event, request.user)
        except Exception as exc:
            raise ValidationError(
                "Could not sync this folder. Check its ID and Drive access, then retry."
            ) from exc
        AuditLog.objects.create(actor=request.user, action="event_gallery_synced")
        return Response({"photos": count})


class GalleryUploadView(APIView):
    permission_classes = [IsAdministrator]

    def post(self, request, pk):
        from django.shortcuts import get_object_or_404

        event = get_object_or_404(Event, pk=pk)
        files = request.FILES.getlist("files")
        if not files or len(files) > 20:
            raise ValidationError("Choose between 1 and 20 photographs per upload.")
        if sum(file.size for file in files) > 500 * 1024 * 1024:
            raise ValidationError("Keep each batch below 500 MB.")
        count, failed = 0, []
        with event_lock(event):
            for file in files:
                try:
                    file_id = upload(file, folder_for("photo", event), "photo")
                    Publication.objects.create(
                        kind="photo",
                        author=request.user,
                        event=event,
                        title=file.name[:160],
                        tag=event.tag,
                        drive_file_id=file_id,
                        published=True,
                    )
                    count += 1
                except (ValueError, ValidationError):
                    failed.append(file.name)
        AuditLog.objects.create(actor=request.user, action="event_photos_uploaded")
        return Response({"uploaded": count, "failed": failed}, status=201)


class MemberSerializer(StrictModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "display_name",
            "role",
            "is_active",
            "email_verified",
            "department",
            "year",
        ]
        read_only_fields = [
            "id",
            "email",
            "username",
            "email_verified",
            "display_name",
            "department",
            "year",
        ]

    def validate(self, data):
        if self.instance.email == settings.MAIN_ADMIN_EMAIL and (
            data.get("role", self.instance.role) != "Administrator"
            or data.get("is_active") is False
        ):
            raise ValidationError("The main Pixel administrator must remain active.")
        if self.instance == self.context["request"].user and (
            data.get("is_active") is False
            or data.get("role", self.instance.role) != "Administrator"
        ):
            raise ValidationError("You cannot remove your own administrator access.")
        return data

    def update(self, instance, validated_data):
        if "role" in validated_data:
            instance.is_staff = validated_data["role"] == "Administrator"
            if not instance.is_staff:
                instance.is_superuser = False
        return super().update(instance, validated_data)


class MembersViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdministrator]
    serializer_class = MemberSerializer
    queryset = User.objects.order_by("username", "email")

    def get_queryset(self):
        items = super().get_queryset()
        query = self.request.query_params.get("q", "")[:80]
        return (
            items.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(display_name__icontains=query)
            )
            if query
            else items
        )

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        AuditLog.objects.create(actor=request.user, action="member_access_updated")
        return Response(serializer.data)


class ModerationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="author.username")
    publication_title = serializers.CharField(source="publication.title")

    class Meta:
        model = Comment
        fields = [
            "id",
            "username",
            "text",
            "publication",
            "parent",
            "publication_title",
            "created_at",
        ]


class ModerationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdministrator]
    serializer_class = ModerationSerializer
    queryset = Comment.objects.select_related("author", "publication").order_by(
        "-created_at", "-id"
    )

    def get_queryset(self):
        items = super().get_queryset()
        publication = self.request.query_params.get("publication")
        if publication:
            from django.core.exceptions import ValidationError as DjangoValidationError

            try:
                items = items.filter(publication_id=publication)
            except DjangoValidationError as exc:
                raise ValidationError("Choose a valid post.") from exc
        query = self.request.query_params.get("q", "").strip()[:300]
        return items.filter(text__icontains=query) if query else items

    @action(detail=False, methods=["get"])
    def groups(self, request):
        items = (
            Publication.objects.annotate(
                comment_count=Count("comments"), latest_comment_at=Max("comments__created_at")
            )
            .filter(comment_count__gt=0)
            .order_by("-latest_comment_at", "-id")
        )
        page = self.paginate_queryset(items)
        data = [
            {
                "id": str(item.pk),
                "title": item.title,
                "kind": item.kind,
                "comment_count": item.comment_count,
                "latest_comment_at": item.latest_comment_at,
            }
            for item in page
            if page is not None
        ]
        return self.get_paginated_response(data)

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        AuditLog.objects.create(actor=request.user, action="comment_moderated")
        return Response(status=204)


class StorageView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request):
        return Response(
            {
                "connected": (settings.BASE_DIR / ".local" / "drive-oauth.json").exists(),
                "folders": list(DriveFolder.objects.values("kind", "folder_id")),
                "connect_url": settings.BACKEND_URL + "/admin/connect-drive/",
            }
        )

    def patch(self, request):
        kind = request.data.get("kind")
        folder = request.data.get("folder_id", "")
        match = re.search(r"/folders/([A-Za-z0-9_-]+)", folder)
        if match:
            folder = match.group(1)
        if kind not in ["post", "moment"] or not re.fullmatch(r"[A-Za-z0-9_-]{5,200}", folder):
            raise ValidationError(
                "Choose Posts or Moments and enter a valid Drive folder link or ID."
            )
        DriveFolder.objects.update_or_create(kind=kind, defaults={"folder_id": folder})
        AuditLog.objects.create(actor=request.user, action="drive_folder_updated")
        return self.get(request)
