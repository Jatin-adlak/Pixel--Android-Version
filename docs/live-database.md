# PIXEL live database

PIXEL now uses Neon PostgreSQL for application metadata and the `pgvector` extension in the same database for gallery face embeddings. Originals remain in Google Drive. The API and workers currently run on this computer; this database connection does not deploy the backend to public hosting.

- Project: `pixel-production` (`twilight-sound-69171218`), AWS Singapore, free plan.
- Console: https://console.neon.tech/app/projects/twilight-sound-69171218
- Runtime: private pooled `DATABASE_URL` in `backend/.env`.
- Schema operations: private direct `DATABASE_DIRECT_URL`; `backend/neon_manage.py` reads the ignored direct/pooled URL files in `backend/.local` for local administration.
- TLS is required. The database URL and Neon CLI credentials must never go into the frontend, version control, screenshots, or chat.

## Face storage and matching

`PhotoFaceIndex` tracks the source revision, model, quality/indexing failures and face count. Each `FaceEmbedding` stores one normalized FP32 SFace embedding in `vector(128)` and its face bounding box. The index is `face_embedding_hnsw_ip`, an HNSW inner-product index with `m=16` and `ef_construction=128`.

The complete-photo search uses an **exact threshold aggregation** in PostgreSQL instead of an approximate top-k query. It returns every indexed photo with a qualifying face and preserves the maximum-over-faces rule and FP32 cutoff behavior. HNSW is available for nearest-neighbor workloads; the full-results workflow does not sacrifice recall to use it. This is computational equivalence, not proof of real-person recognition accuracy; the existing recognition threshold still needs a consented held-out accuracy evaluation.

The worker sends the temporary query vector as a query parameter and does not store it. Uploaded query photos are still deleted after processing. New or changed Drive photos are indexed once, and stale/unpublished photo indexes cascade-delete their embedding rows. Live PostgreSQL does not retain duplicate embeddings in the legacy JSON cache. SQLite keeps that cache only for offline development and rollback comparison.

## Completed migration and verification

1. Created the live schema and pgvector extension using migration `face_search.0002_vector_embeddings`.
2. Passed 65 backend tests on a separate temporary PostgreSQL test database, including real pgvector operators and index checks.
3. Rehearsed and rolled back the initial data import.
4. Stopped local API/Drive/face writers, then backed up SQLite and exported a consistent snapshot.
5. Imported 3,268 records with an atomic PostgreSQL COPY operation. Compared every imported ID, field and relationship against the snapshot. Preserved users, password hashes, sessions, interactions, publication timestamps and saved content.
6. Verified 2 users, 523 publications (518 gallery photos, 2 posts, 3 moments), 518 photo indexes and 1,734 embeddings. Removed duplicate JSON features from PostgreSQL and reset transferred worker leases.
7. Verified the pooled TLS connection, pgvector 0.8.7, `vector(128)` column and HNSW index. The real gallery benchmark returned the same qualifying photo set as the prior FP32 matcher; the measured vector query was about 0.08 seconds, excluding upload, detection and other request work.
8. Switched `backend/.env` to Neon and restarted the API and both workers.

## Commands

From `backend/`, using its Python environment:

```powershell
.venv\Scripts\python.exe manage.py check_vector_database
.venv\Scripts\python.exe manage.py benchmark_face_search
.venv\Scripts\python.exe neon_manage.py migrate
.venv\Scripts\python.exe neon_manage.py test tests --noinput
```

`neon_manage.py test` creates a separate `test_neondb`; it does not run tests inside the application's live tables. `import_initial_database` is only for an empty, freshly migrated PostgreSQL database and refuses to overwrite application data. Its `--dry-run` option rolls back the complete rehearsal.

## Backups and operation

Consistent SQLite snapshots, the private migration export, and the prior `.env` are in ignored `backend/.local/backups/`. The final export path is recorded in ignored `.local/neon-import-manifest.json`. Keep these backups private because they contain account data and gallery biometrics.

The retained SQLite file is a **pre-cutover snapshot**, not an ongoing replica. Restoring it after live writes requires reconciling the newer PostgreSQL data first. Do not simply switch back and discard live changes.

The API, gallery sync and face worker must all use the same database configuration. Persistent polling workers keep Neon compute active; account for that when scheduling production workers and reviewing free-plan usage. Set up and verify the desired hosted-database recovery policy before treating this as a fully deployed production service.
