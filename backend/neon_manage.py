"""Run Django against a privately saved Neon URL without changing the app's active database.

Use the direct connection for migrations and the pooled connection for runtime checks.
No connection strings or passwords are printed by this wrapper.
"""

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit


def main():
    root = Path(__file__).resolve().parent
    args = sys.argv[1:]
    pooled = "--pooled" in args
    args = [arg for arg in args if arg != "--pooled"]
    name = "neon-pooled-url.txt" if pooled else "neon-direct-url.txt"
    path = root / ".local" / name
    if not path.exists():
        raise SystemExit(f"Save the Neon connection string privately in {path} first.")
    value = path.read_text(encoding="utf-8").strip()
    parsed = urlsplit(value)
    if parsed.scheme not in {"postgres", "postgresql"} or not (parsed.hostname or "").endswith(
        ".neon.tech"
    ):
        raise SystemExit("The private connection file must contain a Neon PostgreSQL URL.")
    env = {**os.environ, "DATABASE_URL": value}
    result = subprocess.run([sys.executable, "manage.py", *args], cwd=root, env=env)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
