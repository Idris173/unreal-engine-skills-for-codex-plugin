from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "configure_mcp.py"
SPEC = importlib.util.spec_from_file_location("configure_mcp", SCRIPT)
mcp = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mcp
SPEC.loader.exec_module(mcp)


class ConfigureMcpTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="unreal mcp 配置 ")
        self.root = Path(self.directory.name)
        self.path = self.root / "项目 空格" / ".codex" / "config.toml"

    def tearDown(self):
        # Windows requires the read-only bit to be cleared before deleting files.
        for path in self.root.rglob("*"):
            if path.is_file():
                path.chmod(stat.S_IREAD | stat.S_IWRITE)
        self.directory.cleanup()

    def write(self, content: bytes):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(content)

    def parsed(self):
        return tomllib.loads(self.path.read_bytes().decode("utf-8-sig"))

    def test_preview_missing_file_does_not_create_directories(self):
        plan = mcp.build_plan(self.path)
        self.assertTrue(plan.changed)
        self.assertFalse(self.path.parent.exists())
        self.assertEqual(tomllib.loads(plan.content.decode())["mcp_servers"]["unreal-mcp"], {"url": mcp.DEFAULT_URL})

    def test_apply_new_file_and_repeat_is_noop(self):
        self.assertIsNone(mcp.apply_plan(mcp.build_plan(self.path)))
        original = self.path.read_bytes()
        before = self.path.stat()
        second = mcp.build_plan(self.path)
        self.assertFalse(second.changed)
        self.assertIsNone(mcp.apply_plan(second))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(self.path.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(list(self.path.parent.glob("*.bak.*")), [])

    def test_existing_bytes_comments_and_values_are_preserved_with_backup(self):
        original = (
            b'# Keep this comment\nmodel = "chosen-model"\n\n'
            b'[mcp_servers.other]\ncommand = "tool" # Existing comment\n'
            b'args = ["--option"]\n[mcp_servers.other.env]\nMODE = "local"\n'
        )
        self.write(original)
        plan = mcp.build_plan(self.path)
        self.assertEqual(self.path.read_bytes(), original)
        backup = mcp.apply_plan(plan)
        self.assertEqual(backup.read_bytes(), original)
        self.assertTrue(self.path.read_bytes().startswith(original))
        parsed = self.parsed()
        self.assertEqual(parsed["model"], "chosen-model")
        self.assertEqual(parsed["mcp_servers"]["other"]["env"], {"MODE": "local"})
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_utf8_bom_and_crlf_are_retained(self):
        original = b'\xef\xbb\xbf# comment\r\nmodel = "m"\r\n'
        self.write(original)
        mcp.apply_plan(mcp.build_plan(self.path))
        result = self.path.read_bytes()
        self.assertTrue(result.startswith(original))
        self.assertNotIn(b"\n", result.replace(b"\r\n", b""))
        self.assertEqual(self.parsed()["model"], "m")

    def test_no_final_newline_is_handled(self):
        self.write(b'model = "m" # no final newline')
        mcp.apply_plan(mcp.build_plan(self.path))
        self.assertIn("unreal-mcp", self.parsed()["mcp_servers"])

    def test_bom_only_file_is_valid_and_retained(self):
        self.write(b"\xef\xbb\xbf")
        mcp.apply_plan(mcp.build_plan(self.path))
        self.assertTrue(self.path.read_bytes().startswith(b"\xef\xbb\xbf[mcp_servers."))
        self.assertIn("unreal-mcp", self.parsed()["mcp_servers"])

    def test_semantically_equal_url_and_explicit_enabled_are_noop(self):
        self.write(b'[mcp_servers.unreal-mcp]\nurl = "HTTP://LOCALHOST:80/mcp"\nenabled = true\n')
        self.assertFalse(mcp.build_plan(self.path, "http://localhost/mcp").changed)

    def test_same_name_different_definitions_rejected(self):
        for definition in (
            'url = "http://127.0.0.1:9000/mcp"',
            f'url = "{mcp.DEFAULT_URL}"\nenabled = false',
            f'url = "{mcp.DEFAULT_URL}"\nstartup_timeout_sec = 60',
            'command = "proxy"',
        ):
            with self.subTest(definition=definition):
                original = f"[mcp_servers.unreal-mcp]\n{definition}\n".encode()
                self.write(original)
                with self.assertRaisesRegex(mcp.ConfigError, "different definition"):
                    mcp.build_plan(self.path)
                self.assertEqual(self.path.read_bytes(), original)

    def test_enabled_proxy_is_rejected_even_when_direct_server_matches(self):
        self.write(
            f'[mcp_servers.unreal-mcp]\nurl = "{mcp.DEFAULT_URL}"\n'
            '[mcp_servers.unreal-mcp-proxy]\ncommand = "proxy"\n'.encode()
        )
        with self.assertRaisesRegex(mcp.ConfigError, "enabled 'unreal-mcp-proxy'"):
            mcp.build_plan(self.path)

    def test_disabled_proxy_is_retained(self):
        self.write(b'[mcp_servers.unreal-mcp-proxy]\ncommand = "proxy"\nenabled = false\n')
        mcp.apply_plan(mcp.build_plan(self.path))
        self.assertFalse(self.parsed()["mcp_servers"]["unreal-mcp-proxy"]["enabled"])

    def test_enabled_duplicate_endpoint_is_rejected(self):
        self.write(b'[mcp_servers.existing]\nurl = "HTTP://LOCALHOST:80/mcp"\n')
        with self.assertRaisesRegex(mcp.ConfigError, "already uses this endpoint"):
            mcp.build_plan(self.path, "http://localhost/mcp")

    def test_disabled_duplicate_endpoint_is_allowed(self):
        self.write(f'[mcp_servers.old]\nurl = "{mcp.DEFAULT_URL}"\nenabled = false\n'.encode())
        self.assertTrue(mcp.build_plan(self.path).changed)

    def test_invalid_toml_and_invalid_utf8_are_rejected_without_writes(self):
        for original in (b"[broken", b"model = 1\nmodel = 2\n", b"\xff"):
            with self.subTest(original=original):
                self.write(original)
                with self.assertRaisesRegex(mcp.ConfigError, "valid UTF-8 TOML"):
                    mcp.build_plan(self.path)
                self.assertEqual(self.path.read_bytes(), original)
                self.assertEqual(list(self.path.parent.glob("*.bak.*")), [])

    def test_invalid_mcp_structures_are_rejected(self):
        for original in (
            b'mcp_servers = "bad"\n',
            b'[mcp_servers]\nother = 42\n',
            b'[mcp_servers.other]\nenabled = "false"\n',
        ):
            with self.subTest(original=original):
                self.write(original)
                with self.assertRaises(mcp.ConfigError):
                    mcp.build_plan(self.path)

    def test_inline_parent_table_is_rejected_and_preserved(self):
        original = b'mcp_servers = { other = { command = "tool" } }\n'
        self.write(original)
        with self.assertRaisesRegex(mcp.ConfigError, "cannot be appended safely"):
            mcp.build_plan(self.path)
        self.assertEqual(self.path.read_bytes(), original)

    def test_safe_dotted_keys_can_be_extended(self):
        self.write(b'mcp_servers.other.command = "tool"\n')
        mcp.apply_plan(mcp.build_plan(self.path))
        self.assertEqual(self.parsed()["mcp_servers"]["other"]["command"], "tool")

    def test_valid_loopback_urls(self):
        for url in (
            "http://127.0.0.1:8000/mcp", "https://localhost/mcp", "http://[::1]:8000/mcp",
            "http://127.1.2.3/mcp", "http://localhost/路径?key=value", "http://localhost/",
        ):
            with self.subTest(url=url):
                self.assertTrue(mcp.build_plan(self.path, url).changed)

    def test_unsafe_urls_are_rejected(self):
        for url in (
            "https://example.com/mcp", "http://0.0.0.0/mcp", "http://192.168.0.1/mcp",
            "ftp://localhost/mcp", "file:///tmp/mcp", "http://user:pass@localhost/mcp",
            "http://@localhost/mcp", "http://localhost/mcp#", "http://localhost/mcp#fragment",
            "http://localhost:65536/mcp", "http://localhost:0/mcp", "http://localhost:/mcp",
            "http://localhost:invalid/mcp", "http://[::1", "http://[::1%zone]/mcp",
            "http://localhost.example.com/mcp", "http://localhost/mcp\nmalicious=true",
            " http://localhost/mcp", "http://localhost/a b", "", "http:///mcp",
        ):
            with self.subTest(url=url):
                with self.assertRaises(mcp.ConfigError):
                    mcp.build_plan(self.path, url)

    def test_names_are_restricted(self):
        for name in ("", "-bad", "a.b", 'x"]\n[evil', "名称", "a" * 65, "unreal-mcp-proxy"):
            with self.subTest(name=name):
                with self.assertRaises(mcp.ConfigError):
                    mcp.build_plan(self.path, name=name)
        for name in ("ue", "Unreal_5-7", "a" * 64):
            with self.subTest(name=name):
                self.assertTrue(mcp.build_plan(self.path, name=name).changed)

    def test_url_quotes_and_backslashes_cannot_inject_toml(self):
        url = 'http://localhost/mcp?text=";other=1&path=\\value'
        plan = mcp.build_plan(self.path, url)
        self.assertEqual(tomllib.loads(plan.content.decode()), {"mcp_servers": {"unreal-mcp": {"url": url}}})

    def test_changed_file_is_not_overwritten(self):
        self.write(b'model = "old"\n')
        plan = mcp.build_plan(self.path)
        updated = b'model = "new"\n'
        self.path.write_bytes(updated)
        with self.assertRaisesRegex(mcp.ConfigError, "changed since preview"):
            mcp.apply_plan(plan)
        self.assertEqual(self.path.read_bytes(), updated)
        self.assertEqual(list(self.path.parent.glob("*.bak.*")), [])

    def test_newly_created_file_is_not_overwritten(self):
        plan = mcp.build_plan(self.path)
        self.write(b'model = "created elsewhere"\n')
        with self.assertRaisesRegex(mcp.ConfigError, "changed since preview"):
            mcp.apply_plan(plan)
        self.assertEqual(self.parsed()["model"], "created elsewhere")

    def test_change_during_backup_is_detected_before_replace(self):
        self.write(b'model = "old"\n')
        plan = mcp.build_plan(self.path)
        original_backup = mcp._write_backup

        def mutate_after_backup(path, snapshot):
            backup = original_backup(path, snapshot)
            path.write_bytes(b'model = "concurrent"\n')
            return backup

        with mock.patch.object(mcp, "_write_backup", side_effect=mutate_after_backup):
            with self.assertRaisesRegex(mcp.ConfigError, "changed since preview"):
                mcp.apply_plan(plan)
        self.assertEqual(self.parsed()["model"], "concurrent")
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_backup_failure_does_not_modify_original(self):
        original = b'model = "keep"\n'
        self.write(original)
        with mock.patch.object(mcp, "_write_backup", side_effect=PermissionError("backup denied")):
            with self.assertRaisesRegex(mcp.ConfigError, "Cannot apply"):
                mcp.apply_plan(mcp.build_plan(self.path))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_partial_backup_failure_is_cleaned_up(self):
        original = b'model = "keep"\n'
        self.write(original)
        with mock.patch.object(mcp.os, "fsync", side_effect=OSError("backup sync denied")):
            with self.assertRaises(OSError):
                mcp._write_backup(self.path, mcp._read_snapshot(self.path))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob("*.bak.*")), [])

    def test_directory_target_is_rejected(self):
        self.path.mkdir(parents=True)
        with self.assertRaisesRegex(mcp.ConfigError, "regular file"):
            mcp.build_plan(self.path)

    def test_replace_failure_keeps_original_and_backup(self):
        original = b'model = "keep"\n'
        self.write(original)
        with mock.patch.object(mcp.os, "replace", side_effect=PermissionError("replace denied")):
            with self.assertRaisesRegex(mcp.ConfigError, "Cannot apply"):
                mcp.apply_plan(mcp.build_plan(self.path))
        self.assertEqual(self.path.read_bytes(), original)
        backups = list(self.path.parent.glob("*.bak.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_readonly_target_is_not_replaced(self):
        original = b'model = "keep"\n'
        self.write(original)
        self.path.chmod(stat.S_IREAD)
        self.assertTrue(mcp.build_plan(self.path).changed)
        with self.assertRaisesRegex(mcp.ConfigError, "read-only"):
            mcp.apply_plan(mcp.build_plan(self.path))
        self.assertEqual(self.path.read_bytes(), original)

    @unittest.skipIf(os.name == "nt", "Windows exposes only limited chmod mode bits")
    def test_file_mode_is_preserved(self):
        self.write(b'model = "keep"\n')
        self.path.chmod(0o640)
        backup = mcp.apply_plan(mcp.build_plan(self.path))
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o640)

    def test_symlink_target_is_rejected(self):
        self.write(b'model = "keep"\n')
        link = self.root / "linked.toml"
        try:
            link.symlink_to(self.path)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation unavailable")
        with self.assertRaisesRegex(mcp.ConfigError, "symbolic link"):
            mcp.build_plan(link)

    def test_cli_requires_explicit_target_and_is_preview_only_by_default(self):
        environment = dict(os.environ, PYTHONIOENCODING="utf-8")
        missing = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, encoding="utf-8", env=environment)
        self.assertEqual(missing.returncode, 2)
        self.assertIn("--config", missing.stderr)
        preview = subprocess.run(
            [sys.executable, str(SCRIPT), "--config", str(self.path)],
            capture_output=True, text=True, encoding="utf-8", env=environment,
        )
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn("Preview only", preview.stdout)
        self.assertFalse(self.path.parent.exists())

    def test_cli_reports_invalid_toml_without_secrets_or_traceback(self):
        self.write(b'secret = "do-not-print-me"\ninvalid syntax')
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--config", str(self.path), "--apply"],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Error:", result.stderr)
        self.assertNotIn("do-not-print-me", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_apply_custom_server_then_noop(self):
        original = b'model = "keep"\n'
        self.write(original)
        environment = dict(os.environ, PYTHONIOENCODING="utf-8")
        command = [
            sys.executable, str(SCRIPT), "--config", str(self.path), "--apply",
            "--name", "unreal_project", "--url", "http://[::1]:9000/mcp",
        ]
        first = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=environment)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("Backup:", first.stdout)
        self.assertEqual(self.parsed()["mcp_servers"]["unreal_project"]["url"], "http://[::1]:9000/mcp")
        second = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=environment)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("No files changed", second.stdout)
        backups = list(self.path.parent.glob("*.bak.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
