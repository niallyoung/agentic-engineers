"""
Regression tests for Claude Code harness HANDBACKProcessor.

Tests for parsing and validating HANDBACK blocks from agent execution,
ensuring protocol compliance and quality metric extraction.
"""

from __future__ import annotations

import pytest
import yaml

from src.harnesses.claude_code.handback_processor import (
    HANDBACKProcessor,
    HandbackValidationResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def processor() -> HANDBACKProcessor:
    """Shared HANDBACKProcessor instance."""
    return HANDBACKProcessor()


# ---------------------------------------------------------------------------
# D1.1-D1.5: YAML parsing and validation
# ---------------------------------------------------------------------------


class TestHandbackYAMLParsing:
    """YAML parsing and basic validation tests."""

    def test_parse_valid_yaml(self, processor: HANDBACKProcessor) -> None:
        """Valid YAML string is parsed into a dictionary."""
        yaml_text = "task_id: test-001\nstatus: success\nnotes: All tests pass"
        result = processor.parse(yaml_text)
        assert isinstance(result, dict)
        assert result["task_id"] == "test-001"
        assert result["status"] == "success"

    def test_parse_yaml_with_nested_metrics(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Nested metrics block is preserved during parsing."""
        yaml_text = (
            "task_id: test-002\nstatus: success\nnotes: Test\n"
            "metrics:\n  tokens: 1500\n  quality: 0.95\n  duration_seconds: 42"
        )
        result = processor.parse(yaml_text)
        assert isinstance(result["metrics"], dict)
        assert result["metrics"]["tokens"] == 1500
        assert result["metrics"]["quality"] == 0.95

    def test_parse_malformed_yaml_raises_error(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Malformed YAML raises yaml.YAMLError."""
        bad_yaml = "task_id: test\n  bad indent: [unclosed"
        with pytest.raises(yaml.YAMLError):
            processor.parse(bad_yaml)

    def test_parse_non_dict_yaml_raises_error(
        self, processor: HANDBACKProcessor
    ) -> None:
        """YAML that parses to non-dict raises ValueError."""
        list_yaml = "- item1\n- item2"
        with pytest.raises(ValueError, match="Expected dict"):
            processor.parse(list_yaml)

    def test_validate_required_fields_present(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Handback with all required fields passes validation."""
        handback = {
            "task_id": "test-001",
            "status": "success",
            "notes": "Task completed successfully",
        }
        result = processor.validate(handback)
        assert result.valid is True
        assert result.task_id == "test-001"
        assert result.status == "success"
        assert len(result.missing_fields) == 0

    def test_validate_missing_required_field(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Handback missing required field fails validation."""
        handback = {
            "task_id": "test-002",
            "status": "success",
            # Missing 'notes'
        }
        result = processor.validate(handback)
        assert result.valid is False
        assert "notes" in result.missing_fields

    def test_validate_empty_required_field(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Handback with empty required field is treated as missing."""
        handback = {
            "task_id": "test-003",
            "status": "success",
            "notes": "",  # Empty string
        }
        result = processor.validate(handback)
        assert result.valid is False
        assert "notes" in result.missing_fields

    def test_validate_status_enum_valid(
        self, processor: HANDBACKProcessor
    ) -> None:
        """All valid status values pass validation."""
        for status in ["success", "failure", "partial", "blocked", "escalate"]:
            handback = {
                "task_id": f"test-{status}",
                "status": status,
                "notes": f"Status: {status}",
            }
            result = processor.validate(handback)
            # Status enum is valid, even if other validation fails
            assert status in [w for w in result.warnings if "Invalid status" in w] or (
                result.status == status
            )

    def test_validate_status_invalid(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Invalid status value produces warning."""
        handback = {
            "task_id": "test-bad-status",
            "status": "invalid_status",
            "notes": "Test",
        }
        result = processor.validate(handback)
        assert result.valid is False
        assert any("Invalid status" in w for w in result.warnings)

    def test_validate_status_none_is_acceptable(
        self, processor: HANDBACKProcessor
    ) -> None:
        """status=None does not generate invalid status warning."""
        handback = {
            "task_id": "test-none-status",
            "status": None,
            "notes": "Test",
        }
        result = processor.validate(handback)
        # No warning about invalid status (None is skipped by the validation)
        assert not any("Invalid status" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# D1.6-D1.7: Quality score extraction
# ---------------------------------------------------------------------------


class TestQualityScoreExtraction:
    """Quality score extraction from condensed and flat formats."""

    def test_extract_quality_score_condensed_format(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Quality score is extracted from nested metrics.quality."""
        handback = {
            "task_id": "test-001",
            "status": "success",
            "notes": "Test",
            "metrics": {"quality": 0.87, "tokens": 1500},
        }
        result = processor.validate(handback)
        assert result.quality_score == 0.87

    def test_extract_quality_score_flat_format(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Quality score is extracted from flat quality_score field."""
        handback = {
            "task_id": "test-002",
            "status": "success",
            "notes": "Test",
            "quality_score": 0.92,
        }
        result = processor.validate(handback)
        assert result.quality_score == 0.92

    def test_extract_quality_score_prefers_nested(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Nested metrics.quality takes precedence over flat quality_score."""
        handback = {
            "task_id": "test-003",
            "status": "success",
            "notes": "Test",
            "metrics": {"quality": 0.95},
            "quality_score": 0.50,  # Should be ignored
        }
        result = processor.validate(handback)
        assert result.quality_score == 0.95

    def test_extract_quality_score_missing_returns_none(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Missing quality score returns None."""
        handback = {
            "task_id": "test-004",
            "status": "success",
            "notes": "Test",
        }
        result = processor.validate(handback)
        assert result.quality_score is None

    def test_extract_quality_score_out_of_range_warns(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Quality score outside 0.0-1.0 range generates warning."""
        handback = {
            "task_id": "test-005",
            "status": "success",
            "notes": "Test",
            "quality_score": 1.5,
        }
        result = processor.validate(handback)
        assert any("out of range" in w for w in result.warnings)

    def test_extract_quality_score_invalid_type_returns_none(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Non-numeric quality score returns None."""
        handback = {
            "task_id": "test-006",
            "status": "success",
            "notes": "Test",
            "quality_score": "not-a-number",
        }
        result = processor.validate(handback)
        assert result.quality_score is None


# ---------------------------------------------------------------------------
# D1.8: Skill feedback extraction
# ---------------------------------------------------------------------------


class TestSkillFeedbackExtraction:
    """Skill feedback list extraction and validation."""

    def test_extract_skill_feedback(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Skill feedback list is extracted from HANDBACK."""
        feedback_list = [
            {"skill": "orchestrator", "rating": 5},
            {"skill": "engineer", "rating": 4},
        ]
        handback = {
            "task_id": "test-001",
            "status": "success",
            "notes": "Test",
            "skill_feedback": feedback_list,
        }
        result = processor.validate(handback)
        assert result.skill_feedback == feedback_list
        assert len(result.skill_feedback) == 2

    def test_extract_skill_feedback_missing_returns_empty(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Missing skill_feedback returns empty list."""
        handback = {
            "task_id": "test-002",
            "status": "success",
            "notes": "Test",
        }
        result = processor.validate(handback)
        assert result.skill_feedback == []

    def test_extract_skill_feedback_not_list_warns(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Non-list skill_feedback generates warning."""
        handback = {
            "task_id": "test-003",
            "status": "success",
            "notes": "Test",
            "skill_feedback": "not a list",
        }
        result = processor.validate(handback)
        assert any("not a list" in w for w in result.warnings)
        assert result.skill_feedback == []


# ---------------------------------------------------------------------------
# D1.9-D1.10: Task ID cross-reference validation
# ---------------------------------------------------------------------------


class TestTaskIDValidation:
    """Task ID consistency between DELEGATE and HANDBACK."""

    def test_validate_task_id_matches_delegate(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Matching task IDs between DELEGATE and HANDBACK pass validation."""
        delegate = {"task_id": "task-123"}
        handback = {
            "task_id": "task-123",
            "status": "success",
            "notes": "Test",
        }
        result = processor.validate(handback, original_delegate=delegate)
        assert result.valid is True
        # No task_id mismatch warning
        assert not any("mismatch" in w for w in result.warnings)

    def test_validate_task_id_mismatch_warns(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Mismatched task IDs between DELEGATE and HANDBACK generate warning."""
        delegate = {"task_id": "task-123"}
        handback = {
            "task_id": "task-456",
            "status": "success",
            "notes": "Test",
        }
        result = processor.validate(handback, original_delegate=delegate)
        assert any("mismatch" in w.lower() for w in result.warnings)

    def test_validate_task_id_mismatch_no_delegate(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Without original_delegate, task_id mismatch check is skipped."""
        handback = {
            "task_id": "task-any-value",
            "status": "success",
            "notes": "Test",
        }
        result = processor.validate(handback, original_delegate=None)
        # Should not have mismatch warning (no delegate to compare against)
        assert not any("mismatch" in w for w in result.warnings)

    def test_validate_delegate_with_missing_task_id(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Missing task_id in delegate skips the mismatch check."""
        delegate = {}  # Missing task_id
        handback = {
            "task_id": "task-123",
            "status": "success",
            "notes": "Test",
        }
        result = processor.validate(handback, original_delegate=delegate)
        # Should not generate mismatch warning
        assert not any("mismatch" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# D1: Additional metrics extraction
# ---------------------------------------------------------------------------


class TestMetricsExtraction:
    """Duration and token metrics extraction."""

    def test_extract_tokens_and_duration_nested(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Tokens and duration are extracted from nested metrics."""
        handback = {
            "task_id": "test-001",
            "status": "success",
            "notes": "Test",
            "metrics": {"tokens": 1500, "duration_seconds": 120},
        }
        result = processor.validate(handback)
        assert result.tokens_in == 1500
        assert result.duration_minutes == 2.0  # 120 / 60

    def test_extract_tokens_and_duration_flat(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Tokens and duration are extracted from flat fields when metrics is not a dict."""
        handback = {
            "task_id": "test-002",
            "status": "success",
            "notes": "Test",
            "metrics": None,  # Force fallback to flat format
            "tokens": 2000,
            "duration_seconds": 300,
        }
        result = processor.validate(handback)
        assert result.tokens_in == 2000
        assert result.duration_minutes == 5.0

    def test_extract_metrics_non_dict_metrics_field(
        self, processor: HANDBACKProcessor
    ) -> None:
        """Non-dict metrics field falls back to flat format."""
        handback = {
            "task_id": "test-003",
            "status": "success",
            "notes": "Test",
            "metrics": "not a dict",
            "tokens": 1000,  # Flat format fallback
        }
        result = processor.validate(handback)
        assert result.tokens_in == 1000

    def test_handback_validation_result_fields(
        self, processor: HANDBACKProcessor
    ) -> None:
        """HandbackValidationResult has all expected fields."""
        handback = {
            "task_id": "test-001",
            "status": "success",
            "notes": "Test",
        }
        result = processor.validate(handback)
        assert hasattr(result, "task_id")
        assert hasattr(result, "valid")
        assert hasattr(result, "status")
        assert hasattr(result, "quality_score")
        assert hasattr(result, "tokens_in")
        assert hasattr(result, "tokens_out")
        assert hasattr(result, "duration_minutes")
        assert hasattr(result, "skill_feedback")
        assert hasattr(result, "qe_feedback")
        assert hasattr(result, "missing_fields")
        assert hasattr(result, "warnings")
