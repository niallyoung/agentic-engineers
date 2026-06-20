"""Test session-analyzer skill."""

import pytest
import yaml
import importlib
from pathlib import Path
import tempfile


def test_session_analyzer_imports():
    """Test that SessionAnalyzer can be imported."""
    mod = importlib.import_module('session-analyzer.scripts.session_analyzer')
    SessionAnalyzer = getattr(mod, 'SessionAnalyzer')
    assert SessionAnalyzer is not None


def test_session_analysis_dataclass():
    """Test that SessionAnalysis dataclass works."""
    mod = importlib.import_module('session-analyzer.scripts.session_analyzer')
    SessionAnalysis = getattr(mod, 'SessionAnalysis')

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
    mod = importlib.import_module('session-analyzer.scripts.session_analyzer')
    RepetitivePattern = getattr(mod, 'RepetitivePattern')

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
    mod = importlib.import_module('session-analyzer.scripts.session_analyzer')
    QualityAnomaly = getattr(mod, 'QualityAnomaly')

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
    mod = importlib.import_module('session-analyzer.scripts.session_analyzer')
    Recommendation = getattr(mod, 'Recommendation')

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
    mod = importlib.import_module('session-analyzer.scripts.session_analyzer')
    SessionAnalysis = getattr(mod, 'SessionAnalysis')

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
    mod = importlib.import_module('session-analyzer.scripts.session_analyzer')
    SessionAnalysis = getattr(mod, 'SessionAnalysis')

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


def test_harvest_skill_feedback_empty():
    """HANDBACKs without skill_feedback -> empty dict."""
    mod = importlib.import_module('session-analyzer.scripts.session_analyzer')
    SessionAnalyzer = getattr(mod, 'SessionAnalyzer')

    analyzer = SessionAnalyzer(session_id="test-session")
    # Manually set handbacks without skill_feedback
    analyzer.handbacks = {
        'task-1': {
            'task_id': 'task-1',
            'status': 'success',
            'output': 'Done',
            'metrics': {'quality': 0.9, 'tokens': 1000, 'cost': 0.05, 'duration_seconds': 60},
        },
        'task-2': {
            'task_id': 'task-2',
            'status': 'success',
            'output': 'Done',
            'metrics': {'quality': 0.85, 'tokens': 1500, 'cost': 0.07, 'duration_seconds': 90},
        }
    }

    feedback_map = analyzer._harvest_skill_feedback()
    assert isinstance(feedback_map, dict)
    assert len(feedback_map) == 0


def test_harvest_skill_feedback_aggregates_across_tasks():
    """3 HANDBACKs each with one item -> 3 items under one skill."""
    mod = importlib.import_module('session-analyzer.scripts.session_analyzer')
    SessionAnalyzer = getattr(mod, 'SessionAnalyzer')

    analyzer = SessionAnalyzer(session_id="test-session")
    analyzer.handbacks = {
        'task-1': {
            'task_id': 'task-1',
            'status': 'success',
            'output': 'Done',
            'metrics': {'quality': 0.9, 'tokens': 1000, 'cost': 0.05, 'duration_seconds': 60},
            'skill_feedback': [
                {
                    'skill_name': 'queue-management',
                    'effectiveness_score': 0.85,
                }
            ]
        },
        'task-2': {
            'task_id': 'task-2',
            'status': 'success',
            'output': 'Done',
            'metrics': {'quality': 0.85, 'tokens': 1500, 'cost': 0.07, 'duration_seconds': 90},
            'skill_feedback': [
                {
                    'skill_name': 'queue-management',
                    'effectiveness_score': 0.80,
                }
            ]
        },
        'task-3': {
            'task_id': 'task-3',
            'status': 'success',
            'output': 'Done',
            'metrics': {'quality': 0.88, 'tokens': 2000, 'cost': 0.10, 'duration_seconds': 120},
            'skill_feedback': [
                {
                    'skill_name': 'queue-management',
                    'effectiveness_score': 0.90,
                }
            ]
        }
    }

    feedback_map = analyzer._harvest_skill_feedback()
    assert 'queue-management' in feedback_map
    assert len(feedback_map['queue-management']) == 3
    # Items should include task_id
    for item in feedback_map['queue-management']:
        assert 'task_id' in item


def test_skill_improvement_recommendations_threshold():
    """3+ items -> P0 recommendation; 2 items -> P1."""
    mod = importlib.import_module('session-analyzer.scripts.session_analyzer')
    SessionAnalyzer = getattr(mod, 'SessionAnalyzer')

    analyzer = SessionAnalyzer(session_id="test-session")

    # Create feedback map: one skill with 3 items (P0), one with 2 items (P1)
    feedback_map = {
        'queue-management': [
            {'skill_name': 'queue-management', 'effectiveness_score': 0.85, 'task_id': 'task-1'},
            {'skill_name': 'queue-management', 'effectiveness_score': 0.80, 'task_id': 'task-2'},
            {'skill_name': 'queue-management', 'effectiveness_score': 0.90, 'task_id': 'task-3'},
        ],
        'protocol-validator': [
            {'skill_name': 'protocol-validator', 'effectiveness_score': 0.75, 'task_id': 'task-1'},
            {'skill_name': 'protocol-validator', 'effectiveness_score': 0.85, 'task_id': 'task-2'},
        ]
    }

    recommendations = analyzer._generate_skill_improvement_recommendations(feedback_map)

    # Should have at least 2 recommendations (P0 for queue-management, P1 for protocol-validator)
    assert len(recommendations) >= 2

    # Find P0 recommendations
    p0_recs = [r for r in recommendations if r.priority == 'P0']

    # queue-management (3 items) should be P0
    queue_p0 = [r for r in p0_recs if 'queue-management' in r.title.lower()]
    assert len(queue_p0) > 0


def test_skill_feedback_in_session_analysis_output():
    """analyze_session() with seeded HANDBACKs includes skill_feedback_summary."""
    mod = importlib.import_module('session-analyzer.scripts.session_analyzer')
    SessionAnalyzer = getattr(mod, 'SessionAnalyzer')

    analyzer = SessionAnalyzer(session_id="test-session")
    analyzer.handbacks = {
        'task-1': {
            'task_id': 'task-1',
            'status': 'success',
            'output': 'Done',
            'metrics': {'quality': 0.9, 'tokens': 1000, 'cost': 0.05, 'duration_seconds': 60},
            'skill_feedback': [
                {
                    'skill_name': 'queue-management',
                    'effectiveness_score': 0.85,
                }
            ]
        }
    }

    result = analyzer.analyze_session()

    # result should include skill_feedback_summary
    assert hasattr(result, 'skill_feedback_summary')
    assert isinstance(result.skill_feedback_summary, dict)
