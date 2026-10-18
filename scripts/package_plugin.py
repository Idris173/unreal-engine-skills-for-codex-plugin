#!/usr/bin/env python3
"""Build a deterministic ZIP from an explicit allowlist, excluding development data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from validate_plugin import ROOT, validate


def package_files(root: Path) -> list[Path]:
    names = [
        "plugin.json", ".codex-plugin/plugin.json", ".agents/plugins/marketplace.json",
        "LICENSE", "UPSTREAM.md", "README.md", "README.zh-CN.md",
        "scripts/configure_mcp.py", "scripts/session_context.py",
        "docs/OPTIONAL_HOOK.md", "docs/VALIDATION.md", "docs/MIGRATION_PLAN.zh-CN.md",
    ]
    files = [root / name for name in names]
    files += [p for p in (root / "skills").rglob("*") if p.is_file() and p.suffix in (".md", ".yaml")]
    for path in files:
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Missing or unsafe package file: {path}")
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def build(output: Path, root: Path = ROOT) -> Path:
    errors = validate(root)
    if errors:
        raise ValueError("\n".join(errors))
    files = package_files(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            # Normalize source-control checkout line endings for reproducible cross-platform archives.
            archive.writestr(info, path.read_bytes().replace(b"\r\n", b"\n"))
    return output


def main() -> None:
    manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / f"{manifest['name']}-{manifest['version']}.zip")
    args = parser.parse_args()
    print(build(args.output.resolve()))


if __name__ == "__main__":
    main()
