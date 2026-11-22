import time
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError
from django.db.models import Q
from django.utils import timezone
from face_recognition.app.engine import get_engine

from apps.face_search.models import FaceSearchJob, FaceWorkerState
from apps.face_search.worker import cleanup, index_next, process_job


class Command(BaseCommand):
    help = "Run PIXEL's local face indexing and matching worker."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        get_engine()  # Verify pinned models before advertising readiness.
        token = uuid.uuid4()
        state, _ = FaceWorkerState.objects.get_or_create(node_id=settings.FACE_WORKER_NODE_ID)
        if (
            not FaceWorkerState.objects.filter(pk=state.pk)
            .filter(Q(lease_until__isnull=True) | Q(lease_until__lt=timezone.now()))
            .update(
                token=token,
                lease_until=timezone.now() + timedelta(minutes=2),
                last_seen_at=timezone.now(),
            )
        ):
            raise CommandError("A face worker is already running.")

        last_heartbeat = 0.0

        def heartbeat():
            nonlocal last_heartbeat
            now = time.monotonic()
            if now - last_heartbeat < 5:
                return
            if not FaceWorkerState.objects.filter(pk=state.pk, token=token).update(
                last_seen_at=timezone.now(), lease_until=timezone.now() + timedelta(minutes=2)
            ):
                raise CommandError("Face worker lease was lost.")
            last_heartbeat = now

        try:
            self.stdout.write("Face matching worker ready (local inference).")
            next_cleanup, next_index = 0.0, 0.0
            while True:
                try:
                    heartbeat()
                    now = time.monotonic()
                    if now >= next_cleanup:
                        cleanup()
                        next_cleanup = now + 30
                    job = (
                        FaceSearchJob.objects.filter(
                            worker_node=settings.FACE_WORKER_NODE_ID,
                            status="queued",
                            expires_at__gt=timezone.now(),
                        )
                        .order_by("created_at")
                        .first()
                    )
                    if job:
                        process_job(job.pk, heartbeat)
                    else:
                        worked = index_next(heartbeat) if now >= next_index else False
                        if not worked:
                            next_index = (
                                max(next_index, time.monotonic() + 5)
                                if now >= next_index
                                else next_index
                            )
                            if not options["once"]:
                                time.sleep(0.25)
                except OperationalError:
                    self.stderr.write("Database busy; retrying face work shortly.")
                    time.sleep(2)
                if options["once"]:
                    break
        except KeyboardInterrupt:
            pass
        finally:
            FaceWorkerState.objects.filter(pk=state.pk, token=token).update(
                lease_until=None, token=None, last_seen_at=None
            )
