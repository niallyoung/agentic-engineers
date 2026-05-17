# -*- coding: utf-8 -*-
"""
Tests for CostDashboard.

Coverage: spend summary, trend analysis, alert generation, report generation.
"""

import pytest
from datetime import date, timedelta
from src.orchestration.cost.cost_dashboard import (
    CostDashboard,
    SpendSummary,
    CostAlert,
    CostReport,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dashboard():
    return CostDashboard()


def make_metric(
    agent="engineer",
    role="engineer",
    model="sonnet-4-6",
    cost=0.10,
    quality_score=92.0,
    task_type="implementation",
    timestamp=None,
):
    if timestamp is None:
        timestamp = date.today().isoformat() + "T12:00:00Z"
    return {
        "agent": agent,
        "role": role,
        "model": model,
        "cost": cost,
        "quality_score": quality_score,
        "task_type": task_type,
        "timestamp": timestamp,
    }


def make_historical_metrics(days=7, cost_per_day=1.0):
    """Generate metrics spread over N days."""
    metrics = []
    today = date.today()
    for i in range(days):
        day = (today - timedelta(days=days - 1 - i)).isoformat()
        metrics.append(make_metric(cost=cost_per_day, timestamp=f"{day}T12:00:00Z"))
    return metrics


# ---------------------------------------------------------------------------
# SpendSummary tests
# ---------------------------------------------------------------------------

class TestSpendSummary:
    def test_empty_dashboard_returns_zero_summary(self, dashboard):
        summary = dashboard.get_spend_summary()
        assert summary.total_cost == 0.0
        assert summary.total_tasks == 0

    def test_total_cost_aggregated(self, dashboard):
        dashboard.ingest([make_metric(cost=0.10), make_metric(cost=0.20)])
        summary = dashboard.get_spend_summary()
        assert summary.total_cost == pytest.approx(0.30)

    def test_by_agent_breakdown(self, dashboard):
        dashboard.ingest([
            make_metric(agent="engineer", cost=0.10),
            make_metric(agent="senior_engineer", cost=0.30),
        ])
        summary = dashboard.get_spend_summary()
        assert "engineer" in summary.by_agent
        assert "senior_engineer" in summary.by_agent
        assert summary.by_agent["senior_engineer"] > summary.by_agent["engineer"]

    def test_by_model_breakdown(self, dashboard):
        dashboard.ingest([
            make_metric(model="haiku-4-5", cost=0.05),
            make_metric(model="sonnet-4-6", cost=0.15),
        ])
        summary = dashboard.get_spend_summary()
        assert "haiku-4-5" in summary.by_model
        assert "sonnet-4-6" in summary.by_model

    def test_avg_cost_per_task(self, dashboard):
        dashboard.ingest([make_metric(cost=0.10), make_metric(cost=0.30)])
        summary = dashboard.get_spend_summary()
        assert summary.avg_cost_per_task == pytest.approx(0.20)

    def test_avg_quality_computed(self, dashboard):
        dashboard.ingest([
            make_metric(quality_score=90.0),
            make_metric(quality_score=94.0),
        ])
        summary = dashboard.get_spend_summary()
        assert summary.avg_quality == pytest.approx(92.0)

    def test_summary_render_contains_total(self, dashboard):
        dashboard.ingest([make_metric(cost=0.50)])
        summary = dashboard.get_spend_summary()
        rendered = summary.render()
        assert "0.5" in rendered or "0.50" in rendered

    def test_by_task_type_breakdown(self, dashboard):
        dashboard.ingest([
            make_metric(task_type="routing", cost=0.05),
            make_metric(task_type="implementation", cost=0.25),
        ])
        summary = dashboard.get_spend_summary()
        assert "routing" in summary.by_task_type
        assert "implementation" in summary.by_task_type

    def test_ingest_appends(self, dashboard):
        dashboard.ingest([make_metric(cost=0.10)])
        dashboard.ingest([make_metric(cost=0.20)])
        summary = dashboard.get_spend_summary()
        assert summary.total_tasks == 2

    def test_reset_clears_data(self, dashboard):
        dashboard.ingest([make_metric(cost=0.10)])
        dashboard.reset()
        summary = dashboard.get_spend_summary()
        assert summary.total_tasks == 0


# ---------------------------------------------------------------------------
# Trend analysis tests
# ---------------------------------------------------------------------------

class TestCostTrends:
    def test_stable_trend(self, dashboard):
        metrics = make_historical_metrics(days=7, cost_per_day=1.0)
        dashboard.ingest(metrics)
        trends = dashboard.get_cost_trends(days=7)
        assert trends["direction"] in ("stable", "increasing", "decreasing")

    def test_increasing_trend_detected(self, dashboard):
        today = date.today()
        metrics = []
        for i in range(7):
            day = (today - timedelta(days=6 - i)).isoformat()
            cost = 0.10 * (i + 1)  # Increasing cost
            metrics.append(make_metric(cost=cost, timestamp=f"{day}T12:00:00Z"))
        dashboard.ingest(metrics)
        trends = dashboard.get_cost_trends(days=7)
        assert trends["direction"] == "increasing"

    def test_trends_include_daily_costs(self, dashboard):
        metrics = make_historical_metrics(days=3)
        dashboard.ingest(metrics)
        trends = dashboard.get_cost_trends(days=3)
        assert "daily_costs" in trends
        assert len(trends["daily_costs"]) >= 1

    def test_trends_empty_dashboard(self, dashboard):
        trends = dashboard.get_cost_trends()
        assert trends["direction"] == "stable"


# ---------------------------------------------------------------------------
# Alert tests
# ---------------------------------------------------------------------------

class TestCostAlerts:
    def test_no_alerts_within_budget(self, dashboard):
        dashboard.ingest([make_metric(cost=0.10)])
        alerts = dashboard.check_alerts(daily_budget=100.0)
        overspend = [a for a in alerts if a.alert_type == "overspend"]
        assert len(overspend) == 0

    def test_overspend_warning_at_80pct(self, dashboard):
        # Spend $8 against $10 budget = 80%
        dashboard.ingest([make_metric(cost=8.0)])
        alerts = dashboard.check_alerts(daily_budget=10.0, overspend_pct=80.0)
        overspend = [a for a in alerts if a.alert_type == "overspend"]
        assert len(overspend) >= 1

    def test_overspend_critical_when_exceeded(self, dashboard):
        dashboard.ingest([make_metric(cost=15.0)])
        alerts = dashboard.check_alerts(daily_budget=10.0)
        critical = [a for a in alerts if a.severity == "critical"]
        assert len(critical) >= 1

    def test_efficiency_alert_when_quality_low(self, dashboard):
        dashboard.ingest([make_metric(quality_score=70.0)])
        alerts = dashboard.check_alerts(efficiency_floor=85.0)
        eff_alerts = [a for a in alerts if a.alert_type == "efficiency"]
        assert len(eff_alerts) >= 1

    def test_alert_history_accumulated(self, dashboard):
        dashboard.ingest([make_metric(cost=15.0)])
        dashboard.check_alerts(daily_budget=10.0)
        dashboard.check_alerts(daily_budget=10.0)
        history = dashboard.get_alert_history()
        assert len(history) >= 2

    def test_alert_str_representation(self):
        alert = CostAlert(
            alert_type="overspend",
            severity="warning",
            message="Budget at 85%",
            agent=None,
            threshold=8.0,
            actual_value=8.5,
        )
        text = str(alert)
        assert "WARNING" in text
        assert "overspend" in text


# ---------------------------------------------------------------------------
# Report generation tests
# ---------------------------------------------------------------------------

class TestCostReportGeneration:
    def test_daily_report_generated(self, dashboard):
        dashboard.ingest([make_metric(cost=0.10)])
        report = dashboard.generate_report(period="daily")
        assert isinstance(report, CostReport)
        assert report.period == "daily"

    def test_report_render_contains_period(self, dashboard):
        dashboard.ingest([make_metric(cost=0.10)])
        report = dashboard.generate_report(period="weekly")
        rendered = report.render()
        assert "weekly" in rendered.lower() or "Cost Report" in rendered

    def test_top_cost_agents(self, dashboard):
        dashboard.ingest([
            make_metric(agent="engineer", cost=0.10),
            make_metric(agent="senior_engineer", cost=0.50),
        ])
        top = dashboard.top_cost_agents(n=2)
        assert top[0][0] == "senior_engineer"
        assert top[0][1] == pytest.approx(0.50)

    def test_report_has_trends(self, dashboard):
        metrics = make_historical_metrics(days=5)
        dashboard.ingest(metrics)
        report = dashboard.generate_report()
        assert "direction" in report.trends
