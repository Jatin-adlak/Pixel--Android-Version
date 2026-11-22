"""Read dimensions for older Drive posts; originals and social records are untouched."""

import requests
from django.core.management.base import BaseCommand

from apps.community.media import drive_session
from apps.community.models import Publication


class Command(BaseCommand):
    help = "Backfill missing post-image dimensions from Drive metadata."

    def handle(self, *args, **options):
        changed = skipped = 0
        cached = {}
        with drive_session() as session:
            for post in (
                Publication.objects.filter(kind="post")
                .exclude(drive_file_id="")
                .iterator(chunk_size=100)
            ):
                sizes = dict(post.image_dimensions)
                for file_id in post.post_media or [post.drive_file_id]:
                    if sizes.get(file_id):
                        continue
                    try:
                        if file_id not in cached:
                            response = session.get(
                                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                                params={
                                    "fields": "imageMediaMetadata(width,height,rotation)",
                                    "supportsAllDrives": "true",
                                },
                                timeout=20,
                            )
                            response.raise_for_status()
                            data = response.json().get("imageMediaMetadata", {})
                            width, height = data.get("width", 0), data.get("height", 0)
                            if int(data.get("rotation", 0)) % 2:
                                width, height = height, width
                            cached[file_id] = (
                                {"width": width, "height": height}
                                if width > 0 and height > 0
                                else {}
                            )
                        if cached[file_id]:
                            sizes[file_id] = cached[file_id]
                        else:
                            skipped += 1
                    except (requests.RequestException, ValueError, TypeError):
                        skipped += 1
                if sizes != post.image_dimensions:
                    changed += Publication.objects.filter(
                        pk=post.pk, drive_file_id=post.drive_file_id, post_media=post.post_media
                    ).update(image_dimensions=sizes)
        self.stdout.write(
            f"Updated dimensions on {changed} posts; {skipped} images retain preview fallback."
        )
