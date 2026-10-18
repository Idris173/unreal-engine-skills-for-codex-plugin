#!/usr/bin/env python3
"""Validate the package's identity, paths, skill metadata and distribution boundary."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]


def validate(root: Path = ROOT) -> list[str]:
    errors = []
    try:
        portable = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
        compatibility = json.loads((root / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((root / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        for field in ("name", "version", "author", "repository", "license"):
            if portable.get(field) != compatibility.get(field):
                errors.append(f"Manifest mismatch: {field}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", portable["name"]):
            errors.append("Invalid plugin name")
        if not re.fullmatch(r"\d+\.\d+\.\d+", portable["version"]):
            errors.append("Version must be a stable semantic version")
        extension = portable["extensions"]["com.openai"]
        if extension.get("interface") != compatibility.get("interface"):
            errors.append("OpenAI presentation metadata differs between manifests")
        if not extension.get("requires_local_executor") or not compatibility.get("requires_local_executor"):
            errors.append("The Unreal integration requires a local executor")
        if compatibility.get("skills") != "./skills/":
            errors.append("Compatibility skills path must point to ./skills/")
        entries = marketplace["plugins"]
        if len(entries) != 1 or entries[0]["name"] != portable["name"]:
            errors.append("Marketplace must reference this plugin exactly once")
        if entries[0]["source"] != {"source": "local", "path": "./"}:
            errors.append("Marketplace must resolve the package root")
        for manifest in (extension, compatibility):
            if any(key in manifest for key in ("hooks", "apps", "mcpServers")):
                errors.append("Default package must not auto-register hooks or MCP connections")
    except (OSError, ValueError, KeyError, TypeError) as error:
        errors.append(f"Manifest error: {error}")

    expected = {"unreal-mcp", "create-toolset", "unreal-skill"}
    paths = list((root / "skills").glob("*/SKILL.md"))
    if {path.parent.name for path in paths} != expected:
        errors.append("Package must contain the three adapted upstream skills")
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
            parts = text.split("---", 2)
            if len(parts) != 3 or parts[0].strip():
                raise ValueError("missing YAML frontmatter")
            metadata = yaml.safe_load(parts[1])
            if metadata.get("name") != path.parent.name:
                errors.append(f"{path}: name differs from directory")
            description = metadata.get("description")
            if not isinstance(description, str) or not description.strip() or len(description) > 1024:
                errors.append(f"{path}: description must be 1-1024 characters")
            for link in re.findall(r"\]\(([^)]+)\)", text):
                if "://" not in link and not link.startswith("#"):
                    target = (path.parent / link.split("#", 1)[0]).resolve()
                    if not target.is_relative_to(root.resolve()) or not target.exists():
                        errors.append(f"{path}: missing or external package reference {link}")
            ui_path = path.parent / "agents/openai.yaml"
            if ui_path.exists():
                ui = yaml.safe_load(ui_path.read_text(encoding="utf-8"))
                prompt = ui.get("interface", {}).get("default_prompt", "")
                if prompt and "$" + path.parent.name not in prompt:
                    errors.append(f"{ui_path}: default prompt must mention the skill")
        except (OSError, ValueError, TypeError, AttributeError, yaml.YAMLError) as error:
            errors.append(f"{path}: {error}")
    for forbidden in ("hooks/hooks.json", ".claude-plugin/plugin.json", ".mcp.json", "mcp.json"):
        if (root / forbidden).exists():
            errors.append(f"Unexpected active client configuration: {forbidden}")
    license_text = (root / "LICENSE").read_text(encoding="utf-8")
    if "Copyright (c) 2026 Epic Games, Inc." not in license_text or "MIT License" not in license_text:
        errors.append("Upstream license notice is missing")
    return errors


if __name__ == "__main__":
    problems = validate()
    for problem in problems:
        print(problem, file=sys.stderr)
    print("Package validation passed." if not problems else f"{len(problems)} validation error(s).")
    raise SystemExit(bool(problems))
