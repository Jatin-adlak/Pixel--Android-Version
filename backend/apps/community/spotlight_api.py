"""Upcoming announcements are separate from completed-event photo folders."""

from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .management_api import AdminContentViewSet, StrictModelSerializer, upload
from .media import delivery_url, drive_session
from .models import DriveFolder, Spotlight
from .queries import MemberView, event_data, page


def cover_folder():
    folder = DriveFolder.objects.filter(kind="spotlight").first()
    if folder:
        return folder.folder_id
    parent = DriveFolder.objects.filter(kind="post").first()
    if not parent:
        raise ValidationError("Configure Pixel storage first.")
    with drive_session() as session:
        response = session.post(
            "https://www.googleapis.com/drive/v3/files",
            json={
                "name": "Spotlight Covers",
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent.folder_id],
            },
            timeout=20,
        )
        if not response.ok:
            raise ValidationError(
                "Could not prepare announcement cover storage. Check Drive access."
            )
        folder, _ = DriveFolder.objects.get_or_create(
            kind="spotlight", defaults={"folder_id": response.json()["id"]}
        )
        return folder.folder_id


class SpotlightSerializer(StrictModelSerializer):
    cover_upload = serializers.FileField(write_only=True, required=False)
    cover_preview_url = serializers.CharField(read_only=True)

    class Meta:
        model = Spotlight
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
            "form_url",
            "published",
            "cover_upload",
            "cover_preview_url",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        def value(key):
            return data.get(key, getattr(self.instance, key, None))

        if value("starts_at") and value("ends_at") and value("ends_at") < value("starts_at"):
            raise ValidationError({"ends_at": "End must follow start."})
        if not (value("cover_url") or value("cover_drive_file_id") or data.get("cover_upload")):
            raise ValidationError({"cover_upload": "Choose an announcement cover photo."})
        if value("published") and value("ends_at") and value("ends_at") < timezone.now():
            raise ValidationError(
                {"ends_at": "Choose upcoming or ongoing dates for a published announcement."}
            )
        return data

    def prepare(self, data):
        file = data.pop("cover_upload", None)
        if file:
            data["cover_drive_file_id"] = upload(file, cover_folder(), "photo")
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


class SpotlightViewSet(AdminContentViewSet):
    serializer_class = SpotlightSerializer
    queryset = Spotlight.objects.order_by("starts_at", "id")


class SpotlightListView(MemberView):
    def get(self, request):
        items = Spotlight.objects.filter(published=True, ends_at__gte=timezone.now()).order_by(
            "starts_at", "id"
        )
        return page(request, items, lambda item: event_data(item, request.user))


class SpotlightDetailView(MemberView):
    def get(self, request, pk):
        from django.shortcuts import get_object_or_404

        item = get_object_or_404(Spotlight, pk=pk, published=True, ends_at__gte=timezone.now())
        return Response(event_data(item, request.user))
