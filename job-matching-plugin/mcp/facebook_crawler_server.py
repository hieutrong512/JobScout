#!/usr/bin/env python3
"""Dependency-free stdio MCP adapter for the optional local Facebook crawler."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

for _stream in (sys.stdout, sys.stdin, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

SERVER_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = {"2025-06-18", "2025-03-26", "2024-11-05"}
TOOL_NAME = "run_facebook_crawler"
MAX_GROUPS = 20
MAX_QUERIES = 8
RUN_ID_RE = re.compile(r"[A-Za-z0-9._-]{1,100}")
GROUP_PATH_RE = re.compile(r"/groups/([A-Za-z0-9._-]+)/?")

TOOL_SCHEMA: Dict[str, Any] = {
    "name": TOOL_NAME,
    "description": (
        "Chạy Facebook Group crawler cục bộ. Tính năng này là tùy chọn, cần Playwright và "
        "một phiên Facebook do người dùng đăng nhập. Kết quả trả về output_path và thống kê từng lần chạy."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "workspace_root": {"type": "string"},
            "profile_path": {"type": "string"},
            "config_path": {"type": "string"},
            "groups": {"type": "array", "items": {"type": "string"}, "maxItems": MAX_GROUPS},
            "queries": {"type": "array", "items": {"type": "string"}, "maxItems": MAX_QUERIES},
            "output_path": {"type": "string"},
            "run_id": {"type": "string", "pattern": "^[A-Za-z0-9._-]{1,100}$"},
            "headless": {"type": "boolean", "default": False},
            "force_login": {"type": "boolean", "default": False},
            "login_only": {"type": "boolean", "default": False},
            "no_search": {"type": "boolean", "default": False},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 15},
            "scrolls": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
        },
        "additionalProperties": False,
    },
}


def _resolve_workspace(arguments: Dict[str, Any]) -> Path:
    raw = arguments.get("workspace_root")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        root = Path(os.environ.get("JOB_MATCHING_WORKSPACE_ROOT") or Path.cwd())
    elif isinstance(raw, str):
        root = Path(raw).expanduser()
        if not root.is_absolute():
            raise ValueError("workspace_root must be an absolute path")
    else:
        raise ValueError("workspace_root must be a string")
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


def _clean_list(values: Any, field: str, max_items: int) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise ValueError(f"{field} must be an array of strings")
    cleaned = list(dict.fromkeys(item.strip() for item in values if item.strip()))
    if len(cleaned) > max_items:
        raise ValueError(f"{field} accepts at most {max_items} items")
    if any(len(item) > 500 for item in cleaned):
        raise ValueError(f"{field} contains an item longer than 500 characters")
    return cleaned


def _run_id(value: Any = None) -> str:
    result = value or f"fb-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    if not isinstance(result, str) or not RUN_ID_RE.fullmatch(result):
        raise ValueError("run_id must match [A-Za-z0-9._-]{1,100}")
    return result


def _validate_group_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").casefold()
    if parsed.scheme not in {"http", "https"} or host not in {
        "facebook.com", "www.facebook.com", "m.facebook.com"
    } or not GROUP_PATH_RE.fullmatch(parsed.path):
        raise ValueError(f"Invalid Facebook group URL: {url}")


def _crawler_python() -> str:
    return (os.environ.get("JOB_MATCHING_PYTHON") or sys.executable).strip()


def build_crawler_command(arguments: Dict[str, Any]) -> tuple[list[str], Path, Path, str]:
    root = _resolve_workspace(arguments)
    run_id = _run_id(arguments.get("run_id"))
    config = _resolve_scoped_path(root, arguments.get("config_path"), root / "data" / "config" / "facebook_groups.json")
    output = _resolve_scoped_path(root, arguments.get("output_path"), root / "data" / "jobs" / f"raw_fb_posts_{run_id}.json")
    profile = None
    if arguments.get("profile_path"):
        profile = _resolve_scoped_path(root, arguments["profile_path"], root / "data" / "profiles")
        if not profile.is_file():
            raise ValueError(f"profile_path does not exist: {profile}")

    limit, scrolls = arguments.get("limit", 15), arguments.get("scrolls", 5)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ValueError("limit must be an integer between 1 and 50")
    if isinstance(scrolls, bool) or not isinstance(scrolls, int) or not 1 <= scrolls <= 20:
        raise ValueError("scrolls must be an integer between 1 and 20")

    groups = _clean_list(arguments.get("groups"), "groups", MAX_GROUPS)
    for url in groups:
        _validate_group_url(url)
    queries = _clean_list(arguments.get("queries"), "queries", MAX_QUERIES)

    command = [
        _crawler_python(), str(SERVER_ROOT / "scripts" / "fb_crawler.py"),
        "--workspace-root", str(root), "--config", str(config), "--output", str(output),
        "--run-id", run_id, "--limit", str(limit), "--scrolls", str(scrolls),
    ]
    if profile:
        command.extend(["--profile", str(profile)])
    if groups:
        command.extend(["--groups", ",".join(groups)])
    if queries:
        command.extend(["--queries", ",".join(queries)])
    for key, flag in (("headless", "--headless"), ("force_login", "--force-login"),
                      ("login_only", "--login-only"), ("no_search", "--no-search")):
        if arguments.get(key) is True:
            command.append(flag)
    return command, output, root, run_id


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        process.kill()


def _summary_from_log(log: str) -> Dict[str, Any]:
    for line in reversed(log.splitlines()):
        if line.startswith("[CRAWL_SUMMARY] "):
            try:
                payload = json.loads(line[len("[CRAWL_SUMMARY] "):])
                return payload if isinstance(payload, dict) else {}
            except json.JSONDecodeError:
                return {}
    return {}


def run_facebook_crawler(arguments: Dict[str, Any], cancel_event: Optional[threading.Event] = None) -> Dict[str, Any]:
    command, output, root, run_id = build_crawler_command(arguments)
    env = os.environ.copy()
    env.update({"PYTHONUTF8": "1", "JOB_MATCHING_WORKSPACE_ROOT": str(root)})
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        command, cwd=str(root), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", creationflags=creationflags,
        start_new_session=(os.name != "nt"),
    )
    deadline = time.monotonic() + 1800
    try:
        while True:
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("Facebook crawler cancelled")
            if time.monotonic() >= deadline:
                raise RuntimeError("Facebook crawler timed out after 30 minutes")
            try:
                stdout, stderr = process.communicate(timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                # communicate drains both pipes while waiting, preventing log-buffer deadlocks.
                continue
    except Exception:
        _terminate_process_tree(process)
        process.communicate()
        raise

    log = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
    log_tail = log[-8000:]
    if process.returncode != 0:
        raise RuntimeError(f"Facebook crawler exited with code {process.returncode}.\n{log_tail}")

    login_only = arguments.get("login_only") is True
    summary = _summary_from_log(log)
    status = "login_saved" if login_only else (
        "completed_with_warnings" if summary.get("failed_pages", 0) else "completed"
    )
    result: Dict[str, Any] = {
        "status": status, "run_id": run_id, "workspace_root": str(root),
        "session_path": str(root / "data" / ".auth" / "facebook_state.json"),
        "output_path": None if login_only else str(output), "log_tail": log_tail, **summary,
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
    payload = {"jsonrpc": "2.0", "id": request_id}
    payload["error" if error is not None else "result"] = error if error is not None else result
    return payload


def handle_message(message: Dict[str, Any], cancel_event: Optional[threading.Event] = None) -> Optional[Dict[str, Any]]:
    if not isinstance(message, dict):
        return _response(None, error={"code": -32600, "message": "Invalid Request"})
    method, request_id = message.get("method"), message.get("id")
    if request_id is None:
        return None
    if method == "initialize":
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        version = params.get("protocolVersion")
        return _response(request_id, {"protocolVersion": version if version in SUPPORTED_PROTOCOL_VERSIONS else PROTOCOL_VERSION,
                                     "capabilities": {"tools": {"listChanged": False}},
                                     "serverInfo": {"name": "job-matching-facebook-crawler", "version": "1.1.0"}})
    if method == "ping":
        return _response(request_id, {})
    if method == "tools/list":
        return _response(request_id, {"tools": [TOOL_SCHEMA]})
    if method == "tools/call":
        params = message.get("params")
        if not isinstance(params, dict) or params.get("name") != TOOL_NAME:
            return _response(request_id, error={"code": -32602, "message": "Invalid params or unknown tool"})
        try:
            result = run_facebook_crawler(params.get("arguments") or {}, cancel_event)
            return _response(request_id, {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                                         "structuredContent": result, "isError": False})
        except Exception as exc:
            result = {"status": "error", "message": str(exc)}
            return _response(request_id, {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                                         "structuredContent": result, "isError": True})
    return _response(request_id, error={"code": -32601, "message": f"Method not found: {method}"})


def serve(lines: Iterable[str]) -> None:
    write_lock = threading.Lock()
    cancellations: Dict[Any, threading.Event] = {}

    def write(response: Dict[str, Any]) -> None:
        with write_lock:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()

    def dispatch(message: Dict[str, Any]) -> None:
        request_id = message.get("id")
        event = threading.Event()
        cancellations[request_id] = event
        try:
            response = handle_message(message, event)
            if response is not None:
                write(response)
        finally:
            cancellations.pop(request_id, None)

    for line in lines:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            if message.get("method") == "notifications/cancelled":
                params = message.get("params") or {}
                event = cancellations.get(params.get("requestId"))
                if event:
                    event.set()
                continue
            if message.get("method") == "tools/call" and message.get("id") is not None:
                threading.Thread(target=dispatch, args=(message,), daemon=True).start()
            else:
                response = handle_message(message)
                if response is not None:
                    write(response)
        except (json.JSONDecodeError, TypeError, ValueError):
            write(_response(None, error={"code": -32700, "message": "Parse error"}))


if __name__ == "__main__":
    serve(sys.stdin)
