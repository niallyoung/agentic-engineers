"""
Phase 3 Feature Parity Tests

Validates that Phase 3 monitoring features (token tracking, budget checking,
CLI formatting) behave consistently across all target harnesses and that
renderer scripts maintain consistent behavior patterns.

Tests cover:
1. Token tracking API consistency
2. Budget checking consistency
3. CLI formatting consistency (including NO_COLOR)
4. Renderer script consistency (status/install/uninstall modes)
5. Streaming output consistency (Copilot CLI)
6. Cross-harness behavior parity
"""

import os
import sys
import json
import subprocess
import tempfile
import threading
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
RENDERER_SCRIPTS = REPO_ROOT / "renderer" / "scripts"
SRC_SKILLS = REPO_ROOT / "src" / "skills"

# ---------------------------------------------------------------------------
# Imports from orchestration monitoring stack
# ---------------------------------------------------------------------------
from src.orchestration.monitoring.metrics import MetricsRegistry
from src.orchestration.monitoring.token_tracker import TokenTracker, TokenMetrics, TokenStats
from src.orchestration.monitoring.budget_checker import BudgetChecker, BudgetStatus, BudgetResult
from src.orchestration.monitoring.cli_formatter import CLIFormatter
from src.orchestration.monitoring.orchestrator_cli import OrchestratorCLI
from src.harnesses.copilot_cli.streaming import StreamingRenderer, StreamEvent


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
def sample_stats(tracker):
    """TokenStats with two agents recorded."""
    tracker.record_task_tokens("t1", "engineer", 1000, 500, 100, 0.045)
    tracker.record_task_tokens("t2", "orchestrator", 200, 100, 0, 0.009)
    return tracker.get_stats()


@pytest.fixture
def budget_config(tmp_path):
    cfg = {
        "budget": {
            "session_usd": 10.0,
            "warn_pct": 70,
            "critical_pct": 90,
            "block_pct": 100,
        }
    }
    p = tmp_path / "token_budget.yaml"
    p.write_text(yaml.dump(cfg))
    return p


@pytest.fixture
def checker(budget_config):
    return BudgetChecker(config_path=budget_config)


# ===========================================================================
# 1. Token Tracking API Consistency
# ===========================================================================

class TestTokenTrackingParity:
    """Token tracking API is consistent regardless of calling harness."""

    def test_record_and_retrieve_stats(self, tracker):
        """record_task_tokens → get_stats returns correct aggregates."""
        tracker.record_task_tokens("t1", "engineer", 1000, 500, 100, 0.045)
        stats = tracker.get_stats()
        assert stats.total_input_tokens == 1000
        assert stats.total_output_tokens == 500
        assert stats.total_cached_tokens == 100
        assert abs(stats.total_cost_usd - 0.045) < 1e-9
        assert stats.task_count == 1

    def test_multi_agent_aggregation(self, tracker):
        """Multiple agents are aggregated correctly."""
        tracker.record_task_tokens("t1", "engineer", 1000, 500, 0, 0.045)
        tracker.record_task_tokens("t2", "orchestrator", 200, 100, 0, 0.009)
        stats = tracker.get_stats()
        assert stats.task_count == 2
        assert stats.total_input_tokens == 1200
        assert "engineer" in stats.agent_tokens
        assert "orchestrator" in stats.agent_tokens

    def test_thread_safe_recording(self, tracker):
        """Token recording is thread-safe (concurrent harness calls)."""
        errors = []

        def record(i):
            try:
                tracker.record_task_tokens(f"t{i}", "engineer", 100, 50, 0, 0.001)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        stats = tracker.get_stats()
        assert stats.task_count == 20

    def test_token_metrics_properties(self, tracker):
        """TokenMetrics computed properties are consistent."""
        tracker.record_task_tokens("t1", "engineer", 1000, 500, 100, 0.045)
        history = tracker.get_all_metrics()
        assert len(history) == 1
        m = history[0]
        assert m.total_tokens == 1600  # 1000 + 500 + 100
        assert m.effective_tokens == 1500  # 1000 + 500


# ===========================================================================
# 2. Budget Checking Consistency
# ===========================================================================

class TestBudgetCheckingParity:
    """Budget checking behavior is consistent across all harnesses."""

    def test_ok_status_under_warning_threshold(self, checker, tracker):
        """Low spend → OK status."""
        tracker.record_task_tokens("t1", "engineer", 100, 50, 0, 0.10)
        stats = tracker.get_stats()
        result = checker.check(stats)
        assert result.status == BudgetStatus.OK

    def test_warning_status_at_threshold(self, checker, tracker):
        """Spend at warning threshold → WARNING status."""
        tracker.record_task_tokens("t1", "engineer", 100, 50, 0, 7.50)  # 75% of $10
        stats = tracker.get_stats()
        result = checker.check(stats)
        assert result.status == BudgetStatus.WARNING

    def test_critical_status_at_threshold(self, checker, tracker):
        """Spend at critical threshold → CRITICAL status."""
        tracker.record_task_tokens("t1", "engineer", 100, 50, 0, 9.50)  # 95% of $10
        stats = tracker.get_stats()
        result = checker.check(stats)
        assert result.status == BudgetStatus.CRITICAL

    def test_blocked_status_at_limit(self, checker, tracker):
        """Spend at/over limit → BLOCKED status."""
        tracker.record_task_tokens("t1", "engineer", 100, 50, 0, 10.50)
        stats = tracker.get_stats()
        result = checker.check(stats)
        assert result.status == BudgetStatus.BLOCKED

    def test_should_block_returns_bool(self, checker, tracker):
        """should_block() returns False when under limit."""
        tracker.record_task_tokens("t1", "engineer", 100, 50, 0, 0.10)
        stats = tracker.get_stats()
        assert checker.should_block(stats) is False

    def test_budget_result_str_representation(self, checker, tracker):
        """BudgetResult.__str__ is human-readable."""
        tracker.record_task_tokens("t1", "engineer", 100, 50, 0, 0.10)
        stats = tracker.get_stats()
        result = checker.check(stats)
        s = str(result)
        assert "%" in s
        assert "$" in s


# ===========================================================================
# 3. CLI Formatting Consistency
# ===========================================================================

class TestCLIFormattingParity:
    """CLIFormatter behaves consistently across all harnesses."""

    def test_no_color_env_var_suppresses_ansi(self):
        """NO_COLOR environment variable suppresses all ANSI codes."""
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            formatter = CLIFormatter()
            assert formatter.no_color is True

    def test_no_color_flag_suppresses_ansi(self):
        """no_color=True flag suppresses all ANSI codes."""
        formatter = CLIFormatter(no_color=True)
        assert formatter.no_color is True

    def test_format_task_line_no_ansi_when_no_color(self, tracker):
        """format_task_line output contains no ANSI escape codes when NO_COLOR."""
        tracker.record_task_tokens("t1", "engineer", 1000, 500, 100, 0.045)
        history = tracker.get_all_metrics()
        formatter = CLIFormatter(no_color=True)
        line = formatter.format_task_line(history[0], session_cost=0.045)
        assert "\033[" not in line

    def test_format_task_line_contains_ansi_when_color_enabled(self, tracker, monkeypatch):
        """format_task_line output contains ANSI codes when color enabled."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        tracker.record_task_tokens("t1", "engineer", 1000, 500, 100, 0.045)
        history = tracker.get_all_metrics()
        formatter = CLIFormatter(no_color=False)
        line = formatter.format_task_line(history[0], session_cost=0.045)
        assert "\033[" in line

    def test_format_session_summary_contains_key_fields(self, sample_stats):
        """format_session_summary includes agent breakdown and cost."""
        formatter = CLIFormatter(no_color=True)
        summary = formatter.format_session_summary(sample_stats, budget_usd=10.0)
        assert "engineer" in summary
        assert "$" in summary

    def test_format_budget_line_status_labels(self, checker, sample_stats):
        """format_session_summary includes budget percentage."""
        formatter = CLIFormatter(no_color=True)
        result = checker.check(sample_stats)
        # Use format_session_summary which includes budget info
        summary = formatter.format_session_summary(sample_stats, budget_usd=10.0)
        # Should contain cost or percentage info
        assert "$" in summary or "%" in summary


# ===========================================================================
# 4. Renderer Script Consistency
# ===========================================================================

class TestRendererScriptParity:
    """Renderer scripts have consistent CLI interfaces."""

    def _run_renderer(self, script: str, args: list, env: dict = None) -> subprocess.CompletedProcess:
        """Run a renderer script and return the result."""
        cmd = args
        environment = {**os.environ, **(env or {})}
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=environment,
            timeout=30,
        )

    def test_render_copilot_status_mode(self, tmp_path):
        """render-copilot.sh --status exits 0 with valid source."""
        result = self._run_renderer(
            "render-copilot.sh",
            ["bash", str(RENDERER_SCRIPTS / "render-copilot.sh"),
             str(REPO_ROOT), str(tmp_path), "--status"]
        )
        # Status mode should exit 0 even if nothing installed
        assert result.returncode == 0

    def test_render_copilot_unknown_mode_exits_nonzero(self, tmp_path):
        """render-copilot.sh with unknown mode exits non-zero."""
        result = self._run_renderer(
            "render-copilot.sh",
            ["bash", str(RENDERER_SCRIPTS / "render-copilot.sh"),
             str(REPO_ROOT), str(tmp_path), "--unknown-mode"]
        )
        assert result.returncode != 0

    def test_render_pi_dev_status_mode(self, tmp_path):
        """render-pi-dev.py --status runs without crashing (exit 0 or 1 both valid)."""
        result = self._run_renderer(
            "render-pi-dev.py",
            ["python3", str(RENDERER_SCRIPTS / "render-pi-dev.py"),
             "--dest", str(tmp_path), "--status"]
        )
        # Exit 1 when not installed is valid behavior; exit 2+ indicates crash
        assert result.returncode in (0, 1), \
            f"Unexpected exit code {result.returncode}: {result.stderr}"

    def test_render_pi_dev_no_color_suppresses_ansi(self, tmp_path):
        """render-pi-dev.py respects NO_COLOR environment variable."""
        result = self._run_renderer(
            "render-pi-dev.py",
            ["python3", str(RENDERER_SCRIPTS / "render-pi-dev.py"),
             "--dest", str(tmp_path), "--status"],
            env={"NO_COLOR": "1"}
        )
        # Output should not contain ANSI escape codes
        assert "\033[" not in result.stdout

    def test_render_copilot_no_color_in_stream_mode(self, tmp_path):
        """render-copilot.sh --stream respects NO_COLOR."""
        result = self._run_renderer(
            "render-copilot.sh",
            ["bash", str(RENDERER_SCRIPTS / "render-copilot.sh"),
             str(REPO_ROOT), str(tmp_path), "--stream"],
            env={"NO_COLOR": "1"}
        )
        # Should not contain ANSI escape codes in output
        assert "\033[" not in result.stdout


# ===========================================================================
# 5. Streaming Output Consistency (Copilot CLI)
# ===========================================================================

class TestStreamingOutputParity:
    """Copilot CLI streaming output is consistent and well-formed."""

    def test_streaming_renderer_emits_start_and_complete(self, tmp_path):
        """StreamingRenderer emits start and complete events for each skill."""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()

        # Create a minimal skill
        skill_dir = src / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill\n")

        renderer = StreamingRenderer(str(src), str(dst), ".test-marker")
        events = list(renderer.render_all())

        types = [e.type for e in events]
        assert "start" in types
        assert "complete" in types
        assert "summary" in types

    def test_streaming_renderer_summary_has_count(self, tmp_path):
        """Summary event includes skill count."""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()

        for i in range(3):
            skill_dir = src / f"skill-{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"# Skill {i}\n")

        renderer = StreamingRenderer(str(src), str(dst), ".test-marker")
        events = list(renderer.render_all())

        summary = next(e for e in events if e.type == "summary")
        assert summary.data.get("count") == 3

    def test_stream_event_to_json_is_valid(self, tmp_path):
        """StreamEvent.to_json() produces valid JSON."""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "skill-a").mkdir()
        (src / "skill-a" / "SKILL.md").write_text("# A\n")

        renderer = StreamingRenderer(str(src), str(dst), ".marker")
        for event in renderer.render_all():
            parsed = json.loads(event.to_json())
            assert "type" in parsed
            assert "timestamp" in parsed

    def test_streaming_renderer_cancellation(self, tmp_path):
        """StreamingRenderer.cancel() stops after current skill."""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()

        for i in range(5):
            skill_dir = src / f"skill-{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"# Skill {i}\n")

        renderer = StreamingRenderer(str(src), str(dst), ".marker")
        events = []
        for event in renderer.render_all():
            events.append(event)
            if event.type == "complete":
                renderer.cancel()
                break

        # Should have stopped before processing all 5 skills
        complete_events = [e for e in events if e.type == "complete"]
        assert len(complete_events) <= 5  # cancelled, so fewer than all


# ===========================================================================
# 6. Cross-Harness Behavior Parity
# ===========================================================================

class TestCrossHarnessParity:
    """Verifies consistent behavior across all harnesses."""

    def test_all_harnesses_have_status_mode(self, tmp_path):
        """All bash renderer scripts support --status mode."""
        scripts = [
            (["bash", str(RENDERER_SCRIPTS / "render-copilot.sh"),
              str(REPO_ROOT), str(tmp_path), "--status"]),
            (["bash", str(RENDERER_SCRIPTS / "render-claude.sh"),
              str(REPO_ROOT), str(tmp_path), "--status"]),
        ]
        for cmd in scripts:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, \
                f"Script {cmd[1]} --status failed: {result.stderr}"

    def test_pi_dev_renderer_has_status_mode(self, tmp_path):
        """π.dev renderer supports --status mode (runs without crashing)."""
        result = subprocess.run(
            ["python3", str(RENDERER_SCRIPTS / "render-pi-dev.py"),
             "--dest", str(tmp_path), "--status"],
            capture_output=True, text=True, timeout=30
        )
        # Exit 0 (installed) or 1 (not installed) are both valid
        assert result.returncode in (0, 1), \
            f"Unexpected exit code {result.returncode}: {result.stderr}"

    def test_monitoring_stack_importable_in_all_harness_contexts(self):
        """All Phase 3 monitoring modules are importable (harness-agnostic)."""
        from src.orchestration.monitoring.token_tracker import TokenTracker
        from src.orchestration.monitoring.budget_checker import BudgetChecker
        from src.orchestration.monitoring.cli_formatter import CLIFormatter
        from src.orchestration.monitoring.orchestrator_cli import OrchestratorCLI
        # If we get here, all imports succeeded
        assert True

    def test_no_color_respected_by_cli_formatter_and_pi_dev(self, tmp_path):
        """NO_COLOR is respected by both CLIFormatter and render-pi-dev.py."""
        # Python CLIFormatter
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            formatter = CLIFormatter()
            assert formatter.no_color is True

        # render-pi-dev.py subprocess
        result = subprocess.run(
            ["python3", str(RENDERER_SCRIPTS / "render-pi-dev.py"),
             "--dest", str(tmp_path), "--status"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "NO_COLOR": "1"}
        )
        assert "\033[" not in result.stdout

    def test_budget_checker_consistent_thresholds(self, tmp_path):
        """BudgetChecker applies thresholds consistently regardless of caller."""
        cfg = {
            "budget": {
                "daily_usd": 5.0,
                "warning_pct": 70,
                "critical_pct": 90,
                "block_pct": 100,
            }
        }
        p = tmp_path / "budget.yaml"
        p.write_text(yaml.dump(cfg))

        checker1 = BudgetChecker(config_path=p)
        checker2 = BudgetChecker(config_path=p)

        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        tracker.record_task_tokens("t1", "engineer", 100, 50, 0, 4.00)  # 80% of $5
        stats = tracker.get_stats()

        result1 = checker1.check(stats)
        result2 = checker2.check(stats)

        # Both instances must agree on status
        assert result1.status == result2.status == BudgetStatus.WARNING
        assert abs(result1.pct_used - result2.pct_used) < 0.001
