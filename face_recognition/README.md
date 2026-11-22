# Event photo face search

PIXEL now has a local CPU face-detection, alignment and similarity pipeline. The app calls Django; a private background worker loads the engine from this directory. No selfie or event original is sent to an external recognition API.

```text
face_recognition/
  app/engine.py         Bounded decode, quality checks, YuNet, alignment, SFace, exact cosine matching
  models/manifest.json  Pinned checksums, model versions, dimensions and license sources
  download_models.py    Explicit, checksum-verified setup; never runs implicitly during inference
  evaluate.py           Held-out labeled-pair precision/recall and false-accept evaluation
```

`backend/apps/face_search/` owns durable jobs, event-scoped index records, authorization, result delivery and retention. `manage.py run_face_worker` runs one leased worker per `FACE_WORKER_NODE_ID`, prioritizes that machine's searches, and warms shared gallery indexes between jobs. Setup gives every local clone a distinct ID because selfie files are local to its API host. Readiness, claims, cancellation and local cleanup are scoped to that machine; embeddings remain shared. A separate FastAPI server is unnecessary for this local deployment; the engine boundary permits later process/service separation.

The live Neon PostgreSQL database stores each gallery face in a typed `vector(128)` row with an HNSW index. Warm searches read index metadata in bulk and perform an exact threshold query in pgvector, preserving all qualifying photos without an approximate top-k cutoff. SQLite development retains the exact FP32 batch path. Progress and cancellation checks run per 64 photos. Only new or changed originals are downloaded and indexed; the model and resolution settings are unchanged. Queue polling runs every 250 ms while idle, with index scans and cleanup on separate schedules. Run `manage.py benchmark_face_search` for a read-only comparison against the FP32 baseline; this excludes selfie upload and detection latency. See [live database verification](../docs/live-database.md).

Run `backend/.venv/Scripts/python.exe face_recognition/download_models.py` from the workspace after installing backend dependencies, then `scripts/start-backend.ps1`. The script starts Django, gallery synchronization and the face worker. `scripts/start-face-worker.ps1 -Restart` reloads only face inference after code/model changes. Logs are in ignored `backend/.local/faces.*.log`.

Gallery searches accept a still JPEG/PNG/WebP up to 5 MB and explicit one-use consent. Exactly one sufficiently large, sharp detected query face is required. Camera MPO/JPEG event originals use their primary frame. Gallery originals are bounded to 32 MB / 50 MP, oriented and resized to a maximum 2600 px edge; all qualifying faces are indexed separately. Every result is deduplicated by photo and rechecks current event visibility, availability and source revision. The ordinary publication DTO preserves save/download/previous/next behavior.

Selfies are held only in ignored server temporary storage until the worker reads them, then deleted even on failures; query vectors remain in worker memory only. Cancellation removes results and pending uploads. Jobs expire after the configured timeout (120 minutes by default, allowing initial indexing of large event folders); completed result references expire after 15 minutes. Worker cleanup removes expired artifacts and embeddings of unpublished/unavailable media. Gallery embeddings persist for reuse; they are not linked to person names/accounts. Deployment still needs the college's participant notices and takedown/retention policy.

**Accuracy is not yet calibrated on this college's photographs.** The default cosine cutoff is 0.50, stricter than OpenCV's 0.363 demonstration cutoff; this favors precision but can miss profiles, occlusions and small faces. It is not an accuracy guarantee. Use separate photos of the same person and different-person examples across lighting/poses, never identical-file self-matches, to evaluate:

```powershell
backend/.venv/Scripts/python.exe face_recognition/evaluate.py private_data/pairs.csv --output backend/.local/face-evaluation.json
```

CSV columns: `first,second,same`, paths relative to the CSV, `same` is 1 or 0. The report contains aggregate metrics only. Set `FACE_MATCH_THRESHOLD` on the backend and restart after selecting a measured operating point. Do not lower it just to force a desired match.

Verification includes authorization, one active search per user, consent/upload limits, result source changes, cancellation, expiry, cached index reuse, matching math and the actual pinned detector's no-face handling. Live event indexing is running. A consented real-selfie end-to-end check, held-out accuracy evaluation and Android/device checks remain required before claiming production accuracy.
