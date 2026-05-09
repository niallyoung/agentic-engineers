"""
Tests for ArtifactManager — DELEGATE/HANDBACK/FEEDBACK YAML block persistence.

Coverage targets: write_delegate, write_handback, write_feedback,
read_delegate, read_handback, read_feedback, list_artifacts, export_json.
"""

import json
import os
import pytest
import yaml
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from src.orchestration.agents.artifact_manager import ArtifactManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def artifact_manager(tmp_path):
    """ArtifactManager backed by a temp directory."""
    return ArtifactManager(base_dir=str(tmp_path / "artifacts"))


@pytest.fixture
def sample_delegate():
    return {
        "handoff_type": "DELEGATE",
        "task_id": "2025-01-01-test-task-abc123",
        "role": "engineer",
        "model": "claude-haiku-4.5",
        "effort": "medium",
        "scope": "Implement feature X with full test coverage",
    }


@pytest.fixture
def sample_handback():
    return {
        "handoff_type": "HANDBACK",
        "task_id": "2025-01-01-test-task-abc123",
        "status": "PASS",
        "quality_score": 92,
        "deliverables": ["Feature X implemented"],
    }


@pytest.fixture
def sample_feedback():
    return {
        "handoff_type": "FEEDBACK",
        "task_id": "2025-01-01-test-task-abc123",
        "model_recommendation": "claude-haiku-4.5",
        "confidence": 0.90,
    }


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestArtifactManagerInit:
    def test_init_creates_base_dir(self, tmp_path):
        """__init__ must create the base directory if it does not exist."""
        base_dir = str(tmp_path / "new_artifacts")
        assert not Path(base_dir).exists()
        ArtifactManager(base_dir=base_dir)
        assert Path(base_dir).exists()

    def test_init_default_base_dir_is_artifacts(self, tmp_path, monkeypatch):
        """Default base_dir is 'artifacts' relative to CWD."""
        monkeypatch.chdir(tmp_path)
        am = ArtifactManager()
        assert am.base_dir == "artifacts"

    def test_init_accepts_custom_base_dir(self, tmp_path):
        """Custom base_dir is stored on the instance."""
        base_dir = str(tmp_path / "custom")
        am = ArtifactManager(base_dir=base_dir)
        assert am.base_dir == base_dir


# ---------------------------------------------------------------------------
# write_delegate
# ---------------------------------------------------------------------------

class TestWriteDelegate:
    def test_write_delegate_returns_filepath(self, artifact_manager, sample_delegate):
        """write_delegate returns the path to the written file."""
        path = artifact_manager.write_delegate("task-001", sample_delegate)
        assert path.endswith("DELEGATE-task-001.yaml")

    def test_write_delegate_file_exists(self, artifact_manager, sample_delegate):
        """The written file must exist on disk."""
        path = artifact_manager.write_delegate("task-001", sample_delegate)
        assert Path(path).exists()

    def test_write_delegate_content_is_valid_yaml(self, artifact_manager, sample_delegate):
        """Written DELEGATE file must be parseable YAML with correct data."""
        path = artifact_manager.write_delegate("task-001", sample_delegate)
        with open(path) as f:
            data = yaml.safe_load(f)
        assert data["task_id"] == sample_delegate["task_id"]
        assert data["role"] == sample_delegate["role"]

    def test_write_delegate_organises_by_date(self, artifact_manager, sample_delegate):
        """DELEGATE files must be stored under a YYYY-MM-DD subdirectory."""
        path = artifact_manager.write_delegate("task-001", sample_delegate)
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in path

    def test_write_delegate_overwrites_existing(self, artifact_manager):
        """Writing again with same task_id overwrites the previous file."""
        delegate_v1 = {"version": 1}
        delegate_v2 = {"version": 2}
        artifact_manager.write_delegate("task-001", delegate_v1)
        path = artifact_manager.write_delegate("task-001", delegate_v2)
        with open(path) as f:
            data = yaml.safe_load(f)
        assert data["version"] == 2


# ---------------------------------------------------------------------------
# write_handback
# ---------------------------------------------------------------------------

class TestWriteHandback:
    def test_write_handback_returns_filepath(self, artifact_manager, sample_handback):
        path = artifact_manager.write_handback("task-001", sample_handback)
        assert path.endswith("HANDBACK-task-001.yaml")

    def test_write_handback_file_exists(self, artifact_manager, sample_handback):
        path = artifact_manager.write_handback("task-001", sample_handback)
        assert Path(path).exists()

    def test_write_handback_content_roundtrip(self, artifact_manager, sample_handback):
        path = artifact_manager.write_handback("task-001", sample_handback)
        with open(path) as f:
            data = yaml.safe_load(f)
        assert data["quality_score"] == 92
        assert data["status"] == "PASS"


# ---------------------------------------------------------------------------
# write_feedback
# ---------------------------------------------------------------------------

class TestWriteFeedback:
    def test_write_feedback_returns_filepath(self, artifact_manager, sample_feedback):
        path = artifact_manager.write_feedback("task-001", sample_feedback)
        assert path.endswith("FEEDBACK-task-001.yaml")

    def test_write_feedback_file_exists(self, artifact_manager, sample_feedback):
        path = artifact_manager.write_feedback("task-001", sample_feedback)
        assert Path(path).exists()

    def test_write_feedback_content_roundtrip(self, artifact_manager, sample_feedback):
        path = artifact_manager.write_feedback("task-001", sample_feedback)
        with open(path) as f:
            data = yaml.safe_load(f)
        assert data["model_recommendation"] == "claude-haiku-4.5"


# ---------------------------------------------------------------------------
# read_delegate
# ---------------------------------------------------------------------------

class TestReadDelegate:
    def test_read_delegate_returns_dict(self, artifact_manager, sample_delegate):
        """read_delegate returns the written DELEGATE as a dict."""
        artifact_manager.write_delegate("task-001", sample_delegate)
        result = artifact_manager.read_delegate("task-001")
        assert isinstance(result, dict)
        assert result["task_id"] == sample_delegate["task_id"]

    def test_read_delegate_with_explicit_date(self, artifact_manager, sample_delegate):
        """read_delegate accepts an explicit date string."""
        today = datetime.now().strftime("%Y-%m-%d")
        artifact_manager.write_delegate("task-001", sample_delegate)
        result = artifact_manager.read_delegate("task-001", date=today)
        assert result["role"] == "engineer"

    def test_read_delegate_raises_file_not_found(self, artifact_manager):
        """read_delegate raises FileNotFoundError when file is missing."""
        with pytest.raises(FileNotFoundError, match="DELEGATE not found"):
            artifact_manager.read_delegate("nonexistent-task")

    def test_read_delegate_raises_for_wrong_date(self, artifact_manager, sample_delegate):
        """read_delegate raises FileNotFoundError for a date with no file."""
        artifact_manager.write_delegate("task-001", sample_delegate)
        with pytest.raises(FileNotFoundError):
            artifact_manager.read_delegate("task-001", date="1999-01-01")


# ---------------------------------------------------------------------------
# read_handback
# ---------------------------------------------------------------------------

class TestReadHandback:
    def test_read_handback_returns_dict(self, artifact_manager, sample_handback):
        artifact_manager.write_handback("task-001", sample_handback)
        result = artifact_manager.read_handback("task-001")
        assert result["quality_score"] == 92

    def test_read_handback_raises_file_not_found(self, artifact_manager):
        with pytest.raises(FileNotFoundError, match="HANDBACK not found"):
            artifact_manager.read_handback("missing-task")


# ---------------------------------------------------------------------------
# read_feedback
# ---------------------------------------------------------------------------

class TestReadFeedback:
    def test_read_feedback_returns_dict(self, artifact_manager, sample_feedback):
        artifact_manager.write_feedback("task-001", sample_feedback)
        result = artifact_manager.read_feedback("task-001")
        assert result["confidence"] == 0.90

    def test_read_feedback_raises_file_not_found(self, artifact_manager):
        with pytest.raises(FileNotFoundError, match="FEEDBACK not found"):
            artifact_manager.read_feedback("missing-task")


# ---------------------------------------------------------------------------
# list_artifacts
# ---------------------------------------------------------------------------

class TestListArtifacts:
    def test_list_artifacts_empty_when_no_date_dir(self, artifact_manager):
        """list_artifacts returns empty lists when no date directory exists."""
        result = artifact_manager.list_artifacts(date="1900-01-01")
        assert result == {"delegates": [], "handbacks": [], "feedbacks": []}

    def test_list_artifacts_returns_all_types(self, artifact_manager, sample_delegate,
                                               sample_handback, sample_feedback):
        """list_artifacts returns all three artifact types."""
        today = datetime.now().strftime("%Y-%m-%d")
        artifact_manager.write_delegate("task-001", sample_delegate)
        artifact_manager.write_handback("task-001", sample_handback)
        artifact_manager.write_feedback("task-001", sample_feedback)

        result = artifact_manager.list_artifacts(date=today)
        assert "DELEGATE-task-001.yaml" in result["delegates"]
        assert "HANDBACK-task-001.yaml" in result["handbacks"]
        assert "FEEDBACK-task-001.yaml" in result["feedbacks"]

    def test_list_artifacts_returns_sorted_filenames(self, artifact_manager, sample_delegate):
        """Returned filenames are sorted."""
        today = datetime.now().strftime("%Y-%m-%d")
        artifact_manager.write_delegate("task-zzz", sample_delegate)
        artifact_manager.write_delegate("task-aaa", sample_delegate)
        result = artifact_manager.list_artifacts(date=today)
        assert result["delegates"] == sorted(result["delegates"])

    def test_list_artifacts_defaults_to_today(self, artifact_manager, sample_delegate):
        """list_artifacts without date uses today."""
        artifact_manager.write_delegate("task-today", sample_delegate)
        result = artifact_manager.list_artifacts()
        assert "DELEGATE-task-today.yaml" in result["delegates"]

    def test_list_artifacts_only_own_date(self, artifact_manager, sample_delegate):
        """Artifacts from today do not appear when listing a different date."""
        artifact_manager.write_delegate("task-001", sample_delegate)
        result = artifact_manager.list_artifacts(date="2000-01-01")
        assert result["delegates"] == []


# ---------------------------------------------------------------------------
# export_json
# ---------------------------------------------------------------------------

class TestExportJson:
    def test_export_json_returns_string(self, artifact_manager, sample_delegate):
        artifact_manager.write_delegate("task-001", sample_delegate)
        result = artifact_manager.export_json("task-001")
        assert isinstance(result, str)

    def test_export_json_valid_json(self, artifact_manager, sample_delegate):
        """export_json must return parseable JSON."""
        artifact_manager.write_delegate("task-001", sample_delegate)
        result = artifact_manager.export_json("task-001")
        data = json.loads(result)
        assert data["task_id"] == "task-001"

    def test_export_json_includes_delegate_when_present(self, artifact_manager, sample_delegate):
        artifact_manager.write_delegate("task-001", sample_delegate)
        data = json.loads(artifact_manager.export_json("task-001"))
        assert data["delegate"] is not None
        assert data["handback"] is None
        assert data["feedback"] is None

    def test_export_json_includes_all_three_blocks(self, artifact_manager, sample_delegate,
                                                    sample_handback, sample_feedback):
        artifact_manager.write_delegate("task-001", sample_delegate)
        artifact_manager.write_handback("task-001", sample_handback)
        artifact_manager.write_feedback("task-001", sample_feedback)
        data = json.loads(artifact_manager.export_json("task-001"))
        assert data["delegate"] is not None
        assert data["handback"] is not None
        assert data["feedback"] is not None

    def test_export_json_missing_all_blocks(self, artifact_manager):
        """export_json with no artifacts returns null for all blocks."""
        today = datetime.now().strftime("%Y-%m-%d")
        data = json.loads(artifact_manager.export_json("ghost-task", date=today))
        assert data["delegate"] is None
        assert data["handback"] is None
        assert data["feedback"] is None

    def test_export_json_includes_task_id_and_date(self, artifact_manager, sample_delegate):
        today = datetime.now().strftime("%Y-%m-%d")
        artifact_manager.write_delegate("task-001", sample_delegate)
        data = json.loads(artifact_manager.export_json("task-001"))
        assert data["task_id"] == "task-001"
        assert data["date"] == today
