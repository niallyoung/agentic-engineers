"""Test session-analyzer skill."""

import pytest
import yaml
from pathlib import Path
import tempfile


def test_session_analyzer_imports():
    """Test that SessionAnalyzer can be imported."""
    from session_analyzer.scripts.session_analyzer import SessionAnalyzer
    assert SessionAnalyzer is not None


def test_session_analysis_dataclass():
    """Test that SessionAnalysis dataclass works."""
    from session_analyzer.scripts.session_analyzer import SessionAnalysis

    analysis = SessionAnalysis(
        session_id="test-session",
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

    assert analysis.session_id == "test-session"
    assert analysis.task_count == 5


def test_repetitive_pattern_dataclass():
    """Test that RepetitivePattern dataclass works."""
    from session_analyzer.scripts.session_analyzer import RepetitivePattern

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


def test_quality_anomaly_dataclass():
    """Test that QualityAnomaly dataclass works."""
    from session_analyzer.scripts.session_analyzer import QualityAnomaly

    anomaly = QualityAnomaly(
        anomaly_id="low-confidence",
        description="Task has low confidence",
        severity="warning",
        tasks=["task-1"],
        root_cause="Unclear",
        recommendation="Clarify",
    )

    assert anomaly.anomaly_id == "low-confidence"


def test_recommendation_dataclass():
    """Test that Recommendation dataclass works."""
    from session_analyzer.scripts.session_analyzer import Recommendation

    rec = Recommendation(
        title="Create skill",
        category="meta-skill",
        rationale="Repeated pattern",
        effort="medium",
        impact="High",
        priority="P1",
    )

    assert rec.title == "Create skill"


def test_session_analysis_to_dict():
    """Test SessionAnalysis.to_dict() converts to dict."""
    from session_analyzer.scripts.session_analyzer import SessionAnalysis

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


def test_session_analysis_save_to_yaml():
    """Test SessionAnalysis.save() creates valid YAML."""
    from session_analyzer.scripts.session_analyzer import SessionAnalysis

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
