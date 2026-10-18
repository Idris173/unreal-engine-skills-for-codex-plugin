from pathlib import Path
import hashlib
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from package_plugin import build
from validate_plugin import validate


class PackageTests(unittest.TestCase):
    def test_package_is_reproducible_and_self_contained(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = build(Path(tmp) / "first.zip")
            second = build(Path(tmp) / "second.zip")
            self.assertEqual(hashlib.sha256(first.read_bytes()).digest(), hashlib.sha256(second.read_bytes()).digest())
            with zipfile.ZipFile(first) as archive:
                names = archive.namelist()
                self.assertIn("LICENSE", names)
                self.assertIn("scripts/configure_mcp.py", names)
                self.assertEqual(len([n for n in names if n.endswith("/SKILL.md")]), 3)
                for name in names:
                    self.assertFalse(name.startswith((".git/", ".venv/", ".test-artifacts/", "tests/", "hooks/")))
                    self.assertNotIn("..", Path(name).parts)
                archive.extractall(Path(tmp) / "unpacked")
            self.assertEqual(validate(Path(tmp) / "unpacked"), [])


if __name__ == "__main__":
    unittest.main()
