"""Private Drive transport. Originals never enter database columns or public storage."""

import mimetypes
import os
import re

from django.conf import settings
from django.core import signing
from django.http import HttpResponse, HttpResponseRedirect, StreamingHttpResponse
from django.utils.http import content_disposition_header
from django.utils.text import slugify
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from requests.exceptions import RequestException
from rest_framework.exceptions import (
    APIException,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from apps.accounts.authentication import is_administrator
from apps.accounts.models import User

from .models import Event, ProfileImage, Publication, Spotlight
from .views import MemberView, visible


class MediaUnavailable(APIException):
    status_code = 503
    default_detail = "PIXEL can’t load this media right now. Please try again later."


def drive_session():
    import google.auth

    oauth_path = settings.BASE_DIR / ".local" / "drive-oauth.json"
    if not oauth_path.is_file():
        error = APIException("Drive connection is not configured yet.")
        error.status_code = 503
        raise error
    credentials, _ = google.auth.load_credentials_from_file(
        str(oauth_path), scopes=["https://www.googleapis.com/auth/drive"]
    )
    return AuthorizedSession(credentials)


def drive_read_session():
    key = os.getenv("GOOGLE_DRIVE_CREDENTIALS_FILE", "").strip()
    if not key:
        return drive_session()
    try:
        credentials = service_account.Credentials.from_service_account_file(
            str(settings.BASE_DIR / key),
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
    except (OSError, GoogleAuthError, ValueError) as exc:
        raise MediaUnavailable() from exc
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
        elif not (item.drive_file_id or item.original_url):
            raise NotFound("The original file is unavailable for download.")
        return Response(
            {"url": delivery_url(item, request.user, media_index=index), "expires_in": 600}
        )


class MediaViewerThrottle(SimpleRateThrottle):
    scope = "media_viewer"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": view.media_viewer_id}


class MediaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    def get(self, request, token):
        from django.shortcuts import get_object_or_404

        try:
            data = signing.loads(token, salt="pixel-media", max_age=600)
        except signing.BadSignature as exc:
            raise PermissionDenied(
                "This link has expired. Reopen the photo or video and try again."
            ) from exc
        self.media_viewer_id = data["user"]
        throttle = MediaViewerThrottle()
        if not throttle.allow_request(request, self):
            raise Throttled(wait=throttle.wait())
        viewer = get_object_or_404(User, pk=data["user"], is_active=True, email_verified=True)
        manager = is_administrator(viewer)
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
        session = drive_read_session()
        if data.get("variant") in ["thumbnail", "preview"]:
            from urllib.parse import urlparse

            try:
                metadata = session.get(
                    f"https://www.googleapis.com/drive/v3/files/{file_id}",
                    params={"fields": "thumbnailLink", "supportsAllDrives": "true"},
                    timeout=20,
                )
                thumbnail = metadata.json().get("thumbnailLink", "") if metadata.ok else ""
                if not thumbnail:
                    raise MediaUnavailable("A preview is not available for this file yet.")
                host = urlparse(thumbnail).hostname or ""
                if not host.endswith(".googleusercontent.com"):
                    raise MediaUnavailable("This preview is unavailable. Try reopening the photo.")
                thumbnail = re.sub(
                    r"=s\d+", "=s1600" if data["variant"] == "preview" else "=s800", thumbnail
                )
                preview = session.get(thumbnail, timeout=30)
            except (RequestException, GoogleAuthError) as exc:
                raise MediaUnavailable() from exc
            finally:
                session.close()

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
                session.close()
                raise ValidationError(
                    "Couldn’t start playback or resume the download. Try again from the beginning."
                )
            headers["Range"] = request.headers["Range"]
        try:
            response = session.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                params={"alt": "media", "supportsAllDrives": "true"},
                headers=headers,
                stream=True,
                timeout=(10, 45),
            )
        except (RequestException, GoogleAuthError) as exc:
            session.close()
            raise MediaUnavailable() from exc
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
        if data.get("variant") == "play":
            result["Content-Disposition"] = "inline"
        else:
            name = slugify(getattr(item, "title", ""), allow_unicode=True)[:100] or "pixel-media"
            if "media_index" in data:
                name += f"-{data['media_index'] + 1}"
            mime_type = result["Content-Type"].split(";", 1)[0].strip().lower()
            extension = (
                ".jpg" if mime_type == "image/jpeg" else mimetypes.guess_extension(mime_type)
            )
            result["Content-Disposition"] = content_disposition_header(
                True, name + (extension or "")
            )
        return result
