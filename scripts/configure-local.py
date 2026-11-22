"""Create portable local configuration without printing or committing secrets."""

import argparse
import json
import secrets
import shutil
import uuid
from pathlib import Path

from dotenv import dotenv_values


def configure(root):
    backend = root / "backend"
    private = backend / ".local" / "setup"
    target = backend / ".env"
    fresh = not target.exists()
    values = dict(dotenv_values(backend / ".env.example"))
    if fresh and (private / "backend.env").is_file():
        values.update(dotenv_values(private / "backend.env"))
    if not fresh:
        values.update(dotenv_values(target))
    changed = fresh
    if fresh or values.get("DJANGO_SECRET_KEY") in {
        None,
        "",
        "generate-a-long-random-secret-locally",
    }:
        values["DJANGO_SECRET_KEY"] = secrets.token_urlsafe(48)
        changed = True
    if fresh or not values.get("FACE_WORKER_NODE_ID"):
        values["FACE_WORKER_NODE_ID"] = uuid.uuid4().hex
        changed = True
    if fresh:
        values.update(
            DJANGO_DEBUG="true",
            DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,testserver",
            BACKEND_URL="http://localhost:8000",
            FRONTEND_URL="http://localhost:8081",
            CORS_ALLOWED_ORIGINS="http://localhost:8081",
        )
        # Absolute paths from another computer are not portable.
        values["SQLITE_DATABASE_PATH"] = ""
        values["GOOGLE_DRIVE_CREDENTIALS_FILE"] = ""
    local = backend / ".local"
    local.mkdir(parents=True, exist_ok=True)
    for source, destination in [
        ("drive-oauth.json", "drive-oauth.json"),
        ("service-account.json", "google-service-account.json"),
    ]:
        original, installed = private / source, local / destination
        if original.is_file() and not installed.exists():
            data = json.loads(original.read_text(encoding="utf-8-sig"))
            expected = "authorized_user" if source == "drive-oauth.json" else "service_account"
            if data.get("type") != expected:
                raise ValueError(f"{source} is not the expected Google credential type.")
            shutil.copyfile(original, installed)
        if (
            source == "service-account.json"
            and installed.is_file()
            and not values.get("GOOGLE_DRIVE_CREDENTIALS_FILE")
        ):
            values["GOOGLE_DRIVE_CREDENTIALS_FILE"] = ".local/google-service-account.json"
            changed = True
    if changed:
        text = "# Private local settings. Never commit this file.\n" + "".join(
            f"{key}={json.dumps(value or '', ensure_ascii=False)}\n"
            for key, value in values.items()
        )
        temporary = target.with_name(".env.setup-tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(target)
    frontend_env = root / "frontend" / ".env"
    if not frontend_env.exists():
        frontend_env.write_text(
            "EXPO_PUBLIC_API_URL=http://localhost:8000\nEXPO_PUBLIC_WEB_URL=http://localhost:8081\n",
            encoding="utf-8",
        )
    if not (values.get("DATABASE_URL") or "").startswith(("postgres://", "postgresql://")):
        print(
            "Add the privately supplied Neon DATABASE_URL to backend/.env, then rerun Setup PIXEL.bat."
        )
        print("Or, before first setup, place the private backend.env in backend/.local/setup/.")
        return 2
    print("Private configuration ready. A machine-specific face-worker ID is configured.")
    if not (local / "drive-oauth.json").exists():
        print(
            "Drive uploads require the Pixel account's local authorization. See docs/friend-setup.md."
        )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    try:
        raise SystemExit(configure(args.root.resolve()))
    except (OSError, ValueError):
        raise SystemExit(
            "Local configuration could not be prepared. Check the private input files; their contents were not printed."
        )
