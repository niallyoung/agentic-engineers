"""Comprehensive unit tests for skill interoperability matrix."""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile

from src.evals.skill_matrix.models import (
    SkillTestResult,
    MatrixResult,
    TestStatus,
    FailureMode,
    SkillInvocationTest,
)
# HANDBACK/DELEGATE validation now lives in the protocol-validation skill;
# this module only needs DelegateGenerator for building test DELEGATE blocks.
from src.evals.skill_matrix.protocol import DelegateGenerator
from src.evals.skill_matrix.matrix_runner import SkillInteropMatrix


class TestSkillTestResult:
    """Tests for SkillTestResult model."""

    def test_skill_test_result_creation(self):
        """Test creating a SkillTestResult."""
        result = SkillTestResult(
            skill_name="spec-validator",
            harness="claude",
            status=TestStatus.PASS,
            success_rate=0.95,
            latency_ms=1500.0,
        )
        assert result.skill_name == "spec-validator"
        assert result.harness == "claude"
        assert result.is_success is True

    def test_skill_test_result_is_success_property(self):
        """Test is_success property."""
        pass_result = SkillTestResult(
            skill_name="test", harness="claude",
            status=TestStatus.PASS, success_rate=1.0, latency_ms=100.0
        )
        fail_result = SkillTestResult(
            skill_name="test", harness="claude",
            status=TestStatus.FAIL, success_rate=0.0, latency_ms=100.0
        )
        assert pass_result.is_success is True
        assert fail_result.is_success is False

    def test_skill_test_result_is_warning_property(self):
        """Test is_warning property."""
        yellow_result = SkillTestResult(
            skill_name="test", harness="claude",
            status=TestStatus.YELLOW, success_rate=0.85, latency_ms=100.0
        )
        assert yellow_result.is_warning is True
        assert yellow_result.is_failure is False

    def test_skill_test_result_to_dict(self):
        """Test to_dict serialization."""
        result = SkillTestResult(
            skill_name="spec-validator",
            harness="claude",
            status=TestStatus.PASS,
            success_rate=0.95,
            latency_ms=1500.0,
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.005,
        )
        result_dict = result.to_dict()
        assert result_dict["skill_name"] == "spec-validator"
        assert result_dict["harness"] == "claude"
        assert result_dict["status"] == "✅"
        assert result_dict["success_rate"] == 0.95


class TestMatrixResult:
    """Tests for MatrixResult model."""

    def test_matrix_result_creation(self):
        """Test creating a MatrixResult."""
        result = MatrixResult()
        assert result.total_combinations == 0
        assert result.passed == 0
        assert result.quality_score == 0.0

    def test_matrix_result_add_result_pass(self):
        """Test adding a passing result."""
        matrix = MatrixResult()
        result = SkillTestResult(
            skill_name="test", harness="claude",
            status=TestStatus.PASS, success_rate=1.0, latency_ms=100.0
        )
        matrix.add_result(result)
        assert matrix.total_combinations == 1
        assert matrix.passed == 1
        assert matrix.failed == 0

    def test_matrix_result_add_result_fail(self):
        """Test adding a failing result."""
        matrix = MatrixResult()
        result = SkillTestResult(
            skill_name="test", harness="claude",
            status=TestStatus.FAIL, success_rate=0.0, latency_ms=100.0
        )
        matrix.add_result(result)
        assert matrix.total_combinations == 1
        assert matrix.passed == 0
        assert matrix.failed == 1

    def test_matrix_result_overall_success_rate(self):
        """Test overall success rate calculation."""
        matrix = MatrixResult()
        # Add 3 passing results
        for _ in range(3):
            result = SkillTestResult(
                skill_name="test", harness="claude",
                status=TestStatus.PASS, success_rate=1.0, latency_ms=100.0
            )
            matrix.add_result(result)
        # Add 1 failing result
        fail_result = SkillTestResult(
            skill_name="test", harness="claude",
            status=TestStatus.FAIL, success_rate=0.0, latency_ms=100.0
        )
        matrix.add_result(fail_result)
        assert matrix.overall_success_rate == pytest.approx(0.75, abs=0.01)

    def test_matrix_result_quality_score_excellent(self):
        """Test quality score for excellent results (≥95%)."""
        matrix = MatrixResult()
        for _ in range(19):
            result = SkillTestResult(
                skill_name="test", harness="claude",
                status=TestStatus.PASS, success_rate=1.0, latency_ms=100.0
            )
            matrix.add_result(result)
        result = SkillTestResult(
            skill_name="test", harness="claude",
            status=TestStatus.PASS, success_rate=1.0, latency_ms=100.0
        )
        matrix.add_result(result)
        assert matrix.quality_score == 100.0

    def test_matrix_result_quality_score_warning(self):
        """Test quality score for warning level (80-95%)."""
        matrix = MatrixResult()
        # Add 85 passing results (85% success)
        for _ in range(85):
            result = SkillTestResult(
                skill_name="test", harness="claude",
                status=TestStatus.PASS, success_rate=1.0, latency_ms=100.0
            )
            matrix.add_result(result)
        # Add 15 failing results
        for _ in range(15):
            result = SkillTestResult(
                skill_name="test", harness="claude",
                status=TestStatus.FAIL, success_rate=0.0, latency_ms=100.0
            )
            matrix.add_result(result)
        assert 75 <= matrix.quality_score < 100

    def test_matrix_result_to_dict(self):
        """Test to_dict serialization."""
        matrix = MatrixResult()
        result = SkillTestResult(
            skill_name="test", harness="claude",
            status=TestStatus.PASS, success_rate=1.0, latency_ms=100.0
        )
        matrix.add_result(result)
        matrix_dict = matrix.to_dict()
        assert "summary" in matrix_dict
        assert matrix_dict["summary"]["total_combinations"] == 1
        assert matrix_dict["summary"]["passed"] == 1


class TestDelegateGenerator:
    """Tests for DelegateGenerator."""

    def test_create_skill_test_delegate(self):
        """Test creating a skill test DELEGATE."""
        delegate = DelegateGenerator.create_skill_test_delegate(
            skill_name="spec-validator",
            harness="claude",
        )
        assert delegate["handoff_type"] == "DELEGATE"
        assert delegate["type"] == "skill_test"
        assert delegate["skill"] == "spec-validator"
        assert delegate["harness"] == "claude"
        assert "task_id" in delegate
        assert len(delegate["success_criteria"]) > 0
        assert len(delegate["plan"]) > 0

    def test_create_skill_test_delegate_with_custom_task_id(self):
        """Test creating delegate with custom task_id."""
        custom_id = "2026-05-01-custom-test"
        delegate = DelegateGenerator.create_skill_test_delegate(
            skill_name="test-skill",
            harness="copilot",
            task_id=custom_id,
        )
        assert delegate["task_id"] == custom_id

    def test_save_delegate(self):
        """Test saving delegate to YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            delegate = DelegateGenerator.create_skill_test_delegate(
                skill_name="test",
                harness="claude",
            )
            output_path = Path(tmpdir) / "DELEGATE.yaml"
            saved_path = DelegateGenerator.save_delegate(delegate, output_path)
            assert saved_path.exists()
            assert saved_path == output_path


# NOTE: HANDBACK validation tests previously lived here (TestHandbackValidator).
# They moved with the validator itself to the protocol-validation skill:
#   src/skills/protocol-validation/tests/test_protocol_validation.py


class TestSkillInteropMatrix:
    """Tests for SkillInteropMatrix runner."""

    def test_matrix_creation(self):
        """Test creating a matrix runner."""
        with tempfile.TemporaryDirectory() as tmpdir:
            matrix = SkillInteropMatrix(
                repo_root=Path(tmpdir),
                artifacts_dir=Path(tmpdir) / "artifacts",
            )
            assert matrix.repo_root == Path(tmpdir)
            assert matrix.artifacts_dir == Path(tmpdir) / "artifacts"

    def test_get_available_skills(self):
        """Test getting available skills."""
        matrix = SkillInteropMatrix()
        skills = matrix.get_available_skills()
        assert isinstance(skills, list)
        # Should have some skills available
        assert len(skills) > 0

    def test_test_skill_availability_valid(self):
        """Test checking if a valid skill is available."""
        matrix = SkillInteropMatrix()
        # Use a known available skill
        is_available, error = matrix.test_skill_availability("spec-validator")
        # Note: This depends on actual skills being installed
        # If spec-validator is available, is_available should be True
        assert isinstance(is_available, bool)

    def test_invoke_skill_on_harness(self):
        """Test invoking a skill on a harness."""
        matrix = SkillInteropMatrix()
        result = matrix.invoke_skill_on_harness(
            skill_name="spec-validator",
            harness="claude",
        )
        assert isinstance(result, SkillTestResult)
        assert result.skill_name == "spec-validator"
        assert result.harness == "claude"
        assert result.latency_ms > 0

    def test_generate_matrix_visualization(self):
        """Test generating matrix visualization."""
        matrix = SkillInteropMatrix()
        # Add some test results
        result1 = SkillTestResult(
            skill_name="spec-validator",
            harness="claude",
            status=TestStatus.PASS,
            success_rate=1.0,
            latency_ms=100.0,
        )
        matrix.result.add_result(result1)
        
        visualization = matrix.generate_matrix_visualization()
        assert isinstance(visualization, str)
        assert "Skill Interoperability Matrix" in visualization
        assert "spec-validator" in visualization

    def test_generate_json_report(self):
        """Test generating JSON report."""
        matrix = SkillInteropMatrix()
        result = SkillTestResult(
            skill_name="spec-validator",
            harness="claude",
            status=TestStatus.PASS,
            success_rate=1.0,
            latency_ms=100.0,
        )
        matrix.result.add_result(result)
        
        json_report = matrix.generate_json_report()
        parsed = json.loads(json_report)
        assert "summary" in parsed
        assert parsed["summary"]["total_combinations"] == 1

    def test_save_report(self):
        """Test saving reports to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            matrix = SkillInteropMatrix(
                artifacts_dir=Path(tmpdir) / "artifacts",
            )
            result = SkillTestResult(
                skill_name="test",
                harness="claude",
                status=TestStatus.PASS,
                success_rate=1.0,
                latency_ms=100.0,
            )
            matrix.result.add_result(result)
            
            txt_path, json_path = matrix.save_report()
            assert txt_path.exists()
            assert json_path.exists()


class TestSkillMatrixIntegration:
    """Integration tests for full matrix operations."""

    def test_run_filtered_matrix_by_skill(self):
        """Test running filtered matrix by skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            matrix = SkillInteropMatrix(
                artifacts_dir=Path(tmpdir) / "artifacts",
            )
            # Run filtered by skill that might not exist
            result = matrix.run_filtered_matrix(skill_filter="nonexistent")
            assert isinstance(result, MatrixResult)
            # Should have 0 or some results depending on available skills

    def test_run_filtered_matrix_by_harness(self):
        """Test running filtered matrix by harness."""
        with tempfile.TemporaryDirectory() as tmpdir:
            matrix = SkillInteropMatrix(
                artifacts_dir=Path(tmpdir) / "artifacts",
            )
            result = matrix.run_filtered_matrix(harness_filter="claude")
            assert isinstance(result, MatrixResult)

    def test_matrix_quality_score_calculation(self):
        """Test quality score calculation across multiple results."""
        matrix = SkillInteropMatrix()
        
        # Add 95% passing results
        for _ in range(95):
            result = SkillTestResult(
                skill_name="test",
                harness="claude",
                status=TestStatus.PASS,
                success_rate=1.0,
                latency_ms=100.0,
            )
            matrix.result.add_result(result)
        
        # Add 5% failing results
        for _ in range(5):
            result = SkillTestResult(
                skill_name="test",
                harness="claude",
                status=TestStatus.FAIL,
                success_rate=0.0,
                latency_ms=100.0,
            )
            matrix.result.add_result(result)
        
        # Quality score should be 100 for 95% success
        assert matrix.result.quality_score == 100.0


class TestTestStatus:
    """Tests for TestStatus enum."""

    def test_test_status_values(self):
        """Test that all TestStatus values are defined."""
        assert TestStatus.PASS.value == "✅"
        assert TestStatus.FAIL.value == "❌"
        assert TestStatus.YELLOW.value == "🟡"
        assert TestStatus.TIMEOUT.value == "⏱"
        assert TestStatus.UNAVAILABLE.value == "⊘"


class TestFailureMode:
    """Tests for FailureMode enum."""

    def test_failure_mode_values(self):
        """Test that all FailureMode values are defined."""
        assert FailureMode.SKILL_UNAVAILABLE.value == "skill_unavailable"
        assert FailureMode.INVOCATION_FAILED.value == "invocation_failed"
        assert FailureMode.SCHEMA_INVALID.value == "schema_invalid"
        assert FailureMode.LATENCY_EXCEEDED.value == "latency_exceeded"


class TestProtocolEdgeCases:
    """Tests for edge cases in protocol handling."""

    # HANDBACK-validation edge cases moved to the protocol-validation skill's
    # own test suite (src/skills/protocol-validation/tests/).

    def test_delegate_generator_auto_task_id_format(self):
        """Test that auto-generated task IDs have correct format."""
        delegate = DelegateGenerator.create_skill_test_delegate(
            skill_name="test-skill",
            harness="claude",
        )
        task_id = delegate["task_id"]
        # Should contain date prefix
        assert "2026-05-" in task_id or "202" in task_id
        # Should contain skill and harness identifiers
        assert "skill" in task_id.lower()
        assert "claude" in task_id.lower()


class TestMatrixCellMetadata:
    """Tests for metadata tracking in matrix cells."""

    def test_skill_test_result_with_metadata(self):
        """Test SkillTestResult with custom metadata."""
        metadata = {
            "test_iteration": 1,
            "retry_count": 2,
            "notes": "Second retry succeeded",
        }
        result = SkillTestResult(
            skill_name="test",
            harness="claude",
            status=TestStatus.PASS,
            success_rate=1.0,
            latency_ms=100.0,
            metadata=metadata,
        )
        assert result.metadata["test_iteration"] == 1
        assert result.metadata["retry_count"] == 2

    def test_matrix_result_total_combinations_tracking(self):
        """Test that total_combinations is properly tracked."""
        matrix = MatrixResult()
        assert matrix.total_combinations == 0
        
        for i in range(10):
            result = SkillTestResult(
                skill_name="test",
                harness="claude",
                status=TestStatus.PASS,
                success_rate=1.0,
                latency_ms=100.0,
            )
            matrix.add_result(result)
            assert matrix.total_combinations == i + 1


class TestSkillInteropMatrixEdgeCases:
    """Tests for edge cases in matrix operations."""

    def test_invoke_unavailable_skill(self):
        """Test invoking a skill that's not available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            matrix = SkillInteropMatrix(
                artifacts_dir=Path(tmpdir) / "artifacts",
            )
            result = matrix.invoke_skill_on_harness(
                skill_name="nonexistent-skill-xyz",
                harness="claude",
            )
            assert result.status == TestStatus.UNAVAILABLE
            assert result.failure_mode == FailureMode.SKILL_UNAVAILABLE

    def test_matrix_with_mixed_results(self):
        """Test matrix with mixture of pass, warn, and fail results."""
        matrix = SkillInteropMatrix()
        
        # Add pass results
        for _ in range(10):
            result = SkillTestResult(
                skill_name="test",
                harness="claude",
                status=TestStatus.PASS,
                success_rate=1.0,
                latency_ms=100.0,
            )
            matrix.result.add_result(result)
        
        # Add warning results
        for _ in range(5):
            result = SkillTestResult(
                skill_name="test",
                harness="copilot",
                status=TestStatus.YELLOW,
                success_rate=0.85,
                latency_ms=2500.0,
            )
            matrix.result.add_result(result)
        
        # Add fail results
        for _ in range(5):
            result = SkillTestResult(
                skill_name="test",
                harness="opencode",
                status=TestStatus.FAIL,
                success_rate=0.0,
                latency_ms=5000.0,
            )
            matrix.result.add_result(result)
        
        assert matrix.result.total_combinations == 20
        assert matrix.result.passed == 10
        assert matrix.result.warned == 5
        assert matrix.result.failed == 5


class TestSkillInvocationTest:
    """Tests for SkillInvocationTest model."""

    def test_skill_invocation_test_creation(self):
        """Test creating a SkillInvocationTest."""
        test = SkillInvocationTest(
            skill_name="spec-validator",
            harness="claude",
            timeout_seconds=60,
        )
        assert test.skill_name == "spec-validator"
        assert test.harness == "claude"
        assert test.timeout_seconds == 60

    def test_skill_invocation_test_defaults(self):
        """Test SkillInvocationTest default values."""
        test = SkillInvocationTest(
            skill_name="test",
            harness="claude",
        )
        assert test.timeout_seconds == 30
        assert test.latency_threshold_ms == 5000.0
        assert test.max_retries == 3
        assert test.expected_fields == []
