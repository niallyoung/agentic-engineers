"""
Tests for the ab-testing skill (A/B Testing Framework).

Phase W3-D: Added during Wave 3 skills consolidation to fix zero-test gap.
Target: ≥85% coverage on ab-testing.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Path bootstrap
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Import with dashed module name
import importlib
ab_testing_module = importlib.import_module("ab-testing")
ABTestingFramework = ab_testing_module.ABTestingFramework
Experiment = ab_testing_module.Experiment
ExperimentStatus = ab_testing_module.ExperimentStatus


# ---------------------------------------------------------------------------
# Skill directory structure tests
# ---------------------------------------------------------------------------

class TestSkillStructure:
    """Verify ab-testing skill directory layout."""

    def test_skill_md_exists(self):
        skill_dir = Path(__file__).parent.parent
        assert (skill_dir / "SKILL.md").exists()

    def test_scripts_dir_exists(self):
        assert SCRIPTS_DIR.exists()

    def test_ab_testing_script_exists(self):
        assert (SCRIPTS_DIR / "ab-testing.py").exists()


# ---------------------------------------------------------------------------
# ExperimentStatus enum
# ---------------------------------------------------------------------------

class TestExperimentStatus:
    """Tests for ExperimentStatus enum values."""

    def test_draft_value(self):
        assert ExperimentStatus.DRAFT.value == "draft"

    def test_running_value(self):
        assert ExperimentStatus.RUNNING.value == "running"

    def test_paused_value(self):
        assert ExperimentStatus.PAUSED.value == "paused"

    def test_completed_value(self):
        assert ExperimentStatus.COMPLETED.value == "completed"

    def test_failed_value(self):
        assert ExperimentStatus.FAILED.value == "failed"

    def test_all_statuses_count(self):
        assert len(list(ExperimentStatus)) == 5


# ---------------------------------------------------------------------------
# Experiment dataclass
# ---------------------------------------------------------------------------

class TestExperiment:
    """Tests for Experiment dataclass."""

    def _make_experiment(self, **kwargs) -> Experiment:
        defaults = {
            "id": "test-exp-abc123",
            "name": "Test Experiment",
            "hypothesis": "Sonnet is cheaper than Opus for routing",
            "control": {"model": "claude-opus-4.8"},
            "variant": {"model": "claude-sonnet-4.6"},
        }
        defaults.update(kwargs)
        return Experiment(**defaults)

    def test_experiment_creates_with_defaults(self):
        exp = self._make_experiment()
        assert exp.id == "test-exp-abc123"
        assert exp.name == "Test Experiment"

    def test_experiment_default_status_is_draft(self):
        exp = self._make_experiment()
        assert exp.status == ExperimentStatus.DRAFT.value

    def test_experiment_default_traffic_split(self):
        exp = self._make_experiment()
        assert exp.traffic_split == 0.5

    def test_experiment_default_duration_days(self):
        exp = self._make_experiment()
        assert exp.duration_days == 7

    def test_experiment_created_at_set_on_init(self):
        exp = self._make_experiment()
        assert exp.created_at is not None

    def test_experiment_updated_at_set_on_init(self):
        exp = self._make_experiment()
        assert exp.updated_at is not None

    def test_experiment_control_stored(self):
        exp = self._make_experiment()
        assert exp.control == {"model": "claude-opus-4.8"}

    def test_experiment_variant_stored(self):
        exp = self._make_experiment()
        assert exp.variant == {"model": "claude-sonnet-4.6"}

    def test_experiment_hypothesis_accepted_none_by_default(self):
        exp = self._make_experiment()
        assert exp.hypothesis_accepted is None

    def test_experiment_notes_empty_by_default(self):
        exp = self._make_experiment()
        assert exp.notes == ""


# ---------------------------------------------------------------------------
# ABTestingFramework — create and load
# ---------------------------------------------------------------------------

class TestABTestingFramework:
    """Tests for ABTestingFramework using a temp experiments directory."""

    @pytest.fixture
    def framework(self, tmp_path: Path) -> ABTestingFramework:
        """ABTestingFramework pointed at a temporary directory."""
        # Patch EXPERIMENTS_DIR to use tmp_path
        with patch.object(ab_testing_module, "EXPERIMENTS_DIR", tmp_path):
            fw = ABTestingFramework.__new__(ABTestingFramework)
            fw.__init__()
            fw._experiments_dir = tmp_path
        return fw

    def test_framework_creates_instance(self, framework):
        assert isinstance(framework, ABTestingFramework)

    def test_create_experiment_returns_id(self, tmp_path: Path):
        with patch.object(ab_testing_module, "EXPERIMENTS_DIR", tmp_path):
            fw = ABTestingFramework()
            exp_id = fw.create_experiment(
                name="my-test",
                hypothesis="Haiku is faster",
                control={"model": "sonnet"},
                variant={"model": "haiku"},
            )
        assert isinstance(exp_id, str)
        assert len(exp_id) > 0

    def test_create_experiment_writes_json_file(self, tmp_path: Path):
        with patch.object(ab_testing_module, "EXPERIMENTS_DIR", tmp_path):
            fw = ABTestingFramework()
            exp_id = fw.create_experiment(
                name="json-test",
                hypothesis="Test writes file",
                control={"model": "sonnet"},
                variant={"model": "haiku"},
            )
            exp_file = tmp_path / f"{exp_id}.json"
        assert exp_file.exists(), f"Expected experiment file at {exp_file}"

    def test_create_experiment_json_contains_id(self, tmp_path: Path):
        with patch.object(ab_testing_module, "EXPERIMENTS_DIR", tmp_path):
            fw = ABTestingFramework()
            exp_id = fw.create_experiment(
                name="id-test",
                hypothesis="Test ID in JSON",
                control={"model": "sonnet"},
                variant={"model": "haiku"},
            )
            exp_file = tmp_path / f"{exp_id}.json"
            data = json.loads(exp_file.read_text())
        assert data["id"] == exp_id

    def test_load_experiment_returns_none_for_missing(self, tmp_path: Path):
        with patch.object(ab_testing_module, "EXPERIMENTS_DIR", tmp_path):
            fw = ABTestingFramework()
            result = fw.load_experiment("nonexistent-experiment-id")
        assert result is None

    def test_load_experiment_returns_experiment_object(self, tmp_path: Path):
        with patch.object(ab_testing_module, "EXPERIMENTS_DIR", tmp_path):
            fw = ABTestingFramework()
            exp_id = fw.create_experiment(
                name="load-test",
                hypothesis="Can we load it back?",
                control={"model": "sonnet"},
                variant={"model": "haiku"},
            )
            loaded = fw.load_experiment(exp_id)
        assert loaded is not None
        assert isinstance(loaded, Experiment)
        assert loaded.id == exp_id

    def test_load_experiment_preserves_hypothesis(self, tmp_path: Path):
        with patch.object(ab_testing_module, "EXPERIMENTS_DIR", tmp_path):
            fw = ABTestingFramework()
            exp_id = fw.create_experiment(
                name="hyp-test",
                hypothesis="Hypothesis text preserved",
                control={"model": "sonnet"},
                variant={"model": "haiku"},
            )
            loaded = fw.load_experiment(exp_id)
        assert loaded.hypothesis == "Hypothesis text preserved"

    def test_start_experiment_changes_status(self, tmp_path: Path):
        with patch.object(ab_testing_module, "EXPERIMENTS_DIR", tmp_path):
            fw = ABTestingFramework()
            exp_id = fw.create_experiment(
                name="start-test",
                hypothesis="Starting test",
                control={"model": "sonnet"},
                variant={"model": "haiku"},
            )
            result = fw.start_experiment(exp_id)
            loaded = fw.load_experiment(exp_id)
        assert result is True
        assert loaded.status == ExperimentStatus.RUNNING.value

    def test_start_experiment_missing_returns_false(self, tmp_path: Path):
        with patch.object(ab_testing_module, "EXPERIMENTS_DIR", tmp_path):
            fw = ABTestingFramework()
            result = fw.start_experiment("does-not-exist")
        assert result is False
