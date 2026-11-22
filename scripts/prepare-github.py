"""Produce a clean whole-project source folder; never copy a Git history or secret."""

import argparse
import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

SKIP = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".local",
    ".expo",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
    "credentials",
    "private_data",
    "media",
    "staticfiles",
    "dist",
    "web-build",
    ".vscode",
}
EXTENSIONS = {
    ".py",
    ".ps1",
    ".bat",
    ".md",
    ".json",
    ".toml",
    ".lock",
    ".example",
    ".js",
    ".cjs",
    ".ts",
    ".tsx",
    ".css",
    ".html",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".ttf",
    ".otf",
    ".svg",
    ".license",
}
NAMES = {".gitignore", ".gitattributes", ".python-version", ".node-version", "LICENSE"}
ROOTS = {"backend", "frontend", "face_recognition", "docs", "scripts"}


def allowed(relative):
    if any(part in SKIP for part in relative.parts):
        return False
    name = relative.name
    if name.startswith(".env") and name != ".env.example":
        return False
    if relative.parts[:2] in {("frontend", "android"), ("frontend", "ios")}:
        return False
    if name in {
        "credentials.json",
        "google-services.json",
        "GoogleService-Info.plist",
    } or name.startswith("client_secret"):
        return False
    return name in NAMES or relative.suffix.lower() in EXTENSIONS


def check_source(path):
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_bytes())
        except (ValueError, UnicodeError):
            data = None
        if isinstance(data, dict):
            if data.get("type") in {"authorized_user", "service_account"}:
                raise ValueError(f"Google credential file blocked: {path.name}")
            if any(data.get(key) for key in ("private_key", "refresh_token", "client_secret")):
                raise ValueError(f"Credential material blocked: {path.name}")
            if any(
                isinstance(data.get(key), dict) and data[key].get("client_secret")
                for key in ["web", "installed"]
            ):
                raise ValueError(f"OAuth client credential file blocked: {path.name}")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError:
        return
    if re.search(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----|AIza[0-9A-Za-z_-]{35}", text):
        raise ValueError(f"Possible private key/API key blocked in {path.name}")
    for uri in re.findall(r"postgres(?:ql)?://[^\s\"'`]+", text):
        if "@" in uri and not re.search(r"PASSWORD|password|YOUR_|example|<|USER", uri):
            raise ValueError(f"Possible database credential blocked in {path.name}")


def prepare(root):
    sources = []

    def walk(directory):
        for item in sorted(directory.iterdir()):
            if item.is_symlink():
                continue
            relative = item.relative_to(root)
            if item.is_dir():
                if item.name not in SKIP and relative.parts[:2] not in {
                    ("frontend", "android"),
                    ("frontend", "ios"),
                }:
                    walk(item)
            elif allowed(relative):
                check_source(item)
                sources.append(item)

    for item in sorted(root.iterdir()):
        if item.is_dir() and item.name in ROOTS:
            walk(item)
        elif item.is_file() and (
            item.name in {"README.md", ".gitignore", ".gitattributes"} or item.suffix == ".bat"
        ):
            check_source(item)
            sources.append(item)
    if not sources:
        raise ValueError("No source files found.")
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    destination = root / ".local" / "github-export" / f"PIXEL-{stamp}-{uuid4().hex[:6]}"
    destination.mkdir(parents=True, exist_ok=False)
    for source in sources:
        target = destination / source.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (destination / "SOURCE-MANIFEST.json").write_text(
        json.dumps(
            [str(source.relative_to(root)).replace("\\", "/") for source in sources], indent=2
        ),
        encoding="utf-8",
    )
    print(f"Prepared {len(sources)} source files in:\n{destination}")
    print(
        "Original working files and frontend Git history were not changed. Review this folder, then publish it as a PRIVATE repository."
    )
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    try:
        prepare(args.root.resolve())
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc))
