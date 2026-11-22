"""Exercise new-clone setup/export in temporary workspaces, never the real .env."""

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


configure = module("configure_local", "configure-local.py").configure
export = module("prepare_github", "prepare-github.py").prepare


class CloneSetupTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / "backend" / ".local" / "setup-test-workspaces"
        parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "backend").mkdir()
        (self.root / "frontend" / "src").mkdir(parents=True)
        (self.root / "backend" / ".env.example").write_text(
            (ROOT / "backend" / ".env.example").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (self.root / "frontend" / "src" / "index.tsx").write_text(
            "export default null;", encoding="utf-8"
        )

    def test_private_import_creates_distinct_local_keys_and_preserves_existing_config(
        self,
    ):
        private = self.root / "backend" / ".local" / "setup"
        private.mkdir(parents=True)
        database = "postgresql://user:password@example.invalid/pixel"
        (private / "backend.env").write_text(
            f"DATABASE_URL={database}\nDJANGO_SECRET_KEY=owner-key\nFACE_WORKER_NODE_ID=owner-node\nGOOGLE_CLIENT_SECRET=private-example\n",
            encoding="utf-8",
        )
        (private / "drive-oauth.json").write_text(
            json.dumps({"type": "authorized_user", "refresh_token": "example-token"}),
            encoding="utf-8",
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(configure(self.root), 0)
        values = dotenv_values(self.root / "backend" / ".env")
        self.assertEqual(values["DATABASE_URL"], database)
        self.assertNotEqual(values["DJANGO_SECRET_KEY"], "owner-key")
        self.assertNotEqual(values["FACE_WORKER_NODE_ID"], "owner-node")
        self.assertEqual(values["GOOGLE_CLIENT_SECRET"], "private-example")
        self.assertTrue(
            (self.root / "backend" / ".local" / "drive-oauth.json").exists()
        )
        self.assertNotIn(database, output.getvalue())
        first = (self.root / "backend" / ".env").read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(configure(self.root), 0)
        self.assertEqual(first, (self.root / "backend" / ".env").read_bytes())

    def test_missing_database_requests_private_configuration_instead_of_sqlite(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(configure(self.root), 2)
        self.assertTrue((self.root / "backend" / ".env").exists())

    def test_export_includes_all_source_but_no_secrets_history_dependencies_or_weights(
        self,
    ):
        fixtures = {
            "backend/.env": "SECRET=private",
            "frontend/.git/config": "private-history",
            "frontend/node_modules/package/index.js": "installed",
            "backend/credentials/random.json": "private",
            "face_recognition/models/model.onnx": "weights",
            "backend/.local/selfie.query": "private",
            "face_recognition/models/manifest.json": "{}",
            "backend/manage.py": "# source",
            "frontend/package-lock.json": "{}",
        }
        for name, value in fixtures.items():
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(value, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            target = export(self.root)
        self.assertTrue((target / "backend" / "manage.py").exists())
        self.assertTrue((target / "frontend" / "src" / "index.tsx").exists())
        self.assertTrue((target / "backend" / ".env.example").exists())
        for name in fixtures:
            if any(
                key in name
                for key in [
                    ".env",
                    ".git/",
                    "node_modules",
                    "credentials",
                    ".onnx",
                    ".local",
                ]
            ):
                self.assertFalse((target / name).exists(), name)

    def test_unexpected_google_credentials_block_export_before_copying(self):
        (self.root / "backend" / "random-name.json").write_text(
            json.dumps({"type": "service_account", "private_key": "example"}),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "credential file blocked"):
            export(self.root)
        self.assertFalse((self.root / ".local" / "github-export").exists())


if __name__ == "__main__":
    unittest.main()
