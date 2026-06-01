"""
Test Validators

Tests for validation modules.
"""

import json
import pytest
import tempfile
from pathlib import Path

from scripts.validators import DelegateValidator, HandbackValidator, CycleDetector
from tests.conftest import VALID_SCOPE, VALID_CONTEXT, VALID_PLAN_STEP1, VALID_PLAN_STEP2


@pytest.fixture
def temp_queue():
    """Create temporary queue directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def delegate_validator(temp_queue):
    """Create DelegateValidator instance."""
    return DelegateValidator(queue_path=temp_queue)


@pytest.fixture
def handback_validator():
    """Create HandbackValidator instance."""
    return HandbackValidator()


@pytest.fixture
def cycle_detector(temp_queue):
    """Create CycleDetector instance."""
    return CycleDetector(queue_path=temp_queue)


class TestGroupAValidation:
    """Tests for Group A validation."""

    def test_group_a_valid(self, delegate_validator):
        """Test valid Group A delegate."""
        delegate = {
            "task_id": "valid-task-001",
            "role": "Engineer",
            "scope": VALID_SCOPE,
            "plan": [VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            "context": VALID_CONTEXT,
        }

        errors = delegate_validator.check_group_a(delegate)
        assert len(errors) == 0

    def test_group_a_missing_fields(self, delegate_validator):
        """Test Group A with missing fields."""
        delegate = {"task_id": "test"}

        errors = delegate_validator.check_group_a(delegate)
        assert len(errors) > 0

    def test_group_a_invalid_task_id(self, delegate_validator):
        """Test Group A with invalid task_id."""
        delegate = {
            "task_id": "Invalid-Task-ID",
            "role": "Engineer",
            "scope": VALID_SCOPE,
            "plan": [VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            "context": VALID_CONTEXT,
        }

        errors = delegate_validator.check_group_a(delegate)
        assert any("kebab-case" in e for e in errors)

    def test_group_a_invalid_role(self, delegate_validator):
        """Test Group A with invalid role."""
        delegate = {
            "task_id": "valid-task",
            "role": "InvalidRole",
            "scope": VALID_SCOPE,
            "plan": [VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            "context": VALID_CONTEXT,
        }

        errors = delegate_validator.check_group_a(delegate)
        assert any("role" in e for e in errors)


class TestGroupBValidation:
    """Tests for Group B validation."""

    def test_group_b_valid(self, delegate_validator):
        """Test valid Group B delegate."""
        delegate = {
            "scope": VALID_SCOPE,
            "plan": [VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            "context": VALID_CONTEXT,
        }

        errors = delegate_validator.check_group_b(delegate)
        assert len(errors) == 0

    def test_group_b_scope_too_short(self, delegate_validator):
        """Test scope < 15 words."""
        delegate = {
            "scope": "Too short scope here",
            "plan": [VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            "context": VALID_CONTEXT,
        }

        errors = delegate_validator.check_group_b(delegate)
        assert any("scope" in e for e in errors)

    def test_group_b_context_too_short(self, delegate_validator):
        """Test context < 20 words."""
        delegate = {
            "scope": VALID_SCOPE,
            "plan": [VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            "context": "Too short context",
        }

        errors = delegate_validator.check_group_b(delegate)
        assert any("context" in e for e in errors)


class TestGroupCValidation:
    """Tests for Group C validation."""

    def test_group_c_valid_effort(self, delegate_validator):
        """Test valid effort."""
        delegate = {"effort": "medium"}
        errors = delegate_validator.check_group_c(delegate)
        assert len(errors) == 0

    def test_group_c_invalid_effort(self, delegate_validator):
        """Test invalid effort."""
        delegate = {"effort": "extreme"}
        errors = delegate_validator.check_group_c(delegate)
        assert any("effort" in e for e in errors)


class TestHandbackValidation:
    """Tests for HandbackValidator."""

    def test_handback_valid(self, handback_validator):
        """Test valid HANDBACK."""
        handback = {
            "task_id": "test-task",
            "status": "success",
            "quality_score": 85,
            "deliverables": ["deliverable1"],
        }

        valid, errors = handback_validator.validate(handback)
        assert valid

    def test_handback_invalid_status(self, handback_validator):
        """Test invalid status."""
        handback = {
            "task_id": "test-task",
            "status": "invalid",
            "quality_score": 85,
            "deliverables": ["deliverable1"],
        }

        valid, errors = handback_validator.validate(handback)
        assert not valid

    def test_handback_invalid_quality(self, handback_validator):
        """Test invalid quality_score."""
        handback = {
            "task_id": "test-task",
            "status": "success",
            "quality_score": 150,
            "deliverables": ["deliverable1"],
        }

        valid, errors = handback_validator.validate(handback)
        assert not valid


class TestCycleDetection:
    """Tests for CycleDetector."""

    def _create_task(self, queue_path, task_id, parent_id=None):
        """Helper to create task file."""
        (queue_path / "incoming").mkdir(exist_ok=True, parents=True)
        task = {"task_id": task_id, "parent_task_id": parent_id}
        with open(queue_path / "incoming" / f"{task_id}.json", "w") as f:
            json.dump(task, f)

    def test_no_cycle_linear(self, cycle_detector, temp_queue):
        """Test no cycle in linear chain."""
        self._create_task(temp_queue, "a")
        self._create_task(temp_queue, "b", "a")
        self._create_task(temp_queue, "c", "b")

        assert not cycle_detector.has_cycle("d", "c")

    def test_cycle_self_parent(self, cycle_detector, temp_queue):
        """Test cycle when task is its own parent."""
        assert cycle_detector.has_cycle("a", "a")

    def test_cycle_two_node(self, cycle_detector, temp_queue):
        """Test cycle in two-node chain."""
        self._create_task(temp_queue, "a", "b")
        self._create_task(temp_queue, "b")

        assert cycle_detector.has_cycle("b", "a")

    def test_parent_validation_exists(self, cycle_detector, temp_queue):
        """Test parent validation when parent exists."""
        self._create_task(temp_queue, "parent")
        valid, error_msg = cycle_detector.validate_parent("parent")
        assert valid

    def test_parent_validation_not_exists(self, cycle_detector, temp_queue):
        """Test parent validation when parent doesn't exist."""
        valid, error_msg = cycle_detector.validate_parent("nonexistent")
        assert not valid

    def test_width_limit_under(self, cycle_detector, temp_queue):
        """Test width limit when under limit."""
        self._create_task(temp_queue, "parent")
        for i in range(5):
            self._create_task(temp_queue, f"child-{i}", "parent")

        valid, count = cycle_detector.check_width_limit("parent")
        assert valid
        assert count == 5

    def test_width_limit_exceeded(self, cycle_detector, temp_queue):
        """Test width limit when exceeding."""
        self._create_task(temp_queue, "parent")
        for i in range(11):
            self._create_task(temp_queue, f"child-{i}", "parent")

        valid, count = cycle_detector.check_width_limit("parent")
        assert not valid
