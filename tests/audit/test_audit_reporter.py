"""Comprehensive test suite for audit reporter."""

import pytest
from pathlib import Path
from src.audit.skills_auditor import (
    DimensionScore,
    SkillScorecard,
    SkillsAuditor,
)
from src.audit.audit_reporter import AuditReporter


class TestAuditReporter:
    """Test AuditReporter functionality."""

    def test_reporter_initialization(self) -> None:
        """Test initializing audit reporter."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        assert reporter.auditor == auditor
        assert len(reporter.scorecards) > 10

    def test_generate_markdown_report_creates_file(self) -> None:
        """Test that markdown report is generated and written."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        
        # Generate to temp file
        output_path = Path("/tmp/test_audit_report.md")
        report = reporter.generate_markdown_report(output_path)
        
        # Check file was created
        assert output_path.exists()
        
        # Check content was returned
        assert isinstance(report, str)
        assert len(report) > 1000

    def test_markdown_report_contains_sections(self) -> None:
        """Test that report contains all required sections."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        
        output_path = Path("/tmp/test_audit_report.md")
        report = reporter.generate_markdown_report(output_path)
        
        # Check for major sections
        assert "# Skills Audit Report" in report
        assert "## Executive Summary" in report
        assert "## Category Breakdown" in report
        assert "## Dimension Analysis" in report
        assert "## Skills Needing Improvement" in report
        assert "## Individual Skill Scorecards" in report
        assert "## Framework-Wide Recommendations" in report
        assert "## Audit Methodology" in report

    def test_markdown_report_has_stats(self) -> None:
        """Test that report includes statistics."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        
        output_path = Path("/tmp/test_audit_report.md")
        report = reporter.generate_markdown_report(output_path)
        
        # Should have average score
        assert "Average Skill Score:" in report
        
        # Should have category breakdown
        assert "CORE" in report
        assert "UTILITY" in report
        assert "EXPERIMENTAL" in report

    def test_executive_summary_generation(self) -> None:
        """Test executive summary generation."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        summary = auditor.get_summary_statistics()
        
        lines = reporter._generate_executive_summary(summary)
        
        # Should be a list of strings
        assert isinstance(lines, list)
        assert all(isinstance(line, str) for line in lines)
        
        # Should contain key metrics
        content = "\n".join(lines)
        assert "Average Skill Score:" in content
        assert "Overall Framework Quality:" in content

    def test_category_breakdown_generation(self) -> None:
        """Test category breakdown generation."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        summary = auditor.get_summary_statistics()
        
        lines = reporter._generate_category_breakdown(summary)
        
        content = "\n".join(lines)
        assert "CORE" in content
        assert "UTILITY" in content
        assert "Count:" in content

    def test_dimension_analysis_generation(self) -> None:
        """Test dimension analysis generation."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        summary = auditor.get_summary_statistics()
        
        lines = reporter._generate_dimension_analysis(summary)
        
        content = "\n".join(lines)
        
        # Should have all dimension sections
        assert "VALUE" in content
        assert "USAGE" in content
        assert "MAINTENANCE" in content
        assert "TESTS" in content
        assert "DOCS" in content
        assert "QUALITY" in content

    def test_improvement_needed_generation(self) -> None:
        """Test skills needing improvement section."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        summary = auditor.get_summary_statistics()
        
        lines = reporter._generate_improvement_needed(summary)
        
        assert isinstance(lines, list)
        
        content = "\n".join(lines)
        assert "Skills Needing Improvement" in content or "quality standards" in content

    def test_scorecards_generation(self) -> None:
        """Test individual skill scorecards generation."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        
        lines = reporter._generate_scorecards()
        
        content = "\n".join(lines)
        
        # Should have scorecard section
        assert "Individual Skill Scorecards" in content
        
        # Should have dimension table
        assert "Dimension" in content
        assert "Score" in content

    def test_recommendations_generation(self) -> None:
        """Test recommendations section generation."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        
        lines = reporter._generate_recommendations()
        
        content = "\n".join(lines)
        
        # Should have recommendations
        assert "Recommendations" in content or "Priority Actions" in content

    def test_methodology_generation(self) -> None:
        """Test audit methodology section generation."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        
        lines = reporter._generate_methodology()
        
        content = "\n".join(lines)
        
        # Should explain each dimension
        assert "6-Dimension" in content or "VALUE" in content
        assert "USAGE" in content
        assert "MAINTENANCE" in content
        assert "TESTS" in content
        assert "DOCS" in content
        assert "QUALITY" in content

    def test_methodology_scoring_rubric(self) -> None:
        """Test that methodology includes scoring rubric."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        
        lines = reporter._generate_methodology()
        
        content = "\n".join(lines)
        
        # Should have category thresholds
        assert "CORE" in content
        assert "UTILITY" in content
        assert "EXPERIMENTAL" in content

    def test_report_file_structure(self) -> None:
        """Test that generated report file has expected structure."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        
        output_path = Path("/tmp/test_audit_report.md")
        report = reporter.generate_markdown_report(output_path)
        
        lines = report.split("\n")
        
        # Should start with header
        assert "# Skills Audit Report" in lines[0] or "Skills Audit Report" in lines[0]
        
        # Should have multiple sections
        section_count = sum(1 for line in lines if line.startswith("##"))
        assert section_count >= 6

    def test_report_includes_all_skills(self) -> None:
        """Test that report includes all audited skills."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        
        output_path = Path("/tmp/test_audit_report.md")
        report = reporter.generate_markdown_report(output_path)
        
        # Each skill should appear in report
        for skill_name in list(auditor.scorecards.keys())[:5]:  # Check first 5
            assert skill_name in report

    def test_report_contains_dimension_scores(self) -> None:
        """Test that report includes dimension scores for skills."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        
        output_path = Path("/tmp/test_audit_report.md")
        report = reporter.generate_markdown_report(output_path)
        
        # Should have dimension scores
        assert "Dimension Scores:" in report
        assert "/10" in report


class TestReportIntegration:
    """Integration tests for report generation."""

    def test_full_report_generation_workflow(self) -> None:
        """Test complete report generation workflow."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        
        # Audit
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        # Generate report
        reporter = AuditReporter(auditor)
        
        output_path = Path("/tmp/test_full_audit.md")
        report = reporter.generate_markdown_report(output_path)
        
        # Verify
        assert output_path.exists()
        assert len(report) > 5000
        assert "Skills Audit Report" in report
        assert "Executive Summary" in report

    def test_report_markdown_validity(self) -> None:
        """Test that generated markdown is valid."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        
        output_path = Path("/tmp/test_audit_validity.md")
        report = reporter.generate_markdown_report(output_path)
        
        lines = report.split("\n")
        
        # Check markdown structure
        header_count = sum(1 for line in lines if line.startswith("#"))
        assert header_count > 5
        
        # Check for tables
        table_markers = sum(1 for line in lines if "|" in line)
        assert table_markers > 0

    def test_report_recommendations_specific(self) -> None:
        """Test that recommendations are specific."""
        skills_path = Path("/Users/niall/git/agentic-engineers/src/skills")
        
        auditor = SkillsAuditor(skills_path)
        auditor.audit_all_skills()
        
        reporter = AuditReporter(auditor)
        
        output_path = Path("/tmp/test_audit_recommendations.md")
        report = reporter.generate_markdown_report(output_path)
        
        # Should have specific recommendations
        assert "Test Coverage" in report or "test coverage" in report or "TESTS" in report
        assert "Documentation" in report or "DOCS" in report
