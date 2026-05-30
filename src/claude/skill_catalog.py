"""
Skill catalog and rendering system for Claude Code harness.

This module provides functionality to load, render, and test skill accessibility
across the agentic-engineers framework.
"""

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, TextIO
from datetime import datetime

from .skill_manager import SkillManager, SkillMetadata, SkillAccessibilityStatus


@dataclass
class SkillRenderResult:
    """Result of rendering a skill."""

    skill_name: str
    success: bool
    metadata: Optional[SkillMetadata] = None
    error: Optional[str] = None
    render_time_ms: float = 0.0


class SkillCatalog:
    """Manages skill catalog rendering and accessibility testing."""

    def __init__(self, skills_root: Optional[Path] = None) -> None:
        """
        Initialize skill catalog.

        Args:
            skills_root: Root directory containing skills
        """
        self.skill_manager = SkillManager(skills_root)
        self.skills_root = self.skill_manager.skills_root
        self._render_results: Dict[str, SkillRenderResult] = {}

    def render_skill(self, skill_name: str) -> SkillRenderResult:
        """
        Render a single skill and verify accessibility.

        Args:
            skill_name: Name of the skill to render

        Returns:
            SkillRenderResult with rendering status
        """
        import time

        start_time = time.time()

        try:
            # Load metadata
            metadata = self.skill_manager.load_skill_metadata(skill_name)
            if not metadata:
                return SkillRenderResult(
                    skill_name=skill_name,
                    success=False,
                    error="Failed to load metadata",
                    render_time_ms=(time.time() - start_time) * 1000,
                )

            # Validate metadata
            status = self.skill_manager.validate_skill_metadata(skill_name)
            if not status.is_accessible:
                error_msg = (
                    "; ".join(status.errors) if status.errors else "Unknown error"
                )
                return SkillRenderResult(
                    skill_name=skill_name,
                    success=False,
                    metadata=metadata,
                    error=error_msg,
                    render_time_ms=(time.time() - start_time) * 1000,
                )

            result = SkillRenderResult(
                skill_name=skill_name,
                success=True,
                metadata=metadata,
                render_time_ms=(time.time() - start_time) * 1000,
            )

            self._render_results[skill_name] = result
            return result

        except Exception as e:
            return SkillRenderResult(
                skill_name=skill_name,
                success=False,
                error=f"Exception: {str(e)}",
                render_time_ms=(time.time() - start_time) * 1000,
            )

    def render_all_skills(self) -> Dict[str, SkillRenderResult]:
        """
        Render all available skills.

        Returns:
            Dictionary mapping skill names to SkillRenderResult
        """
        results = {}
        for skill_name in self.skill_manager.discover_skills():
            results[skill_name] = self.render_skill(skill_name)

        self._render_results = results
        return results

    def test_skill_invocation(self, skill_name: str) -> Dict[str, Any]:
        """
        Test end-to-end skill invocation capability.

        Args:
            skill_name: Name of the skill to test

        Returns:
            Dictionary with test results
        """
        result = {
            "skill_name": skill_name,
            "test_passed": False,
            "checks": {},
            "errors": [],
        }

        # Check 1: File exists
        skill_path = self.skills_root / skill_name
        result["checks"]["directory_exists"] = skill_path.exists()

        # Check 2: SKILL.md exists
        skill_md = skill_path / "SKILL.md"
        result["checks"]["skill_md_exists"] = skill_md.exists()

        # Check 3: Metadata loads
        metadata = self.skill_manager.load_skill_metadata(skill_name)
        result["checks"]["metadata_loads"] = metadata is not None

        # Check 4: Metadata valid
        status = self.skill_manager.validate_skill_metadata(skill_name)
        result["checks"]["metadata_valid"] = status.is_accessible
        if status.errors:
            result["errors"].extend(status.errors)

        # Check 5: Has required fields
        if metadata:
            required_fields = ["name", "description"]
            missing = [f for f in required_fields if not getattr(metadata, f, None)]
            result["checks"]["required_fields_present"] = len(missing) == 0
            if missing:
                result["errors"].append(f"Missing fields: {missing}")

        # Overall result
        result["test_passed"] = all(result["checks"].values())
        return result

    def test_all_skills_invocation(self) -> Dict[str, Dict[str, Any]]:
        """
        Test invocation capability for all skills.

        Returns:
            Dictionary mapping skill names to test results
        """
        results = {}
        for skill_name in self.skill_manager.discover_skills():
            results[skill_name] = self.test_skill_invocation(skill_name)

        return results

    def verify_skill_accessibility(self) -> Dict[str, Any]:
        """
        Verify accessibility of all skills.

        Returns:
            Comprehensive accessibility report
        """
        skills = self.skill_manager.discover_skills()
        render_results = self.render_all_skills()
        invocation_results = self.test_all_skills_invocation()

        accessible_count = sum(1 for r in render_results.values() if r.success)
        tests_passed = sum(1 for r in invocation_results.values() if r["test_passed"])

        return {
            "timestamp": datetime.now().isoformat(),
            "total_skills": len(skills),
            "accessible_skills": accessible_count,
            "tests_passed": tests_passed,
            "accessibility_rate": accessible_count / len(skills) if skills else 0,
            "test_pass_rate": tests_passed / len(skills) if skills else 0,
            "skills": [
                {
                    "name": skill_name,
                    "render_result": {
                        "success": render_results[skill_name].success,
                        "error": render_results[skill_name].error,
                        "render_time_ms": render_results[skill_name].render_time_ms,
                    },
                    "invocation_test": invocation_results[skill_name],
                }
                for skill_name in sorted(skills)
            ],
        }

    def generate_accessibility_matrix_csv(self, output_path: Path) -> None:
        """
        Generate accessibility matrix as CSV file.

        Args:
            output_path: Path to write CSV file
        """
        matrix = self.skill_manager.generate_accessibility_matrix()

        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=matrix[0].keys() if matrix else [])
            writer.writeheader()
            writer.writerows(matrix)

    def generate_skill_catalog_report(self, output_path: Path) -> None:
        """
        Generate comprehensive skill catalog report.

        Args:
            output_path: Path to write report file
        """
        report_lines = []
        report_lines.append("# Skill Catalog Report")
        report_lines.append(f"\nGenerated: {datetime.now().isoformat()}")

        # Summary statistics
        stats = self.skill_manager.get_accessibility_stats()
        report_lines.append("\n## Summary Statistics")
        report_lines.append(f"- Total Skills: {stats['total_skills']}")
        report_lines.append(f"- Accessible Skills: {stats['accessible_skills']}")
        report_lines.append(f"- Skills with Errors: {stats['skills_with_errors']}")
        report_lines.append(f"- Skills with Warnings: {stats['skills_with_warnings']}")
        report_lines.append(
            f"- Accessibility Rate: {stats['accessibility_percentage']:.1f}%"
        )

        # Skills by category
        report_lines.append("\n## Skills by Category")
        by_category = self.skill_manager.get_skills_by_category()
        for category, skills in by_category.items():
            report_lines.append(f"\n### {category.title()}")
            for skill in skills:
                report_lines.append(f"- {skill}")

        # Skills by model
        report_lines.append("\n## Skills by Model")
        by_model = self.skill_manager.get_skills_by_model()
        for model, skills in by_model.items():
            report_lines.append(f"\n### {model}")
            for skill in skills:
                report_lines.append(f"- {skill}")

        # Skills by effort
        report_lines.append("\n## Skills by Effort")
        by_effort = self.skill_manager.get_skills_by_effort()
        for effort in ["low", "medium", "high"]:
            if effort in by_effort:
                report_lines.append(f"\n### {effort.title()}")
                for skill in by_effort[effort]:
                    report_lines.append(f"- {skill}")

        # Accessibility matrix
        report_lines.append("\n## Accessibility Matrix")
        matrix = self.skill_manager.generate_accessibility_matrix()
        report_lines.append(
            "| Skill | Accessible | SKILL.md | Frontmatter | Metadata | Category | Version |"
        )
        report_lines.append(
            "|-------|-----------|----------|-------------|----------|----------|---------|"
        )
        for row in matrix:
            report_lines.append(
                f"| {row['skill_name']} | {'✓' if row['accessible'] else '✗'} | "
                f"{'✓' if row['skill_md_exists'] else '✗'} | "
                f"{'✓' if row['frontmatter_valid'] else '✗'} | "
                f"{'✓' if row['metadata_complete'] else '✗'} | "
                f"{row['category']} | {row['version']} |"
            )

        report_text = "\n".join(report_lines)
        with open(output_path, "w") as f:
            f.write(report_text)

    def export_catalog_json(self, output_path: Path) -> None:
        """
        Export full skill catalog as JSON.

        Args:
            output_path: Path to write JSON file
        """
        skills_data = {}
        for skill_name, metadata in self.skill_manager.get_all_skills_metadata().items():
            status = self.skill_manager.validate_skill_metadata(skill_name)
            skills_data[skill_name] = {
                "metadata": metadata.to_dict(),
                "accessibility": {
                    "is_accessible": status.is_accessible,
                    "errors": status.errors,
                    "warnings": status.warnings,
                },
            }

        with open(output_path, "w") as f:
            json.dump(skills_data, f, indent=2, default=str)

    def generate_verification_summary(self) -> str:
        """
        Generate a human-readable verification summary.

        Returns:
            Formatted verification summary string
        """
        report = self.verify_skill_accessibility()
        stats = self.skill_manager.get_accessibility_stats()

        lines = []
        lines.append("=" * 60)
        lines.append("SKILL ACCESSIBILITY VERIFICATION SUMMARY")
        lines.append("=" * 60)
        lines.append(f"Timestamp: {report['timestamp']}")
        lines.append("")
        lines.append(f"Total Skills: {report['total_skills']}")
        lines.append(f"Accessible: {report['accessible_skills']}/{report['total_skills']}")
        lines.append(f"Tests Passed: {report['tests_passed']}/{report['total_skills']}")
        lines.append(f"Accessibility Rate: {report['accessibility_rate']*100:.1f}%")
        lines.append(f"Test Pass Rate: {report['test_pass_rate']*100:.1f}%")
        lines.append("")

        # List failed skills
        failed = [
            s
            for s in report["skills"]
            if not s["render_result"]["success"]
            or not s["invocation_test"]["test_passed"]
        ]
        if failed:
            lines.append("FAILED SKILLS:")
            for skill_info in failed:
                lines.append(f"  - {skill_info['name']}")
                if skill_info["render_result"]["error"]:
                    lines.append(f"      Render Error: {skill_info['render_result']['error']}")
                if skill_info["invocation_test"]["errors"]:
                    for error in skill_info["invocation_test"]["errors"]:
                        lines.append(f"      Test Error: {error}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
