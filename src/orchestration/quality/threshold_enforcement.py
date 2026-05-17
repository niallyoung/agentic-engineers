"""
Threshold Enforcer — Enforce quality thresholds before task completion.

Defines per-metric thresholds, evaluates scores against them, escalates
violations, and generates compliance reports.

Usage::

    enforcer = ThresholdEnforcer()
    result = enforcer.evaluate(task_type="code", score=78.0)
    if not result.passed:
        for v in result.violations:
            print(v.message)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Default thresholds (from QUALITY-BASELINES.md)
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLDS: Dict[str, float] = {
    # task_type -> minimum acceptable score
    "code": 90.0,
    "test": 90.0,
    "documentation": 85.0,
    "performance": 85.0,
    "security": 95.0,
    "default": 85.0,
}

# Escalation threshold: if score is this far below the minimum, escalate
ESCALATION_GAP = 10.0


class ViolationSeverity(str, Enum):
    WARNING = "warning"    # below threshold but within escalation gap
    ERROR = "error"        # at or below escalation threshold
    CRITICAL = "critical"  # security task below threshold


@dataclass
class ThresholdViolation:
    task_type: str
    score: float
    threshold: float
    gap: float              # threshold - score (positive = below threshold)
    severity: ViolationSeverity
    message: str
    escalate: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class EnforcementResult:
    task_type: str
    score: float
    threshold: float
    passed: bool
    violations: List[ThresholdViolation]
    compliance_pct: float   # score / threshold * 100 (capped at 100)
    recommendation: str
    timestamp: float = field(default_factory=time.time)

    @property
    def requires_escalation(self) -> bool:
        return any(v.escalate for v in self.violations)


@dataclass
class ComplianceRecord:
    """Historical record of a threshold evaluation."""
    task_id: str
    result: EnforcementResult


class ThresholdEnforcer:
    """
    Evaluates quality scores against defined thresholds and tracks compliance.
    """

    def __init__(self, thresholds: Optional[Dict[str, float]] = None) -> None:
        self._thresholds: Dict[str, float] = dict(DEFAULT_THRESHOLDS)
        if thresholds:
            self._thresholds.update(thresholds)
        self._history: List[ComplianceRecord] = []

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_threshold(self, task_type: str, minimum: float) -> None:
        """Override the threshold for a task type."""
        if not 0.0 <= minimum <= 100.0:
            raise ValueError(f"Threshold must be 0-100, got {minimum}")
        self._thresholds[task_type] = minimum

    def get_threshold(self, task_type: str) -> float:
        return self._thresholds.get(task_type, self._thresholds["default"])

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        task_type: str,
        score: float,
        task_id: Optional[str] = None,
    ) -> EnforcementResult:
        """Evaluate a score against the threshold for a task type."""
        if not 0.0 <= score <= 100.0:
            raise ValueError(f"score must be 0-100, got {score}")

        threshold = self.get_threshold(task_type)
        passed = score >= threshold
        violations: List[ThresholdViolation] = []

        if not passed:
            gap = threshold - score
            is_security = task_type == "security"

            if is_security:
                severity = ViolationSeverity.CRITICAL
                escalate = True
            elif gap >= ESCALATION_GAP:
                severity = ViolationSeverity.ERROR
                escalate = True
            else:
                severity = ViolationSeverity.WARNING
                escalate = False

            violations.append(
                ThresholdViolation(
                    task_type=task_type,
                    score=score,
                    threshold=threshold,
                    gap=gap,
                    severity=severity,
                    message=(
                        f"[{severity.value.upper()}] {task_type} score {score:.1f} "
                        f"is below threshold {threshold:.1f} (gap: {gap:.1f})"
                    ),
                    escalate=escalate,
                )
            )

        compliance_pct = min(100.0, score / threshold * 100) if threshold > 0 else 100.0

        if passed:
            recommendation = f"PASS — {task_type} score {score:.1f} meets threshold {threshold:.1f}"
        elif violations and violations[0].escalate:
            recommendation = (
                f"ESCALATE — {task_type} score {score:.1f} critically below "
                f"threshold {threshold:.1f}; route to Lead/Principal Engineer"
            )
        else:
            recommendation = (
                f"REWORK — {task_type} score {score:.1f} below threshold {threshold:.1f}; "
                f"request rework before proceeding"
            )

        result = EnforcementResult(
            task_type=task_type,
            score=score,
            threshold=threshold,
            passed=passed,
            violations=violations,
            compliance_pct=compliance_pct,
            recommendation=recommendation,
        )

        if task_id:
            self._history.append(ComplianceRecord(task_id=task_id, result=result))

        return result

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def compliance_report(self) -> Dict[str, Any]:
        """Generate a compliance report across all recorded evaluations."""
        if not self._history:
            return {"total": 0, "passed": 0, "failed": 0, "compliance_rate": None}

        total = len(self._history)
        passed = sum(1 for r in self._history if r.result.passed)
        failed = total - passed
        escalations = sum(1 for r in self._history if r.result.requires_escalation)
        avg_score = sum(r.result.score for r in self._history) / total

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "escalations": escalations,
            "compliance_rate": passed / total * 100,
            "avg_score": avg_score,
            "history": [
                {
                    "task_id": r.task_id,
                    "task_type": r.result.task_type,
                    "score": r.result.score,
                    "threshold": r.result.threshold,
                    "passed": r.result.passed,
                }
                for r in self._history
            ],
        }

    def violations_summary(self) -> List[Dict[str, Any]]:
        """Return all violations across history."""
        out = []
        for record in self._history:
            for v in record.result.violations:
                out.append(
                    {
                        "task_id": record.task_id,
                        "task_type": v.task_type,
                        "score": v.score,
                        "threshold": v.threshold,
                        "gap": v.gap,
                        "severity": v.severity.value,
                        "escalate": v.escalate,
                        "message": v.message,
                    }
                )
        return out
