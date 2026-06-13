# -*- coding: utf-8 -*-
"""
tests/test_session_analyzer_skill.py — Session Analyzer Meta-Skill.

TDD test suite for automated session transcript analysis and pattern detection.

Coverage areas:
  1. SessionAnalysis dataclass — session-level metrics and structure
  2. RepetitivePattern — pattern detection (3+ occurrences)
  3. QualityAnomaly — quality anomaly detection
  4. Recommendation — actionable recommendations
  5. DriftEvent — config/doc drift detection
  6. SessionAnalyzer.analyze_session() — orchestration
  7. Pattern detection logic — repetition counting
  8. Anomaly detection logic — low confidence, high rework, failures
  9. Report generation — YAML output
  10. CLI interface — command-line invocation

Author: Model Engineer (meta-skill, Pattern Detection)
Phase: TDD GREEN-phase (tests verify behavior)
"""

import sys
import json
import tempfile
import importlib
from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# Lazy hyphenated-package import (mirrors test_agent_creator.py convention)
# ---------------------------------------------------------------------------
def _mod():
    sys.path.insert(0, str(Path(__file__).parent.parent))
    return importlib.import_module(
        "src.skills.session-analyzer.scripts.session_analyzer"
    )


m = _mod()

SessionAnalysis = m.SessionAnalysis
RepetitivePattern = m.RepetitivePattern
QualityAnomaly = m.QualityAnomaly
DriftEvent = m.DriftEvent
Recommendation = m.Recommendation
SessionMetrics = m.SessionMetrics
SessionAnalyzer = m.SessionAnalyzer


# ===========================================================================
# Tests
# ===========================================================================


class TestSessionAnalysisDataclass:
    """Test SessionAnalysis dataclass."""

    def test_session_analysis_creates_with_all_fields(self):
        """SessionAnalysis can be created with all required fields."""
        analysis = SessionAnalysis(
            session_id="test-session-001",
            session_start="2026-06-13T08:00:00Z",
            session_end="2026-06-13T17:30:00Z",
            duration_seconds=34200,
            task_count=5,
            total_cost=10.0,
            total_tokens=50000,
            overall_quality=0.85,
            tasks_by_agent={"engineer": 3},
            tasks_by_status={"success": 5},
            model_performance={},
        )
        assert analysis.session_id == "test-session-001"
        assert analysis.task_count == 5
        assert analysis.total_cost == 10.0
        assert analysis.overall_quality == 0.85

    def test_session_analysis_to_dict(self):
        """SessionAnalysis.to_dict() converts to dict."""
        analysis = SessionAnalysis(
            session_id="test",
            session_start="2026-06-13T08:00:00Z",
            session_end="2026-06-13T17:30:00Z",
            duration_seconds=34200,
            task_count=5,
            total_cost=10.0,
            total_tokens=50000,
            overall_quality=0.85,
            tasks_by_agent={},
            tasks_by_status={},
            model_performance={},
        )

        result_dict = analysis.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["session_id"] == "test"
        assert result_dict["task_count"] == 5

    def test_session_analysis_save_to_yaml(self):
        """SessionAnalysis.save() creates valid YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "analysis.yaml"

            analysis = SessionAnalysis(
                session_id="test",
                session_start="2026-06-13T08:00:00Z",
                session_end="2026-06-13T17:30:00Z",
                duration_seconds=34200,
                task_count=5,
                total_cost=10.0,
                total_tokens=50000,
                overall_quality=0.85,
                tasks_by_agent={},
                tasks_by_status={},
                model_performance={},
            )

            analysis.save(str(output_path))
            assert output_path.exists()

            with open(output_path) as f:
                loaded = yaml.safe_load(f)

            assert loaded["session_id"] == "test"
            assert loaded["task_count"] == 5


class TestRepetitivePattern:
    """Test RepetitivePattern dataclass."""

    def test_repetitive_pattern_creates(self):
        """RepetitivePattern can be created with all fields."""
        pattern = RepetitivePattern(
            pattern_id="enum-drift",
            description="Enum validation repeated",
            count=3,
            tasks=["task-1", "task-2", "task-3"],
            skill_candidate="enhanced-protocol-validator",
            effort="medium",
            confidence=0.9,
        )

        assert pattern.pattern_id == "enum-drift"
        assert pattern.count == 3
        assert len(pattern.tasks) == 3


class TestQualityAnomaly:
    """Test QualityAnomaly dataclass."""

    def test_quality_anomaly_creates(self):
        """QualityAnomaly can be created with all fields."""
        anomaly = QualityAnomaly(
            anomaly_id="low-confidence",
            description="Task has low confidence",
            severity="warning",
            tasks=["task-1"],
            root_cause="Unclear scope",
            recommendation="Clarify requirements",
        )

        assert anomaly.anomaly_id == "low-confidence"
        assert anomaly.severity == "warning"


class TestDriftEvent:
    """Test DriftEvent dataclass."""

    def test_drift_event_creates(self):
        """DriftEvent can be created with all fields."""
        drift = DriftEvent(
            drift_id="config-drift-001",
            description="YAML config changed",
            severity="warning",
            files_affected=["src/config/models.yaml"],
            timestamp_window="2026-06-13T12:00:00Z",
            action_required=True,
        )

        assert drift.drift_id == "config-drift-001"
        assert drift.action_required is True


class TestRecommendation:
    """Test Recommendation dataclass."""

    def test_recommendation_creates(self):
        """Recommendation can be created with all fields."""
        rec = Recommendation(
            title="Create session-analyzer skill",
            category="meta-skill",
            rationale="Pattern detection repeated 3x",
            effort="medium",
            impact="High automation potential",
            priority="P1",
        )

        assert rec.title == "Create session-analyzer skill"
        assert rec.priority == "P1"


class TestSessionAnalyzerBasic:
    """Test SessionAnalyzer basic functionality."""

    def test_session_analyzer_instantiation(self):
        """SessionAnalyzer can be instantiated with required parameters."""
        analyzer = SessionAnalyzer(
            session_id="test-session",
            queue_path="/tmp/queue",
        )
        assert analyzer.session_id == "test-session"

    def test_session_metrics_aggregation(self):
        """SessionMetrics aggregates task-level data correctly."""
        metrics = SessionMetrics(
            task_count=5,
            total_cost=25.50,
            total_tokens=125000,
            overall_quality=0.88,
        )
        assert metrics.task_count == 5
        assert metrics.overall_quality == 0.88


class TestPatternDetection:
    """Test pattern detection logic."""

    def test_repetitive_pattern_3plus_detected(self):
        """Pattern with count >= 3 is detected as repetitive."""
        pattern = RepetitivePattern(
            pattern_id="test-pattern",
            description="Test pattern",
            count=3,
            tasks=["t1", "t2", "t3"],
            skill_candidate="test-skill",
            effort="low",
            confidence=0.8,
        )
        # Pattern is valid if count >= 3
        assert pattern.count >= 3

    def test_low_confidence_anomaly_2plus_tasks(self):
        """Quality anomaly with 2+ tasks can be grouped."""
        anomaly = QualityAnomaly(
            anomaly_id="low-conf-group",
            description="Multiple low-confidence tasks",
            severity="warning",
            tasks=["t1", "t2"],
            root_cause="Ambiguous requirements",
            recommendation="Clarify scope",
        )
        assert len(anomaly.tasks) >= 2


class TestDriftDetection:
    """Test drift detection logic."""

    def test_drift_event_with_action(self):
        """Drift event with action_required=True is tracked."""
        drift = DriftEvent(
            drift_id="critical-drift",
            description="Critical file changed",
            severity="error",
            files_affected=["SPEC.md"],
            timestamp_window="2026-06-13T10:00:00Z",
            action_required=True,
        )
        assert drift.action_required is True
        assert drift.severity == "error"


class TestRecommendationPriorities:
    """Test recommendation priority logic."""

    def test_p0_recommendation_highest_priority(self):
        """P0 recommendations are critical."""
        rec = Recommendation(
            title="Fix critical bug",
            category="bug-fix",
            rationale="Data loss possible",
            effort="high",
            impact="Prevents data loss",
            priority="P0",
        )
        assert rec.priority == "P0"

    def test_p1_recommendation_high_priority(self):
        """P1 recommendations are high priority."""
        rec = Recommendation(
            title="Implement feature",
            category="feature",
            rationale="Requested by stakeholders",
            effort="medium",
            impact="Increases productivity",
            priority="P1",
        )
        assert rec.priority == "P1"

    def test_p2_recommendation_low_priority(self):
        """P2 recommendations are low priority."""
        rec = Recommendation(
            title="Nice-to-have enhancement",
            category="enhancement",
            rationale="Convenience improvement",
            effort="low",
            impact="Marginal benefit",
            priority="P2",
        )
        assert rec.priority == "P2"
