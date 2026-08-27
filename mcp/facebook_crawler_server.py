#!/usr/bin/env python3
"""Dependency-free stdio MCP server for the local Facebook crawler."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


SERVER_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = {"2025-06-18", "2025-03-26", "2024-11-05"}
TOOL_NAME = "run_facebook_crawler"


TOOL_SCHEMA: Dict[str, Any] = {
    "name": TOOL_NAME,
    "description": (
        "Run the bundled Facebook Group Playwright crawler on the local Windows host. "
        "Pass an absolute workspace_root so profile, config, session, and output files "
        "remain in the user's active workspace. The first run may open Chromium for login."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "workspace_root": {
                "type": "string",
                "description": "Absolute path to the active workspace that owns data/.",
            },
            "profile_path": {
                "type": "string",
                "description": "Profile JSON path, absolute or relative to workspace_root.",
            },
            "config_path": {
                "type": "string",
                "description": "Facebook groups config path, absolute or relative to workspace_root.",
            },
            "groups": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Public Facebook Group URLs. When supplied, the crawler updates config_path.",
            },
            "queries": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional in-group search queries.",
            },
            "output_path": {
                "type": "string",
                "description": "Output JSON path, absolute or relative to workspace_root.",
            },
            "headless": {"type": "boolean", "default": False},
            "force_login": {"type": "boolean", "default": False},
            "login_only": {"type": "boolean", "default": False},
            "no_search": {"type": "boolean", "default": False},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 15},
            "scrolls": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
        },
        "required": ["workspace_root"],
        "additionalProperties": False,
    },
}


def _resolve_workspace(arguments: Dict[str, Any]) -> Path:
    raw = arguments.get("workspace_root")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("workspace_root is required")
    root = Path(raw).expanduser()
    if not root.is_absolute():
        raise ValueError("workspace_root must be an absolute path")
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"workspace_root does not exist: {root}")
    return root


def _resolve_scoped_path(root: Path, value: Optional[str], default: Path) -> Path:
    path = Path(value).expanduser() if value else default
    path = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path must stay inside workspace_root: {path}") from exc
    return path


def _clean_list(values: Any, field: str) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise ValueError(f"{field} must be an array of strings")
    cleaned = list(dict.fromkeys(item.strip() for item in values if item.strip()))
    if any(len(item) > 500 for item in cleaned):
        raise ValueError(f"{field} contains an item longer than 500 characters")
    return cleaned


def build_crawler_command(arguments: Dict[str, Any]) -> tuple[list[str], Path, Path]:
    root = _resolve_workspace(arguments)
    today = dt.datetime.now().strftime("%Y-%m-%d")
    config = _resolve_scoped_path(
        root, arguments.get("config_path"), root / "data" / "config" / "facebook_groups.json"
    )
    output = _resolve_scoped_path(
        root, arguments.get("output_path"), root / "data" / "jobs" / f"raw_fb_posts_{today}.json"
    )
    profile = None
    if arguments.get("profile_path"):
        profile = _resolve_scoped_path(root, arguments["profile_path"], root / "data" / "profiles")
        if not profile.is_file():
            raise ValueError(f"profile_path does not exist: {profile}")

    limit = arguments.get("limit", 15)
    scrolls = arguments.get("scrolls", 5)
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer")
    if isinstance(scrolls, bool) or not isinstance(scrolls, int):
        raise ValueError("scrolls must be an integer")
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    if not 1 <= scrolls <= 20:
        raise ValueError("scrolls must be between 1 and 20")

    groups = _clean_list(arguments.get("groups"), "groups")
    invalid_groups = []
    for url in groups:
        parsed = urllib.parse.urlparse(url)
        hostname = (parsed.hostname or "").casefold()
        if parsed.scheme not in {"http", "https"} or hostname not in {"facebook.com", "www.facebook.com"} or not parsed.path.startswith("/groups/"):
            invalid_groups.append(url)
    if invalid_groups:
        raise ValueError("Every groups item must be a facebook.com/groups URL")
    queries = _clean_list(arguments.get("queries"), "queries")

    crawler = SERVER_ROOT / "scripts" / "fb_crawler.py"
    command = [
        sys.executable,
        str(crawler),
        "--workspace-root",
        str(root),
        "--config",
        str(config),
        "--output",
        str(output),
        "--limit",
        str(limit),
        "--scrolls",
        str(scrolls),
    ]
    if profile:
        command.extend(["--profile", str(profile)])
    if groups:
        command.extend(["--groups", ",".join(groups)])
    if queries:
        command.extend(["--queries", ",".join(queries)])
    for key, flag in (
        ("headless", "--headless"),
        ("force_login", "--force-login"),
        ("login_only", "--login-only"),
        ("no_search", "--no-search"),
    ):
        if arguments.get(key) is True:
            command.append(flag)
    return command, output, root


def run_facebook_crawler(arguments: Dict[str, Any]) -> Dict[str, Any]:
    command, output, root = build_crawler_command(arguments)
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["JOB_MATCHING_WORKSPACE_ROOT"] = str(root)

    try:
        completed = subprocess.run(
            command,
            cwd=str(SERVER_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Facebook crawler timed out after 30 minutes") from exc
    except OSError as exc:
        raise RuntimeError(f"Could not start the local crawler: {exc}") from exc

    log = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    log_tail = log[-8000:]
    if completed.returncode != 0:
        raise RuntimeError(f"Facebook crawler exited with code {completed.returncode}.\n{log_tail}")

    login_only = arguments.get("login_only") is True
    result: Dict[str, Any] = {
        "status": "login_saved" if login_only else "completed",
        "workspace_root": str(root),
        "session_path": str(root / "data" / ".auth" / "facebook_state.json"),
        "output_path": None if login_only else str(output),
        "log_tail": log_tail,
    }
    if not login_only:
        if not output.is_file():
            raise RuntimeError(f"Crawler completed but did not create output: {output}")
        try:
            payload = json.loads(output.read_text(encoding="utf-8"))
            result["job_count"] = len(payload) if isinstance(payload, list) else None
        except (OSError, json.JSONDecodeError):
            result["job_count"] = None
    return result


def _response(request_id: Any, result: Any = None, error: Any = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result
    return payload


def handle_message(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(message, dict):
        return _response(None, error={"code": -32600, "message": "Invalid Request"})
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None:
        return None
    if method == "initialize":
        params = message.get("params")
        params = params if isinstance(params, dict) else {}
        client_version = params.get("protocolVersion")
        negotiated_version = client_version if client_version in SUPPORTED_PROTOCOL_VERSIONS else PROTOCOL_VERSION
        return _response(
            request_id,
            {
                "protocolVersion": negotiated_version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "job-matching-facebook-crawler", "version": "1.0.0"},
            },
        )
    if method == "ping":
        return _response(request_id, {})
    if method == "tools/list":
        return _response(request_id, {"tools": [TOOL_SCHEMA]})
    if method == "tools/call":
        params = message.get("params")
        if not isinstance(params, dict):
            return _response(request_id, error={"code": -32602, "message": "Invalid params"})
        if params.get("name") != TOOL_NAME:
            return _response(request_id, error={"code": -32602, "message": "Unknown tool"})
        try:
            result = run_facebook_crawler(params.get("arguments") or {})
            return _response(
                request_id,
                {
                    "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                    "structuredContent": result,
                    "isError": False,
                },
            )
        except Exception as exc:
            error_result = {"status": "error", "message": str(exc)}
            return _response(
                request_id,
                {
                    "content": [{"type": "text", "text": json.dumps(error_result, ensure_ascii=False)}],
                    "structuredContent": error_result,
                    "isError": True,
                },
            )
    return _response(request_id, error={"code": -32601, "message": f"Method not found: {method}"})


def serve(lines: Iterable[str]) -> None:
    for line in lines:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            response = handle_message(message)
        except (json.JSONDecodeError, TypeError, ValueError):
            response = _response(None, error={"code": -32700, "message": "Parse error"})
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    serve(sys.stdin)
