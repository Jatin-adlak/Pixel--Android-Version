"""Read-only verification of original bytes and byte-range delivery."""

import hashlib
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.community.media import drive_session
from apps.community.models import EventSyncState, Publication


class Command(BaseCommand):
    help = "Verify one existing gallery original against its Drive checksum without saving or changing media."

    def handle(self, *args, **options):
        photo = (
            Publication.objects.filter(
                kind="photo", available=True, published=True, event__published=True
            )
            .exclude(drive_file_id="")
            .first()
        )
        actor = User.objects.filter(
            email=settings.MAIN_ADMIN_EMAIL, role="Administrator", is_active=True
        ).first()
        if not photo or not actor:
            raise CommandError(
                "A published gallery photograph and Pixel administrator are required."
            )
        with drive_session() as session:
            metadata = session.get(
                f"https://www.googleapis.com/drive/v3/files/{photo.drive_file_id}",
                params={"fields": "size,md5Checksum", "supportsAllDrives": "true"},
                timeout=20,
            )
            metadata.raise_for_status()
            info = metadata.json()
        client = APIClient()
        client.force_authenticate(actor)
        result = client.get(f"/api/v1/publications/{photo.pk}/download/")
        if result.status_code != 200:
            raise CommandError("The authenticated download endpoint did not issue a media link.")
        path = urlsplit(result.data["url"]).path
        response = client.get(path)
        if response.status_code != 200:
            raise CommandError("The original media stream failed.")
        checksum = hashlib.md5(usedforsecurity=False)
        size = 0
        prefix = b""
        try:
            for chunk in response.streaming_content:
                checksum.update(chunk)
                size += len(chunk)
                if len(prefix) < 1024:
                    prefix += chunk[: 1024 - len(prefix)]
        finally:
            response.close()
        if size != int(info["size"]) or checksum.hexdigest() != info.get("md5Checksum"):
            raise CommandError("The delivered original did not match Drive metadata.")
        self.stdout.write("Original bytes: checksum and size match Google Drive.")
        ranged = client.get(path, HTTP_RANGE="bytes=0-1023")
        try:
            data = b"".join(ranged.streaming_content)
        finally:
            ranged.close()
        if ranged.status_code != 206 or data != prefix:
            raise CommandError("Byte-range delivery failed.")
        self.stdout.write("Byte ranges: HTTP 206 and requested bytes verified.")
        state = EventSyncState.objects.filter(event=photo.event).first()
        self.stdout.write(
            f"Event sync: {state.photo_count if state else 0} photographs; successful run recorded: {bool(state and state.last_success_at)}."
        )
