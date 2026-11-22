"""Switch the backend to the verified Neon database; keep the prior env file private."""

import shutil
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import set_key

root = Path(__file__).resolve().parent.parent
backend = root / "backend"
private = backend / ".local"
pooled = (private / "neon-pooled-url.txt").read_text(encoding="utf-8").strip()
direct = (private / "neon-direct-url.txt").read_text(encoding="utf-8").strip()
for value in (pooled, direct):
    if not (urlsplit(value).hostname or "").endswith(".neon.tech"):
        raise SystemExit("The connection files must contain Neon PostgreSQL URLs.")
backup = (
    private
    / "backups"
    / ("before-neon-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + ".env")
)
shutil.copy2(backend / ".env", backup)
set_key(backend / ".env", "DATABASE_URL", pooled)
set_key(backend / ".env", "DATABASE_DIRECT_URL", direct)
print(
    "Activated the Neon pooled runtime connection. Previous configuration saved privately."
)
