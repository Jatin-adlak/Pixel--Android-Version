"""One detector/alignment/embedding implementation for queries and event indexing.

No names, account identification, remote inference or silent model downloads.
"""

import hashlib
import io
import json
import warnings
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

MODEL_ROOT = Path(__file__).resolve().parents[1] / "models"
MANIFEST = json.loads((MODEL_ROOT / "manifest.json").read_text())
MODEL_VERSION = MANIFEST["version"]
DIMENSIONS = MANIFEST["dimensions"]
MAX_BYTES = 32 * 1024 * 1024
MAX_PIXELS = 50_000_000


class FaceInputError(ValueError):
    """A user-correctable image problem, with no biometric information in logs."""


def validate_query_image(data):
    """Validate bounded headers in the API; leave pixel decoding/inference to the worker."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP", "MPO"}:
                    raise FaceInputError("Choose a JPEG, PNG or WebP photograph.")
                if image.width * image.height > 20_000_000 or min(image.size) < 80:
                    raise FaceInputError("Choose a clear selfie up to 20 megapixels.")
                if getattr(image, "n_frames", 1) != 1 and image.format != "MPO":
                    raise FaceInputError("Choose a still photograph.")
                image.verify()
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise FaceInputError("This image could not be read. Choose another photograph.") from exc


def decode_image(data):
    if not data or len(data) > MAX_BYTES:
        raise FaceInputError("This image is too large. Choose a smaller JPEG, PNG or WebP.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP", "MPO"} or (
                    getattr(source, "n_frames", 1) != 1 and source.format != "MPO"
                ):
                    raise FaceInputError("Choose a still JPEG, PNG or WebP photograph.")
                if source.width * source.height > MAX_PIXELS or min(source.size) < 80:
                    raise FaceInputError(
                        "Choose a clear photograph between 80 pixels and 50 megapixels."
                    )
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((2600, 2600), Image.Resampling.LANCZOS)
                return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise FaceInputError("This image could not be read. Choose another photograph.") from exc


def verify_models():
    for kind in ("detector", "recognizer"):
        model = MANIFEST[kind]
        path = MODEL_ROOT / model["file"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != model["sha256"]:
            raise RuntimeError("Face matching models are not installed or failed verification.")


class FaceEngine:
    def __init__(self):
        verify_models()
        cv2.setNumThreads(2)
        self.detector = cv2.FaceDetectorYN.create(
            str(MODEL_ROOT / MANIFEST["detector"]["file"]), "", (320, 320), 0.9, 0.3, 5000
        )
        self.recognizer = cv2.FaceRecognizerSF.create(
            str(MODEL_ROOT / MANIFEST["recognizer"]["file"]), ""
        )

    def extract(self, data, *, query=False):
        image = decode_image(data)
        height, width = image.shape[:2]
        # Preserve small group-photo faces; never upscale a tiny face to pass quality checks.
        self.detector.setInputSize((width, height))
        _, detections = self.detector.detect(image)
        detections = [] if detections is None else detections
        if query and len(detections) != 1:
            raise FaceInputError(
                "Choose a clear photo with only your face visible."
                if len(detections)
                else "No clear face was found. Try a well-lit, front-facing photo."
            )
        results = []
        for face in detections[:300]:
            x, y, w, h = face[:4]
            if min(w, h) < (90 if query else 36):
                if query:
                    raise FaceInputError("Your face is too small. Choose a closer photograph.")
                continue
            aligned = self.recognizer.alignCrop(image, face)
            sharpness = cv2.Laplacian(cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
            if sharpness < (55 if query else 18):
                if query:
                    raise FaceInputError("Your photo looks blurry. Choose a sharper photograph.")
                continue
            vector = self.recognizer.feature(aligned).reshape(-1).astype(np.float32)
            norm = np.linalg.norm(vector)
            if len(vector) != DIMENSIONS or not np.isfinite(vector).all() or norm < 1e-8:
                raise RuntimeError("The face model returned an invalid feature vector.")
            results.append(
                {
                    "vector": (vector / norm).tolist(),
                    "box": [float(x), float(y), float(w), float(h)],
                }
            )
        return results


@lru_cache(maxsize=1)
def get_engine():
    # Worker-local models. The public API never runs model inference.
    return FaceEngine()


def best_similarity(query, faces):
    vector = np.asarray(query, dtype=np.float32)
    if vector.shape != (DIMENSIONS,) or not np.isfinite(vector).all():
        raise ValueError("Invalid query feature.")
    valid = [face["vector"] for face in faces if len(face.get("vector", [])) == DIMENSIONS]
    if not valid:
        return -1.0
    matrix = np.asarray(valid, dtype=np.float32)
    scores = matrix @ vector
    return float(np.max(scores)) if np.isfinite(scores).all() else -1.0


def batch_similarities(query, groups, *, threshold=None):
    """Exact cosine scores, reduced per photograph in one vector operation.

    Uses the same normalized FP32 features and maximum-over-faces rule as
    best_similarity; no approximation, top-k pruning or threshold change.
    """
    vector = np.asarray(query, dtype=np.float32)
    if vector.shape != (DIMENSIONS,) or not np.isfinite(vector).all():
        raise ValueError("Invalid query feature.")
    rows, owners = [], []
    for index, faces in enumerate(groups):
        valid = [face["vector"] for face in faces if len(face.get("vector", [])) == DIMENSIONS]
        if not valid:
            continue
        matrix = np.asarray(valid, dtype=np.float32)
        if not np.isfinite(matrix).all():
            continue
        rows.extend(valid)
        owners.extend([index] * len(valid))
    result = np.full(len(groups), -1.0, dtype=np.float32)
    if rows:
        # A single deterministic reduction avoids BLAS thread startup per photo.
        scores = np.einsum("ij,j->i", np.asarray(rows, dtype=np.float32), vector, optimize=False)
        np.maximum.at(result, np.asarray(owners), scores)
    scores = result.tolist()
    if threshold is not None:
        # Preserve legacy cutoff decisions even at FP32 rounding boundaries.
        for index, score in enumerate(scores):
            if abs(score - threshold) <= 1e-6:
                scores[index] = best_similarity(query, groups[index])
    return scores
