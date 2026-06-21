"""
HANDBACK Processor for the Claude Code harness.

Parses and validates HANDBACK YAML blocks returned by agent execution.
Ensures protocol compliance and extracts quality metrics for downstream
evaluation.

Usage::

    from src.harnesses.claude_code.handback_processor import HANDBACKProcessor

    processor = HANDBACKProcessor()
    handback_dict = processor.parse(yaml_text)
    result = processor.validate(handback_dict, original_delegate=delegate_dict)
    print(result.valid, result.quality_score)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml


logger = logging.getLogger(__name__)


@dataclass
class HandbackValidationResult:
    """Result of validating a HANDBACK block."""

    task_id: str
    valid: bool
    status: Optional[str] = None  # success/failure/partial/blocked/escalate
    quality_score: Optional[float] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    duration_minutes: Optional[float] = None
    skill_feedback: List[Dict] = field(default_factory=list)
    qe_feedback: Optional[Dict] = None
    missing_fields: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class HANDBACKProcessor:
    """Parse and validate HANDBACK blocks from agent execution.

    Enforces protocol compliance, extracts quality metrics, and warns
    about optional-but-expected missing fields.
    """

    REQUIRED_FIELDS = ["task_id", "status", "notes"]
    VALID_STATUSES = {"success", "failure", "partial", "blocked", "escalate"}

    def parse(self, yaml_text: str) -> Dict[str, Any]:
        """Parse YAML text into a dictionary.

        Args:
            yaml_text: YAML string to parse.

        Returns:
            Parsed dictionary.

        Raises:
            yaml.YAMLError: If YAML is malformed.
            ValueError: If parsing fails.
        """
        try:
            data = yaml.safe_load(yaml_text)
            if not isinstance(data, dict):
                raise ValueError(
                    f"Expected dict, got {type(data).__name__}"
                )
            return data
        except yaml.YAMLError as exc:
            logger.error("YAML parse error: %s", exc)
            raise

    def validate(
        self,
        handback: Dict[str, Any],
        original_delegate: Optional[Dict[str, Any]] = None,
    ) -> HandbackValidationResult:
        """Validate a HANDBACK dictionary against the protocol.

        Args:
            handback: Parsed HANDBACK dictionary.
            original_delegate: Original DELEGATE for cross-reference checks.

        Returns:
            HandbackValidationResult with detailed validation outcome.
        """
        task_id = handback.get("task_id", "")
        status = handback.get("status")
        missing_fields = []
        warnings = []
        valid = True

        # Check required fields
        for field_name in self.REQUIRED_FIELDS:
            if field_name not in handback or not handback.get(field_name):
                missing_fields.append(field_name)
                valid = False

        # Validate status enum
        if status is not None and status not in self.VALID_STATUSES:
            warnings.append(
                f"Invalid status '{status}'; expected one of "
                f"{', '.join(sorted(self.VALID_STATUSES))}"
            )
            valid = False

        # Cross-reference task_id if delegate provided
        if original_delegate is not None:
            delegate_task_id = original_delegate.get("task_id")
            if delegate_task_id and task_id != delegate_task_id:
                warnings.append(
                    f"task_id mismatch: HANDBACK={task_id} vs "
                    f"DELEGATE={delegate_task_id}"
                )

        # Extract quality score
        quality_score = self.extract_quality_score(handback)
        if quality_score is not None and not (0.0 <= quality_score <= 1.0):
            warnings.append(
                f"quality_score out of range: {quality_score} "
                f"(expected 0.0-1.0)"
            )

        # Extract metrics
        tokens_in = None
        tokens_out = None
        duration_minutes = None

        # Support both nested (metrics.tokens) and flat (tokens) formats
        metrics = handback.get("metrics", {})
        if isinstance(metrics, dict):
            tokens_in = metrics.get("tokens")
            tokens_out = metrics.get("tokens_out")
            duration_seconds = metrics.get("duration_seconds")
            if duration_seconds is not None:
                duration_minutes = duration_seconds / 60.0
        else:
            # Flat format fallback
            tokens_in = handback.get("tokens")
            tokens_out = handback.get("tokens_out")
            duration_seconds = handback.get("duration_seconds")
            if duration_seconds is not None:
                duration_minutes = duration_seconds / 60.0

        # Extract feedback
        skill_feedback = handback.get("skill_feedback", [])
        if not isinstance(skill_feedback, list):
            skill_feedback = []
            warnings.append("skill_feedback is not a list")

        qe_feedback = handback.get("qe_feedback")

        logger.info(
            "handback.validate",
            extra={
                "task_id": task_id,
                "valid": valid,
                "status": status,
                "missing_fields_count": len(missing_fields),
                "warnings_count": len(warnings),
            },
        )

        return HandbackValidationResult(
            task_id=task_id,
            valid=valid,
            status=status,
            quality_score=quality_score,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duration_minutes=duration_minutes,
            skill_feedback=skill_feedback,
            qe_feedback=qe_feedback,
            missing_fields=missing_fields,
            warnings=warnings,
        )

    def extract_quality_score(self, handback: Dict[str, Any]) -> Optional[float]:
        """Extract quality score from HANDBACK.

        Handles both condensed (metrics.quality) and flat (quality_score)
        HANDBACK formats.

        Args:
            handback: Parsed HANDBACK dictionary.

        Returns:
            Quality score (0.0-1.0) or None if not present.
        """
        # Try nested format first (metrics.quality)
        metrics = handback.get("metrics")
        if isinstance(metrics, dict):
            quality = metrics.get("quality")
            if quality is not None:
                try:
                    return float(quality)
                except (ValueError, TypeError):
                    return None

        # Try flat format (quality_score)
        quality_score = handback.get("quality_score")
        if quality_score is not None:
            try:
                return float(quality_score)
            except (ValueError, TypeError):
                return None

        return None

    def extract_skill_feedback(
        self, handback: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract skill feedback list from HANDBACK.

        Args:
            handback: Parsed HANDBACK dictionary.

        Returns:
            List of feedback dictionaries, or empty list if not present.
        """
        feedback = handback.get("skill_feedback", [])
        if not isinstance(feedback, list):
            logger.warning(
                "skill_feedback is not a list; returning empty list"
            )
            return []
        return feedback
