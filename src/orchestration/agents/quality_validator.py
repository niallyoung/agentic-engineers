"""
Quality Validator — Three-Layer Quality Gate System

Implements Phase 3 of Orchestrator Automation (Quality Gates Integration).

Architecture:
  Layer 1 — Pre-routing validation
      Validates DELEGATE structure and syntax before the task reaches an agent.
      Checks: required fields, task_id format, role validity, YAML hygiene.

  Layer 2 — Task-routing validation
      Validates task quality for intelligent routing decisions.
      Checks: scope clarity, effort/scope consistency, plan presence & quality.

  Layer 3 — Post-completion validation
      Validates HANDBACK structure after a task completes.
      Checks: required HANDBACK fields, status validity, deliverables presence.

Routing decisions based on composite quality score (0–100):
  HIGH    (80–100) → direct dispatch to role agent
  MEDIUM  (60–79)  → route to Lead Engineer for refinement
  LOW     (40–59)  → route to Principal Engineer for design
  CRITICAL (<40 or critical failure) → escalate with detailed analysis

Design reference: docs/architecture-quality-gates-5103.md
"""

import re
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─── Constants ────────────────────────────────────────────────────────────────

VALID_ROLES = {
    "engineer",
    "senior_engineer",
    "lead_engineer",
    "principal_engineer",
    "quality_engineer",
    "model_engineer",
    "security_engineer",
    "orchestrator",
}

VALID_EFFORT_VALUES = {"low", "medium", "high", "max", "epic"}

# Per handback-schema.yaml: complete | failed | partial | blocked | escalate
VALID_HANDBACK_STATUSES = {"complete", "failed", "partial", "blocked", "escalate"}

TASK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-]{0,62}[a-z0-9]$")

# Minimum meaningful word count for a scope description
SCOPE_MIN_WORD_COUNT = 5

# Weight for each validation category (must sum to 100)
LAYER1_WEIGHT = 40   # structural integrity is non-negotiable
LAYER2_WEIGHT = 35   # routing quality matters a lot
LAYER3_WEIGHT = 25   # post-completion is confirmatory


# ─── Data Classes ─────────────────────────────────────────────────────────────


class Severity(str, Enum):
    """Severity of a validation finding."""
    CRITICAL = "critical"   # blocks routing/completion
    ERROR    = "error"      # degrades quality score significantly
    WARNING  = "warning"    # minor deduction
    INFO     = "info"       # no score impact, informational only


class RoutingDecision(str, Enum):
    """Recommended routing action based on quality score."""
    HIGH     = "high"      # 80-100: direct dispatch
    MEDIUM   = "medium"    # 60-79:  route to Lead Engineer
    LOW      = "low"       # 40-59:  route to Principal Engineer
    CRITICAL = "critical"  # <40:    escalate


@dataclass
class ValidationFinding:
    """A single finding from a validation check."""
    layer: int           # 1, 2, or 3
    check: str           # machine-readable check name
    severity: Severity
    message: str
    field: Optional[str] = None   # offending YAML field, if applicable
    score_deduction: int = 0      # points removed from quality score

    def as_dict(self) -> Dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class ValidationResult:
    """Aggregated result of one or more validation layers."""
    task_id: Optional[str]
    layer: int                              # highest layer run (1/2/3)
    quality_score: int                      # 0-100 composite score
    routing_decision: RoutingDecision
    findings: List[ValidationFinding] = field(default_factory=list)
    passed: bool = True
    validated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Per-layer scores (set by QualityValidator)
    layer1_score: Optional[int] = None
    layer2_score: Optional[int] = None
    layer3_score: Optional[int] = None

    @property
    def critical_findings(self) -> List[ValidationFinding]:
        return [f for f in self.findings if f.severity == Severity.CRITICAL]

    @property
    def error_findings(self) -> List[ValidationFinding]:
        return [f for f in self.findings if f.severity == Severity.ERROR]

    @property
    def warning_findings(self) -> List[ValidationFinding]:
        return [f for f in self.findings if f.severity == Severity.WARNING]

    def as_dict(self) -> Dict:
        d = asdict(self)
        d["routing_decision"] = self.routing_decision.value
        d["findings"] = [f.as_dict() for f in self.findings]
        return d


# ─── Quality Validator ────────────────────────────────────────────────────────


class QualityValidator:
    """
    Three-layer quality gate for DELEGATE and HANDBACK YAML blocks.

    Usage::

        validator = QualityValidator()

        # Before routing a task
        result = validator.validate_delegate(delegate_dict)

        # After a task completes
        result = validator.validate_handback(handback_dict, original_delegate)

        # Full end-to-end (layers 1+2 for delegate, layer 3 for handback)
        result = validator.validate_full(delegate_dict, handback_dict)
    """

    def __init__(self, metrics_emitter=None):
        """
        Args:
            metrics_emitter: Optional callable(metric_name, value, tags) for
                             emitting quality metrics to an observability sink.
        """
        self._metrics_emitter = metrics_emitter
        self._validation_history: List[ValidationResult] = []

    # ── Public API ────────────────────────────────────────────────────────────

    def validate_delegate(self, delegate: Dict) -> ValidationResult:
        """
        Run Layer 1 + Layer 2 validation on a DELEGATE block.

        Returns:
            ValidationResult with quality_score, routing_decision, findings.
        """
        start = time.monotonic()
        findings: List[ValidationFinding] = []

        # Layer 1: structural / syntax checks
        l1_findings, l1_score = self._run_layer1(delegate)
        findings.extend(l1_findings)

        # Layer 2: routing / quality checks (only if L1 passes structurally)
        if l1_score >= 50:
            l2_findings, l2_score = self._run_layer2(delegate)
            findings.extend(l2_findings)
        else:
            l2_findings, l2_score = [], 0

        # Composite score weighted by layer importance
        quality_score = self._composite_score(
            l1_score=l1_score,
            l2_score=l2_score,
            l3_score=None,
        )

        routing = self._routing_decision(quality_score, findings)
        passed = routing != RoutingDecision.CRITICAL and not any(
            f.severity == Severity.CRITICAL for f in findings
        )

        result = ValidationResult(
            task_id=delegate.get("task_id"),
            layer=2,
            quality_score=quality_score,
            routing_decision=routing,
            findings=findings,
            passed=passed,
            layer1_score=l1_score,
            layer2_score=l2_score,
        )
        self._record_and_emit(result, duration_ms=(time.monotonic() - start) * 1000)
        return result

    def validate_handback(
        self,
        handback: Dict,
        original_delegate: Optional[Dict] = None,
    ) -> ValidationResult:
        """
        Run Layer 3 validation on a HANDBACK block.

        Args:
            handback: The HANDBACK YAML as a Python dict.
            original_delegate: Original DELEGATE for cross-reference checks.

        Returns:
            ValidationResult with quality_score, routing_decision, findings.
        """
        start = time.monotonic()
        findings: List[ValidationFinding] = []

        l3_findings, l3_score = self._run_layer3(handback, original_delegate)
        findings.extend(l3_findings)

        quality_score = self._composite_score(
            l1_score=None,
            l2_score=None,
            l3_score=l3_score,
        )

        routing = self._routing_decision(quality_score, findings)
        passed = routing != RoutingDecision.CRITICAL and not any(
            f.severity == Severity.CRITICAL for f in findings
        )

        result = ValidationResult(
            task_id=handback.get("task_id") or (
                original_delegate.get("task_id") if original_delegate else None
            ),
            layer=3,
            quality_score=quality_score,
            routing_decision=routing,
            findings=findings,
            passed=passed,
            layer3_score=l3_score,
        )
        self._record_and_emit(result, duration_ms=(time.monotonic() - start) * 1000)
        return result

    def validate_full(
        self,
        delegate: Dict,
        handback: Optional[Dict] = None,
    ) -> ValidationResult:
        """
        Run all applicable layers.

        If handback is provided, runs L1 + L2 on delegate and L3 on handback
        and returns a merged result.  If handback is None, runs L1 + L2 only.
        """
        start = time.monotonic()
        findings: List[ValidationFinding] = []

        l1_findings, l1_score = self._run_layer1(delegate)
        findings.extend(l1_findings)

        if l1_score >= 50:
            l2_findings, l2_score = self._run_layer2(delegate)
            findings.extend(l2_findings)
        else:
            l2_findings, l2_score = [], 0

        l3_score = None
        if handback is not None:
            l3_findings, l3_score = self._run_layer3(handback, delegate)
            findings.extend(l3_findings)

        quality_score = self._composite_score(l1_score, l2_score, l3_score)
        routing = self._routing_decision(quality_score, findings)
        passed = routing != RoutingDecision.CRITICAL and not any(
            f.severity == Severity.CRITICAL for f in findings
        )

        result = ValidationResult(
            task_id=delegate.get("task_id"),
            layer=3 if handback is not None else 2,
            quality_score=quality_score,
            routing_decision=routing,
            findings=findings,
            passed=passed,
            layer1_score=l1_score,
            layer2_score=l2_score,
            layer3_score=l3_score,
        )
        self._record_and_emit(result, duration_ms=(time.monotonic() - start) * 1000)
        return result

    # ── Layer 1: Pre-routing validation ──────────────────────────────────────

    def _run_layer1(self, delegate: Dict) -> Tuple[List[ValidationFinding], int]:
        """
        Layer 1 checks — DELEGATE structure and syntax.

        Checks:
          1.1  ``handoff_type`` present and equals "DELEGATE"
          1.2  ``task_id`` present, non-empty, valid kebab-case format
          1.3  ``task_id`` not excessively long (≤ 64 chars)
          1.4  ``role`` present and recognised
          1.5  ``scope`` present and non-empty
          1.6  ``effort`` present and valid value
          1.7  No forbidden fields (secrets, tokens, passwords)

        Returns:
            (findings, layer1_score 0-100)
        """
        findings: List[ValidationFinding] = []
        deductions = 0

        # 1.1 handoff_type
        handoff_type = delegate.get("handoff_type", "")
        if not handoff_type:
            findings.append(ValidationFinding(
                layer=1, check="handoff_type_missing",
                severity=Severity.ERROR,
                message="'handoff_type' field is missing from DELEGATE block.",
                field="handoff_type", score_deduction=15,
            ))
            deductions += 15
        elif handoff_type != "DELEGATE":
            findings.append(ValidationFinding(
                layer=1, check="handoff_type_invalid",
                severity=Severity.ERROR,
                message=f"'handoff_type' must be 'DELEGATE', got '{handoff_type}'.",
                field="handoff_type", score_deduction=15,
            ))
            deductions += 15

        # 1.2 task_id presence
        task_id = delegate.get("task_id", "")
        if not task_id:
            findings.append(ValidationFinding(
                layer=1, check="task_id_missing",
                severity=Severity.CRITICAL,
                message="'task_id' field is missing. Every task must have a unique ID.",
                field="task_id", score_deduction=25,
            ))
            deductions += 25
        else:
            # 1.3 task_id format
            if not TASK_ID_PATTERN.match(task_id):
                findings.append(ValidationFinding(
                    layer=1, check="task_id_format",
                    severity=Severity.ERROR,
                    message=(
                        f"'task_id' '{task_id}' does not match required pattern: "
                        "lowercase alphanumeric + hyphens, 2-64 characters."
                    ),
                    field="task_id", score_deduction=10,
                ))
                deductions += 10
            if len(task_id) > 64:
                findings.append(ValidationFinding(
                    layer=1, check="task_id_too_long",
                    severity=Severity.WARNING,
                    message=f"'task_id' is {len(task_id)} chars; keep ≤ 64 for readability.",
                    field="task_id", score_deduction=5,
                ))
                deductions += 5

        # 1.4 role
        role = delegate.get("role", "")
        if not role:
            findings.append(ValidationFinding(
                layer=1, check="role_missing",
                severity=Severity.ERROR,
                message="'role' field is missing. Specify the target agent role.",
                field="role", score_deduction=15,
            ))
            deductions += 15
        elif role.lower() not in VALID_ROLES:
            findings.append(ValidationFinding(
                layer=1, check="role_unknown",
                severity=Severity.WARNING,
                message=(
                    f"'role' '{role}' is not a known agent role. "
                    f"Valid roles: {', '.join(sorted(VALID_ROLES))}."
                ),
                field="role", score_deduction=8,
            ))
            deductions += 8

        # 1.5 scope
        scope = str(delegate.get("scope") or "")
        if not scope or not scope.strip():
            findings.append(ValidationFinding(
                layer=1, check="scope_missing",
                severity=Severity.CRITICAL,
                message="'scope' field is missing or empty. Scope is required.",
                field="scope", score_deduction=20,
            ))
            deductions += 20

        # 1.6 effort
        effort = delegate.get("effort", "")
        if not effort:
            findings.append(ValidationFinding(
                layer=1, check="effort_missing",
                severity=Severity.WARNING,
                message="'effort' field is missing. Add effort estimate for routing.",
                field="effort", score_deduction=5,
            ))
            deductions += 5
        elif effort.lower() not in VALID_EFFORT_VALUES:
            findings.append(ValidationFinding(
                layer=1, check="effort_invalid",
                severity=Severity.WARNING,
                message=(
                    f"'effort' value '{effort}' is not recognised. "
                    f"Valid values: {', '.join(sorted(VALID_EFFORT_VALUES))}."
                ),
                field="effort", score_deduction=5,
            ))
            deductions += 5

        # 1.7 forbidden sensitive fields
        sensitive_keys = {"password", "secret", "token", "api_key", "private_key", "credential"}
        for key in delegate:
            if key.lower() in sensitive_keys:
                findings.append(ValidationFinding(
                    layer=1, check="sensitive_field",
                    severity=Severity.CRITICAL,
                    message=f"Field '{key}' looks like a secret/credential. Never embed secrets in DELEGATE.",
                    field=key, score_deduction=40,
                ))
                deductions += 40
                break  # one report is enough

        score = max(0, 100 - deductions)
        return findings, score

    # ── Layer 2: Routing / task-quality validation ────────────────────────────

    def _run_layer2(self, delegate: Dict) -> Tuple[List[ValidationFinding], int]:
        """
        Layer 2 checks — task quality for intelligent routing.

        Checks:
          2.1  Scope has sufficient detail (word count ≥ 5)
          2.2  Scope describes an actionable outcome (not just a noun phrase)
          2.3  Plan present when effort is high/max/epic
          2.4  Plan has meaningful steps (not a one-liner)
          2.5  Effort is consistent with role (e.g. engineer=low/medium)
          2.6  success_criteria or deliverables present for non-trivial tasks

        Returns:
            (findings, layer2_score 0-100)
        """
        findings: List[ValidationFinding] = []
        deductions = 0

        scope = str(delegate.get("scope", "")).strip()
        effort = str(delegate.get("effort", "")).lower()
        role = str(delegate.get("role", "")).lower()
        plan = delegate.get("plan", None)

        # 2.1 Scope word count
        word_count = len(scope.split())
        if word_count < SCOPE_MIN_WORD_COUNT:
            findings.append(ValidationFinding(
                layer=2, check="scope_too_brief",
                severity=Severity.ERROR,
                message=(
                    f"Scope has only {word_count} word(s); at least {SCOPE_MIN_WORD_COUNT} "
                    "required for clear task definition."
                ),
                field="scope", score_deduction=20,
            ))
            deductions += 20
        elif word_count < 15:
            findings.append(ValidationFinding(
                layer=2, check="scope_brief",
                severity=Severity.WARNING,
                message=(
                    f"Scope has {word_count} words — consider expanding for clarity."
                ),
                field="scope", score_deduction=5,
            ))
            deductions += 5

        # 2.2 Scope should describe an action / outcome (contains verb heuristic)
        action_verbs = {
            "implement", "create", "add", "fix", "refactor", "update", "build",
            "design", "integrate", "review", "test", "migrate", "remove", "delete",
            "investigate", "analyse", "analyze", "validate", "configure", "deploy",
        }
        scope_lower = scope.lower()
        has_verb = any(v in scope_lower for v in action_verbs)
        if scope and not has_verb:
            findings.append(ValidationFinding(
                layer=2, check="scope_no_action_verb",
                severity=Severity.WARNING,
                message="Scope doesn't contain a clear action verb. State what should be done.",
                field="scope", score_deduction=8,
            ))
            deductions += 8

        # 2.3 Plan required for high/max/epic effort
        high_effort = effort in {"high", "max", "epic"}
        if high_effort and not plan:
            findings.append(ValidationFinding(
                layer=2, check="plan_required_for_high_effort",
                severity=Severity.ERROR,
                message=(
                    f"Effort is '{effort}' but no 'plan' field provided. "
                    "High-effort tasks must have a plan."
                ),
                field="plan", score_deduction=20,
            ))
            deductions += 20
        elif plan:
            # 2.4 Plan quality check
            plan_text = str(plan).strip()
            plan_lines = [l.strip() for l in plan_text.splitlines() if l.strip()]
            plan_word_count = len(plan_text.split())
            if len(plan_lines) < 2 and plan_word_count < 10:
                findings.append(ValidationFinding(
                    layer=2, check="plan_too_brief",
                    severity=Severity.WARNING,
                    message="Plan appears to be a single line. Break it into numbered steps.",
                    field="plan", score_deduction=8,
                ))
                deductions += 8

        # 2.5 Effort/role consistency
        engineer_only_roles = {"engineer"}
        architect_roles = {"principal_engineer", "senior_engineer", "lead_engineer"}
        if role in engineer_only_roles and effort in {"max", "epic"}:
            findings.append(ValidationFinding(
                layer=2, check="effort_role_mismatch",
                severity=Severity.WARNING,
                message=(
                    f"Role 'engineer' with effort '{effort}' is unusual. "
                    "Consider senior_engineer or lead_engineer for complex tasks."
                ),
                field="effort", score_deduction=5,
            ))
            deductions += 5

        # 2.6 Success criteria / deliverables for non-trivial tasks
        has_criteria = bool(
            delegate.get("success_criteria") or
            delegate.get("deliverables") or
            delegate.get("acceptance_criteria")
        )
        if not has_criteria and effort in {"high", "max", "epic"}:
            findings.append(ValidationFinding(
                layer=2, check="missing_success_criteria",
                severity=Severity.WARNING,
                message=(
                    "No 'success_criteria' or 'deliverables' field for a high-effort task. "
                    "Add clear acceptance criteria so completion can be verified."
                ),
                score_deduction=8,
            ))
            deductions += 8

        score = max(0, 100 - deductions)
        return findings, score

    # ── Layer 3: Post-completion validation ───────────────────────────────────

    def _run_layer3(
        self,
        handback: Dict,
        original_delegate: Optional[Dict],
    ) -> Tuple[List[ValidationFinding], int]:
        """
        Layer 3 checks — HANDBACK structure after task completion.

        Checks:
          3.1  ``handoff_type`` present and equals "HANDBACK"
          3.2  ``task_id`` present and non-empty
          3.3  ``task_id`` matches original DELEGATE (if provided)
          3.4  ``status`` present and valid value
          3.5  ``notes`` present for completed tasks
          3.6  No ``status: failed`` without an explanation
          3.7  ``tests_passed`` present for engineering tasks

        Returns:
            (findings, layer3_score 0-100)
        """
        findings: List[ValidationFinding] = []
        deductions = 0

        # 3.1 handoff_type
        handoff_type = handback.get("handoff_type", "")
        if not handoff_type:
            findings.append(ValidationFinding(
                layer=3, check="handback_type_missing",
                severity=Severity.ERROR,
                message="'handoff_type' missing from HANDBACK block.",
                field="handoff_type", score_deduction=15,
            ))
            deductions += 15
        elif handoff_type != "HANDBACK":
            findings.append(ValidationFinding(
                layer=3, check="handback_type_invalid",
                severity=Severity.ERROR,
                message=f"'handoff_type' must be 'HANDBACK', got '{handoff_type}'.",
                field="handoff_type", score_deduction=15,
            ))
            deductions += 15

        # 3.2 task_id
        task_id = handback.get("task_id", "")
        if not task_id:
            findings.append(ValidationFinding(
                layer=3, check="handback_task_id_missing",
                severity=Severity.CRITICAL,
                message="'task_id' missing from HANDBACK — cannot correlate with DELEGATE.",
                field="task_id", score_deduction=25,
            ))
            deductions += 25
        elif original_delegate:
            # 3.3 task_id cross-reference
            expected_id = original_delegate.get("task_id", "")
            if expected_id and task_id != expected_id:
                findings.append(ValidationFinding(
                    layer=3, check="task_id_mismatch",
                    severity=Severity.CRITICAL,
                    message=(
                        f"HANDBACK task_id '{task_id}' does not match "
                        f"DELEGATE task_id '{expected_id}'."
                    ),
                    field="task_id", score_deduction=30,
                ))
                deductions += 30

        # 3.4 status
        status = str(handback.get("status", "")).lower()
        if not status:
            findings.append(ValidationFinding(
                layer=3, check="handback_status_missing",
                severity=Severity.ERROR,
                message="'status' field missing from HANDBACK.",
                field="status", score_deduction=15,
            ))
            deductions += 15
        elif status not in VALID_HANDBACK_STATUSES:
            findings.append(ValidationFinding(
                layer=3, check="handback_status_invalid",
                severity=Severity.ERROR,
                message=(
                    f"'status' value '{status}' is not valid. "
                    f"Valid values: {', '.join(sorted(VALID_HANDBACK_STATUSES))}."
                ),
                field="status", score_deduction=10,
            ))
            deductions += 10

        # 3.5 notes
        notes = handback.get("notes", "")
        if not notes or not str(notes).strip():
            findings.append(ValidationFinding(
                layer=3, check="handback_notes_missing",
                severity=Severity.WARNING,
                message="'notes' field is missing. Add a summary of what was delivered.",
                field="notes", score_deduction=8,
            ))
            deductions += 8

        # 3.6 failed without explanation
        if status == "failed":
            notes_text = str(notes).strip()
            if len(notes_text.split()) < 5:
                findings.append(ValidationFinding(
                    layer=3, check="failed_without_reason",
                    severity=Severity.ERROR,
                    message=(
                        "HANDBACK status is 'failed' but 'notes' contains no explanation. "
                        "Describe what went wrong so the task can be retried."
                    ),
                    field="notes", score_deduction=15,
                ))
                deductions += 15

        # 3.7 tests_passed for engineering roles
        if original_delegate:
            original_role = str(original_delegate.get("role", "")).lower()
            is_engineering = original_role in {
                "engineer", "senior_engineer", "lead_engineer", "principal_engineer"
            }
            if is_engineering and "tests_passed" not in handback:
                findings.append(ValidationFinding(
                    layer=3, check="tests_passed_missing",
                    severity=Severity.WARNING,
                    message=(
                        "Engineering HANDBACK should include 'tests_passed' field "
                        "(e.g. tests_passed: 47/47)."
                    ),
                    score_deduction=5,
                ))
                deductions += 5

        # 3.8 Enforce Quality Checklist Completion (ORCHESTRATION/QUALITY.md Tiers)
        # All agents must complete Tier 1 (lint, test, scope, hazards)
        tier1_completed = handback.get("checklist_tier_1_completed", False)
        if not tier1_completed and status != "failed":
            findings.append(ValidationFinding(
                layer=3, check="tier1_checklist_incomplete",
                severity=Severity.ERROR,
                message=(
                    "Tier 1 quality checklist not completed. "
                    "HANDBACK must include 'checklist_tier_1_completed: true' "
                    "with proof: lint pass, tests pass, scope validation, no hazards."
                ),
                field="checklist_tier_1_completed", score_deduction=20,
            ))
            deductions += 20

        # Senior Engineer, Lead Engineer, Principal Engineer must complete Tier 2
        # (coverage, docs, plan completeness)
        if original_delegate:
            role = str(original_delegate.get("role", "")).lower()
            if role in {"senior_engineer", "lead_engineer", "principal_engineer"}:
                tier2_completed = handback.get("checklist_tier_2_completed", False)
                if not tier2_completed and status != "failed":
                    findings.append(ValidationFinding(
                        layer=3, check="tier2_checklist_incomplete",
                        severity=Severity.ERROR,
                        message=(
                            f"Tier 2 quality checklist required for {role}. "
                            "HANDBACK must include 'checklist_tier_2_completed: true' "
                            "with proof: coverage maintained/improved, docs added, "
                            "plan steps executed completely."
                        ),
                        field="checklist_tier_2_completed", score_deduction=15,
                    ))
                    deductions += 15

            # Principal Engineer and Security Engineer must complete Tier 3
            # (architecture adherence, IAM/security, cross-service contracts)
            if role in {"principal_engineer", "security_engineer"}:
                tier3_completed = handback.get("checklist_tier_3_completed", False)
                if not tier3_completed and status != "failed":
                    findings.append(ValidationFinding(
                        layer=3, check="tier3_checklist_incomplete",
                        severity=Severity.ERROR,
                        message=(
                            f"Tier 3 quality checklist required for {role}. "
                            "HANDBACK must include 'checklist_tier_3_completed: true' "
                            "with proof: architecture adherence, IAM/security compliance, "
                            "cross-service contract validation."
                        ),
                        field="checklist_tier_3_completed", score_deduction=15,
                    ))
                    deductions += 15

        score = max(0, 100 - deductions)
        return findings, score

    # ── Scoring & Routing ─────────────────────────────────────────────────────

    def _composite_score(
        self,
        l1_score: Optional[int],
        l2_score: Optional[int],
        l3_score: Optional[int],
    ) -> int:
        """
        Calculate composite quality score.

        Weights are applied only for layers that were actually run.
        If a layer is not run, its weight is redistributed proportionally.
        """
        layers_run = []
        if l1_score is not None:
            layers_run.append((l1_score, LAYER1_WEIGHT))
        if l2_score is not None:
            layers_run.append((l2_score, LAYER2_WEIGHT))
        if l3_score is not None:
            layers_run.append((l3_score, LAYER3_WEIGHT))

        if not layers_run:
            return 0

        total_weight = sum(w for _, w in layers_run)
        weighted_sum = sum(score * weight for score, weight in layers_run)
        return round(weighted_sum / total_weight)

    @staticmethod
    def _routing_decision(
        quality_score: int,
        findings: List[ValidationFinding],
    ) -> RoutingDecision:
        """
        Map quality score + findings to a routing decision.

        Critical findings always force CRITICAL routing regardless of score.
        """
        has_critical = any(f.severity == Severity.CRITICAL for f in findings)
        if has_critical or quality_score < 40:
            return RoutingDecision.CRITICAL
        if quality_score >= 80:
            return RoutingDecision.HIGH
        if quality_score >= 60:
            return RoutingDecision.MEDIUM
        return RoutingDecision.LOW

    # ── Metrics & Observability ───────────────────────────────────────────────

    def _record_and_emit(self, result: ValidationResult, duration_ms: float):
        """
        Store result in history and emit metrics to the observability sink.
        """
        self._validation_history.append(result)

        # Emit structured log
        level = logging.WARNING if not result.passed else logging.INFO
        logger.log(
            level,
            "quality_validation",
            extra={
                "task_id": result.task_id,
                "quality_score": result.quality_score,
                "routing_decision": result.routing_decision.value,
                "findings_total": len(result.findings),
                "findings_critical": len(result.critical_findings),
                "findings_error": len(result.error_findings),
                "findings_warning": len(result.warning_findings),
                "layer": result.layer,
                "passed": result.passed,
                "duration_ms": round(duration_ms, 2),
            },
        )

        if self._metrics_emitter:
            tags = {
                "routing_decision": result.routing_decision.value,
                "layer": str(result.layer),
                "passed": str(result.passed).lower(),
            }
            try:
                self._metrics_emitter("quality_score", result.quality_score, tags)
                self._metrics_emitter("validation_duration_ms", duration_ms, tags)
                self._metrics_emitter("validation_findings_total", len(result.findings), tags)
                self._metrics_emitter(
                    "validation_critical_count", len(result.critical_findings), tags
                )
            except Exception as exc:
                logger.warning("Failed to emit quality metrics: %s", exc)

    # ── Reporting Helpers ─────────────────────────────────────────────────────

    def routing_action(self, result: ValidationResult) -> str:
        """
        Return the recommended routing action as a human-readable string.

        This is used by the OrchestratorAgent when deciding what to do with
        a task that failed validation.
        """
        decision = result.routing_decision
        if decision == RoutingDecision.HIGH:
            return "direct_dispatch"
        if decision == RoutingDecision.MEDIUM:
            return "route_to_lead_engineer"
        if decision == RoutingDecision.LOW:
            return "route_to_principal_engineer"
        # CRITICAL
        return "escalate_with_analysis"

    def summary(self, result: ValidationResult) -> str:
        """Human-readable one-line validation summary."""
        finding_parts = []
        if result.critical_findings:
            finding_parts.append(f"{len(result.critical_findings)} critical")
        if result.error_findings:
            finding_parts.append(f"{len(result.error_findings)} error(s)")
        if result.warning_findings:
            finding_parts.append(f"{len(result.warning_findings)} warning(s)")

        finding_str = ", ".join(finding_parts) or "no issues"
        status = "PASS" if result.passed else "FAIL"
        return (
            f"[{status}] score={result.quality_score}/100 "
            f"routing={result.routing_decision.value} "
            f"findings={finding_str}"
        )

    def validation_report(self, result: ValidationResult) -> str:
        """Multi-line human-readable validation report."""
        lines = [
            f"Quality Validation Report",
            f"  Task ID   : {result.task_id or 'unknown'}",
            f"  Score     : {result.quality_score}/100",
            f"  Routing   : {result.routing_decision.value.upper()}",
            f"  Action    : {self.routing_action(result)}",
            f"  Passed    : {result.passed}",
            f"  Validated : {result.validated_at}",
        ]
        if result.layer1_score is not None:
            lines.append(f"  L1 score  : {result.layer1_score}/100 (structural)")
        if result.layer2_score is not None:
            lines.append(f"  L2 score  : {result.layer2_score}/100 (routing quality)")
        if result.layer3_score is not None:
            lines.append(f"  L3 score  : {result.layer3_score}/100 (post-completion)")

        if result.findings:
            lines.append("")
            lines.append("  Findings:")
            for f in result.findings:
                icon = {
                    Severity.CRITICAL: "💥",
                    Severity.ERROR:    "❌",
                    Severity.WARNING:  "⚠️",
                    Severity.INFO:     "ℹ️",
                }.get(f.severity, "?")
                field_note = f" [{f.field}]" if f.field else ""
                lines.append(f"    {icon} L{f.layer}/{f.check}{field_note}: {f.message}")
        else:
            lines.append("  Findings: none")

        return "\n".join(lines)

    def get_history(self) -> List[Dict]:
        """Return validation history as list of dicts (for metrics/dashboards)."""
        return [r.as_dict() for r in self._validation_history]

    def get_metrics_summary(self) -> Dict:
        """Aggregate metrics across all validation history."""
        if not self._validation_history:
            return {"total_validations": 0}

        scores = [r.quality_score for r in self._validation_history]
        passed = [r for r in self._validation_history if r.passed]
        routing_counts: Dict[str, int] = {}
        for r in self._validation_history:
            key = r.routing_decision.value
            routing_counts[key] = routing_counts.get(key, 0) + 1

        return {
            "total_validations": len(self._validation_history),
            "pass_rate": round(len(passed) / len(self._validation_history) * 100, 1),
            "avg_quality_score": round(sum(scores) / len(scores), 1),
            "min_quality_score": min(scores),
            "max_quality_score": max(scores),
            "routing_distribution": routing_counts,
        }
