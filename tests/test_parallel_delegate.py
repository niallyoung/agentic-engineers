"""
Unit tests for parallel_delegate.py

Coverage targets:
  ✅ detect_parallelizable_task - positive and negative cases
  ✅ _detect_domains - keyword matching
  ✅ decompose_task - domain splitting, tier assignment, dependency wiring
  ✅ route_sub_delegates - role routing per domain
  ✅ create_consolidation_delegate - consolidation creation and enrichment
  ✅ validate_dependency_graph - cycle detection, missing nodes
  ✅ ParallelDelegationManager - end-to-end workflow
  ✅ SubDelegate.to_delegate_dict - serialisation
  ✅ ParallelPlan.tier_groups - tier grouping
  ✅ load_decomposition_config - config loading
  ✅ Backward compatibility - non-parallelizable tasks pass through unchanged
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
AGENTS_ROOT = REPO_ROOT / "src" / "orchestration" / "agents"
if str(AGENTS_ROOT.parent.parent) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from orchestration.agents.parallel_delegate import (
    DEFAULT_DECOMPOSITION_RULES,
    ParallelDelegationManager,
    ParallelPlan,
    SubDelegate,
    _detect_domains,
    _extract_domain_criteria,
    _extract_domain_plan,
    _infer_strategy,
    create_consolidation_delegate,
    decompose_task,
    detect_parallelizable_task,
    load_decomposition_config,
    route_sub_delegates,
    validate_dependency_graph,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

COMPLEX_SCOPE = (
    "Implement parallel delegation in the Orchestrator. "
    "This requires security review, comprehensive testing, documentation, "
    "implementation of core routing logic, code review, and infrastructure "
    "pipeline updates. Ensure backward compatibility and validate all changes."
)

SIMPLE_SCOPE = "Fix a typo in README."


@pytest.fixture
def complex_delegate():
    return {
        "handoff_type": "DELEGATE",
        "task_id": "2026-05-16-parallel-impl",
        "role": "senior_engineer",
        "model": "claude-sonnet-4.6",
        "effort": "high",
        "complexity": "high",
        "scope": COMPLEX_SCOPE,
        "context": {"background": "Need parallel delegation for efficiency"},
        "plan": [
            "Implement core routing logic",
            "Write unit tests and integration tests",
            "Update documentation",
            "Security review of new code",
        ],
        "success_criteria": [
            "All tests pass",
            "Security review approved",
            "Documentation complete",
        ],
    }


@pytest.fixture
def simple_delegate():
    return {
        "handoff_type": "DELEGATE",
        "task_id": "2026-05-16-simple-fix",
        "role": "engineer",
        "model": "claude-haiku-4.5",
        "effort": "low",
        "complexity": "low",
        "scope": SIMPLE_SCOPE,
        "plan": ["Fix typo"],
        "success_criteria": ["Typo fixed"],
    }


@pytest.fixture
def manager():
    return ParallelDelegationManager()


# ===========================================================================
# 1. detect_parallelizable_task
# ===========================================================================

class TestDetectParallelizableTask:

    def test_complex_high_complexity_is_parallelizable(self, complex_delegate):
        ok, reason = detect_parallelizable_task(complex_delegate)
        assert ok is True
        assert "domain" in reason.lower() or "parallel" in reason.lower()

    def test_simple_low_complexity_not_parallelizable(self, simple_delegate):
        ok, reason = detect_parallelizable_task(simple_delegate)
        assert ok is False

    def test_child_task_not_parallelizable(self, complex_delegate):
        complex_delegate["parent_task_id"] = "some-parent"
        ok, reason = detect_parallelizable_task(complex_delegate)
        assert ok is False
        assert "sub-task" in reason.lower() or "parent" in reason.lower()

    def test_explicit_disable_flag(self, complex_delegate):
        complex_delegate["parallel_delegation_disabled"] = True
        ok, reason = detect_parallelizable_task(complex_delegate)
        assert ok is False
        assert "disabled" in reason.lower()

    def test_already_has_parallel_plan(self, complex_delegate):
        complex_delegate["parallel_plan"] = {"strategy": "existing"}
        ok, reason = detect_parallelizable_task(complex_delegate)
        assert ok is False

    def test_below_domain_threshold(self):
        delegate = {
            "task_id": "t1",
            "complexity": "high",
            "scope": "Implement a simple feature with some testing",
            "plan": [],
        }
        ok, reason = detect_parallelizable_task(delegate)
        # Only 2 domains (implementation + testing) — below threshold of 3
        assert ok is False

    def test_long_scope_triggers_split_regardless_of_complexity(self):
        # Many words + many domains → should parallelize even with medium complexity
        scope = (
            "We need to implement the new API endpoint with database schema migration, "
            "comprehensive testing coverage, security review, documentation updates, "
            "infrastructure pipeline changes, and code review validation process. "
            "This is a medium complexity task but has many domains."
        )
        delegate = {
            "task_id": "t2",
            "complexity": "medium",
            "scope": scope,
            "plan": [],
        }
        ok, _ = detect_parallelizable_task(delegate)
        assert ok is True

    def test_custom_config_threshold(self, complex_delegate):
        config = dict(DEFAULT_DECOMPOSITION_RULES)
        config["parallelism_threshold"] = 99  # impossibly high
        ok, reason = detect_parallelizable_task(complex_delegate, config)
        assert ok is False

    def test_returns_reason_string(self, complex_delegate):
        ok, reason = detect_parallelizable_task(complex_delegate)
        assert isinstance(reason, str)
        assert len(reason) > 0


# ===========================================================================
# 2. _detect_domains
# ===========================================================================

class TestDetectDomains:

    def test_detects_security_keyword(self):
        domains = _detect_domains("We need a security review", DEFAULT_DECOMPOSITION_RULES["domain_keywords"])
        assert "security" in domains

    def test_detects_testing_keyword(self):
        domains = _detect_domains("Write unit tests and integration tests", DEFAULT_DECOMPOSITION_RULES["domain_keywords"])
        assert "testing" in domains

    def test_detects_multiple_domains(self):
        text = "implement feature with tests and documentation and security review"
        domains = _detect_domains(text, DEFAULT_DECOMPOSITION_RULES["domain_keywords"])
        assert len(domains) >= 3

    def test_case_insensitive(self):
        domains = _detect_domains("SECURITY REVIEW NEEDED", DEFAULT_DECOMPOSITION_RULES["domain_keywords"])
        assert "security" in domains

    def test_empty_text_returns_empty(self):
        domains = _detect_domains("", DEFAULT_DECOMPOSITION_RULES["domain_keywords"])
        assert len(domains) == 0

    def test_no_match_returns_empty(self):
        domains = _detect_domains("hello world foo bar", DEFAULT_DECOMPOSITION_RULES["domain_keywords"])
        assert len(domains) == 0


# ===========================================================================
# 3. decompose_task
# ===========================================================================

class TestDecomposeTask:

    def test_returns_parallel_plan(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        assert isinstance(plan, ParallelPlan)

    def test_plan_has_sub_delegates(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        assert len(plan.sub_delegates) >= 2

    def test_plan_has_consolidation(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        assert plan.consolidation_delegate is not None

    def test_sub_delegates_have_parent_id(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        for sd in plan.sub_delegates:
            assert sd.parent_task_id == complex_delegate["task_id"]

    def test_consolidation_has_parent_id(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        assert plan.consolidation_delegate.parent_task_id == complex_delegate["task_id"]

    def test_tier_assignment(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        tiers = {sd.execution_tier for sd in plan.sub_delegates}
        # Should have at least tier 0
        assert 0 in tiers

    def test_depends_on_implementation_get_tier_1(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        for sd in plan.sub_delegates:
            domain = sd.context.get("domain", "")
            if domain in DEFAULT_DECOMPOSITION_RULES["depends_on_implementation"]:
                assert sd.execution_tier == 1

    def test_dependency_graph_populated(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        assert isinstance(plan.dependency_graph, dict)
        assert len(plan.dependency_graph) > 0

    def test_consolidation_depends_on_all_sub_tasks(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        consolidation_deps = set(plan.consolidation_delegate.dependencies)
        sub_ids = {sd.task_id for sd in plan.sub_delegates}
        assert consolidation_deps == sub_ids

    def test_estimated_parallelism_positive(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        assert plan.estimated_parallelism >= 1

    def test_strategy_is_string(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        assert isinstance(plan.strategy, str)
        assert len(plan.strategy) > 0

    def test_rationale_is_string(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        assert isinstance(plan.rationale, str)

    def test_max_sub_tasks_respected(self, complex_delegate):
        config = dict(DEFAULT_DECOMPOSITION_RULES)
        config["max_sub_tasks"] = 2
        plan = decompose_task(complex_delegate, config)
        assert len(plan.sub_delegates) <= 2

    def test_sub_delegate_ids_unique(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        ids = [sd.task_id for sd in plan.sub_delegates]
        assert len(ids) == len(set(ids))


# ===========================================================================
# 4. SubDelegate.to_delegate_dict
# ===========================================================================

class TestSubDelegateToDict:

    def test_to_dict_has_required_fields(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        d = plan.sub_delegates[0].to_delegate_dict()
        for field in ("handoff_type", "task_id", "parent_task_id", "role", "model",
                      "effort", "scope", "plan", "success_criteria", "dependencies"):
            assert field in d, f"Missing field: {field}"

    def test_handoff_type_is_delegate(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        d = plan.sub_delegates[0].to_delegate_dict()
        assert d["handoff_type"] == "DELEGATE"

    def test_execution_tier_in_dict(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        d = plan.sub_delegates[0].to_delegate_dict()
        assert "execution_tier" in d


# ===========================================================================
# 5. ParallelPlan.tier_groups
# ===========================================================================

class TestParallelPlanTierGroups:

    def test_tier_groups_returns_dict(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        groups = plan.tier_groups
        assert isinstance(groups, dict)

    def test_tier_groups_sorted(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        keys = list(plan.tier_groups.keys())
        assert keys == sorted(keys)

    def test_tier_0_exists(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        assert 0 in plan.tier_groups


# ===========================================================================
# 6. route_sub_delegates
# ===========================================================================

class TestRouteSubDelegates:

    def test_security_domain_routes_to_security_engineer(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        routed = route_sub_delegates(plan)
        security_sds = [sd for sd in routed if sd.context.get("domain") == "security"]
        for sd in security_sds:
            assert sd.role == "security_engineer"

    def test_review_domain_routes_to_quality_engineer(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        routed = route_sub_delegates(plan)
        review_sds = [sd for sd in routed if sd.context.get("domain") == "review"]
        for sd in review_sds:
            assert sd.role == "quality_engineer"

    def test_returns_list_of_sub_delegates(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        routed = route_sub_delegates(plan)
        assert isinstance(routed, list)
        assert all(isinstance(sd, SubDelegate) for sd in routed)


# ===========================================================================
# 7. create_consolidation_delegate
# ===========================================================================

class TestCreateConsolidationDelegate:

    def test_returns_sub_delegate(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        consolidation = create_consolidation_delegate(plan)
        assert isinstance(consolidation, SubDelegate)

    def test_consolidation_role_is_lead_engineer(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        consolidation = create_consolidation_delegate(plan)
        assert consolidation.role == "lead_engineer"

    def test_enriched_with_handbacks(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        handbacks = [
            {"task_id": "t1", "quality_score": 90, "status": "success"},
            {"task_id": "t2", "quality_score": 85, "status": "success"},
        ]
        consolidation = create_consolidation_delegate(plan, handbacks)
        assert "sub_handbacks" in consolidation.context
        assert "avg_sub_quality" in consolidation.context

    def test_avg_quality_computed_correctly(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        handbacks = [
            {"task_id": "t1", "quality_score": 80},
            {"task_id": "t2", "quality_score": 100},
        ]
        consolidation = create_consolidation_delegate(plan, handbacks)
        assert consolidation.context["avg_sub_quality"] == 90.0

    def test_raises_if_no_consolidation(self):
        plan = ParallelPlan(
            parent_task_id="p1",
            strategy="test",
            sub_delegates=[],
            consolidation_delegate=None,
            estimated_parallelism=0,
            dependency_graph={},
            rationale="test",
        )
        with pytest.raises(ValueError, match="no consolidation_delegate"):
            create_consolidation_delegate(plan)


# ===========================================================================
# 8. validate_dependency_graph
# ===========================================================================

class TestValidateDependencyGraph:

    def test_valid_linear_graph(self):
        graph = {"a": [], "b": ["a"], "c": ["b"]}
        valid, errors = validate_dependency_graph(graph)
        assert valid is True
        assert errors == []

    def test_valid_parallel_graph(self):
        graph = {"a": [], "b": [], "c": ["a", "b"]}
        valid, errors = validate_dependency_graph(graph)
        assert valid is True

    def test_cycle_detected(self):
        graph = {"a": ["b"], "b": ["a"]}
        valid, errors = validate_dependency_graph(graph)
        assert valid is False
        assert any("cycle" in e.lower() for e in errors)

    def test_missing_dependency_node(self):
        graph = {"a": ["nonexistent"]}
        valid, errors = validate_dependency_graph(graph)
        assert valid is False
        assert any("unknown" in e.lower() for e in errors)

    def test_empty_graph_is_valid(self):
        valid, errors = validate_dependency_graph({})
        assert valid is True

    def test_self_loop_detected(self):
        graph = {"a": ["a"]}
        valid, errors = validate_dependency_graph(graph)
        assert valid is False

    def test_complex_valid_graph(self, complex_delegate):
        plan = decompose_task(complex_delegate)
        valid, errors = validate_dependency_graph(plan.dependency_graph)
        assert valid is True, f"Errors: {errors}"


# ===========================================================================
# 9. load_decomposition_config
# ===========================================================================

class TestLoadDecompositionConfig:

    def test_returns_defaults_when_no_path(self):
        config = load_decomposition_config()
        assert "domain_keywords" in config
        assert "role_routing" in config

    def test_loads_yaml_file(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("min_sub_tasks: 5\n")
        config = load_decomposition_config(str(config_file))
        assert config["min_sub_tasks"] == 5

    def test_merges_with_defaults(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("min_sub_tasks: 5\n")
        config = load_decomposition_config(str(config_file))
        # Should still have defaults for other keys
        assert "domain_keywords" in config

    def test_falls_back_on_invalid_path(self):
        config = load_decomposition_config("/nonexistent/path.yaml")
        assert config == DEFAULT_DECOMPOSITION_RULES

    def test_falls_back_on_invalid_yaml(self, tmp_path):
        config_file = tmp_path / "bad.yaml"
        config_file.write_text(": invalid: yaml: [\n")
        config = load_decomposition_config(str(config_file))
        assert config == DEFAULT_DECOMPOSITION_RULES


# ===========================================================================
# 10. ParallelDelegationManager
# ===========================================================================

class TestParallelDelegationManager:

    def test_should_parallelize_complex(self, manager, complex_delegate):
        ok, _ = manager.should_parallelize(complex_delegate)
        assert ok is True

    def test_should_not_parallelize_simple(self, manager, simple_delegate):
        ok, _ = manager.should_parallelize(simple_delegate)
        assert ok is False

    def test_plan_returns_parallel_plan(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        assert isinstance(plan, ParallelPlan)

    def test_plan_raises_for_non_parallelizable(self, manager, simple_delegate):
        with pytest.raises(ValueError):
            manager.plan(simple_delegate)

    def test_dispatch_tier_calls_queue_writer(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        mock_writer = MagicMock()
        dispatched = manager.dispatch_tier(plan, 0, mock_writer)
        assert len(dispatched) >= 1
        assert mock_writer.write.call_count == len(dispatched)

    def test_dispatch_consolidation_calls_queue_writer(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        mock_writer = MagicMock()
        task_id = manager.dispatch_consolidation(plan, mock_writer)
        assert task_id == plan.consolidation_delegate.task_id
        mock_writer.write.assert_called_once()

    def test_summarize_plan_returns_string(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        summary = manager.summarize_plan(plan)
        assert isinstance(summary, str)
        assert "Parallel Plan" in summary

    def test_plan_dependency_graph_valid(self, manager, complex_delegate):
        plan = manager.plan(complex_delegate)
        valid, errors = validate_dependency_graph(plan.dependency_graph)
        assert valid is True, f"Errors: {errors}"

    def test_custom_config_path(self, tmp_path, complex_delegate):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("parallelism_threshold: 1\n")
        mgr = ParallelDelegationManager(config_path=str(config_file))
        ok, _ = mgr.should_parallelize(complex_delegate)
        assert ok is True

    def test_backward_compat_simple_task(self, manager, simple_delegate):
        """Simple tasks must not be split — backward compatibility."""
        ok, reason = manager.should_parallelize(simple_delegate)
        assert ok is False
        # Ensure no exception raised
        assert isinstance(reason, str)


# ===========================================================================
# 11. _infer_strategy
# ===========================================================================

class TestInferStrategy:

    def test_security_and_testing(self):
        assert _infer_strategy(["security", "testing"]) == "security_and_quality_split"

    def test_impl_and_testing(self):
        assert _infer_strategy(["implementation", "testing"]) == "impl_test_split"

    def test_many_domains(self):
        assert _infer_strategy(["a", "b", "c", "d"]) == "domain_split"

    def test_two_domains(self):
        assert _infer_strategy(["a", "b"]) == "dual_domain_split"

    def test_three_domains(self):
        assert _infer_strategy(["a", "b", "c"]) == "multi_domain_split"


# ===========================================================================
# 12. _extract_domain_plan / _extract_domain_criteria
# ===========================================================================

class TestExtractHelpers:

    def test_extract_plan_filters_relevant_steps(self):
        original = ["Implement feature", "Write security tests", "Update docs"]
        result = _extract_domain_plan("security", original, "scope")
        assert any("security" in s.lower() for s in result)

    def test_extract_plan_generates_default_when_no_match(self):
        result = _extract_domain_plan("security", [], "my scope")
        assert len(result) > 0

    def test_extract_criteria_filters_relevant(self):
        original = ["All tests pass", "Security review approved", "Docs complete"]
        result = _extract_domain_criteria("security", original)
        assert any("security" in c.lower() for c in result)

    def test_extract_criteria_generates_default(self):
        result = _extract_domain_criteria("security", [])
        assert len(result) > 0


# ===========================================================================
# 13. Integration: full harness consistency task example
# ===========================================================================

class TestHarnessConsistencyExample:
    """
    Validates the example from the task description:
    'Harness consistency task automatically splits into 6 DELEGATEs'
    """

    HARNESS_SCOPE = (
        "Ensure harness consistency across all agent implementations. "
        "This requires: security review of agent harness, comprehensive testing "
        "of all agents, documentation updates, implementation of missing harness "
        "features, code review of existing harness, and infrastructure pipeline "
        "validation. All agents must pass quality gates."
    )

    def test_harness_task_is_parallelizable(self):
        delegate = {
            "task_id": "2026-05-16-harness-consistency",
            "complexity": "high",
            "scope": self.HARNESS_SCOPE,
            "plan": [],
            "success_criteria": [],
        }
        ok, reason = detect_parallelizable_task(delegate)
        assert ok is True

    def test_harness_task_produces_multiple_sub_delegates(self):
        delegate = {
            "task_id": "2026-05-16-harness-consistency",
            "complexity": "high",
            "scope": self.HARNESS_SCOPE,
            "plan": [],
            "success_criteria": [],
        }
        plan = decompose_task(delegate)
        # Should produce at least 4 sub-tasks (security, testing, docs, impl, review, infra)
        assert len(plan.sub_delegates) >= 4

    def test_harness_task_has_consolidation(self):
        delegate = {
            "task_id": "2026-05-16-harness-consistency",
            "complexity": "high",
            "scope": self.HARNESS_SCOPE,
            "plan": [],
            "success_criteria": [],
        }
        plan = decompose_task(delegate)
        assert plan.consolidation_delegate is not None
        assert plan.consolidation_delegate.role == "lead_engineer"

    def test_harness_task_dependency_graph_valid(self):
        delegate = {
            "task_id": "2026-05-16-harness-consistency",
            "complexity": "high",
            "scope": self.HARNESS_SCOPE,
            "plan": [],
            "success_criteria": [],
        }
        plan = decompose_task(delegate)
        valid, errors = validate_dependency_graph(plan.dependency_graph)
        assert valid is True, f"Errors: {errors}"
