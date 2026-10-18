#!/usr/bin/env python3
"""Preview or safely append one local Unreal MCP server to a Codex TOML file.

Python 3.11+; no dependencies. Only the explicitly selected file is inspected.
Other Codex scopes and already installed plugin connections must be checked by
the caller. Writes use optimistic concurrency checks immediately before replace;
an unrelated writer that ignores this tool can still race that final operation.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import tomllib
from urllib.parse import urlsplit


DEFAULT_URL = "http://127.0.0.1:8000/mcp"
DEFAULT_NAME = "unreal-mcp"
NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


class ConfigError(Exception):
    """A configuration cannot be changed safely."""


@dataclass(frozen=True)
class Snapshot:
    data: bytes | None
    identity: tuple[int, int, int, int, int] | None
    mode: int | None


@dataclass(frozen=True)
class Plan:
    path: Path
    name: str
    snapshot: Snapshot
    content: bytes | None
    addition: str

    @property
    def changed(self) -> bool:
        return self.content is not None


def validate_name(name: str) -> None:
    if not NAME_PATTERN.fullmatch(name):
        raise ConfigError(
            "Server name must be 1-64 ASCII letters, digits, '-' or '_', "
            "and begin with a letter or digit."
        )
    if name == "unreal-mcp-proxy":
        raise ConfigError("'unreal-mcp-proxy' is reserved for the optional proxy; choose another name.")


def endpoint(url: str) -> tuple[str, str, int, str, str]:
    """Validate a loopback HTTP URL and return its comparison identity."""
    if not isinstance(url, str) or not url or any(
        character.isspace()
        or ord(character) < 32
        or ord(character) == 127
        or 0xD800 <= ord(character) <= 0xDFFF
        for character in url
    ):
        raise ConfigError("URL must be a nonempty HTTP(S) URL without whitespace or control characters.")
    if "#" in url:
        raise ConfigError("URL fragments are not supported; remove the '#' fragment.")
    try:
        parsed = urlsplit(url)
        if parsed.scheme.lower() not in ("http", "https"):
            raise ConfigError("Only loopback HTTP or HTTPS URLs are supported.")
        if parsed.username is not None or parsed.password is not None:
            raise ConfigError("URL user information is not supported; remove credentials from the URL.")
        hostname = parsed.hostname
        if not hostname:
            raise ConfigError("URL must include a loopback hostname or IP address.")
        if hostname.lower() == "localhost":
            normalized_host = "localhost"
        else:
            address = ipaddress.ip_address(hostname)
            if not address.is_loopback or "%" in hostname:
                raise ConfigError("URL must use localhost or a loopback IP address (127.0.0.0/8 or ::1).")
            normalized_host = address.compressed
        port = parsed.port
        if parsed.netloc.endswith(":") or port == 0:
            raise ConfigError("URL port must be an integer from 1 through 65535.")
    except ValueError as error:
        raise ConfigError("URL must contain a valid loopback IP/localhost and a valid port.") from error
    return (
        parsed.scheme.lower(),
        normalized_host,
        port if port is not None else (443 if parsed.scheme.lower() == "https" else 80),
        parsed.path or "/",
        parsed.query,
    )


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _read_snapshot(path: Path) -> Snapshot:
    try:
        initial = path.lstat()
        if stat.S_ISLNK(initial.st_mode):
            raise ConfigError("The target is a symbolic link; select the actual configuration file explicitly.")
        if not stat.S_ISREG(initial.st_mode):
            raise ConfigError("The target must be a regular file.")
        with path.open("rb") as source:
            before = os.fstat(source.fileno())
            # Some Windows Python versions report ctime differently for lstat
            # and fstat. Compare file identity here, then fstat to fstat below.
            if (initial.st_dev, initial.st_ino) != (before.st_dev, before.st_ino):
                raise ConfigError("The configuration changed before it could be read; retry after other writers finish.")
            data = source.read()
            after = os.fstat(source.fileno())
        if _identity(before) != _identity(after):
            raise ConfigError("The configuration changed while it was being read; retry after other writers finish.")
        return Snapshot(data, _identity(after), stat.S_IMODE(after.st_mode))
    except FileNotFoundError:
        return Snapshot(None, None, None)
    except OSError as error:
        raise ConfigError(f"Cannot read the selected configuration: {error.strerror or error}.") from error


def _parse(data: bytes) -> dict:
    try:
        # UTF-8 BOMs are accepted and preserved even though TOML itself has no BOM.
        return tomllib.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        # Do not echo existing configuration lines: they may contain secrets.
        raise ConfigError("The selected file is not valid UTF-8 TOML. Repair it manually before retrying.") from error


def _enabled(server: dict, name: str) -> bool:
    enabled = server.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ConfigError(f"Server '{name}' has a non-boolean 'enabled' value; adjust it manually.")
    return enabled


def _existing_endpoint(server: dict) -> tuple[str, str, int, str, str] | None:
    try:
        return endpoint(server.get("url"))
    except ConfigError:
        # Other unrelated remote/STDIO servers remain untouched.
        return None


def build_plan(config: str | Path, url: str = DEFAULT_URL, name: str = DEFAULT_NAME) -> Plan:
    validate_name(name)
    desired_endpoint = endpoint(url)
    path = Path(config).expanduser().absolute()
    snapshot = _read_snapshot(path)
    parsed = _parse(snapshot.data or b"")
    servers = parsed.get("mcp_servers", {})
    if not isinstance(servers, dict):
        raise ConfigError("'mcp_servers' must be a TOML table; adjust the selected file manually.")
    for existing_name, server in servers.items():
        if not isinstance(server, dict):
            raise ConfigError(f"Server '{existing_name}' is not a TOML table; adjust it manually.")
        enabled = _enabled(server, existing_name)
        if existing_name == "unreal-mcp-proxy" and enabled:
            raise ConfigError(
                "An enabled 'unreal-mcp-proxy' already exists in this file. "
                "Choose one connection and adjust the configuration manually."
            )
        if existing_name != name and enabled and _existing_endpoint(server) == desired_endpoint:
            raise ConfigError(
                f"Enabled server '{existing_name}' already uses this endpoint. "
                "Reuse that connection or adjust the configuration manually."
            )
    if name in servers:
        existing = servers[name]
        if (
            set(existing).issubset({"url", "enabled"})
            and _enabled(existing, name)
            and _existing_endpoint(existing) == desired_endpoint
        ):
            return Plan(path, name, snapshot, None, "")
        raise ConfigError(
            f"Server '{name}' already has a different definition. "
            "Review and adjust it manually; this tool never overwrites an existing server."
        )

    raw = snapshot.data or b""
    first_newline = re.search(rb"\r?\n", raw)
    newline = first_newline.group().decode("ascii") if first_newline else "\n"
    addition = (
        f"[mcp_servers.{json.dumps(name)}]{newline}"
        f"url = {json.dumps(url, ensure_ascii=False)}{newline}"
    )
    visible_content = raw[3:] if raw.startswith(b"\xef\xbb\xbf") else raw
    separator = "" if not visible_content else (newline if raw.endswith(b"\n") else newline * 2)
    content = raw + (separator + addition).encode("utf-8")
    try:
        resulting = _parse(content)
    except ConfigError as error:
        raise ConfigError(
            "A new server table cannot be appended safely to this TOML structure "
            "(for example, an inline mcp_servers table). Adjust it manually; the file was not changed."
        ) from error
    expected_servers = dict(servers)
    expected_servers[name] = {"url": url}
    expected = dict(parsed)
    expected["mcp_servers"] = expected_servers
    if resulting != expected:
        raise ConfigError("Appending the server would change unrelated TOML values; adjust the file manually.")
    return Plan(path, name, snapshot, content, addition)


def _assert_unchanged(plan: Plan) -> None:
    current = _read_snapshot(plan.path)
    if current != plan.snapshot:
        raise ConfigError("The configuration changed since preview. Nothing was replaced; generate a fresh preview.")


def _write_backup(path: Path, snapshot: Snapshot) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = path.with_name(f"{path.name}.bak.{timestamp}")
    # Exclusive creation prevents accidentally replacing an earlier backup.
    created = False
    try:
        descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, snapshot.mode or 0o600)
        created = True
        with os.fdopen(descriptor, "wb") as destination:
            if snapshot.mode is not None:
                os.chmod(backup, snapshot.mode)
            destination.write(snapshot.data or b"")
            destination.flush()
            os.fsync(destination.fileno())
    except OSError:
        # A failed partial backup is not useful. Never remove a colliding backup.
        if created:
            try:
                backup.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    return backup


def apply_plan(plan: Plan) -> Path | None:
    """Apply one plan; return its backup path, or None for a new file/no-op.

    File mode bits are retained. Platform-specific ACLs/extended attributes are
    not copied; environments that require them should merge their config manually.
    """
    _assert_unchanged(plan)
    if not plan.changed:
        return None
    if plan.snapshot.mode is not None and not plan.snapshot.mode & stat.S_IWUSR:
        raise ConfigError("The selected configuration is read-only; adjust permissions manually before applying.")
    temporary: Path | None = None
    backup: Path | None = None
    try:
        plan.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{plan.path.name}.", suffix=".tmp", dir=plan.path.parent
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as destination:
            if plan.snapshot.mode is not None:
                os.chmod(temporary, plan.snapshot.mode)
            destination.write(plan.content)
            destination.flush()
            os.fsync(destination.fileno())
        _assert_unchanged(plan)
        if plan.snapshot.data is not None:
            backup = _write_backup(plan.path, plan.snapshot)
        _assert_unchanged(plan)
        os.replace(temporary, plan.path)
        temporary = None
        return backup
    except OSError as error:
        raise ConfigError(f"Cannot apply the configuration: {error.strerror or error}.") from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preview or append a local Unreal MCP server while preserving unrelated TOML and comments.",
        epilog=(
            "Only this file is checked. First inspect current Codex connections and other config scopes. "
            "Stop other configuration writers while applying. File mode bits are preserved, but custom ACLs "
            "and extended attributes require a manual merge."
        ),
    )
    parser.add_argument("--config", required=True, help="Explicit target Codex TOML file (quote paths with spaces).")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Loopback HTTP(S) endpoint (default: {DEFAULT_URL}).")
    parser.add_argument("--name", default=DEFAULT_NAME, help=f"Server name (default: {DEFAULT_NAME}).")
    parser.add_argument("--apply", action="store_true", help="Write the previewed change; otherwise do not write any files.")
    args = parser.parse_args(argv)
    try:
        plan = build_plan(args.config, args.url, args.name)
        if not plan.changed:
            print(f"Already configured: '{plan.name}' in {plan.path}. No files changed.")
            return 0
        if not args.apply:
            print(f"Preview only: append to {plan.path}")
            print(plan.addition, end="")
            print("No files written. Re-run with --apply to write this change.")
            return 0
        backup = apply_plan(plan)
        print(f"Configured '{plan.name}' in {plan.path}.")
        if backup is not None:
            print(f"Backup: {backup}")
        return 0
    except ConfigError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
