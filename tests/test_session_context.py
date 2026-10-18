from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "session_context.py"
spec = importlib.util.spec_from_file_location("session_context", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SessionContextTests(unittest.TestCase):
    def test_no_context_for_unrelated_directory_or_bare_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Engine").mkdir()
            (root / "NotAProject.uproject").mkdir()
            self.assertEqual(module.build_context(root), {})

    def test_nested_project_unicode_and_spaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "游戏 Project"
            nested = root / "Source" / "Module"
            nested.mkdir(parents=True)
            (root / "Game.uproject").write_text("{}")
            result = module.build_context(nested)
            context = result["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Unreal", context)
            self.assertNotIn("GenerateClientConfig ClaudeCode", context)
            self.assertIn("user or project", context)
            self.assertEqual(module.find_project_root(nested), root)

    def test_source_tree_and_project_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "Engine" / "Source" / "Runtime" / "Engine"
            nested.mkdir(parents=True)
            (root / "GenerateProjectFiles.bat").touch()
            (root / ".codex").mkdir()
            (root / ".codex" / "config.toml").write_text("model = 'example'")
            self.assertEqual(module.find_project_root(nested), root)
            self.assertIn("does not prove", module.build_context(nested)["hookSpecificOutput"]["additionalContext"])

    def test_cli_uses_hook_cwd_and_handles_malformed_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Game.uproject").touch()
            result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"cwd": tmp}), text=True, capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn("hookSpecificOutput", json.loads(result.stdout))
        result = subprocess.run([sys.executable, str(SCRIPT)], input="{bad", text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), {})


if __name__ == "__main__":
    unittest.main()
