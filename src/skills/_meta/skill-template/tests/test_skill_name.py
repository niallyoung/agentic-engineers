"""TDD RED-phase test scaffold for <skill-name>.

Replace all <PLACEHOLDER> values before implementing.
Tests should be written BEFORE the implementation (TDD RED phase).
Once tests pass, update ``tdd_phase: GREEN`` in SKILL.md.

Running the tests:
    python -m pytest src/skills/<skill-name>/tests/ -v

Coverage target: ≥90%
"""
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Import the skill under test
# Replace with the real module path once the skill is implemented.
# ---------------------------------------------------------------------------
# from src.skills.<skill_name>.scripts.<skill_name> import (
#     <SkillClass>,
#     <SkillConfig>,
#     <SkillResult>,
# )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def default_config():
    """Return a default <SkillConfig> for testing."""
    # return <SkillConfig>()
    return {}  # TODO: replace with real config


@pytest.fixture
def skill(default_config):
    """Return an instance of <SkillClass> for testing."""
    # return <SkillClass>(default_config)
    return None  # TODO: replace with real skill


# ---------------------------------------------------------------------------
# Unit tests — happy path
# ---------------------------------------------------------------------------

class TestSkillHappyPath:
    """Tests for expected successful behaviour."""

    def test_run_returns_success_status(self, skill):
        """Skill.run() should return status='success' for valid input."""
        pytest.skip("TODO: implement <skill-name> and remove this skip")
        # result = skill.run()
        # assert result.status == "success"

    def test_run_returns_result_object(self, skill):
        """Skill.run() should return a <SkillResult> instance."""
        pytest.skip("TODO: implement <skill-name> and remove this skip")
        # result = skill.run()
        # assert isinstance(result, <SkillResult>)

    def test_quality_score_above_threshold(self, skill):
        """Quality score should be ≥90 for valid input."""
        pytest.skip("TODO: implement <skill-name> and remove this skip")
        # result = skill.run()
        # assert result.quality_score >= 90

    def test_no_errors_on_valid_input(self, skill):
        """No errors should be returned for valid input."""
        pytest.skip("TODO: implement <skill-name> and remove this skip")
        # result = skill.run()
        # assert result.errors == []


# ---------------------------------------------------------------------------
# Unit tests — dry-run mode
# ---------------------------------------------------------------------------

class TestDryRun:
    """Tests for dry-run behaviour (no side effects)."""

    def test_dry_run_returns_skipped_status(self):
        """Dry-run mode should return status='skipped'."""
        pytest.skip("TODO: implement <skill-name> and remove this skip")
        # cfg = <SkillConfig>(dry_run=True)
        # result = <SkillClass>(cfg).run()
        # assert result.status == "skipped"

    def test_dry_run_makes_no_file_changes(self, tmp_path):
        """Dry-run should not create or modify any files."""
        pytest.skip("TODO: implement <skill-name> and remove this skip")
        # cfg = <SkillConfig>(input_path=str(tmp_path), dry_run=True)
        # <SkillClass>(cfg).run()
        # assert list(tmp_path.iterdir()) == []  # no new files


# ---------------------------------------------------------------------------
# Unit tests — error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Tests for graceful error handling."""

    def test_missing_input_path_returns_failure(self):
        """Missing input path should return status='failure', not raise."""
        pytest.skip("TODO: implement <skill-name> and remove this skip")
        # cfg = <SkillConfig>(input_path="/nonexistent/path/xyz")
        # result = <SkillClass>(cfg).run()
        # assert result.status == "failure"
        # assert len(result.errors) > 0

    def test_result_str_representation(self):
        """Result __str__ should be non-empty and human-readable."""
        pytest.skip("TODO: implement <skill-name> and remove this skip")
        # result = <SkillResult>(status="success", findings=["ok"])
        # output = str(result)
        # assert "[SUCCESS]" in output


# ---------------------------------------------------------------------------
# Unit tests — CLI entry point
# ---------------------------------------------------------------------------

class TestCLI:
    """Tests for the CLI entry point (main function)."""

    def test_cli_help_exits_zero(self):
        """--help flag should exit with code 0."""
        pytest.skip("TODO: implement <skill-name> and remove this skip")
        # from src.skills.<skill_name>.scripts.<skill_name> import main
        # with pytest.raises(SystemExit) as exc_info:
        #     main(["--help"])
        # assert exc_info.value.code == 0

    def test_cli_dry_run_flag(self):
        """--dry-run flag should not raise an exception."""
        pytest.skip("TODO: implement <skill-name> and remove this skip")
        # from src.skills.<skill_name>.scripts.<skill_name> import main
        # exit_code = main(["--dry-run"])
        # assert exit_code in (0, 1)  # skipped → 1 is acceptable


# ---------------------------------------------------------------------------
# Integration tests (optional)
# ---------------------------------------------------------------------------

class TestIntegration:
    """End-to-end integration tests (may be slow; mark with @pytest.mark.slow)."""

    def test_end_to_end_on_fixture_data(self, tmp_path):
        """Skill should process a known fixture directory correctly."""
        pytest.skip("TODO: create fixture data and implement integration test")
