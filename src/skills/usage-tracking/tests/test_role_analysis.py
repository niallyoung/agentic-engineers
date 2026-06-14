"""
Tests for role_analysis.py (absorbed from tokenadvisor — Wave 3 consolidation).

tokenadvisor was merged into usage-tracking as the role-analysis sub-command.
This file tests the MetricsAnalyzer class from role_analysis.py.

Gate: ≥10 tests passing for the role-analysis sub-command.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Add scripts dir to path
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from role_analysis import MetricsAnalyzer, ROLE_TARGETS, MODEL_COSTS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_METRICS = [
    {
        "role": "Orchestrator",
        "tokens_in": 1000,
        "tokens_out": 500,
        "cost": 0.70,
        "task_type": "routing",
    },
    {
        "role": "Engineer",
        "tokens_in": 500,
        "tokens_out": 200,
        "cost": 0.15,
        "task_type": "implementation",
    },
    {
        "role": "Engineer",
        "tokens_in": 300,
        "tokens_out": 100,
        "cost": 0.08,
        "task_type": "implementation",
    },
    {
        "role": "Senior Engineer",
        "tokens_in": 200,
        "tokens_out": 80,
        "cost": 0.07,
        "task_type": "review",
    },
]


@pytest.fixture
def analyzer_with_data(tmp_path: Path) -> MetricsAnalyzer:
    """MetricsAnalyzer with pre-loaded sample data."""
    analyzer = MetricsAnalyzer(metrics_dir=str(tmp_path))
    analyzer.metrics_data = list(SAMPLE_METRICS)
    return analyzer


@pytest.fixture
def empty_analyzer(tmp_path: Path) -> MetricsAnalyzer:
    """MetricsAnalyzer with no loaded data."""
    return MetricsAnalyzer(metrics_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# ROLE_TARGETS and MODEL_COSTS constants
# ---------------------------------------------------------------------------

class TestConstants:
    """Tests for module-level constants."""

    def test_role_targets_has_orchestrator(self):
        assert "Orchestrator" in ROLE_TARGETS
        assert isinstance(ROLE_TARGETS["Orchestrator"], float)

    def test_role_targets_sum_to_one(self):
        total = sum(ROLE_TARGETS.values())
        assert abs(total - 1.0) < 0.01, f"ROLE_TARGETS should sum to ~1.0, got {total}"

    def test_model_costs_has_haiku(self):
        assert "haiku-4-5" in MODEL_COSTS

    def test_model_costs_are_positive(self):
        for model, cost in MODEL_COSTS.items():
            assert cost > 0, f"Cost for {model} should be positive"


# ---------------------------------------------------------------------------
# MetricsAnalyzer.analyze_by_role
# ---------------------------------------------------------------------------

class TestAnalyzeByRole:
    """Tests for MetricsAnalyzer.analyze_by_role()."""

    def test_analyze_by_role_returns_dict(self, analyzer_with_data: MetricsAnalyzer):
        result = analyzer_with_data.analyze_by_role()
        assert isinstance(result, dict)

    def test_analyze_by_role_has_orchestrator(self, analyzer_with_data: MetricsAnalyzer):
        result = analyzer_with_data.analyze_by_role()
        assert "Orchestrator" in result

    def test_analyze_by_role_has_engineer(self, analyzer_with_data: MetricsAnalyzer):
        result = analyzer_with_data.analyze_by_role()
        assert "Engineer" in result

    def test_analyze_by_role_token_count(self, analyzer_with_data: MetricsAnalyzer):
        result = analyzer_with_data.analyze_by_role()
        # Engineer has 2 records: tokens_in=500+300=800
        assert result["Engineer"]["tokens_in"] == 800

    def test_analyze_by_role_cost_sum(self, analyzer_with_data: MetricsAnalyzer):
        result = analyzer_with_data.analyze_by_role()
        # Engineer total cost: 0.15 + 0.08 = 0.23
        assert abs(result["Engineer"]["cost"] - 0.23) < 0.001

    def test_analyze_by_role_percent_present(self, analyzer_with_data: MetricsAnalyzer):
        result = analyzer_with_data.analyze_by_role()
        for role_data in result.values():
            assert "percent" in role_data

    def test_analyze_by_role_variance_present(self, analyzer_with_data: MetricsAnalyzer):
        result = analyzer_with_data.analyze_by_role()
        for role_data in result.values():
            assert "variance" in role_data

    def test_analyze_by_role_count_accumulates(self, analyzer_with_data: MetricsAnalyzer):
        result = analyzer_with_data.analyze_by_role()
        # Engineer has 2 records
        assert result["Engineer"]["count"] == 2

    def test_analyze_by_role_empty_data(self, empty_analyzer: MetricsAnalyzer):
        result = empty_analyzer.analyze_by_role()
        assert result == {}

    def test_analyze_by_role_skips_missing_role(self, tmp_path: Path):
        analyzer = MetricsAnalyzer(metrics_dir=str(tmp_path))
        # Record without 'role' key — should be skipped
        analyzer.metrics_data = [{"tokens_in": 100, "cost": 0.01}]
        result = analyzer.analyze_by_role()
        assert result == {}


# ---------------------------------------------------------------------------
# MetricsAnalyzer.analyze_by_task_type
# ---------------------------------------------------------------------------

class TestAnalyzeByTaskType:
    """Tests for MetricsAnalyzer.analyze_by_task_type()."""

    def test_analyze_by_task_type_returns_dict(self, analyzer_with_data: MetricsAnalyzer):
        result = analyzer_with_data.analyze_by_task_type()
        assert isinstance(result, dict)

    def test_analyze_by_task_type_has_routing(self, analyzer_with_data: MetricsAnalyzer):
        result = analyzer_with_data.analyze_by_task_type()
        assert "routing" in result

    def test_analyze_by_task_type_has_implementation(self, analyzer_with_data: MetricsAnalyzer):
        result = analyzer_with_data.analyze_by_task_type()
        assert "implementation" in result

    def test_analyze_by_task_type_empty_data(self, empty_analyzer: MetricsAnalyzer):
        result = empty_analyzer.analyze_by_task_type()
        assert result == {}

    def test_analyze_by_task_type_limits_to_5(self, tmp_path: Path):
        analyzer = MetricsAnalyzer(metrics_dir=str(tmp_path))
        # Add 10 different task types
        analyzer.metrics_data = [
            {"task_type": f"type_{i}", "tokens_in": i * 10, "cost": i * 0.01}
            for i in range(10)
        ]
        result = analyzer.analyze_by_task_type()
        assert len(result) <= 5


# ---------------------------------------------------------------------------
# MetricsAnalyzer.find_outliers
# ---------------------------------------------------------------------------

class TestFindOutliers:
    """Tests for MetricsAnalyzer.find_outliers()."""

    def test_find_outliers_returns_list(self, analyzer_with_data: MetricsAnalyzer):
        result = analyzer_with_data.find_outliers()
        assert isinstance(result, list)

    def test_find_outliers_empty_data(self, empty_analyzer: MetricsAnalyzer):
        result = empty_analyzer.find_outliers()
        assert result == []

    def test_find_outliers_single_record(self, tmp_path: Path):
        analyzer = MetricsAnalyzer(metrics_dir=str(tmp_path))
        analyzer.metrics_data = [{"tokens_in": 100, "tokens_out": 50, "cost": 0.01}]
        result = analyzer.find_outliers()
        assert result == []  # Need ≥2 records for percentile calculation

    def test_find_outliers_has_total_tokens(self, analyzer_with_data: MetricsAnalyzer):
        result = analyzer_with_data.find_outliers()
        for item in result:
            assert "total_tokens" in item


# ---------------------------------------------------------------------------
# MetricsAnalyzer.load_metrics
# ---------------------------------------------------------------------------

class TestLoadMetrics:
    """Tests for MetricsAnalyzer.load_metrics()."""

    def test_load_metrics_returns_false_on_missing_date(self, tmp_path: Path):
        analyzer = MetricsAnalyzer(metrics_dir=str(tmp_path))
        result = analyzer.load_metrics("2099-01-01")
        assert result is False

    def test_load_metrics_loads_json_files(self, tmp_path: Path):
        date_dir = tmp_path / "2026-06-14"
        date_dir.mkdir()
        task_file = date_dir / "task_001.json"
        task_file.write_text(
            json.dumps({"role": "Engineer", "tokens_in": 100, "cost": 0.01}),
            encoding="utf-8",
        )
        analyzer = MetricsAnalyzer(metrics_dir=str(tmp_path))
        result = analyzer.load_metrics("2026-06-14")
        assert result is True
        assert len(analyzer.metrics_data) == 1

    def test_load_metrics_loads_session_jsonl(self, tmp_path: Path):
        date_dir = tmp_path / "2026-06-14"
        date_dir.mkdir()
        session_file = date_dir / "session.jsonl"
        session_file.write_text(
            '{"role": "Orchestrator", "tokens_in": 500, "cost": 0.05}\n'
            '{"role": "Engineer", "tokens_in": 100, "cost": 0.01}\n',
            encoding="utf-8",
        )
        analyzer = MetricsAnalyzer(metrics_dir=str(tmp_path))
        result = analyzer.load_metrics("2026-06-14")
        assert result is True
        assert len(analyzer.metrics_data) == 2


# ---------------------------------------------------------------------------
# MetricsAnalyzer initialization
# ---------------------------------------------------------------------------

class TestMetricsAnalyzerInit:
    """Tests for MetricsAnalyzer initialization."""

    def test_default_metrics_dir(self):
        import os
        analyzer = MetricsAnalyzer()
        assert "metrics" in str(analyzer.metrics_dir)

    def test_custom_metrics_dir(self, tmp_path: Path):
        analyzer = MetricsAnalyzer(metrics_dir=str(tmp_path))
        assert analyzer.metrics_dir == tmp_path

    def test_metrics_data_initially_empty(self, tmp_path: Path):
        analyzer = MetricsAnalyzer(metrics_dir=str(tmp_path))
        assert analyzer.metrics_data == []
