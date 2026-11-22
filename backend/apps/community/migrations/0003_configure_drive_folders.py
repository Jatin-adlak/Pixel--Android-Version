from django.db import migrations


def configure(apps, schema_editor):
    Folder = apps.get_model("community", "DriveFolder")
    for kind, folder_id in [
        ("post", "1Fq_95ZS0QFq31cuLXfDwkCda3OpODgkP"),
        ("moment", "10Q0nvDwGMXU8Mc-o1U5QFaY_5r4p2Eqp"),
    ]:
        Folder.objects.get_or_create(kind=kind, defaults={"folder_id": folder_id})
    User = apps.get_model("accounts", "User")
    Follow = apps.get_model("community", "Follow")
    pixel = User.objects.filter(
        email="pixel.club@sait.ac.in", role="Administrator", is_active=True, email_verified=True
    ).first()
    if pixel:
        for user in (
            User.objects.filter(is_active=True, email_verified=True).exclude(pk=pixel.pk).iterator()
        ):
            Follow.objects.update_or_create(
                follower=user, target=pixel, defaults={"accepted": True, "mandatory": True}
            )


class Migration(migrations.Migration):
    dependencies = [("community", "0002_drivefolder_publication_available_and_more")]
    operations = [migrations.RunPython(configure, migrations.RunPython.noop)]
