import getpass
import os
import secrets
from pathlib import Path

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import AuditLog, User


class Command(BaseCommand):
    help = "Provision the main Pixel administrator locally. Existing credentials are never overwritten."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password-file", help="Generate an initial password into a new private local file."
        )

    def handle(self, *args, **options):
        if User.objects.filter(email=settings.MAIN_ADMIN_EMAIL).exists():
            raise CommandError(
                "Main administrator already exists. Use changepassword to change credentials."
            )
        target = None
        if options["password_file"]:
            target = Path(options["password_file"]).resolve()
            local_dir = (settings.BASE_DIR / ".local").resolve()
            if not target.is_relative_to(local_dir):
                raise CommandError(
                    "Password files must stay inside backend/.local/ (ignored by Git)."
                )
            password = secrets.token_urlsafe(24)
            target.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation prevents overwriting an existing credential file.
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        else:
            password = getpass.getpass("Administrator password (12+ characters): ")
            if password != getpass.getpass("Confirm password: "):
                raise CommandError("Passwords did not match.")
        validate_password(password, User(email=settings.MAIN_ADMIN_EMAIL))
        try:
            with transaction.atomic():
                user = User.objects.create_superuser(
                    email=settings.MAIN_ADMIN_EMAIL, password=password, display_name="Pixel"
                )
                AuditLog.objects.create(actor=user, action="administrator_bootstrapped")
            if target:
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(
                        f"PIXEL local administrator\nEmail: {user.email}\nInitial password: {password}\n\nChange this password in Django Admin after your first login.\nKeep this file private and remove it after recording the password securely.\n"
                    )
        except Exception:
            if target:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            raise
        self.stdout.write(
            self.style.SUCCESS("Main administrator provisioned. No password was printed.")
        )
        if target:
            self.stdout.write(f"Initial credential file: {target}")
