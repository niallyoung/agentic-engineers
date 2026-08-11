"""
Queue Query — read-only visibility over the canonical per-session,
per-harness filesystem queue (the local stepping stone toward an external
memory-API queue interface).

The canonical queue lives at:
    ~/.agentic-engineers/<harness>/<session_id>/queue/<state>/
where <state> is one of incoming, processing, done, failed. Task files are
DELEGATE/HANDBACK documents serialised as *.json or *.yaml — this module is
format-agnostic on read so it can observe the whole queue regardless of
which writer produced a task.

Self-contained: path isolation (session/harness detection, traversal-safe
path construction) is inlined below rather than imported from the
now-deleted src/skills/_meta/queue-isolation skill, matching the same
inlined logic in queue-management/scripts/queue_ops.py.

Operations: ls(state), count(state)/count_by_state(), find_orphans(mins),
summarize_done().
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

try:  # Optional YAML support — only required when YAML task files are present.
    import yaml as _yaml
except ImportError:  # pragma: no cover
    _yaml = None


VALID_STATES = ("incoming", "processing", "done", "failed")
_IGNORED_NAMES = {".keep.me", ".gitkeep", ".DS_Store"}
_SAFE_PATH_COMPONENT_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class QueueQueryError(Exception):
    """Raised for invalid queue-query usage (e.g. unknown state, bad path component)."""


# ---------------------------------------------------------------------------
# Path isolation (self-contained — mirrors queue-management/scripts/queue_ops.py)
# ---------------------------------------------------------------------------

def _validate_path_component(value: str, *, field: str) -> str:
    if not isinstance(value, str):
        raise QueueQueryError(f"{field} must be a string, got {type(value).__name__}")
    if value in ("", ".", "..") or "/" in value or "\\" in value or "\x00" in value:
        raise QueueQueryError(f"{field} is empty or a path reference: {value!r}")
    if not _SAFE_PATH_COMPONENT_RE.match(value):
        raise QueueQueryError(
            f"{field} contains illegal characters (allowed: letters, digits, '.', '_', '-'): {value!r}"
        )
    return value


def detect_harness() -> str:
    explicit = os.environ.get("AGENTIC_HARNESS")
    if explicit:
        return explicit
    if os.environ.get("CLAUDE_SESSION_ID"):
        return "claude"
    if os.environ.get("COPILOT_SESSION_ID"):
        return "copilot"
    if os.environ.get("OPENAI_API_KEY"):
        return "gpt"
    return "local"


def get_session_id() -> str:
    for var in ("AGENTIC_SESSION_ID", "CLAUDE_SESSION_ID", "COPILOT_SESSION_ID"):
        value = os.environ.get(var)
        if value:
            return value
    return str(uuid.uuid4())


def get_queue_path(session_id: str, harness: str, *, base_dir: Optional[Path] = None) -> Path:
    base = Path(base_dir) if base_dir is not None else Path.home() / ".agentic-engineers"
    safe_session = _validate_path_component(session_id, field="session_id")
    safe_harness = _validate_path_component(harness, field="harness")
    return base / safe_harness / safe_session / "queue"


# ---------------------------------------------------------------------------
# QueueQuery — read/visibility operations over a single session/harness queue
# ---------------------------------------------------------------------------

class QueueQuery:
    STATES = VALID_STATES

    def __init__(
        self,
        session_id: Optional[str] = None,
        harness: Optional[str] = None,
        *,
        base_dir: Optional[Path] = None,
    ) -> None:
        self.session_id = session_id or get_session_id()
        self.harness = harness or detect_harness()
        self.queue_path: Path = get_queue_path(self.session_id, self.harness, base_dir=base_dir)

    def _state_dir(self, state: str) -> Path:
        if state not in VALID_STATES:
            raise QueueQueryError(f"Unknown state '{state}'. Valid states: {', '.join(VALID_STATES)}")
        return self.queue_path / state

    def _iter_task_files(self, state: str):
        state_dir = self._state_dir(state)
        if not state_dir.is_dir():
            return
        for entry in sorted(state_dir.iterdir()):
            if not entry.is_file():
                continue
            if entry.name in _IGNORED_NAMES or entry.name.startswith("."):
                continue
            if entry.suffix.lower() not in (".json", ".yaml", ".yml"):
                continue
            yield entry

    @staticmethod
    def _load_task(path: Path) -> Dict:
        """Parse a task file; never raise on a single malformed file — a
        visibility tool must keep going and surface the problem per-task."""
        stat = path.stat()
        meta = {"task_id": path.stem, "_file": path.name, "_path": str(path), "_mtime": stat.st_mtime}
        try:
            text = path.read_text(encoding="utf-8")
            if path.suffix.lower() in (".yaml", ".yml"):
                if _yaml is None:
                    raise QueueQueryError("PyYAML is required to read YAML task files but is not installed")
                data = _yaml.safe_load(text) or {}
            else:
                data = json.loads(text) if text.strip() else {}
        except (ValueError, QueueQueryError, OSError) as exc:
            return {**meta, "_error": str(exc)}
        if not isinstance(data, dict):
            data = {"_raw": data}
        data.setdefault("task_id", path.stem)
        data.update(_file=path.name, _path=str(path), _mtime=stat.st_mtime)
        return data

    def ls(self, state: str) -> List[Dict]:
        """Return all tasks in ``state`` (sorted by filename)."""
        return [self._load_task(p) for p in self._iter_task_files(state)]

    def count(self, state: str) -> int:
        return sum(1 for _ in self._iter_task_files(state))

    def count_by_state(self) -> Dict[str, int]:
        return {state: self.count(state) for state in VALID_STATES}

    def find_orphans(self, older_than_minutes: float) -> List[Dict]:
        """Processing tasks idle for longer than ``older_than_minutes`` (by mtime)."""
        if older_than_minutes < 0:
            raise QueueQueryError("older_than_minutes must be >= 0")
        threshold_seconds = older_than_minutes * 60.0
        now = time.time()
        orphans: List[Dict] = []
        for task in self.ls("processing"):
            age_seconds = now - task["_mtime"]
            if age_seconds >= threshold_seconds:
                task["_age_minutes"] = round(age_seconds / 60.0, 2)
                orphans.append(task)
        return orphans

    def summarize_done(self) -> Dict:
        """Counts by status + per-task next-steps from done/."""
        tasks = self.ls("done")
        statuses: Dict[str, int] = {}
        summary_tasks: List[Dict] = []
        for task in tasks:
            status = str(task.get("status", "unknown"))
            statuses[status] = statuses.get(status, 0) + 1
            summary_tasks.append({
                "task_id": task.get("task_id"),
                "status": status,
                "next_steps": task.get("next_steps"),
                "file": task.get("_file"),
            })
        return {"total": len(tasks), "by_status": statuses, "tasks": summary_tasks}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_query(args: argparse.Namespace) -> QueueQuery:
    base_dir = Path(args.base_dir) if args.base_dir else None
    return QueueQuery(session_id=args.session_id, harness=args.harness, base_dir=base_dir)


def _emit(payload, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, default=str))
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            print(f"{key}: {value}")
    elif isinstance(payload, list):
        for item in payload:
            print(item.get("task_id") or item.get("_file") if isinstance(item, dict) else item)
    else:
        print(payload)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="queue-query", description="Query and inspect the local filesystem queue.")
    parser.add_argument("--session-id", default=None, help="Session id (default: detected).")
    parser.add_argument("--harness", default=None, help="Harness name (default: detected).")
    parser.add_argument("--base-dir", default=None, help="Override queue base dir (testing).")
    parser.add_argument("--json", action="store_true", dest="as_json", help="JSON output.")

    sub = parser.add_subparsers(dest="command", required=True)
    p_ls = sub.add_parser("ls", help="List tasks in a state.")
    p_ls.add_argument("--state", required=True, choices=VALID_STATES)
    p_size = sub.add_parser("size", help="Count tasks (a state, or all states).")
    p_size.add_argument("--state", choices=VALID_STATES, default=None)
    sub.add_parser("states", help="Count tasks across every state.")
    p_orph = sub.add_parser("orphans", help="Find stale processing tasks.")
    p_orph.add_argument("--older-than", type=float, default=30.0, help="Minutes (default 30).")
    sub.add_parser("summary", help="Summarise completed (done/) tasks.")

    args = parser.parse_args(argv)

    try:
        query = _build_query(args)
        if args.command == "ls":
            _emit(query.ls(args.state), as_json=args.as_json)
        elif args.command == "size":
            _emit({args.state: query.count(args.state)} if args.state else query.count_by_state(), as_json=args.as_json)
        elif args.command == "states":
            _emit(query.count_by_state(), as_json=args.as_json)
        elif args.command == "orphans":
            _emit(query.find_orphans(args.older_than), as_json=args.as_json)
        elif args.command == "summary":
            _emit(query.summarize_done(), as_json=args.as_json)
    except (QueueQueryError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
