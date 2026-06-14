"""
Smoke tests for metrics-etl skill.

Phase W3-D: Added during Wave 3 skills consolidation to fix zero-test gap.
Target: Minimal smoke tests (MetricsETL class and ETL pipeline basics).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Path bootstrap
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import importlib
metrics_etl_module = importlib.import_module("metrics-etl")
MetricsETL = metrics_etl_module.MetricsETL
PROMETHEUS_FORMAT = metrics_etl_module.PROMETHEUS_FORMAT


# ---------------------------------------------------------------------------
# Skill structure
# ---------------------------------------------------------------------------

class TestSkillStructure:
    """Verify metrics-etl skill directory layout."""

    def test_skill_md_exists(self):
        skill_dir = Path(__file__).parent.parent
        assert (skill_dir / "SKILL.md").exists()

    def test_scripts_dir_exists(self):
        assert SCRIPTS_DIR.exists()

    def test_metrics_etl_script_exists(self):
        assert (SCRIPTS_DIR / "metrics-etl.py").exists()


# ---------------------------------------------------------------------------
# PROMETHEUS_FORMAT constant
# ---------------------------------------------------------------------------

class TestPrometheusFormat:
    """Tests for PROMETHEUS_FORMAT constant."""

    def test_prometheus_format_is_string(self):
        assert isinstance(PROMETHEUS_FORMAT, str)

    def test_prometheus_format_contains_help(self):
        assert "{help}" in PROMETHEUS_FORMAT

    def test_prometheus_format_contains_metric_lines(self):
        assert "{metric_lines}" in PROMETHEUS_FORMAT


# ---------------------------------------------------------------------------
# MetricsETL initialization
# ---------------------------------------------------------------------------

class TestMetricsETLInit:
    """Tests for MetricsETL initialization."""

    def test_default_metrics_dir(self):
        etl = MetricsETL()
        assert "metrics" in str(etl.metrics_dir)

    def test_custom_metrics_dir(self, tmp_path: Path):
        etl = MetricsETL(metrics_dir=str(tmp_path))
        assert etl.metrics_dir == tmp_path

    def test_aggregated_initially_empty(self, tmp_path: Path):
        etl = MetricsETL(metrics_dir=str(tmp_path))
        assert etl.aggregated == {}


# ---------------------------------------------------------------------------
# MetricsETL.aggregate_metrics
# ---------------------------------------------------------------------------

class TestAggregateMetrics:
    """Tests for MetricsETL.aggregate_metrics()."""

    def test_aggregate_returns_dict(self, tmp_path: Path):
        etl = MetricsETL(metrics_dir=str(tmp_path))
        result = etl.aggregate_metrics(days=1)
        assert isinstance(result, dict)

    def test_aggregate_empty_dir_returns_empty(self, tmp_path: Path):
        etl = MetricsETL(metrics_dir=str(tmp_path))
        result = etl.aggregate_metrics(days=7)
        assert len(result) == 0

    def test_aggregate_loads_task_json(self, tmp_path: Path):
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        date_dir = tmp_path / today
        date_dir.mkdir()
        (date_dir / "task_001.json").write_text(
            json.dumps({
                "role": "Engineer",
                "model": "haiku",
                "task_type": "implementation",
                "tokens_in": 500,
                "tokens_out": 200,
                "cost": 0.05,
                "quality_score": 0.9,
            }),
            encoding="utf-8",
        )
        etl = MetricsETL(metrics_dir=str(tmp_path))
        result = etl.aggregate_metrics(days=1)
        assert today in result
        assert result[today]["total_tokens"] == 700
        assert abs(result[today]["total_cost"] - 0.05) < 0.001

    def test_aggregate_role_breakdown(self, tmp_path: Path):
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        date_dir = tmp_path / today
        date_dir.mkdir()
        (date_dir / "task_001.json").write_text(
            json.dumps({
                "role": "Engineer",
                "model": "haiku",
                "task_type": "implementation",
                "tokens_in": 100,
                "tokens_out": 50,
                "cost": 0.01,
                "quality_score": 0.8,
            }),
            encoding="utf-8",
        )
        etl = MetricsETL(metrics_dir=str(tmp_path))
        result = etl.aggregate_metrics(days=1)
        assert "Engineer" in result[today]["role_breakdown"]

    def test_aggregate_model_breakdown(self, tmp_path: Path):
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        date_dir = tmp_path / today
        date_dir.mkdir()
        (date_dir / "task_001.json").write_text(
            json.dumps({
                "role": "Engineer",
                "model": "haiku",
                "task_type": "implementation",
                "tokens_in": 100,
                "tokens_out": 50,
                "cost": 0.01,
                "quality_score": 0.8,
            }),
            encoding="utf-8",
        )
        etl = MetricsETL(metrics_dir=str(tmp_path))
        result = etl.aggregate_metrics(days=1)
        assert "haiku" in result[today]["model_breakdown"]
