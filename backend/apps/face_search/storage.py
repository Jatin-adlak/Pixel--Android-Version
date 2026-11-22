import hashlib

from django.conf import settings

MAX_QUERY_BYTES = 5 * 1024 * 1024
CONSENT_VERSION = "face-event-search-v1"


def query_path(job_id):
    # IDs are server-created UUIDs. Never accept a client filename/path.
    return settings.BASE_DIR / ".local" / "face-queries" / f"{job_id}.query"


def remove_query(job_id):
    query_path(job_id).unlink(missing_ok=True)


def source_key(photo):
    return hashlib.sha256(
        f"{photo.drive_file_id}|{photo.source_revision}|{photo.original_url}".encode()
    ).hexdigest()
