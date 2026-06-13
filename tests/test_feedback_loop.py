"""
Tests for FeedbackLoop - task outcome tracking and analysis.
"""

import json
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from src.orchestration.feedback.feedback_loop import (
    FeedbackLoop,
    FeedbackStore,
    TaskOutcome,
    AgentFeedbackSummary,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_store(tmp_path):
    store_path = tmp_path / "feedback.jsonl"
    return FeedbackStore(store_path=store_path)


@pytest.fixture
def loop(tmp_store):
    return FeedbackLoop(store=tmp_store)


def make_outcome(
    task_id="t-001",
    agent_role="engineer",
    model="sonnet",
    quality_score=85.0,
    status="complete",
    skills_used=None,
    tokens_used=1000,
    duration_minutes=30.0,
    retry_count=0,
):
    return TaskOutcome(
        task_id=task_id,
        agent_role=agent_role,
        model=model,
        quality_score=quality_score,
        status=status,
        skills_used=skills_used or [],
        tokens_used=tokens_used,
        duration_minutes=duration_minutes,
        retry_count=retry_count,
    )


# ---------------------------------------------------------------------------
# TaskOutcome tests
# ---------------------------------------------------------------------------

class TestTaskOutcome:
    def test_success_true_for_complete(self):
        o = make_outcome(status="complete")
        assert o.success is True

    def test_success_true_for_passed(self):
        o = make_outcome(status="passed")
        assert o.success is True

    def test_success_false_for_failed(self):
        o = make_outcome(status="failed")
        assert o.success is False

    def test_success_false_for_escalated(self):
        o = make_outcome(status="escalated")
        assert o.success is False

    def test_to_dict_has_all_fields(self):
        o = make_outcome()
        d = o.to_dict()
        assert "task_id" in d
        assert "agent_role" in d
        assert "quality_score" in d
        assert "status" in d
        assert "timestamp" in d

    def test_timestamp_is_iso_format(self):
        o = make_outcome()
        # Should not raise
        datetime.fromisoformat(o.timestamp)


# ---------------------------------------------------------------------------
# FeedbackStore tests
# ---------------------------------------------------------------------------

class TestFeedbackStore:
    def test_append_and_read(self, tmp_store):
        o = make_outcome()
        tmp_store.append(o)
        outcomes = tmp_store.read_all()
        assert len(outcomes) == 1
        assert outcomes[0].task_id == "t-001"

    def test_multiple_appends(self, tmp_store):
        for i in range(5):
            tmp_store.append(make_outcome(task_id=f"t-{i:03d}"))
        outcomes = tmp_store.read_all()
        assert len(outcomes) == 5

    def test_read_empty_store(self, tmp_store):
        outcomes = tmp_store.read_all()
        assert outcomes == []

    def test_read_since_filters_old(self, tmp_store):
        old = make_outcome(task_id="old")
        # Manually set old timestamp
        old_dict = old.to_dict()
        old_dict["timestamp"] = "2020-01-01T00:00:00"
        with open(tmp_store.store_path, "a") as f:
            f.write(json.dumps(old_dict) + "\n")

        new = make_outcome(task_id="new")
        tmp_store.append(new)

        since = datetime(2023, 1, 1)
        recent = tmp_store.read_since(since)
        task_ids = [o.task_id for o in recent]
        assert "new" in task_ids
        assert "old" not in task_ids

    def test_clear_removes_file(self, tmp_store):
        tmp_store.append(make_outcome())
        tmp_store.clear()
        assert not tmp_store.store_path.exists()

    def test_malformed_line_skipped(self, tmp_store):
        with open(tmp_store.store_path, "w") as f:
            f.write("not valid json\n")
            f.write(json.dumps(make_outcome().to_dict()) + "\n")
        outcomes = tmp_store.read_all()
        assert len(outcomes) == 1


# ---------------------------------------------------------------------------
# FeedbackLoop.record tests
# ---------------------------------------------------------------------------

class TestFeedbackLoopRecord:
    def test_record_persists_outcome(self, loop):
        o = make_outcome()
        loop.record(o)
        outcomes = loop.store.read_all()
        assert len(outcomes) == 1

    def test_record_invalidates_cache(self, loop):
        loop.record(make_outcome(task_id="a"))
        _ = loop._outcomes()  # populate cache
        loop.record(make_outcome(task_id="b"))
        assert loop._cache is None

    def test_record_from_handback(self, loop):
        handback = {
            "task_id": "hb-001",
            "quality_score": 88,
            "status": "success",
            "tokens_in": 500,
            "tokens_out": 300,
            "effort_actual": 0.5,
            "retry_count": 0,
        }
        delegate = {"role": "engineer", "model": "sonnet"}
        outcome = loop.record_from_handback(handback, delegate)
        assert outcome.task_id == "hb-001"
        assert outcome.quality_score == 88.0
        assert outcome.agent_role == "engineer"
        assert outcome.tokens_used == 800

    def test_record_from_handback_with_skills(self, loop):
        handback = {
            "task_id": "hb-002",
            "quality_score": 90,
            "status": "success",
            "skills_used": ["testing", "quality"],
        }
        delegate = {"role": "quality_engineer", "model": "sonnet"}
        outcome = loop.record_from_handback(handback, delegate)
        assert "testing" in outcome.skills_used


# ---------------------------------------------------------------------------
# FeedbackLoop analysis tests
# ---------------------------------------------------------------------------

class TestFeedbackLoopAnalysis:
    def test_agent_summary_empty(self, loop):
        summary = loop.agent_summary("engineer")
        assert summary.total_tasks == 0
        assert summary.success_rate == 0.0

    def test_agent_summary_with_data(self, loop):
        loop.record(make_outcome(agent_role="engineer", quality_score=90, status="complete"))
        loop.record(make_outcome(agent_role="engineer", quality_score=70, status="failed", task_id="t2"))
        summary = loop.agent_summary("engineer")
        assert summary.total_tasks == 2
        assert summary.successful_tasks == 1
        assert abs(summary.success_rate - 0.5) < 0.01
        assert abs(summary.avg_quality - 80.0) < 0.01

    def test_all_agent_summaries(self, loop):
        loop.record(make_outcome(agent_role="engineer"))
        loop.record(make_outcome(agent_role="senior_engineer", task_id="t2"))
        summaries = loop.all_agent_summaries()
        assert "engineer" in summaries
        assert "senior_engineer" in summaries

    def test_quality_trend_returns_list(self, loop):
        loop.record(make_outcome(agent_role="engineer", quality_score=85))
        trend = loop.quality_trend("engineer", days=30)
        assert isinstance(trend, list)
        if trend:
            date, avg = trend[0]
            assert isinstance(date, str)
            assert isinstance(avg, float)

    def test_skill_effectiveness(self, loop):
        loop.record(make_outcome(skills_used=["testing"], quality_score=90))
        loop.record(make_outcome(skills_used=["testing"], quality_score=80, task_id="t2"))
        eff = loop.skill_effectiveness()
        assert "testing" in eff
        assert eff["testing"]["count"] == 2
        assert abs(eff["testing"]["avg_quality"] - 85.0) < 0.1

    def test_recent_outcomes_limit(self, loop):
        for i in range(25):
            loop.record(make_outcome(task_id=f"t-{i:03d}"))
        recent = loop.recent_outcomes(limit=10)
        assert len(recent) == 10

    def test_overall_stats(self, loop):
        loop.record(make_outcome(quality_score=90, status="complete"))
        loop.record(make_outcome(quality_score=70, status="failed", task_id="t2"))
        stats = loop.overall_stats()
        assert stats["total_tasks"] == 2
        assert stats["successful_tasks"] == 1
        assert abs(stats["success_rate"] - 0.5) < 0.01

    def test_overall_stats_empty(self, loop):
        stats = loop.overall_stats()
        assert stats["total_tasks"] == 0

    def test_skill_quality_tracked_in_summary(self, loop):
        loop.record(make_outcome(agent_role="engineer", skills_used=["testing"], quality_score=88))
        summary = loop.agent_summary("engineer")
        assert "testing" in summary.skill_quality
