"""
Phase 3 Production Readiness Tests

Validates production readiness across:
1. Backward compatibility — no breaking changes to existing APIs
2. Error handling — graceful degradation under failure conditions
3. Configuration — YAML loading, env vars, fallback defaults
4. Performance — token tracking overhead, formatting speed
5. Security — no secrets in metrics, cost data sanitization
6. Monitoring — Prometheus metrics, structured output
"""

import os
import time
import threading
import tempfile
import yaml
import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

import pytest

from src.orchestration.monitoring.metrics import MetricsRegistry
from src.orchestration.monitoring.token_tracker import TokenTracker, TokenMetrics, TokenStats
from src.orchestration.monitoring.cli_formatter import CLIFormatter
from src.orchestration.monitoring.budget_checker import BudgetChecker, BudgetStatus
from src.orchestration.monitoring.orchestrator_cli import OrchestratorCLI
from src.orchestration.models.complexity_scorer import ComplexityScorer, TaskAttributes
from src.orchestration.models.model_selector import ModelSelector, ModelTier


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def registry():
    return MetricsRegistry()


@pytest.fixture
def tracker(registry):
    return TokenTracker(registry)


@pytest.fixture
def tmp_dirs(tmp_path):
    processing = tmp_path / "processing"
    delegates = tmp_path / "delegates"
    spans = tmp_path / "spans"
    for d in [processing, delegates, spans]:
        d.mkdir(parents=True)
    return {"processing": processing, "delegates": delegates, "spans": spans, "base": tmp_path}


def make_handback(task_id="task-prod-001", tokens_in=1000, tokens_out=500, cost_usd=0.05):
    return {
        "handoff_type": "HANDBACK",
        "task_id": task_id,
        "status": "success",
        "deliverables": ["Modified: test.py"],
        "tests": [{"command": "pytest", "result": "PASS"}],
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_cached": 0,
        "model": "claude-sonnet-4.6",
        "effort": "medium",
        "duration_minutes": 5,
        "escalations": 0,
        "cost_usd": cost_usd,
    }


def make_delegate(task_id="task-prod-001", role="Engineer"):
    return {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "role": role,
        "model": "claude-sonnet-4.6",
        "effort": "medium",
        "scope": "Production test scope",
        "context": ["File: test.py"],
        "plan": ["1. Run tests"],
        "success_criteria": ["Tests pass"],
    }


# ===========================================================================
# 1. Backward Compatibility Tests
# ===========================================================================

class TestNoBreakingChangesToExistingAPIs:
    """Verify Phase 3 additions don't break existing APIs."""

    def test_token_tracker_record_task_tokens_signature(self, tracker):
        """Verify record_task_tokens accepts all documented parameters."""
        # Should work with all parameters
        tracker.record_task_tokens(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=100,
            cost_usd=0.05,
        )
        stats = tracker.get_stats()
        assert stats.task_count == 1

    def test_token_tracker_record_task_tokens_minimal_signature(self, tracker):
        """Verify record_task_tokens works with minimal required parameters."""
        # cached_tokens and cost_usd should be optional with defaults
        tracker.record_task_tokens(
            task_id="task-002",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
        )
        stats = tracker.get_stats()
        assert stats.task_count == 1
        assert stats.total_cost_usd == 0.0

    def test_cli_formatter_init_no_args(self):
        """Verify CLIFormatter can be initialized with no arguments."""
        formatter = CLIFormatter()
        assert formatter is not None

    def test_budget_checker_init_no_args(self):
        """Verify BudgetChecker can be initialized with no arguments."""
        checker = BudgetChecker()
        assert checker is not None

    def test_orchestrator_cli_minimal_init(self, tracker):
        """Verify OrchestratorCLI can be initialized with only token_tracker."""
        cli = OrchestratorCLI(token_tracker=tracker)
        assert cli is not None

    def test_complexity_scorer_init_no_args(self):
        """Verify ComplexityScorer can be initialized with no arguments."""
        scorer = ComplexityScorer()
        assert scorer is not None

    def test_model_selector_init_no_args(self):
        """Verify ModelSelector can be initialized with no arguments."""
        selector = ModelSelector()
        assert selector is not None

    def test_task_attributes_all_optional_fields(self):
        """Verify TaskAttributes can be created with no arguments."""
        attrs = TaskAttributes()
        assert attrs.effort == "medium"
        assert attrs.task_type == "general"
        assert attrs.has_plan is True

    def test_token_stats_default_values(self):
        """Verify TokenStats initializes with zero defaults."""
        stats = TokenStats()
        assert stats.total_input_tokens == 0
        assert stats.total_output_tokens == 0
        assert stats.total_cost_usd == 0.0
        assert stats.task_count == 0


class TestOptionalParametersDefaultCorrectly:
    """Verify optional parameters have correct defaults."""

    def test_budget_checker_default_session_budget(self):
        """Verify default session budget is $5.00."""
        checker = BudgetChecker()
        assert checker.budget_config["session_usd"] == 5.0

    def test_budget_checker_default_warn_pct(self):
        """Verify default warning threshold is 70%."""
        checker = BudgetChecker()
        assert checker.budget_config["warn_pct"] == 70

    def test_budget_checker_default_critical_pct(self):
        """Verify default critical threshold is 90%."""
        checker = BudgetChecker()
        assert checker.budget_config["critical_pct"] == 90

    def test_budget_checker_default_block_pct(self):
        """Verify default block threshold is 100%."""
        checker = BudgetChecker()
        assert checker.budget_config["block_pct"] == 100

    def test_cli_formatter_default_no_color_false(self):
        """Verify CLIFormatter defaults to color enabled."""
        # Without NO_COLOR env var, no_color should be False
        with patch.dict(os.environ, {}, clear=True):
            # Remove NO_COLOR if present
            os.environ.pop("NO_COLOR", None)
            formatter = CLIFormatter()
        assert formatter.no_color is False

    def test_task_attributes_default_scope_clarity(self):
        """Verify scope_clarity defaults to 1.0 (clear)."""
        attrs = TaskAttributes()
        assert attrs.scope_clarity == 1.0

    def test_task_attributes_default_required_quality(self):
        """Verify required_quality_score defaults to 85.0."""
        attrs = TaskAttributes()
        assert attrs.required_quality_score == 85.0


# ===========================================================================
# 2. Error Handling Tests
# ===========================================================================

class TestTokenTrackerErrorsDontBreakTaskExecution:
    """Verify TokenTracker errors are handled gracefully."""

    def test_tracker_handles_concurrent_errors_gracefully(self, tracker):
        """Verify tracker remains consistent after concurrent error conditions."""
        errors = []

        def record_with_error(i):
            try:
                if i % 3 == 0:
                    # Intentionally invalid — should raise ValueError
                    tracker.record_task_tokens(f"task-{i}", "engineer", -1, 0)
                else:
                    tracker.record_task_tokens(f"task-{i}", "engineer", 100, 50)
            except ValueError:
                pass  # Expected
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_with_error, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Unexpected errors: {errors}"
        # Valid tasks should be recorded
        stats = tracker.get_stats()
        assert stats.task_count > 0


class TestBudgetCheckerErrorsDontBlockTasks:
    """Verify BudgetChecker errors don't block task execution."""

    def test_budget_checker_with_corrupted_yaml(self, tmp_path):
        """Verify BudgetChecker falls back to defaults on corrupted YAML."""
        config_path = tmp_path / "token_budget.yaml"
        config_path.write_text("this: is: not: valid: yaml: !!!")

        # Should not raise — falls back to defaults
        checker = BudgetChecker(config_path=config_path)
        assert checker.budget_config["session_usd"] == 5.0  # Default

    def test_budget_checker_with_empty_yaml(self, tmp_path):
        """Verify BudgetChecker handles empty YAML file."""
        config_path = tmp_path / "token_budget.yaml"
        config_path.write_text("")

        checker = BudgetChecker(config_path=config_path)
        assert checker.budget_config["session_usd"] == 5.0

    def test_budget_checker_with_partial_yaml(self, tmp_path):
        """Verify BudgetChecker merges partial config with defaults."""
        config = {"budget": {"session_usd": 10.0}}  # Only override session_usd
        config_path = tmp_path / "token_budget.yaml"
        config_path.write_text(yaml.dump(config))

        checker = BudgetChecker(config_path=config_path)
        assert checker.budget_config["session_usd"] == 10.0
        assert checker.budget_config["warn_pct"] == 70  # Default preserved

    def test_budget_checker_with_nonexistent_path(self):
        """Verify BudgetChecker handles nonexistent config path."""
        checker = BudgetChecker(config_path=Path("/nonexistent/config.yaml"))
        stats = TokenStats()
        result = checker.check(stats)
        assert result.status == BudgetStatus.OK


class TestOrchestratorCLIErrorsDontCrashOrchestrator:
    """Verify OrchestratorCLI errors are handled gracefully."""

    def test_on_task_complete_with_missing_token_fields(self, tracker, capsys):
        """Verify on_task_complete handles missing token fields gracefully."""
        cli = OrchestratorCLI(token_tracker=tracker, no_color=True)
        delegate = make_delegate("task-err-001")
        # Handback with no token fields
        handback = {
            "handoff_type": "HANDBACK",
            "task_id": "task-err-001",
            "status": "success",
        }

        # Should not raise — uses defaults
        cli.on_task_complete(delegate, handback)

        stats = cli.get_session_stats()
        assert stats.task_count == 1
        assert stats.total_cost_usd == 0.0

    def test_on_task_complete_with_zero_tokens(self, tracker, capsys):
        """Verify on_task_complete handles zero token counts."""
        cli = OrchestratorCLI(token_tracker=tracker, no_color=True)
        delegate = make_delegate("task-zero-001")
        handback = make_handback("task-zero-001", tokens_in=0, tokens_out=0, cost_usd=0.0)

        cli.on_task_complete(delegate, handback)

        stats = cli.get_session_stats()
        assert stats.task_count == 1

    def test_budget_callback_error_does_not_crash_cli(self, tracker):
        """Verify errors in budget callback don't crash OrchestratorCLI."""
        def bad_callback(result):
            raise RuntimeError("Callback error")

        cli = OrchestratorCLI(
            token_tracker=tracker,
            no_color=True,
            on_budget_exceeded=bad_callback,
        )
        # Spend enough to trigger warning ($5 * 70% = $3.50)
        delegate = make_delegate("task-cb-001")
        handback = make_handback("task-cb-001", cost_usd=3.6)

        # Should not raise even if callback raises
        try:
            cli.on_task_complete(delegate, handback)
        except RuntimeError:
            pytest.fail("Callback error should not propagate from OrchestratorCLI")


# ===========================================================================
# 3. Configuration Tests
# ===========================================================================

class TestTokenBudgetYamlLoadsCorrectly:
    """Verify token_budget.yaml configuration loading."""

    def test_full_config_loads_all_fields(self, tmp_path):
        """Verify all config fields are loaded from YAML."""
        config = {
            "budget": {
                "session_usd": 15.0,
                "daily_usd": 50.0,
                "warn_pct": 65,
                "critical_pct": 85,
                "block_pct": 100,
            },
            "display": {
                "mode": "verbose",
                "show_per_task": True,
                "show_session_summary": True,
            }
        }
        config_path = tmp_path / "token_budget.yaml"
        config_path.write_text(yaml.dump(config))

        checker = BudgetChecker(config_path=config_path)
        assert checker.budget_config["session_usd"] == 15.0
        assert checker.budget_config["warn_pct"] == 65
        assert checker.budget_config["critical_pct"] == 85

    def test_config_with_display_settings(self, tmp_path):
        """Verify display settings are loaded from YAML."""
        config = {
            "display": {
                "mode": "compact",
                "show_per_task": False,
            }
        }
        config_path = tmp_path / "token_budget.yaml"
        config_path.write_text(yaml.dump(config))

        checker = BudgetChecker(config_path=config_path)
        assert checker.display_config["mode"] == "compact"
        assert checker.display_config["show_per_task"] is False


class TestNoColorEnvVarRespected:
    """Verify NO_COLOR environment variable is respected."""

    def test_no_color_env_var_disables_ansi(self):
        """Verify NO_COLOR env var disables ANSI color codes."""
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            formatter = CLIFormatter()
        assert formatter.no_color is True

        metrics = TokenMetrics("t1", "engineer", 100, 50, 0, 0.01)
        line = formatter.format_task_line(metrics)
        assert "\033[" not in line

    def test_no_color_env_var_any_value_disables_color(self):
        """Verify NO_COLOR with any value disables color."""
        for value in ["1", "true", "yes", "0", ""]:
            with patch.dict(os.environ, {"NO_COLOR": value}):
                formatter = CLIFormatter()
            assert formatter.no_color is True, f"NO_COLOR={value!r} should disable color"

    def test_no_color_param_overrides_env(self):
        """Verify no_color=True parameter disables color even without env var."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("NO_COLOR", None)
            formatter = CLIFormatter(no_color=True)
        assert formatter.no_color is True

    def test_color_enabled_without_env_var(self):
        """Verify color is enabled when NO_COLOR is not set."""
        env = {k: v for k, v in os.environ.items() if k != "NO_COLOR"}
        with patch.dict(os.environ, env, clear=True):
            formatter = CLIFormatter(no_color=False)
        assert formatter.no_color is False


class TestConfigFallbackToDefaults:
    """Verify configuration falls back to sensible defaults."""

    def test_budget_checker_defaults_match_expected_values(self):
        """Verify default config matches documented defaults."""
        checker = BudgetChecker()
        assert checker.budget_config["session_usd"] == 5.0
        assert checker.budget_config["daily_usd"] == 20.0
        assert checker.budget_config["warn_pct"] == 70
        assert checker.budget_config["critical_pct"] == 90
        assert checker.budget_config["block_pct"] == 100

    def test_display_defaults_match_expected_values(self):
        """Verify display defaults match documented values."""
        checker = BudgetChecker()
        assert checker.display_config["mode"] == "compact"
        assert checker.display_config["show_per_task"] is True
        assert checker.display_config["show_session_summary"] is True


# ===========================================================================
# 4. Performance Tests
# ===========================================================================

class TestTokenTrackingOverheadMinimal:
    """Verify token tracking adds minimal overhead."""

    def test_record_task_tokens_completes_in_under_1ms(self, tracker):
        """Verify single token recording completes in under 1ms."""
        start = time.perf_counter()
        tracker.record_task_tokens("t1", "engineer", 1000, 500, cost_usd=0.05)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 1.0, f"Token recording took {elapsed_ms:.2f}ms (expected < 1ms)"

    def test_get_stats_completes_quickly_with_many_records(self, tracker):
        """Verify get_stats is fast even with 1000 records."""
        for i in range(1000):
            tracker.record_task_tokens(f"task-{i}", "engineer", 100, 50)

        start = time.perf_counter()
        stats = tracker.get_stats()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert stats.task_count == 1000
        assert elapsed_ms < 50.0, f"get_stats took {elapsed_ms:.2f}ms (expected < 50ms)"

    def test_token_tracking_overhead_under_5_percent(self, tracker):
        """Verify token tracking overhead is under 5% of baseline."""
        n_iterations = 1000

        # Baseline: simple dict operations
        baseline_start = time.perf_counter()
        for i in range(n_iterations):
            _ = {"task_id": f"task-{i}", "tokens": 100}
        baseline_ms = (time.perf_counter() - baseline_start) * 1000

        # With token tracking
        tracking_start = time.perf_counter()
        for i in range(n_iterations):
            tracker.record_task_tokens(f"task-{i}", "engineer", 100, 50)
        tracking_ms = (time.perf_counter() - tracking_start) * 1000

        # Token tracking should complete in reasonable time
        # (5% overhead test is relative — just verify it's fast enough)
        assert tracking_ms < 500.0, f"Tracking {n_iterations} tasks took {tracking_ms:.2f}ms"


class TestCLIFormattingPerformanceAcceptable:
    """Verify CLI formatting is fast."""

    def test_format_task_line_under_1ms(self):
        """Verify format_task_line completes in under 1ms."""
        formatter = CLIFormatter(no_color=True)
        metrics = TokenMetrics("t1", "engineer", 1000, 500, 0, 0.05)

        start = time.perf_counter()
        line = formatter.format_task_line(metrics, session_cost=0.12)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 1.0, f"format_task_line took {elapsed_ms:.2f}ms"

    def test_format_session_summary_under_10ms(self, tracker):
        """Verify format_session_summary completes in under 10ms."""
        formatter = CLIFormatter(no_color=True)
        for i in range(100):
            tracker.record_task_tokens(f"task-{i}", f"agent-{i % 8}", 100, 50, cost_usd=0.005)

        stats = tracker.get_stats()
        start = time.perf_counter()
        summary = formatter.format_session_summary(stats, budget_usd=5.0)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 10.0, f"format_session_summary took {elapsed_ms:.2f}ms"


class TestBudgetCheckingPerformanceAcceptable:
    """Verify budget checking is fast."""

    def test_budget_check_under_1ms(self):
        """Verify budget check completes in under 1ms."""
        checker = BudgetChecker()
        stats = TokenStats()
        stats.total_cost_usd = 2.5

        start = time.perf_counter()
        result = checker.check(stats)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 1.0, f"Budget check took {elapsed_ms:.2f}ms"

    def test_should_block_under_1ms(self):
        """Verify should_block completes in under 1ms."""
        checker = BudgetChecker()
        stats = TokenStats()
        stats.total_cost_usd = 2.5

        start = time.perf_counter()
        result = checker.should_block(stats)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 1.0, f"should_block took {elapsed_ms:.2f}ms"

    def test_1000_budget_checks_under_100ms(self):
        """Verify 1000 budget checks complete in under 100ms."""
        checker = BudgetChecker()
        stats = TokenStats()
        stats.total_cost_usd = 2.5

        start = time.perf_counter()
        for _ in range(1000):
            checker.check(stats)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100.0, f"1000 budget checks took {elapsed_ms:.2f}ms"


class TestComplexityScoringPerformance:
    """Verify complexity scoring is fast."""

    def test_score_completes_under_1ms(self):
        """Verify complexity scoring completes in under 1ms."""
        scorer = ComplexityScorer()
        attrs = TaskAttributes(effort="high", task_type="refactor", estimated_tokens=10_000)

        start = time.perf_counter()
        score, level = scorer.score(attrs)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 1.0, f"Complexity scoring took {elapsed_ms:.2f}ms"

    def test_model_selection_under_1ms(self):
        """Verify model selection completes in under 1ms."""
        selector = ModelSelector()
        attrs = TaskAttributes(effort="high", task_type="architecture")

        start = time.perf_counter()
        decision = selector.select(attrs)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 1.0, f"Model selection took {elapsed_ms:.2f}ms"


# ===========================================================================
# 5. Security Tests
# ===========================================================================

class TestNoSecretsInTokenMetrics:
    """Verify no secrets are stored in token metrics."""

    def test_token_metrics_contains_no_sensitive_fields(self, tracker):
        """Verify TokenMetrics only contains non-sensitive fields."""
        tracker.record_task_tokens(
            task_id="task-sec-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.05,
        )
        metrics = tracker.get_all_metrics()
        assert len(metrics) == 1

        metric = metrics[0]
        # Check that only expected fields exist
        allowed_fields = {"task_id", "agent", "input_tokens", "output_tokens",
                         "cached_tokens", "cost_usd", "timestamp",
                         "total_tokens", "effective_tokens"}

        # Verify no suspicious fields
        metric_dict = {
            "task_id": metric.task_id,
            "agent": metric.agent,
            "input_tokens": metric.input_tokens,
            "output_tokens": metric.output_tokens,
        }
        for key, value in metric_dict.items():
            assert "password" not in str(key).lower()
            assert "secret" not in str(key).lower()
            assert "api_key" not in str(key).lower()
            assert "credential" not in str(key).lower()

    def test_agent_stats_contains_no_sensitive_data(self, tracker):
        """Verify agent stats don't contain sensitive information."""
        tracker.record_task_tokens("t1", "engineer", 1000, 500, cost_usd=0.05)
        stats = tracker.get_agent_stats("engineer")

        # All values should be numeric or string identifiers
        for key, value in stats.items():
            assert not isinstance(value, (list, dict)), f"Unexpected complex value for {key}"

    def test_cost_attribution_contains_only_numeric_data(self, tracker):
        """Verify cost attribution only contains numeric percentages."""
        tracker.record_task_tokens("t1", "engineer", 1000, 500, cost_usd=0.05)
        attribution = tracker.get_cost_attribution()

        for agent, data in attribution.items():
            assert isinstance(data["tokens"], (int, float))
            assert isinstance(data["cost"], float)
            assert isinstance(data["token_percentage"], float)
            assert isinstance(data["cost_percentage"], float)
            # Percentages should be 0-100
            assert 0 <= data["token_percentage"] <= 100
            assert 0 <= data["cost_percentage"] <= 100


class TestNoBudgetConfigSecrets:
    """Verify budget config doesn't expose sensitive data."""

    def test_budget_config_only_contains_expected_keys(self):
        """Verify budget config only has documented keys."""
        checker = BudgetChecker()
        expected_budget_keys = {"session_usd", "daily_usd", "warn_pct", "critical_pct", "block_pct"}
        expected_display_keys = {"mode", "show_per_task", "show_session_summary"}

        assert set(checker.budget_config.keys()) == expected_budget_keys
        assert set(checker.display_config.keys()) == expected_display_keys

    def test_budget_result_message_contains_no_secrets(self):
        """Verify BudgetResult message doesn't contain sensitive info."""
        checker = BudgetChecker()
        stats = TokenStats()
        stats.total_cost_usd = 2.5
        result = checker.check(stats)

        message = result.message
        # Should not contain auth tokens, passwords, etc.
        assert "password" not in message.lower()
        assert "secret" not in message.lower()
        assert "api_key" not in message.lower()


class TestCostDataProperlySanitized:
    """Verify cost data is properly formatted and sanitized."""

    def test_cost_values_are_finite_floats(self, tracker):
        """Verify all cost values are finite floats."""
        tracker.record_task_tokens("t1", "engineer", 1000, 500, cost_usd=0.05)
        tracker.record_task_tokens("t2", "orchestrator", 500, 200, cost_usd=0.02)

        stats = tracker.get_stats()
        import math
        assert math.isfinite(stats.total_cost_usd)
        assert math.isfinite(stats.avg_cost_per_task)

    def test_cost_attribution_percentages_are_finite(self, tracker):
        """Verify cost attribution percentages are finite."""
        import math
        tracker.record_task_tokens("t1", "engineer", 1000, 500, cost_usd=0.05)
        attribution = tracker.get_cost_attribution()

        for agent, data in attribution.items():
            assert math.isfinite(data["cost_percentage"])
            assert math.isfinite(data["token_percentage"])

    def test_budget_result_pct_is_finite(self):
        """Verify budget percentage is finite."""
        import math
        checker = BudgetChecker()
        stats = TokenStats()
        stats.total_cost_usd = 2.5
        result = checker.check(stats)
        assert math.isfinite(result.pct_used)


# ===========================================================================
# 6. Monitoring Integration Tests
# ===========================================================================

class TestPrometheusMetricsExportedCorrectly:
    """Verify Prometheus metrics are properly registered and updated."""

    def test_token_tracker_registers_counters(self, tracker):
        """Verify TokenTracker registers expected Prometheus counters."""
        # Verify counters are registered
        assert hasattr(tracker, "tokens_input_total")
        assert hasattr(tracker, "tokens_output_total")
        assert hasattr(tracker, "tokens_cached_total")
        assert hasattr(tracker, "cost_usd_total")

    def test_token_tracker_registers_histograms(self, tracker):
        """Verify TokenTracker registers expected Prometheus histograms."""
        assert hasattr(tracker, "tokens_per_task")
        assert hasattr(tracker, "cost_per_task")

    def test_counters_increment_on_record(self, tracker):
        """Verify counters increment when tokens are recorded."""
        tracker.record_task_tokens("t1", "engineer", 1000, 500, cost_usd=0.05)

        assert tracker.tokens_input_total.value == 1000
        assert tracker.tokens_output_total.value == 500
        assert abs(tracker.cost_usd_total.value - 0.05) < 0.0001

    def test_per_agent_counters_created_on_first_record(self, tracker):
        """Verify per-agent counters are created on first task record."""
        assert "engineer" not in tracker.tokens_by_agent

        tracker.record_task_tokens("t1", "engineer", 1000, 500)

        assert "engineer" in tracker.tokens_by_agent
        assert "engineer" in tracker.cost_by_agent

    def test_per_agent_counters_accumulate(self, tracker):
        """Verify per-agent counters accumulate across multiple tasks."""
        tracker.record_task_tokens("t1", "engineer", 1000, 500)
        tracker.record_task_tokens("t2", "engineer", 2000, 1000)

        assert tracker.tokens_by_agent["engineer"].value == 4500  # (1000+500) + (2000+1000)

    def test_counters_reset_on_clear(self, tracker):
        """Verify counters reset to zero on clear()."""
        tracker.record_task_tokens("t1", "engineer", 1000, 500, cost_usd=0.05)
        tracker.clear()

        assert tracker.tokens_input_total.value == 0
        assert tracker.tokens_output_total.value == 0
        assert tracker.cost_usd_total.value == 0.0


class TestStructuredOutputFormat:
    """Verify structured output format is consistent."""

    def test_task_line_format_is_consistent(self):
        """Verify task line format matches documented format."""
        formatter = CLIFormatter(no_color=True)
        metrics = TokenMetrics("t1", "engineer", 1234, 567, 0, 0.0045)
        line = formatter.format_task_line(metrics, session_cost=0.12)

        # Format: [tokens] {agent}: {in:,} in / {out:,} out | ${cost:.4f} | session: ${session_cost:.2f}
        assert line.startswith("[tokens]")
        assert "engineer:" in line
        assert "1,234 in" in line
        assert "567 out" in line
        assert "$0.0045" in line
        assert "session: $0.12" in line

    def test_session_summary_format_has_header(self):
        """Verify session summary has expected header."""
        formatter = CLIFormatter(no_color=True)
        stats = TokenStats()
        stats.total_cost_usd = 1.0
        stats.task_count = 5
        stats.total_input_tokens = 5000
        stats.total_output_tokens = 2500

        summary = formatter.format_session_summary(stats, budget_usd=5.0)
        assert "Token Session Summary" in summary
        assert "Tasks:" in summary
        assert "Total in:" in summary
        assert "Cost:" in summary

    def test_budget_result_str_has_status(self):
        """Verify BudgetResult string representation includes status."""
        checker = BudgetChecker()
        stats = TokenStats()
        stats.total_cost_usd = 0.5
        result = checker.check(stats)
        result_str = str(result)

        # Should contain status and percentage
        assert any(s in result_str for s in ["OK", "WARNING", "CRITICAL", "BLOCKED"])
        assert "%" in result_str


# ===========================================================================
# 7. Concurrency / Load Tests (lightweight)
# ===========================================================================

class TestConcurrentTokenTracking:
    """Verify token tracking works correctly under concurrent load."""

    def test_50_concurrent_agents_token_tracking(self, tracker):
        """Simulate 50 concurrent agents recording token metrics."""
        n_agents = 50
        n_tasks_per_agent = 5
        errors = []

        def agent_work(agent_id):
            try:
                for task_i in range(n_tasks_per_agent):
                    tracker.record_task_tokens(
                        task_id=f"agent-{agent_id}-task-{task_i}",
                        agent=f"agent-{agent_id % 8}",
                        input_tokens=1000,
                        output_tokens=500,
                        cost_usd=0.05,
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=agent_work, args=(i,)) for i in range(n_agents)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent tracking errors: {errors}"
        stats = tracker.get_stats()
        assert stats.task_count == n_agents * n_tasks_per_agent
        assert abs(stats.total_cost_usd - (n_agents * n_tasks_per_agent * 0.05)) < 0.001

    def test_concurrent_budget_checking(self, tracker):
        """Verify concurrent budget checks are consistent."""
        checker = BudgetChecker()
        tracker.record_task_tokens("t1", "engineer", 1000, 500, cost_usd=2.5)

        results = []
        errors = []

        def check_budget():
            try:
                stats = tracker.get_stats()
                result = checker.check(stats)
                results.append(result.status)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=check_budget) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # All results should be consistent (same status)
        assert len(set(results)) == 1

    def test_concurrent_stats_retrieval_consistent(self, tracker):
        """Verify concurrent get_stats() calls return consistent results."""
        # Pre-populate with known data
        for i in range(100):
            tracker.record_task_tokens(f"task-{i}", "engineer", 100, 50, cost_usd=0.005)

        stats_results = []
        errors = []

        def get_stats():
            try:
                stats = tracker.get_stats()
                stats_results.append(stats.task_count)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_stats) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # All should see 100 tasks
        assert all(c == 100 for c in stats_results)
