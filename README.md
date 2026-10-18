# Unreal Engine Skills for Codex

[简体中文](README.zh-CN.md)

A community Codex adaptation of [Epic Games' Unreal Engine skills](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin).
Not an official Epic Games or OpenAI release. Original MIT copyright and Git history are preserved.

This plugin teaches Codex to use **Unreal Engine's official MCP server and ToolsetRegistry**.
It does not include Unreal Engine, the engine-side plugins, or a replacement MCP server.

| Skill | Use it for |
| --- | --- |
| `unreal-mcp` | Connect to, inspect, and operate a live Unreal Editor; diagnose connections |
| `create-toolset` | Author or extend C++/Python tools registered with ToolsetRegistry |
| `unreal-skill` | Author Unreal's in-editor Agent Skills (Python classes or UAssets) |

## Requirements

- A local Codex client supporting Skills and MCP; marketplace installation also requires plugin support.
- An engine containing `ModelContextProtocol` and `AllToolsets` (or the specific toolset plugins you need).
- A running editor and MCP server for live operations.
- Python **3.11+** for the optional configuration helper/development checks; manual MCP setup needs no Python.

There is no verified universal minimum UE version. See [validation evidence](docs/VALIDATION.md) for tested builds.

## Install

In a supporting Codex CLI:

```sh
codex plugin marketplace add Idris173/unreal-engine-skills-for-codex-plugin
codex plugin add unreal-engine-skills-for-codex@unreal-codex
```

For a local checkout, replace the first command with:

```powershell
codex plugin marketplace add "H:\Unreal-Skill\unreal-engine-skills-for-codex-plugin"
```

The desktop marketplace label is **Unreal Codex Community**. If your CLI lacks `plugin add`, install through
the desktop plugin directory after registering the marketplace. Start a fresh chat if the skills do not appear.
Avoid installing a second standalone copy of the same skills.

The package provides a portable `plugin.json` and a `.codex-plugin/plugin.json` compatibility manifest.
It does **not** automatically register a fixed MCP endpoint or run a lifecycle hook.

## Connect an editor

Enable `ModelContextProtocol` and `AllToolsets` in the project editor, restarting if requested.
Run `ModelContextProtocol.StartServer` in the UE console; the default is `http://127.0.0.1:8000/mcp`.
For an occupied port, use `ModelContextProtocol.StartServer <free-port>`.
Choose **one** configuration route after checking existing connections:

**Project configuration:** run this in the UE console:

```text
ModelContextProtocol.GenerateClientConfig Codex
```

Installed builds write `.codex/config.toml` beside the `.uproject`; source builds write at the workspace root
beside `Engine/`. Codex loads project configuration only in trusted projects. The generator refuses to overwrite
existing TOML. To preview an addition from this checkout:

```powershell
python scripts/configure_mcp.py --config "F:\MyProject\.codex\config.toml" --url "http://127.0.0.1:8000/mcp"
```

Add `--apply` to write. The helper backs up an existing file, preserves unrelated text/comments, validates TOML,
and refuses conflicting definitions. Identical entries remain unchanged. It checks only the selected file;
inspect other config scopes and installed connectors for duplicates. Edit an existing entry deliberately when
changing its port. Configs with custom ACLs/extended attributes should be merged manually.

**User configuration:** alternatively use Codex's own writer:

```sh
codex mcp add unreal-mcp --url http://127.0.0.1:8000/mcp
```

This writes user configuration. Do not also register a duplicate project connection or proxy for the same editor.
With multiple editors, identify the intended instance and use distinct endpoints with appropriate project scope.

## Verify

`codex mcp list` proves configuration, not live access. In a fresh chat:

> Use $unreal-mcp to inspect the current level and list a few actors without modifying the project.

The skill uses `list_toolsets → describe_toolset → call_tool`, or advertised native tools when search mode is off.
Check the returned project/editor information before changes. Asset creation, saving, and readback after restart
are separate evidence levels.

See [setup](skills/unreal-mcp/references/setup.md) and [operations](skills/unreal-mcp/references/operations.md).
Proxy automation is outside v0.1: do not pass TOML to the upstream proxy's `--mcp-json` installer.
The core plugin needs no Bash; [Python session context](docs/OPTIONAL_HOOK.md) is an explicit optional setup.

## Develop and package

Use a Git checkout for development (development tools/tests are excluded from the ZIP).
Create a virtual environment, then run:

```sh
python -m pip install -r requirements-dev.txt
python scripts/validate_plugin.py
python -m unittest discover -s tests -v
python scripts/package_plugin.py
```

The deterministic ZIP under `dist/` can be extracted and registered as a local marketplace. It contains skills,
manifests, docs and helpers; it excludes Git, virtual environments, tests and raw editor logs.
CI runs the checks on Windows/Linux with Python 3.11/3.14.

See the [implementation plan](docs/MIGRATION_PLAN.zh-CN.md), [validation record](docs/VALIDATION.md), and
[upstream maintenance notes](UPSTREAM.md). Public plugin-directory submission is a separate follow-up;
a GitHub fork is not a directory listing.

## License and live access

[MIT](LICENSE), including Epic Games' original notice. External UE code/binaries retain their own terms.
MCP tools can change live objects and files. Keep the server on loopback, confirm the intended project, and keep
a recovery point for bulk changes. Installation does not require bypassing Codex permissions.
