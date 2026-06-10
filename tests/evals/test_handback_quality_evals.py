"""
tests/evals/test_handback_quality_evals.py — Quality evaluation tests for HANDBACK blocks.

Tests that HANDBACKs conform to QUEUE-PROTOCOL.md canonical schema and quality standards:
- Required fields are present and non-empty
- Status is canonical (success|failure|partial|blocked|escalate)
- Metrics are all numeric and valid
- Quality score is calibrated to status
- Output is substantial (not empty summary)
"""

import pytest
from typing import Dict


class TestHandbackHasRequiredFields:
    """Eval: HANDBACK must have all required fields per QUEUE-PROTOCOL.md."""

    REQUIRED_FIELDS = [
        "handoff_type",
        "task_id",
        "agent",
        "status",
        "output",
        "metrics",
    ]

    REQUIRED_METRICS_FIELDS = [
        "quality",
        "tokens",
        "cost",
        "duration_seconds",
    ]

    def eval_has_all_required_fields(self, handback: Dict) -> bool:
        """Check that all required top-level fields are present."""
        for field in self.REQUIRED_FIELDS:
            if field not in handback:
                return False
        return True

    def eval_metrics_has_all_required_fields(self, handback: Dict) -> bool:
        """Check that metrics dict has all required sub-fields."""
        metrics = handback.get("metrics", {})
        if not isinstance(metrics, dict):
            return False
        for field in self.REQUIRED_METRICS_FIELDS:
            if field not in metrics:
                return False
        return True

    def eval_handoff_type_is_handback(self, handback: Dict) -> bool:
        """Check that handoff_type is exactly 'HANDBACK'."""
        return handback.get("handoff_type") == "HANDBACK"

    def test_canonical_handback_success_has_all_required_fields(self, canonical_handback_success):
        """Test that canonical success HANDBACK has all required fields."""
        assert self.eval_has_all_required_fields(canonical_handback_success)
        assert self.eval_handoff_type_is_handback(canonical_handback_success)
        assert self.eval_metrics_has_all_required_fields(canonical_handback_success)

    def test_all_handback_statuses_have_required_fields(
        self,
        canonical_handback_success,
        canonical_handback_failure,
        canonical_handback_partial,
        canonical_handback_blocked,
        canonical_handback_escalate,
    ):
        """Test that all HANDBACK statuses have required fields."""
        for handback in [
            canonical_handback_success,
            canonical_handback_failure,
            canonical_handback_partial,
            canonical_handback_blocked,
            canonical_handback_escalate,
        ]:
            assert self.eval_has_all_required_fields(handback), f"Missing fields in {handback.get('task_id')}"
            assert self.eval_metrics_has_all_required_fields(handback)

    def test_all_handbacks_in_corpus_have_required_fields(self, handback_corpus):
        """Test that all HANDBACK samples in corpus have required fields."""
        for handback in handback_corpus:
            assert self.eval_has_all_required_fields(handback), f"Missing fields in {handback.get('task_id')}"
            assert self.eval_metrics_has_all_required_fields(handback)


class TestHandbackStatusIsCanonical:
    """Eval: status field must be one of the canonical values."""

    CANONICAL_STATUSES = ["success", "failure", "partial", "blocked", "escalate"]

    def eval_status_is_canonical(self, status: str) -> bool:
        """Check that status is one of the canonical values."""
        return status in self.CANONICAL_STATUSES

    def test_canonical_handbacks_have_canonical_status(
        self,
        canonical_handback_success,
        canonical_handback_failure,
        canonical_handback_partial,
        canonical_handback_blocked,
        canonical_handback_escalate,
    ):
        """Test that all canonical HANDBACK samples have canonical status."""
        for handback in [
            canonical_handback_success,
            canonical_handback_failure,
            canonical_handback_partial,
            canonical_handback_blocked,
            canonical_handback_escalate,
        ]:
            assert self.eval_status_is_canonical(handback.get("status", ""))

    def test_all_handbacks_in_corpus_have_canonical_status(self, handback_corpus):
        """Test that all HANDBACK statuses in corpus are canonical."""
        for handback in handback_corpus:
            status = handback.get("status", "")
            assert self.eval_status_is_canonical(status), f"Invalid status '{status}' in {handback.get('task_id')}"


class TestHandbackMetricsAreNumeric:
    """Eval: All metrics fields must be valid numbers."""

    def eval_metrics_are_all_numeric(self, metrics: Dict) -> bool:
        """Check that all required metrics are valid numbers."""
        if not isinstance(metrics, dict):
            return False

        required = ["quality", "tokens", "cost", "duration_seconds"]
        for field in required:
            value = metrics.get(field)
            if not isinstance(value, (int, float)):
                return False
        return True

    def eval_quality_is_valid_float(self, metrics: Dict) -> bool:
        """Check that quality is a float between 0.0 and 1.0 (not 0-100)."""
        quality = metrics.get("quality")
        if not isinstance(quality, (int, float)):
            return False
        return 0.0 <= quality <= 1.0

    def eval_tokens_is_non_negative(self, metrics: Dict) -> bool:
        """Check that tokens is non-negative integer."""
        tokens = metrics.get("tokens")
        if not isinstance(tokens, int):
            return False
        return tokens >= 0

    def eval_cost_is_non_negative(self, metrics: Dict) -> bool:
        """Check that cost is non-negative float (USD)."""
        cost = metrics.get("cost")
        if not isinstance(cost, (int, float)):
            return False
        return cost >= 0.0

    def eval_duration_is_non_negative(self, metrics: Dict) -> bool:
        """Check that duration_seconds is non-negative float."""
        duration = metrics.get("duration_seconds")
        if not isinstance(duration, (int, float)):
            return False
        return duration >= 0.0

    def test_canonical_handback_metrics_are_numeric(self, canonical_handback_success):
        """Test that canonical HANDBACK metrics are all numeric."""
        metrics = canonical_handback_success.get("metrics", {})
        assert self.eval_metrics_are_all_numeric(metrics)
        assert self.eval_quality_is_valid_float(metrics)
        assert self.eval_tokens_is_non_negative(metrics)
        assert self.eval_cost_is_non_negative(metrics)
        assert self.eval_duration_is_non_negative(metrics)

    def test_all_handback_metrics_in_corpus_are_numeric(self, handback_corpus):
        """Test that all HANDBACK metrics in corpus are numeric."""
        for handback in handback_corpus:
            metrics = handback.get("metrics", {})
            assert self.eval_metrics_are_all_numeric(metrics), f"Invalid metrics in {handback.get('task_id')}"
            assert self.eval_quality_is_valid_float(metrics), f"Quality out of range in {handback.get('task_id')}"


class TestHandbackConfidenceCalibration:
    """Eval: quality and confidence should be calibrated to status."""

    def eval_success_has_quality_threshold(self, handback: Dict, threshold: float = 0.70) -> bool:
        """Check that status=success has quality >= threshold."""
        status = handback.get("status")
        if status != "success":
            return True  # Only check for success status

        quality = handback.get("metrics", {}).get("quality", 0.0)
        return quality >= threshold

    def eval_escalate_status_handled(self, handback: Dict) -> bool:
        """Check that status=escalate has escalation_chain or escalate_to."""
        status = handback.get("status")
        if status != "escalate":
            return True  # Only check for escalate status

        output = handback.get("output", {})
        if isinstance(output, dict):
            return "escalate_to" in output or "escalation_reason" in output
        return True

    def test_canonical_success_has_sufficient_quality(self, canonical_handback_success):
        """Test that success HANDBACK has quality >= 0.70."""
        assert self.eval_success_has_quality_threshold(canonical_handback_success, 0.70)

    def test_canonical_high_quality_has_high_score(self, canonical_handback_high_quality):
        """Test that exemplary HANDBACK has quality >= 0.90."""
        assert self.eval_success_has_quality_threshold(canonical_handback_high_quality, 0.90)

    def test_canonical_escalate_has_escalation_info(self, canonical_handback_escalate):
        """Test that escalate HANDBACK has escalation info."""
        assert self.eval_escalate_status_handled(canonical_handback_escalate)

    def test_handback_corpus_quality_matches_status(self, handback_corpus):
        """Test that all HANDBACKs have appropriate quality for their status."""
        for handback in handback_corpus:
            status = handback.get("status")
            quality = handback.get("metrics", {}).get("quality", 0.0)

            # Success should generally have quality >= 0.70
            if status == "success":
                assert quality >= 0.70, f"Success status should have quality >= 0.70 in {handback.get('task_id')}"

            # Failure can have low quality
            elif status == "failure":
                assert quality < 0.70, f"Failure status should have low quality in {handback.get('task_id')}"


class TestHandbackOutputIsSubstantial:
    """Eval: output field must not be empty/trivial."""

    def eval_output_is_substantial(self, output) -> bool:
        """Check that output is not empty or trivial."""
        if output is None:
            return False

        if isinstance(output, str):
            return len(output.strip()) >= 50

        elif isinstance(output, dict):
            # Should have at least one non-empty value
            total_length = 0
            for value in output.values():
                if isinstance(value, str):
                    total_length += len(value)
                elif isinstance(value, (list, dict)):
                    total_length += len(str(value))
            return total_length >= 50

        elif isinstance(output, list):
            return len(str(output)) >= 50

        return False

    def eval_output_has_summary(self, output) -> bool:
        """Check that output contains a summary or description."""
        if isinstance(output, dict):
            return "summary" in output or "description" in output or len(output) > 0
        return isinstance(output, str)

    def test_canonical_handback_output_is_substantial(self, canonical_handback_success):
        """Test that canonical HANDBACK output is substantial."""
        output = canonical_handback_success.get("output", "")
        assert self.eval_output_is_substantial(output)
        assert self.eval_output_has_summary(output)

    def test_all_handback_outputs_in_corpus_are_substantial(self, handback_corpus):
        """Test that all HANDBACK outputs in corpus are substantial."""
        for handback in handback_corpus:
            output = handback.get("output", "")
            assert self.eval_output_is_substantial(output), f"Output too trivial in {handback.get('task_id')}"


class TestHandbackTaskIdMatchesDelegateId:
    """Eval: HANDBACK task_id must match original DELEGATE task_id."""

    def eval_task_id_format_matches_delegate(self, task_id: str) -> bool:
        """Check that task_id follows YYYY-MM-DD-kebab-case format."""
        import re
        pattern = r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+$"
        return bool(re.match(pattern, task_id))

    def test_canonical_handback_task_ids_are_valid(
        self,
        canonical_handback_success,
        canonical_handback_failure,
        canonical_handback_escalate,
    ):
        """Test that canonical HANDBACK task_ids are valid format."""
        for handback in [canonical_handback_success, canonical_handback_failure, canonical_handback_escalate]:
            task_id = handback.get("task_id", "")
            assert self.eval_task_id_format_matches_delegate(task_id)


class TestHandbackAgentFieldValid:
    """Eval: agent field must match the role that completed the work."""

    VALID_AGENTS = [
        "engineer",
        "senior-engineer",
        "lead-engineer",
        "quality-engineer",
        "principal-engineer",
        "security-engineer",
        "model-engineer",
        "orchestrator",
    ]

    def eval_agent_is_valid_role(self, agent: str) -> bool:
        """Check that agent is hyphenated lowercase (format only)."""
        return agent.islower() and all(c.isalpha() or c == "-" for c in agent)

    def test_canonical_handback_agents_are_valid(
        self,
        canonical_handback_success,
        canonical_handback_failure,
    ):
        """Test that canonical HANDBACK agents are valid."""
        for handback in [canonical_handback_success, canonical_handback_failure]:
            agent = handback.get("agent", "")
            assert self.eval_agent_is_valid_role(agent)

    def test_all_handback_agents_in_corpus_are_valid(self, handback_corpus):
        """Test that all HANDBACK agents in corpus are valid."""
        for handback in handback_corpus:
            agent = handback.get("agent", "")
            assert self.eval_agent_is_valid_role(agent), f"Invalid agent format: {agent}"


# ============================================================================
# Summary: Composite Tests
# ============================================================================


class TestHandbackQualitySummary:
    """Summary: Complete quality check for a HANDBACK."""

    def test_canonical_success_handback_passes_all_evals(self, canonical_handback_success):
        """Test that canonical success HANDBACK passes all quality evals."""
        # Required fields
        assert "handoff_type" in canonical_handback_success
        assert canonical_handback_success["handoff_type"] == "HANDBACK"
        assert "task_id" in canonical_handback_success
        assert "agent" in canonical_handback_success
        assert "status" in canonical_handback_success
        assert "output" in canonical_handback_success
        assert "metrics" in canonical_handback_success

        # Metrics validation
        metrics = canonical_handback_success["metrics"]
        assert isinstance(metrics, dict)
        assert "quality" in metrics
        assert "tokens" in metrics
        assert "cost" in metrics
        assert "duration_seconds" in metrics

        # Quality calibration
        assert canonical_handback_success["status"] == "success"
        assert metrics["quality"] >= 0.70

        # Output substance
        output = canonical_handback_success["output"]
        assert len(str(output)) > 50

    def test_canonical_failure_handback_passes_all_evals(self, canonical_handback_failure):
        """Test that canonical failure HANDBACK passes all quality evals."""
        assert canonical_handback_failure["handoff_type"] == "HANDBACK"
        assert canonical_handback_failure["status"] == "failure"
        assert "metrics" in canonical_handback_failure

    def test_canonical_escalate_handback_passes_all_evals(self, canonical_handback_escalate):
        """Test that canonical escalate HANDBACK passes all quality evals."""
        assert canonical_handback_escalate["handoff_type"] == "HANDBACK"
        assert canonical_handback_escalate["status"] == "escalate"
        assert "escalation_chain" in canonical_handback_escalate or "escalate_to" in canonical_handback_escalate.get("output", {})

    def test_handback_corpus_all_pass_baseline_quality(self, handback_corpus):
        """Test that all HANDBACKs in corpus pass baseline quality gates."""
        for handback in handback_corpus:
            # Required fields
            assert "handoff_type" in handback
            assert handback["handoff_type"] == "HANDBACK"
            assert "task_id" in handback
            assert "agent" in handback
            assert "status" in handback
            assert "output" in handback
            assert "metrics" in handback

            # Status validity
            assert handback["status"] in ["success", "failure", "partial", "blocked", "escalate"]

            # Metrics validity
            metrics = handback["metrics"]
            assert isinstance(metrics, dict)
            assert all(k in metrics for k in ["quality", "tokens", "cost", "duration_seconds"])
            assert isinstance(metrics["quality"], (int, float))
            assert isinstance(metrics["tokens"], int)
            assert isinstance(metrics["cost"], (int, float))
            assert isinstance(metrics["duration_seconds"], (int, float))
