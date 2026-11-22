"""Make a consistent SQLite backup and private export for the initial Neon import."""

import json
import os
import sqlite3
import subprocess
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parent.parent
backend = root / "backend"
folder = backend / ".local" / "backups"
folder.mkdir(parents=True, exist_ok=True)
stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
snapshot = folder / f"neon-snapshot-{stamp}.sqlite3"
fixture = folder / f"neon-import-{stamp}.json"
with sqlite3.connect(
    (backend / "db.sqlite3").as_uri() + "?mode=ro", uri=True
) as source:
    if source.execute(
        "SELECT COUNT(*) FROM face_search_facesearchjob WHERE status IN ('queued','processing')"
    ).fetchone()[0]:
        raise SystemExit(
            "Wait for active face searches to finish before taking the migration snapshot."
        )
    with sqlite3.connect(snapshot) as target:
        source.backup(target)
env = {
    **os.environ,
    "DATABASE_URL": "",
    "DJANGO_DEBUG": "true",
    "SQLITE_DATABASE_PATH": str(snapshot),
}
python = backend / ".venv" / "Scripts" / "python.exe"
for command in [
    ["backfill_face_vectors", "--rebuild-local"],
    ["dumpdata", "--exclude", "face_search.faceworkerstate", "--output", str(fixture)],
]:
    subprocess.run(
        [str(python), "manage.py", *command], cwd=backend, env=env, check=True
    )
manifest = {"snapshot": str(snapshot), "fixture": str(fixture)}
(backend / ".local" / "neon-import-manifest.json").write_text(
    json.dumps(manifest), encoding="utf-8"
)
print("Private migration snapshot and export prepared:", fixture.name)
