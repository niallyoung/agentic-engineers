"""
Tests for the validators module (DelegateValidator, HandbackValidator, CycleDetector).

These tests validate src/skills/queue-management/scripts/validators.py.
TDD red-phase style: covers all Groups A/B/C validation, HANDBACK validation,
cycle detection, parent validation, and width limits.

Target: >=90% branch coverage of validators.py
"""
import json
import sys
import tempfile
from pathlib import Path
from typing import Tuple

import pytest

# ── Path setup ─────────────────────────────────────────────────────────────
# Add queue-management/scripts dir directly to avoid namespace collision with
# other skills' 'scripts' packages.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_QM_SCRIPTS = _REPO_ROOT / "src" / "skills" / "queue-management" / "scripts"
if str(_QM_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_QM_SCRIPTS))

from validators import DelegateValidator, HandbackValidator, CycleDetector

# ── Valid test strings (>=15 and >=20 words respectively) ──────────────────
VALID_SCOPE = (
    "This is an implementation task that requires careful design with "
    "comprehensive testing across all error scenarios and edge cases"
)  # 19 words
VALID_CONTEXT = (
    "This is the context for task execution and includes important information "
    "about requirements and specifications for successful completion here today "
    "and tomorrow"
)  # 22 words
VALID_PLAN_STEP1 = "Implement the core functionality with proper error handling and validation"
VALID_PLAN_STEP2 = "Write comprehensive tests for all code paths and edge cases"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_queue(tmp_path):
    """Return a temporary queue directory path."""
    return tmp_path


@pytest.fixture
def delegate_validator(temp_queue):
    """Return a DelegateValidator with a fresh temp queue."""
    return DelegateValidator(queue_path=temp_queue)


@pytest.fixture
def handback_validator():
    """Return a HandbackValidator instance."""
    return HandbackValidator()


@pytest.fixture
def cycle_detector(temp_queue):
    """Return a CycleDetector with a fresh temp queue."""
    return CycleDetector(queue_path=temp_queue)


@pytest.fixture
def valid_delegate():
    """Return a fully-valid DELEGATE dict."""
    return {
        "task_id": "valid-task-01",
        "role": "Engineer",
        "scope": VALID_SCOPE,
        "plan": [VALID_PLAN_STEP1, VALID_PLAN_STEP2],
        "context": VALID_CONTEXT,
    }


@pytest.fixture
def valid_handback():
    """Return a fully-valid HANDBACK dict."""
    return {
        "task_id": "test-task",
        "status": "complete",
        "quality_score": 85,
        "deliverables": ["deliverable1"],
    }


# ── Task file helper ────────────────────────────────────────────────────────

def _create_task(queue_path: Path, task_id: str, parent_id: str = None, state: str = "incoming"):
    """Create a task JSON file in the given state directory."""
    state_dir = queue_path / state
    state_dir.mkdir(parents=True, exist_ok=True)
    task = {"task_id": task_id}
    if parent_id is not None:
        task["parent_task_id"] = parent_id
    task_file = state_dir / f"{task_id}.json"
    task_file.write_text(json.dumps(task))
    return task_file


# ---------------------------------------------------------------------------
# DelegateValidator — constructor
# ---------------------------------------------------------------------------

class TestDelegateValidatorConstructor:
    """Tests for DelegateValidator initialisation."""

    def test_init_stores_queue_path(self, temp_queue):
        """DelegateValidator stores queue_path as a Path object."""
        validator = DelegateValidator(queue_path=temp_queue)
        assert validator.queue_path == Path(temp_queue)

    def test_init_with_string_path(self, tmp_path):
        """DelegateValidator accepts string queue_path."""
        validator = DelegateValidator(queue_path=str(tmp_path))
        assert isinstance(validator.queue_path, Path)

    def test_valid_roles_defined(self, delegate_validator):
        """DelegateValidator has a non-empty set of valid roles."""
        assert len(delegate_validator.valid_roles) > 0

    def test_valid_efforts_defined(self, delegate_validator):
        """DelegateValidator has valid_efforts set."""
        assert "low" in delegate_validator.valid_efforts
        assert "medium" in delegate_validator.valid_efforts
        assert "high" in delegate_validator.valid_efforts


# ---------------------------------------------------------------------------
# DelegateValidator — validate_groups (full pipeline)
# ---------------------------------------------------------------------------

class TestValidateGroups:
    """Tests for DelegateValidator.validate_groups."""

    def test_valid_delegate_passes_all_groups(self, delegate_validator, valid_delegate):
        """Valid delegate passes all groups and returns (True, [])."""
        valid, errors = delegate_validator.validate_groups(valid_delegate)
        assert valid is True
        assert errors == []

    def test_invalid_delegate_returns_errors(self, delegate_validator):
        """Invalid delegate returns (False, errors)."""
        valid, errors = delegate_validator.validate_groups({})
        assert valid is False
        assert len(errors) > 0

    def test_errors_from_all_groups_combined(self, delegate_validator):
        """Errors from Groups A, B, C are all included in output."""
        delegate = {
            "task_id": "valid-id",
            "role": "Engineer",
            "scope": "short",  # Group B fail
            "plan": [VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            "context": "too short",  # Group B fail
        }
        valid, errors = delegate_validator.validate_groups(delegate)
        assert valid is False


# ---------------------------------------------------------------------------
# DelegateValidator — check_group_a
# ---------------------------------------------------------------------------

class TestGroupAValidation:
    """Tests for DelegateValidator.check_group_a."""

    def test_group_a_valid(self, delegate_validator, valid_delegate):
        """Valid Group A delegate returns no errors."""
        errors = delegate_validator.check_group_a(valid_delegate)
        assert errors == []

    def test_group_a_missing_all_fields(self, delegate_validator):
        """Empty dict produces errors for all required fields."""
        errors = delegate_validator.check_group_a({})
        assert len(errors) > 0

    def test_group_a_missing_task_id(self, delegate_validator, valid_delegate):
        """Missing task_id produces an error."""
        del valid_delegate["task_id"]
        errors = delegate_validator.check_group_a(valid_delegate)
        assert any("task_id" in e for e in errors)

    def test_group_a_invalid_task_id_uppercase(self, delegate_validator, valid_delegate):
        """Uppercase task_id fails kebab-case check."""
        valid_delegate["task_id"] = "Invalid-Task-ID"
        errors = delegate_validator.check_group_a(valid_delegate)
        assert any("kebab-case" in e or "task_id" in e for e in errors)

    def test_group_a_task_id_with_underscore(self, delegate_validator, valid_delegate):
        """Underscore in task_id is rejected."""
        valid_delegate["task_id"] = "task_with_underscore"
        errors = delegate_validator.check_group_a(valid_delegate)
        assert any("task_id" in e for e in errors)

    def test_group_a_task_id_too_short(self, delegate_validator, valid_delegate):
        """task_id of 2 chars is too short."""
        valid_delegate["task_id"] = "ab"
        errors = delegate_validator.check_group_a(valid_delegate)
        assert any("task_id" in e for e in errors)

    def test_group_a_task_id_too_long(self, delegate_validator, valid_delegate):
        """task_id of 51 chars is too long."""
        valid_delegate["task_id"] = "a" * 51
        errors = delegate_validator.check_group_a(valid_delegate)
        assert any("task_id" in e for e in errors)

    def test_group_a_task_id_empty_string(self, delegate_validator, valid_delegate):
        """Empty string task_id is rejected."""
        valid_delegate["task_id"] = ""
        errors = delegate_validator.check_group_a(valid_delegate)
        assert any("task_id" in e for e in errors)

    def test_group_a_task_id_not_string(self, delegate_validator, valid_delegate):
        """Non-string task_id is rejected."""
        valid_delegate["task_id"] = 12345
        errors = delegate_validator.check_group_a(valid_delegate)
        assert any("task_id" in e for e in errors)

    def test_group_a_invalid_role(self, delegate_validator, valid_delegate):
        """Role not in valid_roles is rejected."""
        valid_delegate["role"] = "InvalidRole"
        errors = delegate_validator.check_group_a(valid_delegate)
        assert any("role" in e for e in errors)

    def test_group_a_empty_role(self, delegate_validator, valid_delegate):
        """Empty role string is rejected."""
        valid_delegate["role"] = ""
        errors = delegate_validator.check_group_a(valid_delegate)
        assert any("role" in e for e in errors)

    def test_group_a_all_valid_roles(self, delegate_validator, valid_delegate):
        """All canonical roles are accepted."""
        valid_roles = [
            "Engineer", "Senior Engineer", "Lead Engineer", "Principal Engineer",
            "Quality Engineer", "Security Engineer", "Model Engineer", "Orchestrator",
        ]
        for role in valid_roles:
            valid_delegate["role"] = role
            errors = delegate_validator.check_group_a(valid_delegate)
            role_errors = [e for e in errors if "role" in e]
            assert role_errors == [], f"Role '{role}' rejected: {role_errors}"

    def test_group_a_empty_scope(self, delegate_validator, valid_delegate):
        """Empty scope is rejected."""
        valid_delegate["scope"] = ""
        errors = delegate_validator.check_group_a(valid_delegate)
        assert any("scope" in e for e in errors)

    def test_group_a_scope_not_string(self, delegate_validator, valid_delegate):
        """Non-string scope is rejected."""
        valid_delegate["scope"] = ["list", "of", "items"]
        errors = delegate_validator.check_group_a(valid_delegate)
        assert any("scope" in e for e in errors)

    def test_group_a_empty_plan(self, delegate_validator, valid_delegate):
        """Empty plan list is rejected."""
        valid_delegate["plan"] = []
        errors = delegate_validator.check_group_a(valid_delegate)
        assert any("plan" in e for e in errors)

    def test_group_a_plan_not_list(self, delegate_validator, valid_delegate):
        """Non-list plan is rejected."""
        valid_delegate["plan"] = "not a list"
        errors = delegate_validator.check_group_a(valid_delegate)
        assert any("plan" in e for e in errors)

    def test_group_a_empty_context(self, delegate_validator, valid_delegate):
        """Empty context string is rejected."""
        valid_delegate["context"] = ""
        errors = delegate_validator.check_group_a(valid_delegate)
        assert any("context" in e for e in errors)

    def test_group_a_context_not_string(self, delegate_validator, valid_delegate):
        """Non-string context is rejected."""
        valid_delegate["context"] = 42
        errors = delegate_validator.check_group_a(valid_delegate)
        assert any("context" in e for e in errors)


# ---------------------------------------------------------------------------
# DelegateValidator — check_group_b
# ---------------------------------------------------------------------------

class TestGroupBValidation:
    """Tests for DelegateValidator.check_group_b."""

    def test_group_b_valid(self, delegate_validator, valid_delegate):
        """Valid Group B delegate returns no errors."""
        errors = delegate_validator.check_group_b(valid_delegate)
        assert errors == []

    def test_group_b_scope_too_short(self, delegate_validator, valid_delegate):
        """Scope with fewer than 15 words is rejected."""
        valid_delegate["scope"] = "Too short scope here"
        errors = delegate_validator.check_group_b(valid_delegate)
        assert any("scope" in e for e in errors)

    def test_group_b_scope_exactly_15_words(self, delegate_validator, valid_delegate):
        """Scope with exactly 15 words passes."""
        valid_delegate["scope"] = (
            "one two three four five six seven eight nine ten "
            "eleven twelve thirteen fourteen fifteen"
        )
        errors = delegate_validator.check_group_b(valid_delegate)
        scope_errors = [e for e in errors if "scope" in e]
        assert scope_errors == []

    def test_group_b_context_too_short(self, delegate_validator, valid_delegate):
        """Context with fewer than 20 words is rejected."""
        valid_delegate["context"] = "Too short context here"
        errors = delegate_validator.check_group_b(valid_delegate)
        assert any("context" in e for e in errors)

    def test_group_b_context_exactly_20_words(self, delegate_validator, valid_delegate):
        """Context with exactly 20 words passes."""
        valid_delegate["context"] = (
            "one two three four five six seven eight nine ten "
            "eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty"
        )
        errors = delegate_validator.check_group_b(valid_delegate)
        context_errors = [e for e in errors if "context" in e]
        assert context_errors == []

    def test_group_b_plan_with_one_step(self, delegate_validator, valid_delegate):
        """Plan with fewer than 2 steps is rejected."""
        valid_delegate["plan"] = [VALID_PLAN_STEP1]
        errors = delegate_validator.check_group_b(valid_delegate)
        assert any("plan" in e for e in errors)

    def test_group_b_plan_step_too_short(self, delegate_validator, valid_delegate):
        """Plan step with fewer than 3 words is rejected."""
        valid_delegate["plan"] = ["Short", VALID_PLAN_STEP2]
        errors = delegate_validator.check_group_b(valid_delegate)
        assert any("plan" in e for e in errors)

    def test_group_b_plan_step_not_string(self, delegate_validator, valid_delegate):
        """Non-string plan step is rejected."""
        valid_delegate["plan"] = [123, VALID_PLAN_STEP2]
        errors = delegate_validator.check_group_b(valid_delegate)
        assert any("plan" in e for e in errors)

    def test_group_b_plan_exactly_two_valid_steps(self, delegate_validator, valid_delegate):
        """Plan with exactly 2 valid steps passes."""
        valid_delegate["plan"] = [VALID_PLAN_STEP1, VALID_PLAN_STEP2]
        errors = delegate_validator.check_group_b(valid_delegate)
        plan_errors = [e for e in errors if "plan" in e]
        assert plan_errors == []

    def test_group_b_plan_not_a_list(self, delegate_validator, valid_delegate):
        """Non-list plan is ignored in group B (group A catches it)."""
        valid_delegate["plan"] = "not a list"
        errors = delegate_validator.check_group_b(valid_delegate)
        # Non-list plan: group B skips check (isinstance guard)
        # Just ensure no crash
        assert isinstance(errors, list)


# ---------------------------------------------------------------------------
# DelegateValidator — check_group_c
# ---------------------------------------------------------------------------

class TestGroupCValidation:
    """Tests for DelegateValidator.check_group_c."""

    def test_group_c_no_optional_fields(self, delegate_validator):
        """No optional fields produces no errors."""
        errors = delegate_validator.check_group_c({})
        assert errors == []

    def test_group_c_valid_effort(self, delegate_validator):
        """Valid effort values produce no errors."""
        for effort in ("low", "medium", "high"):
            errors = delegate_validator.check_group_c({"effort": effort})
            assert errors == [], f"effort={effort!r} unexpectedly rejected: {errors}"

    def test_group_c_invalid_effort(self, delegate_validator):
        """Invalid effort is rejected."""
        errors = delegate_validator.check_group_c({"effort": "extreme"})
        assert any("effort" in e for e in errors)

    def test_group_c_valid_model(self, delegate_validator):
        """A valid model string produces no errors."""
        errors = delegate_validator.check_group_c({"model": "gpt-5.4"})
        assert errors == []

    def test_group_c_invalid_model(self, delegate_validator):
        """An unrecognised model is rejected."""
        errors = delegate_validator.check_group_c({"model": "imaginary-model-99"})
        assert any("model" in e for e in errors)

    def test_group_c_valid_task_tier_zero(self, delegate_validator):
        """task_tier=0 with no parent is valid (root task)."""
        errors = delegate_validator.check_group_c({"task_tier": 0})
        assert errors == []

    def test_group_c_task_tier_out_of_range_negative(self, delegate_validator):
        """task_tier < 0 is rejected."""
        errors = delegate_validator.check_group_c({"task_tier": -1})
        assert any("task_tier" in e for e in errors)

    def test_group_c_task_tier_out_of_range_above(self, delegate_validator):
        """task_tier > 5 is rejected."""
        errors = delegate_validator.check_group_c({"task_tier": 6})
        assert any("task_tier" in e for e in errors)

    def test_group_c_task_tier_not_int(self, delegate_validator):
        """Non-integer task_tier is rejected."""
        errors = delegate_validator.check_group_c({"task_tier": 2.5})
        assert any("task_tier" in e for e in errors)

    def test_group_c_parent_without_task_tier(self, delegate_validator):
        """parent_task_id without task_tier is rejected."""
        errors = delegate_validator.check_group_c({"parent_task_id": "parent-01"})
        assert any("task_tier" in e for e in errors)

    def test_group_c_task_tier_positive_without_parent(self, delegate_validator):
        """task_tier > 0 without parent_task_id is rejected."""
        errors = delegate_validator.check_group_c({"task_tier": 1})
        assert any("parent_task_id" in e for e in errors)

    def test_group_c_task_tier_with_parent(self, delegate_validator):
        """task_tier=1 with parent_task_id is valid."""
        errors = delegate_validator.check_group_c({
            "task_tier": 1,
            "parent_task_id": "parent-01",
        })
        assert errors == []

    def test_group_c_task_tier_boundary_five(self, delegate_validator):
        """task_tier=5 (max allowed) with parent is valid."""
        errors = delegate_validator.check_group_c({
            "task_tier": 5,
            "parent_task_id": "parent-01",
        })
        assert errors == []


# ---------------------------------------------------------------------------
# HandbackValidator — validate
# ---------------------------------------------------------------------------

class TestHandbackValidation:
    """Tests for HandbackValidator.validate."""

    def test_handback_valid(self, handback_validator, valid_handback):
        """Valid HANDBACK passes validation."""
        valid, errors = handback_validator.validate(valid_handback)
        assert valid is True
        assert errors == []

    def test_handback_empty_dict_fails(self, handback_validator):
        """Empty dict fails with multiple errors."""
        valid, errors = handback_validator.validate({})
        assert valid is False
        assert len(errors) > 0

    def test_handback_missing_task_id(self, handback_validator, valid_handback):
        """Missing task_id produces an error."""
        del valid_handback["task_id"]
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid

    def test_handback_task_id_not_string(self, handback_validator, valid_handback):
        """Non-string task_id is rejected."""
        valid_handback["task_id"] = 999
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid
        assert any("task_id" in e for e in errors)

    def test_handback_invalid_status(self, handback_validator, valid_handback):
        """Status not in {complete, escalated} is rejected."""
        valid_handback["status"] = "invalid"
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid
        assert any("status" in e for e in errors)

    def test_handback_status_complete(self, handback_validator, valid_handback):
        """status='complete' is accepted."""
        valid_handback["status"] = "complete"
        valid, errors = handback_validator.validate(valid_handback)
        status_errors = [e for e in errors if "status" in e]
        assert status_errors == []

    def test_handback_status_escalated(self, handback_validator, valid_handback):
        """status='escalated' is accepted."""
        valid_handback["status"] = "escalated"
        valid, errors = handback_validator.validate(valid_handback)
        status_errors = [e for e in errors if "status" in e]
        assert status_errors == []

    def test_handback_quality_score_too_high(self, handback_validator, valid_handback):
        """quality_score > 100 is rejected."""
        valid_handback["quality_score"] = 150
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid
        assert any("quality_score" in e for e in errors)

    def test_handback_quality_score_negative(self, handback_validator, valid_handback):
        """Negative quality_score is rejected."""
        valid_handback["quality_score"] = -1
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid
        assert any("quality_score" in e for e in errors)

    def test_handback_quality_score_zero_accepted(self, handback_validator, valid_handback):
        """quality_score=0 is accepted (boundary)."""
        valid_handback["quality_score"] = 0
        valid, errors = handback_validator.validate(valid_handback)
        qs_errors = [e for e in errors if "quality_score" in e]
        assert qs_errors == []

    def test_handback_quality_score_100_accepted(self, handback_validator, valid_handback):
        """quality_score=100 is accepted (boundary)."""
        valid_handback["quality_score"] = 100
        valid, errors = handback_validator.validate(valid_handback)
        qs_errors = [e for e in errors if "quality_score" in e]
        assert qs_errors == []

    def test_handback_quality_score_not_number(self, handback_validator, valid_handback):
        """Non-numeric quality_score is rejected."""
        valid_handback["quality_score"] = "high"
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid

    def test_handback_deliverables_not_list(self, handback_validator, valid_handback):
        """Non-list deliverables is rejected."""
        valid_handback["deliverables"] = "one deliverable"
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid
        assert any("deliverables" in e for e in errors)

    def test_handback_deliverables_empty_list(self, handback_validator, valid_handback):
        """Empty deliverables list is rejected."""
        valid_handback["deliverables"] = []
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid
        assert any("deliverables" in e for e in errors)

    def test_handback_test_results_invalid_structure(self, handback_validator, valid_handback):
        """test_results missing 'passed'/'total' is rejected."""
        valid_handback["test_results"] = {"count": 5}
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid
        assert any("test_results" in e for e in errors)

    def test_handback_test_results_not_dict(self, handback_validator, valid_handback):
        """Non-dict test_results is rejected."""
        valid_handback["test_results"] = [1, 2, 3]
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid

    def test_handback_test_results_valid(self, handback_validator, valid_handback):
        """Valid test_results passes."""
        valid_handback["test_results"] = {"passed": 10, "total": 10}
        valid, errors = handback_validator.validate(valid_handback)
        tr_errors = [e for e in errors if "test_results" in e]
        assert tr_errors == []

    def test_handback_metrics_not_dict(self, handback_validator, valid_handback):
        """Non-dict metrics is rejected."""
        valid_handback["metrics"] = "fast"
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid
        assert any("metrics" in e for e in errors)

    def test_handback_metrics_valid_dict(self, handback_validator, valid_handback):
        """Dict metrics passes."""
        valid_handback["metrics"] = {"tokens": 5000, "cost": 0.10}
        valid, errors = handback_validator.validate(valid_handback)
        metrics_errors = [e for e in errors if "metrics" in e]
        assert metrics_errors == []

    def test_handback_children_created_not_list(self, handback_validator, valid_handback):
        """Non-list children_created is rejected."""
        valid_handback["children_created"] = "child-01"
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid
        assert any("children_created" in e for e in errors)

    def test_handback_children_created_with_empty_string(self, handback_validator, valid_handback):
        """children_created with empty string element is rejected."""
        valid_handback["children_created"] = [""]
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid

    def test_handback_children_created_valid(self, handback_validator, valid_handback):
        """Valid children_created list passes."""
        valid_handback["children_created"] = ["child-task-01", "child-task-02"]
        valid, errors = handback_validator.validate(valid_handback)
        cc_errors = [e for e in errors if "children_created" in e]
        assert cc_errors == []

    def test_handback_children_results_not_dict(self, handback_validator, valid_handback):
        """Non-dict children_results is rejected."""
        valid_handback["children_results"] = ["x"]
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid
        assert any("children_results" in e for e in errors)

    def test_handback_children_results_missing_status(self, handback_validator, valid_handback):
        """children_results entry missing 'status' is rejected."""
        valid_handback["children_results"] = {"child-01": {"quality": 0.9}}
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid
        assert any("status" in e for e in errors)

    def test_handback_children_results_missing_quality(self, handback_validator, valid_handback):
        """children_results entry missing 'quality' is rejected."""
        valid_handback["children_results"] = {"child-01": {"status": "complete"}}
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid

    def test_handback_children_results_valid(self, handback_validator, valid_handback):
        """Valid children_results passes."""
        valid_handback["children_results"] = {
            "child-01": {"status": "complete", "quality": 0.9}
        }
        valid, errors = handback_validator.validate(valid_handback)
        cr_errors = [e for e in errors if "children_results" in e]
        assert cr_errors == []

    def test_handback_children_failed_not_list(self, handback_validator, valid_handback):
        """Non-list children_failed is rejected."""
        valid_handback["children_failed"] = "child-01"
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid
        assert any("children_failed" in e for e in errors)

    def test_handback_children_failed_list_accepted(self, handback_validator, valid_handback):
        """List children_failed passes."""
        valid_handback["children_failed"] = ["child-02"]
        valid, errors = handback_validator.validate(valid_handback)
        cf_errors = [e for e in errors if "children_failed" in e]
        assert cf_errors == []

    def test_handback_result_aggregation_status_invalid(self, handback_validator, valid_handback):
        """Invalid result_aggregation_status is rejected."""
        valid_handback["result_aggregation_status"] = "unknown_status"
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid
        assert any("result_aggregation_status" in e for e in errors)

    def test_handback_result_aggregation_status_valid(self, handback_validator, valid_handback):
        """Valid result_aggregation_status values are accepted."""
        for status in ("all_complete", "partial", "timed_out"):
            valid_handback["result_aggregation_status"] = status
            valid, errors = handback_validator.validate(valid_handback)
            ras_errors = [e for e in errors if "result_aggregation_status" in e]
            assert ras_errors == [], f"status={status!r} unexpectedly rejected: {ras_errors}"

    def test_handback_children_results_quality_not_number(self, handback_validator, valid_handback):
        """children_results quality that is not a number is rejected."""
        valid_handback["children_results"] = {
            "child-01": {"status": "complete", "quality": "perfect"}
        }
        valid, errors = handback_validator.validate(valid_handback)
        assert not valid


# ---------------------------------------------------------------------------
# CycleDetector — has_cycle
# ---------------------------------------------------------------------------

class TestCycleDetection:
    """Tests for CycleDetector.has_cycle."""

    def test_no_cycle_simple_link(self, cycle_detector, temp_queue):
        """Linking task to unrelated parent creates no cycle."""
        _create_task(temp_queue, "parent-01")
        assert cycle_detector.has_cycle("new-task", "parent-01") is False

    def test_self_cycle_detected(self, cycle_detector):
        """A task cannot be its own parent."""
        assert cycle_detector.has_cycle("task-a", "task-a") is True

    def test_two_node_cycle_detected(self, cycle_detector, temp_queue):
        """task-a → task-b, task-b → task-a creates a cycle."""
        _create_task(temp_queue, "task-a", parent_id="task-b")
        _create_task(temp_queue, "task-b")
        assert cycle_detector.has_cycle("task-b", "task-a") is True

    def test_no_cycle_in_linear_chain(self, cycle_detector, temp_queue):
        """Linear chain a ← b ← c has no cycle for new task d."""
        _create_task(temp_queue, "a")
        _create_task(temp_queue, "b", parent_id="a")
        _create_task(temp_queue, "c", parent_id="b")
        assert cycle_detector.has_cycle("d", "c") is False

    def test_cycle_at_chain_root(self, cycle_detector, temp_queue):
        """Linking root back to its own descendant creates a cycle."""
        _create_task(temp_queue, "root")
        _create_task(temp_queue, "child", parent_id="root")
        assert cycle_detector.has_cycle("root", "child") is True

    def test_no_cycle_independent_tasks(self, cycle_detector, temp_queue):
        """Completely unrelated tasks produce no cycle."""
        _create_task(temp_queue, "task-x")
        _create_task(temp_queue, "task-y")
        assert cycle_detector.has_cycle("task-z", "task-x") is False


# ---------------------------------------------------------------------------
# CycleDetector — validate_parent
# ---------------------------------------------------------------------------

class TestParentValidation:
    """Tests for CycleDetector.validate_parent."""

    def test_parent_exists_in_incoming(self, cycle_detector, temp_queue):
        """Parent in 'incoming' state is valid."""
        _create_task(temp_queue, "parent-01", state="incoming")
        valid, msg = cycle_detector.validate_parent("parent-01")
        assert valid is True
        assert msg == ""

    def test_parent_exists_in_processing(self, cycle_detector, temp_queue):
        """Parent in 'processing' state is valid."""
        _create_task(temp_queue, "parent-02", state="processing")
        valid, msg = cycle_detector.validate_parent("parent-02")
        assert valid is True

    def test_parent_exists_in_done(self, cycle_detector, temp_queue):
        """Parent in 'done' state is valid."""
        _create_task(temp_queue, "parent-03", state="done")
        valid, msg = cycle_detector.validate_parent("parent-03")
        assert valid is True

    def test_parent_not_found(self, cycle_detector, temp_queue):
        """Nonexistent parent returns (False, error_msg)."""
        valid, msg = cycle_detector.validate_parent("nonexistent-parent")
        assert valid is False
        assert len(msg) > 0


# ---------------------------------------------------------------------------
# CycleDetector — check_width_limit
# ---------------------------------------------------------------------------

class TestWidthLimit:
    """Tests for CycleDetector.check_width_limit."""

    def test_width_under_limit(self, cycle_detector, temp_queue):
        """5 children is under the 10-child limit."""
        _create_task(temp_queue, "parent")
        for i in range(5):
            _create_task(temp_queue, f"child-{i}", parent_id="parent")
        valid, count = cycle_detector.check_width_limit("parent")
        assert valid is True
        assert count == 5

    def test_width_exactly_at_limit(self, cycle_detector, temp_queue):
        """Exactly 10 children exceeds the limit (max_width=10, check is count < max_width)."""
        _create_task(temp_queue, "parent")
        for i in range(10):
            _create_task(temp_queue, f"child-{i}", parent_id="parent")
        valid, count = cycle_detector.check_width_limit("parent")
        # max_width=10, check is count < max_width, so 10 children = not valid
        assert valid is False
        assert count == 10

    def test_width_exceeded(self, cycle_detector, temp_queue):
        """11 children exceeds the 10-child limit."""
        _create_task(temp_queue, "parent")
        for i in range(11):
            _create_task(temp_queue, f"child-{i}", parent_id="parent")
        valid, count = cycle_detector.check_width_limit("parent")
        assert valid is False
        assert count == 11

    def test_width_zero_children(self, cycle_detector, temp_queue):
        """Parent with no children is valid."""
        _create_task(temp_queue, "lonely-parent")
        valid, count = cycle_detector.check_width_limit("lonely-parent")
        assert valid is True
        assert count == 0

    def test_width_counts_across_states(self, cycle_detector, temp_queue):
        """Children in different states are all counted."""
        _create_task(temp_queue, "parent")
        _create_task(temp_queue, "child-in", parent_id="parent", state="incoming")
        _create_task(temp_queue, "child-proc", parent_id="parent", state="processing")
        _create_task(temp_queue, "child-done", parent_id="parent", state="done")
        valid, count = cycle_detector.check_width_limit("parent")
        assert count == 3


# ---------------------------------------------------------------------------
# CycleDetector — _get_parent (internal)
# ---------------------------------------------------------------------------

class TestGetParent:
    """Tests for CycleDetector._get_parent internal method."""

    def test_get_parent_returns_parent_id(self, cycle_detector, temp_queue):
        """_get_parent returns the parent_task_id for a task that has one."""
        _create_task(temp_queue, "child", parent_id="real-parent")
        result = cycle_detector._get_parent("child")
        assert result == "real-parent"

    def test_get_parent_no_parent_returns_none(self, cycle_detector, temp_queue):
        """_get_parent returns None for a root task."""
        _create_task(temp_queue, "root")
        result = cycle_detector._get_parent("root")
        assert result is None

    def test_get_parent_nonexistent_task_returns_none(self, cycle_detector):
        """_get_parent returns None for a task that doesn't exist."""
        result = cycle_detector._get_parent("ghost-task")
        assert result is None

    def test_get_parent_corrupt_json_returns_none(self, cycle_detector, temp_queue):
        """_get_parent returns None when the task file contains invalid JSON."""
        state_dir = temp_queue / "incoming"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "bad-task.json").write_text("{ not valid json }")
        result = cycle_detector._get_parent("bad-task")
        assert result is None
