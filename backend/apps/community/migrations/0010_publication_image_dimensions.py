from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("community", "0009_publication_post_media")]
    operations = [
        migrations.AddField(
            model_name="publication",
            name="image_dimensions",
            field=models.JSONField(default=dict, blank=True, editable=False),
        )
    ]
