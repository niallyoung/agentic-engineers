# -*- coding: utf-8 -*-
"""
cost_dashboard.py — aggregate cost+budget signal across recent task metrics.

A thin CLI wrapper that combines:
  - BudgetMonitor (per-role budget evaluation)
  - Aggregate spend by role / model
  - Top offenders (tasks over budget)

Designed to be human-readable on the terminal and machine-readable with --json.

Usage::

    python -m src.skills.cost-aggregation.scripts.cost_dashboard \\
        --metrics artifacts/metrics.jsonl

    # Machine-readable:
    python -m src.skills.cost-aggregation.scripts.cost_dashboard \\
        --metrics artifacts/metrics.jsonl --json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    # Preferred: when imported via the conftest-mapped package path
    # (`src.skills.cost-aggregation.scripts.monitor_budgets`)
    import importlib
    _mb = importlib.import_module(
        "src.skills.cost-aggregation.scripts.monitor_budgets"
    )
except ModuleNotFoundError:  # pragma: no cover — script-mode fallback
    import importlib
    _mb = importlib.import_module("monitor_budgets")

BudgetMonitor = _mb.BudgetMonitor
BudgetLevel = _mb.BudgetLevel
BudgetStatus = _mb.BudgetStatus
_read_jsonl = _mb._read_jsonl


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

@dataclass
class RoleAggregate:
    role: str
    task_count: int = 0
    total_tokens: int = 0
    avg_tokens: float = 0.0
    over_budget_count: int = 0
    escalations: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def aggregate(records: Iterable[Dict[str, Any]], monitor: BudgetMonitor) -> Dict[str, RoleAggregate]:
    """Group records by role and compute aggregate stats + budget evaluations."""
    by_role: Dict[str, List[int]] = defaultdict(list)
    for rec in records:
        role = rec.get("role") or rec.get("agent")
        tokens = rec.get("tokens_used") or rec.get("tokens") or 0
        if not role or role not in monitor.roles:
            continue
        try:
            by_role[role].append(int(tokens))
        except (TypeError, ValueError):
            continue

    out: Dict[str, RoleAggregate] = {}
    for role, token_list in by_role.items():
        agg = RoleAggregate(
            role=role,
            task_count=len(token_list),
            total_tokens=sum(token_list),
            avg_tokens=round(sum(token_list) / len(token_list), 2) if token_list else 0.0,
        )
        for t in token_list:
            st = monitor.check(role, t)
            if st.level in (BudgetLevel.ERROR, BudgetLevel.ESCALATE):
                agg.over_budget_count += 1
            if st.level == BudgetLevel.ESCALATE:
                agg.escalations += 1
        out[role] = agg
    return out


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_table(aggregates: Dict[str, RoleAggregate], monitor: BudgetMonitor) -> str:
    if not aggregates:
        return "(no task records found)"
    headers = ["role", "tasks", "avg_tok", "budget", "over", "escalated"]
    rows = []
    for role in sorted(aggregates):
        a = aggregates[role]
        rb = monitor.role_budget(role)
        rows.append([
            role,
            str(a.task_count),
            f"{a.avg_tokens:.0f}",
            str(rb.budget),
            str(a.over_budget_count),
            str(a.escalations),
        ])
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    def line(cells):
        return "  ".join(c.ljust(widths[i]) for i, c in enumerate(cells))
    sep = "  ".join("-" * w for w in widths)
    return "\n".join([line(headers), sep, *(line(r) for r in rows)])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="cost_dashboard",
        description="Aggregate cost + budget signal across recent task metrics.",
    )
    ap.add_argument("--metrics", required=True, help="JSONL metrics file (one task per line)")
    ap.add_argument("--config", help="Override path to token-budgets.yaml")
    ap.add_argument("--json", action="store_true", help="Emit JSON output")
    args = ap.parse_args(argv)

    monitor = (
        BudgetMonitor.from_yaml(Path(args.config))
        if args.config
        else BudgetMonitor.from_default_config()
    )
    records = _read_jsonl(Path(args.metrics))
    aggregates = aggregate(records, monitor)

    if args.json:
        print(json.dumps({r: a.as_dict() for r, a in aggregates.items()}, indent=2))
    else:
        print(render_table(aggregates, monitor))

    total_esc = sum(a.escalations for a in aggregates.values())
    return 0 if total_esc == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
