# Local inference module

- `engine.py`: pinned-model verification, bounded decoding, orientation, primary MPO/JPEG handling, quality gates, YuNet detection, SFace alignment/embedding and exact cosine similarity.
- Models are loaded by the background worker. The public API validates image bounds and queues work; it does not expose vectors or anonymous inference.

The selfie flow rejects no-face and multiple-face images with actionable errors; indexing supports multiple faces per event photograph. Jobs and photo features record the manifest model/preprocessing version. Django orchestration lives in `backend/apps/face_search/`. A separate FastAPI process is a future scaling option, not a dependency of this local implementation.

Prefer passing bounded image bytes over caller-controlled arbitrary URLs. If URL fetching is introduced, restrict it to authorized storage origins and enforce network, redirect, size and timeout controls. Never accept arbitrary filesystem paths from public users.
