# -*- coding: utf-8 -*-
"""
tests/test_doc_quality_monitor.py — Doc-Quality-Monitor Skill (MONITORING-001).

TDD test suite for automated documentation-quality monitoring.

Coverage areas:
  1. MonitorConfig        — defaults, overrides, from_dict, threshold config
  2. Issue / Severity     — dataclass fields, ordering
  3. Discovery            — markdown discovery, exclude globs
  4. Broken links         — internal relative links + anchors, http skipped
  5. Required sections    — missing-section detection (case-insensitive)
  6. Staleness            — mtime older than staleness_days
  7. Placeholders         — TODO/FIXME/TBD/lorem leakage with line numbers
  8. Structure            — missing H1, min word count
  9. Report               — counts, health score, JSON + human-readable, write
 10. End-to-end run       — clean vs dirty docs trees

Author: Security/Lead Engineer (MONITORING-001)
Phase: TDD RED-phase (tests define behaviour before implementation)
"""

import sys
import json
import time
import os
import importlib
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Lazy hyphenated-package import (mirrors test_agent_creator.py convention)
# ---------------------------------------------------------------------------
def _mod():
    sys.path.insert(0, str(Path(__file__).parent.parent))
    return importlib.import_module(
        "src.skills.doc-quality-monitor.scripts.doc_quality_monitor"
    )


m = _mod()

MonitorConfig = m.MonitorConfig
Issue = m.Issue
Severity = m.Severity
Category = m.Category
DocQualityReport = m.DocQualityReport
DocQualityMonitor = m.DocQualityMonitor


# ===========================================================================
# Fixtures
# ===========================================================================
@pytest.fixture()
def docs_tree(tmp_path: Path) -> Path:
    """Build a small docs tree with a mix of good and bad markdown."""
    root = tmp_path / "docs"
    root.mkdir()

    # Good doc — H1, required sections, internal link that resolves, fresh
    (root / "index.md").write_text(
        "# Index\n\n"
        "## Overview\n\nWelcome to the project documentation set.\n\n"
        "## Usage\n\nSee the [guide](guide.md) for details and worked examples.\n"
    )

    # Target of the internal link
    (root / "guide.md").write_text(
        "# Guide\n\n## Overview\n\nA thorough guide spanning many useful words "
        "to satisfy the readability threshold without any issues whatsoever.\n"
    )

    # Bad doc — broken internal link, missing Overview, placeholders, no H1
    (root / "broken.md").write_text(
        "## Notes\n\n"
        "Link to [missing file](does-not-exist.md).\n\n"
        "TODO: write this section.\n"
        "FIXME later.\n"
    )

    return root


@pytest.fixture()
def clean_tree(tmp_path: Path) -> Path:
    root = tmp_path / "clean"
    root.mkdir()
    (root / "a.md").write_text(
        "# Alpha\n\n## Overview\n\n"
        "This document is complete and contains enough words to be considered "
        "readable for the purposes of the structural quality gate checks here.\n"
    )
    return root


# ===========================================================================
# 1. MonitorConfig
# ===========================================================================
class TestMonitorConfig:
    def test_defaults(self):
        cfg = MonitorConfig()
        assert cfg.staleness_days == 30
        assert isinstance(cfg.placeholder_patterns, list)
        assert any("TODO" in p for p in cfg.placeholder_patterns)
        assert cfg.min_word_count >= 0
        assert cfg.check_broken_links is True

    def test_override(self):
        cfg = MonitorConfig(staleness_days=7, min_word_count=100)
        assert cfg.staleness_days == 7
        assert cfg.min_word_count == 100

    def test_from_dict(self):
        cfg = MonitorConfig.from_dict(
            {"staleness_days": 14, "required_sections": ["Overview", "Usage"]}
        )
        assert cfg.staleness_days == 14
        assert cfg.required_sections == ["Overview", "Usage"]

    def test_from_dict_ignores_unknown_keys(self):
        cfg = MonitorConfig.from_dict({"bogus_key": 1, "staleness_days": 5})
        assert cfg.staleness_days == 5


# ===========================================================================
# 2. Issue / Severity / Category
# ===========================================================================
class TestIssue:
    def test_issue_fields(self):
        iss = Issue(
            file="docs/x.md",
            line=3,
            category=Category.PLACEHOLDER,
            severity=Severity.WARNING,
            message="TODO found",
        )
        assert iss.file == "docs/x.md"
        assert iss.line == 3
        assert iss.category == Category.PLACEHOLDER
        assert iss.severity == Severity.WARNING

    def test_severity_values(self):
        assert {Severity.ERROR, Severity.WARNING, Severity.INFO}

    def test_category_values(self):
        for name in (
            "BROKEN_LINK",
            "MISSING_SECTION",
            "STALE_DOC",
            "PLACEHOLDER",
            "STRUCTURE",
        ):
            assert hasattr(Category, name)


# ===========================================================================
# 3. Discovery
# ===========================================================================
class TestDiscovery:
    def test_discovers_markdown(self, docs_tree: Path):
        mon = DocQualityMonitor(root=docs_tree)
        docs = mon.discover_docs()
        names = {p.name for p in docs}
        assert {"index.md", "guide.md", "broken.md"} <= names

    def test_exclude_globs(self, docs_tree: Path):
        cfg = MonitorConfig(exclude_globs=["broken.md"])
        mon = DocQualityMonitor(root=docs_tree, config=cfg)
        names = {p.name for p in mon.discover_docs()}
        assert "broken.md" not in names
        assert "index.md" in names

    def test_ignores_non_markdown(self, tmp_path: Path):
        (tmp_path / "notes.txt").write_text("not markdown")
        (tmp_path / "real.md").write_text("# Real\n\n## Overview\n\nwords here.\n")
        mon = DocQualityMonitor(root=tmp_path)
        names = {p.name for p in mon.discover_docs()}
        assert "real.md" in names
        assert "notes.txt" not in names


# ===========================================================================
# 4. Broken links
# ===========================================================================
class TestBrokenLinks:
    def test_detects_broken_internal_link(self, docs_tree: Path):
        mon = DocQualityMonitor(root=docs_tree)
        issues = mon.check_broken_links(docs_tree / "broken.md")
        assert any(i.category == Category.BROKEN_LINK for i in issues)
        assert any("does-not-exist.md" in i.message for i in issues)

    def test_valid_internal_link_no_issue(self, docs_tree: Path):
        mon = DocQualityMonitor(root=docs_tree)
        issues = mon.check_broken_links(docs_tree / "index.md")
        assert not any(i.category == Category.BROKEN_LINK for i in issues)

    def test_external_links_ignored(self, tmp_path: Path):
        d = tmp_path / "e.md"
        d.write_text("# E\n\n[site](https://example.com) [mail](mailto:a@b.c)\n")
        mon = DocQualityMonitor(root=tmp_path)
        issues = mon.check_broken_links(d)
        assert not any(i.category == Category.BROKEN_LINK for i in issues)

    def test_anchor_fragment_stripped(self, tmp_path: Path):
        (tmp_path / "t.md").write_text("# T\n\nsome content\n")
        d = tmp_path / "s.md"
        d.write_text("# S\n\n[ref](t.md#a-heading)\n")
        mon = DocQualityMonitor(root=tmp_path)
        issues = mon.check_broken_links(d)
        assert not any(i.category == Category.BROKEN_LINK for i in issues)

    def test_broken_link_reports_line(self, tmp_path: Path):
        d = tmp_path / "s.md"
        d.write_text("# S\n\nline2\n[x](nope.md)\n")
        mon = DocQualityMonitor(root=tmp_path)
        issues = [i for i in mon.check_broken_links(d) if i.category == Category.BROKEN_LINK]
        assert issues and issues[0].line == 4


# ===========================================================================
# 5. Required sections
# ===========================================================================
class TestRequiredSections:
    def test_missing_section_flagged(self, tmp_path: Path):
        d = tmp_path / "x.md"
        d.write_text("# X\n\n## Intro\n\nbody\n")
        cfg = MonitorConfig(required_sections=["Overview"])
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        issues = mon.check_required_sections(d)
        assert any(i.category == Category.MISSING_SECTION for i in issues)

    def test_present_section_ok_case_insensitive(self, tmp_path: Path):
        d = tmp_path / "x.md"
        d.write_text("# X\n\n## overview\n\nbody\n")
        cfg = MonitorConfig(required_sections=["Overview"])
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        assert not mon.check_required_sections(d)

    def test_no_required_sections_no_issues(self, tmp_path: Path):
        d = tmp_path / "x.md"
        d.write_text("# X\n\nbody\n")
        cfg = MonitorConfig(required_sections=[])
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        assert not mon.check_required_sections(d)


# ===========================================================================
# 6. Staleness
# ===========================================================================
class TestStaleness:
    def test_old_file_flagged(self, tmp_path: Path):
        d = tmp_path / "old.md"
        d.write_text("# Old\n\n## Overview\n\ncontent\n")
        old = time.time() - 60 * 60 * 24 * 90  # 90 days
        os.utime(d, (old, old))
        cfg = MonitorConfig(staleness_days=30)
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        issues = mon.check_staleness(d)
        assert any(i.category == Category.STALE_DOC for i in issues)

    def test_fresh_file_ok(self, tmp_path: Path):
        d = tmp_path / "new.md"
        d.write_text("# New\n\n## Overview\n\ncontent\n")
        cfg = MonitorConfig(staleness_days=30)
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        assert not mon.check_staleness(d)


# ===========================================================================
# 7. Placeholders
# ===========================================================================
class TestPlaceholders:
    def test_todo_detected_with_line(self, tmp_path: Path):
        d = tmp_path / "p.md"
        d.write_text("# P\n\n## Overview\n\nTODO: fill this in\n")
        mon = DocQualityMonitor(root=tmp_path)
        issues = [i for i in mon.check_placeholders(d) if i.category == Category.PLACEHOLDER]
        assert issues
        assert issues[0].line == 5

    def test_multiple_placeholders(self, tmp_path: Path):
        d = tmp_path / "p.md"
        d.write_text("# P\n\nTODO one\nFIXME two\nTBD three\n")
        mon = DocQualityMonitor(root=tmp_path)
        issues = [i for i in mon.check_placeholders(d) if i.category == Category.PLACEHOLDER]
        assert len(issues) >= 3

    def test_clean_doc_no_placeholders(self, tmp_path: Path):
        d = tmp_path / "p.md"
        d.write_text("# P\n\n## Overview\n\nAll content is final and complete.\n")
        mon = DocQualityMonitor(root=tmp_path)
        assert not [i for i in mon.check_placeholders(d) if i.category == Category.PLACEHOLDER]

    def test_custom_placeholder_pattern(self, tmp_path: Path):
        d = tmp_path / "p.md"
        d.write_text("# P\n\nSomething is HACKME here\n")
        cfg = MonitorConfig(placeholder_patterns=["HACKME"])
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        issues = [i for i in mon.check_placeholders(d) if i.category == Category.PLACEHOLDER]
        assert issues


# ===========================================================================
# 8. Structure / readability
# ===========================================================================
class TestStructure:
    def test_missing_h1_flagged(self, tmp_path: Path):
        d = tmp_path / "s.md"
        d.write_text("## Sub only\n\nbody content here is enough words maybe\n")
        mon = DocQualityMonitor(root=tmp_path)
        issues = mon.check_structure(d)
        assert any(i.category == Category.STRUCTURE for i in issues)

    def test_h1_present_ok(self, tmp_path: Path):
        d = tmp_path / "s.md"
        d.write_text(
            "# Title\n\n## Overview\n\n"
            + ("word " * 40)
            + "\n"
        )
        cfg = MonitorConfig(min_word_count=10)
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        assert not any(
            i.category == Category.STRUCTURE and "H1" in i.message
            for i in mon.check_structure(d)
        )

    def test_too_short_flagged(self, tmp_path: Path):
        d = tmp_path / "s.md"
        d.write_text("# Tiny\n\nhi\n")
        cfg = MonitorConfig(min_word_count=50)
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        issues = mon.check_structure(d)
        assert any(i.category == Category.STRUCTURE for i in issues)


# ===========================================================================
# 9. Report
# ===========================================================================
class TestReport:
    def test_run_returns_report(self, docs_tree: Path):
        mon = DocQualityMonitor(root=docs_tree, config=MonitorConfig(required_sections=["Overview"]))
        report = mon.run()
        assert isinstance(report, DocQualityReport)
        assert report.total_docs == 3
        assert report.total_issues > 0

    def test_health_score_range(self, docs_tree: Path):
        mon = DocQualityMonitor(root=docs_tree)
        report = mon.run()
        assert 0.0 <= report.health_score <= 100.0

    def test_clean_tree_high_score(self, clean_tree: Path):
        mon = DocQualityMonitor(root=clean_tree, config=MonitorConfig(required_sections=["Overview"]))
        report = mon.run()
        assert report.total_issues == 0
        assert report.health_score == 100.0

    def test_report_to_dict_json_serializable(self, docs_tree: Path):
        mon = DocQualityMonitor(root=docs_tree)
        report = mon.run()
        d = report.to_dict()
        s = json.dumps(d)  # must not raise
        assert "health_score" in s
        assert "issues" in d
        assert "by_category" in d

    def test_report_to_text(self, docs_tree: Path):
        mon = DocQualityMonitor(root=docs_tree)
        text = mon.run().to_text()
        assert "Health" in text or "health" in text
        assert isinstance(text, str)

    def test_write_report(self, docs_tree: Path, tmp_path: Path):
        mon = DocQualityMonitor(root=docs_tree)
        report = mon.run()
        jpath = tmp_path / "out" / "report.json"
        tpath = tmp_path / "out" / "report.md"
        report.write(json_path=jpath, text_path=tpath)
        assert jpath.exists() and tpath.exists()
        loaded = json.loads(jpath.read_text())
        assert loaded["total_docs"] == 3

    def test_by_category_counts(self, docs_tree: Path):
        cfg = MonitorConfig(required_sections=["Overview"])
        mon = DocQualityMonitor(root=docs_tree, config=cfg)
        report = mon.run()
        assert report.by_category.get("BROKEN_LINK", 0) >= 1
        assert report.by_category.get("PLACEHOLDER", 0) >= 1


# ===========================================================================
# 10. End-to-end / passing gate
# ===========================================================================
class TestEndToEnd:
    def test_passes_threshold_on_clean(self, clean_tree: Path):
        cfg = MonitorConfig(required_sections=["Overview"], fail_under=90.0)
        mon = DocQualityMonitor(root=clean_tree, config=cfg)
        report = mon.run()
        assert report.passed is True

    def test_fails_threshold_on_dirty(self, docs_tree: Path):
        cfg = MonitorConfig(required_sections=["Overview"], fail_under=99.0)
        mon = DocQualityMonitor(root=docs_tree, config=cfg)
        report = mon.run()
        assert report.passed is False

    def test_empty_tree_is_perfect(self, tmp_path: Path):
        mon = DocQualityMonitor(root=tmp_path)
        report = mon.run()
        assert report.total_docs == 0
        assert report.health_score == 100.0


# ===========================================================================
# 11. Phantom references (PHANTOM_REFERENCE category)
# ===========================================================================
class TestPhantomReferences:
    """Tests for check_phantom_references — known-dead class/path detection."""

    def test_phantom_category_exists(self):
        """Category enum must include PHANTOM_REFERENCE."""
        assert hasattr(Category, "PHANTOM_REFERENCE")
        assert Category.PHANTOM_REFERENCE.value == "PHANTOM_REFERENCE"

    def test_detects_automation_controller_ref(self, tmp_path: Path):
        """AutomationController mention in docs is flagged as phantom reference."""
        d = tmp_path / "guide.md"
        d.write_text(
            "# Guide\n\n"
            "Use AutomationController to run the polling loop.\n"
        )
        cfg = MonitorConfig(check_phantom_references=True)
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        issues = mon.check_phantom_references(d)
        assert any(i.category == Category.PHANTOM_REFERENCE for i in issues)
        assert any("AutomationController" in i.message for i in issues)

    def test_detects_dead_import_path(self, tmp_path: Path):
        """automation_controller.py path mention flagged as phantom."""
        d = tmp_path / "troubleshooting.md"
        d.write_text(
            "# Troubleshoot\n\n"
            "```\npython3 -c 'from orchestration.agents.automation import AutomationController'\n```\n"
        )
        cfg = MonitorConfig(check_phantom_references=True)
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        issues = mon.check_phantom_references(d)
        # Either AutomationController or automation_controller.py pattern triggers
        assert any(i.category == Category.PHANTOM_REFERENCE for i in issues)

    def test_phantom_check_disabled_by_default(self, tmp_path: Path):
        """Default MonitorConfig does NOT run phantom scan."""
        d = tmp_path / "r.md"
        d.write_text("# R\n\nUse AutomationController here.\n")
        cfg = MonitorConfig()  # check_phantom_references=False
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        issues = mon.check_phantom_references(d)
        assert not issues

    def test_phantom_check_opt_in(self, tmp_path: Path):
        """Phantom check only fires when explicitly enabled."""
        d = tmp_path / "r.md"
        d.write_text("# R\n\nUse AutomationController here.\n")
        cfg = MonitorConfig(check_phantom_references=True)
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        issues = mon.check_phantom_references(d)
        assert any(i.category == Category.PHANTOM_REFERENCE for i in issues)

    def test_custom_phantom_patterns(self, tmp_path: Path):
        """User can supply their own phantom patterns."""
        d = tmp_path / "r.md"
        d.write_text("# R\n\nSee OldWidget for details.\n")
        cfg = MonitorConfig(
            check_phantom_references=True,
            phantom_patterns=[("OldWidget", "OldWidget (replaced by NewWidget)")],
        )
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        issues = mon.check_phantom_references(d)
        assert any("OldWidget" in i.message for i in issues)

    def test_phantom_no_false_positives_on_clean_doc(self, tmp_path: Path):
        """Clean doc with no dead symbols passes phantom check."""
        d = tmp_path / "clean.md"
        d.write_text(
            "# Orchestrator\n\nThe Orchestrator polls for tasks via queue-management.\n"
        )
        cfg = MonitorConfig(check_phantom_references=True)
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        issues = mon.check_phantom_references(d)
        assert not issues

    def test_phantom_reports_correct_line(self, tmp_path: Path):
        """Phantom finding is attributed to the correct line number."""
        d = tmp_path / "r.md"
        d.write_text(
            "# Guide\n\nLine two.\nSee AutomationController usage.\nLine five.\n"
        )
        cfg = MonitorConfig(check_phantom_references=True)
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        issues = [i for i in mon.check_phantom_references(d) if i.category == Category.PHANTOM_REFERENCE]
        assert issues
        assert issues[0].line == 4

    def test_phantom_run_integrates_into_report(self, tmp_path: Path):
        """Full .run() with phantom check enabled includes PHANTOM_REFERENCE in by_category."""
        d = tmp_path / "bad.md"
        d.write_text(
            "# Bad\n\n## Overview\n\nWe use AutomationController here for polling.\n"
        )
        cfg = MonitorConfig(check_phantom_references=True, staleness_days=9999)
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        report = mon.run()
        assert report.by_category.get("PHANTOM_REFERENCE", 0) >= 1


# ===========================================================================
# 12. Stale docstrings (STALE_DOCSTRING category)
# ===========================================================================
class TestStaleDocstrings:
    """Tests for check_stale_docstrings — SKILL.md version/tdd_phase drift detection."""

    def test_stale_docstring_category_exists(self):
        """Category enum must include STALE_DOCSTRING."""
        assert hasattr(Category, "STALE_DOCSTRING")
        assert Category.STALE_DOCSTRING.value == "STALE_DOCSTRING"

    def test_version_0_1_with_green_tdd_flagged(self, tmp_path: Path):
        """SKILL.md with version 0.1 (proposed) but tdd_phase GREEN (implemented) is stale."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\n"
            "name: test-skill\n"
            "version: \"0.1\"\n"
            "tdd_phase: GREEN\n"
            "---\n\n"
            "# Test Skill\n\nContent here.\n"
        )
        cfg = MonitorConfig(check_stale_docstrings=True)
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        issues = mon.check_stale_docstrings(skill_file)
        assert any(i.category == Category.STALE_DOCSTRING for i in issues)

    def test_version_1_0_with_red_tdd_flagged(self, tmp_path: Path):
        """SKILL.md with version 1.0 (released) but tdd_phase RED (not implemented) is stale."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\n"
            "name: test-skill\n"
            "version: \"1.0\"\n"
            "tdd_phase: RED\n"
            "---\n\n"
            "# Test Skill\n\nContent here.\n"
        )
        cfg = MonitorConfig(check_stale_docstrings=True)
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        issues = mon.check_stale_docstrings(skill_file)
        assert any(i.category == Category.STALE_DOCSTRING for i in issues)

    def test_consistent_version_tdd_not_flagged(self, tmp_path: Path):
        """SKILL.md with consistent version/tdd_phase is not flagged."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\n"
            "name: test-skill\n"
            "version: \"1.0\"\n"
            "tdd_phase: GREEN\n"
            "---\n\n"
            "# Test Skill\n\nFully implemented and released.\n"
        )
        cfg = MonitorConfig(check_stale_docstrings=True)
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        issues = mon.check_stale_docstrings(skill_file)
        stale_issues = [i for i in issues if i.category == Category.STALE_DOCSTRING]
        assert not stale_issues

    def test_stale_docstring_check_disabled_by_default(self, tmp_path: Path):
        """Stale docstring check is NOT run by default."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\n"
            "name: test-skill\n"
            "version: \"0.1\"\n"
            "tdd_phase: GREEN\n"
            "---\n\n"
            "# Test Skill\n\nContent.\n"
        )
        cfg = MonitorConfig()  # check_stale_docstrings=False by default
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        issues = mon.check_stale_docstrings(skill_file)
        assert not issues

    def test_non_skill_md_not_checked(self, tmp_path: Path):
        """Non-SKILL.md files are not checked for stale docstrings."""
        md_file = tmp_path / "guide.md"
        md_file.write_text(
            "---\n"
            "version: \"0.1\"\n"
            "tdd_phase: GREEN\n"
            "---\n\n"
            "# Guide\n\nContent.\n"
        )
        cfg = MonitorConfig(check_stale_docstrings=True)
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        issues = mon.check_stale_docstrings(md_file)
        assert not issues

    def test_stale_docstring_in_report(self, tmp_path: Path):
        """Full .run() with stale_docstring check included in by_category."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\n"
            "name: test-skill\n"
            "version: \"0.1\"\n"
            "tdd_phase: GREEN\n"
            "---\n\n"
            "# Test Skill\n\nContent.\n"
        )
        cfg = MonitorConfig(check_stale_docstrings=True, staleness_days=9999)
        mon = DocQualityMonitor(root=tmp_path, config=cfg)
        report = mon.run()
        assert report.by_category.get("STALE_DOCSTRING", 0) >= 1
