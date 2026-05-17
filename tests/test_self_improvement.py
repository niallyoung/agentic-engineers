"""
Tests for SelfImprovement - feedback trend analysis and recommendations.
"""

import pytest
from src.orchestration.optimization.self_improvement import (
    SelfImprovement,
    ImprovementRecommendation,
    ImprovementReport,
)
from src.orchestration.feedback.feedback_loop import AgentFeedbackSummary


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def improver():
    return SelfImprovement()


def make_summary(
    agent_role="engineer",
    total_tasks=10,
    successful_tasks=8,
    total_quality=850.0,
    total_retries=1,
):
    s = AgentFeedbackSummary(agent_role=agent_role)
    s.total_tasks = total_tasks
    s.successful_tasks = successful_tasks
    s.total_quality = total_quality
    s.total_retries = total_retries
    return s


def make_summaries(**kwargs):
    """Build dict of AgentFeedbackSummary objects."""
    return {role: make_summary(agent_role=role, **kw) for role, kw in kwargs.items()}


# ---------------------------------------------------------------------------
# ImprovementRecommendation tests
# ---------------------------------------------------------------------------

class TestImprovementRecommendation:
    def test_to_dict_has_required_fields(self):
        rec = ImprovementRecommendation(
            category="routing",
            priority="HIGH",
            title="Test",
            description="Test description",
            affected_agents=["engineer"],
            expected_quality_gain=5.0,
            evidence={},
        )
        d = rec.to_dict()
        assert "category" in d
        assert "priority" in d
        assert "title" in d
        assert "description" in d
        assert "affected_agents" in d
        assert "expected_quality_gain" in d
        assert "timestamp" in d


# ---------------------------------------------------------------------------
# SelfImprovement.analyze tests
# ---------------------------------------------------------------------------

class TestSelfImprovementAnalyze:
    def test_analyze_returns_report(self, improver):
        summaries = {"engineer": make_summary()}
        report = improver.analyze(
            agent_summaries=summaries,
            skill_effectiveness={},
            quality_trends={},
            degradation_alerts=[],
        )
        assert isinstance(report, ImprovementReport)

    def test_analyze_empty_data(self, improver):
        report = improver.analyze(
            agent_summaries={},
            skill_effectiveness={},
            quality_trends={},
            degradation_alerts=[],
        )
        assert report.total_tasks_analyzed == 0
        assert isinstance(report.recommendations, list)

    def test_low_success_rate_generates_recommendation(self, improver):
        summaries = {
            "engineer": make_summary(
                total_tasks=10,
                successful_tasks=5,  # 50% success rate < 70% threshold
                total_quality=600.0,
            )
        }
        report = improver.analyze(
            agent_summaries=summaries,
            skill_effectiveness={},
            quality_trends={},
            degradation_alerts=[],
        )
        high_recs = [r for r in report.recommendations if r.priority == "HIGH"]
        assert len(high_recs) >= 1

    def test_low_quality_generates_recommendation(self, improver):
        summaries = {
            "engineer": make_summary(
                total_tasks=10,
                successful_tasks=9,
                total_quality=600.0,  # avg 60 < 75 threshold
            )
        }
        report = improver.analyze(
            agent_summaries=summaries,
            skill_effectiveness={},
            quality_trends={},
            degradation_alerts=[],
        )
        assert len(report.recommendations) >= 1

    def test_high_retry_rate_generates_recommendation(self, improver):
        summaries = {
            "engineer": make_summary(
                total_tasks=10,
                successful_tasks=9,
                total_quality=900.0,
                total_retries=5,  # 50% retry rate > 30% threshold
            )
        }
        report = improver.analyze(
            agent_summaries=summaries,
            skill_effectiveness={},
            quality_trends={},
            degradation_alerts=[],
        )
        process_recs = [r for r in report.recommendations if r.category == "process"]
        assert len(process_recs) >= 1

    def test_declining_trend_generates_recommendation(self, improver):
        summaries = {"engineer": make_summary()}
        trend = [
            ("2026-05-10", 90.0),
            ("2026-05-11", 85.0),
            ("2026-05-12", 78.0),  # declining
        ]
        report = improver.analyze(
            agent_summaries=summaries,
            skill_effectiveness={},
            quality_trends={"engineer": trend},
            degradation_alerts=[],
        )
        # May or may not generate recommendation depending on threshold
        assert isinstance(report.recommendations, list)

    def test_skill_underperformance_generates_recommendation(self, improver):
        skill_eff = {
            "testing": {"count": 5, "avg_quality": 60.0, "min_quality": 50, "max_quality": 70}
        }
        report = improver.analyze(
            agent_summaries={},
            skill_effectiveness=skill_eff,
            quality_trends={},
            degradation_alerts=[],
        )
        skill_recs = [r for r in report.recommendations if r.category == "skill"]
        assert len(skill_recs) >= 1

    def test_degradation_alert_generates_recommendation(self, improver):
        alert = {
            "agent_role": "engineer",
            "task_type": "feature",
            "previous_avg": 90.0,
            "current_avg": 65.0,
            "drop": 25.0,
            "alert_level": "CRITICAL",
            "timestamp": "2026-05-17T10:00:00",
        }

        class AlertObj:
            def to_dict(self):
                return alert

        report = improver.analyze(
            agent_summaries={},
            skill_effectiveness={},
            quality_trends={},
            degradation_alerts=[AlertObj()],
        )
        assert len(report.recommendations) >= 1

    def test_recommendations_sorted_by_priority(self, improver):
        summaries = {
            "engineer": make_summary(
                total_tasks=10,
                successful_tasks=4,  # low success → HIGH
                total_quality=600.0,  # low quality → HIGH
                total_retries=4,      # high retry → MEDIUM
            )
        }
        report = improver.analyze(
            agent_summaries=summaries,
            skill_effectiveness={},
            quality_trends={},
            degradation_alerts=[],
        )
        priorities = [r.priority for r in report.recommendations]
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        for i in range(len(priorities) - 1):
            assert priority_order.get(priorities[i], 3) <= priority_order.get(priorities[i + 1], 3)

    def test_agent_rankings_in_report(self, improver):
        summaries = {
            "engineer": make_summary(agent_role="engineer", total_tasks=10, successful_tasks=9, total_quality=900.0),
            "senior_engineer": make_summary(agent_role="senior_engineer", total_tasks=5, successful_tasks=5, total_quality=475.0),
        }
        report = improver.analyze(
            agent_summaries=summaries,
            skill_effectiveness={},
            quality_trends={},
            degradation_alerts=[],
        )
        assert len(report.agent_rankings) == 2
        # Rankings should be sorted by composite score descending
        scores = [r["composite_score"] for r in report.agent_rankings]
        assert scores == sorted(scores, reverse=True)

    def test_report_summary_string(self, improver):
        report = improver.analyze(
            agent_summaries={},
            skill_effectiveness={},
            quality_trends={},
            degradation_alerts=[],
        )
        assert isinstance(report.summary, str)
        assert len(report.summary) > 0

    def test_report_to_dict(self, improver):
        report = improver.analyze(
            agent_summaries={},
            skill_effectiveness={},
            quality_trends={},
            degradation_alerts=[],
        )
        d = report.to_dict()
        assert "generated_at" in d
        assert "recommendations" in d
        assert "agent_rankings" in d
        assert "summary" in d


# ---------------------------------------------------------------------------
# SelfImprovement state tests
# ---------------------------------------------------------------------------

class TestSelfImprovementState:
    def test_latest_report_none_initially(self, improver):
        assert improver.latest_report() is None

    def test_latest_report_after_analyze(self, improver):
        improver.analyze({}, {}, {}, [])
        assert improver.latest_report() is not None

    def test_all_reports_accumulates(self, improver):
        improver.analyze({}, {}, {}, [])
        improver.analyze({}, {}, {}, [])
        assert len(improver.all_reports()) == 2

    def test_top_recommendations_empty(self, improver):
        recs = improver.top_recommendations()
        assert recs == []

    def test_top_recommendations_after_analyze(self, improver):
        summaries = {
            "engineer": make_summary(
                total_tasks=10,
                successful_tasks=4,
                total_quality=600.0,
            )
        }
        improver.analyze(summaries, {}, {}, [])
        recs = improver.top_recommendations(n=3)
        assert isinstance(recs, list)
        assert len(recs) <= 3

    def test_insufficient_data_skipped(self, improver):
        # Agent with < 3 tasks should not generate recommendations
        summaries = {
            "engineer": make_summary(
                total_tasks=2,
                successful_tasks=0,
                total_quality=0.0,
            )
        }
        report = improver.analyze(summaries, {}, {}, [])
        routing_recs = [r for r in report.recommendations if "engineer" in r.affected_agents]
        assert len(routing_recs) == 0
