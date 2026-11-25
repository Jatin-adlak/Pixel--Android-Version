import os
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.community.models import Event
from apps.community.queries import MemberView, content, page, visible

from .models import FaceSearchJob, FaceWorkerState
from .storage import CONSENT_VERSION, MAX_QUERY_BYTES, query_path, remove_query, source_key


def worker_ready():
    from face_recognition.app.engine import MANIFEST, MODEL_ROOT

    return (
        all((MODEL_ROOT / MANIFEST[k]["file"]).is_file() for k in ("detector", "recognizer"))
        and FaceWorkerState.objects.filter(
            node_id=settings.FACE_WORKER_NODE_ID,
            last_seen_at__gte=timezone.now() - timedelta(seconds=120),
        ).exists()
    )


def owned_job(request, pk):
    job = get_object_or_404(
        FaceSearchJob,
        pk=pk,
        user=request.user,
        worker_node=settings.FACE_WORKER_NODE_ID,
        event__published=True,
        event__spotlight=False,
    )
    if job.expires_at <= timezone.now():
        remove_query(job.pk)
        job.results = []
        job.status = "expired"
        job.save(update_fields=["results", "status"])
    return job


def job_data(job):
    return {
        "id": str(job.pk),
        "status": job.status,
        "phase": job.phase,
        "processed": job.processed,
        "total": job.total,
        "skipped": job.skipped,
        "match_count": len(job.results),
        "error": job.error,
        "expires_at": job.expires_at,
    }


class FaceSearchCreate(MemberView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "face_search"

    def get_throttles(self):
        if self.request.method == "POST":
            return super().get_throttles()
        return [throttle() for throttle in MemberView.throttle_classes]

    def get(self, request, event_id):
        get_object_or_404(Event, pk=event_id, published=True, spotlight=False)
        latest = (
            FaceSearchJob.objects.filter(
                user=request.user,
                worker_node=settings.FACE_WORKER_NODE_ID,
                event_id=event_id,
            )
            .order_by("-created_at", "-pk")
            .first()
        )
        active = None
        recent = None
        if latest and latest.expires_at > timezone.now():
            if latest.status in {"queued", "processing"}:
                active = job_data(latest)
            elif latest.status in {"complete", "failed"}:
                recent = job_data(latest)
        return Response(
            {
                "available": worker_ready(),
                "consent_version": CONSENT_VERSION,
                "max_upload_bytes": MAX_QUERY_BYTES,
                "active_job": active,
                "recent_job": recent,
            }
        )

    def post(self, request, event_id):
        from face_recognition.app.engine import MODEL_VERSION, FaceInputError, validate_query_image

        event = get_object_or_404(Event, pk=event_id, published=True, spotlight=False)
        if request.data.get("consent") != CONSENT_VERSION:
            raise ValidationError(
                "Confirm that this is your photograph and allow matching in this event."
            )
        if not worker_ready():
            return Response(
                {"detail": "Photo matching is temporarily unavailable. Please try again shortly."},
                status=503,
            )
        file = request.FILES.get("photo")
        if not file or file.size > MAX_QUERY_BYTES:
            raise ValidationError("Choose a JPEG, PNG or WebP photograph up to 5 MB.")
        data = file.read(MAX_QUERY_BYTES + 1)
        try:
            validate_query_image(data)
        except FaceInputError as exc:
            raise ValidationError(str(exc)) from exc
        # Expired jobs must not block a new request; no raw query is retained afterward.
        expired = FaceSearchJob.objects.filter(
            user=request.user,
            expires_at__lte=timezone.now(),
            status__in=["queued", "processing"],
        )
        for old in expired:
            if old.worker_node == settings.FACE_WORKER_NODE_ID:
                remove_query(old.pk)
        expired.update(status="expired", results=[])
        job = FaceSearchJob(
            worker_node=settings.FACE_WORKER_NODE_ID,
            user=request.user,
            event=event,
            consent_version=CONSENT_VERSION,
            model_version=MODEL_VERSION,
            threshold=settings.FACE_MATCH_THRESHOLD,
            expires_at=timezone.now() + timedelta(minutes=settings.FACE_SEARCH_TIMEOUT_MINUTES),
        )
        path = query_path(job.pk)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            with transaction.atomic():
                FaceWorkerState.objects.select_for_update().get_or_create(node_id="__queue__")
                if (
                    FaceSearchJob.objects.filter(
                        status__in=["queued", "processing"], expires_at__gt=timezone.now()
                    ).count()
                    >= 8
                ):
                    raise Throttled(wait=30, code="face_search_busy")
                job.save(force_insert=True)
                with os.fdopen(
                    os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
                ) as query:
                    query.write(data)
        except IntegrityError as exc:
            remove_query(job.pk)
            raise ValidationError(
                "You already have a photo search running. Wait for it or cancel it first."
            ) from exc
        except Exception:
            remove_query(job.pk)
            raise
        return Response(job_data(job), status=202)


class FaceSearchStatus(MemberView):
    def get(self, request, pk):
        return Response(job_data(owned_job(request, pk)))

    def delete(self, request, pk):
        # Withdrawal stays available even after event access is revoked.
        job = get_object_or_404(
            FaceSearchJob, pk=pk, user=request.user, worker_node=settings.FACE_WORKER_NODE_ID
        )
        FaceSearchJob.objects.filter(pk=job.pk).update(
            status="cancelled", results=[], phase="Cancelled"
        )
        remove_query(job.pk)
        return Response(status=204)


class FaceSearchResults(MemberView):
    def get(self, request, pk):
        job = owned_job(request, pk)
        if job.status in {"queued", "processing"}:
            raise ValidationError(
                "PIXEL is still looking for your photos. Check again in a moment."
            )
        if job.status != "complete":
            raise ValidationError(
                "These results are no longer available. Start a new search to try again."
            )
        candidates = {
            str(photo.pk): photo
            for photo in visible(request.user).filter(
                event_id=job.event_id, kind="photo", pk__in=[row["id"] for row in job.results]
            )
        }
        # Recheck both access and exact source revision on every result read.
        photos = [
            candidates[row["id"]]
            for row in job.results
            if row["id"] in candidates and source_key(candidates[row["id"]]) == row["source_key"]
        ]
        return page(request, photos, lambda photo: content(photo, request.user))
