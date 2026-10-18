# Operations: Console Commands, Settings, Recovery

Read this for missing tools, port conflicts, stale catalogs, or non-default server settings. Check the actual engine implementation and runtime schema if they differ from the upstream baseline documented here.

## Unreal console commands

Run these in the Unreal Editor console, not in the Codex shell:

| Command | Purpose |
| --- | --- |
| `ModelContextProtocol.StartServer [port]` | Start the server, optionally overriding its port. |
| `ModelContextProtocol.StopServer` | Stop the server when an authorized recovery requires it. |
| `ModelContextProtocol.RefreshTools` | Re-register loaded toolsets after registration changes. Enabling a new plugin may still require an editor restart. |
| `ModelContextProtocol.GenerateClientConfig Codex` | Generate a new `.codex/config.toml`; refuses to overwrite an existing TOML file. |

For a changed port or path, update the existing Codex entry deliberately. Do not delete existing TOML or use a JSON config writer to refresh it. See [setup.md](setup.md) for scope and merge options.

## Tool-search mode

`bEnableToolSearch` on `UModelContextProtocolSettings` controls the catalog:

- **`True` (upstream default):** `tools/list` advertises `list_toolsets`, `describe_toolset`, and `call_tool`. Discover schemas and dispatch individual toolset tools through `call_tool`.
- **`False`:** toolset tools are native MCP tools with schemas in the catalog. Use those actual names and schemas directly; do not assume the meta-tools exist in this mode.

The override lives alongside `bAutoStartServer` in the per-user editor settings:

```ini
[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]
bEnableToolSearch=False
```

Changing this setting is not a routine solution for missing tools. Check connection state and plugin registration first.

## Direct HTTP recovery

1. Inspect Codex's loaded MCP connection and its configured endpoint. `codex mcp list` and `codex mcp get <server-name>` help inspect configuration; they do not prove a live Unreal session. Check project trust and effective config scope when a valid project file appears ignored.
2. Inspect the intended editor's Output Log, startup arguments, and server settings. With multiple editors, identify which process owns the configured port.
3. Resolve the specific failure (server stopped, port collision, missing plugin, or wrong path). Retry a read-only tool call once the server is ready. If Codex retains a failed/stale connection, use its available reconnect/reload controls or start a new session.

Keep recovery bounded: repeated identical failures call for new evidence, not an endless retry loop. A mutation that timed out may already have completed. After reconnecting, query the affected asset/state before deciding whether to replay it; do not blindly retry a create, delete, or other non-idempotent operation. Restarting the editor or terminating processes can affect unsaved work; use the existing authorization and preserve that work first.

## Existing proxy connections

Proxy behavior is engine-build dependent; this adaptation has not validated a Codex proxy installation. For an already configured proxy, inspect the build's `Extras/Proxy/README.md` and its actual STDIO command/arguments.

- `unreal_mcp_status`, if present, reports an initialized upstream session, not a fresh reachability check.
- The catalog can be cached. Confirm recovery with a read-only Unreal tool call.
- With no cached catalog or upstream session, the proxy may expose only status, then emit `notifications/tools/list_changed` after recovery. Codex must refresh the catalog; reconnect/reload or start a new session if it remains stale.
- Killing the proxy closes Codex's STDIO connection. An unrelated new proxy process cannot repair it; the client must reconnect. Do not kill active proxies unless that interruption is within the user's requested recovery.

Inspect proxy stderr, the server startup log, and the configured upstream endpoint if calls still fail. Do not add a second direct connection as an implicit proxy recovery step, and never pass a TOML config to a JSON-only installer.

## Troubleshooting

| Symptom | Next check |
| --- | --- |
| No Unreal tools | Inspect loaded server names, config scopes, project trust, endpoint, and the editor log. Server names may be customized. Distinguish search mode, a native catalog, and proxy status-only mode before diagnosing a stopped editor. |
| "Failed to listen on port" | Identify the port owner. Choose an available port with the authorized server settings, then update the existing Codex URL. Do not stop an unrelated service. |
| Expected toolset is missing | Confirm its plugin exists and is enabled in this engine/project. Refresh registration; honor plugin restart requirements. Do not infer availability from another UE build. |
| Calls hang or fail | Check compilation, level loading, and PIE. Wait for a known in-progress operation, inspect errors, then retry only when state changed. Discover Live Coding support before using it. |
| Live Coding unavailable or insufficient | Use the project's supported build workflow. Coordinate any needed editor restart and preserve unsaved work. |
| `AIAssistantToolset.GetDockedContext` is empty or absent | Docked context depends on an editor-side client integration. A standalone Codex connection does not guarantee it. Use explicit asset paths, selection/query tools, or a focused clarification to identify the target. |
| Conflicting mutation results | Serialize dependent calls and all changes sharing an asset/editor state, including changes by multiple agents. Read back state before continuing. |
