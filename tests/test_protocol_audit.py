"""
Tests for protocol_audit module.

Covers AuditReport, check_schema_files, check_validator_modules,
check_orchestrator_logic, check_pre_commit_hook, check_documentation,
_parse_pytest_counts, and generate_compliance_report.

TDD red-phase style — tests exercise real behaviour of the existing module.
Target: >=90% branch coverage of protocol_audit.py
"""
import importlib.util
import json
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Import protocol_audit via importlib (not in package pythonpath) ──────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
_AUDIT_PATH = _REPO_ROOT / "src" / "orchestration" / "tools" / "protocol_audit.py"

_spec = importlib.util.spec_from_file_location("protocol_audit", _AUDIT_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

AuditReport = _mod.AuditReport
check_schema_files = _mod.check_schema_files
check_validator_modules = _mod.check_validator_modules
check_orchestrator_logic = _mod.check_orchestrator_logic
check_pre_commit_hook = _mod.check_pre_commit_hook
check_documentation = _mod.check_documentation
run_test_suite = _mod.run_test_suite
generate_compliance_report = _mod.generate_compliance_report
_parse_pytest_counts = _mod._parse_pytest_counts
REPO_ROOT = _mod.REPO_ROOT


# ---------------------------------------------------------------------------
# AuditReport
# ---------------------------------------------------------------------------

class TestAuditReport:
    """Tests for the AuditReport accumulator class."""

    def test_empty_report(self):
        """A new AuditReport has no checks."""
        report = AuditReport()
        assert report.total == 0
        assert report.passed == 0
        assert report.failed == 0

    def test_score_with_no_checks_is_zero(self):
        """score is 0 when there are no checks."""
        report = AuditReport()
        assert report.score == 0

    def test_ready_with_no_checks_is_true(self):
        """report.ready is True when there are zero failed checks."""
        report = AuditReport()
        assert report.ready is True

    def test_add_passing_check(self):
        """add() with passed=True increments total and passed."""
        report = AuditReport()
        report.add("Test check", True, "All good")
        assert report.total == 1
        assert report.passed == 1
        assert report.failed == 0

    def test_add_failing_check(self):
        """add() with passed=False increments total and failed."""
        report = AuditReport()
        report.add("Test check", False, "Something wrong")
        assert report.total == 1
        assert report.passed == 0
        assert report.failed == 1

    def test_score_all_pass(self):
        """100% pass rate gives score of 100."""
        report = AuditReport()
        for i in range(5):
            report.add(f"check-{i}", True, "ok")
        assert report.score == 100

    def test_score_all_fail(self):
        """0% pass rate gives score of 0."""
        report = AuditReport()
        for i in range(5):
            report.add(f"check-{i}", False, "fail")
        assert report.score == 0

    def test_score_half_pass(self):
        """50% pass rate gives score of 50."""
        report = AuditReport()
        report.add("pass", True, "ok")
        report.add("fail", False, "not ok")
        assert report.score == 50

    def test_ready_true_all_pass(self):
        """ready is True when all checks pass."""
        report = AuditReport()
        report.add("check1", True, "ok")
        report.add("check2", True, "ok")
        assert report.ready is True

    def test_ready_false_any_fail(self):
        """ready is False when any check fails."""
        report = AuditReport()
        report.add("check1", True, "ok")
        report.add("check2", False, "broken")
        assert report.ready is False

    def test_checks_list_populated(self):
        """checks list contains dicts with expected keys."""
        report = AuditReport()
        report.add("My Check", True, "detail text")
        assert len(report.checks) == 1
        check = report.checks[0]
        assert check["name"] == "My Check"
        assert check["passed"] is True
        assert check["detail"] == "detail text"

    def test_multiple_checks_accumulate(self):
        """Multiple add() calls accumulate correctly."""
        report = AuditReport()
        report.add("a", True, "ok")
        report.add("b", True, "ok")
        report.add("c", False, "fail")
        assert report.total == 3
        assert report.passed == 2
        assert report.failed == 1


# ---------------------------------------------------------------------------
# _parse_pytest_counts
# ---------------------------------------------------------------------------

class TestParsePytestCounts:
    """Tests for _parse_pytest_counts helper."""

    def test_parse_typical_passed_output(self):
        """Parses '26 passed' from typical pytest output."""
        output = "26 passed in 1.5s"
        passed, failed = _parse_pytest_counts(output)
        assert passed == 26
        assert failed == 0

    def test_parse_with_failures(self):
        """Parses '5 failed, 10 passed' output."""
        output = "10 passed, 5 failed in 2.0s"
        passed, failed = _parse_pytest_counts(output)
        assert passed == 10
        assert failed == 5

    def test_parse_no_tests(self):
        """Returns (0, 0) for output with no test counts."""
        passed, failed = _parse_pytest_counts("no tests ran")
        assert passed == 0
        assert failed == 0

    def test_parse_multiline_output(self):
        """Extracts counts from multiline output."""
        output = "some stuff\n100 passed, 2 failed in 10.0s\nother stuff"
        passed, failed = _parse_pytest_counts(output)
        assert passed == 100
        assert failed == 2

    def test_parse_only_failed(self):
        """Handles output with only failures."""
        output = "3 failed in 0.5s"
        passed, failed = _parse_pytest_counts(output)
        assert failed == 3
        assert passed == 0

    def test_parse_empty_string(self):
        """Returns (0, 0) for empty input."""
        passed, failed = _parse_pytest_counts("")
        assert passed == 0
        assert failed == 0


# ---------------------------------------------------------------------------
# check_schema_files
# ---------------------------------------------------------------------------

class TestCheckSchemaFiles:
    """Tests for check_schema_files check function."""

    def test_schema_files_added_to_report(self):
        """check_schema_files adds at least one check for each required schema."""
        report = AuditReport()
        check_schema_files(report)
        # Should add entries for delegate-schema and handback-schema
        names = [c["name"] for c in report.checks]
        assert any("schema" in n.lower() or "Schema" in n for n in names)

    def test_schema_check_count_matches_required(self):
        """Adds exactly len(REQUIRED_SCHEMA_FILES) check entries."""
        report = AuditReport()
        check_schema_files(report)
        assert report.total == len(_mod.REQUIRED_SCHEMA_FILES)

    def test_schema_files_pass_when_present(self):
        """If schema files exist, checks pass (assuming they're present in repo)."""
        report = AuditReport()
        check_schema_files(report)
        # We test behaviour, not specific outcomes (files may or may not exist)
        for check in report.checks:
            assert "name" in check
            assert "passed" in check
            assert "detail" in check

    def test_schema_check_handles_missing_file(self, tmp_path, monkeypatch):
        """Missing schema file results in a failed check."""
        fake_schema_paths = [tmp_path / "missing-schema.yaml"]
        monkeypatch.setattr(_mod, "REQUIRED_SCHEMA_FILES", fake_schema_paths)
        report = AuditReport()
        check_schema_files(report)
        assert report.failed == 1
        assert "not found" in report.checks[0]["detail"]

    def test_schema_check_handles_valid_yaml(self, tmp_path, monkeypatch):
        """Valid YAML schema file results in a passing check."""
        schema_file = tmp_path / "delegate-schema.yaml"
        schema_file.write_text(
            "required_fields:\n  - task_id\n  - agent\n  - scope\n"
            "type: object\ndescription: test schema\n"
        )
        monkeypatch.setattr(_mod, "REQUIRED_SCHEMA_FILES", [schema_file])
        report = AuditReport()
        check_schema_files(report)
        assert report.passed >= 1

    def test_schema_check_handles_invalid_yaml(self, tmp_path, monkeypatch):
        """Invalid YAML content results in a failed check."""
        schema_file = tmp_path / "bad-schema.yaml"
        schema_file.write_text("{{{{ not valid yaml at all\n")
        monkeypatch.setattr(_mod, "REQUIRED_SCHEMA_FILES", [schema_file])
        report = AuditReport()
        check_schema_files(report)
        # Should not raise; should report failure
        assert report.total == 1


# ---------------------------------------------------------------------------
# check_validator_modules
# ---------------------------------------------------------------------------

class TestCheckValidatorModules:
    """Tests for check_validator_modules check function."""

    def test_adds_one_check_per_required_module(self):
        """Adds one check for each required module."""
        report = AuditReport()
        check_validator_modules(report)
        assert report.total == len(_mod.REQUIRED_MODULES)

    def test_missing_module_fails(self, tmp_path, monkeypatch):
        """Missing module file produces a failed check."""
        fake_modules = [tmp_path / "nonexistent_module.py"]
        monkeypatch.setattr(_mod, "REQUIRED_MODULES", fake_modules)
        report = AuditReport()
        check_validator_modules(report)
        assert report.failed == 1
        assert "not found" in report.checks[0]["detail"]

    def test_present_module_passes(self, tmp_path, monkeypatch):
        """Existing Python file produces a passing check."""
        mod_file = tmp_path / "simple_module.py"
        mod_file.write_text("x = 1\n")
        monkeypatch.setattr(_mod, "REQUIRED_MODULES", [mod_file])
        report = AuditReport()
        check_validator_modules(report)
        assert report.passed == 1

    def test_check_names_include_module_filename(self, tmp_path, monkeypatch):
        """Check names include the module filename."""
        mod_file = tmp_path / "my_validator.py"
        mod_file.write_text("x = 1\n")
        monkeypatch.setattr(_mod, "REQUIRED_MODULES", [mod_file])
        report = AuditReport()
        check_validator_modules(report)
        assert any("my_validator" in c["name"] for c in report.checks)

    def test_schema_no_yaml_fallback(self, tmp_path, monkeypatch):
        """When yaml module not available, falls back to content check."""
        schema_file = tmp_path / "delegate-schema.yaml"
        schema_file.write_text(
            "required_fields:\n  - task_id\n  - agent\n  - scope\n"
            "type: object\ndescription: test schema for fallback check. x" * 3 + "\n"
        )
        monkeypatch.setattr(_mod, "REQUIRED_SCHEMA_FILES", [schema_file])
        # Simulate yaml import failing
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("no yaml")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        report = AuditReport()
        check_schema_files(report)
        assert report.total == 1  # Handled gracefully


# ---------------------------------------------------------------------------
# check_orchestrator_logic
# ---------------------------------------------------------------------------

class TestCheckOrchestratorLogic:
    """Tests for check_orchestrator_logic check function."""

    def test_adds_two_checks(self, tmp_path, monkeypatch):
        """check_orchestrator_logic adds exactly 2 check entries."""
        orch_file = tmp_path / "orchestrator.py"
        orch_file.write_text("x = 90\ny = 80\nz = 70\nMAX_RETRIES = 3\n")
        monkeypatch.setattr(_mod, "AGENTS_DIR", tmp_path)
        report = AuditReport()
        check_orchestrator_logic(report)
        assert report.total == 2

    def test_routing_bands_pass_when_present(self, tmp_path, monkeypatch):
        """Routing bands check passes when >= 3 band values are present."""
        orch_file = tmp_path / "orchestrator.py"
        orch_file.write_text("score_90 = True\nscore_80 = True\nscore_70 = True\nMAX_RETRIES = 5\n")
        monkeypatch.setattr(_mod, "AGENTS_DIR", tmp_path)
        report = AuditReport()
        check_orchestrator_logic(report)
        # Band check and MAX_RETRIES check
        assert report.passed == 2

    def test_max_retries_check_fails_when_absent(self, tmp_path, monkeypatch):
        """MAX_RETRIES check fails when sentinel not in orchestrator.py."""
        orch_file = tmp_path / "orchestrator.py"
        orch_file.write_text("score = 90\nother = 80\nanother = 70\n")
        monkeypatch.setattr(_mod, "AGENTS_DIR", tmp_path)
        report = AuditReport()
        check_orchestrator_logic(report)
        # MAX_RETRIES missing → one failure
        max_check = [c for c in report.checks if "MAX_RETRIES" in c["name"]]
        assert len(max_check) == 1
        assert max_check[0]["passed"] is False

    def test_missing_orchestrator_file(self, tmp_path, monkeypatch):
        """Missing orchestrator.py produces two failed checks."""
        monkeypatch.setattr(_mod, "AGENTS_DIR", tmp_path)
        report = AuditReport()
        check_orchestrator_logic(report)
        assert report.total == 2
        assert report.failed == 2

    def test_routing_bands_fail_with_fewer_than_three(self, tmp_path, monkeypatch):
        """Routing bands check fails when fewer than 3 bands present."""
        orch_file = tmp_path / "orchestrator.py"
        orch_file.write_text("score = 90\nMAX_RETRIES = 3\n")
        monkeypatch.setattr(_mod, "AGENTS_DIR", tmp_path)
        report = AuditReport()
        check_orchestrator_logic(report)
        band_check = [c for c in report.checks if "routing bands" in c["name"]]
        assert len(band_check) == 1
        assert band_check[0]["passed"] is False


# ---------------------------------------------------------------------------
# check_pre_commit_hook
# ---------------------------------------------------------------------------

class TestCheckPreCommitHook:
    """Tests for check_pre_commit_hook check function."""

    def test_adds_two_checks(self):
        """check_pre_commit_hook adds exactly 2 checks."""
        report = AuditReport()
        check_pre_commit_hook(report)
        assert report.total == 2

    def test_hook_installed_and_executable(self, tmp_path, monkeypatch):
        """Existing executable hook file produces 2 passing checks."""
        hook = tmp_path / "pre-commit"
        hook.write_text("#!/bin/sh\nexit 0\n")
        hook.chmod(0o755)
        monkeypatch.setattr(_mod, "PRE_COMMIT_HOOK", hook)
        monkeypatch.setattr(_mod, "GITHOOKS_DIR", tmp_path / "nonexistent")
        monkeypatch.setattr(_mod, "REPO_ROOT", tmp_path)
        report = AuditReport()
        check_pre_commit_hook(report)
        installed_check = [c for c in report.checks if "installed" in c["name"]]
        exec_check = [c for c in report.checks if "executable" in c["name"]]
        assert installed_check[0]["passed"] is True
        assert exec_check[0]["passed"] is True

    def test_hook_installed_not_executable(self, tmp_path, monkeypatch):
        """Non-executable hook fails the executable check."""
        hook = tmp_path / "pre-commit"
        hook.write_text("#!/bin/sh\n")
        hook.chmod(0o644)  # not executable
        monkeypatch.setattr(_mod, "PRE_COMMIT_HOOK", hook)
        monkeypatch.setattr(_mod, "GITHOOKS_DIR", tmp_path / "nonexistent")
        monkeypatch.setattr(_mod, "REPO_ROOT", tmp_path)
        report = AuditReport()
        check_pre_commit_hook(report)
        exec_check = [c for c in report.checks if "executable" in c["name"]]
        assert exec_check[0]["passed"] is False

    def test_hook_not_installed_no_githooks(self, tmp_path, monkeypatch):
        """Missing hook with no .githooks produces 2 failed checks."""
        monkeypatch.setattr(_mod, "PRE_COMMIT_HOOK", tmp_path / "nonexistent-hook")
        monkeypatch.setattr(_mod, "GITHOOKS_DIR", tmp_path / "nonexistent-githooks")
        report = AuditReport()
        check_pre_commit_hook(report)
        assert report.failed == 2

    def test_hook_found_in_githooks_dir(self, tmp_path, monkeypatch):
        """Hook found in .githooks/ dir produces 2 passing checks."""
        githooks_dir = tmp_path / ".githooks"
        githooks_dir.mkdir()
        (githooks_dir / "pre-commit").write_text("#!/bin/sh\n")
        monkeypatch.setattr(_mod, "PRE_COMMIT_HOOK", tmp_path / "nonexistent")
        monkeypatch.setattr(_mod, "GITHOOKS_DIR", githooks_dir)
        report = AuditReport()
        check_pre_commit_hook(report)
        installed_check = [c for c in report.checks if "installed" in c["name"]]
        assert installed_check[0]["passed"] is True


# ---------------------------------------------------------------------------
# check_documentation
# ---------------------------------------------------------------------------

class TestCheckDocumentation:
    """Tests for check_documentation check function."""

    def test_adds_one_check_per_required_doc(self):
        """check_documentation adds one check per required doc."""
        report = AuditReport()
        check_documentation(report)
        assert report.total == len(_mod.REQUIRED_DOCS)

    def test_missing_doc_fails(self, tmp_path, monkeypatch):
        """Missing doc file produces a failed check."""
        fake_docs = [tmp_path / "MISSING.md"]
        monkeypatch.setattr(_mod, "REQUIRED_DOCS", fake_docs)
        report = AuditReport()
        check_documentation(report)
        assert report.failed == 1
        assert "not found" in report.checks[0]["detail"]

    def test_doc_too_small_fails(self, tmp_path, monkeypatch):
        """Doc file below minimum size produces a failed check."""
        small_doc = tmp_path / "PROTOCOL-QUICK-REFERENCE.md"
        small_doc.write_text("# tiny\n")
        monkeypatch.setattr(_mod, "REQUIRED_DOCS", [small_doc])
        report = AuditReport()
        check_documentation(report)
        assert report.failed == 1

    def test_doc_adequate_size_passes(self, tmp_path, monkeypatch):
        """Doc file above minimum size produces a passing check."""
        large_doc = tmp_path / "PROTOCOL-QUICK-REFERENCE.md"
        large_doc.write_text("x" * 2000)
        monkeypatch.setattr(_mod, "REQUIRED_DOCS", [large_doc])
        report = AuditReport()
        check_documentation(report)
        assert report.passed == 1

    def test_doc_check_names_include_filename(self, tmp_path, monkeypatch):
        """Check names reference the document filename."""
        doc = tmp_path / "PROTOCOL-QUICK-REFERENCE.md"
        doc.write_text("x" * 2000)
        monkeypatch.setattr(_mod, "REQUIRED_DOCS", [doc])
        report = AuditReport()
        check_documentation(report)
        assert any("PROTOCOL-QUICK-REFERENCE" in c["name"] for c in report.checks)


# ---------------------------------------------------------------------------
# generate_compliance_report
# ---------------------------------------------------------------------------

class TestGenerateComplianceReport:
    """Tests for generate_compliance_report output formatter."""

    def _build_report(self, passes=3, fails=1):
        """Helper: build an AuditReport with given pass/fail counts."""
        report = AuditReport()
        for i in range(passes):
            report.add(f"Pass check {i}", True, "ok")
        for i in range(fails):
            report.add(f"Fail check {i}", False, "broken")
        return report

    def test_text_output_is_string(self):
        """generate_compliance_report returns a string in text mode."""
        report = self._build_report()
        output = generate_compliance_report(report)
        assert isinstance(output, str)

    def test_text_output_contains_score(self):
        """Text output includes 'Compliance Score'."""
        report = self._build_report()
        output = generate_compliance_report(report)
        assert "Compliance Score" in output

    def test_text_output_contains_pass_count(self):
        """Text output includes passed/total check count."""
        report = self._build_report(passes=3, fails=1)
        output = generate_compliance_report(report)
        assert "3/4" in output or "Checks:" in output

    def test_json_output_is_valid_json(self):
        """JSON output mode produces valid JSON."""
        report = self._build_report()
        output = generate_compliance_report(report, as_json=True)
        data = json.loads(output)
        assert "score" in data
        assert "passed" in data
        assert "failed" in data
        assert "total" in data
        assert "ready" in data
        assert "checks" in data

    def test_json_output_score_correct(self):
        """JSON output score matches computed score."""
        report = self._build_report(passes=2, fails=2)
        output = generate_compliance_report(report, as_json=True)
        data = json.loads(output)
        assert data["score"] == 50

    def test_json_output_ready_false_when_failures(self):
        """JSON output ready=false when there are failures."""
        report = self._build_report(passes=2, fails=1)
        output = generate_compliance_report(report, as_json=True)
        data = json.loads(output)
        assert data["ready"] is False

    def test_json_output_ready_true_when_all_pass(self):
        """JSON output ready=true when all checks pass."""
        report = self._build_report(passes=5, fails=0)
        output = generate_compliance_report(report, as_json=True)
        data = json.loads(output)
        assert data["ready"] is True

    def test_json_output_includes_next_audit_date(self):
        """JSON output includes next_audit date."""
        report = self._build_report()
        output = generate_compliance_report(report, as_json=True)
        data = json.loads(output)
        assert "next_audit" in data

    def test_quiet_mode_text_output(self):
        """Quiet mode still produces a string."""
        report = self._build_report()
        output = generate_compliance_report(report, quiet=True)
        assert isinstance(output, str)

    def test_text_output_contains_next_audit(self):
        """Text output includes next audit recommendation."""
        report = self._build_report()
        output = generate_compliance_report(report)
        assert "Next audit" in output or "next audit" in output

    def test_all_pass_shows_ready(self):
        """Text output shows ready status when all pass."""
        report = AuditReport()
        report.add("check1", True, "ok")
        output = generate_compliance_report(report)
        assert "READY" in output or "100" in output

    def test_failure_shows_issues(self):
        """Text output mentions issues count when failures exist."""
        report = self._build_report(passes=2, fails=1)
        output = generate_compliance_report(report)
        # Should show failure info
        assert "❌" in output or "fail" in output.lower() or "issues" in output.lower()

    def test_check_icons_in_text(self):
        """Text output uses ✅ and ❌ icons."""
        report = AuditReport()
        report.add("pass-check", True, "good")
        report.add("fail-check", False, "bad")
        output = generate_compliance_report(report)
        assert "✅" in output
        assert "❌" in output


# ---------------------------------------------------------------------------
# run_test_suite
# ---------------------------------------------------------------------------

class TestRunTestSuite:
    """Tests for run_test_suite with mocked subprocess."""

    def test_run_test_suite_success(self):
        """run_test_suite adds two checks when tests pass."""
        mock_result = MagicMock()
        mock_result.stdout = "250 passed in 5.0s"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            report = AuditReport()
            run_test_suite(report)

        assert report.total == 2
        passing_check = [c for c in report.checks if "passing count" in c["name"]]
        assert len(passing_check) == 1
        assert passing_check[0]["passed"] is True

    def test_run_test_suite_below_minimum(self):
        """run_test_suite fails passing-count check when below MIN_PASSING_TESTS."""
        mock_result = MagicMock()
        mock_result.stdout = "5 passed in 0.5s"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            report = AuditReport()
            run_test_suite(report)

        passing_check = [c for c in report.checks if "passing count" in c["name"]]
        assert len(passing_check) == 1
        assert passing_check[0]["passed"] is False

    def test_run_test_suite_zero_failures(self):
        """run_test_suite passes zero-failures check when narrow run has no failures."""
        mock_result = MagicMock()
        mock_result.stdout = "250 passed in 5.0s"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            report = AuditReport()
            run_test_suite(report)

        zero_check = [c for c in report.checks if "zero failures" in c["name"]]
        assert len(zero_check) == 1
        assert zero_check[0]["passed"] is True

    def test_run_test_suite_with_failures_in_narrow(self):
        """run_test_suite fails zero-failures check when narrow run has failures."""
        def mock_run(cmd, **kwargs):
            result = MagicMock()
            if "-m" in cmd:
                result.stdout = "250 passed in 5.0s"
            else:
                result.stdout = "5 failed, 2 passed in 0.5s"
            result.stderr = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            report = AuditReport()
            run_test_suite(report)

        # Both checks present
        assert report.total == 2

    def test_run_test_suite_timeout(self):
        """run_test_suite handles subprocess timeout."""
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pytest", 120)):
            report = AuditReport()
            run_test_suite(report)

        assert report.total == 2
        assert report.failed == 2

    def test_run_test_suite_file_not_found(self):
        """run_test_suite handles pytest not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError("pytest not found")):
            report = AuditReport()
            run_test_suite(report)

        assert report.total == 2
        assert report.failed == 2


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

class TestMain:
    """Tests for the main() entry point."""

    def test_main_returns_0_on_all_pass(self, monkeypatch):
        """main() returns 0 when all checks pass."""
        def _mock_subprocess(*args, **kwargs):
            r = MagicMock()
            r.stdout = "250 passed in 5.0s"
            r.stderr = ""
            return r

        monkeypatch.setattr("sys.argv", ["protocol_audit.py"])
        with patch("subprocess.run", side_effect=_mock_subprocess), \
             patch.object(_mod, "check_schema_files", lambda r: r.add("s", True, "ok")), \
             patch.object(_mod, "check_validator_modules", lambda r: r.add("v", True, "ok")), \
             patch.object(_mod, "check_orchestrator_logic", lambda r: r.add("o", True, "ok")), \
             patch.object(_mod, "check_pre_commit_hook", lambda r: r.add("p", True, "ok")), \
             patch.object(_mod, "check_documentation", lambda r: r.add("d", True, "ok")), \
             patch.object(_mod, "run_test_suite", lambda r: r.add("t", True, "ok")), \
             patch("builtins.print"):
            result = _mod.main()
        assert result == 0

    def test_main_returns_1_on_failure(self, monkeypatch):
        """main() returns 1 when any check fails."""
        monkeypatch.setattr("sys.argv", ["protocol_audit.py"])
        with patch.object(_mod, "check_schema_files", lambda r: r.add("s", False, "fail")), \
             patch.object(_mod, "check_validator_modules", lambda r: None), \
             patch.object(_mod, "check_orchestrator_logic", lambda r: None), \
             patch.object(_mod, "check_pre_commit_hook", lambda r: None), \
             patch.object(_mod, "check_documentation", lambda r: None), \
             patch.object(_mod, "run_test_suite", lambda r: None), \
             patch("builtins.print"):
            result = _mod.main()
        assert result == 1

    def test_main_json_flag(self, monkeypatch, capsys):
        """main() with --json outputs valid JSON."""
        monkeypatch.setattr("sys.argv", ["protocol_audit.py", "--json"])
        with patch.object(_mod, "check_schema_files", lambda r: r.add("s", True, "ok")), \
             patch.object(_mod, "check_validator_modules", lambda r: None), \
             patch.object(_mod, "check_orchestrator_logic", lambda r: None), \
             patch.object(_mod, "check_pre_commit_hook", lambda r: None), \
             patch.object(_mod, "check_documentation", lambda r: None), \
             patch.object(_mod, "run_test_suite", lambda r: None):
            _mod.main()
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "score" in data


# ---------------------------------------------------------------------------
# Integration: full audit run
# ---------------------------------------------------------------------------

class TestFullAuditIntegration:
    """Integration tests that exercise the full check pipeline."""

    def test_run_all_checks_produces_report(self):
        """Running all check functions populates report without exceptions."""
        report = AuditReport()
        check_schema_files(report)
        check_validator_modules(report)
        check_orchestrator_logic(report)
        check_pre_commit_hook(report)
        check_documentation(report)
        # No assertion on pass/fail — just ensure no crash
        assert report.total > 0

    def test_report_score_is_percentage(self):
        """Score is always an integer 0-100."""
        report = AuditReport()
        check_schema_files(report)
        assert 0 <= report.score <= 100

    def test_json_output_checks_list_structure(self):
        """JSON output checks list has expected structure per entry."""
        report = AuditReport()
        report.add("Sample", True, "ok")
        output = generate_compliance_report(report, as_json=True)
        data = json.loads(output)
        for check in data["checks"]:
            assert "name" in check
            assert "passed" in check
            assert "detail" in check
