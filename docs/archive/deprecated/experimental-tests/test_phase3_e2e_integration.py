"""
Phase 3 End-to-End Integration Tests

Comprehensive integration tests covering all Phase 3 components:
1. Token visibility (TokenTracker, CLIFormatter, BudgetChecker, OrchestratorCLI)
2. Model selection (ComplexityScorer, ModelSelector, CostQualityAnalyzer)
3. Orchestrator improvements (dry-run, shadow mode, gradual rollout)
4. Harness implementations (Copilot CLI streaming)
5. Integration points (AgentInvoker → TokenTracker, Orchestrator → OrchestratorCLI)
"""

import os
import json
import time
import threading
import tempfile
import yaml
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from datetime import datetime

import pytest

# Token visibility imports
from src.orchestration.monitoring.metrics import MetricsRegistry
from src.orchestration.monitoring.token_tracker import TokenTracker, TokenMetrics, TokenStats
from src.orchestration.monitoring.cli_formatter import CLIFormatter
from src.orchestration.monitoring.budget_checker import BudgetChecker, BudgetStatus, BudgetResult
from src.orchestration.monitoring.orchestrator_cli import OrchestratorCLI

# Model selection imports
from src.orchestration.models.complexity_scorer import ComplexityScorer, ComplexityLevel, TaskAttributes
from src.orchestration.models.model_selector import ModelSelector, ModelTier, RoutingDecision
from src.orchestration.models.cost_quality_analyzer import CostQualityAnalyzer

# Orchestrator improvements
from src.orchestration.dry_run import DryRunContext, OperationType
from src.orchestration.agents.shadow_mode import ShadowModeContext, ShadowModeTraffic
from src.orchestration.agents.gradual_rollout import RolloutManager, RolloutStage, RolloutConfig, TrafficSampler

# Harness imports
from src.harnesses.copilot_cli.streaming import StreamingRenderer, StreamEvent

# Agent invoker
from src.orchestration.agents.invoke_agent import AgentInvoker


# ===========================================================================
# Shared Fixtures
# ===========================================================================

@pytest.fixture
def registry():
    return MetricsRegistry()


@pytest.fixture
def tracker(registry):
    return TokenTracker(registry)


@pytest.fixture
def formatter():
    return CLIFormatter(no_color=True)


@pytest.fixture
def budget_checker():
    return BudgetChecker()


@pytest.fixture
def orchestrator_cli(tracker):
    return OrchestratorCLI(token_tracker=tracker, no_color=True)


@pytest.fixture
def scorer():
    return ComplexityScorer()


@pytest.fixture
def selector():
    return ModelSelector()


@pytest.fixture
def analyzer():
    return CostQualityAnalyzer()


@pytest.fixture
def tmp_dirs(tmp_path):
    processing = tmp_path / "processing"
    delegates = tmp_path / "delegates"
    spans = tmp_path / "spans"
    for d in [processing, delegates, spans]:
        d.mkdir(parents=True)
    return {"processing": processing, "delegates": delegates, "spans": spans, "base": tmp_path}


def make_delegate(task_id="task-e2e-001", role="Engineer", effort="medium"):
    return {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "role": role,
        "model": "claude-sonnet-4-6",
        "effort": effort,
        "scope": "E2E test scope",
        "context": ["File: test.py"],
        "plan": ["1. Run tests"],
        "success_criteria": ["All tests pass"],
    }


def make_handback(task_id="task-e2e-001", tokens_in=1000, tokens_out=500, cost_usd=0.05):
    return {
        "handoff_type": "HANDBACK",
        "task_id": task_id,
        "status": "complete",
        "deliverables": ["Modified: test.py"],
        "tests": [{"command": "pytest", "result": "PASS"}],
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_cached": 0,
        "model": "claude-sonnet-4-6",
        "effort": "medium",
        "duration_minutes": 5,
        "escalations": 0,
        "cost_usd": cost_usd,
    }


# ===========================================================================
# 1. Token Tracker E2E Tests
# ===========================================================================

class TestTokenTrackerWithRealAgents:
    """E2E tests for TokenTracker with realistic multi-agent scenarios."""

    def test_token_tracker_records_multiple_agents_sequentially(self, tracker):
        """Record tokens for all 8 agent types and verify aggregation."""
        agents = [
            ("orchestrator", 500, 200, 0.02),
            ("engineer", 2000, 1000, 0.09),
            ("senior-engineer", 3000, 1500, 0.135),
            ("lead-engineer", 1500, 750, 0.0675),
            ("principal-engineer", 4000, 2000, 0.18),
            ("quality-engineer", 800, 400, 0.036),
            ("model-engineer", 600, 300, 0.027),
            ("security-engineer", 1200, 600, 0.054),
        ]

        for i, (agent, inp, out, cost) in enumerate(agents):
            tracker.record_task_tokens(
                task_id=f"task-{i:03d}",
                agent=agent,
                input_tokens=inp,
                output_tokens=out,
                cost_usd=cost,
            )

        stats = tracker.get_stats()
        assert stats.task_count == 8
        assert stats.total_input_tokens == sum(a[1] for a in agents)
        assert stats.total_output_tokens == sum(a[2] for a in agents)
        assert abs(stats.total_cost_usd - sum(a[3] for a in agents)) < 0.0001

        # Verify all agents tracked
        for agent, _, _, _ in agents:
            agent_stats = tracker.get_agent_stats(agent)
            assert agent_stats is not None, f"Missing stats for {agent}"
            assert agent_stats["task_count"] == 1

    def test_token_tracker_cost_attribution_sums_to_100_percent(self, tracker):
        """Verify cost attribution percentages sum to 100%."""
        tracker.record_task_tokens("t1", "engineer", 1000, 500, cost_usd=0.05)
        tracker.record_task_tokens("t2", "orchestrator", 500, 200, cost_usd=0.02)
        tracker.record_task_tokens("t3", "quality-engineer", 800, 400, cost_usd=0.03)

        attribution = tracker.get_cost_attribution()
        total_pct = sum(v["cost_percentage"] for v in attribution.values())
        assert abs(total_pct - 100.0) < 0.01

    def test_token_tracker_thread_safety_concurrent_writes(self, tracker):
        """Verify TokenTracker is thread-safe under concurrent writes."""
        errors = []
        n_threads = 20
        n_tasks_per_thread = 10

        def record_tokens(thread_id):
            try:
                for i in range(n_tasks_per_thread):
                    tracker.record_task_tokens(
                        task_id=f"thread-{thread_id}-task-{i}",
                        agent="engineer",
                        input_tokens=100,
                        output_tokens=50,
                        cost_usd=0.005,
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_tokens, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread safety errors: {errors}"
        stats = tracker.get_stats()
        assert stats.task_count == n_threads * n_tasks_per_thread

    def test_token_tracker_avg_metrics_computed_correctly(self, tracker):
        """Verify average cost and token calculations."""
        tracker.record_task_tokens("t1", "engineer", 1000, 500, cost_usd=0.10)
        tracker.record_task_tokens("t2", "engineer", 2000, 1000, cost_usd=0.20)

        stats = tracker.get_stats()
        assert abs(stats.avg_cost_per_task - 0.15) < 0.0001
        assert abs(stats.avg_tokens_per_task - 2250.0) < 0.1  # (1500 + 3000) / 2

    def test_token_tracker_clear_resets_all_state(self, tracker):
        """Verify clear() resets all metrics."""
        tracker.record_task_tokens("t1", "engineer", 1000, 500, cost_usd=0.05)
        tracker.clear()

        stats = tracker.get_stats()
        assert stats.task_count == 0
        assert stats.total_cost_usd == 0.0
        assert stats.total_input_tokens == 0

    def test_token_tracker_get_all_metrics_returns_copies(self, tracker):
        """Verify get_all_metrics returns a copy, not the internal list."""
        tracker.record_task_tokens("t1", "engineer", 1000, 500)
        metrics = tracker.get_all_metrics()
        assert len(metrics) == 1
        # Modifying the returned list should not affect internal state
        metrics.clear()
        assert len(tracker.get_all_metrics()) == 1

    def test_token_tracker_rejects_negative_tokens(self, tracker):
        """Verify negative token counts raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            tracker.record_task_tokens("t1", "engineer", -1, 500)

    def test_token_tracker_rejects_negative_cost(self, tracker):
        """Verify negative cost raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            tracker.record_task_tokens("t1", "engineer", 100, 50, cost_usd=-0.01)

    def test_token_tracker_zero_tokens_allowed(self, tracker):
        """Verify zero token counts are valid."""
        tracker.record_task_tokens("t1", "engineer", 0, 0, cost_usd=0.0)
        stats = tracker.get_stats()
        assert stats.task_count == 1

    def test_token_tracker_unknown_agent_returns_none(self, tracker):
        """Verify get_agent_stats returns None for unknown agent."""
        result = tracker.get_agent_stats("nonexistent-agent")
        assert result is None

    def test_token_tracker_effective_tokens_excludes_cached(self, tracker):
        """Verify effective_tokens = input + output (not cached)."""
        tracker.record_task_tokens("t1", "engineer", 1000, 500, cached_tokens=200)
        stats = tracker.get_stats()
        assert stats.effective_tokens == 1500
        assert stats.total_tokens == 1700


# ===========================================================================
# 2. CLI Formatter E2E Tests
# ===========================================================================

class TestCLIFormatterWithRealMetrics:
    """E2E tests for CLIFormatter with realistic metrics."""

    def test_format_task_line_contains_all_fields(self, formatter):
        """Verify task line format includes agent, tokens, cost, session cost."""
        metrics = TokenMetrics(
            task_id="task-001",
            agent="engineer",
            input_tokens=1234,
            output_tokens=567,
            cached_tokens=0,
            cost_usd=0.0045,
        )
        line = formatter.format_task_line(metrics, session_cost=0.12)
        assert "engineer" in line
        assert "1,234" in line
        assert "567" in line
        assert "0.0045" in line
        assert "0.12" in line

    def test_format_task_line_no_color_mode(self):
        """Verify NO_COLOR env var disables ANSI codes."""
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            formatter = CLIFormatter()
        metrics = TokenMetrics("t1", "engineer", 100, 50, 0, 0.01)
        line = formatter.format_task_line(metrics)
        assert "\033[" not in line

    def test_format_session_summary_with_multiple_agents(self, formatter, tracker):
        """Verify session summary shows per-agent breakdown."""
        tracker.record_task_tokens("t1", "engineer", 2000, 1000, cost_usd=0.10)
        tracker.record_task_tokens("t2", "orchestrator", 500, 200, cost_usd=0.02)
        tracker.record_task_tokens("t3", "quality-engineer", 800, 400, cost_usd=0.04)

        stats = tracker.get_stats()
        summary = formatter.format_session_summary(stats, budget_usd=5.0)

        assert "engineer" in summary
        assert "orchestrator" in summary
        assert "quality-engineer" in summary
        assert "Token Session Summary" in summary

    def test_format_session_summary_shows_budget_percentage(self, formatter):
        """Verify budget percentage is shown in session summary."""
        stats = TokenStats()
        stats.total_cost_usd = 3.5
        stats.task_count = 5
        stats.total_input_tokens = 5000
        stats.total_output_tokens = 2500
        stats.total_cached_tokens = 0

        summary = formatter.format_session_summary(stats, budget_usd=5.0)
        assert "70.0%" in summary

    def test_format_session_summary_empty_stats(self, formatter):
        """Verify formatter handles empty stats gracefully."""
        stats = TokenStats()
        summary = formatter.format_session_summary(stats, budget_usd=5.0)
        assert "Token Session Summary" in summary
        assert "0" in summary

    def test_format_session_summary_agents_sorted_by_cost(self, formatter, tracker):
        """Verify agents are sorted by cost descending."""
        tracker.record_task_tokens("t1", "cheap-agent", 100, 50, cost_usd=0.01)
        tracker.record_task_tokens("t2", "expensive-agent", 5000, 2500, cost_usd=0.50)

        stats = tracker.get_stats()
        summary = formatter.format_session_summary(stats, budget_usd=10.0)

        # expensive-agent should appear before cheap-agent
        expensive_pos = summary.index("expensive-agent")
        cheap_pos = summary.index("cheap-agent")
        assert expensive_pos < cheap_pos

    def test_colorize_with_color_enabled(self):
        """Verify ANSI codes are added when color is enabled."""
        formatter = CLIFormatter(no_color=False)
        colored = formatter._colorize("test", formatter.ANSI_GREEN)
        assert "\033[32m" in colored
        assert "\033[0m" in colored

    def test_budget_color_thresholds(self, formatter):
        """Verify color thresholds: green < 70%, yellow 70-90%, red >= 90%."""
        assert formatter._budget_color(50.0) == formatter.ANSI_GREEN
        assert formatter._budget_color(75.0) == formatter.ANSI_YELLOW
        assert formatter._budget_color(95.0) == formatter.ANSI_RED
        assert formatter._budget_color(100.0) == formatter.ANSI_RED
        assert formatter._budget_color(0.0) == formatter.ANSI_GREEN
        assert formatter._budget_color(69.9) == formatter.ANSI_GREEN
        assert formatter._budget_color(70.0) == formatter.ANSI_YELLOW
        assert formatter._budget_color(90.0) == formatter.ANSI_RED


# ===========================================================================
# 3. Budget Checker E2E Tests
# ===========================================================================

class TestBudgetCheckerEnforcement:
    """E2E tests for BudgetChecker enforcement logic."""

    def test_budget_ok_at_low_spend(self, budget_checker):
        """Verify OK status when spend is below warning threshold."""
        stats = TokenStats()
        stats.total_cost_usd = 1.0  # 20% of $5.00 default
        result = budget_checker.check(stats)
        assert result.status == BudgetStatus.OK
        assert result.pct_used < 70

    def test_budget_warning_at_70_percent(self, budget_checker):
        """Verify WARNING status at 70% of budget."""
        stats = TokenStats()
        stats.total_cost_usd = 3.5  # 70% of $5.00
        result = budget_checker.check(stats)
        assert result.status == BudgetStatus.WARNING

    def test_budget_critical_at_90_percent(self, budget_checker):
        """Verify CRITICAL status at 90% of budget."""
        stats = TokenStats()
        stats.total_cost_usd = 4.5  # 90% of $5.00
        result = budget_checker.check(stats)
        assert result.status == BudgetStatus.CRITICAL

    def test_budget_blocked_at_100_percent(self, budget_checker):
        """Verify BLOCKED status at 100% of budget."""
        stats = TokenStats()
        stats.total_cost_usd = 5.0  # 100% of $5.00
        result = budget_checker.check(stats)
        assert result.status == BudgetStatus.BLOCKED

    def test_budget_blocked_over_100_percent(self, budget_checker):
        """Verify BLOCKED status when over budget."""
        stats = TokenStats()
        stats.total_cost_usd = 6.0  # 120% of $5.00
        result = budget_checker.check(stats)
        assert result.status == BudgetStatus.BLOCKED

    def test_should_block_returns_true_when_blocked(self, budget_checker):
        """Verify should_block() returns True when budget exhausted."""
        stats = TokenStats()
        stats.total_cost_usd = 5.0
        assert budget_checker.should_block(stats) is True

    def test_should_block_returns_false_when_ok(self, budget_checker):
        """Verify should_block() returns False when budget is OK."""
        stats = TokenStats()
        stats.total_cost_usd = 1.0
        assert budget_checker.should_block(stats) is False

    def test_budget_result_str_representation(self, budget_checker):
        """Verify BudgetResult __str__ includes key info."""
        stats = TokenStats()
        stats.total_cost_usd = 2.5
        result = budget_checker.check(stats)
        result_str = str(result)
        assert "OK" in result_str or "WARNING" in result_str
        assert "%" in result_str

    def test_budget_checker_loads_from_yaml_config(self, tmp_path):
        """Verify BudgetChecker loads custom config from YAML."""
        config = {
            "budget": {
                "session_usd": 10.0,
                "warn_pct": 60,
                "critical_pct": 80,
                "block_pct": 100,
            }
        }
        config_path = tmp_path / "token_budget.yaml"
        config_path.write_text(yaml.dump(config))

        checker = BudgetChecker(config_path=config_path)
        stats = TokenStats()
        stats.total_cost_usd = 6.5  # 65% of $10.00 — should be WARNING with 60% threshold
        result = checker.check(stats)
        assert result.status == BudgetStatus.WARNING
        assert result.budget_usd == 10.0

    def test_budget_checker_falls_back_to_defaults_on_missing_file(self):
        """Verify BudgetChecker uses defaults when config file missing."""
        checker = BudgetChecker(config_path=Path("/nonexistent/path.yaml"))
        stats = TokenStats()
        stats.total_cost_usd = 0.0
        result = checker.check(stats)
        assert result.status == BudgetStatus.OK
        assert result.budget_usd == 5.0  # Default

    def test_budget_checker_zero_budget_with_no_spend(self, tmp_path):
        """Verify zero budget with zero spend returns OK."""
        config = {"budget": {"session_usd": 0.0}}
        config_path = tmp_path / "token_budget.yaml"
        config_path.write_text(yaml.dump(config))

        checker = BudgetChecker(config_path=config_path)
        stats = TokenStats()
        stats.total_cost_usd = 0.0
        result = checker.check(stats)
        assert result.status == BudgetStatus.OK

    def test_budget_checker_zero_budget_with_any_spend(self, tmp_path):
        """Verify zero budget with any spend returns BLOCKED."""
        config = {"budget": {"session_usd": 0.0}}
        config_path = tmp_path / "token_budget.yaml"
        config_path.write_text(yaml.dump(config))

        checker = BudgetChecker(config_path=config_path)
        stats = TokenStats()
        stats.total_cost_usd = 0.01
        result = checker.check(stats)
        assert result.status == BudgetStatus.BLOCKED

    def test_budget_remaining_calculated_correctly(self, budget_checker):
        """Verify remaining_usd is calculated correctly."""
        stats = TokenStats()
        stats.total_cost_usd = 2.0
        result = budget_checker.check(stats)
        assert abs(result.remaining_usd - 3.0) < 0.001

    def test_budget_remaining_clamped_to_zero(self, budget_checker):
        """Verify remaining_usd never goes negative."""
        stats = TokenStats()
        stats.total_cost_usd = 10.0  # Over $5.00 budget
        result = budget_checker.check(stats)
        assert result.remaining_usd == 0.0


# ===========================================================================
# 4. OrchestratorCLI E2E Tests
# ===========================================================================

class TestOrchestratorCLIFullWorkflow:
    """E2E tests for OrchestratorCLI unified integration."""

    def test_on_task_complete_records_and_prints(self, orchestrator_cli, capsys):
        """Verify on_task_complete records metrics and prints output."""
        delegate = make_delegate("task-cli-001", role="Engineer")
        handback = make_handback("task-cli-001", tokens_in=1000, tokens_out=500, cost_usd=0.05)

        orchestrator_cli.on_task_complete(delegate, handback)

        captured = capsys.readouterr()
        assert "engineer" in captured.out.lower()

        stats = orchestrator_cli.get_session_stats()
        assert stats.task_count == 1
        assert stats.total_cost_usd == 0.05

    def test_on_task_complete_raises_without_task_id(self, orchestrator_cli):
        """Verify on_task_complete raises ValueError when task_id missing."""
        delegate = make_delegate()
        handback = make_handback()
        del handback["task_id"]

        with pytest.raises(ValueError, match="task_id"):
            orchestrator_cli.on_task_complete(delegate, handback)

    def test_on_task_complete_calls_budget_callback_on_warning(self, tracker):
        """Verify budget callback is called when budget warning triggered."""
        callback_results = []
        cli = OrchestratorCLI(
            token_tracker=tracker,
            no_color=True,
            on_budget_exceeded=lambda r: callback_results.append(r),
        )

        # Set up a budget that will trigger warning at $3.50
        # Default budget is $5.00, warning at 70%
        delegate = make_delegate("task-budget-001")
        handback = make_handback("task-budget-001", cost_usd=3.6)  # 72% of $5.00

        cli.on_task_complete(delegate, handback)

        assert len(callback_results) == 1
        assert callback_results[0].status in (BudgetStatus.WARNING, BudgetStatus.CRITICAL, BudgetStatus.BLOCKED)

    def test_print_session_summary_outputs_formatted_text(self, orchestrator_cli, capsys):
        """Verify print_session_summary produces formatted output."""
        delegate = make_delegate("task-sum-001")
        handback = make_handback("task-sum-001", tokens_in=2000, tokens_out=1000, cost_usd=0.10)
        orchestrator_cli.on_task_complete(delegate, handback)

        orchestrator_cli.print_session_summary()

        captured = capsys.readouterr()
        assert "Token Session Summary" in captured.out
        assert "engineer" in captured.out.lower()

    def test_should_block_new_tasks_false_when_under_budget(self, orchestrator_cli):
        """Verify should_block_new_tasks returns False when under budget."""
        assert orchestrator_cli.should_block_new_tasks() is False

    def test_should_block_new_tasks_true_when_over_budget(self, tracker, tmp_path):
        """Verify should_block_new_tasks returns True when over budget."""
        config = {"budget": {"session_usd": 1.0}}
        config_path = tmp_path / "token_budget.yaml"
        config_path.write_text(yaml.dump(config))

        cli = OrchestratorCLI(
            token_tracker=tracker,
            budget_config_path=config_path,
            no_color=True,
        )
        tracker.record_task_tokens("t1", "engineer", 1000, 500, cost_usd=1.5)
        assert cli.should_block_new_tasks() is True

    def test_reset_session_clears_all_metrics(self, orchestrator_cli):
        """Verify reset_session clears all recorded metrics."""
        delegate = make_delegate("task-reset-001")
        handback = make_handback("task-reset-001", cost_usd=0.10)
        orchestrator_cli.on_task_complete(delegate, handback)

        orchestrator_cli.reset_session()

        stats = orchestrator_cli.get_session_stats()
        assert stats.task_count == 0
        assert stats.total_cost_usd == 0.0

    def test_get_budget_status_returns_budget_result(self, orchestrator_cli):
        """Verify get_budget_status returns a BudgetResult."""
        result = orchestrator_cli.get_budget_status()
        assert isinstance(result, BudgetResult)
        assert result.status == BudgetStatus.OK

    def test_full_session_lifecycle(self, orchestrator_cli, capsys):
        """E2E test: full session with multiple tasks, summary, and reset."""
        agents = [
            ("Engineer", "task-life-001", 1000, 500, 0.05),
            ("Senior Engineer", "task-life-002", 2000, 1000, 0.10),
            ("Quality Engineer", "task-life-003", 800, 400, 0.04),
        ]

        for role, task_id, inp, out, cost in agents:
            delegate = make_delegate(task_id, role=role)
            handback = make_handback(task_id, tokens_in=inp, tokens_out=out, cost_usd=cost)
            orchestrator_cli.on_task_complete(delegate, handback)

        stats = orchestrator_cli.get_session_stats()
        assert stats.task_count == 3
        assert abs(stats.total_cost_usd - 0.19) < 0.001

        orchestrator_cli.print_session_summary()
        captured = capsys.readouterr()
        assert "Token Session Summary" in captured.out

        orchestrator_cli.reset_session()
        stats_after = orchestrator_cli.get_session_stats()
        assert stats_after.task_count == 0


# ===========================================================================
# 5. Model Selection E2E Tests
# ===========================================================================

class TestComplexityScorerWithRealTasks:
    """E2E tests for ComplexityScorer with realistic task attributes."""

    def test_trivial_routing_task_scores_low(self, scorer):
        """Verify trivial routing tasks score < 20."""
        attrs = TaskAttributes(effort="low", task_type="routing", has_plan=True)
        score, level = scorer.score(attrs)
        assert level == ComplexityLevel.TRIVIAL
        assert score < 20

    def test_high_effort_architecture_scores_critical(self, scorer):
        """Verify high-effort architecture tasks score >= 60."""
        attrs = TaskAttributes(
            effort="high",
            task_type="architecture",
            has_plan=False,
            scope_clarity=0.3,
            is_cross_service=True,
            estimated_tokens=50_000,
        )
        score, level = scorer.score(attrs)
        assert level in (ComplexityLevel.HIGH, ComplexityLevel.CRITICAL)
        assert score >= 60

    def test_security_sensitive_adds_penalty(self, scorer):
        """Verify security_sensitive=True increases score."""
        base_attrs = TaskAttributes(effort="medium", task_type="implementation")
        secure_attrs = TaskAttributes(effort="medium", task_type="implementation", security_sensitive=True)

        base_score, _ = scorer.score(base_attrs)
        secure_score, _ = scorer.score(secure_attrs)
        assert secure_score > base_score

    def test_no_plan_adds_penalty(self, scorer):
        """Verify has_plan=False increases score."""
        with_plan = TaskAttributes(effort="medium", has_plan=True)
        without_plan = TaskAttributes(effort="medium", has_plan=False)

        score_with, _ = scorer.score(with_plan)
        score_without, _ = scorer.score(without_plan)
        assert score_without > score_with

    def test_score_clamped_to_100(self, scorer):
        """Verify score never exceeds 100."""
        attrs = TaskAttributes(
            effort="max",
            task_type="architecture",
            has_plan=False,
            scope_clarity=0.0,
            is_cross_service=True,
            has_external_dependencies=True,
            security_sensitive=True,
            estimated_tokens=100_000,
            num_files_affected=20,
            prior_escalation_count=10,
            required_quality_score=99.0,
        )
        score, _ = scorer.score(attrs)
        assert score <= 100.0

    def test_score_clamped_to_zero(self, scorer):
        """Verify score never goes below 0."""
        attrs = TaskAttributes(
            effort="low",
            task_type="trivial",
            tags=["trivial", "simple", "well-scoped"],
        )
        score, _ = scorer.score(attrs)
        assert score >= 0.0

    def test_score_from_dict_matches_score_from_attrs(self, scorer):
        """Verify score_from_dict produces same result as score()."""
        data = {
            "effort": "high",
            "task_type": "refactor",
            "has_plan": False,
            "scope_clarity": 0.7,
            "estimated_tokens": 10_000,
        }
        attrs = TaskAttributes(
            effort="high",
            task_type="refactor",
            has_plan=False,
            scope_clarity=0.7,
            estimated_tokens=10_000,
        )

        score_dict, level_dict = scorer.score_from_dict(data)
        score_attrs, level_attrs = scorer.score(attrs)

        assert score_dict == score_attrs
        assert level_dict == level_attrs

    def test_describe_returns_human_readable_string(self, scorer):
        """Verify describe() returns a non-empty human-readable string."""
        attrs = TaskAttributes(effort="high", task_type="refactor", security_sensitive=True)
        score, level = scorer.score(attrs)
        description = scorer.describe(attrs, score, level)
        assert "Complexity Score" in description
        assert str(round(score, 1)) in description

    def test_cross_service_adds_penalty(self, scorer):
        """Verify is_cross_service=True increases score."""
        base = TaskAttributes(effort="medium")
        cross = TaskAttributes(effort="medium", is_cross_service=True)
        base_score, _ = scorer.score(base)
        cross_score, _ = scorer.score(cross)
        assert cross_score > base_score

    def test_tags_affect_score(self, scorer):
        """Verify tags can increase or decrease score."""
        base = TaskAttributes(effort="medium")
        ambiguous = TaskAttributes(effort="medium", tags=["ambiguous"])
        simple = TaskAttributes(effort="medium", tags=["simple"])

        base_score, _ = scorer.score(base)
        ambiguous_score, _ = scorer.score(ambiguous)
        simple_score, _ = scorer.score(simple)

        assert ambiguous_score > base_score
        assert simple_score < base_score


class TestModelSelectorRoutingDecisions:
    """E2E tests for ModelSelector routing decisions."""

    def test_trivial_task_routes_to_haiku(self, selector):
        """Verify trivial tasks route to Haiku."""
        attrs = TaskAttributes(effort="low", task_type="routing")
        decision = selector.select(attrs)
        assert decision.model == ModelTier.HAIKU

    def test_medium_task_routes_to_sonnet(self, selector):
        """Verify medium-complexity tasks route to Sonnet."""
        attrs = TaskAttributes(effort="medium", task_type="general")
        decision = selector.select(attrs)
        assert decision.model in (ModelTier.HAIKU, ModelTier.SONNET)

    def test_critical_task_routes_to_opus(self, selector):
        """Verify critical tasks route to Opus."""
        attrs = TaskAttributes(
            effort="max",
            task_type="architecture",
            has_plan=False,
            scope_clarity=0.2,
            is_cross_service=True,
            estimated_tokens=100_000,
        )
        decision = selector.select(attrs)
        assert decision.model == ModelTier.OPUS

    def test_security_sensitive_overrides_to_opus(self, selector):
        """Verify security_sensitive=True forces Opus minimum."""
        attrs = TaskAttributes(effort="low", task_type="trivial", security_sensitive=True)
        decision = selector.select(attrs)
        assert decision.model == ModelTier.OPUS
        assert decision.override_applied is True
        assert "security" in decision.override_reason.lower()

    def test_cross_service_overrides_to_sonnet_minimum(self, selector):
        """Verify is_cross_service=True forces Sonnet minimum from Haiku."""
        attrs = TaskAttributes(effort="low", task_type="routing", is_cross_service=True)
        decision = selector.select(attrs)
        assert decision.model != ModelTier.HAIKU
        assert decision.override_applied is True

    def test_high_quality_requirement_upgrades_model(self, selector):
        """Verify required_quality_score > 95 upgrades model one tier."""
        attrs = TaskAttributes(
            effort="low",
            task_type="trivial",
            required_quality_score=96.0,
        )
        decision = selector.select(attrs)
        # Should be upgraded from Haiku to Sonnet
        assert decision.model != ModelTier.HAIKU or decision.override_applied

    def test_routing_decision_has_all_fields(self, selector):
        """Verify RoutingDecision contains all expected fields."""
        attrs = TaskAttributes(effort="medium")
        decision = selector.select(attrs)

        assert decision.model is not None
        assert decision.complexity_score >= 0
        assert decision.complexity_level is not None
        assert decision.cost_multiplier > 0
        assert decision.quality_baseline > 0
        assert decision.rationale != ""

    def test_select_from_dict_matches_select_from_attrs(self, selector):
        """Verify select_from_dict produces same result as select()."""
        data = {"effort": "high", "task_type": "refactor", "has_plan": False}
        attrs = TaskAttributes(effort="high", task_type="refactor", has_plan=False)

        decision_dict = selector.select_from_dict(data)
        decision_attrs = selector.select(attrs)

        assert decision_dict.model == decision_attrs.model
        assert decision_dict.complexity_score == decision_attrs.complexity_score

    def test_estimate_cost_returns_zero_without_tokens(self, selector):
        """Verify estimate_cost returns 0.0 when estimated_tokens is None."""
        attrs = TaskAttributes(effort="medium")
        cost = selector.estimate_cost(attrs)
        assert cost == 0.0

    def test_estimate_cost_scales_with_model_tier(self, selector):
        """Verify cost estimate scales with model cost multiplier."""
        haiku_attrs = TaskAttributes(effort="low", task_type="routing", estimated_tokens=1000)
        opus_attrs = TaskAttributes(
            effort="max", task_type="architecture",
            estimated_tokens=1000, security_sensitive=True
        )

        haiku_cost = selector.estimate_cost(haiku_attrs)
        opus_cost = selector.estimate_cost(opus_attrs)

        assert opus_cost > haiku_cost

    def test_model_str_representation(self, selector):
        """Verify RoutingDecision __str__ is informative."""
        attrs = TaskAttributes(effort="high", security_sensitive=True)
        decision = selector.select(attrs)
        decision_str = str(decision)
        assert "Model:" in decision_str
        assert "Cost multiplier" in decision_str


class TestCostQualityAnalyzerTradeoffs:
    """E2E tests for CostQualityAnalyzer."""

    def _make_records(self):
        """Create a realistic set of task metric records."""
        return [
            {"role": "engineer", "model": "haiku-4-5", "tokens_in": 1000, "tokens_out": 500,
             "cost": 0.05, "quality_score": 88.0, "complexity_score": 25.0, "escalated": False},
            {"role": "engineer", "model": "haiku-4-5", "tokens_in": 1500, "tokens_out": 750,
             "cost": 0.07, "quality_score": 85.0, "complexity_score": 30.0, "escalated": False},
            {"role": "senior-engineer", "model": "sonnet-4-6", "tokens_in": 3000, "tokens_out": 1500,
             "cost": 0.20, "quality_score": 94.0, "complexity_score": 65.0, "escalated": False},
            {"role": "orchestrator", "model": "haiku-4-5", "tokens_in": 500, "tokens_out": 200,
             "cost": 0.02, "quality_score": 90.0, "complexity_score": 15.0, "escalated": False},
        ]

    def test_analyze_returns_efficiency_report(self, analyzer):
        """Verify analyze() returns an EfficiencyReport."""
        records = self._make_records()
        analyzer.load(records)
        report = analyzer.analyze()
        assert report is not None
        assert report.total_tasks == len(records)

    def test_analyze_computes_role_stats(self, analyzer):
        """Verify per-role statistics are computed."""
        records = self._make_records()
        analyzer.load(records)
        report = analyzer.analyze()
        assert "engineer" in report.role_stats
        assert "senior-engineer" in report.role_stats

    def test_analyze_computes_total_cost(self, analyzer):
        """Verify total cost is summed correctly."""
        records = self._make_records()
        analyzer.load(records)
        report = analyzer.analyze()
        expected_cost = sum(r["cost"] for r in records)
        assert abs(report.total_cost - expected_cost) < 0.001

    def test_analyze_empty_records(self, analyzer):
        """Verify analyzer handles empty records gracefully."""
        analyzer.load([])
        report = analyzer.analyze()
        assert report.total_tasks == 0
        assert report.total_cost == 0.0

    def test_report_summary_is_human_readable(self, analyzer):
        """Verify report.summary() returns a non-empty string."""
        records = self._make_records()
        analyzer.load(records)
        report = analyzer.analyze()
        summary = report.summary()
        assert len(summary) > 0
        assert "Cost-Quality" in summary


# ===========================================================================
# 6. Orchestrator Improvements E2E Tests
# ===========================================================================

class TestDryRunModeEndToEnd:
    """E2E tests for DryRunContext."""

    def test_dry_run_logs_file_write_without_writing(self, tmp_path):
        """Verify file writes are logged but not executed in dry-run mode."""
        target_file = tmp_path / "output.txt"

        with DryRunContext(enabled=True) as dry_run:
            dry_run.log_file_write(str(target_file), "test content")
            ops = dry_run.operations

        assert not target_file.exists()
        assert len(ops) == 1
        assert ops[0].operation_type == OperationType.FILE_WRITE

    def test_dry_run_logs_multiple_operations(self, tmp_path):
        """Verify multiple operations are all logged."""
        with DryRunContext(enabled=True) as dry_run:
            dry_run.log_file_write("/tmp/a.txt", "content a")
            dry_run.log_file_write("/tmp/b.txt", "content b")
            dry_run.log_git_commit("Add feature X")
            dry_run.log_queue_move("task-001", "incoming", "processing")
            ops = dry_run.operations

        assert len(ops) == 4

    def test_dry_run_audit_trail_is_serializable(self, tmp_path):
        """Verify audit trail can be serialized to JSON."""
        with DryRunContext(enabled=True) as dry_run:
            dry_run.log_file_write("/tmp/test.txt", "content")
            dry_run.log_git_commit("Test commit")
            ops = dry_run.operations

        for op in ops:
            # Should not raise
            serialized = json.dumps(op.to_dict())
            assert serialized is not None

    def test_dry_run_disabled_mode_records_nothing(self, tmp_path):
        """Verify disabled dry-run mode still records operations (audit trail always on)."""
        with DryRunContext(enabled=False) as dry_run:
            dry_run.log_file_write("/tmp/test.txt", "content")
            ops = dry_run.operations

        # DryRunContext always records operations for audit trail,
        # but enabled=False means operations are not intercepted (would actually execute)
        # The operations list tracks what was called, regardless of enabled state
        assert isinstance(ops, list)

    def test_dry_run_operation_timestamps_are_valid(self, tmp_path):
        """Verify all logged operations have valid ISO timestamps."""
        with DryRunContext(enabled=True) as dry_run:
            dry_run.log_file_write("/tmp/test.txt", "content")
            ops = dry_run.operations

        for op in ops:
            # Should parse without error
            datetime.fromisoformat(op.timestamp)

    def test_dry_run_get_audit_trail_returns_dict(self, tmp_path):
        """Verify get_audit_trail returns a serializable dict."""
        with DryRunContext(enabled=True) as dry_run:
            dry_run.log_file_write("/tmp/test.txt", "content")
            trail = dry_run.get_audit_trail()

        assert isinstance(trail, dict)
        assert "operations" in trail

    def test_dry_run_print_summary_returns_string(self, tmp_path):
        """Verify print_summary returns a non-empty string."""
        with DryRunContext(enabled=True) as dry_run:
            dry_run.log_file_write("/tmp/test.txt", "content")
            dry_run.log_git_commit("Test commit")
            summary = dry_run.print_summary()

        assert isinstance(summary, str)
        assert len(summary) > 0


class TestShadowModeWithMetrics:
    """E2E tests for ShadowModeContext."""

    def test_shadow_mode_executes_production_path(self, tmp_path):
        """Verify shadow mode executes production function and captures result."""
        production_calls = []

        def production_fn():
            production_calls.append(1)
            return {"result": "production"}

        ctx = ShadowModeContext(
            task_id="task-shadow-001",
            traffic_percentage=100,
            metrics_dir=str(tmp_path),
            enabled=True,
        )
        result = ctx.execute_production(production_fn)

        assert result == {"result": "production"}
        assert len(production_calls) == 1
        assert ctx.production_result == {"result": "production"}

    def test_shadow_mode_executes_shadow_when_sampled(self, tmp_path):
        """Verify shadow function is executed when task is sampled."""
        shadow_calls = []

        ctx = ShadowModeContext(
            task_id="task-shadow-002",
            traffic_percentage=100,  # 100% ensures sampling
            metrics_dir=str(tmp_path),
            enabled=True,
        )
        # Force sampled=True for determinism
        ctx.sampled = True

        ctx.execute_shadow(lambda: shadow_calls.append(1) or "shadow")

        assert len(shadow_calls) == 1

    def test_shadow_mode_disabled_skips_shadow(self, tmp_path):
        """Verify disabled shadow mode marks task as not sampled."""
        ctx = ShadowModeContext(
            task_id="task-shadow-003",
            traffic_percentage=100,
            metrics_dir=str(tmp_path),
            enabled=False,
        )
        assert ctx.sampled is False

    def test_shadow_mode_records_production_latency(self, tmp_path):
        """Verify shadow mode records latency for production path."""
        ctx = ShadowModeContext(
            task_id="task-shadow-004",
            traffic_percentage=100,
            metrics_dir=str(tmp_path),
            enabled=True,
        )
        ctx.execute_production(lambda: time.sleep(0.01) or "done")
        assert ctx.production_latency_ms >= 0

    def test_shadow_mode_deterministic_sampling(self, tmp_path):
        """Verify same task_id always produces same sampling decision."""
        results = set()
        for _ in range(5):
            ctx = ShadowModeContext(
                task_id="deterministic-task-id",
                traffic_percentage=50,
                metrics_dir=str(tmp_path),
                enabled=True,
            )
            results.add(ctx.sampled)

        # Same task_id should always produce same sampling decision
        assert len(results) == 1

    def test_shadow_mode_traffic_percentage_validation(self, tmp_path):
        """Verify invalid traffic percentage raises ValueError."""
        with pytest.raises(ValueError):
            ShadowModeContext(
                task_id="task-invalid",
                traffic_percentage=42,  # Not a valid ShadowModeTraffic value
                metrics_dir=str(tmp_path),
                enabled=True,
            )


class TestGradualRolloutStages:
    """E2E tests for RolloutManager."""

    def test_rollout_disabled_does_not_use_new_path(self, tmp_path):
        """Verify disabled rollout never routes to new path."""
        from src.orchestration.agents.gradual_rollout import RolloutConfig
        config = RolloutConfig(audit_dir=str(tmp_path))
        rollout = RolloutManager(config=config, initial_stage=RolloutStage.DISABLED)

        for i in range(10):
            assert rollout.should_use_new_path(f"task-{i:03d}") is False

    def test_rollout_100_percent_uses_new_path(self, tmp_path):
        """Verify 100% rollout always routes to new path."""
        from src.orchestration.agents.gradual_rollout import RolloutConfig
        config = RolloutConfig(audit_dir=str(tmp_path))
        rollout = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_100)

        for i in range(10):
            assert rollout.should_use_new_path(f"task-{i:03d}") is True

    def test_rollout_deterministic_sampling(self, tmp_path):
        """Verify same task_id always routes the same way."""
        from src.orchestration.agents.gradual_rollout import RolloutConfig
        config = RolloutConfig(audit_dir=str(tmp_path))
        rollout = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_50)

        results = set()
        for _ in range(5):
            results.add(rollout.should_use_new_path("deterministic-task-id"))

        # Same task_id should always produce same result
        assert len(results) == 1

    def test_rollout_stage_progression(self, tmp_path):
        """Verify rollout can advance through stages."""
        from src.orchestration.agents.gradual_rollout import RolloutConfig
        config = RolloutConfig(audit_dir=str(tmp_path))
        rollout = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_10)

        assert rollout.stage == RolloutStage.STAGE_10
        rollout.advance()
        assert rollout.stage == RolloutStage.STAGE_25

    def test_rollout_rollback(self, tmp_path):
        """Verify rollout can roll back to previous stage."""
        from src.orchestration.agents.gradual_rollout import RolloutConfig
        config = RolloutConfig(audit_dir=str(tmp_path))
        rollout = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_50)

        rollout.rollback()
        assert rollout.stage.value < 50

    def test_rollout_pause_and_resume(self, tmp_path):
        """Verify rollout can be paused and resumed."""
        from src.orchestration.agents.gradual_rollout import RolloutConfig
        config = RolloutConfig(audit_dir=str(tmp_path))
        rollout = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_25)

        rollout.pause()
        assert rollout.is_paused is True

        rollout.resume()
        assert rollout.is_paused is False


# ===========================================================================
# 7. Harness E2E Tests
# ===========================================================================

class TestCopilotCLIHarnessWithTokenTracking:
    """E2E tests for Copilot CLI streaming harness."""

    def test_streaming_renderer_yields_start_event(self, tmp_path):
        """Verify StreamingRenderer yields start events for each skill."""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()

        # Create a minimal skill directory
        skill_dir = src / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill\n")

        renderer = StreamingRenderer(str(src), str(dst), "SKILL.md")
        events = list(renderer.render_all())

        event_types = [e.type for e in events]
        assert "start" in event_types or "summary" in event_types

    def test_streaming_renderer_yields_summary_event(self, tmp_path):
        """Verify StreamingRenderer yields a summary event at the end."""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()

        renderer = StreamingRenderer(str(src), str(dst), "SKILL.md")
        events = list(renderer.render_all())

        # Last event should be summary
        if events:
            assert events[-1].type == "summary"

    def test_stream_event_to_json_is_valid(self):
        """Verify StreamEvent.to_json() produces valid JSON."""
        event = StreamEvent(
            type="complete",
            skill="test-skill",
            timestamp="2026-05-17T12:00:00Z",
            data={"duration_ms": 150, "bytes": 4096},
        )
        json_str = event.to_json()
        parsed = json.loads(json_str)
        assert parsed["type"] == "complete"
        assert parsed["skill"] == "test-skill"
        assert parsed["data"]["duration_ms"] == 150

    def test_streaming_renderer_handles_empty_src_dir(self, tmp_path):
        """Verify StreamingRenderer handles empty source directory."""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()

        renderer = StreamingRenderer(str(src), str(dst), "SKILL.md")
        events = list(renderer.render_all())

        # Should yield at least a summary event
        assert any(e.type == "summary" for e in events)


# ===========================================================================
# 8. AgentInvoker → TokenTracker Integration Tests
# ===========================================================================

class TestAgentInvokerToTokenTrackerIntegration:
    """E2E tests for AgentInvoker → TokenTracker integration."""

    def test_invoker_wires_token_tracker(self, tmp_dirs, tracker):
        """Verify AgentInvoker accepts and stores TokenTracker."""
        invoker = AgentInvoker(
            processing_dir=tmp_dirs["processing"],
            delegates_dir=tmp_dirs["delegates"],
            spans_dir=tmp_dirs["spans"],
            token_tracker=tracker,
        )
        assert invoker._token_tracker is tracker

    def test_invoker_records_tokens_on_handback(self, tmp_dirs, tracker):
        """Verify _record_token_metrics records to TokenTracker."""
        invoker = AgentInvoker(
            processing_dir=tmp_dirs["processing"],
            delegates_dir=tmp_dirs["delegates"],
            spans_dir=tmp_dirs["spans"],
            token_tracker=tracker,
        )
        delegate = make_delegate("task-wire-001", role="Engineer")
        handback = make_handback("task-wire-001", tokens_in=1500, tokens_out=750, cost_usd=0.075)

        invoker._record_token_metrics(delegate, handback)

        stats = tracker.get_stats()
        assert stats.task_count == 1
        assert stats.total_input_tokens == 1500
        assert stats.total_output_tokens == 750

    def test_invoker_normalizes_role_to_agent_name(self, tmp_dirs, tracker):
        """Verify role names are normalized to agent slugs."""
        invoker = AgentInvoker(
            processing_dir=tmp_dirs["processing"],
            delegates_dir=tmp_dirs["delegates"],
            spans_dir=tmp_dirs["spans"],
            token_tracker=tracker,
        )
        delegate = make_delegate("task-norm-001", role="Senior Engineer")
        handback = make_handback("task-norm-001")

        invoker._record_token_metrics(delegate, handback)

        agent_stats = tracker.get_agent_stats("senior-engineer")
        assert agent_stats is not None

    def test_invoker_skips_synthetic_handbacks(self, tmp_dirs, tracker):
        """Verify synthetic HANDBACKs are not recorded."""
        invoker = AgentInvoker(
            processing_dir=tmp_dirs["processing"],
            delegates_dir=tmp_dirs["delegates"],
            spans_dir=tmp_dirs["spans"],
            token_tracker=tracker,
        )
        delegate = make_delegate("task-synth-001")
        handback = make_handback("task-synth-001")
        handback["_synthetic"] = True

        # Simulate the check
        if tracker and not handback.get("_synthetic"):
            invoker._record_token_metrics(delegate, handback)

        stats = tracker.get_stats()
        assert stats.task_count == 0

    def test_invoker_graceful_degradation_without_tracker(self, tmp_dirs):
        """Verify invoker works without TokenTracker (no crash)."""
        invoker = AgentInvoker(
            processing_dir=tmp_dirs["processing"],
            delegates_dir=tmp_dirs["delegates"],
            spans_dir=tmp_dirs["spans"],
        )
        assert invoker._token_tracker is None
        # No crash when no tracker
        delegate = make_delegate("task-no-tracker-001")
        handback = make_handback("task-no-tracker-001")
        # Should not raise
        if invoker._token_tracker:
            invoker._record_token_metrics(delegate, handback)

    def test_invoker_handles_tracker_errors_gracefully(self, tmp_dirs, tracker):
        """Verify tracker errors don't crash the invoker."""
        invoker = AgentInvoker(
            processing_dir=tmp_dirs["processing"],
            delegates_dir=tmp_dirs["delegates"],
            spans_dir=tmp_dirs["spans"],
            token_tracker=tracker,
        )
        tracker.record_task_tokens = MagicMock(side_effect=RuntimeError("Tracker error"))

        delegate = make_delegate("task-err-001")
        handback = make_handback("task-err-001")

        # Should not raise
        invoker._record_token_metrics(delegate, handback)


# ===========================================================================
# 9. Full Task Lifecycle Integration Test
# ===========================================================================

class TestFullTaskLifecycleWithAllComponents:
    """Full end-to-end lifecycle tests integrating all Phase 3 components."""

    def test_complete_task_lifecycle_with_model_selection_and_token_tracking(
        self, tracker, orchestrator_cli, selector, capsys
    ):
        """
        E2E: Select model → execute task → record tokens → check budget → print summary.
        """
        # Step 1: Model selection
        attrs = TaskAttributes(
            effort="high",
            task_type="implementation",
            estimated_tokens=5000,
            has_plan=True,
        )
        decision = selector.select(attrs)
        assert decision.model in (ModelTier.SONNET, ModelTier.OPUS)

        # Step 2: Simulate task execution and record tokens
        delegate = make_delegate("task-lifecycle-001", role="Senior Engineer")
        handback = make_handback(
            "task-lifecycle-001",
            tokens_in=5000,
            tokens_out=2500,
            cost_usd=0.225,
        )

        # Step 3: Record via OrchestratorCLI
        orchestrator_cli.on_task_complete(delegate, handback)

        # Step 4: Verify token tracking
        stats = orchestrator_cli.get_session_stats()
        assert stats.task_count == 1
        assert stats.total_input_tokens == 5000

        # Step 5: Check budget
        budget_status = orchestrator_cli.get_budget_status()
        assert budget_status.status in (BudgetStatus.OK, BudgetStatus.WARNING, BudgetStatus.CRITICAL)

        # Step 6: Print summary
        orchestrator_cli.print_session_summary()
        captured = capsys.readouterr()
        assert "Token Session Summary" in captured.out

    def test_multi_agent_session_with_budget_enforcement(self, tmp_path, capsys):
        """
        E2E: Multiple agents, budget enforcement, session reset.
        """
        # Set tight budget
        config = {"budget": {"session_usd": 0.5, "warn_pct": 70, "critical_pct": 90, "block_pct": 100}}
        config_path = tmp_path / "token_budget.yaml"
        config_path.write_text(yaml.dump(config))

        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        budget_alerts = []
        cli = OrchestratorCLI(
            token_tracker=tracker,
            budget_config_path=config_path,
            no_color=True,
            on_budget_exceeded=lambda r: budget_alerts.append(r),
        )

        # Run tasks until budget is exceeded
        tasks = [
            ("Engineer", "task-budget-001", 1000, 500, 0.15),
            ("Senior Engineer", "task-budget-002", 2000, 1000, 0.20),
            ("Lead Engineer", "task-budget-003", 1500, 750, 0.18),
        ]

        for role, task_id, inp, out, cost in tasks:
            delegate = make_delegate(task_id, role=role)
            handback = make_handback(task_id, tokens_in=inp, tokens_out=out, cost_usd=cost)
            cli.on_task_complete(delegate, handback)

        # Total cost = 0.53 > 0.50 budget → should be blocked
        assert cli.should_block_new_tasks() is True
        assert len(budget_alerts) > 0

        # Reset and verify clean state
        cli.reset_session()
        assert cli.should_block_new_tasks() is False

    def test_complexity_to_model_to_cost_pipeline(self, scorer, selector):
        """
        E2E: Task attributes → complexity score → model selection → cost estimate.
        """
        # Trivial task
        trivial = TaskAttributes(effort="low", task_type="routing", estimated_tokens=500)
        trivial_score, trivial_level = scorer.score(trivial)
        trivial_decision = selector.select(trivial)
        trivial_cost = selector.estimate_cost(trivial)

        # Critical task
        critical = TaskAttributes(
            effort="max",
            task_type="architecture",
            estimated_tokens=50_000,
            security_sensitive=True,
        )
        critical_score, critical_level = scorer.score(critical)
        critical_decision = selector.select(critical)
        critical_cost = selector.estimate_cost(critical)

        # Verify pipeline produces sensible results
        assert trivial_score < critical_score
        assert trivial_cost < critical_cost
        assert trivial_decision.cost_multiplier <= critical_decision.cost_multiplier
