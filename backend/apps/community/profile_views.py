from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.models import User

from .models import Follow, ProfileImage
from .queries import MemberView, content, ensure_pixel, identity, page, profile_data, visible


class MemberProfileView(MemberView):
    def get(self, request, username):
        user = get_object_or_404(
            User,
            username=username.lower(),
            is_active=True,
            email_verified=True,
            profile_completed=True,
        )
        return Response(profile_data(user, request.user))


class SavedView(MemberView):
    def get(self, request, username):
        user = get_object_or_404(
            User,
            username=username.lower(),
            is_active=True,
            email_verified=True,
            profile_completed=True,
        )
        kind = request.query_params.get("kind", "post")
        if kind not in ["post", "moment", "photo"]:
            raise ValidationError("Unknown saved section.")
        if kind == "photo" and not profile_data(user, request.user)["can_see_photos"]:
            raise PermissionDenied(
                "Follow this person and wait for acceptance to see saved pictures."
            )
        items = visible(request.user).filter(
            kind=kind, reactions__user=user, reactions__action="save"
        )
        return page(request, items, lambda item: content(item, request.user))


class FollowView(MemberView):
    def put(self, request, username):
        user = get_object_or_404(
            User,
            username=username.lower(),
            is_active=True,
            email_verified=True,
            profile_completed=True,
        )
        if user == request.user:
            raise ValidationError("You cannot follow yourself.")
        ensure_pixel(request.user)
        Follow.objects.get_or_create(follower=request.user, target=user)
        return Response(profile_data(user, request.user))

    def delete(self, request, username):
        user = get_object_or_404(User, username=username.lower())
        ensure_pixel(request.user)
        relation = Follow.objects.filter(follower=request.user, target=user).first()
        if relation and relation.mandatory:
            raise ValidationError("Your Pixel follow is required.")
        if relation:
            relation.delete()
        return Response(profile_data(user, request.user))


class ConnectionsView(MemberView):
    def get(self, request):
        ensure_pixel(request.user)
        kind = request.query_params.get("kind", "requests")
        if kind not in ["requests", "followers", "following"]:
            raise ValidationError("Unknown connection section.")
        items = (
            Follow.objects.filter(follower=request.user, accepted=True)
            if kind == "following"
            else Follow.objects.filter(target=request.user, accepted=kind == "followers")
        )
        return page(
            request,
            items.select_related("follower", "target").order_by("-created_at"),
            lambda item: {
                "id": item.id,
                "mandatory": item.mandatory,
                "user": identity(item.target if kind == "following" else item.follower),
            },
        )


class ConnectionView(MemberView):
    @transaction.atomic
    def put(self, request, pk):
        item = get_object_or_404(Follow.objects.select_for_update(), pk=pk, target=request.user)
        item.accepted = True
        item.save(update_fields=["accepted"])
        return Response({"accepted": True})

    def delete(self, request, pk):
        item = get_object_or_404(Follow, pk=pk)
        if request.user not in [item.target, item.follower]:
            raise PermissionDenied()
        if item.mandatory:
            raise ValidationError("The Pixel follow cannot be removed.")
        item.delete()
        return Response(status=204)


class AvatarView(MemberView):
    def post(self, request):
        from .drive import upload_media
        from .media import delivery_url, drive_session
        from .models import DriveFolder

        upload = request.FILES.get("file")
        if not upload or upload.size > 5 * 1024 * 1024:
            raise ValidationError("Choose a JPEG, PNG or WebP image up to 5 MB.")
        folder = DriveFolder.objects.filter(kind="avatar").first()
        if not folder:
            parent = get_object_or_404(DriveFolder, kind="post")
            from django.conf import settings

            if not (settings.BASE_DIR / ".local" / "drive-oauth.json").exists():
                raise ValidationError(
                    "Profile picture uploads are waiting for the administrator to connect Drive."
                )
            with drive_session() as session:
                response = session.post(
                    "https://www.googleapis.com/drive/v3/files",
                    json={
                        "name": "Profile Pictures",
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": [parent.folder_id],
                    },
                    timeout=20,
                )
                if not response.ok:
                    raise ValidationError("Profile picture storage is temporarily unavailable.")
                folder, _ = DriveFolder.objects.get_or_create(
                    kind="avatar", defaults={"folder_id": response.json()["id"]}
                )
        try:
            file_id = upload_media(upload, folder.folder_id, "photo")
        except (ValueError, RuntimeError) as exc:
            raise ValidationError(str(exc)) from exc
        image, _ = ProfileImage.objects.update_or_create(
            user=request.user, defaults={"url": "", "drive_file_id": file_id}
        )
        return Response({"avatar_url": delivery_url(image, request.user, "thumbnail")})

    def put(self, request):
        from rest_framework import serializers

        field = serializers.URLField(max_length=2000)
        url = field.run_validation(request.data.get("url"))
        if not url.startswith("https://"):
            raise ValidationError("Use an HTTPS image URL.")
        ProfileImage.objects.update_or_create(
            user=request.user, defaults={"url": url, "drive_file_id": ""}
        )
        return Response({"avatar_url": url})
