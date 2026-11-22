from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("face_search", "0002_vector_embeddings")]
    operations = [
        migrations.AddField(
            model_name="facesearchjob",
            name="worker_node",
            field=models.CharField(default="legacy", max_length=100, db_index=True, editable=False),
        ),
        migrations.AddField(
            model_name="faceworkerstate",
            name="node_id",
            field=models.CharField(default="legacy", max_length=100, unique=True),
        ),
    ]
