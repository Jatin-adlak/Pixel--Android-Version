from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import AuditLog, AuthSession, EmailVerification, OAuthAttempt, OAuthTicket


class Command(BaseCommand):
    help = (
        "Remove expired authentication artifacts and audit records older than 90 days. Run daily."
    )

    def handle(self, *args, **options):
        now = timezone.now()
        for model in (AuthSession, EmailVerification, OAuthAttempt, OAuthTicket):
            model.objects.filter(expires_at__lt=now).delete()
        AuditLog.objects.filter(created_at__lt=now - timedelta(days=90)).delete()
        call_command("flushexpiredtokens")
        self.stdout.write("Expired authentication artifacts cleaned.")
