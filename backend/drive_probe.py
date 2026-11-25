"""Read-only connectivity check for the configured media folders."""

import os

import django


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    from apps.community.media import drive_session
    from apps.community.models import DriveFolder

    with drive_session() as session:
        for folder in DriveFolder.objects.filter(kind__in=["post", "moment"]):
            response = session.get(
                f"https://www.googleapis.com/drive/v3/files/{folder.folder_id}",
                params={
                    "fields": "id,capabilities(canAddChildren,canDownload)",
                    "supportsAllDrives": "true",
                },
                timeout=20,
            )
            print(f"{folder.kind}: HTTP {response.status_code}")


if __name__ == "__main__":
    main()
