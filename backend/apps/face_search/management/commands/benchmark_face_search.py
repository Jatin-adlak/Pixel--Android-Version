"""Read-only cached matching benchmark. Never exports vectors, identities or results."""

import json
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from face_recognition.app.engine import MODEL_VERSION, batch_similarities, best_similarity

from apps.community.models import Publication
from apps.face_search.models import FaceEmbedding, PhotoFaceIndex
from apps.face_search.storage import source_key
from apps.face_search.vectors import exact_scores


class Command(BaseCommand):
    help = "Compare cached per-photo reads against bulk exact face matching (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("--event")

    def handle(self, *args, **options):
        photos = Publication.objects.filter(
            kind="photo", available=True, published=True, event__published=True
        )
        event_id = options["event"] or photos.values_list("event_id", flat=True).first()
        if not event_id:
            raise CommandError("No event photographs are available.")
        photos = photos.filter(event_id=event_id).order_by("id")
        if connection.vendor == "postgresql":
            self.postgres_benchmark(photos)
            return
        seed = (
            PhotoFaceIndex.objects.filter(
                photo__in=photos, error=False, model_version=MODEL_VERSION
            )
            .exclude(faces=[])
            .first()
        )
        if seed is None:
            raise CommandError("Index at least one face before benchmarking.")
        query = seed.faces[0]["vector"]
        report = {}
        for method in ("per_photo", "bulk"):
            count = [0]

            def counter(execute, sql, params, many, context):
                count[0] += 1
                return execute(sql, params, many, context)

            start = time.perf_counter()
            groups = []
            with connection.execute_wrapper(counter):
                if method == "per_photo":
                    for photo in photos.all():
                        cached = PhotoFaceIndex.objects.filter(
                            photo=photo,
                            error=False,
                            source_key=source_key(photo),
                            model_version=MODEL_VERSION,
                        ).first()
                        groups.append(cached.faces if cached else [])
                    scores = [best_similarity(query, faces) for faces in groups]
                else:
                    for photo in photos.select_related("face_index"):
                        try:
                            cached = photo.face_index
                        except PhotoFaceIndex.DoesNotExist:
                            cached = None
                        groups.append(
                            cached.faces
                            if cached
                            and not cached.error
                            and cached.model_version == MODEL_VERSION
                            and cached.source_key == source_key(photo)
                            else []
                        )
                    scores = batch_similarities(query, groups)
            report[method] = {
                "seconds": round(time.perf_counter() - start, 4),
                "database_queries": count[0],
                "photos": len(groups),
                "faces": sum(map(len, groups)),
            }
            if method == "per_photo":
                baseline = scores
            else:
                report["max_score_difference"] = max(
                    (abs(a - b) for a, b in zip(baseline, scores)), default=0
                )
        self.stdout.write(json.dumps(report))

    def postgres_benchmark(self, photos):
        indexes = list(
            PhotoFaceIndex.objects.filter(
                photo__in=photos,
                error=False,
                vectorized=True,
                model_version=MODEL_VERSION,
            )
            .select_related("photo")
            .defer("faces")
        )
        indexes = {row.pk: row for row in indexes if row.source_key == source_key(row.photo)}
        groups = {pk: [] for pk in indexes}
        for pk, vector in FaceEmbedding.objects.filter(index_id__in=indexes).values_list(
            "index_id", "embedding"
        ):
            groups[pk].append({"vector": vector.tolist()})
        query = next((faces[0]["vector"] for faces in groups.values() if faces), None)
        if query is None:
            raise CommandError("Index at least one face before benchmarking.")
        scores = batch_similarities(query, list(groups.values()), threshold=0.5)
        expected = {pk: score for pk, score in zip(groups, scores) if score >= 0.5}
        start = time.perf_counter()
        actual = exact_scores(query, indexes, 0.5)
        elapsed = time.perf_counter() - start
        if actual.keys() != expected.keys():
            raise CommandError("PostgreSQL and FP32 matching returned different photograph sets.")
        self.stdout.write(
            json.dumps(
                {
                    "method": "pgvector_exact_threshold",
                    "seconds": round(elapsed, 4),
                    "photos": len(indexes),
                    "faces": sum(map(len, groups.values())),
                    "result_set_matches_fp32": True,
                    "max_score_difference": max(
                        (abs(actual[pk] - expected[pk]) for pk in actual), default=0
                    ),
                }
            )
        )
