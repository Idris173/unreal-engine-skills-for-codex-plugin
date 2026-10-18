#!/usr/bin/env python3
"""Optional Codex SessionStart context; never writes configuration or starts UE."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


def find_project_root(cwd: Path) -> Path | None:
    for directory in (cwd, *cwd.parents):
        try:
            if any(path.is_file() for path in directory.glob("*.uproject")) or any(
                (directory / marker).is_file()
                for marker in ("GenerateProjectFiles.bat", "GenerateProjectFiles.sh", "GenerateProjectFiles.command")
            ):
                return directory
        except OSError:
            continue
    return None


def build_context(cwd: Path) -> dict:
    root = find_project_root(cwd.resolve())
    if root is None:
        return {}
    context = (
        "This working directory is inside an Unreal Engine project or engine source tree. "
        "Use Unreal C++/UObject, Slate and UHT conventions where relevant. "
        "Use the unreal-mcp skill for live editor tasks. Check the current MCP connection "
        "and tool schemas before operating on the editor. "
    )
    if (root / ".codex" / "config.toml").is_file():
        context += "A project Codex configuration file exists; its presence does not prove an Unreal connection."
    else:
        context += "Connection settings may be in user or project Codex configuration; inspect them only if setup or diagnosis is needed."
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", type=Path, help="Explicit directory for manual testing; otherwise read hook stdin")
    args = parser.parse_args()
    try:
        if args.cwd is not None:
            cwd = args.cwd
        else:
            payload = json.load(sys.stdin)
            if not isinstance(payload, dict):
                raise ValueError("hook input must be an object")
            cwd = Path(payload.get("cwd") or os.getcwd())
        print(json.dumps(build_context(cwd), ensure_ascii=True))
    except (OSError, ValueError, TypeError) as error:
        print(f"Unreal context skipped: {error}", file=sys.stderr)
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
