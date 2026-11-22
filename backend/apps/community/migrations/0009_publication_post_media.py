from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("community", "0008_spotlight_alter_drivefolder_kind_and_more")]
    operations = [
        migrations.AddField(
            model_name="publication",
            name="post_media",
            field=models.JSONField(default=list, blank=True, editable=False),
        )
    ]
