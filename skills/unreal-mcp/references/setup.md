# First-Time MCP Server Setup for Codex

Use this reference to configure direct HTTP access from Codex to Epic's Unreal MCP server. The plugin package contains skills, not a static MCP connection or the UE server binaries. First inspect existing connections in the current session and the intended configuration scope; a missing project config does not mean there is no user-level connection.

Identify the actual `.uproject` and engine build. Confirm that the engine includes `ModelContextProtocol` and the requested toolset plugins before editing configuration. This repository does not establish a minimum supported UE version. If the plugins are absent, report the missing components and stop that setup path; do not substitute another MCP backend without the user's direction.

## 1. Enable the UE plugins

Within the user's setup request, update the identified `.uproject` `Plugins` array while preserving unrelated entries:

```json
{
  "Name": "ModelContextProtocol",
  "Enabled": true
},
{
  "Name": "AllToolsets",
  "Enabled": true
}
```

`ModelContextProtocol` provides the server/transport. `AllToolsets` is the upstream editor-only aggregator and must be enabled explicitly; alternatively, enable only the individual toolset plugins required by the project. A running server without toolset plugins does not supply editor operations. Follow the engine's restart requirements after changing plugin enablement.

## 2. Start the server

For the current editor session, run this Unreal console command:

```text
ModelContextProtocol.StartServer
```

For persistent auto-start, merge this setting into the editor's per-user file, preserving other settings:

`<Project>/Saved/Config/<Platform>Editor/EditorPerProjectUserSettings.ini`

```ini
[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]
bAutoStartServer=True
```

Optional overrides when the default conflicts with another local service:

```ini
ServerPortNumber=8000
ServerUrlPath=/mcp
```

The editor also supports `-ModelContextProtocolStartServer` and optionally `-ModelContextProtocolPort=<port>` at launch. Use a loopback endpoint for local Codex. Match the actual server port/path, especially when multiple editors are running.

## 3. Configure one Codex connection

Choose one of the following methods. Project configuration is `.codex/config.toml` in the relevant workspace; Codex loads project configuration only for trusted projects. User configuration is normally `~/.codex/config.toml`, or under `CODEX_HOME` when customized. Trust is a user decision: do not change trust settings merely to bypass a load failure.

### A. Generate a new project configuration in Unreal

Run the Unreal console command:

```text
ModelContextProtocol.GenerateClientConfig Codex
```

Upstream writes `.codex/config.toml` at:

- **Source build:** the workspace root beside `Engine/`, which may differ from the `.uproject` directory.
- **Installed/launcher build:** the directory beside the `.uproject`.

Check the Output Log and the generated path instead of assuming that Codex's current workspace is the same directory. The generator **refuses to overwrite an existing TOML file**. Do not delete that file to force regeneration; use a deliberate merge instead. Avoid `All`, which also writes configurations for unrelated clients.

### B. Merge into an explicit config file

This repository includes `scripts/configure_mcp.py` (Python 3.11+). Run it from the repository root, replacing the example project and endpoint with the actual ones:

```powershell
python scripts/configure_mcp.py --config "C:\Projects\MyGame\.codex\config.toml" --url "http://127.0.0.1:8000/mcp"
```

The default is a preview. Inspect the intended file and changes, then add `--apply` when the user's setup request authorizes the write:

```powershell
python scripts/configure_mcp.py --config "C:\Projects\MyGame\.codex\config.toml" --url "http://127.0.0.1:8000/mcp" --apply
```

The helper preserves unrelated settings and comments, backs up an existing changed file, and refuses conflicting definitions rather than silently replacing them. It only examines the supplied file; check other active scopes before using it. If the helper is unavailable in a skill-only installation, perform the same scoped edit after reading the existing TOML. The minimal direct HTTP entry is:

```toml
[mcp_servers.unreal-mcp]
url = "http://127.0.0.1:8000/mcp"
```

Do not append a second table with an existing name. A port change in an existing connection requires editing that connection deliberately; a conflict error from the helper is not permission to overwrite it.

### C. Use Codex CLI for user-level configuration

If a shared user-level connection is intended:

```text
codex mcp add unreal-mcp --url http://127.0.0.1:8000/mcp
```

This command targets user configuration; running it in a project does not make the entry project-local. Inspect `codex mcp list` / `codex mcp get unreal-mcp` and existing project configuration first. Choose either this registration or the project-level entry for a given endpoint, avoiding duplicate direct/proxy registrations.

Reload/reconnect using the available Codex client controls, or start a new session if necessary, so the changed MCP configuration is loaded. A config file on disk alone does not prove that the current session has connected.

## 4. Optional proxy: conditional, not validated by this adaptation

Direct HTTP is the supported initial path. An engine may include `Engine/Plugins/Experimental/ModelContextProtocol/Extras/Proxy`; if it does not, keep direct HTTP. For an existing proxy connection, use it and follow [operations.md](operations.md) for recovery.

Before installing a proxy for Codex, read that build's `Extras/Proxy/README.md` and the executable's actual CLI help. Upstream documents an installer using `--mcp-json` to modify JSON client files. **Do not point `--mcp-json` at Codex's TOML file**, and do not invent a TOML installation flag. Only configure a Codex STDIO server after verifying the real proxy command, arguments, configuration requirements, and platform support. Otherwise report the unsupported step and retain the working direct connection.

Do not register both a proxy and a duplicate direct connection. A proxy maintains a client session while the editor is unavailable; live editor operations still require Unreal to be reachable.

## Verify the actual connection

- The Unreal Output Log shows a successful server startup at the intended endpoint.
- Codex has loaded the intended project/user connection; `codex mcp list` shows configuration, not proof of editor reachability.
- Discover the tool catalog: use `list_toolsets` and `describe_toolset` in search mode, or the actual native tool schema when search mode is disabled.
- Execute a read-only Unreal operation and confirm it refers to the intended project. Cached tools or proxy status alone are insufficient.

When asset editing is part of the task, separately verify the requested change, save it, and read it back or reload as appropriate. For connection failures see [operations.md](operations.md).
