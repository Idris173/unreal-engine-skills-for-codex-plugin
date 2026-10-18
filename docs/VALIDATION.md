# Validation record

Date: 2026-10-18. Adaptation: **0.1.0**. Upstream: `a6aa73ada02a9fb1f5415bec491f9942c519b297`.

## Package and helpers

Local environment: Windows, Python 3.14.2, PyYAML 6.0.3.

- `python scripts/validate_plugin.py`: passed identity, metadata, skill reference, license and default-package checks.
- `python -m unittest discover -s tests -v`: **38 tests, 36 passed, 2 skipped** on this Windows host.
  Skips: POSIX mode-bit preservation and symlink creation unavailable to this Windows process.
- Config tests cover preview without writes, explicit apply, byte/comment/BOM/CRLF preservation, timestamped
  backup, idempotency, URL/name validation, duplicate/proxy conflicts, invalid TOML, write failures and concurrent changes.
- Context tests cover real project markers, source trees, nested directories, spaces/Unicode and stdin JSON.
- Packaging tests check an allowlist, complete skill resources, reproducible ZIP bytes and validation after extraction.
- The extracted ZIP's configuration helper (preview/apply) and context helper were additionally run in a temporary directory.
- All three skills passed the skill-creator `quick_validate.py` check. UI YAML and relative references were checked.
- Independent scenario review covered custom server names/native catalogs, config scopes, offline tool authoring,
  host-vs-UE skills and uncertain write outcomes. Recovery instructions now require readback before replaying a write.
- Independent code/package review found no remaining blocking defect.

CI is configured for Windows/Linux with Python 3.11/3.14. Its actual results are visible in
[GitHub Actions](https://github.com/Idris173/unreal-engine-skills-for-codex-plugin/actions/workflows/validate.yml).
This file does not equate configured CI coverage with a successful remote run.

## Codex client integration

Client: `codex-cli 0.163.0-alpha.10.2` on Windows. Used a temporary child-process `CODEX_HOME` and an ephemeral
app-server thread; the user's real Codex configuration and plugin installation were not changed.

1. Registered the local marketplace with `codex plugin marketplace add`.
2. Installed `unreal-engine-skills-for-codex@unreal-codex`; the client reported version 0.1.0, installed and enabled.
3. `skills/list` returned all three enabled plugin-namespaced skills with no package load failure.
4. The configuration helper appended the test endpoint while retaining the temporary plugin settings.
5. Codex's actual MCP client reported `connected` and discovered `list_toolsets`, `describe_toolset`, `call_tool`.
6. Through app-server `mcpServer/tool/call`, discovered the toolsets/schema and invoked the current-level query.
   It returned the live test project's level successfully.

This verifies installation, runtime skill discovery and Codex-native MCP calls. It is not a desktop UI inspection
or a benchmark of automatic model skill selection. The temporary home emitted a PATH-alias warning because it
was under the OS temp directory; installation/discovery/calls succeeded without those helper aliases.

## Unreal integration and asset persistence

Engine: **5.8.3, CL 58210709**, Windows installed build. Official ModelContextProtocol, ToolsetRegistry and
AllToolsets binaries were present. A user-designated test project was launched with:

```text
-EnablePlugins=ModelContextProtocol,AllToolsets
-ModelContextProtocolStartServer
-ModelContextProtocolPort=18765
```

The isolated test used `http://127.0.0.1:18765/mcp` and negotiated MCP `2025-11-25`.
Across the native HTTP persistence test, 26 requests completed (24 HTTP 200, two notification HTTP 202),
with no transport errors. A second session was established after editor restart.

- Discovered 55 toolsets and read their schemas. Registered names included module-qualified prefixes.
- Successfully queried the active level and actors through the real editor tools.
- Created one MaterialParameterCollection in a unique `/Game/__CodexPluginSmoke/Session_.../` directory.
- Saved only that explicit asset; confirmed its file existed (1,230 bytes) and `is_dirty` was false.
- Closed the test editor normally, restarted it, rediscovered tools and loaded the saved asset.
- The asset SHA-256 before/after restart matched:
  `41f1e3d3e67c980847035e36698af1761df83c4b02360d556aca8dbb19f97719`.
- Deleted only the test asset using the native tool and removed its newly created empty directories.
- The `.uproject` and `DefaultEngine.ini` hashes stayed unchanged; existing unrelated editor processes were not targeted.
- All dedicated test editor processes closed normally, and test port 18765 was released after the Codex client check.

The engine did not advertise LiveCodingToolset in this setup, confirming why the adapted skills must discover
capabilities rather than require that tool. The engine's ProgrammaticToolset is a restricted tool-orchestration
environment; this adaptation does not assume unrestricted Python execution.

## Observed limits

- AllToolsets caused GameFeatures startup errors about a missing GameFeatureData Asset Manager rule in the test project.
  They did not prevent the verified MCP/asset operations. Project settings were not changed to suppress them.
  Projects that do not need all domains can enable the required individual toolset plugins.
- No proxy was present in this engine installation; proxy setup/recovery was not tested.
- Only Windows UE 5.8.3 was exercised live. No broad Blueprint/Niagara/Control Rig/compilation domain coverage is claimed.
- No screenshot-based visual acceptance was performed. The test asset was a parameter collection, not a rendered effect.
- The optional context helper was tested as a program; automatic hook activation/trust was not installed in the user's profile.
- The config helper inspects one file, does not resolve DNS aliases, and preserves mode bits rather than custom ACLs/xattrs.
  External writers must be stopped while applying; optimistic rechecks cannot eliminate a last-instant noncooperating write.
- Public plugin-directory submission is outside this release's scope.

Raw RPC traces, local installation paths, editor logs and temporary profiles are excluded from Git and distributable packages.
