"""Comprehensive test suite for skill_catalog module."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from src.harnesses.claude_code.skill_catalog import SkillCatalog, SkillRenderResult
from src.harnesses.claude_code.skill_manager import SkillManager


class TestSkillRendering:
    """Test skill rendering functionality."""

    def test_render_skill_returns_result(self, skills_root: Path) -> None:
        """Test that render_skill returns SkillRenderResult."""
        catalog = SkillCatalog(skills_root)
        result = catalog.render_skill("agent-creator")
        assert isinstance(result, SkillRenderResult)

    def test_render_skill_successful_has_metadata(self, skills_root: Path) -> None:
        """Test that successful render has metadata."""
        catalog = SkillCatalog(skills_root)
        result = catalog.render_skill("agent-creator")
        assert result.success is True
        assert result.metadata is not None

    def test_render_skill_successful_no_error(self, skills_root: Path) -> None:
        """Test that successful render has no error."""
        catalog = SkillCatalog(skills_root)
        result = catalog.render_skill("agent-creator")
        assert result.success is True
        assert result.error is None

    def test_render_skill_has_render_time(self, skills_root: Path) -> None:
        """Test that render result includes timing."""
        catalog = SkillCatalog(skills_root)
        result = catalog.render_skill("agent-creator")
        assert result.render_time_ms >= 0

    def test_render_skill_nonexistent_fails(self, skills_root: Path) -> None:
        """Test that rendering non-existent skill fails."""
        catalog = SkillCatalog(skills_root)
        result = catalog.render_skill("nonexistent-skill")
        assert result.success is False

    def test_render_all_skills_returns_dict(self, skills_root: Path) -> None:
        """Test that render_all_skills returns dictionary."""
        catalog = SkillCatalog(skills_root)
        results = catalog.render_all_skills()
        assert isinstance(results, dict)

    def test_render_all_skills_non_empty(self, skills_root: Path) -> None:
        """Test that render_all_skills returns non-empty dict."""
        catalog = SkillCatalog(skills_root)
        results = catalog.render_all_skills()
        assert len(results) > 0

    def test_render_all_skills_all_keys_are_strings(self, skills_root: Path) -> None:
        """Test that all keys in render results are strings."""
        catalog = SkillCatalog(skills_root)
        results = catalog.render_all_skills()
        assert all(isinstance(key, str) for key in results.keys())

    def test_render_all_skills_all_values_are_results(self, skills_root: Path) -> None:
        """Test that all values are SkillRenderResult."""
        catalog = SkillCatalog(skills_root)
        results = catalog.render_all_skills()
        assert all(isinstance(v, SkillRenderResult) for v in results.values())


class TestSkillInvocationTesting:
    """Test end-to-end skill invocation testing."""

    def test_test_skill_invocation_returns_dict(self, skills_root: Path) -> None:
        """Test that test_skill_invocation returns dictionary."""
        catalog = SkillCatalog(skills_root)
        result = catalog.test_skill_invocation("agent-creator")
        assert isinstance(result, dict)

    def test_test_skill_invocation_has_skill_name(self, skills_root: Path) -> None:
        """Test that invocation test has skill_name field."""
        catalog = SkillCatalog(skills_root)
        result = catalog.test_skill_invocation("agent-creator")
        assert "skill_name" in result
        assert result["skill_name"] == "agent-creator"

    def test_test_skill_invocation_has_test_passed(self, skills_root: Path) -> None:
        """Test that invocation test has test_passed field."""
        catalog = SkillCatalog(skills_root)
        result = catalog.test_skill_invocation("agent-creator")
        assert "test_passed" in result
        assert isinstance(result["test_passed"], bool)

    def test_test_skill_invocation_has_checks(self, skills_root: Path) -> None:
        """Test that invocation test has checks field."""
        catalog = SkillCatalog(skills_root)
        result = catalog.test_skill_invocation("agent-creator")
        assert "checks" in result
        assert isinstance(result["checks"], dict)

    def test_test_skill_invocation_has_errors(self, skills_root: Path) -> None:
        """Test that invocation test has errors field."""
        catalog = SkillCatalog(skills_root)
        result = catalog.test_skill_invocation("agent-creator")
        assert "errors" in result
        assert isinstance(result["errors"], list)

    def test_test_skill_invocation_valid_skill_passes(self, skills_root: Path) -> None:
        """Test that valid skill invocation passes."""
        catalog = SkillCatalog(skills_root)
        result = catalog.test_skill_invocation("agent-creator")
        assert result["test_passed"] is True

    def test_test_all_skills_invocation_returns_dict(self, skills_root: Path) -> None:
        """Test that test_all_skills_invocation returns dictionary."""
        catalog = SkillCatalog(skills_root)
        results = catalog.test_all_skills_invocation()
        assert isinstance(results, dict)

    def test_test_all_skills_invocation_non_empty(self, skills_root: Path) -> None:
        """Test that test_all_skills_invocation has results."""
        catalog = SkillCatalog(skills_root)
        results = catalog.test_all_skills_invocation()
        assert len(results) > 0


class TestSkillAccessibilityVerification:
    """Test skill accessibility verification."""

    def test_verify_skill_accessibility_returns_dict(self, skills_root: Path) -> None:
        """Test that verify_skill_accessibility returns dictionary."""
        catalog = SkillCatalog(skills_root)
        report = catalog.verify_skill_accessibility()
        assert isinstance(report, dict)

    def test_verify_skill_accessibility_has_timestamp(self, skills_root: Path) -> None:
        """Test that accessibility report has timestamp."""
        catalog = SkillCatalog(skills_root)
        report = catalog.verify_skill_accessibility()
        assert "timestamp" in report

    def test_verify_skill_accessibility_has_stats(self, skills_root: Path) -> None:
        """Test that accessibility report has statistics."""
        catalog = SkillCatalog(skills_root)
        report = catalog.verify_skill_accessibility()
        assert "total_skills" in report
        assert "accessible_skills" in report
        assert "tests_passed" in report
        assert "accessibility_rate" in report
        assert "test_pass_rate" in report

    def test_verify_skill_accessibility_stats_valid(self, skills_root: Path) -> None:
        """Test that accessibility stats have valid values."""
        catalog = SkillCatalog(skills_root)
        report = catalog.verify_skill_accessibility()
        assert report["total_skills"] > 0
        assert 0 <= report["accessible_skills"] <= report["total_skills"]
        assert 0 <= report["accessibility_rate"] <= 1
        assert 0 <= report["test_pass_rate"] <= 1

    def test_verify_skill_accessibility_has_skills(self, skills_root: Path) -> None:
        """Test that accessibility report has skills list."""
        catalog = SkillCatalog(skills_root)
        report = catalog.verify_skill_accessibility()
        assert "skills" in report
        assert isinstance(report["skills"], list)

    def test_verify_skill_accessibility_skills_have_required_fields(
        self, skills_root: Path
    ) -> None:
        """Test that each skill in report has required fields."""
        catalog = SkillCatalog(skills_root)
        report = catalog.verify_skill_accessibility()
        for skill in report["skills"]:
            assert "name" in skill
            assert "render_result" in skill
            assert "invocation_test" in skill


class TestSkillCatalogReporting:
    """Test skill catalog reporting functionality."""

    def test_generate_accessibility_matrix_csv(self, skills_root: Path) -> None:
        """Test CSV matrix generation."""
        catalog = SkillCatalog(skills_root)
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "matrix.csv"
            catalog.generate_accessibility_matrix_csv(output_path)
            assert output_path.exists()
            # Verify CSV content
            with open(output_path) as f:
                content = f.read()
                assert "skill_name" in content
                assert len(content) > 0

    def test_generate_skill_catalog_report(self, skills_root: Path) -> None:
        """Test skill catalog report generation."""
        catalog = SkillCatalog(skills_root)
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.md"
            catalog.generate_skill_catalog_report(output_path)
            assert output_path.exists()
            # Verify report content
            with open(output_path) as f:
                content = f.read()
                assert "Skill Catalog Report" in content
                assert "Summary Statistics" in content

    def test_export_catalog_json(self, skills_root: Path) -> None:
        """Test JSON catalog export."""
        catalog = SkillCatalog(skills_root)
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "catalog.json"
            catalog.export_catalog_json(output_path)
            assert output_path.exists()
            # Verify JSON content
            with open(output_path) as f:
                data = json.load(f)
                assert isinstance(data, dict)
                assert len(data) > 0

    def test_generate_verification_summary(self, skills_root: Path) -> None:
        """Test verification summary generation."""
        catalog = SkillCatalog(skills_root)
        summary = catalog.generate_verification_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "SKILL ACCESSIBILITY VERIFICATION SUMMARY" in summary


class TestSkillCatalogIntegration:
    """Integration tests for skill catalog functionality."""

    def test_full_workflow(self, skills_root: Path) -> None:
        """Test full skill catalog workflow."""
        catalog = SkillCatalog(skills_root)

        # Discover and render
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Render all skills
            results = catalog.render_all_skills()
            assert len(results) > 0

            # Test invocations
            invocation_results = catalog.test_all_skills_invocation()
            assert len(invocation_results) > 0

            # Generate reports
            catalog.generate_accessibility_matrix_csv(tmpdir_path / "matrix.csv")
            catalog.generate_skill_catalog_report(tmpdir_path / "report.md")
            catalog.export_catalog_json(tmpdir_path / "catalog.json")

            # Verify all files were created
            assert (tmpdir_path / "matrix.csv").exists()
            assert (tmpdir_path / "report.md").exists()
            assert (tmpdir_path / "catalog.json").exists()

    def test_render_and_verify(self, skills_root: Path) -> None:
        """Test rendering followed by verification."""
        catalog = SkillCatalog(skills_root)

        # Render specific skill
        render_result = catalog.render_skill("agent-creator")
        assert render_result.success

        # Verify accessibility
        report = catalog.verify_skill_accessibility()
        assert report["total_skills"] > 0
        assert report["accessible_skills"] > 0
