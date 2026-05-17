"""
ThresholdEnforcer - Quality threshold enforcement for the Orchestrator.

Defines quality baselines by task type, enforces minimum quality before
proceeding, escalates low-quality tasks, and tracks quality trends over time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & constants
# ---------------------------------------------------------------------------

class EnforcementAction(Enum):
    PROCEED = "PROCEED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    REWORK = "REWORK"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"


class TaskType(Enum):
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    CODE_REVIEW = "code_review"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    INFRASTRUCTURE = "infrastructure"
    DEFAULT = "default"


# Quality thresholds per task type
# (proceed_min, manual_review_min, rework_min, escalate_below)
QUALITY_THRESHOLDS: Dict[TaskType, Tuple[int, int, int, int]] = {
    TaskType.SECURITY:       (95, 90, 80, 80),
    TaskType.ARCHITECTURE:   (90, 85, 75, 75),
    TaskType.FEATURE:        (85, 75, 65, 65),
    TaskType.BUGFIX:         (85, 75, 65, 65),
    TaskType.REFACTOR:       (80, 70, 60, 60),
    TaskType.CODE_REVIEW:    (85, 75, 65, 65),
    TaskType.TESTING:        (85, 75, 65, 65),
    TaskType.DOCUMENTATION:  (75, 65, 55, 55),
    TaskType.INFRASTRUCTURE: (85, 75, 65, 65),
    TaskType.DEFAULT:        (80, 70, 60, 60),
}

# Alert thresholds for quality degradation
DEGRADATION_ALERT_THRESHOLD = 10.0   # points drop triggers alert
DEGRADATION_WINDOW_DAYS = 7


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ThresholdResult:
    """Result of a threshold enforcement check."""
    action: EnforcementAction
    quality_score: float
    task_type: TaskType
    threshold_used: int          # the proceed_min threshold that was applied
    rationale: str
    escalation_target: Optional[str] = None
    rework_guidance: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def should_proceed(self) -> bool:
        return self.action == EnforcementAction.PROCEED

    @property
    def requires_escalation(self) -> bool:
        return self.action == EnforcementAction.ESCALATE

    def to_dict(self) -> Dict:
        return {
            "action": self.action.value,
            "quality_score": self.quality_score,
            "task_type": self.task_type.value,
            "threshold_used": self.threshold_used,
            "rationale": self.rationale,
            "escalation_target": self.escalation_target,
            "rework_guidance": self.rework_guidance,
            "timestamp": self.timestamp,
        }


@dataclass
class QualityTrendPoint:
    date: str
    avg_quality: float
    task_count: int


@dataclass
class DegradationAlert:
    agent_role: str
    task_type: str
    previous_avg: float
    current_avg: float
    drop: float
    alert_level: str       # WARNING | CRITICAL
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "agent_role": self.agent_role,
            "task_type": self.task_type,
            "previous_avg": self.previous_avg,
            "current_avg": self.current_avg,
            "drop": self.drop,
            "alert_level": self.alert_level,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# ThresholdEnforcer
# ---------------------------------------------------------------------------

class ThresholdEnforcer:
    """
    Enforce quality thresholds and detect quality degradation.

    Usage:
        enforcer = ThresholdEnforcer()
        result = enforcer.enforce(quality_score=82, task_type=TaskType.FEATURE)
        if result.action == EnforcementAction.REWORK:
            ...
    """

    def __init__(self, custom_thresholds: Optional[Dict[TaskType, Tuple[int, int, int, int]]] = None):
        self._thresholds = dict(QUALITY_THRESHOLDS)
        if custom_thresholds:
            self._thresholds.update(custom_thresholds)
        # In-memory quality history: {(agent_role, task_type): [quality_score, ...]}
        self._history: Dict[Tuple[str, str], List[float]] = {}
        self._alerts: List[DegradationAlert] = []

    # ------------------------------------------------------------------
    # Threshold enforcement
    # ------------------------------------------------------------------

    def enforce(
        self,
        quality_score: float,
        task_type: TaskType = TaskType.DEFAULT,
        retry_count: int = 0,
        max_retries: int = 2,
        has_critical_issues: bool = False,
        agent_role: str = "unknown",
    ) -> ThresholdResult:
        """
        Evaluate quality score against thresholds and return enforcement action.

        Args:
            quality_score: 0-100 quality score from Quality Engineer.
            task_type: Type of task being evaluated.
            retry_count: How many times this task has already been retried.
            max_retries: Maximum allowed retries before escalation.
            has_critical_issues: If True, force ESCALATE regardless of score.
            agent_role: Agent that produced the work (for history tracking).

        Returns:
            ThresholdResult with action and rationale.
        """
        thresholds = self._thresholds.get(task_type, self._thresholds[TaskType.DEFAULT])
        proceed_min, manual_min, rework_min, escalate_below = thresholds

        # Record for trend tracking
        self._record_quality(agent_role, task_type.value, quality_score)

        # Critical issues always escalate
        if has_critical_issues:
            return ThresholdResult(
                action=EnforcementAction.ESCALATE,
                quality_score=quality_score,
                task_type=task_type,
                threshold_used=proceed_min,
                rationale="Critical issues detected — immediate escalation required.",
                escalation_target="principal_engineer",
            )

        # Score-based routing
        if quality_score >= proceed_min:
            return ThresholdResult(
                action=EnforcementAction.PROCEED,
                quality_score=quality_score,
                task_type=task_type,
                threshold_used=proceed_min,
                rationale=f"Quality {quality_score:.0f} ≥ threshold {proceed_min} → PROCEED.",
            )

        if quality_score >= manual_min:
            return ThresholdResult(
                action=EnforcementAction.MANUAL_REVIEW,
                quality_score=quality_score,
                task_type=task_type,
                threshold_used=proceed_min,
                rationale=(
                    f"Quality {quality_score:.0f} in manual-review band "
                    f"[{manual_min}, {proceed_min}) → MANUAL_REVIEW."
                ),
                escalation_target="lead_engineer",
            )

        if quality_score >= rework_min:
            if retry_count >= max_retries:
                return ThresholdResult(
                    action=EnforcementAction.ESCALATE,
                    quality_score=quality_score,
                    task_type=task_type,
                    threshold_used=proceed_min,
                    rationale=(
                        f"Quality {quality_score:.0f} in rework band but max retries "
                        f"({max_retries}) reached → ESCALATE."
                    ),
                    escalation_target="principal_engineer",
                )
            return ThresholdResult(
                action=EnforcementAction.REWORK,
                quality_score=quality_score,
                task_type=task_type,
                threshold_used=proceed_min,
                rationale=(
                    f"Quality {quality_score:.0f} in rework band "
                    f"[{rework_min}, {manual_min}) → REWORK (attempt {retry_count + 1}/{max_retries})."
                ),
                rework_guidance=self._build_rework_guidance(quality_score, task_type),
            )

        # Below escalate_below
        return ThresholdResult(
            action=EnforcementAction.ESCALATE,
            quality_score=quality_score,
            task_type=task_type,
            threshold_used=proceed_min,
            rationale=f"Quality {quality_score:.0f} < {escalate_below} → ESCALATE.",
            escalation_target="principal_engineer",
        )

    def infer_task_type(self, delegate: Dict) -> TaskType:
        """Infer TaskType from DELEGATE fields."""
        scope = (delegate.get("scope", "") or "").lower()
        description = str(delegate.get("description", "")).lower()
        text = scope + " " + description

        if any(kw in text for kw in ("security", "auth", "crypt", "vuln")):
            return TaskType.SECURITY
        if any(kw in text for kw in ("architecture", "cross-service", "cross_service")):
            return TaskType.ARCHITECTURE
        if any(kw in text for kw in ("code review", "pr review", "pull request")):
            return TaskType.CODE_REVIEW
        if any(kw in text for kw in ("test", "coverage", "spec")):
            return TaskType.TESTING
        if any(kw in text for kw in ("refactor", "clean", "restructure")):
            return TaskType.REFACTOR
        if any(kw in text for kw in ("bug", "fix", "patch", "hotfix")):
            return TaskType.BUGFIX
        if any(kw in text for kw in ("infra", "deploy", "pipeline", "ci", "cd")):
            return TaskType.INFRASTRUCTURE
        if any(kw in text for kw in ("doc", "readme", "changelog")):
            return TaskType.DOCUMENTATION
        if any(kw in text for kw in ("feature", "implement", "add", "build", "create")):
            return TaskType.FEATURE
        return TaskType.DEFAULT

    # ------------------------------------------------------------------
    # Quality trend tracking
    # ------------------------------------------------------------------

    def _record_quality(self, agent_role: str, task_type: str, quality_score: float) -> None:
        key = (agent_role, task_type)
        self._history.setdefault(key, []).append(quality_score)

    def check_degradation(self, agent_role: str, task_type: str) -> Optional[DegradationAlert]:
        """
        Check if quality has degraded significantly for an agent/task-type combo.

        Returns a DegradationAlert if degradation detected, else None.
        """
        key = (agent_role, task_type)
        scores = self._history.get(key, [])
        if len(scores) < 4:
            return None  # not enough data

        # Compare first half vs second half
        mid = len(scores) // 2
        prev_avg = sum(scores[:mid]) / mid
        curr_avg = sum(scores[mid:]) / (len(scores) - mid)
        drop = prev_avg - curr_avg

        if drop >= DEGRADATION_ALERT_THRESHOLD:
            level = "CRITICAL" if drop >= 20 else "WARNING"
            alert = DegradationAlert(
                agent_role=agent_role,
                task_type=task_type,
                previous_avg=round(prev_avg, 1),
                current_avg=round(curr_avg, 1),
                drop=round(drop, 1),
                alert_level=level,
            )
            self._alerts.append(alert)
            logger.warning(
                "Quality degradation %s: %s/%s dropped %.1f points (%.1f → %.1f)",
                level, agent_role, task_type, drop, prev_avg, curr_avg,
            )
            return alert
        return None

    def all_alerts(self) -> List[DegradationAlert]:
        return list(self._alerts)

    def quality_history(self, agent_role: str, task_type: str) -> List[float]:
        return list(self._history.get((agent_role, task_type), []))

    def get_threshold(self, task_type: TaskType) -> Tuple[int, int, int, int]:
        return self._thresholds.get(task_type, self._thresholds[TaskType.DEFAULT])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_rework_guidance(self, quality_score: float, task_type: TaskType) -> str:
        gap = 80 - quality_score  # rough gap to acceptable
        guidance = [f"Quality gap: ~{gap:.0f} points to acceptable threshold."]
        if task_type == TaskType.SECURITY:
            guidance.append("Ensure all security findings are addressed.")
        elif task_type == TaskType.TESTING:
            guidance.append("Increase test coverage and add edge-case tests.")
        elif task_type == TaskType.FEATURE:
            guidance.append("Review success criteria and ensure all are met.")
        else:
            guidance.append("Review Quality Engineer feedback and address all findings.")
        return " ".join(guidance)
