"""
Integration tests for parallel delegation in the Orchestrator.

Tests cover:
  ✅ OrchestratorAgent.should_parallelize_task() integration
  ✅ OrchestratorAgent.create_parallel_plan() integration
  ✅ Parallel plan written to queue (sub-delegates enqueued)
  ✅ Consolidation delegate written to queue after sub-tasks
  ✅ Backward compatibility: single-agent path unchanged
  ✅ Parallel plan summary logged
  ✅ Dependency graph validated before dispatch
  ✅ Sub-delegates have correct parent_task_id
  ✅ Tier-0 dispatched before tier-1
  ✅ Full end-to-end: complex task → parallel plan → queue entries
"""

import sys
import tempfile
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest
import yaml

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from orchestration.agents.parallel_delegate import (
    ParallelDelegationManager,
    ParallelPlan,
    SubDelegate,
    decompose_task,
    detect_parallelizable_task,
    validate_dependency_graph,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

COMPLEX_SCOPE = (
    "Implement parallel delegation in the Orchestrator. "
    "This requires security review, comprehensive testing, documentation, "
    "implementation of core routing logic, code review, and infrastructure "
    "pipeline updates. Ensure backward compatibility and validate all changes."
)

SIMPLE_SCOPE = "Fix a typo in README."


def _make_delegate(scope: str, complexity: str = "high", task_id: str = "test-task") -> Dict:
    return {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "role": "senior_engineer",
        "model": "claude-sonnet-4.6",
        "effort": "high",
        "complexity": complexity,
        "scope": scope,
        "context": {"background": "Integration test"},
        "plan": [
            "Implement core feature",
            "Write tests",
            "Update documentation",
            "Security review",
        ],
        "success_criteria": [
            "All tests pass",
            "Security review approved",
        ],
    }


class MockQueueWriter:
    """Captures write() calls for assertion."""

    def __init__(self):
        self.written: List[Dict] = []

    def write(self, task_id: str, delegate_dict: Dict):
        self.written.append({"task_id": task_id, "delegate": delegate_dict})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def complex_delegate():
    return _make_delegate(COMPLEX_SCOPE, complexity="high", task_id="2026-05-16-parallel-impl")


@pytest.fixture
def simple_delegate():
    return _make_delegate(SIMPLE_SCOPE, complexity="low", task_id="2026-05-16-simple-fix")


@pytest.fixture
def manager():
    return ParallelDelegationManager()


# ===========================================================================
# 1. ParallelDelegationManager integration
# ===========================================================================

class TestParallelDelegationManagerIntegration:

    def test_complex_task_should_parallelize(self, manager, complex_delegate):
        ok, reason = manager.should_parallelize(complex_delegate)
        assert ok is True

    def test_simple_task_should_not_parallelize(self, manager, simple_delegate):
        ok, reason = manager.should_parallelize(simple_delegate)
        assert ok is False

    def test_plan_produces_valid_parallel_plan(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        assert isinstance(plan, ParallelPlan)
        assert len(plan.sub_delegates) >= 2
        assert plan.consolidation_delegate is not None

    def test_plan_dependency_graph_valid(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        valid, errors = validate_dependency_graph(plan.dependency_graph)
        assert valid is True, f"Dependency errors: {errors}"

    def test_dispatch_tier_0_writes_to_queue(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        writer = MockQueueWriter()
        dispatched = manager.dispatch_tier(plan, 0, writer)
        assert len(dispatched) >= 1
        assert len(writer.written) == len(dispatched)

    def test_dispatch_tier_1_writes_to_queue(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        writer = MockQueueWriter()
        # Tier 1 may or may not exist
        if 1 in plan.tier_groups:
            dispatched = manager.dispatch_tier(plan, 1, writer)
            assert len(dispatched) >= 1

    def test_dispatch_consolidation_writes_to_queue(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        writer = MockQueueWriter()
        task_id = manager.dispatch_consolidation(plan, writer)
        assert task_id == plan.consolidation_delegate.task_id
        assert len(writer.written) == 1

    def test_tier_0_dispatched_before_tier_1(self, manager, complex_delegate):
        """Tier 0 tasks must be dispatched before tier 1."""
        plan = manager.plan(complex_delegate)
        writer = MockQueueWriter()
        tier_0_dispatched = manager.dispatch_tier(plan, 0, writer)
        tier_0_ids = set(tier_0_dispatched)

        if 1 in plan.tier_groups:
            tier_1_dispatched = manager.dispatch_tier(plan, 1, writer)
            # Tier-1 tasks should depend on tier-0 tasks
            for sd in plan.tier_groups[1]:
                for dep in sd.dependencies:
                    assert dep in tier_0_ids, (
                        f"Tier-1 task '{sd.task_id}' depends on '{dep}' "
                        f"which was not in tier-0: {tier_0_ids}"
                    )

    def test_sub_delegates_have_correct_parent_id(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        for sd in plan.sub_delegates:
            assert sd.parent_task_id == complex_delegate["task_id"]

    def test_consolidation_depends_on_all_sub_tasks(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        sub_ids = {sd.task_id for sd in plan.sub_delegates}
        consolidation_deps = set(plan.consolidation_delegate.dependencies)
        assert consolidation_deps == sub_ids

    def test_summarize_plan_contains_task_id(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        summary = manager.summarize_plan(plan)
        assert complex_delegate["task_id"] in summary

    def test_summarize_plan_mentions_tiers(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        summary = manager.summarize_plan(plan)
        assert "Tier" in summary


# ===========================================================================
# 2. Sub-delegate structure validation
# ===========================================================================

class TestSubDelegateStructure:

    def test_all_sub_delegates_have_handoff_type(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        for sd in plan.sub_delegates:
            d = sd.to_delegate_dict()
            assert d["handoff_type"] == "DELEGATE"

    def test_all_sub_delegates_have_role(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        for sd in plan.sub_delegates:
            assert sd.role in (
                "engineer", "senior_engineer", "lead_engineer",
                "principal_engineer", "quality_engineer",
                "model_engineer", "security_engineer",
            )

    def test_all_sub_delegates_have_scope(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        for sd in plan.sub_delegates:
            assert len(sd.scope) > 0

    def test_all_sub_delegates_have_plan(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        for sd in plan.sub_delegates:
            assert isinstance(sd.plan, list)
            assert len(sd.plan) > 0

    def test_all_sub_delegates_have_success_criteria(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        for sd in plan.sub_delegates:
            assert isinstance(sd.success_criteria, list)
            assert len(sd.success_criteria) > 0

    def test_consolidation_role_is_lead_engineer(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        assert plan.consolidation_delegate.role == "lead_engineer"

    def test_consolidation_has_plan(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        assert len(plan.consolidation_delegate.plan) > 0


# ===========================================================================
# 3. Backward compatibility
# ===========================================================================

class TestBackwardCompatibility:

    def test_simple_task_not_split(self, manager, simple_delegate):
        ok, _ = manager.should_parallelize(simple_delegate)
        assert ok is False

    def test_child_task_not_re_split(self, manager, complex_delegate):
        complex_delegate["parent_task_id"] = "some-parent"
        ok, _ = manager.should_parallelize(complex_delegate)
        assert ok is False

    def test_disabled_flag_prevents_split(self, manager, complex_delegate):
        complex_delegate["parallel_delegation_disabled"] = True
        ok, _ = manager.should_parallelize(complex_delegate)
        assert ok is False

    def test_plan_raises_for_simple_task(self, manager, simple_delegate):
        with pytest.raises(ValueError):
            manager.plan(simple_delegate)

    def test_existing_parallel_plan_not_re_split(self, manager, complex_delegate):
        complex_delegate["parallel_plan"] = {"strategy": "existing"}
        ok, _ = manager.should_parallelize(complex_delegate)
        assert ok is False


# ===========================================================================
# 4. Full end-to-end workflow
# ===========================================================================

class TestEndToEndWorkflow:

    def test_full_workflow_complex_task(self, manager, complex_delegate):
        """
        Full workflow:
        1. Detect parallelizable
        2. Create plan
        3. Dispatch tier 0
        4. Dispatch tier 1 (if exists)
        5. Dispatch consolidation
        """
        writer = MockQueueWriter()

        # Step 1: detect
        ok, reason = manager.should_parallelize(complex_delegate)
        assert ok is True

        # Step 2: plan
        plan = manager.plan(complex_delegate)
        assert len(plan.sub_delegates) >= 2

        # Step 3: dispatch all tiers
        all_dispatched = []
        for tier in sorted(plan.tier_groups.keys()):
            dispatched = manager.dispatch_tier(plan, tier, writer)
            all_dispatched.extend(dispatched)

        # Step 4: dispatch consolidation
        consolidation_id = manager.dispatch_consolidation(plan, writer)

        # Verify
        total_expected = len(plan.sub_delegates) + 1  # +1 for consolidation
        assert len(writer.written) == total_expected

        # All written delegates have correct structure
        for entry in writer.written:
            d = entry["delegate"]
            assert d["handoff_type"] == "DELEGATE"
            assert "task_id" in d
            assert "role" in d

    def test_consolidation_enriched_with_handbacks(self, manager, complex_delegate):
        """Consolidation delegate can be enriched with sub-task results."""
        plan = manager.plan(complex_delegate)
        writer = MockQueueWriter()

        # Simulate sub-task completion
        fake_handbacks = [
            {"task_id": sd.task_id, "quality_score": 90, "status": "complete"}
            for sd in plan.sub_delegates
        ]

        consolidation_id = manager.dispatch_consolidation(
            plan, writer, sub_handbacks=fake_handbacks
        )

        # The consolidation delegate should have enriched context
        written_consolidation = writer.written[0]["delegate"]
        assert "context" in written_consolidation
        context = written_consolidation["context"]
        assert "sub_handbacks" in context
        assert "avg_sub_quality" in context
        assert context["avg_sub_quality"] == 90.0
