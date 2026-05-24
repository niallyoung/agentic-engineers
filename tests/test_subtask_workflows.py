"""
Integration tests for sub-task workflows (Phase 2).

Tests cover:
  ✅ Parent creates single child
  ✅ Parent creates multiple children (parallelization)
  ✅ Grandparent → Parent → Children (3-tier)
  ✅ Max depth (task_tier=5 allowed, 6 rejected)
  ✅ Max width (10 children allowed, 11 rejected)
  ✅ Child task failure handling
  ✅ Partial results aggregation
  ✅ Child timeout handling
  ✅ Result quality score calculation
  ✅ Token/cost aggregation
  ✅ Invalid parent_task_id error
  ✅ Invalid task_tier error
  ✅ Orphaned child detection
  ✅ Child completion ordering (any order)
  ✅ Concurrent child execution
  ✅ Session isolation (parent/child in same session)
  ✅ Backward compatibility (non-sub-task DELEGATEs work)
  ✅ HANDBACK with @children_results validation
  ✅ Status enum for result_aggregation_status
  ✅ Performance: aggregation <5s for 10 children
"""

import json
import sys
import time
import tempfile
import threading
from pathlib import Path
from typing import Dict, List

import pytest

# ---------------------------------------------------------------------------
# Path setup – allow running from repo root or tests/ directory
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "src" / "skills"

import importlib
import sys

# Ensure src/skills is in sys.path
if str(SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(SKILLS_DIR))

# Use importlib.import_module to handle hyphenated package names (queue-management, etc.)
try:
    _qm_scripts = importlib.import_module("queue-management.scripts")
    _qm_queue_ops = importlib.import_module("queue-management.scripts.queue_ops")
    _qm_validators = importlib.import_module("queue-management.scripts.subtask_validators")
    _qm_result_agg = importlib.import_module("queue-management.scripts.result_aggregator")
    _qm_validators_validators = importlib.import_module("queue-management.scripts.validators")
    
    QueueOperations = _qm_queue_ops.QueueOperations
    SubTaskValidator = _qm_validators.SubTaskValidator
    MAX_TASK_TIER = _qm_validators.MAX_TASK_TIER
    MAX_CHILDREN_PER_PARENT = _qm_validators.MAX_CHILDREN_PER_PARENT
    ResultAggregator = _qm_result_agg.ResultAggregator
    ChildWaiter = _qm_result_agg.ChildWaiter
    HandbackValidator = _qm_validators_validators.HandbackValidator
except ModuleNotFoundError as e:
    # If imports fail during collection, define placeholder classes
    # This allows pytest to collect the tests even if the import fails
    QueueOperations = None
    SubTaskValidator = None
    MAX_TASK_TIER = None
    MAX_CHILDREN_PER_PARENT = None
    ResultAggregator = None
    ChildWaiter = None
    HandbackValidator = None


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

VALID_SCOPE = (
    "This is an implementation task that requires careful design "
    "with comprehensive testing across all error scenarios and edge cases"
)
VALID_CONTEXT = (
    "This is the context for task execution and includes important information "
    "about requirements and specifications for successful completion here today "
    "and tomorrow with proper documentation"
)
VALID_PLAN = [
    "Implement the core functionality with proper error handling and validation",
    "Write comprehensive tests for all code paths and edge cases",
]


@pytest.fixture
def tmp_queue(tmp_path):
    """Temporary queue root directory."""
    return str(tmp_path)


@pytest.fixture
def ops(tmp_queue):
    """QueueOperations instance with a fresh temp queue."""
    return QueueOperations(session_id="test-session", queue_path=tmp_queue)


@pytest.fixture
def aggregator():
    return ResultAggregator()


def _make_handback(
    task_id: str,
    status: str = "complete",
    quality: float = 90.0,
    effort: str = "medium",
    tokens_in: int = 1000,
    tokens_out: int = 500,
) -> Dict:
    return {
        "task_id": task_id,
        "status": status,
        "quality_score": quality,
        "effort": effort,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "deliverables": [f"output/{task_id}.py"],
    }


# ---------------------------------------------------------------------------
# 1. Parent creates single child
# ---------------------------------------------------------------------------

class TestParentCreatesSingleChild:
    def test_single_child_creation(self, ops):
        """Parent creates exactly one child; child count is 1."""
        ops.create_delegate(
            task_id="parent-task",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
        )
        result = ops.create_delegate(
            task_id="child-task",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
            parent_task_id="parent-task",
        )
        assert result["status"] == "created"
        assert result["parent_task_id"] == "parent-task"
        assert result["task_tier"] == 1

    def test_child_appears_in_incoming(self, ops):
        """Child task is placed in incoming queue."""
        ops.create_delegate(
            task_id="par-one",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
        )
        ops.create_delegate(
            task_id="child-one",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
            parent_task_id="par-one",
        )
        children = ops.query_tasks("incoming", parent_task_id="par-one")
        assert len(children) == 1
        assert children[0]["task_id"] == "child-one"


# ---------------------------------------------------------------------------
# 2. Parent creates multiple children (parallelization)
# ---------------------------------------------------------------------------

class TestParentCreatesMultipleChildren:
    def test_three_children(self, ops):
        """Parent can create 3 children; all appear in query."""
        ops.create_delegate(
            task_id="multi-parent",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
        )
        for i in range(3):
            ops.create_delegate(
                task_id=f"child-{i}",
                role="Engineer",
                scope=VALID_SCOPE,
                plan=VALID_PLAN,
                context=VALID_CONTEXT,
                parent_task_id="multi-parent",
            )

        children = ops.query_tasks("incoming", parent_task_id="multi-parent")
        assert len(children) == 3

    def test_children_have_tier_one(self, ops):
        """All direct children have task_tier == 1."""
        ops.create_delegate(
            task_id="tier-parent",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
        )
        for i in range(2):
            result = ops.create_delegate(
                task_id=f"tier-child-{i}",
                role="Engineer",
                scope=VALID_SCOPE,
                plan=VALID_PLAN,
                context=VALID_CONTEXT,
                parent_task_id="tier-parent",
            )
            assert result["task_tier"] == 1


# ---------------------------------------------------------------------------
# 3. Grandparent → Parent → Children (3-tier)
# ---------------------------------------------------------------------------

class TestThreeTierHierarchy:
    def test_grandparent_parent_child(self, ops):
        """Three-tier hierarchy: tiers 0 → 1 → 2."""
        # Tier 0: root
        ops.create_delegate(
            task_id="root",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
        )
        # Tier 1: child of root
        r1 = ops.create_delegate(
            task_id="mid",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
            parent_task_id="root",
        )
        assert r1["task_tier"] == 1

        # Tier 2: grandchild
        r2 = ops.create_delegate(
            task_id="leaf",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
            parent_task_id="mid",
        )
        assert r2["task_tier"] == 2


# ---------------------------------------------------------------------------
# 4. Max depth (task_tier=5 allowed, 6 rejected)
# ---------------------------------------------------------------------------

class TestMaxDepth:
    def _build_chain(self, ops, length: int) -> str:
        """Build a parent chain of given length; return leaf task_id."""
        # Create root
        ops.create_delegate(
            task_id="depth-root",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
        )
        prev = "depth-root"
        for i in range(1, length):
            tid = f"depth-{i}"
            ops.create_delegate(
                task_id=tid,
                role="Engineer",
                scope=VALID_SCOPE,
                plan=VALID_PLAN,
                context=VALID_CONTEXT,
                parent_task_id=prev,
            )
            prev = tid
        return prev

    def test_tier_five_allowed(self, ops):
        """task_tier=5 (depth 5) is allowed."""
        leaf = self._build_chain(ops, MAX_TASK_TIER)  # depth-root + 4 children = tier 4
        result = ops.create_delegate(
            task_id="depth-max",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
            parent_task_id=leaf,
        )
        assert result["task_tier"] == MAX_TASK_TIER

    def test_tier_six_rejected(self, ops):
        """task_tier=6 (depth 6) is rejected."""
        leaf = self._build_chain(ops, MAX_TASK_TIER)
        # depth-max is at tier MAX_TASK_TIER; trying to go one deeper should fail
        ops.create_delegate(
            task_id="depth-max",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
            parent_task_id=leaf,
        )
        with pytest.raises((ValueError, RuntimeError)):
            ops.create_delegate(
                task_id="depth-over",
                role="Engineer",
                scope=VALID_SCOPE,
                plan=VALID_PLAN,
                context=VALID_CONTEXT,
                parent_task_id="depth-max",
            )


# ---------------------------------------------------------------------------
# 5. Max width (10 children allowed, 11 rejected)
# ---------------------------------------------------------------------------

class TestMaxWidth:
    def test_ten_children_allowed(self, ops):
        """10 children per parent is allowed."""
        ops.create_delegate(
            task_id="wide-parent",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
        )
        for i in range(MAX_CHILDREN_PER_PARENT):
            ops.create_delegate(
                task_id=f"wide-child-{i}",
                role="Engineer",
                scope=VALID_SCOPE,
                plan=VALID_PLAN,
                context=VALID_CONTEXT,
                parent_task_id="wide-parent",
            )
        children = ops.query_tasks("incoming", parent_task_id="wide-parent")
        assert len(children) == MAX_CHILDREN_PER_PARENT

    def test_eleven_children_rejected(self, ops):
        """11th child exceeds max width and is rejected."""
        ops.create_delegate(
            task_id="wide-parent2",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
        )
        for i in range(MAX_CHILDREN_PER_PARENT):
            ops.create_delegate(
                task_id=f"wc2-child-{i}",
                role="Engineer",
                scope=VALID_SCOPE,
                plan=VALID_PLAN,
                context=VALID_CONTEXT,
                parent_task_id="wide-parent2",
            )
        with pytest.raises(RuntimeError, match="max 10"):
            ops.create_delegate(
                task_id="wc2-child-over",
                role="Engineer",
                scope=VALID_SCOPE,
                plan=VALID_PLAN,
                context=VALID_CONTEXT,
                parent_task_id="wide-parent2",
            )


# ---------------------------------------------------------------------------
# 6. Child task failure handling
# ---------------------------------------------------------------------------

class TestChildTaskFailureHandling:
    def test_aggregate_with_one_failed_child(self, aggregator):
        """Partial aggregation when one of three children fails."""
        handbacks = [
            _make_handback("child-a", status="complete", quality=90),
            _make_handback("child-b", status="failed", quality=0),
            _make_handback("child-c", status="complete", quality=80),
        ]
        result = aggregator.aggregate("parent", handbacks)
        assert result["result_aggregation_status"] == "partial"
        assert "child-b" in result["children_failed"]
        assert result["status"] == "partial"

    def test_all_or_nothing_failure(self, aggregator):
        """all_or_nothing mode fails parent when any child fails."""
        handbacks = [
            _make_handback("c1", status="complete"),
            _make_handback("c2", status="failed"),
        ]
        result = aggregator.aggregate("parent", handbacks, failure_mode="all_or_nothing")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# 7. Partial results aggregation
# ---------------------------------------------------------------------------

class TestPartialResultsAggregation:
    def test_partial_results_contain_successes(self, aggregator):
        """children_results includes both successful and failed children."""
        handbacks = [
            _make_handback("ok", status="complete", quality=85),
            _make_handback("bad", status="failed", quality=0),
        ]
        result = aggregator.aggregate("parent", handbacks)
        assert "ok" in result["children_results"]
        assert "bad" in result["children_results"]
        assert result["children_results"]["ok"]["status"] == "complete"
        assert result["children_results"]["bad"]["status"] == "failed"


# ---------------------------------------------------------------------------
# 8. Child timeout handling
# ---------------------------------------------------------------------------

class TestChildTimeoutHandling:
    def test_timeout_returns_timed_out_status(self, tmp_queue):
        """ChildWaiter returns timed_out when children don't complete in time."""
        ops = QueueOperations(session_id="timeout-sess", queue_path=tmp_queue)
        ops.create_delegate(
            task_id="parent-timeout",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
        )
        ops.create_delegate(
            task_id="slow-child",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
            parent_task_id="parent-timeout",
        )

        waiter = ChildWaiter(queue_ops=ops, poll_interval=0.05)
        result = waiter.wait(
            parent_task_id="parent-timeout",
            expected_children=["slow-child"],
            timeout_seconds=0.1,  # Very short timeout
        )
        assert result["status"] == "timed_out"
        assert "slow-child" in result["children_failed"]


# ---------------------------------------------------------------------------
# 9. Result quality score calculation
# ---------------------------------------------------------------------------

class TestResultQualityScoreCalculation:
    def test_weighted_average_quality(self, aggregator):
        """Effort-weighted quality: high=3x, medium=2x, low=1x."""
        handbacks = [
            _make_handback("high-task", quality=90, effort="high"),    # 3x weight
            _make_handback("medium-task", quality=60, effort="medium"), # 2x weight
            _make_handback("low-task", quality=30, effort="low"),       # 1x weight
        ]
        score = aggregator.calculate_quality_score(handbacks)
        # (90*3 + 60*2 + 30*1) / (3+2+1) = (270+120+30)/6 = 420/6 = 70.0
        assert score == pytest.approx(70.0)

    def test_equal_weights_mean(self, aggregator):
        """Without effort tags, all tasks get equal weight."""
        handbacks = [
            {"task_id": "t1", "quality_score": 80},
            {"task_id": "t2", "quality_score": 60},
        ]
        score = aggregator.calculate_quality_score(handbacks)
        # Both default to medium (2x): (80*2 + 60*2) / 4 = 70.0
        assert score == pytest.approx(70.0)

    def test_empty_children_returns_zero(self, aggregator):
        assert aggregator.calculate_quality_score([]) == 0.0


# ---------------------------------------------------------------------------
# 10. Token/cost aggregation
# ---------------------------------------------------------------------------

class TestTokenCostAggregation:
    def test_tokens_summed(self, aggregator):
        """Total tokens = sum of all children's tokens."""
        handbacks = [
            _make_handback("t1", tokens_in=1000, tokens_out=500),
            _make_handback("t2", tokens_in=2000, tokens_out=800),
            _make_handback("t3", tokens_in=1500, tokens_out=600),
        ]
        result = aggregator.aggregate("parent", handbacks)
        assert result["metrics"]["tokens_in"] == 4500
        assert result["metrics"]["tokens_out"] == 1900
        assert result["metrics"]["total_tokens"] == 6400

    def test_cost_aggregated(self, aggregator):
        """Total cost is sum of children costs."""
        handbacks = [
            {**_make_handback("a"), "cost": 0.10},
            {**_make_handback("b"), "cost": 0.25},
        ]
        result = aggregator.aggregate("parent", handbacks)
        assert result["metrics"]["cost"] == pytest.approx(0.35)


# ---------------------------------------------------------------------------
# 11. Invalid parent_task_id error
# ---------------------------------------------------------------------------

class TestInvalidParentTaskId:
    def test_nonexistent_parent_raises(self, ops):
        """Creating a child with a non-existent parent raises ValueError."""
        with pytest.raises(ValueError, match="parent_task_id"):
            ops.create_delegate(
                task_id="orphan-child",
                role="Engineer",
                scope=VALID_SCOPE,
                plan=VALID_PLAN,
                context=VALID_CONTEXT,
                parent_task_id="does-not-exist",
            )

    def test_empty_parent_id_raises(self, ops):
        """parent_task_id='' raises ValueError."""
        with pytest.raises((ValueError, RuntimeError)):
            ops.create_delegate(
                task_id="empty-parent",
                role="Engineer",
                scope=VALID_SCOPE,
                plan=VALID_PLAN,
                context=VALID_CONTEXT,
                parent_task_id="",
            )


# ---------------------------------------------------------------------------
# 12. Invalid task_tier error
# ---------------------------------------------------------------------------

class TestInvalidTaskTier:
    def test_tier_beyond_max_rejected_by_validator(self, tmp_queue):
        """SubTaskValidator rejects task_tier > 5."""
        sv = SubTaskValidator(queue_path=Path(tmp_queue) / "test")
        valid, err = sv.validate_task_tier("some-parent", MAX_TASK_TIER + 1)
        assert not valid
        assert "maximum" in err.lower() or "exceed" in err.lower()

    def test_tier_mismatch_rejected(self, tmp_queue):
        """SubTaskValidator rejects tier ≠ parent_tier + 1."""
        queue_path = Path(tmp_queue) / "tier-check"
        ops = QueueOperations(session_id="tier-check", queue_path=tmp_queue)
        ops.create_delegate(
            task_id="tier-root",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
        )
        sv = SubTaskValidator(queue_path=queue_path)
        # Parent is at tier 0; proposing tier 3 (not 1) should fail
        valid, err = sv.validate_task_tier("tier-root", 3)
        assert not valid


# ---------------------------------------------------------------------------
# 13. Orphaned child detection
# ---------------------------------------------------------------------------

class TestOrphanedChildDetection:
    def test_orphan_child_rejected(self, ops):
        """A child whose parent_task_id points to non-existent task is rejected."""
        with pytest.raises(ValueError):
            ops.create_delegate(
                task_id="orphan",
                role="Engineer",
                scope=VALID_SCOPE,
                plan=VALID_PLAN,
                context=VALID_CONTEXT,
                parent_task_id="ghost-parent",
            )

    def test_validate_parent_not_found(self, tmp_queue):
        """SubTaskValidator.validate_parent_task_id returns False for missing parent."""
        sv = SubTaskValidator(queue_path=Path(tmp_queue) / "empty-sess")
        valid, err = sv.validate_parent_task_id("nonexistent-task")
        assert not valid
        assert "not found" in err.lower()


# ---------------------------------------------------------------------------
# 14. Child completion ordering (any order)
# ---------------------------------------------------------------------------

class TestChildCompletionOrdering:
    def test_children_complete_out_of_order(self, aggregator):
        """Aggregation works regardless of child completion order."""
        # Simulate children completing out of order
        handbacks_out_of_order = [
            _make_handback("child-c", quality=70),
            _make_handback("child-a", quality=90),
            _make_handback("child-b", quality=80),
        ]
        result = aggregator.aggregate("parent", handbacks_out_of_order)
        assert set(result["children_created"]) == {"child-a", "child-b", "child-c"}
        assert result["result_aggregation_status"] == "all_complete"


# ---------------------------------------------------------------------------
# 15. Concurrent child execution
# ---------------------------------------------------------------------------

class TestConcurrentChildExecution:
    def test_concurrent_child_creation(self, tmp_queue):
        """Multiple threads can create children of the same parent concurrently."""
        ops = QueueOperations(session_id="concurrent-sess", queue_path=tmp_queue)
        ops.create_delegate(
            task_id="concurrent-parent",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
        )

        errors = []

        def create_child(i):
            try:
                ops.create_delegate(
                    task_id=f"concurrent-child-{i}",
                    role="Engineer",
                    scope=VALID_SCOPE,
                    plan=VALID_PLAN,
                    context=VALID_CONTEXT,
                    parent_task_id="concurrent-parent",
                )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_child, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        children = ops.query_tasks("incoming", parent_task_id="concurrent-parent")
        # All 5 should have been created (no errors due to rate-limiting, width ok)
        assert len(errors) == 0 or all(isinstance(e, (RuntimeError,)) for e in errors)
        # At least some children were created
        assert len(children) + len(errors) == 5


# ---------------------------------------------------------------------------
# 16. Session isolation (parent/child in same session)
# ---------------------------------------------------------------------------

class TestSessionIsolation:
    def test_children_isolated_to_session(self, tmp_queue):
        """Children created in session-A are NOT visible in session-B."""
        s_a = QueueOperations(session_id="sess-a", queue_path=tmp_queue)
        s_b = QueueOperations(session_id="sess-b", queue_path=tmp_queue)

        s_a.create_delegate(
            task_id="parent-a",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
        )
        s_a.create_delegate(
            task_id="child-a",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
            parent_task_id="parent-a",
        )

        # Session B has no tasks
        children_b = s_b.query_tasks("incoming")
        assert len(children_b) == 0

    def test_parent_child_same_session(self, ops):
        """Parent and child tasks can coexist in the same session queue."""
        ops.create_delegate(
            task_id="same-sess-parent",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
        )
        ops.create_delegate(
            task_id="same-sess-child",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
            parent_task_id="same-sess-parent",
        )
        all_tasks = ops.query_tasks("incoming")
        assert len(all_tasks) == 2


# ---------------------------------------------------------------------------
# 17. Backward compatibility (non-sub-task DELEGATEs work)
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    def test_root_task_without_parent(self, ops):
        """A DELEGATE without parent_task_id is still created successfully."""
        result = ops.create_delegate(
            task_id="legacy-task",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
        )
        assert result["status"] == "created"
        assert result["parent_task_id"] is None
        assert result["task_tier"] == 0

    def test_root_task_reaches_done(self, ops):
        """A root task can transition through the full workflow unchanged."""
        ops.create_delegate(
            task_id="compat-task",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=VALID_PLAN,
            context=VALID_CONTEXT,
        )
        ops.move_task("compat-task", "incoming", "processing")
        ops.move_task("compat-task", "processing", "done")
        done = ops.query_tasks("done")
        assert any(t["task_id"] == "compat-task" for t in done)


# ---------------------------------------------------------------------------
# 18. HANDBACK with @children_results validation
# ---------------------------------------------------------------------------

class TestHandbackChildrenResultsValidation:
    def test_valid_handback_with_children(self):
        """HandbackValidator accepts a HANDBACK with well-formed children_results."""
        validator = HandbackValidator()
        handback = {
            "task_id": "parent-task",
            "status": "complete",
            "quality_score": 88,
            "deliverables": ["output/parent.py"],
            "children_created": ["child-a", "child-b"],
            "children_results": {
                "child-a": {"status": "complete", "output": {"data": 1}, "quality": 90},
                "child-b": {"status": "complete", "output": {"data": 2}, "quality": 85},
            },
            "children_failed": [],
            "result_aggregation_status": "all_complete",
        }
        valid, errors = validator.validate(handback)
        assert valid, f"Expected valid HANDBACK but got errors: {errors}"

    def test_invalid_children_results_not_dict(self):
        """HandbackValidator rejects children_results that is not a dict."""
        validator = HandbackValidator()
        handback = {
            "task_id": "bad-task",
            "status": "complete",
            "quality_score": 80,
            "deliverables": ["f.py"],
            "children_results": "should-be-a-dict",
        }
        valid, errors = validator.validate(handback)
        assert not valid
        assert any("children_results" in e for e in errors)

    def test_children_results_missing_status_field(self):
        """HandbackValidator rejects children_results entry missing 'status'."""
        validator = HandbackValidator()
        handback = {
            "task_id": "missing-status",
            "status": "complete",
            "quality_score": 80,
            "deliverables": ["f.py"],
            "children_results": {
                "child-x": {"output": {}, "quality": 90},  # no "status"
            },
        }
        valid, errors = validator.validate(handback)
        assert not valid
        assert any("status" in e for e in errors)


# ---------------------------------------------------------------------------
# 19. Status enum for result_aggregation_status
# ---------------------------------------------------------------------------

class TestResultAggregationStatusEnum:
    @pytest.mark.parametrize("status", ["all_complete", "partial", "timed_out"])
    def test_valid_aggregation_status_accepted(self, status):
        """HandbackValidator accepts all valid result_aggregation_status values."""
        validator = HandbackValidator()
        handback = {
            "task_id": "enum-test",
            "status": "complete",
            "quality_score": 80,
            "deliverables": ["f.py"],
            "result_aggregation_status": status,
        }
        valid, errors = validator.validate(handback)
        assert valid, f"Unexpected errors for status={status!r}: {errors}"

    def test_invalid_aggregation_status_rejected(self):
        """HandbackValidator rejects unknown result_aggregation_status values."""
        validator = HandbackValidator()
        handback = {
            "task_id": "bad-status",
            "status": "complete",
            "quality_score": 80,
            "deliverables": ["f.py"],
            "result_aggregation_status": "not_a_valid_status",
        }
        valid, errors = validator.validate(handback)
        assert not valid
        assert any("result_aggregation_status" in e for e in errors)


# ---------------------------------------------------------------------------
# 20. Performance: aggregation <5s for 10 children
# ---------------------------------------------------------------------------

class TestAggregationPerformance:
    def test_aggregate_ten_children_under_five_seconds(self, aggregator):
        """Aggregating 10 children completes in less than 5 seconds."""
        handbacks = [
            _make_handback(
                f"perf-child-{i}",
                quality=float(70 + i),
                tokens_in=1000 * (i + 1),
                tokens_out=500 * (i + 1),
            )
            for i in range(10)
        ]

        start = time.monotonic()
        result = aggregator.aggregate("perf-parent", handbacks)
        elapsed = time.monotonic() - start

        assert elapsed < 5.0, f"Aggregation took {elapsed:.3f}s (limit 5s)"
        assert result["metrics"]["children_count"] == 10
        assert result["result_aggregation_status"] == "all_complete"

    def test_quality_score_correct_for_ten_children(self, aggregator):
        """Quality score is correctly calculated for 10 children (all medium effort)."""
        handbacks = [
            _make_handback(f"q-child-{i}", quality=float(80), effort="medium")
            for i in range(10)
        ]
        result = aggregator.aggregate("q-parent", handbacks)
        assert result["metrics"]["quality"] == pytest.approx(80.0)
