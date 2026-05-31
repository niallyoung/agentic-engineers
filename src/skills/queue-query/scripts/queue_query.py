"""
Queue Query Module
==================

Read-oriented visibility and management over the canonical per-session,
per-harness filesystem queue, as a local stepping stone toward an external
memory-API.

The canonical queue lives at::

    ~/.agentic-engineers/artifacts/<session_id>/<harness>/queue/<state>/

where ``<state>`` is one of ``incoming``, ``processing``, ``done``, ``failed``.
Task files are DELEGATE/HANDBACK documents serialised as either ``*.json``
(QueueOperations) or ``*.yaml`` (orchestrator). This module is deliberately
format-agnostic on read so it can observe the whole queue regardless of which
writer produced a task.

Operations provided (the gaps that ``QueueOperations.query_tasks`` does not
cover):

* ``ls(state)``            — list every task in a state
* ``count(state)`` /
  ``count_by_state()``     — backlog sizing
* ``find_orphans(mins)``   — processing tasks stale for > N minutes (resume)
* ``summarize_done()``     — gather results / next-steps from done/

Path math is delegated to the canonical ``queue_isolation`` skill; this module
never constructs queue paths by hand.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# queue-isolation integration (canonical path math)
# ---------------------------------------------------------------------------
_QUEUE_ISOLATION_SCRIPTS = (
    Path(__file__).parent.parent.parent  # src/skills/
    / "_meta" / "queue-isolation" / "scripts"
)


def _import_queue_isolation():
    """Import the canonical queue_isolation module (raises if unavailable)."""
    if str(_QUEUE_ISOLATION_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_QUEUE_ISOLATION_SCRIPTS))
    import queue_isolation as _qi  # noqa: PLC0415

    return _qi


# Optional YAML support — only required when YAML task files are present.
try:  # pragma: no cover - exercised indirectly
    import yaml as _yaml
except ImportError:  # pragma: no cover
    _yaml = None


VALID_STATES = ("incoming", "processing", "done", "failed")

# Files that are queue scaffolding rather than tasks.
_IGNORED_NAMES = {".keep.me", ".gitkeep", ".DS_Store"}


class QueueQueryError(Exception):
    """Raised for invalid queue-query usage (e.g. unknown state)."""


class QueueQuery:
    """Read/visibility operations over a single session/harness queue."""

    STATES = VALID_STATES

    def __init__(
        self,
        session_id: Optional[str] = None,
        harness: Optional[str] = None,
        *,
        base_dir: Optional[Path] = None,
    ) -> None:
        qi = _import_queue_isolation()
        self._qi = qi
        self.session_id = session_id or qi.get_session_id()
        self.harness = harness or qi.detect_harness()
        self.queue_path: Path = qi.get_queue_path(
            self.session_id, self.harness, base_dir=base_dir
        )

    # -- internal helpers ---------------------------------------------------

    def _state_dir(self, state: str) -> Path:
        if state not in VALID_STATES:
            raise QueueQueryError(
                f"Unknown state '{state}'. Valid states: {', '.join(VALID_STATES)}"
            )
        return self.queue_path / state

    def _iter_task_files(self, state: str):
        """Yield Paths of task files in a state dir (json/yaml, no scaffolding)."""
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
        """Parse a task file (json or yaml); attach read-only queue metadata."""
        text = path.read_text(encoding="utf-8")
        data: Dict
        if path.suffix.lower() in (".yaml", ".yml"):
            if _yaml is None:  # pragma: no cover
                raise QueueQueryError(
                    "PyYAML is required to read YAML task files but is not installed"
                )
            data = _yaml.safe_load(text) or {}
        else:
            data = json.loads(text) if text.strip() else {}
        if not isinstance(data, dict):
            data = {"_raw": data}
        stat = path.stat()
        data.setdefault("task_id", path.stem)
        data["_file"] = path.name
        data["_path"] = str(path)
        data["_mtime"] = stat.st_mtime
        return data

    # -- public query API ---------------------------------------------------

    def ls(self, state: str) -> List[Dict]:
        """Return all tasks in ``state`` (sorted by filename)."""
        return [self._load_task(p) for p in self._iter_task_files(state)]

    def count(self, state: str) -> int:
        """Return the number of tasks in ``state``."""
        return sum(1 for _ in self._iter_task_files(state))

    def count_by_state(self) -> Dict[str, int]:
        """Return a ``{state: count}`` map across all canonical states."""
        return {state: self.count(state) for state in VALID_STATES}

    def find_orphans(self, older_than_minutes: float) -> List[Dict]:
        """Return processing tasks idle for longer than ``older_than_minutes``.

        Staleness is measured from each task file's modification time, which is
        format-agnostic and updated on every state transition.
        """
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
        """Summarise completed tasks: counts by status + per-task next-steps."""
        tasks = self.ls("done")
        statuses: Dict[str, int] = {}
        summary_tasks: List[Dict] = []
        for task in tasks:
            status = str(task.get("status", "unknown"))
            statuses[status] = statuses.get(status, 0) + 1
            summary_tasks.append(
                {
                    "task_id": task.get("task_id"),
                    "status": status,
                    "next_steps": task.get("next_steps"),
                    "file": task.get("_file"),
                }
            )
        return {
            "total": len(tasks),
            "by_status": statuses,
            "tasks": summary_tasks,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_query(args: argparse.Namespace) -> QueueQuery:
    base_dir = Path(args.base_dir) if args.base_dir else None
    return QueueQuery(
        session_id=args.session_id,
        harness=args.harness,
        base_dir=base_dir,
    )


def _emit(payload, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, default=str))
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            print(f"{key}: {value}")
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                print(item.get("task_id") or item.get("_file"))
            else:
                print(item)
    else:
        print(payload)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="queue-query",
        description="Query and inspect the local filesystem queue.",
    )
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
            if args.state:
                _emit({args.state: query.count(args.state)}, as_json=args.as_json)
            else:
                _emit(query.count_by_state(), as_json=args.as_json)
        elif args.command == "states":
            _emit(query.count_by_state(), as_json=args.as_json)
        elif args.command == "orphans":
            _emit(query.find_orphans(args.older_than), as_json=args.as_json)
        elif args.command == "summary":
            _emit(query.summarize_done(), as_json=args.as_json)
    except QueueQueryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
