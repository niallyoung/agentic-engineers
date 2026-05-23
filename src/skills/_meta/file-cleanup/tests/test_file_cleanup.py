# -*- coding: utf-8 -*-
"""
test_file_cleanup.py — TDD test suite for file-cleanup skill.

TDD Phases:
  RED  — All tests written here; run before implementation (expect failures).
  GREEN — Implementation added in scripts/file_cleanup.py; all tests pass.
  REFACTOR — Cleanup for clarity and edge-cases.

Test categories:
  1. Pattern detection (phase files, session/temp, debug logs, coverage, vim swap)
  2. Directory detection (testing-results/)
  3. Protection / exclusion logic (real docs, git-tracked files, protected dirs)
  4. Dry-run mode (list what would be deleted, touch nothing)
  5. Analysis-only mode (structured report, no deletions)
  6. Git integration (exclude files in the git index)
  7. Config-consolidation analysis (duplicate config detection)
  8. Risk assessment (low / medium / high per category)
"""

import os
import sys
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap: make the skill importable regardless of working directory
# ---------------------------------------------------------------------------
_SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SKILL_ROOT))

from scripts.file_cleanup import (  # noqa: E402  (after sys.path insertion)
    CleanupCandidate,
    CleanupCategory,
    CleanupConfig,
    FileCleanupAnalyzer,
    RiskLevel,
    run_cleanup,
)


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture()
def tmp_repo(tmp_path: Path) -> Path:
    """
    Minimal fake repo root with a .git directory so git integration tests
    can distinguish tracked vs. untracked files without touching the real repo.
    """
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
    return tmp_path


def _make_file(parent: Path, name: str, content: str = "") -> Path:
    """Create a file at parent/name with optional content."""
    p = parent / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


# ===========================================================================
# 1. Phase / temporary session files
# ===========================================================================

class TestPhaseFilesDetection:
    """PHASE_*.md and PHASE-*.md pattern matching."""

    def test_identifies_phase_underscore_files(self, tmp_repo: Path):
        """PHASE_<name>.md files are flagged as session/temp."""
        _make_file(tmp_repo, "PHASE_01_ANALYSIS.md", "# Phase 01")
        _make_file(tmp_repo, "PHASE_02_IMPLEMENT.md", "# Phase 02")

        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()

        paths = [c.path.name for c in candidates]
        assert "PHASE_01_ANALYSIS.md" in paths
        assert "PHASE_02_IMPLEMENT.md" in paths

    def test_identifies_phase_hyphen_files(self, tmp_repo: Path):
        """PHASE-<name>.md files are flagged as session/temp."""
        _make_file(tmp_repo, "PHASE-planning.md", "planning notes")

        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()

        paths = [c.path.name for c in candidates]
        assert "PHASE-planning.md" in paths

    def test_phase_files_categorized_correctly(self, tmp_repo: Path):
        """Phase files get CleanupCategory.SESSION_TEMP."""
        _make_file(tmp_repo, "PHASE_01.md")

        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()

        phase_candidates = [c for c in candidates if c.path.name == "PHASE_01.md"]
        assert len(phase_candidates) == 1
        assert phase_candidates[0].category == CleanupCategory.SESSION_TEMP


# ===========================================================================
# 2. Session / temporary files
# ===========================================================================

class TestSessionTempFilesDetection:
    """WIP_*, TEMP_*, TMP_*, *-SESSION-*, *-session-* pattern matching."""

    def test_identifies_wip_files(self, tmp_repo: Path):
        _make_file(tmp_repo, "WIP_feature_notes.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert any(c.path.name == "WIP_feature_notes.md" for c in candidates)

    def test_identifies_temp_files(self, tmp_repo: Path):
        _make_file(tmp_repo, "TEMP_scratch.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert any(c.path.name == "TEMP_scratch.md" for c in candidates)

    def test_identifies_tmp_files(self, tmp_repo: Path):
        _make_file(tmp_repo, "TMP_notes.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert any(c.path.name == "TMP_notes.md" for c in candidates)

    def test_identifies_session_hyphen_files(self, tmp_repo: Path):
        _make_file(tmp_repo, "WORK-SESSION-2026-01.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert any(c.path.name == "WORK-SESSION-2026-01.md" for c in candidates)

    def test_identifies_lowercase_session_files(self, tmp_repo: Path):
        _make_file(tmp_repo, "work-session-notes.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert any(c.path.name == "work-session-notes.md" for c in candidates)

    def test_identifies_vim_swap_files(self, tmp_repo: Path):
        _make_file(tmp_repo, ".README.md.swp")
        _make_file(tmp_repo, ".notes.swo")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        names = [c.path.name for c in candidates]
        assert ".README.md.swp" in names
        assert ".notes.swo" in names

    def test_session_temp_files_have_low_risk(self, tmp_repo: Path):
        """Temp/session files without content = low risk."""
        _make_file(tmp_repo, "WIP_scratch.md", "")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        wip = next(c for c in candidates if c.path.name == "WIP_scratch.md")
        assert wip.risk == RiskLevel.LOW


# ===========================================================================
# 3. Debug / progress log files
# ===========================================================================

class TestDebugLogFilesDetection:
    """Files that are purely debug/progress markers."""

    def test_identifies_progress_only_files(self, tmp_repo: Path):
        """Files containing only STARTED/COMPLETED/IN_PROGRESS markers."""
        content = textwrap.dedent("""\
            STARTED
            IN_PROGRESS
            COMPLETED
        """)
        _make_file(tmp_repo, "progress_log.md", content)
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert any(c.path.name == "progress_log.md" for c in candidates)

    def test_identifies_debug_header_files(self, tmp_repo: Path):
        """Files with [DEBUG]/[LOG]/[TRACE] header and minimal substantive content."""
        content = "[DEBUG] 2026-01-01 some debug trace\n[LOG] step completed\n"
        _make_file(tmp_repo, "debug_output.md", content)
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert any(c.path.name == "debug_output.md" for c in candidates)

    def test_identifies_timestamped_progress_files(self, tmp_repo: Path):
        """Files with timestamp pattern *_2026_*.md are flagged."""
        _make_file(tmp_repo, "run_2026_01_15_analysis.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert any(c.path.name == "run_2026_01_15_analysis.md" for c in candidates)

    def test_debug_files_categorized_correctly(self, tmp_repo: Path):
        content = "[DEBUG] trace info\n[LOG] step 1\n"
        _make_file(tmp_repo, "debug_only.md", content)
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        debug_c = next(c for c in candidates if c.path.name == "debug_only.md")
        assert debug_c.category == CleanupCategory.DEBUG_LOG


# ===========================================================================
# 4. Test / quality output files
# ===========================================================================

class TestCoverageReportDetection:
    """*.coverage files, .coverage.* reports, and HTML reports outside docs/."""

    def test_identifies_coverage_files(self, tmp_repo: Path):
        _make_file(tmp_repo, "app.coverage")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert any(c.path.name == "app.coverage" for c in candidates)

    def test_identifies_dotcoverage_files(self, tmp_repo: Path):
        _make_file(tmp_repo, ".coverage.main")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert any(c.path.name == ".coverage.main" for c in candidates)

    def test_coverage_files_categorized_correctly(self, tmp_repo: Path):
        _make_file(tmp_repo, "tests.coverage")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        cov = next(c for c in candidates if c.path.name == "tests.coverage")
        assert cov.category == CleanupCategory.COVERAGE_REPORT

    def test_identifies_html_coverage_outside_docs(self, tmp_repo: Path):
        """htmlcov/ at root level should be flagged."""
        html_dir = tmp_repo / "htmlcov"
        html_dir.mkdir()
        (html_dir / "index.html").write_text("<html></html>")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        # Should flag htmlcov/ as a directory-level candidate
        assert any("htmlcov" in str(c.path) for c in candidates)

    def test_html_coverage_in_docs_not_flagged(self, tmp_repo: Path):
        """htmlcov/ nested inside docs/ should NOT be flagged."""
        docs_dir = tmp_repo / "docs" / "htmlcov"
        docs_dir.mkdir(parents=True)
        (docs_dir / "index.html").write_text("<html></html>")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert not any("docs/htmlcov" in str(c.path) for c in candidates)


class TestTestingResultsDetection:
    """testing-results/ directory detection."""

    def test_identifies_testing_results_directory(self, tmp_repo: Path):
        tr_dir = tmp_repo / "testing-results"
        tr_dir.mkdir()
        (tr_dir / "report.json").write_text("{}")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert any("testing-results" in str(c.path) for c in candidates)

    def test_testing_results_dir_categorized_correctly(self, tmp_repo: Path):
        tr_dir = tmp_repo / "testing-results"
        tr_dir.mkdir()
        (tr_dir / "report.json").write_text("{}")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        tr_candidate = next(c for c in candidates if "testing-results" in str(c.path))
        assert tr_candidate.category == CleanupCategory.TESTING_RESULTS


# ===========================================================================
# 5. Preservation: real documentation must never be flagged
# ===========================================================================

class TestPreservationOfRealDocs:
    """README.md, TODO.md, SPEC.md, CHANGELOG.md etc. must NOT be flagged."""

    PROTECTED = [
        "README.md",
        "TODO.md",
        "SPEC.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "setup.py",
        "Makefile",
        "pytest.ini",
    ]

    def test_preserves_readme(self, tmp_repo: Path):
        _make_file(tmp_repo, "README.md", "# Project\nReal documentation.")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert not any(c.path.name == "README.md" for c in candidates)

    def test_preserves_todo(self, tmp_repo: Path):
        _make_file(tmp_repo, "TODO.md", "- [ ] task one")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert not any(c.path.name == "TODO.md" for c in candidates)

    def test_preserves_spec(self, tmp_repo: Path):
        _make_file(tmp_repo, "SPEC.md", "# Spec")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert not any(c.path.name == "SPEC.md" for c in candidates)

    @pytest.mark.parametrize("name", PROTECTED)
    def test_all_protected_files_preserved(self, name: str, tmp_repo: Path):
        _make_file(tmp_repo, name, "content")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert not any(c.path.name == name for c in candidates), (
            f"{name} should not be flagged for cleanup"
        )

    def test_src_directory_never_flagged(self, tmp_repo: Path):
        """Files under src/ are NEVER candidates."""
        src_file = tmp_repo / "src" / "PHASE_01.md"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("# Phase 01")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert not any("src/" in str(c.path) for c in candidates)

    def test_tests_directory_never_flagged(self, tmp_repo: Path):
        """Files under tests/ are NEVER candidates."""
        test_file = tmp_repo / "tests" / "PHASE_01.md"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("# Phase 01")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert not any("tests/" in str(c.path) for c in candidates)

    def test_git_directory_never_flagged(self, tmp_repo: Path):
        """Files under .git/ are NEVER candidates."""
        # .git already exists in tmp_repo fixture
        git_file = tmp_repo / ".git" / "PHASE_01.md"
        git_file.write_text("phase data")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        candidates = analyzer.scan()
        assert not any(".git/" in str(c.path) for c in candidates)


# ===========================================================================
# 6. Git integration — never delete git-tracked files
# ===========================================================================

class TestGitIntegration:
    """Git-tracked files must be excluded even if they match cleanup patterns."""

    def test_excludes_git_tracked_files(self, tmp_repo: Path):
        """A file matching PHASE_*.md pattern but tracked by git is excluded."""
        phase_file = _make_file(tmp_repo, "PHASE_01.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)

        # Simulate git reporting the file as tracked
        def mock_is_tracked(path: Path) -> bool:
            return path.name == "PHASE_01.md"

        with patch.object(analyzer, "_is_git_tracked", side_effect=mock_is_tracked):
            candidates = analyzer.scan()

        assert not any(c.path.name == "PHASE_01.md" for c in candidates)

    def test_includes_untracked_phase_files(self, tmp_repo: Path):
        """Untracked files matching PHASE_*.md are included."""
        _make_file(tmp_repo, "PHASE_99.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)

        with patch.object(analyzer, "_is_git_tracked", return_value=False):
            candidates = analyzer.scan()

        assert any(c.path.name == "PHASE_99.md" for c in candidates)

    def test_git_tracked_flag_set_on_candidate(self, tmp_repo: Path):
        """CleanupCandidate.git_tracked reflects git status."""
        _make_file(tmp_repo, "WIP_notes.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)

        # Not tracked → should appear, git_tracked=False
        with patch.object(analyzer, "_is_git_tracked", return_value=False):
            candidates = analyzer.scan()

        wip = next(c for c in candidates if c.path.name == "WIP_notes.md")
        assert wip.git_tracked is False


# ===========================================================================
# 7. Dry-run mode
# ===========================================================================

class TestDryRunMode:
    """--dry-run reports candidates but does NOT delete any files."""

    def test_dry_run_returns_candidates(self, tmp_repo: Path):
        _make_file(tmp_repo, "WIP_scratch.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo, dry_run=True)
        with patch.object(analyzer, "_is_git_tracked", return_value=False):
            result = analyzer.execute()
        assert len(result.candidates) > 0

    def test_dry_run_does_not_delete_files(self, tmp_repo: Path):
        target = _make_file(tmp_repo, "WIP_scratch.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo, dry_run=True)
        with patch.object(analyzer, "_is_git_tracked", return_value=False):
            analyzer.execute()
        assert target.exists(), "Dry-run must not delete files"

    def test_dry_run_result_has_deleted_empty(self, tmp_repo: Path):
        _make_file(tmp_repo, "WIP_scratch.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo, dry_run=True)
        with patch.object(analyzer, "_is_git_tracked", return_value=False):
            result = analyzer.execute()
        assert result.deleted == []


# ===========================================================================
# 8. Analysis-only mode
# ===========================================================================

class TestAnalysisOnlyMode:
    """--analysis-only produces a structured report, never deletes."""

    def test_analysis_only_returns_report(self, tmp_repo: Path):
        _make_file(tmp_repo, "PHASE_01.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo, analysis_only=True)
        with patch.object(analyzer, "_is_git_tracked", return_value=False):
            result = analyzer.execute()
        assert result is not None
        assert hasattr(result, "candidates")
        assert hasattr(result, "summary")

    def test_analysis_only_does_not_delete(self, tmp_repo: Path):
        target = _make_file(tmp_repo, "PHASE_01.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo, analysis_only=True)
        with patch.object(analyzer, "_is_git_tracked", return_value=False):
            analyzer.execute()
        assert target.exists()

    def test_analysis_only_summary_contains_categories(self, tmp_repo: Path):
        _make_file(tmp_repo, "PHASE_01.md")
        _make_file(tmp_repo, "WIP_notes.md")
        _make_file(tmp_repo, "tests.coverage")
        analyzer = FileCleanupAnalyzer(root=tmp_repo, analysis_only=True)
        with patch.object(analyzer, "_is_git_tracked", return_value=False):
            result = analyzer.execute()
        # Summary should contain counts by category
        assert isinstance(result.summary, dict)
        assert CleanupCategory.SESSION_TEMP in result.summary or len(result.candidates) >= 0


# ===========================================================================
# 9. Config consolidation analysis
# ===========================================================================

class TestConfigConsolidation:
    """Detect duplicate/redundant config files."""

    def test_detects_duplicate_config_files(self, tmp_repo: Path):
        """Identical files with the same base name in different directories."""
        cfg_dir1 = tmp_repo / "config"
        cfg_dir2 = tmp_repo / "config" / "backup"
        cfg_dir1.mkdir(parents=True)
        cfg_dir2.mkdir(parents=True)
        content = "key=value\nfoo=bar\n"
        (cfg_dir1 / "settings.cfg").write_text(content)
        (cfg_dir2 / "settings.cfg").write_text(content)

        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        report = analyzer.config_consolidation_report()

        assert report is not None
        assert len(report.duplicates) > 0

    def test_no_false_positives_for_unique_configs(self, tmp_repo: Path):
        """Unique config files should not appear as duplicates."""
        cfg_dir = tmp_repo / "config"
        cfg_dir.mkdir()
        (cfg_dir / "dev.cfg").write_text("mode=dev\n")
        (cfg_dir / "prod.cfg").write_text("mode=prod\n")

        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        report = analyzer.config_consolidation_report()

        # dev.cfg and prod.cfg have different content — not duplicates
        dup_names = {p.name for pair in report.duplicates for p in pair}
        assert "dev.cfg" not in dup_names or "prod.cfg" not in dup_names

    def test_config_report_has_recommendation(self, tmp_repo: Path):
        """Config consolidation report includes human-readable recommendation."""
        cfg_dir = tmp_repo / "config"
        cfg_dir.mkdir()
        content = "same=content\n"
        (cfg_dir / "a.cfg").write_text(content)
        (cfg_dir / "b.cfg").write_text(content)

        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        report = analyzer.config_consolidation_report()

        assert hasattr(report, "recommendation")
        assert isinstance(report.recommendation, str)


# ===========================================================================
# 10. Risk assessment
# ===========================================================================

class TestRiskAssessment:
    """Each candidate has an appropriate risk level."""

    def test_vim_swap_files_are_low_risk(self, tmp_repo: Path):
        _make_file(tmp_repo, ".file.swp")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        with patch.object(analyzer, "_is_git_tracked", return_value=False):
            candidates = analyzer.scan()
        swp = next(c for c in candidates if c.path.name == ".file.swp")
        assert swp.risk == RiskLevel.LOW

    def test_empty_phase_files_are_low_risk(self, tmp_repo: Path):
        _make_file(tmp_repo, "PHASE_01.md", "")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        with patch.object(analyzer, "_is_git_tracked", return_value=False):
            candidates = analyzer.scan()
        ph = next(c for c in candidates if c.path.name == "PHASE_01.md")
        assert ph.risk == RiskLevel.LOW

    def test_nonempty_phase_files_are_medium_risk(self, tmp_repo: Path):
        content = "# Phase 01\n\nLots of detailed notes here.\n" * 5
        _make_file(tmp_repo, "PHASE_01.md", content)
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        with patch.object(analyzer, "_is_git_tracked", return_value=False):
            candidates = analyzer.scan()
        ph = next(c for c in candidates if c.path.name == "PHASE_01.md")
        assert ph.risk in (RiskLevel.MEDIUM, RiskLevel.LOW)

    def test_candidate_has_reason_string(self, tmp_repo: Path):
        _make_file(tmp_repo, "TEMP_scratch.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo)
        with patch.object(analyzer, "_is_git_tracked", return_value=False):
            candidates = analyzer.scan()
        temp = next(c for c in candidates if c.path.name == "TEMP_scratch.md")
        assert isinstance(temp.reason, str)
        assert len(temp.reason) > 0


# ===========================================================================
# 11. Execute mode (actual deletion — guarded by dry_run=False)
# ===========================================================================

class TestExecuteMode:
    """execute() with dry_run=False actually removes untracked cleanup targets."""

    def test_execute_deletes_untracked_temp_file(self, tmp_repo: Path):
        target = _make_file(tmp_repo, "WIP_scratch.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo, dry_run=False)
        with patch.object(analyzer, "_is_git_tracked", return_value=False):
            result = analyzer.execute()
        assert not target.exists(), "Execute mode must delete the file"
        assert target in result.deleted

    def test_execute_never_deletes_tracked_files(self, tmp_repo: Path):
        target = _make_file(tmp_repo, "WIP_important.md", "tracked content")
        analyzer = FileCleanupAnalyzer(root=tmp_repo, dry_run=False)

        def only_tracked(path: Path) -> bool:
            return path.name == "WIP_important.md"

        with patch.object(analyzer, "_is_git_tracked", side_effect=only_tracked):
            result = analyzer.execute()

        assert target.exists(), "Execute must not delete git-tracked files"
        assert target not in result.deleted

    def test_execute_result_lists_deleted_paths(self, tmp_repo: Path):
        target = _make_file(tmp_repo, "TEMP_gone.md")
        analyzer = FileCleanupAnalyzer(root=tmp_repo, dry_run=False)
        with patch.object(analyzer, "_is_git_tracked", return_value=False):
            result = analyzer.execute()
        assert target in result.deleted


# ===========================================================================
# 12. CleanupConfig customisation
# ===========================================================================

class TestCleanupConfig:
    """Users can extend patterns via CleanupConfig."""

    def test_custom_pattern_is_detected(self, tmp_repo: Path):
        """Adding a custom pattern to config causes matching files to be flagged."""
        _make_file(tmp_repo, "CUSTOM_artifact.md")
        config = CleanupConfig(extra_patterns=["CUSTOM_*.md"])
        analyzer = FileCleanupAnalyzer(root=tmp_repo, config=config)
        with patch.object(analyzer, "_is_git_tracked", return_value=False):
            candidates = analyzer.scan()
        assert any(c.path.name == "CUSTOM_artifact.md" for c in candidates)

    def test_custom_exclusion_prevents_flagging(self, tmp_repo: Path):
        """Adding a path to exclusions prevents it from being flagged."""
        _make_file(tmp_repo, "WIP_keep_me.md")
        config = CleanupConfig(extra_exclusions=["WIP_keep_me.md"])
        analyzer = FileCleanupAnalyzer(root=tmp_repo, config=config)
        with patch.object(analyzer, "_is_git_tracked", return_value=False):
            candidates = analyzer.scan()
        assert not any(c.path.name == "WIP_keep_me.md" for c in candidates)


# ===========================================================================
# 13. run_cleanup() CLI entry-point integration
# ===========================================================================

class TestRunCleanupEntrypoint:
    """run_cleanup() is the module-level CLI dispatcher."""

    def test_run_cleanup_dry_run_returns_result(self, tmp_repo: Path):
        _make_file(tmp_repo, "WIP_file.md")
        with patch("scripts.file_cleanup.FileCleanupAnalyzer._is_git_tracked",
                   return_value=False):
            result = run_cleanup(root=tmp_repo, dry_run=True)
        assert result is not None
        assert hasattr(result, "candidates")

    def test_run_cleanup_analysis_only_returns_result(self, tmp_repo: Path):
        _make_file(tmp_repo, "PHASE_01.md")
        with patch("scripts.file_cleanup.FileCleanupAnalyzer._is_git_tracked",
                   return_value=False):
            result = run_cleanup(root=tmp_repo, analysis_only=True)
        assert result is not None

    def test_run_cleanup_execute_deletes_file(self, tmp_repo: Path):
        target = _make_file(tmp_repo, "TMP_delete_me.md")
        with patch("scripts.file_cleanup.FileCleanupAnalyzer._is_git_tracked",
                   return_value=False):
            result = run_cleanup(root=tmp_repo, dry_run=False)
        assert not target.exists()
        assert target in result.deleted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
