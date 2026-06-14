"""
Skill-level tests for doc-quality-monitor (MONITORING-001).

These tests verify the skill structure and basic functionality of
doc_quality_monitor.py. Comprehensive coverage exists in the top-level
tests/test_doc_quality_monitor.py (53 tests).

Phase W3-D: Added during Wave 3 skills consolidation (m3-skills-deprecation).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Path bootstrap
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from doc_quality_monitor import (
    Category,
    DocQualityReport,
    Issue,
    MonitorConfig,
    Severity,
    _SEVERITY_PENALTY,
)


class TestMonitorConfig:
    """Tests for MonitorConfig defaults and overrides."""

    def test_default_config_creates_instance(self):
        config = MonitorConfig()
        assert isinstance(config, MonitorConfig)

    def test_default_staleness_days_positive(self):
        config = MonitorConfig()
        assert config.staleness_days > 0

    def test_custom_staleness_days(self):
        config = MonitorConfig(staleness_days=30)
        assert config.staleness_days == 30

    def test_required_sections_is_list(self):
        config = MonitorConfig()
        assert isinstance(config.required_sections, list)

    def test_fail_under_is_float_or_int(self):
        config = MonitorConfig()
        assert isinstance(config.fail_under, (float, int))


class TestSeverityAndCategory:
    """Tests for Severity and Category enums."""

    def test_severity_error_value(self):
        assert Severity.ERROR.value == "error"

    def test_severity_warning_value(self):
        assert Severity.WARNING.value == "warning"

    def test_severity_info_value(self):
        assert Severity.INFO.value == "info"

    def test_severity_penalty_error_higher_than_warning(self):
        assert _SEVERITY_PENALTY[Severity.ERROR] > _SEVERITY_PENALTY[Severity.WARNING]

    def test_severity_penalty_warning_higher_than_info(self):
        assert _SEVERITY_PENALTY[Severity.WARNING] > _SEVERITY_PENALTY[Severity.INFO]

    def test_category_broken_link(self):
        assert Category.BROKEN_LINK.value == "BROKEN_LINK"

    def test_category_placeholder(self):
        assert Category.PLACEHOLDER.value == "PLACEHOLDER"

    def test_category_stale_doc(self):
        assert Category.STALE_DOC.value == "STALE_DOC"


class TestIssue:
    """Tests for Issue dataclass."""

    def test_issue_creates_with_required_fields(self):
        issue = Issue(
            file=Path("docs/test.md"),
            category=Category.PLACEHOLDER,
            severity=Severity.WARNING,
            message="TODO found on line 5",
            line=5,
        )
        assert issue.category == Category.PLACEHOLDER
        assert issue.severity == Severity.WARNING

    def test_issue_file_is_path(self):
        issue = Issue(
            file=Path("docs/test.md"),
            category=Category.STRUCTURE,
            severity=Severity.INFO,
            message="Missing H1",
            line=1,
        )
        assert isinstance(issue.file, Path)


class TestSkillDirectory:
    """Tests for skill directory structure."""

    def test_skill_md_exists(self):
        skill_dir = Path(__file__).parent.parent
        assert (skill_dir / "SKILL.md").exists()

    def test_scripts_dir_exists(self):
        scripts_dir = Path(__file__).parent.parent / "scripts"
        assert scripts_dir.exists()

    def test_main_script_exists(self):
        script = Path(__file__).parent.parent / "scripts" / "doc_quality_monitor.py"
        assert script.exists()
