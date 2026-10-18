# Optional UE session context

The plugin works without hooks. `scripts/session_context.py` reads the hook's `cwd`, walks upward for
`.uproject` or `GenerateProjectFiles.*`, and returns context only for Unreal directories. It never writes
configuration, starts an editor, or treats a config file as proof of connectivity. Project filenames and
file contents are not inserted into the instructions.

## Explicit local setup

Use a stable checkout/extracted package, not an auto-updated cache path. Merge this into
`<project>/.codex/hooks.json` or `~/.codex/hooks.json`, preserving existing hooks. Choose one scope.
Ensure Python 3.11+ is available as `python` on PATH. Replace the example script path with your checkout:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear|compact|fork",
        "hooks": [
          {
            "type": "command",
            "command": "python \"H:/Unreal-Skill/unreal-engine-skills-for-codex-plugin/scripts/session_context.py\"",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

On macOS/Linux use, for example, `python3 "/home/user/plugin/scripts/session_context.py"`.
Open `/hooks` in a supporting Codex CLI to review and trust the definition. Project hooks need a trusted
project. The repository does not install this file or bypass trust. Remove only your added entry to undo.

## Manual check

```powershell
python scripts/session_context.py --cwd "F:\MyProject\Source"
```

Unrelated directories return `{}`; UE directories return `hookSpecificOutput.additionalContext` for
`SessionStart`. Normal hook execution reads JSON on stdin. See [Codex Hooks](https://learn.chatgpt.com/docs/hooks).
Public-directory submission has separate restrictions on lifecycle hooks. This helper is not declared
as an automatically loaded plugin hook.
