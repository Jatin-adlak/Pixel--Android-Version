import uuid

from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField


class PhotoFaceIndex(models.Model):
    photo = models.OneToOneField(
        "community.Publication", on_delete=models.CASCADE, related_name="face_index"
    )
    source_key = models.CharField(max_length=64)
    model_version = models.CharField(max_length=100)
    faces = models.JSONField(default=list)
    vectorized = models.BooleanField(default=False)
    face_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    error = models.BooleanField(default=False)
    retry_after = models.DateTimeField(null=True)


class FaceEmbedding(models.Model):
    index = models.ForeignKey(PhotoFaceIndex, on_delete=models.CASCADE, related_name="embeddings")
    position = models.PositiveSmallIntegerField()
    embedding = VectorField(dimensions=128)
    box = models.JSONField(default=list)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["index", "position"], name="unique_face_per_index")
        ]
        indexes = [
            HnswIndex(
                name="face_embedding_hnsw_ip",
                fields=["embedding"],
                m=16,
                ef_construction=128,
                opclasses=["vector_ip_ops"],
            )
        ]


class FaceSearchJob(models.Model):
    worker_node = models.CharField(max_length=100, default="legacy", db_index=True, editable=False)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event = models.ForeignKey("community.Event", on_delete=models.CASCADE)
    status = models.CharField(max_length=16, default="queued", db_index=True)
    phase = models.CharField(max_length=80, default="Waiting to start")
    processed = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    skipped = models.PositiveIntegerField(default=0)
    results = models.JSONField(default=list)
    error = models.CharField(max_length=300, blank=True)
    consent_version = models.CharField(max_length=32)
    model_version = models.CharField(max_length=100)
    threshold = models.FloatField(default=0.5)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    lease_until = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status__in=["queued", "processing"]),
                name="one_active_face_search_per_user",
            )
        ]


class FaceWorkerState(models.Model):
    node_id = models.CharField(max_length=100, default="legacy", unique=True)
    lease_until = models.DateTimeField(null=True)
    token = models.UUIDField(null=True)
    last_seen_at = models.DateTimeField(null=True)
