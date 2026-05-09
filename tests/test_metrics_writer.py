"""
Tests for MetricsWriter — persistence and aggregation of task execution metrics.

Covers: TaskMetrics.to_dict, write_metrics, load_metrics, aggregate_metrics.
"""

import os
import yaml
import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.orchestration.agents.metrics_writer import MetricsWriter, TaskMetrics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def metrics_writer(tmp_path):
    """MetricsWriter backed by a temporary directory."""
    return MetricsWriter(metrics_dir=str(tmp_path / "metrics"))


@pytest.fixture
def minimal_metrics():
    """Minimal valid metrics dict required by write_metrics."""
    return {
        "task_id": "test-task-001",
        "timestamp": "2025-01-15T10:00:00",
        "quality_score_validator": 92,
    }


@pytest.fixture
def full_metrics():
    """Full metrics dict with all fields."""
    return {
        "task_id": "test-task-001",
        "timestamp": "2025-01-15T10:00:00",
        "role": "engineer",
        "model": "claude-haiku-4.5",
        "effort": "medium",
        "effort_actual": 4.5,
        "tokens_in": 1000,
        "tokens_out": 500,
        "total_tokens": 1500,
        "duration_minutes": 30,
        "quality_score_validator": 92,
        "quality_score_agent_self": 90,
        "status": "complete",
        "retry_count": 0,
        "test_coverage": 95.0,
        "deliverables_count": 3,
        "efficiency_score": 6.13,
        "rework_cost_ratio": 1.0,
    }


# ---------------------------------------------------------------------------
# TaskMetrics dataclass
# ---------------------------------------------------------------------------

class TestTaskMetrics:
    def test_to_dict_returns_dict(self):
        """TaskMetrics.to_dict returns a dictionary."""
        metrics = TaskMetrics(
            task_id="task-001",
            timestamp="2025-01-15T10:00:00",
            role="engineer",
            model="claude-haiku-4.5",
            effort="medium",
            effort_actual=4.0,
            tokens_in=1000,
            tokens_out=500,
            total_tokens=1500,
            duration_minutes=30,
            quality_score_validator=90,
            quality_score_agent_self=88,
            status="complete",
        )
        result = metrics.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_includes_required_fields(self):
        """to_dict includes all required metrics fields."""
        metrics = TaskMetrics(
            task_id="task-001",
            timestamp="2025-01-15T10:00:00",
            role="engineer",
            model="claude-haiku-4.5",
            effort="medium",
            effort_actual=4.0,
            tokens_in=1000,
            tokens_out=500,
            total_tokens=1500,
            duration_minutes=30,
            quality_score_validator=90,
            quality_score_agent_self=88,
            status="complete",
        )
        result = metrics.to_dict()
        assert result["task_id"] == "task-001"
        assert result["quality_score_validator"] == 90
        assert result["status"] == "complete"

    def test_to_dict_excludes_none_values(self):
        """to_dict excludes None values."""
        metrics = TaskMetrics(
            task_id="task-001",
            timestamp="2025-01-15T10:00:00",
            role="engineer",
            model="claude-haiku-4.5",
            effort="medium",
            effort_actual=4.0,
            tokens_in=1000,
            tokens_out=500,
            total_tokens=1500,
            duration_minutes=30,
            quality_score_validator=90,
            quality_score_agent_self=88,
            status="complete",
            first_try_quality=None,  # explicitly None
        )
        result = metrics.to_dict()
        assert "first_try_quality" not in result

    def test_default_retry_count_is_zero(self):
        metrics = TaskMetrics(
            task_id="task-001",
            timestamp="2025-01-15T10:00:00",
            role="engineer",
            model="claude-haiku-4.5",
            effort="medium",
            effort_actual=4.0,
            tokens_in=1000,
            tokens_out=500,
            total_tokens=1500,
            duration_minutes=30,
            quality_score_validator=90,
            quality_score_agent_self=88,
            status="complete",
        )
        assert metrics.retry_count == 0


# ---------------------------------------------------------------------------
# MetricsWriter.__init__
# ---------------------------------------------------------------------------

class TestMetricsWriterInit:
    def test_creates_metrics_directory(self, tmp_path):
        """MetricsWriter creates the metrics directory on init."""
        metrics_dir = tmp_path / "new_metrics"
        assert not metrics_dir.exists()
        MetricsWriter(metrics_dir=str(metrics_dir))
        assert metrics_dir.exists()

    def test_metrics_dir_stored_as_path(self, tmp_path):
        """MetricsWriter stores metrics_dir as a Path object."""
        metrics_dir = tmp_path / "metrics"
        mw = MetricsWriter(metrics_dir=str(metrics_dir))
        assert isinstance(mw.metrics_dir, Path)


# ---------------------------------------------------------------------------
# write_metrics
# ---------------------------------------------------------------------------

class TestWriteMetrics:
    def test_write_metrics_returns_filepath(self, metrics_writer, minimal_metrics):
        """write_metrics returns the path to the written file."""
        filepath = metrics_writer.write_metrics(minimal_metrics)
        assert isinstance(filepath, str)
        assert filepath.endswith(".yaml")

    def test_write_metrics_file_exists_on_disk(self, metrics_writer, minimal_metrics):
        """The written metrics file must exist on disk."""
        filepath = metrics_writer.write_metrics(minimal_metrics)
        assert Path(filepath).exists()

    def test_write_metrics_filename_includes_date(self, metrics_writer, minimal_metrics):
        """Filename includes date from timestamp field."""
        filepath = metrics_writer.write_metrics(minimal_metrics)
        assert "2025-01-15" in filepath

    def test_write_metrics_filename_includes_task_id(self, metrics_writer, minimal_metrics):
        """Filename includes task_id."""
        filepath = metrics_writer.write_metrics(minimal_metrics)
        assert "test-task-001" in filepath

    def test_write_metrics_content_is_valid_yaml(self, metrics_writer, full_metrics):
        """Written file is parseable YAML with correct data."""
        filepath = metrics_writer.write_metrics(full_metrics)
        with open(filepath) as f:
            data = yaml.safe_load(f)
        assert data["task_id"] == full_metrics["task_id"]
        assert data["quality_score_validator"] == 92

    def test_write_metrics_missing_task_id_raises(self, metrics_writer):
        """write_metrics raises ValueError when task_id is missing."""
        with pytest.raises(ValueError, match="Missing required metrics fields"):
            metrics_writer.write_metrics({
                "timestamp": "2025-01-15T10:00:00",
                "quality_score_validator": 90,
            })

    def test_write_metrics_missing_timestamp_raises(self, metrics_writer):
        """write_metrics raises ValueError when timestamp is missing."""
        with pytest.raises(ValueError, match="Missing required metrics fields"):
            metrics_writer.write_metrics({
                "task_id": "task-001",
                "quality_score_validator": 90,
            })

    def test_write_metrics_missing_quality_score_raises(self, metrics_writer):
        """write_metrics raises ValueError when quality_score_validator is missing."""
        with pytest.raises(ValueError, match="Missing required metrics fields"):
            metrics_writer.write_metrics({
                "task_id": "task-001",
                "timestamp": "2025-01-15T10:00:00",
            })

    def test_write_metrics_invalid_timestamp_uses_today(self, metrics_writer):
        """Invalid timestamp falls back to today's date."""
        metrics = {
            "task_id": "fallback-task",
            "timestamp": "not-a-date",
            "quality_score_validator": 85,
        }
        filepath = metrics_writer.write_metrics(metrics)
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in filepath


# ---------------------------------------------------------------------------
# load_metrics
# ---------------------------------------------------------------------------

class TestLoadMetrics:
    def test_load_metrics_returns_dict(self, metrics_writer, full_metrics):
        """load_metrics returns a dict with the written data."""
        metrics_writer.write_metrics(full_metrics)
        result = metrics_writer.load_metrics("test-task-001", date_str="2025-01-15")
        assert isinstance(result, dict)
        assert result["task_id"] == "test-task-001"

    def test_load_metrics_preserves_quality_score(self, metrics_writer, full_metrics):
        """Loaded metrics preserve quality_score_validator."""
        metrics_writer.write_metrics(full_metrics)
        result = metrics_writer.load_metrics("test-task-001", date_str="2025-01-15")
        assert result["quality_score_validator"] == 92

    def test_load_metrics_not_found_raises(self, metrics_writer):
        """load_metrics raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError, match="Metrics file not found"):
            metrics_writer.load_metrics("ghost-task", date_str="2000-01-01")

    def test_load_metrics_defaults_to_today(self, metrics_writer):
        """load_metrics with no date defaults to today."""
        today = datetime.now().strftime("%Y-%m-%d")
        metrics = {
            "task_id": "today-task",
            "timestamp": f"{today}T10:00:00",
            "quality_score_validator": 88,
        }
        metrics_writer.write_metrics(metrics)
        result = metrics_writer.load_metrics("today-task")
        assert result["task_id"] == "today-task"


# ---------------------------------------------------------------------------
# aggregate_metrics
# ---------------------------------------------------------------------------

class TestAggregateMetrics:
    def test_aggregate_empty_returns_zero_task_count(self, metrics_writer):
        """aggregate_metrics returns task_count=0 when no files found."""
        result = metrics_writer.aggregate_metrics(date_str="1900-01-01")
        assert result["task_count"] == 0

    def test_aggregate_single_task(self, metrics_writer, full_metrics):
        """aggregate_metrics with one task produces correct stats."""
        metrics_writer.write_metrics(full_metrics)
        result = metrics_writer.aggregate_metrics(date_str="2025-01-15")
        assert result["task_count"] == 1
        assert result["quality_score"]["avg"] == 92

    def test_aggregate_multiple_tasks_averages_quality(self, metrics_writer):
        """aggregate_metrics correctly averages quality scores."""
        for i, score in enumerate([80, 90, 100]):
            metrics_writer.write_metrics({
                "task_id": f"task-{i:03d}",
                "timestamp": "2025-02-01T10:00:00",
                "quality_score_validator": score,
                "status": "complete",
                "retry_count": 0,
            })
        result = metrics_writer.aggregate_metrics(date_str="2025-02-01")
        assert result["task_count"] == 3
        assert result["quality_score"]["avg"] == pytest.approx(90.0)
        assert result["quality_score"]["min"] == 80
        assert result["quality_score"]["max"] == 100

    def test_aggregate_completion_rate(self, metrics_writer):
        """aggregate_metrics calculates completion_rate correctly."""
        for i, status in enumerate(["complete", "complete", "failed"]):
            metrics_writer.write_metrics({
                "task_id": f"rate-task-{i}",
                "timestamp": "2025-03-01T10:00:00",
                "quality_score_validator": 85,
                "status": status,
                "retry_count": 0,
            })
        result = metrics_writer.aggregate_metrics(date_str="2025-03-01")
        assert result["completion_rate"] == pytest.approx(2 / 3)

    def test_aggregate_retry_rate(self, metrics_writer):
        """aggregate_metrics calculates retry_rate correctly."""
        for i, retries in enumerate([0, 0, 2]):
            metrics_writer.write_metrics({
                "task_id": f"retry-task-{i}",
                "timestamp": "2025-04-01T10:00:00",
                "quality_score_validator": 85,
                "status": "complete",
                "retry_count": retries,
            })
        result = metrics_writer.aggregate_metrics(date_str="2025-04-01")
        assert result["retry_rate"] == pytest.approx(1 / 3)

    def test_aggregate_total_tokens(self, metrics_writer):
        """aggregate_metrics sums total_tokens across all tasks."""
        for i in range(3):
            metrics_writer.write_metrics({
                "task_id": f"token-task-{i}",
                "timestamp": "2025-05-01T10:00:00",
                "quality_score_validator": 85,
                "status": "complete",
                "retry_count": 0,
                "total_tokens": 1000,
            })
        result = metrics_writer.aggregate_metrics(date_str="2025-05-01")
        assert result["tokens"]["total"] == 3000

    def test_aggregate_result_contains_date(self, metrics_writer):
        """Aggregated result includes the date field."""
        result = metrics_writer.aggregate_metrics(date_str="2025-06-01")
        assert result["date"] == "2025-06-01"

    def test_aggregate_tasks_list(self, metrics_writer):
        """Aggregated result includes a list of task_ids."""
        metrics_writer.write_metrics({
            "task_id": "listed-task",
            "timestamp": "2025-07-01T10:00:00",
            "quality_score_validator": 85,
        })
        result = metrics_writer.aggregate_metrics(date_str="2025-07-01")
        assert "listed-task" in result["tasks"]

    def test_aggregate_writes_output_file_when_specified(self, metrics_writer, tmp_path):
        """aggregate_metrics writes a YAML report when output_file is specified."""
        metrics_writer.write_metrics({
            "task_id": "report-task",
            "timestamp": "2025-08-01T10:00:00",
            "quality_score_validator": 88,
        })
        output_file = str(tmp_path / "report.yaml")
        metrics_writer.aggregate_metrics(date_str="2025-08-01", output_file=output_file)
        assert Path(output_file).exists()
        with open(output_file) as f:
            report = yaml.safe_load(f)
        assert report["task_count"] == 1

    def test_aggregate_defaults_to_today(self, metrics_writer):
        """aggregate_metrics without date argument uses today."""
        today = datetime.now().strftime("%Y-%m-%d")
        metrics_writer.write_metrics({
            "task_id": "today-agg-task",
            "timestamp": f"{today}T10:00:00",
            "quality_score_validator": 91,
        })
        result = metrics_writer.aggregate_metrics()
        assert result["date"] == today
