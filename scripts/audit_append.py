#!/usr/bin/env python3
"""audit_append.py — Deterministic append helper for the SPEC clause-7 audit JSONL.

## What this is

`docs/SPEC.md` § ORCHESTRATOR-FIRST EXECUTION MODEL, clause 7 ("Audit Trail:
Append-Only JSONL, Write-Only from the Agent") requires every orchestration event —
`delegate_issued`, `subagent_spawned`, `handback_received`, `gate_result`,
`escalation`, `refusal`, `limit_exceeded` — to be appended as one JSON object per
line to `~/.agentic-engineers/{harness}/{session-id}/audit/events-YYYY-MM-DD.jsonl`.

This script is that append helper: a deterministic, stdlib-only utility an AGENT
invokes at each lifecycle point it owns (see `src/AGENTS.md` § Direct Sub-Agent Spawn
Execution Model § Audit Events for which role appends which events). The AGENT decides
*when* and *what* to log; this script owns *formatting, validation, and the actual
append* — the same division of labor the old (now-removed) `enqueue()` had between
caller and queue helper, per `docs/SPEC.md` clause 8 ("advisory Python").

## The one permitted failure mode

Per clause 7 the schema is exact: an unknown `event` name, or a missing required
field, is rejected (exit code 2, a clear stderr message) rather than silently
written. That is the ONLY thing this script treats as an error worth stopping over.
Everything else — a filesystem write failure, an unwritable audit directory — is
still reported (non-zero exit, stderr message) but is a WARNING an agent should log
and move past, never a reason to abandon the actual work it was doing. Nothing about
this script's exit code should ever block a DELEGATE/HANDBACK from proceeding.

## Append-only

Every invocation performs exactly one O_APPEND, single `write()` syscall of one JSON
line — this script never reads, rewrites, reorders, or truncates prior lines.
Corrections are new events, never edits, per clause 7's own text.

## Usage

    # Flag mode — one event, fields as CLI args:
    python3 scripts/audit_append.py --event delegate_issued \\
        --task-id my-task --parent-task-id orchestrator-root --depth 1 \\
        --agent-role senior-engineer --agent-model claude-sonnet-5 --status success

    # Stdin mode — one event, fields as a JSON object on stdin:
    echo '{"event": "handback_received", "task_id": "my-task", ...}' \\
        | python3 scripts/audit_append.py

    # Preview without writing:
    python3 scripts/audit_append.py --event refusal --dry-run --task-id t1 \\
        --parent-task-id null --depth 4 --agent-role orchestrator \\
        --agent-model claude-sonnet-5 --status blocked

## Session/harness resolution

Reuses the env-priority convention `src/skills/queue-management/scripts/queue_ops.py`
used pre-removal (recovered from git history — see `get_session_id`/`detect_harness`
below): `AGENTIC_SESSION_ID` > `CLAUDE_SESSION_ID` > `COPILOT_SESSION_ID` for the
session id (falling back to a fresh UUID4 if none are set); `AGENTIC_HARNESS`
(explicit) > `CLAUDE_SESSION_ID` > `COPILOT_SESSION_ID` > `OPENAI_API_KEY` > `"local"`
for the harness.

## Dependencies

stdlib only. No network access, no PyYAML.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# -----------------------------------------------------------------------------
# Clause-7 contract
# -----------------------------------------------------------------------------

ALLOWED_EVENTS = {
    "delegate_issued",
    "subagent_spawned",
    "handback_received",
    "gate_result",
    "escalation",
    "refusal",
    "limit_exceeded",
}

# Required on every event per docs/SPEC.md clause 7 ("required fields: ts ..., event,
# task_id, parent_task_id, depth, agent_role, agent_model, status"). `ts` is computed
# by this script, never accepted from the caller — see main(). `parent_task_id` MAY be
# null (root-level events have no parent) but the KEY must be present.
REQUIRED_KEYS = ("task_id", "parent_task_id", "depth", "agent_role", "agent_model", "status")

_NUMERIC_OPTIONAL_KEYS = ("tokens", "cost")

_SAFE_PATH_COMPONENT_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _validate_path_component(value: str, *, field: str) -> str:
    """Validate a session_id/harness value before using it in an audit path.

    Mirrors ``queue_ops.py``'s ``_validate_path_component`` (recovered from git
    history prior to the queue's removal) so audit paths get the same defense
    against path traversal / illegal characters that queue paths used to.
    """
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string, got {type(value).__name__}")
    if value in ("", ".", ".."):
        raise ValueError(f"{field} is empty or a path reference: {value!r}")
    if "/" in value or "\\" in value or "\x00" in value:
        raise ValueError(f"{field} contains illegal path separators: {value!r}")
    if not _SAFE_PATH_COMPONENT_RE.match(value):
        raise ValueError(
            f"{field} contains illegal characters (allowed: letters, digits, '.', '_', '-'): {value!r}"
        )
    return value


def detect_harness(env: Optional[Dict[str, str]] = None) -> str:
    """Detect the current AI harness from environment variables.

    Priority: AGENTIC_HARNESS (explicit) > CLAUDE_SESSION_ID > COPILOT_SESSION_ID
    > OPENAI_API_KEY > 'local' (fallback). Reimplemented compactly from
    ``queue_ops.py``'s pre-removal ``detect_harness()`` (git history:
    ``git show <pre-removal-sha>:src/skills/queue-management/scripts/queue_ops.py``).
    """
    e = env if env is not None else os.environ
    explicit = e.get("AGENTIC_HARNESS")
    if explicit:
        return explicit
    if e.get("CLAUDE_SESSION_ID"):
        return "claude"
    if e.get("COPILOT_SESSION_ID"):
        return "copilot"
    if e.get("OPENAI_API_KEY"):
        return "gpt"
    return "local"


def get_session_id(env: Optional[Dict[str, str]] = None) -> str:
    """Retrieve the current session ID from environment, or generate a UUID4.

    Priority: AGENTIC_SESSION_ID > CLAUDE_SESSION_ID > COPILOT_SESSION_ID.
    Reimplemented compactly from ``queue_ops.py``'s pre-removal ``get_session_id()``.
    """
    e = env if env is not None else os.environ
    for var in ("AGENTIC_SESSION_ID", "CLAUDE_SESSION_ID", "COPILOT_SESSION_ID"):
        value = e.get(var)
        if value:
            return value
    return str(uuid.uuid4())


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_event(doc: Dict[str, Any]) -> List[str]:
    """Check a candidate event dict against the clause-7 contract.

    Returns a list of error strings (empty == usable). This is the ONE permitted
    failure mode this script raises over — see module docstring.
    """
    errors: List[str] = []

    event = doc.get("event")
    if event not in ALLOWED_EVENTS:
        errors.append("event: must be one of %s (got %r)" % (sorted(ALLOWED_EVENTS), event))

    for key in REQUIRED_KEYS:
        if key not in doc:
            errors.append("%s: required field missing" % key)

    if "task_id" in doc and (not isinstance(doc["task_id"], str) or not doc["task_id"].strip()):
        errors.append("task_id: must be a non-empty string")

    if "depth" in doc:
        depth = doc["depth"]
        if isinstance(depth, bool) or not isinstance(depth, int) or depth < 0:
            errors.append("depth: must be a non-negative integer")

    if "agent_role" in doc and (not isinstance(doc["agent_role"], str) or not doc["agent_role"].strip()):
        errors.append("agent_role: must be a non-empty string")

    if "agent_model" in doc and (not isinstance(doc["agent_model"], str) or not doc["agent_model"].strip()):
        errors.append("agent_model: must be a non-empty string")

    if "status" in doc and (not isinstance(doc["status"], str) or not doc["status"].strip()):
        errors.append("status: must be a non-empty string")

    if "parent_task_id" in doc:
        ptid = doc["parent_task_id"]
        if ptid is not None and (not isinstance(ptid, str) or not ptid.strip()):
            errors.append("parent_task_id: must be a non-empty string or null")

    for key in _NUMERIC_OPTIONAL_KEYS:
        if key in doc and doc[key] is not None and not _is_number(doc[key]):
            errors.append("%s: must be a number" % key)

    return errors


_OUTPUT_KEY_ORDER = ("ts", "event", "task_id", "parent_task_id", "depth", "agent_role", "agent_model", "status")


def _order_event(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of doc with the canonical clause-7 keys first, extras after."""
    ordered: Dict[str, Any] = {k: doc[k] for k in _OUTPUT_KEY_ORDER if k in doc}
    for k, v in doc.items():
        if k not in ordered:
            ordered[k] = v
    return ordered


def compute_ts(now: Optional[datetime] = None) -> str:
    """Compute the event's UTC ISO-8601 timestamp. Never trust a caller-supplied ts."""
    now = now if now is not None else datetime.now(timezone.utc)
    # Millisecond precision, explicit 'Z' suffix (ISO-8601 UTC).
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + ("%03dZ" % (now.microsecond // 1000))


def resolve_audit_path(
    *, harness: str, session_id: str, date_str: str, base_dir: Optional[Path] = None
) -> Path:
    """Canonical audit path: <base_dir>/<harness>/<session_id>/audit/events-<date_str>.jsonl."""
    base = base_dir if base_dir is not None else Path.home() / ".agentic-engineers"
    safe_harness = _validate_path_component(harness, field="harness")
    safe_session = _validate_path_component(session_id, field="session_id")
    return base / safe_harness / safe_session / "audit" / ("events-%s.jsonl" % date_str)


def append_line(path: Path, line: str) -> None:
    """Append one line to path, creating parent dirs as needed.

    A single O_APPEND write() call — append-only, no read/rewrite/truncate of
    prior content, per clause 7.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
    try:
        os.write(fd, (line + "\n").encode("utf-8"))
    finally:
        os.close(fd)


def _build_doc_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    doc: Dict[str, Any] = {"event": args.event}
    # A flag left unset (None) means the field is genuinely absent — omit the key
    # entirely so validate_event() reports it as "required field missing" rather
    # than a type error. parent_task_id is the one exception: None is a valid
    # value (root-level events have no parent), so its key is always present.
    for key, value in (
        ("task_id", args.task_id),
        ("depth", args.depth),
        ("agent_role", args.agent_role),
        ("agent_model", args.agent_model),
        ("status", args.status),
    ):
        if value is not None:
            doc[key] = value
    doc["parent_task_id"] = args.parent_task_id
    if args.tokens is not None:
        doc["tokens"] = args.tokens
    if args.cost is not None:
        doc["cost"] = args.cost
    return doc


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Append one clause-7 audit event to the session's audit JSONL. "
            "Advisory formatting/validation helper — never owns dispatch or control flow."
        )
    )
    parser.add_argument("--event", choices=sorted(ALLOWED_EVENTS), help="Event name (omit to read a full JSON object from stdin)")
    parser.add_argument("--task-id")
    parser.add_argument("--parent-task-id", help="Parent task_id, or omit/pass an empty value for root-level events")
    parser.add_argument("--depth", type=int)
    parser.add_argument("--agent-role")
    parser.add_argument("--agent-model")
    parser.add_argument("--status")
    parser.add_argument("--tokens", type=float)
    parser.add_argument("--cost", type=float)
    parser.add_argument("--extra", help="JSON object string merged into the event as additional fields")
    parser.add_argument("--dry-run", action="store_true", help="Print the JSON line without writing it")
    parser.add_argument("--base-dir", help="Override the ~/.agentic-engineers base directory (mainly for tests)")
    args = parser.parse_args(argv)

    if args.event is None:
        raw = sys.stdin.read()
        if not raw.strip():
            print("audit_append: no --event given and stdin is empty", file=sys.stderr)
            return 2
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError as e:
            print("audit_append: invalid JSON on stdin: %s" % e, file=sys.stderr)
            return 2
        if not isinstance(doc, dict):
            print("audit_append: stdin JSON must be an object", file=sys.stderr)
            return 2
    else:
        doc = _build_doc_from_args(args)

    if args.extra:
        try:
            extra = json.loads(args.extra)
        except json.JSONDecodeError as e:
            print("audit_append: invalid JSON in --extra: %s" % e, file=sys.stderr)
            return 2
        if not isinstance(extra, dict):
            print("audit_append: --extra must be a JSON object", file=sys.stderr)
            return 2
        doc.update(extra)

    errors = validate_event(doc)
    if errors:
        print("audit_append: rejected — " + "; ".join(errors), file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc)
    doc["ts"] = compute_ts(now)  # computed here, always overrides any caller-supplied ts
    ordered = _order_event(doc)
    line = json.dumps(ordered, sort_keys=False)

    if args.dry_run:
        print(line)
        return 0

    try:
        harness = detect_harness()
        session_id = get_session_id()
        base_dir = Path(args.base_dir) if args.base_dir else None
        path = resolve_audit_path(
            harness=harness, session_id=session_id, date_str=now.strftime("%Y-%m-%d"), base_dir=base_dir
        )
        append_line(path, line)
    except (OSError, ValueError) as e:
        # The one non-validation failure mode: report and let the caller treat it
        # as a warning. This must never block the agent's actual work.
        print("audit_append: warning — failed to append audit event: %s" % e, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
