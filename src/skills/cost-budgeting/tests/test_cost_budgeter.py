"""
Tests for cost-budgeting skill (COST-001).

Coverage:
  - Session budget enforcement (can't exceed session cap)
  - Hourly budget enforcement (rolling hour tracking)
  - Daily budget enforcement (calendar day)
  - Provider cost calculation (different rates per provider)
  - Alert thresholds (50/75/90/100% alerts)
  - Graceful degradation (warn→block progression)
  - Multi-day rollover (budget resets correctly)
  - Concurrent sessions (independent budgets)
  - Edge cases: zero spend, exact limit, negative amounts
  - Data model validation
  - Persistence (save/load round-trip)
  - Fallback rates for unknown providers/models
"""

from __future__ import annotations

import json
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

# Bootstrap import path so tests can import from scripts/
_SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SKILL_ROOT))

from scripts.cost_budgeter import (
    CostBudget,
    CostBudgeter,
    VALID_GRANULARITIES,
    DEFAULT_ALERT_THRESHOLDS,
    FALLBACK_COST_RATES,
    _is_expired,
    _window_start,
    _utcnow,
)


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture()
def costs_dir(tmp_path: Path) -> Path:
    """Isolated costs directory for each test."""
    d = tmp_path / "costs"
    d.mkdir()
    return d


@pytest.fixture()
def models_yaml(tmp_path: Path) -> Path:
    """Minimal models.yaml with known cost data for deterministic tests."""
    content = """
providers:
  anthropic:
    claude-haiku:
      input: 0.00008
      output: 0.00024
    claude-sonnet:
      input: 0.003
      output: 0.015
    claude-opus:
      input: 0.015
      output: 0.075
  openai:
    gpt-4o-mini:
      input: 0.00015
      output: 0.0006
    gpt-4o:
      input: 0.0025
      output: 0.01
    gpt-4:
      input: 0.01
      output: 0.03
  google:
    gemini-flash:
      input: 0.000075
      output: 0.0003
    gemini-pro:
      input: 0.00125
      output: 0.005
  github_copilot:
    gpt-4o-mini:
      input: 0.00015
      output: 0.0006
    gpt-4o:
      input: 0.0025
      output: 0.01
    gpt-4:
      input: 0.01
      output: 0.03
"""
    p = tmp_path / "models.yaml"
    p.write_text(content)
    return p


@pytest.fixture()
def budgeter(costs_dir: Path, models_yaml: Path) -> CostBudgeter:
    """CostBudgeter instance backed by tmp directories."""
    return CostBudgeter(costs_dir=costs_dir, models_yaml=models_yaml)


# ===========================================================================
# CostBudget data model
# ===========================================================================

class TestCostBudgetDataModel:
    """Test CostBudget dataclass validation and computed properties."""

    def test_valid_budget_creation(self):
        """CostBudget with valid fields creates without error."""
        b = CostBudget(
            session_id="test-session",
            granularity="session",
            limit_usd=5.0,
        )
        assert b.session_id == "test-session"
        assert b.granularity == "session"
        assert b.limit_usd == 5.0
        assert b.current_spend == 0.0
        assert b.alert_thresholds == DEFAULT_ALERT_THRESHOLDS
        assert b.hard_limit_action == "block"
        assert b.period_start  # auto-populated

    def test_invalid_granularity_raises(self):
        """Unknown granularity raises ValueError."""
        with pytest.raises(ValueError, match="granularity"):
            CostBudget(session_id="s", granularity="quarterly", limit_usd=10.0)

    def test_non_positive_limit_raises(self):
        """Zero or negative limit raises ValueError."""
        with pytest.raises(ValueError, match="limit_usd"):
            CostBudget(session_id="s", granularity="session", limit_usd=0.0)
        with pytest.raises(ValueError, match="limit_usd"):
            CostBudget(session_id="s", granularity="session", limit_usd=-1.0)

    def test_invalid_hard_limit_action_raises(self):
        """Unknown hard_limit_action raises ValueError."""
        with pytest.raises(ValueError, match="hard_limit_action"):
            CostBudget(
                session_id="s", granularity="session", limit_usd=5.0,
                hard_limit_action="ignore",
            )

    def test_spend_percent_zero_spend(self):
        """spend_percent is 0% when nothing spent."""
        b = CostBudget(session_id="s", granularity="day", limit_usd=10.0)
        assert b.spend_percent == 0.0

    def test_spend_percent_half(self):
        """spend_percent is 50% at half the limit."""
        b = CostBudget(session_id="s", granularity="day", limit_usd=10.0, current_spend=5.0)
        assert b.spend_percent == pytest.approx(50.0)

    def test_spend_percent_over_limit(self):
        """spend_percent can exceed 100%."""
        b = CostBudget(session_id="s", granularity="session", limit_usd=5.0, current_spend=6.0)
        assert b.spend_percent > 100.0

    def test_remaining_usd(self):
        """remaining_usd = limit - spend."""
        b = CostBudget(session_id="s", granularity="session", limit_usd=5.0, current_spend=2.0)
        assert b.remaining_usd == pytest.approx(3.0)

    def test_is_over_limit(self):
        """is_over_limit is True when spend >= limit."""
        b = CostBudget(session_id="s", granularity="session", limit_usd=5.0, current_spend=5.0)
        assert b.is_over_limit is True

    def test_roundtrip_serialisation(self):
        """to_dict / from_dict round-trip preserves all fields."""
        b = CostBudget(
            session_id="round-trip",
            granularity="day",
            limit_usd=20.0,
            current_spend=7.5,
            alert_thresholds=[0.5, 0.75],
            hard_limit_action="warn",
            provider_splits={"anthropic": 6.0, "openai": 1.5},
            period_start="2026-06-01T00:00:00Z",
            alerts_fired=[0.5],
        )
        d = b.to_dict()
        b2 = CostBudget.from_dict(d)
        assert b2.session_id == b.session_id
        assert b2.granularity == b.granularity
        assert b2.current_spend == b.current_spend
        assert b2.provider_splits == b.provider_splits
        assert b2.alerts_fired == b.alerts_fired

    @pytest.mark.parametrize("gran", VALID_GRANULARITIES)
    def test_all_valid_granularities_accepted(self, gran):
        """All five granularities are accepted without error."""
        b = CostBudget(session_id="s", granularity=gran, limit_usd=1.0)
        assert b.granularity == gran


# ===========================================================================
# Session budget enforcement
# ===========================================================================

class TestSessionBudgetEnforcement:
    """Session budgets — can't exceed session cap."""

    def test_task_allowed_within_budget(self, budgeter):
        """Task is allowed when projected spend is within the session limit."""
        budgeter.get_budget("sess-A", "session", default_limit_usd=5.0)
        allowed = budgeter.enforce_budget("sess-A", task_cost=1.0, granularity="session")
        assert allowed is True

    def test_task_blocked_when_over_limit(self, budgeter):
        """Task is blocked when it would push spend over the session limit."""
        budgeter.get_budget("sess-B", "session", default_limit_usd=2.0)
        budgeter.record_spend("sess-B", 1.9, "session")
        # 1.9 + 0.5 = 2.4 > 2.0 → blocked
        allowed = budgeter.enforce_budget("sess-B", task_cost=0.5, granularity="session")
        assert allowed is False

    def test_task_allowed_at_exact_limit(self, budgeter):
        """Task that brings spend to exactly the limit is allowed."""
        budgeter.get_budget("sess-C", "session", default_limit_usd=3.0)
        budgeter.record_spend("sess-C", 2.5, "session")
        # 2.5 + 0.5 = 3.0 == 3.0 → allowed (projected does not *exceed* limit)
        allowed = budgeter.enforce_budget("sess-C", task_cost=0.5, granularity="session")
        assert allowed is True

    def test_zero_cost_task_always_allowed(self, budgeter):
        """Zero-cost task is always allowed, even at full limit."""
        budgeter.get_budget("sess-D", "session", default_limit_usd=1.0)
        budgeter.record_spend("sess-D", 1.0, "session")  # at limit
        allowed = budgeter.enforce_budget("sess-D", task_cost=0.0, granularity="session")
        assert allowed is True

    def test_negative_task_cost_raises(self, budgeter):
        """Negative task cost raises ValueError."""
        budgeter.get_budget("sess-E", "session", default_limit_usd=5.0)
        with pytest.raises(ValueError, match="non-negative"):
            budgeter.enforce_budget("sess-E", task_cost=-0.01, granularity="session")

    def test_warn_action_allows_overage(self, budgeter, costs_dir):
        """hard_limit_action='warn' allows tasks even over the limit."""
        b = CostBudget(
            session_id="sess-warn",
            granularity="session",
            limit_usd=1.0,
            current_spend=0.9,
            hard_limit_action="warn",
            period_start="2026-06-01T00:00:00Z",
        )
        (costs_dir / "sess-warn").mkdir(exist_ok=True)
        (costs_dir / "sess-warn" / "session.json").write_text(json.dumps(b.to_dict()))
        # 0.9 + 0.5 = 1.4 > 1.0, but action=warn → still True
        allowed = budgeter.enforce_budget("sess-warn", task_cost=0.5, granularity="session")
        assert allowed is True

    def test_escalate_action_blocks_overage(self, budgeter, costs_dir):
        """hard_limit_action='escalate' blocks tasks over the limit (same as block)."""
        b = CostBudget(
            session_id="sess-escalate",
            granularity="session",
            limit_usd=1.0,
            current_spend=0.9,
            hard_limit_action="escalate",
            period_start="2026-06-01T00:00:00Z",
        )
        (costs_dir / "sess-escalate").mkdir(exist_ok=True)
        (costs_dir / "sess-escalate" / "session.json").write_text(json.dumps(b.to_dict()))
        allowed = budgeter.enforce_budget("sess-escalate", task_cost=0.5, granularity="session")
        assert allowed is False

    def test_spend_not_recorded_by_enforce(self, budgeter):
        """enforce_budget() must NOT record spend; only check."""
        budgeter.get_budget("sess-F", "session", default_limit_usd=5.0)
        budgeter.enforce_budget("sess-F", task_cost=2.0, granularity="session")
        b = budgeter.get_budget("sess-F", "session")
        assert b.current_spend == 0.0  # unchanged


# ===========================================================================
# Hourly budget enforcement
# ===========================================================================

class TestHourlyBudgetEnforcement:
    """Rolling hour budget tracking."""

    def test_hourly_budget_created_fresh(self, budgeter):
        """Fresh hourly budget starts at zero spend."""
        b = budgeter.get_budget("sess-hour", "hour", default_limit_usd=1.0)
        assert b.current_spend == 0.0
        assert b.granularity == "hour"

    def test_hourly_task_blocked_over_limit(self, budgeter):
        """Hourly task blocked when over hour limit."""
        budgeter.get_budget("sess-hour2", "hour", default_limit_usd=0.50)
        budgeter.record_spend("sess-hour2", 0.45, "hour")
        allowed = budgeter.enforce_budget("sess-hour2", task_cost=0.10, granularity="hour")
        assert allowed is False

    def test_hourly_budget_expires_after_one_hour(self, budgeter, costs_dir):
        """Hourly budget resets when window is older than 1 hour."""
        old_start = (_utcnow() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        b = CostBudget(
            session_id="sess-hour-old",
            granularity="hour",
            limit_usd=1.0,
            current_spend=0.80,
            period_start=old_start,
        )
        (costs_dir / "sess-hour-old").mkdir(exist_ok=True)
        (costs_dir / "sess-hour-old" / "hour.json").write_text(json.dumps(b.to_dict()))

        reloaded = budgeter.get_budget("sess-hour-old", "hour")
        assert reloaded.current_spend == 0.0  # reset

    def test_hourly_budget_not_expired_within_window(self, budgeter, costs_dir):
        """Hourly budget does NOT reset if still within 1-hour window."""
        recent_start = (_utcnow() - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        b = CostBudget(
            session_id="sess-hour-recent",
            granularity="hour",
            limit_usd=1.0,
            current_spend=0.40,
            period_start=recent_start,
        )
        (costs_dir / "sess-hour-recent").mkdir(exist_ok=True)
        (costs_dir / "sess-hour-recent" / "hour.json").write_text(json.dumps(b.to_dict()))

        reloaded = budgeter.get_budget("sess-hour-recent", "hour")
        assert reloaded.current_spend == pytest.approx(0.40)  # NOT reset


# ===========================================================================
# Daily budget enforcement
# ===========================================================================

class TestDailyBudgetEnforcement:
    """Calendar-day budget enforcement."""

    def test_daily_budget_created_fresh(self, budgeter):
        """Fresh daily budget starts at zero spend."""
        b = budgeter.get_budget("sess-day", "day", default_limit_usd=10.0)
        assert b.current_spend == 0.0
        assert b.granularity == "day"

    def test_daily_task_within_limit_allowed(self, budgeter):
        """Daily task allowed when under limit."""
        budgeter.get_budget("sess-day2", "day", default_limit_usd=10.0)
        budgeter.record_spend("sess-day2", 5.0, "day")
        allowed = budgeter.enforce_budget("sess-day2", task_cost=4.0, granularity="day")
        assert allowed is True

    def test_daily_task_over_limit_blocked(self, budgeter):
        """Daily task blocked when it would exceed limit."""
        budgeter.get_budget("sess-day3", "day", default_limit_usd=10.0)
        budgeter.record_spend("sess-day3", 9.5, "day")
        allowed = budgeter.enforce_budget("sess-day3", task_cost=1.0, granularity="day")
        assert allowed is False

    def test_daily_budget_expires_after_one_day(self, budgeter, costs_dir):
        """Daily budget resets when window is older than 24 hours."""
        old_start = (_utcnow() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        b = CostBudget(
            session_id="sess-day-old",
            granularity="day",
            limit_usd=10.0,
            current_spend=8.0,
            period_start=old_start,
        )
        (costs_dir / "sess-day-old").mkdir(exist_ok=True)
        (costs_dir / "sess-day-old" / "day.json").write_text(json.dumps(b.to_dict()))

        reloaded = budgeter.get_budget("sess-day-old", "day")
        assert reloaded.current_spend == 0.0  # reset after day rollover


# ===========================================================================
# Provider cost calculation
# ===========================================================================

class TestProviderCostCalculation:
    """Different rates per provider/model — accurate to within 1%."""

    def test_anthropic_haiku_cost(self, budgeter):
        """claude-haiku: $0.00008 input + $0.00024 output per 1K tokens."""
        cost = budgeter.calculate_provider_cost(
            "anthropic",
            {"input": 10_000, "output": 3_000},
            "claude-haiku",
        )
        expected = (10_000 / 1000) * 0.00008 + (3_000 / 1000) * 0.00024
        assert cost == pytest.approx(expected, rel=0.01)

    def test_anthropic_sonnet_cost(self, budgeter):
        """claude-sonnet: $0.003 input + $0.015 output per 1K tokens."""
        cost = budgeter.calculate_provider_cost(
            "anthropic",
            {"input": 5_000, "output": 1_500},
            "claude-sonnet",
        )
        expected = (5_000 / 1000) * 0.003 + (1_500 / 1000) * 0.015
        assert cost == pytest.approx(expected, rel=0.01)

    def test_anthropic_opus_cost(self, budgeter):
        """claude-opus: $0.015 input + $0.075 output per 1K tokens."""
        cost = budgeter.calculate_provider_cost(
            "anthropic",
            {"input": 2_000, "output": 500},
            "claude-opus",
        )
        expected = (2_000 / 1000) * 0.015 + (500 / 1000) * 0.075
        assert cost == pytest.approx(expected, rel=0.01)

    def test_openai_gpt4o_mini_cost(self, budgeter):
        """gpt-4o-mini: $0.00015 input + $0.0006 output per 1K tokens."""
        cost = budgeter.calculate_provider_cost(
            "openai",
            {"input": 20_000, "output": 5_000},
            "gpt-4o-mini",
        )
        expected = (20_000 / 1000) * 0.00015 + (5_000 / 1000) * 0.0006
        assert cost == pytest.approx(expected, rel=0.01)

    def test_openai_gpt4o_cost(self, budgeter):
        """gpt-4o: $0.0025 input + $0.01 output per 1K tokens."""
        cost = budgeter.calculate_provider_cost(
            "openai",
            {"input": 8_000, "output": 2_000},
            "gpt-4o",
        )
        expected = (8_000 / 1000) * 0.0025 + (2_000 / 1000) * 0.01
        assert cost == pytest.approx(expected, rel=0.01)

    def test_google_gemini_flash_cost(self, budgeter):
        """gemini-flash: $0.000075 input + $0.0003 output per 1K tokens."""
        cost = budgeter.calculate_provider_cost(
            "google",
            {"input": 50_000, "output": 10_000},
            "gemini-flash",
        )
        expected = (50_000 / 1000) * 0.000075 + (10_000 / 1000) * 0.0003
        assert cost == pytest.approx(expected, rel=0.01)

    def test_github_copilot_gpt4o_cost(self, budgeter):
        """github_copilot/gpt-4o uses same rates as openai/gpt-4o."""
        cost_copilot = budgeter.calculate_provider_cost(
            "github_copilot",
            {"input": 10_000, "output": 2_000},
            "gpt-4o",
        )
        cost_openai = budgeter.calculate_provider_cost(
            "openai",
            {"input": 10_000, "output": 2_000},
            "gpt-4o",
        )
        assert cost_copilot == pytest.approx(cost_openai, rel=0.01)

    def test_sonnet_costs_more_than_haiku(self, budgeter):
        """Sonnet costs more than Haiku for identical token counts."""
        tokens = {"input": 10_000, "output": 3_000}
        haiku = budgeter.calculate_provider_cost("anthropic", tokens, "claude-haiku")
        sonnet = budgeter.calculate_provider_cost("anthropic", tokens, "claude-sonnet")
        assert sonnet > haiku

    def test_opus_costs_more_than_sonnet(self, budgeter):
        """Opus costs more than Sonnet for identical token counts."""
        tokens = {"input": 10_000, "output": 3_000}
        sonnet = budgeter.calculate_provider_cost("anthropic", tokens, "claude-sonnet")
        opus = budgeter.calculate_provider_cost("anthropic", tokens, "claude-opus")
        assert opus > sonnet

    def test_zero_tokens_zero_cost(self, budgeter):
        """Zero tokens produce zero cost."""
        cost = budgeter.calculate_provider_cost("anthropic", {"input": 0, "output": 0}, "claude-sonnet")
        assert cost == 0.0

    def test_input_only_tokens(self, budgeter):
        """Only input tokens charged correctly."""
        cost = budgeter.calculate_provider_cost("anthropic", {"input": 1_000}, "claude-sonnet")
        assert cost == pytest.approx(0.003, rel=0.01)

    def test_output_only_tokens(self, budgeter):
        """Only output tokens charged correctly."""
        cost = budgeter.calculate_provider_cost("anthropic", {"output": 1_000}, "claude-sonnet")
        assert cost == pytest.approx(0.015, rel=0.01)

    def test_negative_tokens_raises(self, budgeter):
        """Negative token counts raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            budgeter.calculate_provider_cost("anthropic", {"input": -100, "output": 0}, "claude-sonnet")

    def test_unknown_provider_uses_fallback(self, budgeter):
        """Unknown provider uses fallback rates without raising."""
        cost = budgeter.calculate_provider_cost(
            "unknown-provider",
            {"input": 1_000, "output": 0},
            "some-model",
        )
        expected = (1_000 / 1000) * FALLBACK_COST_RATES["input"]
        assert cost == pytest.approx(expected, rel=0.01)

    def test_unknown_model_uses_fallback(self, budgeter):
        """Unknown model for a known provider uses fallback rates without raising."""
        cost = budgeter.calculate_provider_cost(
            "anthropic",
            {"input": 1_000, "output": 0},
            "claude-ultra-9000",  # doesn't exist
        )
        # Should use fallback (gpt-4o rates)
        assert cost > 0.0

    def test_partial_model_name_match(self, budgeter):
        """Partial model name matches closest known model."""
        # 'claude-sonnet-4.6' should match 'claude-sonnet'
        cost = budgeter.calculate_provider_cost(
            "anthropic",
            {"input": 1_000, "output": 0},
            "claude-sonnet-4.6",
        )
        # Should match claude-sonnet rates: 1K input * $0.003
        assert cost == pytest.approx(0.003, rel=0.01)


# ===========================================================================
# Alert thresholds
# ===========================================================================

class TestAlertThresholds:
    """50/75/90/100% threshold alerts fire at correct spend levels."""

    def test_no_alert_below_50_percent(self, budgeter):
        """No alert when spend is below 50%."""
        budgeter.get_budget("sess-alert", "session", default_limit_usd=10.0)
        msg = budgeter.alert_at_threshold("sess-alert", current_spend=4.9, limit=10.0)
        assert msg == ""

    def test_alert_at_50_percent(self, budgeter):
        """Alert fires at exactly 50% spend."""
        budgeter.get_budget("sess-50", "session", default_limit_usd=10.0)
        msg = budgeter.alert_at_threshold("sess-50", current_spend=5.0, limit=10.0)
        assert "50%" in msg
        assert "sess-50" in msg

    def test_alert_at_75_percent(self, budgeter):
        """Alert fires at exactly 75% spend."""
        budgeter.get_budget("sess-75", "session", default_limit_usd=10.0)
        msg = budgeter.alert_at_threshold("sess-75", current_spend=7.5, limit=10.0)
        assert "75%" in msg

    def test_alert_at_90_percent(self, budgeter):
        """Alert fires at exactly 90% spend."""
        budgeter.get_budget("sess-90", "session", default_limit_usd=10.0)
        msg = budgeter.alert_at_threshold("sess-90", current_spend=9.0, limit=10.0)
        assert "90%" in msg

    def test_alert_at_100_percent(self, budgeter):
        """Alert fires at exactly 100% spend."""
        budgeter.get_budget("sess-100", "session", default_limit_usd=10.0)
        msg = budgeter.alert_at_threshold("sess-100", current_spend=10.0, limit=10.0)
        assert "100%" in msg

    def test_no_double_alert_for_same_threshold(self, budgeter):
        """Second call at same spend level does not fire duplicate alert."""
        budgeter.get_budget("sess-dedup", "session", default_limit_usd=10.0)
        msg1 = budgeter.alert_at_threshold("sess-dedup", current_spend=5.0, limit=10.0)
        msg2 = budgeter.alert_at_threshold("sess-dedup", current_spend=5.0, limit=10.0)
        assert msg1 != ""   # first fires
        assert msg2 == ""   # second suppressed

    def test_higher_threshold_takes_priority(self, budgeter):
        """When multiple thresholds crossed, highest fires first."""
        budgeter.get_budget("sess-multi", "session", default_limit_usd=10.0)
        # 8.0 / 10.0 = 80% → crosses both 50% and 75%
        msg = budgeter.alert_at_threshold("sess-multi", current_spend=8.0, limit=10.0)
        # Should fire 75% (highest crossed threshold not yet fired)
        assert "75%" in msg

    def test_subsequent_threshold_alert_fires(self, budgeter):
        """After 50% alert, 75% alert fires when spend rises further."""
        budgeter.get_budget("sess-seq", "session", default_limit_usd=10.0)
        budgeter.alert_at_threshold("sess-seq", current_spend=5.0, limit=10.0)  # fires 50%
        msg = budgeter.alert_at_threshold("sess-seq", current_spend=7.5, limit=10.0)
        assert "75%" in msg

    def test_alert_message_contains_dollar_amounts(self, budgeter):
        """Alert message includes spend and limit dollar amounts."""
        budgeter.get_budget("sess-amts", "session", default_limit_usd=20.0)
        msg = budgeter.alert_at_threshold("sess-amts", current_spend=10.0, limit=20.0)
        assert "$10.0" in msg or "10.0000" in msg
        assert "$20.0" in msg or "20.0000" in msg

    def test_alert_message_contains_level(self, budgeter):
        """Alert message includes degradation level."""
        budgeter.get_budget("sess-level", "session", default_limit_usd=10.0)
        msg = budgeter.alert_at_threshold("sess-level", current_spend=9.5, limit=10.0)
        assert "level=" in msg

    def test_zero_limit_returns_empty(self, budgeter):
        """Zero limit skips alert to avoid division by zero."""
        msg = budgeter.alert_at_threshold("sess-zero", current_spend=5.0, limit=0.0)
        assert msg == ""


# ===========================================================================
# Graceful degradation
# ===========================================================================

class TestGracefulDegradation:
    """Warn → block progression through degradation levels."""

    @pytest.mark.parametrize("pct,expected", [
        (0.0, "safe"),
        (25.0, "safe"),
        (49.9, "safe"),
        (50.0, "caution"),
        (60.0, "caution"),
        (74.9, "caution"),
        (75.0, "critical"),
        (82.0, "critical"),
        (89.9, "critical"),
        (90.0, "blocked"),
        (95.0, "blocked"),
        (100.0, "blocked"),
        (150.0, "blocked"),  # over 100% → still blocked
    ])
    def test_degradation_level(self, budgeter, pct, expected):
        """spend_percent → correct degradation level."""
        assert budgeter.graceful_degrade(pct) == expected

    def test_exact_boundary_50(self, budgeter):
        """50.0% is 'caution', not 'safe'."""
        assert budgeter.graceful_degrade(50.0) == "caution"

    def test_exact_boundary_75(self, budgeter):
        """75.0% is 'critical', not 'caution'."""
        assert budgeter.graceful_degrade(75.0) == "critical"

    def test_exact_boundary_90(self, budgeter):
        """90.0% is 'blocked', not 'critical'."""
        assert budgeter.graceful_degrade(90.0) == "blocked"


# ===========================================================================
# Multi-day rollover
# ===========================================================================

class TestMultiDayRollover:
    """Budget resets correctly when windows expire."""

    def test_day_budget_resets_on_new_day(self, budgeter, costs_dir):
        """Daily budget resets when period_start is more than 1 day ago."""
        old_start = (_utcnow() - timedelta(days=1, hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        b = CostBudget(
            session_id="sess-rollover",
            granularity="day",
            limit_usd=10.0,
            current_spend=8.5,
            period_start=old_start,
        )
        (costs_dir / "sess-rollover").mkdir(exist_ok=True)
        (costs_dir / "sess-rollover" / "day.json").write_text(json.dumps(b.to_dict()))

        reloaded = budgeter.get_budget("sess-rollover", "day")
        assert reloaded.current_spend == 0.0
        assert reloaded.limit_usd == 10.0  # limit preserved on reset

    def test_week_budget_resets_after_7_days(self, budgeter, costs_dir):
        """Weekly budget resets when period_start is more than 7 days ago."""
        old_start = (_utcnow() - timedelta(weeks=1, hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        b = CostBudget(
            session_id="sess-week-rollover",
            granularity="week",
            limit_usd=50.0,
            current_spend=35.0,
            period_start=old_start,
        )
        (costs_dir / "sess-week-rollover").mkdir(exist_ok=True)
        (costs_dir / "sess-week-rollover" / "week.json").write_text(json.dumps(b.to_dict()))

        reloaded = budgeter.get_budget("sess-week-rollover", "week")
        assert reloaded.current_spend == 0.0
        assert reloaded.limit_usd == 50.0

    def test_month_budget_resets_after_30_days(self, budgeter, costs_dir):
        """Monthly budget resets when period_start is more than 30 days ago."""
        old_start = (_utcnow() - timedelta(days=31)).strftime("%Y-%m-%dT%H:%M:%SZ")
        b = CostBudget(
            session_id="sess-month-rollover",
            granularity="month",
            limit_usd=100.0,
            current_spend=90.0,
            period_start=old_start,
        )
        (costs_dir / "sess-month-rollover").mkdir(exist_ok=True)
        (costs_dir / "sess-month-rollover" / "month.json").write_text(json.dumps(b.to_dict()))

        reloaded = budgeter.get_budget("sess-month-rollover", "month")
        assert reloaded.current_spend == 0.0

    def test_session_budget_never_expires(self, budgeter, costs_dir):
        """Session-granularity budgets never auto-expire."""
        old_start = (_utcnow() - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
        b = CostBudget(
            session_id="sess-never-expire",
            granularity="session",
            limit_usd=5.0,
            current_spend=3.0,
            period_start=old_start,
        )
        (costs_dir / "sess-never-expire").mkdir(exist_ok=True)
        (costs_dir / "sess-never-expire" / "session.json").write_text(json.dumps(b.to_dict()))

        reloaded = budgeter.get_budget("sess-never-expire", "session")
        assert reloaded.current_spend == pytest.approx(3.0)  # NOT reset

    def test_reset_expired_budgets_returns_count(self, budgeter, costs_dir):
        """reset_expired_budgets() returns number of budgets reset."""
        old_start = (_utcnow() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for gran in ("hour", "day"):
            b = CostBudget(
                session_id="sess-reset-all",
                granularity=gran,
                limit_usd=10.0,
                current_spend=5.0,
                period_start=old_start,
            )
            (costs_dir / "sess-reset-all").mkdir(exist_ok=True)
            (costs_dir / "sess-reset-all" / f"{gran}.json").write_text(json.dumps(b.to_dict()))

        count = budgeter.reset_expired_budgets("sess-reset-all")
        assert count >= 1  # at least hour budget reset


# ===========================================================================
# Concurrent sessions
# ===========================================================================

class TestConcurrentSessions:
    """Independent budgets per session — no cross-session contamination."""

    def test_two_sessions_independent_spend(self, budgeter):
        """Spending in session A does not affect session B."""
        budgeter.get_budget("sess-indep-A", "session", default_limit_usd=5.0)
        budgeter.get_budget("sess-indep-B", "session", default_limit_usd=5.0)
        budgeter.record_spend("sess-indep-A", 4.0, "session")

        b_a = budgeter.get_budget("sess-indep-A", "session")
        b_b = budgeter.get_budget("sess-indep-B", "session")

        assert b_a.current_spend == pytest.approx(4.0)
        assert b_b.current_spend == pytest.approx(0.0)

    def test_session_a_blocked_session_b_allowed(self, budgeter):
        """Blocking session A does not block session B."""
        budgeter.get_budget("sess-blk-A", "session", default_limit_usd=2.0)
        budgeter.get_budget("sess-blk-B", "session", default_limit_usd=10.0)
        budgeter.record_spend("sess-blk-A", 2.0, "session")  # A at limit

        allowed_a = budgeter.enforce_budget("sess-blk-A", task_cost=0.01, granularity="session")
        allowed_b = budgeter.enforce_budget("sess-blk-B", task_cost=5.0, granularity="session")

        assert allowed_a is False
        assert allowed_b is True

    def test_many_sessions_independent_budgets(self, budgeter):
        """10 concurrent sessions each have independent budgets."""
        session_ids = [f"sess-concurrent-{i}" for i in range(10)]
        for i, sid in enumerate(session_ids):
            budgeter.get_budget(sid, "session", default_limit_usd=float(i + 1))
            budgeter.record_spend(sid, float(i) * 0.1, "session")

        for i, sid in enumerate(session_ids):
            b = budgeter.get_budget(sid, "session")
            assert b.limit_usd == pytest.approx(float(i + 1))
            assert b.current_spend == pytest.approx(float(i) * 0.1)

    def test_provider_splits_per_session(self, budgeter):
        """Provider splits are tracked independently per session."""
        budgeter.record_spend("sess-prov-A", 1.0, "session", provider="anthropic")
        budgeter.record_spend("sess-prov-B", 2.0, "session", provider="openai")

        b_a = budgeter.get_budget("sess-prov-A", "session")
        b_b = budgeter.get_budget("sess-prov-B", "session")

        assert b_a.provider_splits.get("anthropic", 0) == pytest.approx(1.0)
        assert b_a.provider_splits.get("openai", 0) == 0.0
        assert b_b.provider_splits.get("openai", 0) == pytest.approx(2.0)
        assert b_b.provider_splits.get("anthropic", 0) == 0.0


# ===========================================================================
# Persistence
# ===========================================================================

class TestPersistence:
    """Save/load round-trip for budget state."""

    def test_budget_persisted_to_disk(self, budgeter, costs_dir):
        """Budget is written to the expected filesystem path."""
        budgeter.get_budget("sess-persist", "session", default_limit_usd=5.0)
        expected_path = costs_dir / "sess-persist" / "session.json"
        assert expected_path.exists()

    def test_spend_persists_across_instances(self, costs_dir, models_yaml):
        """Spend recorded in one CostBudgeter instance is visible in a new instance."""
        b1 = CostBudgeter(costs_dir=costs_dir, models_yaml=models_yaml)
        b1.get_budget("sess-across", "session", default_limit_usd=10.0)
        b1.record_spend("sess-across", 3.5, "session")

        b2 = CostBudgeter(costs_dir=costs_dir, models_yaml=models_yaml)
        b = b2.get_budget("sess-across", "session")
        assert b.current_spend == pytest.approx(3.5)

    def test_corrupted_json_creates_fresh_budget(self, budgeter, costs_dir):
        """Corrupted JSON file is replaced with a fresh budget."""
        (costs_dir / "sess-corrupt").mkdir(exist_ok=True)
        (costs_dir / "sess-corrupt" / "session.json").write_text("NOT VALID JSON {{{{")

        b = budgeter.get_budget("sess-corrupt", "session", default_limit_usd=7.0)
        assert b.current_spend == 0.0
        assert b.limit_usd == 7.0

    def test_incremental_spend_accumulates(self, budgeter):
        """Multiple record_spend calls accumulate correctly."""
        budgeter.get_budget("sess-accum", "session", default_limit_usd=10.0)
        budgeter.record_spend("sess-accum", 1.0, "session")
        budgeter.record_spend("sess-accum", 2.0, "session")
        budgeter.record_spend("sess-accum", 0.5, "session")

        b = budgeter.get_budget("sess-accum", "session")
        assert b.current_spend == pytest.approx(3.5)

    def test_negative_spend_raises(self, budgeter):
        """Negative spend amount raises ValueError."""
        budgeter.get_budget("sess-neg", "session", default_limit_usd=5.0)
        with pytest.raises(ValueError, match="non-negative"):
            budgeter.record_spend("sess-neg", -0.01, "session")


# ===========================================================================
# Edge cases and integration
# ===========================================================================

class TestEdgeCasesAndIntegration:
    """Edge cases and integration scenarios."""

    def test_unknown_granularity_raises(self, budgeter):
        """Unknown granularity raises ValueError from get_budget."""
        with pytest.raises(ValueError, match="granularity"):
            budgeter.get_budget("sess-x", granularity="quarterly")

    def test_all_granularities_independent_for_same_session(self, budgeter):
        """Session/hour/day/week/month budgets are independent for the same session."""
        sid = "sess-gran-independence"
        for gran in VALID_GRANULARITIES:
            budgeter.get_budget(sid, gran, default_limit_usd=float(VALID_GRANULARITIES.index(gran) + 1))
        for gran in VALID_GRANULARITIES:
            budgeter.record_spend(sid, 0.5, gran)

        for gran in VALID_GRANULARITIES:
            b = budgeter.get_budget(sid, gran)
            assert b.granularity == gran
            assert b.current_spend == pytest.approx(0.5)

    def test_enforce_then_record_full_flow(self, budgeter):
        """Full flow: enforce → record → check updated spend."""
        budgeter.get_budget("sess-flow", "session", default_limit_usd=5.0)

        cost = budgeter.calculate_provider_cost("anthropic", {"input": 10_000, "output": 2_000}, "claude-sonnet")
        allowed = budgeter.enforce_budget("sess-flow", task_cost=cost, granularity="session")
        assert allowed is True

        budgeter.record_spend("sess-flow", cost, "session", provider="anthropic")
        b = budgeter.get_budget("sess-flow", "session")
        assert b.current_spend == pytest.approx(cost)
        assert b.provider_splits.get("anthropic", 0) == pytest.approx(cost)

    def test_graceful_degrade_reflects_real_spend(self, budgeter):
        """graceful_degrade() on a loaded budget correctly reflects real spend."""
        budgeter.get_budget("sess-degrade", "session", default_limit_usd=10.0)
        budgeter.record_spend("sess-degrade", 8.0, "session")  # 80%

        b = budgeter.get_budget("sess-degrade", "session")
        level = budgeter.graceful_degrade(b.spend_percent)
        assert level == "critical"

    def test_cost_accuracy_within_one_percent(self, budgeter):
        """Cost calculation is accurate to within 1% (spec requirement)."""
        # claude-sonnet: input=$0.003, output=$0.015 per 1K tokens
        cost = budgeter.calculate_provider_cost(
            "anthropic",
            {"input": 100_000, "output": 20_000},
            "claude-sonnet",
        )
        # 100 * 0.003 + 20 * 0.015 = 0.3 + 0.3 = 0.6
        expected = 0.3 + 0.3
        assert abs(cost - expected) / expected < 0.01  # within 1%


# ===========================================================================
# Branch coverage helpers
# ===========================================================================

class TestBranchCoverage:
    """Targeted tests for defensive branches that normal flows don't reach."""

    def test_load_cost_rates_missing_yaml(self, costs_dir, tmp_path):
        """CostBudgeter with non-existent models_yaml uses fallback rates without error."""
        missing = tmp_path / "nonexistent.yaml"
        b = CostBudgeter(costs_dir=costs_dir, models_yaml=missing)
        # Should still work with fallback rates
        cost = b.calculate_provider_cost("any-provider", {"input": 1_000}, "any-model")
        assert cost > 0.0

    def test_load_cost_rates_malformed_yaml(self, costs_dir, tmp_path):
        """CostBudgeter with unparseable models_yaml uses fallback rates without error."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("{invalid: yaml: content: [[[")
        b = CostBudgeter(costs_dir=costs_dir, models_yaml=bad_yaml)
        cost = b.calculate_provider_cost("anthropic", {"input": 1_000}, "claude-sonnet")
        # Fallback rates used; cost should be FALLBACK_COST_RATES["input"] * 1
        assert cost == pytest.approx(FALLBACK_COST_RATES["input"], rel=0.01)

    def test_get_budget_invalid_data_in_valid_json(self, budgeter, costs_dir):
        """Valid JSON but invalid budget data (bad granularity) recreates budget."""
        (costs_dir / "sess-invalid-data").mkdir(exist_ok=True)
        bad_data = {
            "session_id": "sess-invalid-data",
            "granularity": "quarterly",   # invalid — will raise in CostBudget.__post_init__
            "limit_usd": 5.0,
            "current_spend": 1.0,
            "alert_thresholds": [0.5, 0.75, 0.9, 1.0],
            "hard_limit_action": "block",
            "provider_splits": {},
            "period_start": "2026-06-01T00:00:00Z",
            "alerts_fired": [],
        }
        (costs_dir / "sess-invalid-data" / "session.json").write_text(json.dumps(bad_data))
        # Should recreate with fresh budget instead of crashing
        b = budgeter.get_budget("sess-invalid-data", "session", default_limit_usd=7.0)
        assert b.current_spend == 0.0
        assert b.granularity == "session"

    def test_is_expired_empty_period_start(self):
        """_is_expired returns False when period_start is empty string."""
        # Create CostBudget with period_start forced to empty after construction
        b = CostBudget(session_id="s", granularity="day", limit_usd=1.0)
        object.__setattr__(b, "period_start", "")  # bypass post_init
        # Should return False, not crash
        result = _is_expired(b)
        assert result is False

    def test_is_expired_malformed_period_start(self):
        """_is_expired returns False when period_start is not valid ISO-8601."""
        b = CostBudget(session_id="s", granularity="hour", limit_usd=1.0)
        object.__setattr__(b, "period_start", "not-a-date")
        result = _is_expired(b)
        assert result is False

    def test_reset_expired_budgets_handles_error_gracefully(self, budgeter, costs_dir):
        """reset_expired_budgets skips sessions with unreadable budget files."""
        # Write a file that is valid JSON but invalid budget data
        (costs_dir / "sess-bad-reset").mkdir(exist_ok=True)
        bad = {"session_id": "sess-bad-reset", "granularity": "INVALID", "limit_usd": 1.0}
        (costs_dir / "sess-bad-reset" / "day.json").write_text(json.dumps(bad))
        # Should not raise
        count = budgeter.reset_expired_budgets("sess-bad-reset")
        assert isinstance(count, int)
