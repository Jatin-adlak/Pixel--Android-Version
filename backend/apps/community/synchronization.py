"""Database leases and retry state for event media synchronization only."""

import uuid
from contextlib import contextmanager
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .drive import sync_event
from .models import EventSyncState


@contextmanager
def event_lock(event):
    state, _ = EventSyncState.objects.get_or_create(
        event=event, defaults={"next_run_at": timezone.now()}
    )
    token = uuid.uuid4()
    claimed = (
        EventSyncState.objects.filter(pk=state.pk)
        .filter(Q(lease_until__isnull=True) | Q(lease_until__lt=timezone.now()))
        .update(lease_token=token, lease_until=timezone.now() + timedelta(minutes=10))
    )
    if not claimed:
        raise ValidationError("This event is synchronizing. Try again shortly.")
    try:
        yield state, token
    finally:
        EventSyncState.objects.filter(pk=state.pk, lease_token=token).update(
            lease_token=None, lease_until=None
        )


def synchronize(event, author):
    with event_lock(event) as (state, token):

        def heartbeat():
            if not EventSyncState.objects.filter(pk=state.pk, lease_token=token).update(
                lease_until=timezone.now() + timedelta(minutes=10)
            ):
                raise RuntimeError("Synchronization lease expired.")

        try:
            count = sync_event(event, author, heartbeat=heartbeat)
            EventSyncState.objects.filter(pk=state.pk, lease_token=token).update(
                last_success_at=timezone.now(),
                next_run_at=timezone.now() + timedelta(seconds=60),
                failures=0,
                last_error="",
                photo_count=count,
            )
            return count
        except Exception:
            failures = state.failures + 1
            EventSyncState.objects.filter(pk=state.pk, lease_token=token).update(
                failures=failures,
                next_run_at=timezone.now()
                + timedelta(seconds=min(3600, 30 * 2 ** min(failures, 7))),
                last_error="Drive synchronization failed. Check folder access and connection, then retry.",
            )
            raise
