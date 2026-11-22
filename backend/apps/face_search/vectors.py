"""Gallery vector persistence and exact, event-scoped PostgreSQL matching.

Query/selfie vectors stay in memory. HNSW supports nearest-neighbor workloads;
the complete-photo workflow deliberately uses an exact threshold aggregation.
"""

import numpy as np
from django.db import connection, transaction
from django.db.models import Min
from face_recognition.app.engine import DIMENSIONS, best_similarity
from pgvector.django import MaxInnerProduct

from .models import FaceEmbedding, PhotoFaceIndex


def replace_embeddings(index, faces):
    rows = []
    for position, face in enumerate(faces):
        vector = np.asarray(face.get("vector", []), dtype=np.float32)
        if vector.shape != (DIMENSIONS,) or not np.isfinite(vector).all():
            raise ValueError("Invalid gallery face vector.")
        if abs(float(np.linalg.norm(vector)) - 1.0) > 1e-4:
            raise ValueError("Gallery face vectors must be normalized.")
        rows.append(
            FaceEmbedding(index=index, position=position, embedding=vector, box=face.get("box", []))
        )
    with transaction.atomic():
        # Callers also lock the publication when replacing a source revision.
        current = PhotoFaceIndex.objects.select_for_update().get(pk=index.pk)
        if (current.source_key, current.model_version) != (index.source_key, index.model_version):
            return False
        index.embeddings.all().delete()
        FaceEmbedding.objects.bulk_create(rows, batch_size=500)
        values = {"vectorized": True, "face_count": len(rows)}
        if connection.vendor == "postgresql":
            values["faces"] = []  # No duplicate JSON biometrics in the live database.
        PhotoFaceIndex.objects.filter(pk=index.pk).update(**values)
        for name, value in values.items():
            setattr(index, name, value)
    return True


def exact_scores(query, indexes, threshold):
    """One score per qualifying photo, without approximate top-k omissions."""
    vector = np.asarray(query, dtype=np.float32)
    if vector.shape != (DIMENSIONS,) or not np.isfinite(vector).all():
        raise ValueError("Invalid query vector.")
    if not indexes:
        return {}
    rows = (
        FaceEmbedding.objects.filter(index_id__in=indexes)
        .values("index_id")
        .annotate(distance=Min(MaxInnerProduct("embedding", vector.tolist())))
        .filter(distance__lte=-threshold + 1e-6)
        .values_list("index_id", "distance")
    )
    scores = {pk: -float(distance) for pk, distance in rows}
    # Keep the previous FP32 cutoff decision at numerical rounding boundaries.
    boundary = {pk: [] for pk, score in scores.items() if abs(score - threshold) <= 1e-6}
    if boundary:
        for pk, value in FaceEmbedding.objects.filter(index_id__in=boundary).values_list(
            "index_id", "embedding"
        ):
            boundary[pk].append({"vector": value.tolist()})
        for pk, faces in boundary.items():
            scores[pk] = best_similarity(vector, faces)
    return {pk: score for pk, score in scores.items() if score >= threshold}
