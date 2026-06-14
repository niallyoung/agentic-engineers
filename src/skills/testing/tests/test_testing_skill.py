"""
Tests for the testing skill (test-sync-validator).

Phase W3-D: Added during Wave 3 skills consolidation to fix zero-test gap.
Target: ≥85% coverage on test_sync_validator.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Path bootstrap — point at the scripts dir where test_sync_validator.py lives
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from test_sync_validator import (
    ChangeType,
    Mismatch,
    MismatchSeverity,
)


# ---------------------------------------------------------------------------
# Skill directory structure tests
# ---------------------------------------------------------------------------

class TestSkillStructure:
    """Verify testing skill directory layout."""

    def test_skill_md_exists(self):
        skill_dir = Path(__file__).parent.parent
        assert (skill_dir / "SKILL.md").exists()

    def test_scripts_dir_exists(self):
        assert SCRIPTS_DIR.exists()

    def test_test_sync_validator_exists(self):
        assert (SCRIPTS_DIR / "test_sync_validator.py").exists()


# ---------------------------------------------------------------------------
# ChangeType enum tests
# ---------------------------------------------------------------------------

class TestChangeType:
    """Tests for ChangeType enum values."""

    def test_model_upgrade_value(self):
        assert ChangeType.MODEL_UPGRADE.value == "model_upgrade"

    def test_config_update_value(self):
        assert ChangeType.CONFIG_UPDATE.value == "config_update"

    def test_api_change_value(self):
        assert ChangeType.API_CHANGE.value == "api_change"

    def test_refactor_value(self):
        assert ChangeType.REFACTOR.value == "refactor"

    def test_documentation_value(self):
        assert ChangeType.DOCUMENTATION.value == "documentation"

    def test_unknown_value(self):
        assert ChangeType.UNKNOWN.value == "unknown"

    def test_all_change_types_count(self):
        # Ensure we test all 6 change types
        assert len(list(ChangeType)) == 6


# ---------------------------------------------------------------------------
# MismatchSeverity enum tests
# ---------------------------------------------------------------------------

class TestMismatchSeverity:
    """Tests for MismatchSeverity enum values."""

    def test_critical_value(self):
        assert MismatchSeverity.CRITICAL.value == "critical"

    def test_high_value(self):
        assert MismatchSeverity.HIGH.value == "high"

    def test_medium_value(self):
        assert MismatchSeverity.MEDIUM.value == "medium"

    def test_low_value(self):
        assert MismatchSeverity.LOW.value == "low"

    def test_all_severities_count(self):
        assert len(list(MismatchSeverity)) == 4


# ---------------------------------------------------------------------------
# Mismatch class tests
# ---------------------------------------------------------------------------

class TestMismatch:
    """Tests for Mismatch dataclass/class."""

    def _make_mismatch(self, severity=MismatchSeverity.HIGH) -> Mismatch:
        return Mismatch(
            test_file="tests/test_model.py",
            line=42,
            change_type=ChangeType.MODEL_UPGRADE.value,
            severity=severity.value,
            message="Model name changed from claude-2 to claude-3",
            affected_code="assert model == 'claude-2'",
            remediation="Update test to use 'claude-3'",
        )

    def test_mismatch_creates_with_fields(self):
        m = self._make_mismatch()
        assert m.test_file == "tests/test_model.py"
        assert m.line == 42

    def test_mismatch_to_dict_returns_dict(self):
        m = self._make_mismatch()
        d = m.to_dict()
        assert isinstance(d, dict)

    def test_mismatch_to_dict_has_test_file(self):
        m = self._make_mismatch()
        d = m.to_dict()
        assert "test_file" in d
        assert d["test_file"] == "tests/test_model.py"

    def test_mismatch_to_dict_has_line(self):
        m = self._make_mismatch()
        d = m.to_dict()
        assert "line" in d
        assert d["line"] == 42

    def test_mismatch_to_dict_has_severity(self):
        m = self._make_mismatch(MismatchSeverity.CRITICAL)
        d = m.to_dict()
        assert "severity" in d
        assert d["severity"] == "critical"

    def test_mismatch_to_dict_has_message(self):
        m = self._make_mismatch()
        d = m.to_dict()
        assert "message" in d

    def test_mismatch_to_dict_has_remediation(self):
        m = self._make_mismatch()
        d = m.to_dict()
        assert "remediation" in d

    def test_mismatch_change_type_stored(self):
        m = self._make_mismatch()
        assert m.change_type == ChangeType.MODEL_UPGRADE.value

    def test_mismatch_affected_code_stored(self):
        m = self._make_mismatch()
        assert "claude-2" in m.affected_code
