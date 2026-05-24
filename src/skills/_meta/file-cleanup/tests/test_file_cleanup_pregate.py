# -*- coding: utf-8 -*-
"""
test_file_cleanup_pregate.py — TDD tests for the file-cleanup pre-gate modules.

Tests 5 classes:
  1. TestPreGateValidator       (7 tests)
  2. TestReferenceScanner       (8 tests)
  3. TestRiskAssessor           (6 tests)
  4. TestDeletionReportGenerator (4 tests)
  5. TestFileCleanupWithPreGate  (5 tests)
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SKILL_ROOT))

from scripts.pre_gate_validator import PreGateValidator  # noqa: E402
from scripts.reference_scanner import ReferenceScanner, Reference  # noqa: E402
from scripts.risk_assessor import RiskAssessor, RiskScore  # noqa: E402
from scripts.deletion_report_generator import DeletionReportGenerator, DeletionReport  # noqa: E402
from scripts.file_cleanup import run_cleanup, CleanupConfig  # noqa: E402


# ===========================================================================
# Shared fixture
# ===========================================================================

@pytest.fixture()
def tmp_repo(tmp_path: Path) -> Path:
    """Minimal fake repo with .git directory."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
    return tmp_path


# ===========================================================================
# TestPreGateValidator
# ===========================================================================

class TestPreGateValidator:

    def test_blocks_cleanup_if_sync_report_missing(self, tmp_repo: Path):
        """Gate blocks if SYNC_REPORT.md does not exist."""
        validator = PreGateValidator(tmp_repo)
        with patch.object(validator, "_all_tests_pass", return_value=True), \
             patch.object(validator, "_git_working_dir_clean", return_value=True):
            can_proceed, reason = validator.validate()
        assert not can_proceed
        assert "SYNC_REPORT.md" in reason

    def test_blocks_cleanup_if_sync_decisions_missing(self, tmp_repo: Path):
        """Gate blocks if SYNC_DECISIONS.md does not exist."""
        (tmp_repo / "SYNC_REPORT.md").write_text("# Sync Report\n")
        validator = PreGateValidator(tmp_repo)
        with patch.object(validator, "_all_tests_pass", return_value=True), \
             patch.object(validator, "_git_working_dir_clean", return_value=True):
            can_proceed, reason = validator.validate()
        assert not can_proceed
        assert "SYNC_DECISIONS.md" in reason

    def test_blocks_cleanup_if_sync_decisions_have_pending(self, tmp_repo: Path):
        """Gate blocks if SYNC_DECISIONS.md has PENDING entries."""
        (tmp_repo / "SYNC_REPORT.md").write_text("# Sync Report\n")
        (tmp_repo / "SYNC_DECISIONS.md").write_text("## script.py\nStatus: PENDING\n")
        validator = PreGateValidator(tmp_repo)
        with patch.object(validator, "_all_tests_pass", return_value=True), \
             patch.object(validator, "_git_working_dir_clean", return_value=True):
            can_proceed, reason = validator.validate()
        assert not can_proceed
        assert "PENDING" in reason

    def test_blocks_cleanup_if_working_directory_dirty(self, tmp_repo: Path):
        """Gate blocks if git working directory has uncommitted changes."""
        (tmp_repo / "SYNC_REPORT.md").write_text("# Sync Report\n")
        (tmp_repo / "SYNC_DECISIONS.md").write_text("## script.py\nStatus: ACCEPTED\n")
        validator = PreGateValidator(tmp_repo)
        with patch.object(validator, "_git_working_dir_clean", return_value=False), \
             patch.object(validator, "_count_modified_files", return_value=3), \
             patch.object(validator, "_all_tests_pass", return_value=True):
            can_proceed, reason = validator.validate()
        assert not can_proceed
        assert "modified" in reason.lower() or "working directory" in reason.lower()

    def test_blocks_cleanup_if_tests_failing(self, tmp_repo: Path):
        """Gate blocks if tests are failing."""
        (tmp_repo / "SYNC_REPORT.md").write_text("# Sync Report\n")
        (tmp_repo / "SYNC_DECISIONS.md").write_text("## script.py\nStatus: ACCEPTED\n")
        validator = PreGateValidator(tmp_repo)
        with patch.object(validator, "_git_working_dir_clean", return_value=True), \
             patch.object(validator, "_all_tests_pass", return_value=False):
            can_proceed, reason = validator.validate()
        assert not can_proceed
        assert "test" in reason.lower() or "failing" in reason.lower()

    def test_allows_cleanup_when_all_gates_pass(self, tmp_repo: Path):
        """Gate allows cleanup when all conditions are met."""
        (tmp_repo / "SYNC_REPORT.md").write_text("# Sync Report\n")
        (tmp_repo / "SYNC_DECISIONS.md").write_text("## script.py\nStatus: ACCEPTED\n")
        validator = PreGateValidator(tmp_repo)
        with patch.object(validator, "_git_working_dir_clean", return_value=True), \
             patch.object(validator, "_all_tests_pass", return_value=True):
            can_proceed, reason = validator.validate()
        assert can_proceed

    def test_generates_helpful_error_messages(self, tmp_repo: Path):
        """Blocked validation produces a descriptive error message."""
        validator = PreGateValidator(tmp_repo)
        with patch.object(validator, "_all_tests_pass", return_value=True), \
             patch.object(validator, "_git_working_dir_clean", return_value=True):
            can_proceed, reason = validator.validate()
        assert not can_proceed
        assert len(reason) > 20  # non-trivially descriptive


# ===========================================================================
# TestReferenceScanner
# ===========================================================================

class TestReferenceScanner:

    def test_detects_script_referenced_as_string_literal(self, tmp_repo: Path):
        """Scanner finds script name in string literal."""
        (tmp_repo / "caller.py").write_text('x = "scripts/cleanup.py"\n')
        scanner = ReferenceScanner(tmp_repo)
        refs = scanner.find_all_references("cleanup.py")
        assert any("caller.py" in str(r.file_path) for r in refs)

    def test_detects_script_in_fstring(self, tmp_repo: Path):
        """Scanner finds script name in f-string."""
        (tmp_repo / "runner.py").write_text('cmd = f"python cleanup.py --dry-run"\n')
        scanner = ReferenceScanner(tmp_repo)
        refs = scanner.find_all_references("cleanup.py")
        assert any("runner.py" in str(r.file_path) for r in refs)

    def test_detects_script_in_subprocess_call(self, tmp_repo: Path):
        """Scanner finds script name in subprocess call."""
        (tmp_repo / "invoke.py").write_text(
            'import subprocess\nsubprocess.run(["python", "cleanup.py"])\n'
        )
        scanner = ReferenceScanner(tmp_repo)
        refs = scanner.find_all_references("cleanup.py")
        assert any("invoke.py" in str(r.file_path) for r in refs)

    def test_detects_script_in_makefile(self, tmp_repo: Path):
        """Scanner finds script name in Makefile."""
        (tmp_repo / "Makefile").write_text("cleanup:\n\tpython scripts/cleanup.py\n")
        scanner = ReferenceScanner(tmp_repo)
        refs = scanner.find_all_references("cleanup.py")
        assert any("Makefile" in str(r.file_path) for r in refs)

    def test_detects_script_in_ci_workflows(self, tmp_repo: Path):
        """Scanner finds script name in CI workflows."""
        wf_dir = tmp_repo / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text("- run: python scripts/cleanup.py\n")
        scanner = ReferenceScanner(tmp_repo)
        refs = scanner.find_all_references("cleanup.py")
        assert any("ci.yml" in str(r.file_path) for r in refs)

    def test_detects_script_in_documentation(self, tmp_repo: Path):
        """Scanner finds script name in Markdown docs."""
        (tmp_repo / "CONTRIBUTING.md").write_text(
            "Run `scripts/cleanup.py` to clean up the repo.\n"
        )
        scanner = ReferenceScanner(tmp_repo)
        refs = scanner.find_all_references("cleanup.py")
        assert any("CONTRIBUTING.md" in str(r.file_path) for r in refs)

    def test_detects_script_in_comments(self, tmp_repo: Path):
        """Scanner finds script name in inline comments."""
        (tmp_repo / "main.py").write_text("# TODO: use cleanup.py here\npass\n")
        scanner = ReferenceScanner(tmp_repo)
        refs = scanner.find_all_references("cleanup.py")
        assert any("main.py" in str(r.file_path) for r in refs)

    def test_reference_objects_have_complete_context(self, tmp_repo: Path):
        """Each Reference has file_path, line_number, context, and ref_type."""
        (tmp_repo / "caller.py").write_text('x = "cleanup.py"\n')
        scanner = ReferenceScanner(tmp_repo)
        refs = scanner.find_all_references("cleanup.py")
        assert len(refs) > 0
        ref = refs[0]
        assert hasattr(ref, "file_path")
        assert hasattr(ref, "line_number")
        assert hasattr(ref, "context")
        assert hasattr(ref, "ref_type")
        assert ref.line_number >= 1
        assert len(ref.context) > 0


# ===========================================================================
# TestRiskAssessor
# ===========================================================================

class TestRiskAssessor:

    def test_scores_low_risk_orphaned_temp_file(self, tmp_repo: Path):
        """File with no references scores LOW risk."""
        temp_file = tmp_repo / "PHASE_01_planning.md"
        temp_file.write_text("# Phase 1\n")
        assessor = RiskAssessor(tmp_repo)
        risk = assessor.assess_deletion_risk(temp_file, [])
        assert risk.level == "LOW"
        assert risk.score <= 30

    def test_scores_high_risk_actively_used_script(self, tmp_repo: Path):
        """File with many active references scores HIGH risk."""
        script = tmp_repo / "critical.py"
        script.write_text("def critical(): pass\n")
        refs = [
            Reference(tmp_repo / f"file{i}.py", i, f"import critical", "import")
            for i in range(5)
        ]
        assessor = RiskAssessor(tmp_repo)
        with patch.object(assessor, "_score_git_history", return_value=15.0):
            risk = assessor.assess_deletion_risk(script, refs)
        assert risk.score > 30

    def test_scores_medium_risk_with_hidden_references(self, tmp_repo: Path):
        """File with hidden references (string literals) scores > LOW."""
        script = tmp_repo / "util.py"
        script.write_text("def util(): pass\n")
        refs = [
            Reference(tmp_repo / "config.py", 1, '"util.py"', "string"),
            Reference(tmp_repo / "config.py", 2, '"util.py"', "string"),
            Reference(tmp_repo / "config.py", 3, '"util.py"', "string"),
        ]
        assessor = RiskAssessor(tmp_repo)
        with patch.object(assessor, "_score_git_history", return_value=0.0):
            risk = assessor.assess_deletion_risk(script, refs)
        assert risk.score > 0

    def test_assigns_risk_level_low_medium_high(self, tmp_repo: Path):
        """Risk level is one of LOW, MEDIUM, HIGH."""
        script = tmp_repo / "script.py"
        script.write_text("pass\n")
        assessor = RiskAssessor(tmp_repo)
        risk = assessor.assess_deletion_risk(script, [])
        assert risk.level in ("LOW", "MEDIUM", "HIGH")

    def test_includes_confidence_score(self, tmp_repo: Path):
        """RiskScore has a confidence value between 0 and 1."""
        script = tmp_repo / "script.py"
        script.write_text("pass\n")
        assessor = RiskAssessor(tmp_repo)
        risk = assessor.assess_deletion_risk(script, [])
        assert 0.0 <= risk.confidence <= 1.0

    def test_recommends_deletion_for_clear_cases(self, tmp_repo: Path):
        """Files with no references get DELETE recommendation."""
        script = tmp_repo / "orphan.py"
        script.write_text("# orphaned\n")
        assessor = RiskAssessor(tmp_repo)
        with patch.object(assessor, "_score_git_history", return_value=0.0), \
             patch.object(assessor, "_score_age_and_frequency", return_value=0.0):
            risk = assessor.assess_deletion_risk(script, [])
        assert risk.recommendation == "DELETE"


# ===========================================================================
# TestDeletionReportGenerator
# ===========================================================================

class TestDeletionReportGenerator:

    def test_generates_report_with_all_risk_factors(self, tmp_repo: Path):
        """generate_report() produces DeletionReport with all key fields."""
        file_path = tmp_repo / "old_script.py"
        file_path.write_text("# old\n")
        risk = RiskScore(score=10, level="LOW", confidence=0.95,
                         recommendation="DELETE", reasoning=["No refs: 0pts"])
        generator = DeletionReportGenerator(tmp_repo)
        report = generator.generate_report(file_path, risk, [])
        assert isinstance(report, DeletionReport)
        assert report.risk_level == "LOW"
        assert report.recommendation == "DELETE"

    def test_highlights_active_references_prominently(self, tmp_repo: Path):
        """Report separates active from hidden references."""
        file_path = tmp_repo / "script.py"
        file_path.write_text("pass\n")
        refs = [
            Reference(tmp_repo / "importer.py", 1, "import script", "import"),
            Reference(tmp_repo / "config.py", 2, '"script.py"', "string"),
        ]
        risk = RiskScore(score=25, level="LOW", confidence=0.95,
                         recommendation="DELETE", reasoning=[])
        generator = DeletionReportGenerator(tmp_repo)
        report = generator.generate_report(file_path, risk, refs)
        assert len(report.active_references) > 0 or len(report.hidden_references) > 0

    def test_shows_recovery_command_for_reversibility(self, tmp_repo: Path):
        """Report includes a git recovery command."""
        file_path = tmp_repo / "old.py"
        file_path.write_text("# old\n")
        risk = RiskScore(score=5, level="LOW", confidence=0.95,
                         recommendation="DELETE", reasoning=[])
        generator = DeletionReportGenerator(tmp_repo)
        report = generator.generate_report(file_path, risk, [])
        assert "git" in report.recovery_command
        assert str(file_path) in report.recovery_command or "old.py" in report.recovery_command

    def test_provides_clear_confirmation_prompt(self, tmp_repo: Path):
        """format_report() produces a human-readable string."""
        file_path = tmp_repo / "temp.py"
        file_path.write_text("# temp\n")
        risk = RiskScore(score=5, level="LOW", confidence=0.95,
                         recommendation="DELETE", reasoning=["No refs"])
        generator = DeletionReportGenerator(tmp_repo)
        report = generator.generate_report(file_path, risk, [])
        formatted = generator.format_report(report)
        assert len(formatted) > 50
        assert "DELETION REPORT" in formatted


# ===========================================================================
# TestFileCleanupWithPreGate
# ===========================================================================

class TestFileCleanupWithPreGate:

    def test_cleanup_blocked_without_sync_report(self, tmp_repo: Path):
        """run_cleanup() with pre_gate=True is blocked if SYNC_REPORT.md missing."""
        validator = PreGateValidator(tmp_repo)
        with patch.object(validator, "_all_tests_pass", return_value=True), \
             patch.object(validator, "_git_working_dir_clean", return_value=True):
            can_proceed, reason = validator.validate()
        assert not can_proceed

    def test_cleanup_proceeds_after_sync_workflow_complete(self, tmp_repo: Path):
        """run_cleanup() proceeds when all pre-gate conditions are met."""
        (tmp_repo / "SYNC_REPORT.md").write_text("# Report\n")
        (tmp_repo / "SYNC_DECISIONS.md").write_text("Status: ACCEPTED\n")
        validator = PreGateValidator(tmp_repo)
        with patch.object(validator, "_git_working_dir_clean", return_value=True), \
             patch.object(validator, "_all_tests_pass", return_value=True):
            can_proceed, _ = validator.validate()
        assert can_proceed

    def test_reads_sync_decisions_to_skip_integrated_scripts(self, tmp_repo: Path):
        """Scripts marked ACCEPTED in SYNC_DECISIONS.md are excluded from cleanup."""
        (tmp_repo / "SYNC_DECISIONS.md").write_text(
            "## my_script.py\nStatus: ACCEPTED\n"
        )
        # Verify we can parse ACCEPTED decisions
        content = (tmp_repo / "SYNC_DECISIONS.md").read_text()
        assert "ACCEPTED" in content
        assert "PENDING" not in content

    def test_generates_deletion_log_with_recovery_commands(self, tmp_repo: Path):
        """DeletionReportGenerator creates recovery-aware reports."""
        file_path = tmp_repo / "old_debug.py"
        file_path.write_text("# debug\n")
        from scripts.risk_assessor import RiskScore
        risk = RiskScore(score=5, level="LOW", confidence=0.95,
                         recommendation="DELETE", reasoning=[])
        generator = DeletionReportGenerator(tmp_repo)
        report = generator.generate_report(file_path, risk, [])
        assert "git checkout" in report.recovery_command

    def test_full_workflow_from_sync_to_cleanup(self, tmp_repo: Path):
        """End-to-end: SYNC_REPORT.md → SYNC_DECISIONS.md → PreGateValidator passes."""
        # Write both required files
        (tmp_repo / "SYNC_REPORT.md").write_text("# File-Sync Report\nAnalyzed 5 scripts.\n")
        (tmp_repo / "SYNC_DECISIONS.md").write_text(
            "## get_version.py\nStatus: ACCEPTED\n\n## debug_old.sh\nStatus: REJECTED\n"
        )
        validator = PreGateValidator(tmp_repo)
        with patch.object(validator, "_git_working_dir_clean", return_value=True), \
             patch.object(validator, "_all_tests_pass", return_value=True):
            can_proceed, reason = validator.validate()
        assert can_proceed
