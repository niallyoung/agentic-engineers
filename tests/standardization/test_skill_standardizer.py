"""
Unit tests for the skill standardization framework.

Tests:
- Template validation
- Frontmatter parsing and validation
- Document structure validation
- Compliance scoring
- Audit report generation
- Error handling and edge cases
"""

import pytest
from pathlib import Path
import tempfile
import yaml
from src.standardization import (
    SkillStandardizer,
    SkillStandardTemplate,
    SkillAuditResult,
    ComplianceIssue,
    ComplianceLevel,
)


@pytest.fixture
def temp_skill_dir():
    """Create a temporary skill directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def valid_skill_content():
    """Valid SKILL.md content."""
    return """---
name: test-skill
description: This is a test skill that demonstrates the standard format.
license: Proprietary
compatibility: agentic-engineers framework
metadata:
  author: agentic-engineers
  version: "1.0"
  category: testing
  role: engineer
---

## Overview

This is a comprehensive test skill that shows the expected structure and content format.

## Invocation

```bash
python scripts/test-skill.py --help
```
"""


@pytest.fixture
def minimal_skill_content():
    """Minimal SKILL.md content."""
    return """---
name: minimal-skill
description: Minimal test skill.
---

## Overview

Basic overview.

## Invocation

Basic invocation.
"""


@pytest.fixture
def invalid_frontmatter_content():
    """SKILL.md with invalid frontmatter."""
    return """---
name: invalid-skill
description: Invalid test skill
  extra: indentation

## Overview

This has malformed YAML.
"""


class TestSkillNameValidation:
    """Tests for skill name validation."""

    def test_valid_skill_names(self):
        """Test validation of valid skill names."""
        valid_names = [
            "test-skill",
            "ab-testing",
            "skill123",
            "tokenadvisor",
            "my-test-skill-123",
        ]

        for name in valid_names:
            is_valid, error = SkillStandardTemplate.validate_skill_name(name)
            assert is_valid, f"Expected '{name}' to be valid: {error}"

    def test_invalid_skill_names(self):
        """Test validation of invalid skill names."""
        invalid_names = [
            "",  # Empty
            "SkillName",  # Uppercase
            "-skill",  # Leading hyphen
            "skill-",  # Trailing hyphen
            "skill--name",  # Consecutive hyphens
            "a" * 65,  # Too long
            "skill name",  # Space
            "skill_name",  # Underscore
        ]

        for name in invalid_names:
            is_valid, error = SkillStandardTemplate.validate_skill_name(name)
            assert not is_valid, f"Expected '{name}' to be invalid"
            assert error is not None

    def test_empty_skill_name(self):
        """Test validation of empty skill name."""
        is_valid, error = SkillStandardTemplate.validate_skill_name("")
        assert not is_valid
        assert "cannot be empty" in error


class TestDescriptionValidation:
    """Tests for description field validation."""

    def test_valid_descriptions(self):
        """Test validation of valid descriptions."""
        valid_descriptions = [
            "Short but adequate description of skill",
            "A" * 1024,  # Max length
            "This is a medium-length description that explains what the skill does",
        ]

        for desc in valid_descriptions:
            is_valid, error = SkillStandardTemplate.validate_description(desc)
            assert is_valid, f"Expected description to be valid: {error}"

    def test_invalid_descriptions(self):
        """Test validation of invalid descriptions."""
        invalid_descriptions = [
            "",  # Empty
            "Short",  # Too short
            "A" * 1025,  # Too long
        ]

        for desc in invalid_descriptions:
            is_valid, error = SkillStandardTemplate.validate_description(desc)
            assert not is_valid, f"Expected '{desc[:50]}...' to be invalid"
            assert error is not None


class TestFrontmatterParsing:
    """Tests for YAML frontmatter parsing."""

    def test_parse_valid_frontmatter(self, valid_skill_content):
        """Test parsing of valid frontmatter."""
        standardizer = SkillStandardizer()
        frontmatter, body = standardizer._parse_frontmatter(valid_skill_content)

        assert frontmatter is not None
        assert frontmatter["name"] == "test-skill"
        assert frontmatter["description"] is not None
        assert "Overview" in body

    def test_parse_invalid_frontmatter(self, invalid_frontmatter_content):
        """Test parsing of invalid YAML frontmatter."""
        standardizer = SkillStandardizer()
        frontmatter, body = standardizer._parse_frontmatter(invalid_frontmatter_content)

        # Should return None for invalid YAML
        assert frontmatter is None

    def test_parse_no_frontmatter(self):
        """Test parsing content without frontmatter."""
        content = "## Overview\n\nSome content"
        standardizer = SkillStandardizer()
        frontmatter, body = standardizer._parse_frontmatter(content)

        assert frontmatter is None
        assert body == content


class TestDocumentStructure:
    """Tests for document structure validation."""

    def test_extract_sections(self):
        """Test extraction of markdown sections."""
        content = """## Overview

This is the overview.

## Invocation

This is invocation.

## Configuration

This is configuration.
"""
        standardizer = SkillStandardizer()
        sections = standardizer._extract_sections(content)

        assert "Overview" in sections
        assert "Invocation" in sections
        assert "Configuration" in sections
        assert "overview" in sections["Overview"]

    def test_required_sections_present(self, temp_skill_dir):
        """Test detection of required sections."""
        skill_path = temp_skill_dir / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)

        content = """---
name: test-skill
description: Test skill
---

## Overview

Overview content here.

## Invocation

Invocation content here.
"""
        skill_path.write_text(content)

        standardizer = SkillStandardizer(temp_skill_dir)
        result = standardizer.audit_skill(skill_path)

        assert result.sections_present.get("Overview") is True
        assert result.sections_present.get("Invocation") is True

    def test_required_sections_missing(self, temp_skill_dir):
        """Test detection of missing required sections."""
        skill_path = temp_skill_dir / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)

        content = """---
name: test-skill
description: Test skill
---

## Overview

Overview content here.
"""
        skill_path.write_text(content)

        standardizer = SkillStandardizer(temp_skill_dir)
        result = standardizer.audit_skill(skill_path)

        assert result.sections_present.get("Overview") is True
        assert result.sections_present.get("Invocation") is False

        # Should have an issue for missing Invocation
        missing_issues = [i for i in result.issues if "Invocation" in i.message]
        assert len(missing_issues) > 0


class TestComplianceScoring:
    """Tests for compliance scoring."""

    def test_compliant_skill(self, temp_skill_dir, valid_skill_content):
        """Test scoring of compliant skill."""
        skill_path = temp_skill_dir / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text(valid_skill_content)

        standardizer = SkillStandardizer(temp_skill_dir)
        result = standardizer.audit_skill(skill_path)

        assert result.compliance_level == ComplianceLevel.COMPLIANT
        assert result.score >= 85

    def test_partial_skill(self, temp_skill_dir):
        """Test scoring of partially compliant skill."""
        skill_path = temp_skill_dir / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)

        content = """---
name: test-skill
description: Test skill description.
---

## Overview

Short overview.

## Invocation

Short invocation.
"""
        skill_path.write_text(content)

        standardizer = SkillStandardizer(temp_skill_dir)
        result = standardizer.audit_skill(skill_path)

        # Should have warnings but not critical issues
        assert result.compliance_level == ComplianceLevel.PARTIAL
        critical_issues = [i for i in result.issues if i.severity == "critical"]
        assert len(critical_issues) == 0

    def test_non_compliant_skill(self, temp_skill_dir):
        """Test scoring of non-compliant skill."""
        skill_path = temp_skill_dir / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)

        content = """---
invalid yaml:
  - foo:

## Overview

Overview
"""
        skill_path.write_text(content)

        standardizer = SkillStandardizer(temp_skill_dir)
        result = standardizer.audit_skill(skill_path)

        assert result.compliance_level == ComplianceLevel.NON_COMPLIANT
        critical_issues = [i for i in result.issues if i.severity == "critical"]
        assert len(critical_issues) > 0


class TestAuditReportGeneration:
    """Tests for audit report generation."""

    def test_single_skill_audit(self, temp_skill_dir, valid_skill_content):
        """Test auditing a single skill."""
        skill_path = temp_skill_dir / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text(valid_skill_content)

        standardizer = SkillStandardizer(temp_skill_dir)
        result = standardizer.audit_skill(skill_path)

        assert isinstance(result, SkillAuditResult)
        assert result.skill_name == "test-skill"
        assert result.frontmatter_valid is True
        assert result.score >= 0

    def test_audit_all_skills(self, temp_skill_dir, valid_skill_content, minimal_skill_content):
        """Test auditing multiple skills."""
        # Create multiple skills
        for i, content in enumerate([valid_skill_content, minimal_skill_content]):
            skill_path = temp_skill_dir / f"skill-{i}" / "SKILL.md"
            skill_path.parent.mkdir(parents=True)
            skill_path.write_text(content)

        standardizer = SkillStandardizer(temp_skill_dir)
        results = standardizer.audit_all_skills()

        assert len(results) == 2
        assert all(isinstance(r, SkillAuditResult) for r in results)

    def test_compliance_report_generation(self, temp_skill_dir, valid_skill_content):
        """Test comprehensive compliance report generation."""
        skill_path = temp_skill_dir / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text(valid_skill_content)

        standardizer = SkillStandardizer(temp_skill_dir)
        standardizer.audit_all_skills()
        report = standardizer.generate_compliance_report()

        assert report["total_skills"] == 1
        assert "compliance_percentage" in report
        assert "average_score" in report
        assert "results" in report


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_missing_file(self, temp_skill_dir):
        """Test handling of missing SKILL.md file."""
        skill_path = temp_skill_dir / "nonexistent" / "SKILL.md"

        standardizer = SkillStandardizer(temp_skill_dir)
        result = standardizer.audit_skill(skill_path)

        assert result.compliance_level == ComplianceLevel.NON_COMPLIANT
        assert any(i.issue_type == "FILE_NOT_FOUND" for i in result.issues)

    def test_unreadable_file(self, temp_skill_dir):
        """Test handling of unreadable file."""
        skill_path = temp_skill_dir / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("test content")

        # Make file unreadable (this may not work on all systems)
        skill_path.chmod(0o000)

        try:
            standardizer = SkillStandardizer(temp_skill_dir)
            result = standardizer.audit_skill(skill_path)

            # Should handle the error gracefully
            assert result.compliance_level == ComplianceLevel.NON_COMPLIANT
        finally:
            # Restore permissions for cleanup
            skill_path.chmod(0o644)

    def test_empty_file(self, temp_skill_dir):
        """Test handling of empty SKILL.md file."""
        skill_path = temp_skill_dir / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("")

        standardizer = SkillStandardizer(temp_skill_dir)
        result = standardizer.audit_skill(skill_path)

        assert result.compliance_level == ComplianceLevel.NON_COMPLIANT
