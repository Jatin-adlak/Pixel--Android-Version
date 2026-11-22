from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import User

from .models import Follow


@receiver(post_save, sender=User)
def follow_pixel(sender, instance, **kwargs):
    if not instance.is_active or not instance.email_verified:
        return
    if instance.email == settings.MAIN_ADMIN_EMAIL and instance.role == "Administrator":
        for user in (
            User.objects.filter(is_active=True, email_verified=True)
            .exclude(pk=instance.pk)
            .iterator()
        ):
            Follow.objects.update_or_create(
                follower=user, target=instance, defaults={"accepted": True, "mandatory": True}
            )
    else:
        pixel = User.objects.filter(
            email=settings.MAIN_ADMIN_EMAIL,
            role="Administrator",
            is_active=True,
            email_verified=True,
        ).first()
        if pixel:
            Follow.objects.update_or_create(
                follower=instance, target=pixel, defaults={"accepted": True, "mandatory": True}
            )
