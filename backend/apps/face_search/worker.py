"""Durable job orchestration; the CPU inference implementation lives in face_recognition/."""

from datetime import timedelta

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone
from face_recognition.app.engine import (
    MODEL_VERSION,
    FaceInputError,
    batch_similarities,
    get_engine,
)

from apps.community.media import drive_session
from apps.community.models import Publication

from .models import FaceSearchJob, PhotoFaceIndex
from .storage import query_path, remove_query, source_key
from .vectors import exact_scores, replace_embeddings


def download_original(photo):
    if not photo.drive_file_id:
        raise ValueError("Only connected Drive photographs can be indexed.")
    with drive_session() as session:
        with session.get(
            f"https://www.googleapis.com/drive/v3/files/{photo.drive_file_id}",
            params={"alt": "media", "supportsAllDrives": "true"},
            stream=True,
            timeout=(10, 45),
        ) as response:
            response.raise_for_status()
            data = bytearray()
            for block in response.iter_content(128 * 1024):
                data.extend(block)
                if len(data) > 32 * 1024 * 1024:
                    raise ValueError("Original photograph exceeds the indexing limit.")
            return bytes(data)


def index_photo(photo, engine):
    signature = source_key(photo)
    cached = PhotoFaceIndex.objects.filter(
        photo=photo, model_version=MODEL_VERSION, source_key=signature
    ).first()
    if cached and (
        not cached.error or (cached.retry_after and cached.retry_after > timezone.now())
    ):
        if not cached.vectorized:
            if not replace_embeddings(cached, cached.faces):
                return None
        return cached
    try:
        faces = engine.extract(download_original(photo))
        failed = False
    except Exception:
        faces, failed = [], True
    # Lock the source record so a simultaneous Drive reconciliation cannot commit stale features.
    with transaction.atomic():
        current = (
            Publication.objects.select_for_update()
            .filter(pk=photo.pk, available=True, published=True, event__published=True)
            .first()
        )
        if not current or source_key(current) != signature:
            return None
        result, _ = PhotoFaceIndex.objects.update_or_create(
            photo=current,
            defaults={
                "source_key": signature,
                "model_version": MODEL_VERSION,
                "faces": faces,
                "error": failed,
                "retry_after": timezone.now() + timedelta(minutes=10) if failed else None,
            },
        )
        replace_embeddings(result, faces)
        return result


def cleanup():
    now = timezone.now()
    local_jobs = FaceSearchJob.objects.filter(worker_node=settings.FACE_WORKER_NODE_ID)
    stale = local_jobs.filter(status="processing", lease_until__lt=now)
    for job in stale:
        remove_query(job.pk)
    stale.update(
        status="failed",
        error="Matching was interrupted. Please upload your photo again.",
        results=[],
    )
    expired = local_jobs.filter(expires_at__lte=now).exclude(status="expired")
    for job in expired:
        remove_query(job.pk)
    expired.update(status="expired", results=[])
    # Delete obsolete biometrics as soon as their photograph is unavailable/unpublished.
    PhotoFaceIndex.objects.filter(photo__available=False).delete()
    PhotoFaceIndex.objects.filter(photo__published=False).delete()
    PhotoFaceIndex.objects.filter(photo__event__published=False).delete()
    # Orphan files from a crash between upload and job creation are bounded by age.
    root = query_path("unused").parent
    if root.exists():
        active_queries = {
            str(pk)
            for pk in local_jobs.filter(
                status__in=["queued", "processing"], expires_at__gt=now
            ).values_list("pk", flat=True)
        }
        for path in root.glob("*.query"):
            if (
                path.stem not in active_queries
                and path.stat().st_mtime < (now - timedelta(minutes=45)).timestamp()
            ):
                path.unlink(missing_ok=True)


def process_job(job_id, heartbeat=lambda: None):
    now = timezone.now()
    if not FaceSearchJob.objects.filter(
        pk=job_id, worker_node=settings.FACE_WORKER_NODE_ID, status="queued", expires_at__gt=now
    ).update(
        status="processing", phase="Checking your photo", lease_until=now + timedelta(minutes=2)
    ):
        return
    job = FaceSearchJob.objects.select_related("user", "event").get(pk=job_id)
    try:
        engine = get_engine()
        data = query_path(job.pk).read_bytes()
        try:
            query_faces = engine.extract(data, query=True)
        finally:
            remove_query(job.pk)
            del data
        if len(query_faces) != 1:
            raise FaceInputError("Choose a clear photo with just your face visible.")
        query = query_faces[0]["vector"]
        del query_faces
        photos = Publication.objects.filter(
            event=job.event, kind="photo", published=True, available=True, event__published=True
        ).order_by("id")
        # One event-scoped snapshot includes cached features. Close its cursor
        # before downloads/inference so gallery sync is never blocked by a reader.
        database_matching = connection.vendor == "postgresql"
        photos = photos.select_related("face_index")
        if database_matching:
            photos = photos.defer("face_index__faces")
        photos = list(photos)
        total = len(photos)
        FaceSearchJob.objects.filter(pk=job.pk, status="processing").update(
            total=total, phase="Matching indexed event photos"
        )
        matches, skipped = [], 0
        searchable = {}
        batch_size = 64
        for offset in range(0, total, batch_size):
            heartbeat()
            current = FaceSearchJob.objects.filter(
                pk=job.pk,
                status="processing",
                expires_at__gt=timezone.now(),
                user__is_active=True,
                user__email_verified=True,
                event__published=True,
            ).exists()
            if not current:
                return
            batch = photos[offset : offset + batch_size]
            groups, signatures = [], []
            for index, photo in enumerate(batch):
                signature = source_key(photo)
                try:
                    cached = photo.face_index
                except PhotoFaceIndex.DoesNotExist:
                    cached = None
                if (
                    not cached
                    or cached.model_version != MODEL_VERSION
                    or cached.source_key != signature
                    or (database_matching and not cached.vectorized)
                    or (
                        cached.error
                        and (not cached.retry_after or cached.retry_after <= timezone.now())
                    )
                ):
                    # New/changed originals retain the full-resolution pipeline.
                    # Report every cold photo; warm batches need only one update.
                    heartbeat()
                    if not FaceSearchJob.objects.filter(
                        pk=job.pk,
                        status="processing",
                        expires_at__gt=timezone.now(),
                        user__is_active=True,
                        event__published=True,
                    ).exists():
                        return
                    FaceSearchJob.objects.filter(pk=job.pk, status="processing").update(
                        phase="Indexing new event photos",
                        lease_until=timezone.now() + timedelta(minutes=2),
                    )
                    cached = index_photo(photo, engine)
                    FaceSearchJob.objects.filter(pk=job.pk, status="processing").update(
                        processed=offset + index + 1,
                        lease_until=timezone.now() + timedelta(minutes=2),
                    )
                if cached is None or cached.error:
                    skipped += 1
                    groups.append([])
                    signatures.append(signature)
                else:
                    if database_matching:
                        searchable[cached.pk] = (str(photo.pk), cached.source_key)
                        groups.append([])
                    else:
                        groups.append(cached.faces)
                    signatures.append(cached.source_key)
            for photo, signature, score in zip(
                batch,
                signatures,
                []
                if database_matching
                else batch_similarities(query, groups, threshold=job.threshold),
            ):
                if score >= job.threshold:
                    matches.append(
                        {"id": str(photo.pk), "score": round(score, 6), "source_key": signature}
                    )
            FaceSearchJob.objects.filter(pk=job.pk, status="processing").update(
                processed=min(offset + batch_size, total),
                skipped=skipped,
                phase="Matching indexed event photos",
                lease_until=timezone.now() + timedelta(minutes=2),
            )
        if database_matching:
            heartbeat()
            for index_id, score in exact_scores(query, searchable, job.threshold).items():
                photo_id, signature = searchable[index_id]
                matches.append({"id": photo_id, "score": round(score, 6), "source_key": signature})
        matches.sort(key=lambda row: (-row["score"], row["id"]))
        if total and skipped == total:
            raise RuntimeError("No event photographs could be read.")
        # Cancellation/withdrawal may race with the last image. A conditional update prevents resurrection.
        FaceSearchJob.objects.filter(
            pk=job.pk,
            status="processing",
            user__is_active=True,
            user__email_verified=True,
            event__published=True,
            expires_at__gt=timezone.now(),
        ).update(
            status="complete",
            phase="Matching complete",
            results=matches,
            expires_at=timezone.now() + timedelta(minutes=15),
            lease_until=None,
        )
    except Exception as exc:
        message = (
            str(exc)
            if isinstance(exc, FaceInputError)
            else "Matching could not finish. Please try again with a clear photo."
        )
        FaceSearchJob.objects.filter(pk=job.pk, status="processing").update(
            status="failed", error=message[:300], results=[], lease_until=None
        )
    finally:
        remove_query(job.pk)


def index_next(heartbeat=lambda: None):
    """Warm the gallery index between searches, without delaying a queued search by a full album."""
    candidates = (
        Publication.objects.filter(
            kind="photo", published=True, available=True, event__published=True
        )
        .select_related("face_index")
        .only(
            "id",
            "drive_file_id",
            "source_revision",
            "original_url",
            "face_index__model_version",
            "face_index__source_key",
            "face_index__error",
            "face_index__retry_after",
            "face_index__vectorized",
        )
    )
    # Finish the database read before network/inference work. An open SQLite read
    # cursor would otherwise block the Drive sync writer for the whole download.
    for photo in list(candidates):
        try:
            cached = photo.face_index
        except PhotoFaceIndex.DoesNotExist:
            cached = None
        if (
            cached
            and cached.model_version == MODEL_VERSION
            and cached.source_key == source_key(photo)
            and (connection.vendor != "postgresql" or cached.vectorized)
            and (not cached.error or cached.retry_after > timezone.now())
        ):
            continue
        heartbeat()
        index_photo(photo, get_engine())
        return True
    return False
