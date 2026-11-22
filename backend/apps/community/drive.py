"""Idempotent folder discovery. Reconcile deletions only after a complete listing."""

from django.db import transaction

from .media import drive_session
from .models import Publication


def upload_media(upload, folder, kind, existing_id=None):
    import re

    from django.conf import settings

    if not folder or not re.fullmatch(r"[A-Za-z0-9_-]+", folder):
        raise ValueError("Configure a valid destination Drive folder ID first.")
    if not (settings.BASE_DIR / ".local" / "drive-oauth.json").exists():
        raise ValueError(
            "Connect the Pixel Google account using the link above before uploading to My Drive."
        )
    if upload.size > 100 * 1024 * 1024:
        raise ValueError("Maximum upload size is 100 MB.")
    header = upload.read(32)
    upload.seek(0)
    image = (
        header.startswith(b"\xff\xd8\xff")
        or header.startswith(b"\x89PNG\r\n\x1a\n")
        or (header[:4] == b"RIFF" and header[8:12] == b"WEBP")
    )
    video = header[4:8] == b"ftyp"
    if (kind == "moment" and not video) or (kind != "moment" and not image):
        raise ValueError("Use JPEG, PNG or WebP images, or an MP4 video for moments.")
    mime = (
        "video/mp4"
        if kind == "moment"
        else "image/png"
        if header.startswith(b"\x89PNG")
        else "image/webp"
        if header[:4] == b"RIFF"
        else "image/jpeg"
    )
    import requests

    try:
        with drive_session() as session:
            response = (session.patch if existing_id else session.post)(
                "https://www.googleapis.com/upload/drive/v3/files"
                + (f"/{existing_id}" if existing_id else ""),
                params={"uploadType": "resumable", "supportsAllDrives": "true", "fields": "id"},
                json={"name": upload.name, **({} if existing_id else {"parents": [folder]})},
                headers={
                    "X-Upload-Content-Type": mime,
                    "X-Upload-Content-Length": str(upload.size),
                },
                timeout=30,
            )
            response.raise_for_status()
            location = response.headers.get("Location", "")
            if not location.startswith("https://www.googleapis.com/"):
                raise RuntimeError("Drive did not provide a valid upload session.")
            result = session.put(
                location,
                data=upload,
                headers={"Content-Type": mime, "Content-Length": str(upload.size)},
                timeout=(10, 180),
            )
            result.raise_for_status()
            return result.json()["id"]
    except (requests.RequestException, KeyError) as exc:
        raise RuntimeError(
            "Upload failed. Check the Google account connection and Drive folder access, then retry."
        ) from exc


def sync_event(event, author, heartbeat=None):
    if not event.drive_folder_id:
        raise ValueError("Set the event Drive folder ID first.")
    files = []
    token = None
    with drive_session() as session:
        folder = session.get(
            f"https://www.googleapis.com/drive/v3/files/{event.drive_folder_id}",
            params={"fields": "mimeType,trashed", "supportsAllDrives": "true"},
            timeout=20,
        )
        folder.raise_for_status()
        if folder.json().get(
            "mimeType"
        ) != "application/vnd.google-apps.folder" or folder.json().get("trashed"):
            raise ValueError(
                "The event folder is unavailable. Existing photo records were retained."
            )
        while True:
            response = session.get(
                "https://www.googleapis.com/drive/v3/files",
                params={
                    "q": f"'{event.drive_folder_id}' in parents and trashed = false",
                    "pageSize": 1000,
                    "fields": "nextPageToken,files(id,name,mimeType,version)",
                    "supportsAllDrives": "true",
                    "includeItemsFromAllDrives": "true",
                    **({"pageToken": token} if token else {}),
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            if heartbeat:
                heartbeat()
            files.extend(f for f in data.get("files", []) if f["mimeType"].startswith("image/"))
            token = data.get("nextPageToken")
            if not token:
                break
    with transaction.atomic():
        for file in files:
            item, created = Publication.objects.get_or_create(
                event=event,
                kind="photo",
                drive_file_id=file["id"],
                defaults={
                    "author": author,
                    "title": file["name"],
                    "tag": event.tag,
                    "published": True,
                },
            )
            item.source_revision = file.get("version", "")
            item.available = True
            item.title = file["name"][:160]
            item.save(update_fields=["source_revision", "available", "title"])
        Publication.objects.filter(event=event, kind="photo").exclude(drive_file_id="").exclude(
            drive_file_id__in=[f["id"] for f in files]
        ).update(available=False)
    return len(files)


def change_drive_file(file_id, **metadata):
    with drive_session() as session:
        response = session.patch(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            params={"supportsAllDrives": "true"},
            json=metadata,
            timeout=25,
        )
        if not response.ok:
            raise ValueError(
                "Drive could not update this photograph. Check the connection and retry."
            )


def move_drive_file(file_id, source, target):
    if not source or not target:
        raise ValueError("Both event folders must be connected before moving a photograph.")
    with drive_session() as session:
        response = session.patch(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            params={"addParents": target, "removeParents": source, "supportsAllDrives": "true"},
            json={},
            timeout=25,
        )
        if not response.ok:
            raise ValueError("Drive could not move this photograph. Check both event folders.")
