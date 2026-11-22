"""Private Drive transport. Originals never enter database columns or public storage."""

import os
import re

from django.conf import settings
from django.core import signing
from django.http import HttpResponseRedirect, StreamingHttpResponse
from google.auth.transport.requests import AuthorizedSession
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User

from .models import Event, ProfileImage, Publication, Spotlight
from .views import MemberView, visible


def drive_session():
    import google.auth

    oauth_path = settings.BASE_DIR / ".local" / "drive-oauth.json"
    path = (
        str(oauth_path) if oauth_path.exists() else os.getenv("GOOGLE_DRIVE_CREDENTIALS_FILE", "")
    )
    if not path:
        error = APIException("Drive connection is not configured yet.")
        error.status_code = 503
        raise error
    if not os.path.isabs(path):
        path = str(settings.BASE_DIR / path)
    credentials, _ = google.auth.load_credentials_from_file(
        path, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return AuthorizedSession(credentials)


def delivery_url(item, user, variant="original", media_index=None):
    resource = (
        "avatar"
        if isinstance(item, ProfileImage)
        else "spotlight"
        if isinstance(item, Spotlight)
        else "event"
        if isinstance(item, Event)
        else "publication"
    )
    token = signing.dumps(
        {
            resource: str(item.pk),
            "user": str(user.pk),
            "variant": variant,
            **({"media_index": media_index} if media_index is not None else {}),
        },
        salt="pixel-media",
        compress=True,
    )
    return f"{settings.BACKEND_URL}/api/v1/media/{token}/"


class DownloadView(MemberView):
    def get(self, request, pk):
        from django.shortcuts import get_object_or_404

        item = get_object_or_404(visible(), pk=pk)
        index = request.query_params.get("image")
        if index is not None:
            try:
                index = int(index)
            except ValueError as exc:
                raise ValidationError("Choose a valid post image.") from exc
            if item.kind != "post" or not 0 <= index < len(item.post_media):
                raise ValidationError("This post image is unavailable.")
        return Response(
            {"url": delivery_url(item, request.user, media_index=index), "expires_in": 600}
        )


class MediaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, token):
        from django.shortcuts import get_object_or_404

        try:
            data = signing.loads(token, salt="pixel-media", max_age=600)
        except signing.BadSignature as exc:
            raise PermissionDenied("This media link has expired.") from exc
        viewer = get_object_or_404(User, pk=data["user"], is_active=True, email_verified=True)
        manager = viewer.role == "Administrator" and viewer.is_staff
        if "avatar" in data:
            item = get_object_or_404(
                ProfileImage, pk=data["avatar"], user__is_active=True, user__email_verified=True
            )
            file_id = item.drive_file_id
        elif "spotlight" in data:
            item = get_object_or_404(
                Spotlight, pk=data["spotlight"], **({} if manager else {"published": True})
            )
            file_id = item.cover_drive_file_id
        elif "event" in data:
            item = get_object_or_404(
                Event, pk=data["event"], **({} if manager else {"published": True})
            )
            file_id = item.cover_drive_file_id
        else:
            item = get_object_or_404(
                Publication,
                pk=data["publication"],
                **(
                    {}
                    if manager
                    else {"published": True, "available": True, "event__published": True}
                ),
            )
            file_id = (
                item.cover_drive_file_id
                if data.get("variant") == "thumbnail" and item.cover_drive_file_id
                else item.drive_file_id
            )
            if "media_index" in data:
                index = data["media_index"]
                if (
                    item.kind != "post"
                    or not isinstance(index, int)
                    or not 0 <= index < len(item.post_media)
                ):
                    raise PermissionDenied("This post image is no longer available.")
                file_id = item.post_media[index]
        if not file_id:
            url = getattr(item, "original_url", getattr(item, "cover_url", ""))
            if not url:
                from django.http import Http404

                raise Http404()
            response = HttpResponseRedirect(url)
            response["Cache-Control"] = "private, no-store"
            return response
        session = drive_session()
        if data.get("variant") in ["thumbnail", "preview"]:
            metadata = session.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                params={"fields": "thumbnailLink", "supportsAllDrives": "true"},
                timeout=20,
            )
            thumbnail = metadata.json().get("thumbnailLink", "") if metadata.ok else ""
            if not thumbnail:
                session.close()
                raise APIException("A preview is not available for this file yet.")
            from urllib.parse import urlparse

            host = urlparse(thumbnail).hostname or ""
            if not host.endswith(".googleusercontent.com"):
                session.close()
                raise APIException("Unexpected preview provider.")
            thumbnail = re.sub(
                r"=s\d+", "=s1600" if data["variant"] == "preview" else "=s800", thumbnail
            )
            preview = session.get(thumbnail, timeout=30)
            session.close()
            from django.http import HttpResponse

            result = HttpResponse(
                preview.content,
                status=preview.status_code,
                content_type=preview.headers.get("Content-Type", "image/jpeg"),
            )
            result["Cache-Control"] = "private, max-age=120"
            return result
        headers = {}
        if request.headers.get("Range"):
            if not re.fullmatch(r"bytes=\d*-\d*", request.headers["Range"]):
                raise ValidationError("Invalid byte range.")
            headers["Range"] = request.headers["Range"]
        response = session.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            params={"alt": "media", "supportsAllDrives": "true"},
            headers=headers,
            stream=True,
            timeout=(10, 45),
        )
        if response.status_code not in [200, 206]:
            response.close()
            session.close()
            raise APIException("Drive media is temporarily unavailable.")

        def chunks():
            try:
                yield from response.iter_content(128 * 1024)
            finally:
                response.close()
                session.close()

        result = StreamingHttpResponse(
            chunks(),
            status=response.status_code,
            content_type=response.headers.get("Content-Type", "application/octet-stream"),
        )
        for key in ["Content-Length", "Content-Range", "Accept-Ranges"]:
            if key in response.headers:
                result[key] = response.headers[key]
        result["Cache-Control"] = "private, no-store"
        result["Content-Disposition"] = "inline" if data.get("variant") == "play" else "attachment"
        return result
