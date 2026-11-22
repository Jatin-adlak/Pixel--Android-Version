"""Explicit setup only; inference never downloads weights."""

import hashlib
import json
from pathlib import Path

import requests


def main():
    root = Path(__file__).parent / "models"
    manifest = json.loads((root / "manifest.json").read_text())
    for kind in ("detector", "recognizer"):
        model = manifest[kind]
        target = root / model["file"]
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == model["sha256"]:
            print(f"Verified {kind}.")
            continue
        response = requests.get(model["url"], timeout=(10, 180))
        response.raise_for_status()
        if hashlib.sha256(response.content).hexdigest() != model["sha256"]:
            raise RuntimeError(f"{kind} checksum does not match the pinned manifest.")
        target.write_bytes(response.content)
        license_response = requests.get(model["license_url"], timeout=30)
        license_response.raise_for_status()
        (root / f"{kind}.LICENSE").write_text(license_response.text, encoding="utf-8")
        print(f"Installed and verified {kind} ({len(response.content)} bytes).")


if __name__ == "__main__":
    main()
