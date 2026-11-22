import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.community.models import Event, EventSyncState
from apps.community.synchronization import synchronize


class Command(BaseCommand):
    help = "Keep event gallery media synchronized with Drive. Run separately from Django."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        while True:
            actor = User.objects.filter(
                email=settings.MAIN_ADMIN_EMAIL,
                role="Administrator",
                is_active=True,
                email_verified=True,
            ).first()
            if actor:
                for event in (
                    Event.objects.filter(spotlight=False).exclude(drive_folder_id="").iterator()
                ):
                    state, _ = EventSyncState.objects.get_or_create(
                        event=event, defaults={"next_run_at": timezone.now()}
                    )
                    if state.next_run_at <= timezone.now():
                        try:
                            count = synchronize(event, actor)
                            self.stdout.write(f"Event {event.pk}: {count} photos synchronized.")
                        except Exception:
                            self.stderr.write(
                                f"Event {event.pk}: sync deferred; see Admin Studio for status."
                            )
            if options["once"]:
                break
            time.sleep(5)
