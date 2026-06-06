# -*- coding: utf-8 -*-
"""
monitor_budgets.py — per-task budget monitor backed by token-budgets.yaml.

Provides BudgetMonitor: given an actual token usage count and a role,
returns a structured BudgetStatus indicating OK / WARN / ERROR / ESCALATE.

CLI usage::

    python -m src.skills.cost-aggregation.scripts.monitor_budgets \\
        --role engineer --tokens 1300

    python -m src.skills.cost-aggregation.scripts.monitor_budgets \\
        --report artifacts/metrics.jsonl

Programmatic usage::

    monitor = BudgetMonitor.from_default_config()
    status = monitor.check("engineer", tokens_used=1800)
    if status.escalated:
        ...
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class BudgetLevel(str, Enum):
    OK = "ok"
    WARN = "warn"
    ERROR = "error"
    ESCALATE = "escalate"


@dataclass
class BudgetStatus:
    role: str
    budget: int
    tokens_used: int
    pct: float
    level: BudgetLevel
    message: str

    @property
    def escalated(self) -> bool:
        return self.level == BudgetLevel.ESCALATE

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["level"] = self.level.value
        return d


@dataclass
class RoleBudget:
    role: str
    budget: int
    warn_pct: float
    error_pct: float
    escalate_pct: float
    model: str = ""
    rationale: str = ""


# ---------------------------------------------------------------------------
# Monitor
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    # src/skills/cost-aggregation/scripts/monitor_budgets.py → repo root
    return Path(__file__).resolve().parents[4]


class BudgetMonitor:
    """Evaluate token usage against per-role budgets + thresholds."""

    def __init__(self, role_budgets: Dict[str, RoleBudget]) -> None:
        if not role_budgets:
            raise ValueError("BudgetMonitor requires at least one role budget")
        self._roles: Dict[str, RoleBudget] = dict(role_budgets)

    # -- construction -------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: Path) -> "BudgetMonitor":
        with open(path, "r") as fh:
            data = yaml.safe_load(fh) or {}
        defaults = data.get("defaults", {}) or {}
        warn = float(defaults.get("warn_pct", 80))
        err = float(defaults.get("error_pct", 100))
        esc = float(defaults.get("escalate_pct", 120))

        roles: Dict[str, RoleBudget] = {}
        for role, cfg in (data.get("roles", {}) or {}).items():
            overrides = (cfg.get("overrides") or {}) if isinstance(cfg, dict) else {}
            roles[role] = RoleBudget(
                role=role,
                budget=int(cfg.get("budget", 1500)),
                warn_pct=float(overrides.get("warn_pct", warn)),
                error_pct=float(overrides.get("error_pct", err)),
                escalate_pct=float(overrides.get("escalate_pct", esc)),
                model=str(cfg.get("model", "")),
                rationale=str(cfg.get("rationale", "")).strip(),
            )
        return cls(roles)

    @classmethod
    def from_default_config(cls) -> "BudgetMonitor":
        return cls.from_yaml(_repo_root() / "src" / "config" / "token-budgets.yaml")

    # -- queries ------------------------------------------------------------

    @property
    def roles(self) -> List[str]:
        return list(self._roles)

    def role_budget(self, role: str) -> RoleBudget:
        if role not in self._roles:
            raise KeyError(f"Unknown role '{role}'. Known: {sorted(self._roles)}")
        return self._roles[role]

    # -- evaluation ---------------------------------------------------------

    def check(self, role: str, tokens_used: int) -> BudgetStatus:
        if tokens_used < 0:
            raise ValueError("tokens_used must be >= 0")
        rb = self.role_budget(role)
        pct = (tokens_used / rb.budget) * 100.0 if rb.budget > 0 else 0.0
        if pct >= rb.escalate_pct:
            level = BudgetLevel.ESCALATE
            msg = (
                f"[ESCALATE] {role}: {tokens_used}/{rb.budget} tokens "
                f"({pct:.1f}% ≥ {rb.escalate_pct:.0f}%) — escalate to Principal."
            )
        elif pct >= rb.error_pct:
            level = BudgetLevel.ERROR
            msg = (
                f"[ERROR] {role}: {tokens_used}/{rb.budget} tokens "
                f"({pct:.1f}% ≥ {rb.error_pct:.0f}%) — budget exceeded."
            )
        elif pct >= rb.warn_pct:
            level = BudgetLevel.WARN
            msg = (
                f"[WARN] {role}: {tokens_used}/{rb.budget} tokens "
                f"({pct:.1f}% ≥ {rb.warn_pct:.0f}%) — approaching cap."
            )
        else:
            level = BudgetLevel.OK
            msg = f"[OK] {role}: {tokens_used}/{rb.budget} tokens ({pct:.1f}%)."
        return BudgetStatus(
            role=role,
            budget=rb.budget,
            tokens_used=tokens_used,
            pct=round(pct, 2),
            level=level,
            message=msg,
        )

    def check_batch(self, records: Iterable[Dict[str, Any]]) -> List[BudgetStatus]:
        """Evaluate a sequence of {'role': ..., 'tokens_used': ...} records.

        Records missing/unknown roles are silently skipped — monitoring
        should never crash on a malformed metrics line.
        """
        out: List[BudgetStatus] = []
        for rec in records:
            role = rec.get("role") or rec.get("agent")
            tokens = rec.get("tokens_used") or rec.get("tokens") or 0
            if not role or role not in self._roles:
                continue
            try:
                out.append(self.check(role, int(tokens)))
            except (TypeError, ValueError):
                continue
        return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="monitor_budgets",
        description="Check per-task token usage against role budgets.",
    )
    ap.add_argument("--role", help="Role to check (e.g. engineer)")
    ap.add_argument("--tokens", type=int, help="Tokens used by the task")
    ap.add_argument("--report", help="Path to JSONL metrics file to evaluate")
    ap.add_argument("--config", help="Path to token-budgets.yaml override")
    ap.add_argument("--json", action="store_true", help="Emit JSON output")
    args = ap.parse_args(argv)

    monitor = (
        BudgetMonitor.from_yaml(Path(args.config))
        if args.config
        else BudgetMonitor.from_default_config()
    )

    statuses: List[BudgetStatus] = []
    if args.report:
        statuses = monitor.check_batch(_read_jsonl(Path(args.report)))
    elif args.role and args.tokens is not None:
        statuses = [monitor.check(args.role, args.tokens)]
    else:
        ap.error("Provide --role and --tokens, or --report PATH")
        return 2

    if args.json:
        print(json.dumps([s.as_dict() for s in statuses], indent=2))
    else:
        for s in statuses:
            print(s.message)

    # Exit non-zero if any escalations
    return 0 if not any(s.escalated for s in statuses) else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
