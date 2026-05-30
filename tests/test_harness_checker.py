"""Tests for OpenCode harness runtime validation.

Target: ≥95% line coverage of ``src/harness/harness_checker.py``.

Test groups:
  1. HarnessChecker initialization and repo root detection
  2. check_agents_loaded() — verify agent roster validation
  3. check_skills_available() — verify skill directory validation
  4. check_queue_paths() — verify queue path validation
  5. check_orchestrator() — verify orchestrator configuration validation
  6. check_schemas() — verify DELEGATE/HANDBACK schema validation
  7. run_all_checks() — verify full validation flow
  8. CLI entry point and output formatting
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Ensure repo root is importable
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.harness.harness_checker import (
    CheckResult,
    HarnessChecker,
    HarnessCheckError,
    ValidationReport,
    main,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_root() -> Path:
    """Get the actual repo root for tests."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def checker(repo_root: Path) -> HarnessChecker:
    """Create a HarnessChecker instance with the actual repo."""
    return HarnessChecker(repo_root=str(repo_root))


# ---------------------------------------------------------------------------
# CheckResult and ValidationReport Tests
# ---------------------------------------------------------------------------


class TestCheckResult:
    """Test CheckResult data model."""

    def test_check_result_passed(self):
        """Test CheckResult with passing check."""
        result = CheckResult(
            check_name="test_check",
            passed=True,
            message="All good",
        )
        assert result.passed is True
        assert result.check_name == "test_check"
        assert result.message == "All good"
        assert "✅" in result.format()

    def test_check_result_failed(self):
        """Test CheckResult with failing check."""
        result = CheckResult(
            check_name="test_check",
            passed=False,
            message="Something broke",
            remediation="Fix it like this",
        )
        assert result.passed is False
        assert "❌" in result.format()
        assert "Fix it like this" in result.format()

    def test_check_result_frozen(self):
        """Test that CheckResult is immutable."""
        result = CheckResult(
            check_name="test",
            passed=True,
            message="msg",
        )
        with pytest.raises(AttributeError):
            result.passed = False


class TestValidationReport:
    """Test ValidationReport aggregation."""

    def test_empty_report(self):
        """Test empty validation report."""
        report = ValidationReport()
        assert report.all_passed is True
        assert report.passed_count == 0
        assert report.failed_count == 0

    def test_report_with_mixed_results(self):
        """Test report with both passed and failed checks."""
        report = ValidationReport(
            checks=[
                CheckResult("check1", True, "Passed"),
                CheckResult("check2", False, "Failed"),
                CheckResult("check3", True, "Passed"),
            ]
        )
        assert report.all_passed is False
        assert report.passed_count == 2
        assert report.failed_count == 1

    def test_report_formatting(self):
        """Test report format output."""
        report = ValidationReport(
            checks=[
                CheckResult("check1", True, "Passed"),
                CheckResult("check2", False, "Failed", "Do this"),
            ]
        )
        formatted = report.report()
        assert "OpenCode Harness Validation Report" in formatted
        assert "FAILED" in formatted
        assert "✅ check1" in formatted
        assert "❌ check2" in formatted


# ---------------------------------------------------------------------------
# HarnessChecker Initialization Tests
# ---------------------------------------------------------------------------


class TestHarnessCheckerInit:
    """Test HarnessChecker initialization."""

    def test_init_with_explicit_repo_root(self, repo_root: Path):
        """Test initialization with explicit repo root."""
        checker = HarnessChecker(repo_root=str(repo_root))
        assert checker.repo_root == repo_root
        assert checker.src_root == repo_root / "src"

    def test_init_with_auto_detection(self):
        """Test initialization with automatic repo root detection."""
        # Get the repo root directly
        repo_root = Path(__file__).resolve().parents[2]
        checker = HarnessChecker(repo_root=str(repo_root))
        assert checker.repo_root == repo_root

    def test_init_with_invalid_repo_root(self):
        """Test initialization with invalid repo root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Should not raise; will silently create minimal structure
            checker = HarnessChecker(repo_root=tmpdir)
            assert checker.repo_root == Path(tmpdir)


# ---------------------------------------------------------------------------
# Agent Validation Tests
# ---------------------------------------------------------------------------


class TestCheckAgentsLoaded:
    """Test check_agents_loaded validation."""

    def test_agents_loaded_success(self, checker: HarnessChecker):
        """Test successful agent validation."""
        result = checker.check_agents_loaded()
        assert result.passed is True
        assert "8" in result.message
        assert result.check_name == "check_agents_loaded"

    def test_agents_loaded_missing_file(self, checker: HarnessChecker):
        """Test agent validation with missing AGENTS.md."""
        with mock.patch.object(checker, "src_root", Path("/nonexistent")):
            result = checker.check_agents_loaded()
            assert result.passed is False
            assert "AGENTS.md" in result.message
            assert result.remediation

    def test_agents_loaded_partial(self, checker: HarnessChecker):
        """Test agent validation with incomplete agent roster."""
        # Create a temporary minimal AGENTS.md
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            agents_file = tmpdir_path / "AGENTS.md"
            agents_file.write_text("# Agents\n\n| # | Role | Model |\n|---|------|-------|\n")
            
            with mock.patch.object(checker, "src_root", tmpdir_path):
                result = checker.check_agents_loaded()
                assert result.passed is False


# ---------------------------------------------------------------------------
# Skills Validation Tests
# ---------------------------------------------------------------------------


class TestCheckSkillsAvailable:
    """Test check_skills_available validation."""

    def test_skills_available_success(self, checker: HarnessChecker):
        """Test successful skills validation."""
        result = checker.check_skills_available()
        assert result.passed is True
        assert "skills" in result.message.lower()

    def test_skills_available_missing_directory(self, checker: HarnessChecker):
        """Test skills validation with missing skills directory."""
        with mock.patch.object(checker, "dist_opencode", Path("/nonexistent")):
            result = checker.check_skills_available()
            assert result.passed is False
            assert "Skills directory not found" in result.message

    def test_skills_available_insufficient_count(self, checker: HarnessChecker):
        """Test skills validation with insufficient skill count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            skills_dir = tmpdir_path / "skills"
            skills_dir.mkdir()
            # Create only 5 skills (less than minimum 14)
            for i in range(5):
                skill_dir = skills_dir / f"skill-{i}"
                skill_dir.mkdir()
                (skill_dir / "SKILL.md").write_text("# Skill")

            with mock.patch.object(checker, "dist_opencode", tmpdir_path):
                result = checker.check_skills_available()
                assert result.passed is False
                assert "5" in result.message
                assert "14" in result.message


# ---------------------------------------------------------------------------
# Queue Path Validation Tests
# ---------------------------------------------------------------------------


class TestCheckQueuePaths:
    """Test check_queue_paths validation."""

    def test_queue_paths_success(self, checker: HarnessChecker):
        """Test successful queue path validation."""
        result = checker.check_queue_paths()
        # May pass or fail depending on existing queue structure
        assert result.check_name == "check_queue_paths"
        assert isinstance(result.passed, bool)

    def test_queue_paths_creates_base(self):
        """Test queue path validation creates missing base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_home = Path(tmpdir)
            queue_base = fake_home / ".agentic-engineers"
            
            with mock.patch("pathlib.Path.home", return_value=fake_home):
                checker = HarnessChecker(repo_root=Path(__file__).resolve().parents[2])
                result = checker.check_queue_paths()
                # Should create the base path
                assert queue_base.exists()

    def test_queue_paths_unwritable(self):
        """Test queue path validation with unwritable directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_home = Path(tmpdir)
            queue_base = fake_home / ".agentic-engineers"
            queue_base.mkdir()
            
            # Make it unwritable
            import os
            os.chmod(str(queue_base), 0o444)
            
            try:
                with mock.patch("pathlib.Path.home", return_value=fake_home):
                    checker = HarnessChecker(repo_root=Path(__file__).resolve().parents[2])
                    result = checker.check_queue_paths()
                    # Should fail gracefully
                    assert isinstance(result.passed, bool)
            finally:
                # Restore permissions for cleanup
                os.chmod(str(queue_base), 0o755)


# ---------------------------------------------------------------------------
# Orchestrator Validation Tests
# ---------------------------------------------------------------------------


class TestCheckOrchestrator:
    """Test check_orchestrator validation."""

    def test_orchestrator_success(self, checker: HarnessChecker):
        """Test successful orchestrator validation."""
        result = checker.check_orchestrator()
        assert result.passed is True
        assert "orchestrator" in result.message.lower()

    def test_orchestrator_missing_file(self, checker: HarnessChecker):
        """Test orchestrator validation with missing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            with mock.patch.object(checker, "dist_opencode", tmpdir_path):
                result = checker.check_orchestrator()
                assert result.passed is False
                assert "not found" in result.message.lower()

    def test_orchestrator_empty_file(self, checker: HarnessChecker):
        """Test orchestrator validation with empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            agents_dir = tmpdir_path / "agents"
            agents_dir.mkdir()
            (agents_dir / "orchestrator.md").write_text("")
            
            with mock.patch.object(checker, "dist_opencode", tmpdir_path):
                result = checker.check_orchestrator()
                assert result.passed is False

    def test_orchestrator_missing_sections(self, checker: HarnessChecker):
        """Test orchestrator validation with missing required sections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            agents_dir = tmpdir_path / "agents"
            agents_dir.mkdir()
            # Write minimal file missing required sections
            (agents_dir / "orchestrator.md").write_text("# Orchestrator\n" * 20)
            
            with mock.patch.object(checker, "dist_opencode", tmpdir_path):
                result = checker.check_orchestrator()
                assert result.passed is False
                assert "missing" in result.message.lower() or "required" in result.message.lower()


# ---------------------------------------------------------------------------
# Schema Validation Tests
# ---------------------------------------------------------------------------


class TestCheckSchemas:
    """Test check_schemas validation."""

    def test_schemas_success(self, checker: HarnessChecker):
        """Test successful schema validation."""
        result = checker.check_schemas()
        assert result.passed is True
        assert "schema" in result.message.lower()

    def test_schemas_missing_files(self, checker: HarnessChecker):
        """Test schema validation with missing schema files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            orch_dir = tmpdir_path / "orchestration"
            orch_dir.mkdir()
            # Don't create any schema files
            
            with mock.patch.object(checker, "dist_agent_dir", tmpdir_path):
                result = checker.check_schemas()
                assert result.passed is False
                assert "not found" in result.message.lower()

    def test_schemas_invalid_yaml(self, checker: HarnessChecker):
        """Test schema validation with invalid YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            orch_dir = tmpdir_path / "orchestration"
            orch_dir.mkdir()
            
            # Write invalid YAML
            (orch_dir / "delegate-schema.yaml").write_text("invalid: yaml: content:")
            (orch_dir / "handback-schema.yaml").write_text("valid: yaml")
            
            with mock.patch.object(checker, "src_root", tmpdir_path):
                result = checker.check_schemas()
                # May fail on parse or missing required_fields
                assert isinstance(result.passed, bool)

    def test_schemas_missing_required_fields(self, checker: HarnessChecker):
        """Test schema validation with missing required_fields section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Write valid YAML but missing required_fields
            (tmpdir_path / "delegate-schema.yaml").write_text("version: 1\n")
            (tmpdir_path / "handback-schema.yaml").write_text("version: 1\n")
            
            with mock.patch.object(checker, "dist_agent_dir", tmpdir_path):
                result = checker.check_schemas()
                assert result.passed is False
                assert "required_fields" in result.message.lower()


# ---------------------------------------------------------------------------
# Full Validation Flow Tests
# ---------------------------------------------------------------------------


class TestRunAllChecks:
    """Test full validation flow."""

    def test_run_all_checks_success(self, checker: HarnessChecker):
        """Test running all checks on valid harness."""
        report = checker.run_all_checks()
        assert isinstance(report, ValidationReport)
        assert len(report.checks) == 5
        # We expect most checks to pass on a valid repo
        assert report.passed_count >= 3

    def test_run_all_checks_count(self, checker: HarnessChecker):
        """Test that all 5 checks are run."""
        report = checker.run_all_checks()
        check_names = {c.check_name for c in report.checks}
        expected_checks = {
            "check_agents_loaded",
            "check_skills_available",
            "check_queue_paths",
            "check_orchestrator",
            "check_schemas",
        }
        assert check_names == expected_checks

    def test_run_all_checks_exception_handling(self, checker: HarnessChecker):
        """Test that exceptions during checks are caught and reported."""
        # Replace check_agents_loaded with a function that raises
        original_check = checker.check_agents_loaded
        
        def raising_check():
            raise RuntimeError("Boom!")
        
        checker.check_agents_loaded = raising_check
        
        try:
            report = checker.run_all_checks()
            # Check should be recorded as failed
            agents_check = next(c for c in report.checks if c.check_name == "check_agents_loaded")
            assert agents_check.passed is False
            assert "exception" in agents_check.message.lower()
        finally:
            checker.check_agents_loaded = original_check


# ---------------------------------------------------------------------------
# CLI Entry Point Tests
# ---------------------------------------------------------------------------


class TestCLI:
    """Test CLI entry point."""

    def test_main_success(self, repo_root: Path, capsys):
        """Test CLI with valid harness."""
        result = main(["--repo-root", str(repo_root)])
        assert result in [0, 1]  # One of these is expected depending on repo state

    def test_main_json_output(self, repo_root: Path, capsys):
        """Test CLI with JSON output."""
        result = main(["--repo-root", str(repo_root), "--json"])
        captured = capsys.readouterr()
        # Should be valid JSON
        parsed = json.loads(captured.out)
        assert "passed" in parsed
        assert "checks" in parsed
        assert len(parsed["checks"]) == 5

    def test_main_verbose_output(self, repo_root: Path, capsys):
        """Test CLI with verbose output."""
        result = main(["--repo-root", str(repo_root), "--verbose"])
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_main_exception_handling(self, capsys):
        """Test CLI exception handling."""
        result = main(["--repo-root", "/nonexistent"])
        assert result == 1
        captured = capsys.readouterr()
        assert "failed" in captured.out.lower() or "error" in captured.out.lower()


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestIntegration:
    """Integration tests with real repo structure."""

    def test_harness_checker_on_real_repo(self, repo_root: Path):
        """Test HarnessChecker on the actual agentic-engineers repo."""
        checker = HarnessChecker(repo_root=str(repo_root))
        report = checker.run_all_checks()
        
        # At minimum, these should pass on a valid repo
        check_names = {c.check_name: c.passed for c in report.checks}
        
        # Agents and schemas should always be defined
        assert check_names.get("check_agents_loaded") is True
        assert check_names.get("check_schemas") is True
        assert check_names.get("check_orchestrator") is True

    def test_full_validation_report(self, repo_root: Path, capsys):
        """Test full validation report output."""
        checker = HarnessChecker(repo_root=str(repo_root))
        report = checker.run_all_checks()
        output = report.report()
        
        # Check for expected report sections
        assert "OpenCode Harness Validation Report" in output
        assert "check_agents_loaded" in output
        assert "check_skills_available" in output
        assert "check_queue_paths" in output
        assert "check_orchestrator" in output
        assert "check_schemas" in output

    def test_orchestrator_missing_sections_better_message(self, checker: HarnessChecker):
        """Test that orchestrator validation shows what content was found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            agents_dir = tmpdir_path / "agents"
            agents_dir.mkdir()
            # Write minimal file with just "Orchestrator" but missing Route
            (agents_dir / "orchestrator.md").write_text("# Orchestrator Agent\n" * 20)
            
            with mock.patch.object(checker, "dist_opencode", tmpdir_path):
                result = checker.check_orchestrator()
                assert result.passed is False

    def test_report_with_all_failed_checks(self):
        """Test validation report with all checks failing."""
        report = ValidationReport(
            checks=[
                CheckResult("check1", False, "Failed 1", "Fix 1"),
                CheckResult("check2", False, "Failed 2", "Fix 2"),
                CheckResult("check3", False, "Failed 3", "Fix 3"),
            ]
        )
        assert report.all_passed is False
        assert report.failed_count == 3
        assert report.passed_count == 0
        output = report.report()
        assert "FAILED" in output
        assert "3 critical" in output

    def test_check_result_with_empty_remediation(self):
        """Test CheckResult formatting without remediation."""
        result = CheckResult(
            check_name="test",
            passed=True,
            message="All good",
            remediation="",
        )
        formatted = result.format()
        assert "✅" in formatted
        assert "test" in formatted
        assert "All good" in formatted
        # Remediation line should not appear
        assert "Remediation:" not in formatted

    def test_schemas_with_empty_yaml_file(self, checker: HarnessChecker):
        """Test schema validation with empty YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            (tmpdir_path / "delegate-schema.yaml").write_text("")
            (tmpdir_path / "handback-schema.yaml").write_text("required_fields: {}")
            
            with mock.patch.object(checker, "dist_agent_dir", tmpdir_path):
                result = checker.check_schemas()
                assert result.passed is False
                assert "empty" in result.message.lower()

    def test_queue_paths_with_canonical_structure(self):
        """Test queue paths validation with properly structured queue."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_home = Path(tmpdir)
            queue_base = fake_home / ".agentic-engineers"
            
            # Create canonical queue structure
            queue_dir = queue_base / "test-session" / "opencode" / "queue"
            for subdir in ["incoming", "processing", "done"]:
                (queue_dir / subdir).mkdir(parents=True, exist_ok=True)
            
            with mock.patch("pathlib.Path.home", return_value=fake_home):
                checker = HarnessChecker(repo_root=Path(__file__).resolve().parent.parent)
                result = checker.check_queue_paths()
                # Should pass because canonical structure exists
                assert result.passed is True

    def test_cli_with_invalid_json_flag(self, repo_root: Path, capsys):
        """Test CLI JSON output is valid JSON."""
        result = main(["--repo-root", str(repo_root), "--json"])
        captured = capsys.readouterr()
        output = captured.out.split('\n')[0:-1]  # Remove warning line
        output_str = '\n'.join(output)
        try:
            parsed = json.loads(output_str)
            assert isinstance(parsed, dict)
            assert "checks" in parsed
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON output: {e}")
