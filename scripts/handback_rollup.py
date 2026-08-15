#!/usr/bin/env python3
"""handback_rollup.py — Aggregate HANDBACK metrics into a per-role cost/quality report.

## What this is

Backlog item #10 (docs/LANDSCAPE.md § Bonus-Task Backlog): a deterministic script that
reads one or more files (or stdin) containing HANDBACK YAML blocks — the format agents
actually emit in a harness session transcript, either fenced (```yaml ... ```) or bare,
one or many per source, optionally `---`-separated (the pattern shown in
`src/AGENTS.md` § HANDBACK Block Format) — and aggregates them per agent-role into a
compact table: count, total tokens, total cost, mean quality, mean duration. Where
`docs/SPEC.md` still defines a Cost Target Distribution (as of SPEC-2026-005 it does —
see COST_TARGET_DISTRIBUTION below, and `tests/test_handback_rollup.py`'s drift check
against the live SPEC.md text), each role's actual cost share is printed alongside its
target for comparison.

As of the SPEC clause-7 audit-JSONL work (`docs/PROTOCOL.md` §7a), this script also
accepts `--events <path...>`: one or more clause-7 audit JSONL files (written by
`scripts/audit_append.py`) read instead of, or alongside, HANDBACK YAML sources.
Only `handback_received` events are aggregated (the other six clause-7 event types are
silently skipped); see `parse_events()` below and §7a for the full input contract.

## Advisory-only discipline (docs/SPEC.md clause 3: "Python is advisory only")

This script REPORTS. It never GATES. It does not exit non-zero because of what the
HANDBACKs it read contain — a heavy-cost role, a quality dip, a distribution that
doesn't match target is information for a human or for Quality Engineer review, not a
build failure. The only non-zero exits are ordinary CLI usage errors (e.g. a source
file that doesn't exist) — never a judgment about the aggregated content. It owns no
dispatch, scheduling, or supervision, and every function below is a pure function of
its input text: no network calls, no filesystem writes, no global state.

## The `agent` field convention

The canonical HANDBACK schema (docs/specs/protocol-core-v1.0.yaml) has no `agent` or
`role` field — only the DELEGATE that originated a task names its target `agent`. To
attribute a HANDBACK's cost to a role, this script relies on a convention, not a schema
requirement: a HANDBACK MAY echo the originating DELEGATE's `agent` value back as its
own `agent:` (or `role:`) field. This is an ordinary forward-compatible extra field —
protocol-core-v1.0.yaml's own header states unknown fields "produce warnings, never
hard failures" — not a wire-format change, and this script makes no edit to that schema
or to renderer/scripts/claude-delegate-guard.py. HANDBACKs that omit the field are still
aggregated, just grouped under the synthetic role "unknown"; that omission alone is
never treated as malformed.

## Usage

    python3 scripts/handback_rollup.py session1.yaml session2.yaml
    python3 scripts/handback_rollup.py --json < session.log
    cat session.log | python3 scripts/handback_rollup.py

    # --events mode: read docs/SPEC.md clause-7 audit JSONL instead of (or
    # alongside) HANDBACK YAML sources — see docs/PROTOCOL.md §7a.
    python3 scripts/handback_rollup.py --events ~/.agentic-engineers/claude/sess-1/audit/events-2026-08-14.jsonl
    python3 scripts/handback_rollup.py session1.yaml --events events-2026-08-14.jsonl --json

## Dependencies

stdlib + PyYAML only. No network access.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import yaml

# -----------------------------------------------------------------------------
# Cost Target Distribution — cited from docs/SPEC.md § Agent Roster table, as of
# SPEC-2026-005 ("Rebalanced from the prior Haiku-Orchestrator distribution now
# that Orchestrator runs on Sonnet-tier"). Percentages are share of total COST.
#
# Deliberately a hardcoded literal, not parsed from docs/SPEC.md at runtime — this
# script is a pure function of its stdin/file input and must not depend on repo
# layout to run standalone (mirrors renderer/scripts/claude-delegate-guard.py's
# FRAMEWORK_ROLES literal, for the same reason). Drift between this literal and the
# live docs/SPEC.md text is instead caught by
# tests/test_handback_rollup.py::test_cost_target_distribution_matches_spec.
#
# If a future SPEC.md revision removes the Cost Target Distribution line entirely,
# that test should be updated to assert its absence, and this script's distribution
# comparison should be skipped rather than inventing a target (see docstring above).
COST_TARGET_DISTRIBUTION: Dict[str, float] = {
    "orchestrator": 55.0,
    "engineer": 18.0,
    "senior-engineer": 8.0,
    "quality-engineer": 8.0,
    "lead-engineer": 3.0,
    "model-engineer": 3.0,
    "principal-engineer": 3.0,
    "security-engineer": 2.0,
}

VALID_STATUSES = {"success", "failure", "partial", "blocked", "escalate"}

_FENCED_RE = re.compile(r"```(?:ya?ml)?\s*\n(.*?)\n```", re.DOTALL)
_DOC_SEP_RE = re.compile(r"(?m)^---\s*$")
_HANDBACK_HINT_RE = re.compile(r"handoff_type|^\s*type\s*:\s*HANDBACK\b", re.MULTILINE)


def iter_candidate_documents(text: str) -> List[str]:
    """Split free-form text into candidate YAML document strings.

    Recognizes two patterns actually seen in this repo's agent output:
      1. Fenced ```yaml ... ``` code blocks.
      2. Bare, optionally ``---``-separated YAML documents (the pattern shown in
         ``src/AGENTS.md`` § HANDBACK Block Format, which prefixes each HANDBACK
         with a leading ``---`` line).

    Candidates that show no sign of carrying a HANDBACK (no ``handoff_type`` or
    deprecated ``type: HANDBACK`` text) are dropped before ever attempting to
    parse them as YAML, so ordinary prose paragraphs are never misread as
    malformed documents.
    """
    candidates: List[str] = []
    remainder_parts: List[str] = []
    cursor = 0

    for m in _FENCED_RE.finditer(text):
        remainder_parts.append(text[cursor:m.start()])
        candidates.append(m.group(1))
        cursor = m.end()
    remainder_parts.append(text[cursor:])
    remainder = "\n".join(remainder_parts)

    for chunk in _DOC_SEP_RE.split(remainder):
        if chunk.strip():
            candidates.append(chunk)

    return [c for c in candidates if _HANDBACK_HINT_RE.search(c)]


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_handback(doc: Dict[str, Any]) -> List[str]:
    """Check the HANDBACK core fields this rollup depends on.

    Returns a list of error strings (empty == usable). Deliberately narrower than
    the full protocol-validator skill — this only validates the fields the rollup
    actually consumes (task_id, status, output, metrics.*).
    """
    errors: List[str] = []

    task_id = doc.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        errors.append("task_id: required, must be a non-empty string")

    status = doc.get("status")
    if status not in VALID_STATUSES:
        errors.append("status: must be one of %s (got %r)" % (sorted(VALID_STATUSES), status))

    if "output" not in doc:
        errors.append("output: required key missing")

    metrics = doc.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("metrics: required, must be a mapping")
    else:
        if not _is_number(metrics.get("quality")) or not (0.0 <= metrics.get("quality", -1) <= 1.0):
            errors.append("metrics.quality: required number in [0.0, 1.0]")
        if not _is_number(metrics.get("tokens")) or metrics.get("tokens", -1) < 0:
            errors.append("metrics.tokens: required non-negative number")
        if not _is_number(metrics.get("cost")) or metrics.get("cost", -1) < 0:
            errors.append("metrics.cost: required non-negative number")
        if not _is_number(metrics.get("duration_seconds")) or metrics.get("duration_seconds", -1) < 0:
            errors.append("metrics.duration_seconds: required non-negative number")

    return errors


def parse_handbacks(text: str, source: str = "<input>") -> Tuple[List[Dict[str, Any]], List[str]]:
    """Extract usable HANDBACK records and skip warnings from free-form text.

    Returns (records, warnings). Each record is
    ``{"task_id", "status", "agent", "metrics": {quality, tokens, cost, duration_seconds}}``.
    Malformed candidates (bad YAML, missing/invalid required fields) are skipped with
    a warning, never raised — this function never crashes on bad input.
    """
    records: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for i, candidate in enumerate(iter_candidate_documents(text)):
        try:
            doc = yaml.safe_load(candidate)
        except yaml.YAMLError as e:
            warnings.append("%s: candidate #%d: invalid YAML (%s)" % (source, i, str(e).splitlines()[0]))
            continue

        if not isinstance(doc, dict):
            # Looked like it mentioned HANDBACK but didn't parse to a mapping —
            # e.g. a prose sentence that happens to contain the word. Not treated
            # as malformed structured content.
            continue

        discriminator = doc.get("handoff_type") or doc.get("type")
        if discriminator != "HANDBACK":
            # Not a HANDBACK (e.g. a DELEGATE block, or an ESCALATION packet) —
            # correctly ignored, not a warning.
            continue

        errors = validate_handback(doc)
        if errors:
            task_id = doc.get("task_id", "<unknown task_id>")
            warnings.append(
                "%s: candidate #%d (task_id=%r): malformed HANDBACK skipped — %s"
                % (source, i, task_id, "; ".join(errors))
            )
            continue

        role = doc.get("agent") or doc.get("role") or "unknown"
        records.append({
            "task_id": doc["task_id"],
            "status": doc["status"],
            "agent": str(role),
            "metrics": {
                "quality": float(doc["metrics"]["quality"]),
                "tokens": float(doc["metrics"]["tokens"]),
                "cost": float(doc["metrics"]["cost"]),
                "duration_seconds": float(doc["metrics"]["duration_seconds"]),
            },
        })

    return records, warnings


def validate_event_record(doc: Dict[str, Any]) -> List[str]:
    """Check the fields this rollup depends on for a `handback_received` audit event.

    Narrower than the clause-7 contract `scripts/audit_append.py` enforces at write
    time — this only validates the fields the rollup actually consumes (task_id,
    status, agent_role, and the optional numeric fields).
    """
    errors: List[str] = []

    task_id = doc.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        errors.append("task_id: required, must be a non-empty string")

    status = doc.get("status")
    if status not in VALID_STATUSES:
        errors.append("status: must be one of %s (got %r)" % (sorted(VALID_STATUSES), status))

    role = doc.get("agent_role")
    if role is not None and not isinstance(role, str):
        errors.append("agent_role: must be a string when present")

    for key in ("tokens", "cost", "quality", "duration_seconds"):
        if key in doc and doc[key] is not None and not _is_number(doc[key]):
            errors.append("%s: must be a number" % key)

    return errors


def parse_events(text: str, source: str = "<input>") -> Tuple[List[Dict[str, Any]], List[str]]:
    """Extract usable `handback_received` records from a clause-7 audit JSONL log.

    Reads one JSON object per line (`docs/SPEC.md` clause 7 format, written by
    `scripts/audit_append.py`). Only `handback_received` events are aggregated — the
    other six clause-7 event types (`delegate_issued`, `subagent_spawned`,
    `gate_result`, `escalation`, `refusal`, `limit_exceeded`) are silently skipped,
    exactly like a DELEGATE block is silently skipped by `parse_handbacks()`.
    Malformed lines (invalid JSON, not an object, missing/invalid a required field)
    are skipped with a warning, never raised — this function never crashes on bad
    input, same discipline as `parse_handbacks()`.

    `quality` and `duration_seconds` are NOT part of the clause-7 required-field set
    (see `docs/PROTOCOL.md` §7a) — an event may optionally carry them (e.g. via
    `audit_append.py --extra`) to mirror the originating HANDBACK's full metrics; when
    absent they default to 0.0 so the record still fits the same
    `aggregate()`/`render_table()` shape `parse_handbacks()` produces. This is a known
    limitation of events-only rollups: a pure clause-7 event log carries no
    quality/duration signal unless the agent chose to attach it.
    """
    records: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for i, raw_line in enumerate(text.splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
        except json.JSONDecodeError as e:
            warnings.append("%s: line %d: invalid JSON (%s)" % (source, i + 1, str(e)))
            continue

        if not isinstance(doc, dict):
            warnings.append("%s: line %d: not a JSON object" % (source, i + 1))
            continue

        if doc.get("event") != "handback_received":
            # Not the event type this rollup aggregates — correctly ignored, not a warning.
            continue

        errors = validate_event_record(doc)
        if errors:
            task_id = doc.get("task_id", "<unknown task_id>")
            warnings.append(
                "%s: line %d (task_id=%r): malformed handback_received event skipped — %s"
                % (source, i + 1, task_id, "; ".join(errors))
            )
            continue

        role = doc.get("agent_role") or "unknown"
        records.append({
            "task_id": doc["task_id"],
            "status": doc["status"],
            "agent": str(role),
            "metrics": {
                "quality": float(doc.get("quality") or 0.0),
                "tokens": float(doc.get("tokens") or 0.0),
                "cost": float(doc.get("cost") or 0.0),
                "duration_seconds": float(doc.get("duration_seconds") or 0.0),
            },
        })

    return records, warnings


def aggregate(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Group records by role and compute count/totals/means. Pure function."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        groups.setdefault(r["agent"], []).append(r)

    stats: Dict[str, Dict[str, float]] = {}
    for role, items in groups.items():
        qualities = [i["metrics"]["quality"] for i in items]
        durations = [i["metrics"]["duration_seconds"] for i in items]
        stats[role] = {
            "count": len(items),
            "tokens": sum(i["metrics"]["tokens"] for i in items),
            "cost": sum(i["metrics"]["cost"] for i in items),
            "quality_mean": sum(qualities) / len(qualities),
            "duration_mean": sum(durations) / len(durations),
        }
    return stats


def render_table(stats: Dict[str, Dict[str, float]], warnings: List[str], show_distribution: bool = True) -> str:
    """Render the compact human-readable report. Pure function of its inputs."""
    lines: List[str] = []
    lines.append("HANDBACK Cost/Quality Rollup — advisory report, never gates CI/CD")
    lines.append("=" * 78)

    if not stats:
        lines.append("(no usable HANDBACK records found)")
    else:
        header = "%-20s %8s %12s %12s %13s %16s" % (
            "Role", "Count", "Tokens", "Cost", "Avg Quality", "Avg Duration(s)"
        )
        lines.append(header)
        lines.append("-" * len(header))
        total_count = total_tokens = total_cost = 0.0
        weighted_quality = weighted_duration = 0.0
        for role in sorted(stats, key=lambda r: -stats[r]["cost"]):
            s = stats[role]
            lines.append("%-20s %8d %12.0f %12s %13.2f %16.1f" % (
                role, int(s["count"]), s["tokens"], "$%.2f" % s["cost"], s["quality_mean"], s["duration_mean"]
            ))
            total_count += s["count"]
            total_tokens += s["tokens"]
            total_cost += s["cost"]
            weighted_quality += s["quality_mean"] * s["count"]
            weighted_duration += s["duration_mean"] * s["count"]
        lines.append("-" * len(header))
        lines.append("%-20s %8d %12.0f %12s %13.2f %16.1f" % (
            "TOTAL", int(total_count), total_tokens, "$%.2f" % total_cost,
            (weighted_quality / total_count) if total_count else 0.0,
            (weighted_duration / total_count) if total_count else 0.0,
        ))

        if show_distribution and total_cost > 0:
            lines.append("")
            lines.append("Cost Target Distribution comparison (docs/SPEC.md, as of SPEC-2026-005):")
            dist_header = "%-20s %10s %10s %10s" % ("Role", "Actual %", "Target %", "Delta")
            lines.append(dist_header)
            lines.append("-" * len(dist_header))
            for role in sorted(stats, key=lambda r: -stats[r]["cost"]):
                actual_pct = 100.0 * stats[role]["cost"] / total_cost
                target_pct = COST_TARGET_DISTRIBUTION.get(role)
                if target_pct is None:
                    lines.append("%-20s %9.1f%% %10s %10s" % (role, actual_pct, "n/a", "n/a"))
                else:
                    lines.append("%-20s %9.1f%% %9.1f%% %+9.1f%%" % (
                        role, actual_pct, target_pct, actual_pct - target_pct
                    ))

    if warnings:
        lines.append("")
        lines.append("Warnings (%d record(s) skipped):" % len(warnings))
        for w in warnings:
            lines.append("  - %s" % w)

    return "\n".join(lines)


def render_json(stats: Dict[str, Dict[str, float]], warnings: List[str]) -> str:
    """Render the machine-readable report. Pure function of its inputs."""
    total_cost = sum(s["cost"] for s in stats.values())
    roles_out = {}
    for role, s in stats.items():
        entry = dict(s)
        if total_cost > 0:
            entry["actual_cost_pct"] = round(100.0 * s["cost"] / total_cost, 2)
        entry["target_cost_pct"] = COST_TARGET_DISTRIBUTION.get(role)
        roles_out[role] = entry
    payload = {
        "roles": roles_out,
        "totals": {
            "count": sum(s["count"] for s in stats.values()),
            "tokens": sum(s["tokens"] for s in stats.values()),
            "cost": total_cost,
        },
        "warnings": warnings,
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _read_source(source: str) -> Tuple[str, str]:
    """Return (label, text) for a CLI source argument ('-' or a file path)."""
    if source == "-":
        return "<stdin>", sys.stdin.read()
    with open(source, "r", encoding="utf-8") as f:
        return source, f.read()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate HANDBACK YAML blocks into a per-role cost/quality report. Advisory only — never gates."
    )
    parser.add_argument("sources", nargs="*", help="HANDBACK YAML files to read (use '-' or omit for stdin)")
    parser.add_argument(
        "--events", nargs="*", default=None,
        help="clause-7 audit JSONL files to read (docs/PROTOCOL.md §7a) — mixable with positional YAML sources",
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON instead of a table")
    args = parser.parse_args(argv)

    sources = list(args.sources or [])
    event_sources = list(args.events) if args.events is not None else []
    if not sources and not event_sources:
        sources = ["-"]

    all_records: List[Dict[str, Any]] = []
    all_warnings: List[str] = []
    for source in sources:
        try:
            label, text = _read_source(source)
        except OSError as e:
            print("error: could not read %r: %s" % (source, e), file=sys.stderr)
            return 2
        records, warnings = parse_handbacks(text, source=label)
        all_records.extend(records)
        all_warnings.extend(warnings)

    for source in event_sources:
        try:
            label, text = _read_source(source)
        except OSError as e:
            print("error: could not read %r: %s" % (source, e), file=sys.stderr)
            return 2
        records, warnings = parse_events(text, source=label)
        all_records.extend(records)
        all_warnings.extend(warnings)

    stats = aggregate(all_records)

    if args.as_json:
        print(render_json(stats, all_warnings))
    else:
        print(render_table(stats, all_warnings))

    return 0


if __name__ == "__main__":
    sys.exit(main())
