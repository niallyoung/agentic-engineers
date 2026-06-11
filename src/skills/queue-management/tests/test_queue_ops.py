"""
Test Queue Operations

Tests for QueueOperations class with proper validation strings.
"""

import json
import yaml
import pytest
import tempfile
from pathlib import Path

from scripts.queue_ops import QueueOperations, VALID_AGENTS, VALID_STATUSES, VALID_HANDOFF_TYPES
from tests.conftest import VALID_SCOPE, VALID_CONTEXT, VALID_PLAN_STEP1, VALID_PLAN_STEP2


# ---------------------------------------------------------------------------
# Canonical enqueue() fixtures
# ---------------------------------------------------------------------------

VALID_ENQUEUE_SCOPE = (
    "Implement the mandatory enqueue wrapper for DELEGATE and HANDBACK "
    "protocol so all agents must route through queue_ops.enqueue() to "
    "create queue artifacts, preventing direct file writes."
)  # >= 15 words

VALID_ENQUEUE_CONTEXT = (
    "The queue directory lives at ~/.agentic-engineers/{session-id}/{harness}/queue/. "
    "Agents may not write directly to queue subdirectories. All DELEGATEs and HANDBACKs "
    "must pass through enqueue() for schema validation before being written atomically."
)  # >= 20 words

VALID_DELEGATE_ARTIFACT = {
    "handoff_type": "DELEGATE",
    "task_id": "enqueue-test-001",
    "agent": "engineer",
    "scope": VALID_ENQUEUE_SCOPE,
    "plan": [
        "Read the existing queue_ops module to understand validation gaps",
        "Add enqueue() method with canonical schema enforcement",
        "Write tests covering both valid and rejected payloads",
    ],
    "context": VALID_ENQUEUE_CONTEXT,
    "success_criteria": [
        "enqueue() rejects legacy schema fields with clear errors",
        "enqueue() accepts canonical DELEGATE and HANDBACK artifacts",
        "All queue file writes go through enqueue()",
    ],
}

VALID_HANDBACK_ARTIFACT = {
    "handoff_type": "HANDBACK",
    "task_id": "enqueue-test-001",
    "agent": "engineer",
    "status": "success",
    "output": {"deliverables": ["queue_ops.py modified"], "notes": "done"},
    "metrics": {
        "quality": 0.95,
        "tokens": 3200,
        "cost": 0.016,
        "duration_seconds": 38.5,
    },
}


@pytest.fixture
def temp_queue():
    """Create temporary queue directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def queue_ops(temp_queue):
    """Create QueueOperations instance with temp queue."""
    return QueueOperations(session_id="test-session", queue_path=temp_queue)


class TestQueueOpsBasic:
    """Basic tests for QueueOperations."""

    def test_create_delegate_valid(self, queue_ops):
        """Test creating valid DELEGATE."""
        result = queue_ops.create_delegate(
            task_id="test-task-001",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        assert result["status"] == "created"
        assert result["task_id"] == "test-task-001"
        assert "timestamp" in result

    def test_create_delegate_duplicate_fails(self, queue_ops):
        """Test that duplicate task_id raises FileExistsError."""
        queue_ops.create_delegate(
            task_id="duplicate",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        with pytest.raises(FileExistsError):
            queue_ops.create_delegate(
                task_id="duplicate",
                role="Engineer",
                scope=VALID_SCOPE,
                plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
                context=VALID_CONTEXT,
            )

    def test_move_task_valid(self, queue_ops):
        """Test moving task between states."""
        queue_ops.create_delegate(
            task_id="move-test",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        result = queue_ops.move_task("move-test", "incoming", "processing")
        assert result["status"] == "moved"
        assert result["from_state"] == "incoming"
        assert result["to_state"] == "processing"

    def test_query_tasks_by_state(self, queue_ops):
        """Test querying tasks by state."""
        for i in range(3):
            queue_ops.create_delegate(
                task_id=f"task-{i}",
                role="Engineer",
                scope=VALID_SCOPE,
                plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
                context=VALID_CONTEXT,
            )

        tasks = queue_ops.query_tasks("incoming")
        assert len(tasks) == 3

    def test_validate_delegate_valid(self, queue_ops):
        """Test validation of valid DELEGATE."""
        delegate = {
            "task_id": "valid-task",
            "role": "Engineer",
            "scope": VALID_SCOPE,
            "plan": [VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            "context": VALID_CONTEXT,
        }

        valid, errors = queue_ops.validate_delegate(delegate)
        assert valid
        assert len(errors) == 0

    def test_validate_delegate_invalid_scope(self, queue_ops):
        """Test validation with invalid scope."""
        delegate = {
            "task_id": "invalid-task",
            "role": "Engineer",
            "scope": "Too short",  # < 15 words
            "plan": [VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            "context": VALID_CONTEXT,
        }

        valid, errors = queue_ops.validate_delegate(delegate)
        assert not valid
        assert any("scope" in e.lower() for e in errors)

    def test_parent_task_creation(self, queue_ops):
        """Test creating task with parent_task_id."""
        # Create parent
        queue_ops.create_delegate(
            task_id="parent",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        # Create child
        result = queue_ops.create_delegate(
            task_id="child",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
            parent_task_id="parent",
        )

        assert result["parent_task_id"] == "parent"

    def test_query_by_parent(self, queue_ops):
        """Test querying tasks by parent."""
        queue_ops.create_delegate(
            task_id="parent",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        for i in range(2):
            queue_ops.create_delegate(
                task_id=f"child-{i}",
                role="Engineer",
                scope=VALID_SCOPE,
                plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
                context=VALID_CONTEXT,
                parent_task_id="parent",
            )

        children = queue_ops.query_tasks("incoming", parent_task_id="parent")
        assert len(children) == 2

    def test_rate_limit_status(self, queue_ops):
        """Test getting rate limit status."""
        status = queue_ops.get_rate_limit_status("test-session")
        assert status["limit"] == 100
        assert status["tasks_this_hour"] == 0

    def test_move_task_to_done(self, queue_ops):
        """Test complete workflow: create -> processing -> done."""
        queue_ops.create_delegate(
            task_id="workflow-test",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        queue_ops.move_task("workflow-test", "incoming", "processing")
        queue_ops.move_task("workflow-test", "processing", "done")

        done_tasks = queue_ops.query_tasks("done")
        assert len(done_tasks) == 1
        assert done_tasks[0]["task_id"] == "workflow-test"


# ===========================================================================
# Tests for mandatory enqueue() wrapper
# ===========================================================================

class TestEnqueueCanonicalSchema:
    """enqueue() accepts canonical schema for DELEGATE and HANDBACK."""

    def test_enqueue_valid_delegate(self, queue_ops):
        """Valid canonical DELEGATE artifact is accepted and written to incoming/."""
        result = queue_ops.enqueue(VALID_DELEGATE_ARTIFACT)

        assert result["status"] == "enqueued"
        assert result["handoff_type"] == "DELEGATE"
        assert result["task_id"] == "enqueue-test-001"
        assert "timestamp" in result
        assert "queue_path" in result

        # File must exist in incoming/
        written = Path(result["queue_path"])
        assert written.exists(), "DELEGATE file must be written to incoming/"
        with open(written) as f:
            on_disk = yaml.safe_load(f)
        assert on_disk["handoff_type"] == "DELEGATE"
        assert on_disk["agent"] == "engineer"
        assert on_disk["task_id"] == "enqueue-test-001"

    def test_enqueue_valid_handback(self, queue_ops):
        """Valid canonical HANDBACK artifact is accepted and written to processing/."""
        result = queue_ops.enqueue(VALID_HANDBACK_ARTIFACT)

        assert result["status"] == "enqueued"
        assert result["handoff_type"] == "HANDBACK"
        assert result["task_id"] == "enqueue-test-001"
        assert "timestamp" in result

        written = Path(result["queue_path"])
        assert written.exists(), "HANDBACK file must be written to processing/"
        # Path should contain 'processing'
        assert "processing" in str(written)

    def test_enqueue_all_valid_agents(self, queue_ops):
        """enqueue() accepts each of the 8 canonical agent names."""
        for i, agent in enumerate(sorted(VALID_AGENTS)):
            artifact = {
                **VALID_DELEGATE_ARTIFACT,
                "task_id": f"agent-test-{i:03d}",
                "agent": agent,
            }
            result = queue_ops.enqueue(artifact)
            assert result["status"] == "enqueued", (
                f"agent '{agent}' should be valid"
            )

    def test_enqueue_all_valid_handback_statuses(self, queue_ops):
        """enqueue() accepts each of the 5 canonical HANDBACK status values."""
        for i, status in enumerate(sorted(VALID_STATUSES)):
            artifact = {
                **VALID_HANDBACK_ARTIFACT,
                "task_id": f"status-test-{i:03d}",
                "status": status,
            }
            result = queue_ops.enqueue(artifact)
            assert result["status"] == "enqueued", (
                f"status '{status}' should be valid"
            )

    def test_enqueue_context_as_list(self, queue_ops):
        """enqueue() accepts context as a non-empty list of strings."""
        artifact = {
            **VALID_DELEGATE_ARTIFACT,
            "task_id": "context-list-001",
            "context": [
                "The queue operations module handles all atomic file writes.",
                "Agents route work through enqueue() for validation and rate limiting.",
            ],
        }
        result = queue_ops.enqueue(artifact)
        assert result["status"] == "enqueued"

    def test_enqueue_returns_file_path(self, queue_ops):
        """enqueue() returns the exact path of the written file."""
        result = queue_ops.enqueue(VALID_DELEGATE_ARTIFACT)
        written = Path(result["queue_path"])
        assert written.exists()
        assert written.suffix == ".yaml"  # SPEC: queue files are YAML
        assert written.stem == "enqueue-test-001"

    def test_enqueue_file_contains_enqueued_at(self, queue_ops):
        """Written file includes enqueued_at timestamp added by enqueue()."""
        result = queue_ops.enqueue(VALID_DELEGATE_ARTIFACT)
        with open(result["queue_path"]) as f:
            on_disk = yaml.safe_load(f)
        assert "enqueued_at" in on_disk
        assert "queue_state" in on_disk
        assert on_disk["queue_state"] == "incoming"


class TestEnqueueRejectsLegacyFields:
    """enqueue() rejects artifacts with old/legacy schema fields."""

    def test_rejects_type_field(self, queue_ops):
        """enqueue() rejects 'type' field (old schema) with clear guidance."""
        artifact = {
            **VALID_DELEGATE_ARTIFACT,
            "type": "DELEGATE",  # old field — must be handoff_type
        }
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)

        error_msg = str(exc_info.value)
        assert "type" in error_msg
        assert "handoff_type" in error_msg, "Error must guide user to use handoff_type"
        assert "legacy" in error_msg.lower()

    def test_rejects_role_field(self, queue_ops):
        """enqueue() rejects 'role' field (old schema) with guidance to use 'agent'."""
        artifact = {
            **VALID_DELEGATE_ARTIFACT,
            "role": "Engineer",  # old field — must be agent
        }
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)

        error_msg = str(exc_info.value)
        assert "role" in error_msg
        assert "agent" in error_msg, "Error must guide user to use 'agent' field"

    def test_rejects_top_level_quality_score(self, queue_ops):
        """enqueue() rejects top-level quality_score with guidance to put in metrics."""
        artifact = {
            **VALID_DELEGATE_ARTIFACT,
            "quality_score": 92,  # must be inside metrics.quality
        }
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)

        error_msg = str(exc_info.value)
        assert "quality_score" in error_msg
        assert "metrics" in error_msg, "Error must guide user to move it into metrics"

    def test_rejects_multiple_legacy_fields_together(self, queue_ops):
        """All legacy fields in one artifact all appear in the error message."""
        artifact = {
            **VALID_DELEGATE_ARTIFACT,
            "type": "DELEGATE",
            "role": "Engineer",
            "quality_score": 90,
        }
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)

        error_msg = str(exc_info.value)
        assert "type" in error_msg
        assert "role" in error_msg
        assert "quality_score" in error_msg

    def test_rejects_missing_handoff_type(self, queue_ops):
        """enqueue() rejects artifact with no handoff_type field."""
        artifact = {k: v for k, v in VALID_DELEGATE_ARTIFACT.items() if k != "handoff_type"}
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        assert "handoff_type" in str(exc_info.value)

    def test_rejects_invalid_handoff_type(self, queue_ops):
        """enqueue() rejects unsupported handoff_type values."""
        artifact = {**VALID_DELEGATE_ARTIFACT, "handoff_type": "TASK"}
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        assert "handoff_type" in str(exc_info.value)

    def test_rejects_missing_agent(self, queue_ops):
        """enqueue() rejects artifact with no agent field."""
        artifact = {k: v for k, v in VALID_DELEGATE_ARTIFACT.items() if k != "agent"}
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        assert "agent" in str(exc_info.value)

    def test_rejects_invalid_agent(self, queue_ops):
        """enqueue() rejects unknown agent names."""
        artifact = {**VALID_DELEGATE_ARTIFACT, "agent": "unknown-agent-xyz"}
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        assert "agent" in str(exc_info.value)


class TestEnqueueDelegateFieldValidation:
    """enqueue() validates DELEGATE-specific required fields."""

    def test_rejects_short_scope(self, queue_ops):
        """Scope with fewer than 15 words is rejected."""
        artifact = {**VALID_DELEGATE_ARTIFACT, "scope": "Too short scope"}
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        assert "scope" in str(exc_info.value)
        assert "15" in str(exc_info.value)

    def test_rejects_missing_scope(self, queue_ops):
        """Missing scope is rejected."""
        artifact = {k: v for k, v in VALID_DELEGATE_ARTIFACT.items() if k != "scope"}
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        assert "scope" in str(exc_info.value)

    def test_rejects_plan_with_one_step(self, queue_ops):
        """Plan with fewer than 2 steps is rejected."""
        artifact = {
            **VALID_DELEGATE_ARTIFACT,
            "task_id": "plan-one-step",
            "plan": ["Only one step here which is not enough"],
        }
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        assert "plan" in str(exc_info.value)

    def test_rejects_plan_step_too_short(self, queue_ops):
        """Plan step with fewer than 3 words is rejected."""
        artifact = {
            **VALID_DELEGATE_ARTIFACT,
            "task_id": "plan-short-step",
            "plan": ["Good detailed first step here", "Bad"],
        }
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        assert "plan" in str(exc_info.value)

    def test_rejects_short_context(self, queue_ops):
        """Context string with fewer than 20 words is rejected."""
        artifact = {
            **VALID_DELEGATE_ARTIFACT,
            "task_id": "short-context-001",
            "context": "This context is too short.",
        }
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        assert "context" in str(exc_info.value)

    def test_rejects_empty_success_criteria(self, queue_ops):
        """Empty success_criteria list is rejected."""
        artifact = {
            **VALID_DELEGATE_ARTIFACT,
            "task_id": "empty-sc-001",
            "success_criteria": [],
        }
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        assert "success_criteria" in str(exc_info.value)

    def test_rejects_missing_success_criteria(self, queue_ops):
        """Missing success_criteria is rejected."""
        artifact = {
            k: v for k, v in VALID_DELEGATE_ARTIFACT.items()
            if k != "success_criteria"
        }
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        assert "success_criteria" in str(exc_info.value)


class TestEnqueueHandbackFieldValidation:
    """enqueue() validates HANDBACK-specific required fields."""

    def test_rejects_invalid_status(self, queue_ops):
        """HANDBACK with non-canonical status is rejected."""
        artifact = {**VALID_HANDBACK_ARTIFACT, "status": "complete"}  # legacy alias
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        error_msg = str(exc_info.value)
        assert "status" in error_msg

    def test_rejects_missing_output(self, queue_ops):
        """HANDBACK without output field is rejected."""
        artifact = {k: v for k, v in VALID_HANDBACK_ARTIFACT.items() if k != "output"}
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        assert "output" in str(exc_info.value)

    def test_rejects_missing_metrics(self, queue_ops):
        """HANDBACK without metrics is rejected."""
        artifact = {k: v for k, v in VALID_HANDBACK_ARTIFACT.items() if k != "metrics"}
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        assert "metrics" in str(exc_info.value)

    def test_rejects_metrics_quality_out_of_range(self, queue_ops):
        """metrics.quality outside 0.0-1.0 is rejected."""
        for bad_quality in [1.5, -0.1, 101]:
            artifact = {
                **VALID_HANDBACK_ARTIFACT,
                "task_id": f"quality-test-{bad_quality}".replace(".", ""),
                "metrics": {**VALID_HANDBACK_ARTIFACT["metrics"], "quality": bad_quality},
            }
            with pytest.raises(ValueError) as exc_info:
                queue_ops.enqueue(artifact)
            assert "quality" in str(exc_info.value)

    def test_rejects_metrics_tokens_negative(self, queue_ops):
        """metrics.tokens as negative is rejected."""
        artifact = {
            **VALID_HANDBACK_ARTIFACT,
            "task_id": "neg-tokens-001",
            "metrics": {**VALID_HANDBACK_ARTIFACT["metrics"], "tokens": -1},
        }
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        assert "tokens" in str(exc_info.value)

    def test_rejects_metrics_cost_negative(self, queue_ops):
        """metrics.cost as negative is rejected."""
        artifact = {
            **VALID_HANDBACK_ARTIFACT,
            "task_id": "neg-cost-001",
            "metrics": {**VALID_HANDBACK_ARTIFACT["metrics"], "cost": -0.01},
        }
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        assert "cost" in str(exc_info.value)

    def test_rejects_metrics_duration_negative(self, queue_ops):
        """metrics.duration_seconds as negative is rejected."""
        artifact = {
            **VALID_HANDBACK_ARTIFACT,
            "task_id": "neg-duration-001",
            "metrics": {**VALID_HANDBACK_ARTIFACT["metrics"], "duration_seconds": -1},
        }
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        assert "duration_seconds" in str(exc_info.value)

    def test_rejects_metrics_missing_required_subfields(self, queue_ops):
        """Missing required metrics subfields are all reported."""
        artifact = {
            **VALID_HANDBACK_ARTIFACT,
            "task_id": "empty-metrics-001",
            "metrics": {},  # all required subfields missing
        }
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue(artifact)
        error_msg = str(exc_info.value)
        assert "quality" in error_msg
        assert "tokens" in error_msg
        assert "cost" in error_msg
        assert "duration_seconds" in error_msg


class TestEnqueueDuplicateAndRateLimit:
    """enqueue() enforces duplicate and rate-limit guards."""

    def test_rejects_duplicate_task_id(self, queue_ops):
        """enqueue() raises FileExistsError on duplicate task_id."""
        queue_ops.enqueue(VALID_DELEGATE_ARTIFACT)
        with pytest.raises(FileExistsError):
            queue_ops.enqueue(VALID_DELEGATE_ARTIFACT)

    def test_error_messages_are_actionable(self, queue_ops):
        """All enqueue() error messages include actionable guidance."""
        # Legacy 'type' field
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue({**VALID_DELEGATE_ARTIFACT, "type": "DELEGATE"})
        msg = str(exc_info.value)
        # Must explain what to use instead
        assert "handoff_type" in msg

        # Invalid agent
        with pytest.raises(ValueError) as exc_info:
            queue_ops.enqueue({**VALID_DELEGATE_ARTIFACT, "task_id": "t2", "agent": "bad"})
        msg = str(exc_info.value)
        assert "engineer" in msg.lower() or "orchestrator" in msg.lower()  # shows valid options
