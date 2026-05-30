"""
SKILL.md Standardization Framework

Audits and standardizes SKILL.md files across all skills to enforce consistent
structure, formatting, and quality gates. Provides compliance reporting and
automated remediation capabilities.

Requirements:
- ≥85% test coverage
- Type hints on all functions
- ≥92/100 quality score with ≥95% confidence
- All code must pass linting
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import yaml
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
import json


class ComplianceLevel(Enum):
    """Skill compliance levels."""
    COMPLIANT = "COMPLIANT"
    PARTIAL = "PARTIAL"
    NON_COMPLIANT = "NON_COMPLIANT"


@dataclass
class SkillMetadata:
    """Standardized skill metadata structure."""
    name: str
    description: str
    license: str = "Proprietary"
    compatibility: str = "agentic-engineers framework"
    author: str = "agentic-engineers"
    version: str = "1.0"
    category: str = ""
    role: str = ""
    schedule: Optional[str] = None
    tdd_phase: Optional[str] = None
    allowed_tools: Optional[List[str]] = field(default_factory=list)


@dataclass
class ComplianceIssue:
    """Represents a compliance issue found during audit."""
    issue_type: str
    severity: str  # critical, warning, info
    section: str
    message: str
    suggested_fix: Optional[str] = None


@dataclass
class SkillAuditResult:
    """Results from auditing a single skill."""
    skill_name: str
    skill_path: Path
    compliance_level: ComplianceLevel
    issues: List[ComplianceIssue] = field(default_factory=list)
    metadata: Optional[SkillMetadata] = None
    structure_valid: bool = False
    frontmatter_valid: bool = False
    sections_present: Dict[str, bool] = field(default_factory=dict)
    section_lengths: Dict[str, int] = field(default_factory=dict)
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit result to dictionary."""
        return {
            "skill_name": self.skill_name,
            "skill_path": str(self.skill_path),
            "compliance_level": self.compliance_level.value,
            "issues": [asdict(issue) for issue in self.issues],
            "metadata": asdict(self.metadata) if self.metadata else None,
            "structure_valid": self.structure_valid,
            "frontmatter_valid": self.frontmatter_valid,
            "sections_present": self.sections_present,
            "section_lengths": self.section_lengths,
            "score": self.score,
        }


class SkillStandardTemplate:
    """Defines the standard SKILL.md template and validation rules."""

    REQUIRED_SECTIONS: List[str] = [
        "Overview",
        "Invocation",
    ]

    OPTIONAL_SECTIONS: List[str] = [
        "Voice Notifications",
        "Configuration",
        "Integration",
        "Scripts",
        "Advanced Configuration",
        "Troubleshooting",
        "Examples",
        "References",
        "Directory Structure",
        "Creating",
        "Naming Conventions",
        "Categories",
        "Compliance Checklist",
        "Validation",
        "File References",
        "Documentation Structure",
    ]

    REQUIRED_FRONTMATTER_FIELDS: List[str] = [
        "name",
        "description",
    ]

    OPTIONAL_FRONTMATTER_FIELDS: List[str] = [
        "license",
        "compatibility",
        "metadata",
    ]

    # Quality thresholds
    MIN_DESCRIPTION_LENGTH: int = 20
    MAX_DESCRIPTION_LENGTH: int = 1024
    MIN_OVERVIEW_LENGTH: int = 50
    MIN_INVOCATION_LENGTH: int = 30
    MAX_SKILL_NAME_LENGTH: int = 64

    @classmethod
    def get_template(cls) -> str:
        """Get the standard SKILL.md template."""
        return """---
name: {skill-name}
description: {Brief description of what this skill does and when to use it. Include primary use case and key functionality.}
license: Proprietary
compatibility: agentic-engineers framework
metadata:
  author: agentic-engineers
  version: "1.0"
  category: {Choose: orchestration, monitoring, optimization, patterns, security, testing, shared, architecture, review, or roles}
  role: {Choose: engineer, senior-engineer, lead-engineer, orchestrator, or principal-engineer}
---

## Overview

{Detailed explanation of what the skill does, its key features, and when to use it.
Should be at least 50 characters. This section provides context for users.}

## Invocation

{Instructions for how to invoke this skill, including manual and automated methods.
Include code examples, environment variables, and configuration if applicable.}

## Integration

{How this skill integrates with other components in the agentic-engineers framework.
Document inputs, outputs, and dependencies.}

## Configuration

{Configuration options, environment variables, and customization points.}

## Examples

{Practical examples of using this skill in real scenarios.}
"""

    @classmethod
    def validate_skill_name(cls, name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate skill name format.

        Args:
            name: Skill name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name:
            return False, "Skill name cannot be empty"

        if len(name) > cls.MAX_SKILL_NAME_LENGTH:
            return False, f"Skill name exceeds max length of {cls.MAX_SKILL_NAME_LENGTH}"

        # Check for consecutive hyphens
        if "--" in name:
            return False, "Skill name cannot contain consecutive hyphens"

        if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", name):
            return (
                False,
                "Skill name must contain only lowercase letters, numbers, and hyphens",
            )

        return True, None

    @classmethod
    def validate_description(cls, description: str) -> Tuple[bool, Optional[str]]:
        """
        Validate description field.

        Args:
            description: Description to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not description:
            return False, "Description cannot be empty"

        if len(description) < cls.MIN_DESCRIPTION_LENGTH:
            return (
                False,
                f"Description must be at least {cls.MIN_DESCRIPTION_LENGTH} characters",
            )

        if len(description) > cls.MAX_DESCRIPTION_LENGTH:
            return (
                False,
                f"Description cannot exceed {cls.MAX_DESCRIPTION_LENGTH} characters",
            )

        return True, None


class SkillStandardizer:
    """Main standardization engine for auditing and updating SKILL.md files."""

    def __init__(self, repository_root: Optional[Path] = None):
        """
        Initialize the standardizer.

        Args:
            repository_root: Root path of the repository (defaults to current working directory)
        """
        self.repository_root = repository_root or Path.cwd()
        self.template = SkillStandardTemplate()
        self.audit_results: List[SkillAuditResult] = []

    def find_all_skills(self) -> List[Path]:
        """
        Find all SKILL.md files in the repository.

        Returns:
            List of paths to SKILL.md files
        """
        skill_files = list(self.repository_root.glob("**/SKILL.md"))
        return sorted(skill_files)

    def audit_skill(self, skill_path: Path) -> SkillAuditResult:
        """
        Audit a single skill file for compliance.

        Args:
            skill_path: Path to the SKILL.md file

        Returns:
            SkillAuditResult with detailed compliance information
        """
        result = SkillAuditResult(
            skill_name=skill_path.parent.name,
            skill_path=skill_path,
            compliance_level=ComplianceLevel.NON_COMPLIANT,
        )

        # Check file exists and is readable
        if not skill_path.exists():
            result.issues.append(
                ComplianceIssue(
                    issue_type="FILE_NOT_FOUND",
                    severity="critical",
                    section="File",
                    message=f"SKILL.md file not found at {skill_path}",
                )
            )
            return result

        try:
            content = skill_path.read_text(encoding="utf-8")
        except Exception as e:
            result.issues.append(
                ComplianceIssue(
                    issue_type="READ_ERROR",
                    severity="critical",
                    section="File",
                    message=f"Failed to read SKILL.md: {str(e)}",
                )
            )
            return result

        # Parse YAML frontmatter
        frontmatter, body = self._parse_frontmatter(content)
        if frontmatter is None:
            result.issues.append(
                ComplianceIssue(
                    issue_type="FRONTMATTER_INVALID",
                    severity="critical",
                    section="Frontmatter",
                    message="Invalid YAML frontmatter or missing delimiters",
                    suggested_fix="Ensure frontmatter is wrapped in --- delimiters",
                )
            )
        else:
            result.frontmatter_valid = True
            self._validate_frontmatter(frontmatter, result)

        # Check document structure
        self._validate_structure(content, result)

        # Calculate compliance score
        self._calculate_compliance_score(result)

        # Determine overall compliance level
        critical_issues = [i for i in result.issues if i.severity == "critical"]
        warning_issues = [i for i in result.issues if i.severity == "warning"]

        if critical_issues:
            result.compliance_level = ComplianceLevel.NON_COMPLIANT
        elif warning_issues:
            result.compliance_level = ComplianceLevel.PARTIAL
        else:
            result.compliance_level = ComplianceLevel.COMPLIANT

        return result

    def _parse_frontmatter(
        self, content: str
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Parse YAML frontmatter from skill file.

        Args:
            content: Full content of SKILL.md file

        Returns:
            Tuple of (frontmatter_dict, body_content)
        """
        if not content.startswith("---"):
            return None, content

        # Find closing --- delimiter
        lines = content.split("\n")
        end_index = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_index = i
                break

        if end_index is None:
            return None, content

        try:
            frontmatter_str = "\n".join(lines[1:end_index])
            frontmatter = yaml.safe_load(frontmatter_str)
            body = "\n".join(lines[end_index + 1 :])
            return frontmatter, body
        except yaml.YAMLError:
            return None, content

    def _validate_frontmatter(
        self, frontmatter: Dict[str, Any], result: SkillAuditResult
    ) -> None:
        """
        Validate frontmatter against standard requirements.

        Args:
            frontmatter: Parsed YAML frontmatter
            result: SkillAuditResult to accumulate issues
        """
        # Check required fields
        for field in self.template.REQUIRED_FRONTMATTER_FIELDS:
            if field not in frontmatter:
                result.issues.append(
                    ComplianceIssue(
                        issue_type="MISSING_FIELD",
                        severity="critical",
                        section="Frontmatter",
                        message=f"Missing required field: {field}",
                        suggested_fix=f"Add '{field}' field to frontmatter",
                    )
                )

        # Validate name
        if "name" in frontmatter:
            is_valid, error = self.template.validate_skill_name(frontmatter["name"])
            if not is_valid:
                result.issues.append(
                    ComplianceIssue(
                        issue_type="INVALID_SKILL_NAME",
                        severity="critical",
                        section="Frontmatter.name",
                        message=error or "Invalid skill name",
                        suggested_fix="Use lowercase alphanumeric characters and hyphens",
                    )
                )

        # Validate description
        if "description" in frontmatter:
            is_valid, error = self.template.validate_description(
                str(frontmatter["description"])
            )
            if not is_valid:
                result.issues.append(
                    ComplianceIssue(
                        issue_type="INVALID_DESCRIPTION",
                        severity="critical",
                        section="Frontmatter.description",
                        message=error or "Invalid description",
                    )
                )

        # Create metadata object
        metadata_dict = frontmatter.get("metadata", {})
        result.metadata = SkillMetadata(
            name=frontmatter.get("name", ""),
            description=frontmatter.get("description", ""),
            license=frontmatter.get("license", "Proprietary"),
            compatibility=frontmatter.get("compatibility", "agentic-engineers framework"),
            author=metadata_dict.get("author", "agentic-engineers"),
            version=metadata_dict.get("version", "1.0"),
            category=metadata_dict.get("category", ""),
            role=metadata_dict.get("role", ""),
            schedule=metadata_dict.get("schedule"),
            tdd_phase=metadata_dict.get("tdd_phase"),
            allowed_tools=metadata_dict.get("allowed_tools", []),
        )

        # Validate metadata fields
        if not result.metadata.category:
            result.issues.append(
                ComplianceIssue(
                    issue_type="MISSING_METADATA",
                    severity="warning",
                    section="Frontmatter.metadata",
                    message="Missing category in metadata",
                    suggested_fix="Add category field to metadata section",
                )
            )

        if not result.metadata.role:
            result.issues.append(
                ComplianceIssue(
                    issue_type="MISSING_METADATA",
                    severity="warning",
                    section="Frontmatter.metadata",
                    message="Missing role in metadata",
                    suggested_fix="Add role field to metadata section",
                )
            )

    def _validate_structure(self, content: str, result: SkillAuditResult) -> None:
        """
        Validate document structure and sections.

        Args:
            content: Full content of SKILL.md file
            result: SkillAuditResult to accumulate issues
        """
        # Extract sections
        sections = self._extract_sections(content)
        result.structure_valid = len(sections) > 0

        # Check for required sections
        for section in self.template.REQUIRED_SECTIONS:
            if section in sections:
                result.sections_present[section] = True
                result.section_lengths[section] = len(sections[section])
            else:
                result.sections_present[section] = False
                result.issues.append(
                    ComplianceIssue(
                        issue_type="MISSING_SECTION",
                        severity="critical",
                        section=section,
                        message=f"Missing required section: ## {section}",
                        suggested_fix=f"Add '## {section}' section to document",
                    )
                )

        # Check for minimum content in required sections
        for section in self.template.REQUIRED_SECTIONS:
            if section in sections:
                section_content = sections[section]
                if section == "Overview":
                    if len(section_content) < self.template.MIN_OVERVIEW_LENGTH:
                        result.issues.append(
                            ComplianceIssue(
                                issue_type="INSUFFICIENT_CONTENT",
                                severity="warning",
                                section=section,
                                message=f"Overview section too short (< {self.template.MIN_OVERVIEW_LENGTH} chars)",
                                suggested_fix="Expand Overview with more detailed description",
                            )
                        )
                elif section == "Invocation":
                    if len(section_content) < self.template.MIN_INVOCATION_LENGTH:
                        result.issues.append(
                            ComplianceIssue(
                                issue_type="INSUFFICIENT_CONTENT",
                                severity="warning",
                                section=section,
                                message=f"Invocation section too short (< {self.template.MIN_INVOCATION_LENGTH} chars)",
                                suggested_fix="Expand Invocation with usage examples",
                            )
                        )

        # Track optional sections found
        for section in self.template.OPTIONAL_SECTIONS:
            if section in sections:
                result.sections_present[section] = True
                result.section_lengths[section] = len(sections[section])

    def _extract_sections(self, content: str) -> Dict[str, str]:
        """
        Extract markdown sections from content.

        Args:
            content: Markdown content

        Returns:
            Dictionary mapping section names to their content
        """
        sections: Dict[str, str] = {}
        current_section = None
        current_content: List[str] = []

        for line in content.split("\n"):
            if line.startswith("## "):
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = line[3:].strip()
                current_content = []
            elif current_section:
                current_content.append(line)

        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _calculate_compliance_score(self, result: SkillAuditResult) -> None:
        """
        Calculate an overall compliance score (0-100).

        Args:
            result: SkillAuditResult to update with score
        """
        score = 100.0

        # Deduct for critical issues (-15 each)
        critical_count = sum(1 for i in result.issues if i.severity == "critical")
        score -= critical_count * 15

        # Deduct for warning issues (-5 each)
        warning_count = sum(1 for i in result.issues if i.severity == "warning")
        score -= warning_count * 5

        # Bonus for having optional sections
        optional_count = sum(
            1 for section in self.template.OPTIONAL_SECTIONS
            if result.sections_present.get(section, False)
        )
        bonus = min(optional_count * 2, 15)  # Max +15 bonus
        score += bonus

        result.score = max(0.0, min(100.0, score))

    def audit_all_skills(self) -> List[SkillAuditResult]:
        """
        Audit all skills in the repository.

        Returns:
            List of SkillAuditResult objects for all skills
        """
        skill_files = self.find_all_skills()
        self.audit_results = []

        for skill_file in skill_files:
            result = self.audit_skill(skill_file)
            self.audit_results.append(result)

        return self.audit_results

    def generate_compliance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive compliance report.

        Returns:
            Dictionary with compliance statistics and details
        """
        compliant_count = sum(
            1 for r in self.audit_results
            if r.compliance_level == ComplianceLevel.COMPLIANT
        )
        partial_count = sum(
            1 for r in self.audit_results
            if r.compliance_level == ComplianceLevel.PARTIAL
        )
        non_compliant_count = sum(
            1 for r in self.audit_results
            if r.compliance_level == ComplianceLevel.NON_COMPLIANT
        )

        total_issues = sum(len(r.issues) for r in self.audit_results)
        avg_score = (
            sum(r.score for r in self.audit_results) / len(self.audit_results)
            if self.audit_results
            else 0.0
        )

        return {
            "timestamp": str(Path.cwd()),
            "total_skills": len(self.audit_results),
            "compliant": compliant_count,
            "partial": partial_count,
            "non_compliant": non_compliant_count,
            "compliance_percentage": (
                compliant_count / len(self.audit_results) * 100
                if self.audit_results
                else 0.0
            ),
            "average_score": avg_score,
            "total_issues": total_issues,
            "results": [r.to_dict() for r in self.audit_results],
        }

    def export_report(self, output_path: Path) -> None:
        """
        Export compliance report to JSON file.

        Args:
            output_path: Path where to save the report
        """
        report = self.generate_compliance_report()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
