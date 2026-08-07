"""
Skill inventory and metadata management for Claude Code harness.

This module provides comprehensive skill discovery, validation, and metadata
management for the agentic-engineers framework.
"""

import os
import re
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import yaml


@dataclass
class SkillMetadata:
    """Encapsulates skill metadata from SKILL.md frontmatter."""

    name: str
    description: str
    license: Optional[str] = None
    compatibility: Optional[str] = None
    author: Optional[str] = None
    version: str = "1.0"
    category: str = "general"
    role: str = "engineer"
    model: str = "claude-haiku-4.5"
    effort: str = "low"
    thinking: bool = False
    path: Optional[Path] = None
    skill_md_path: Optional[Path] = None
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary, excluding Path objects."""
        d = asdict(self)
        d["path"] = str(d["path"]) if d["path"] else None
        d["skill_md_path"] = str(d["skill_md_path"]) if d["skill_md_path"] else None
        return d


@dataclass
class SkillAccessibilityStatus:
    """Status of skill accessibility checks."""

    name: str
    is_accessible: bool
    skill_md_exists: bool
    frontmatter_valid: bool
    metadata_complete: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SkillManager:
    """Manages skill discovery, validation, and metadata extraction."""

    def __init__(self, skills_root: Optional[Path] = None) -> None:
        """
        Initialize skill manager.

        Args:
            skills_root: Root directory containing skills. Defaults to ~/.claude/skills
        """
        if skills_root is None:
            skills_root = Path.home() / ".claude" / "skills"
        self.skills_root = skills_root
        self._skills_cache: Dict[str, SkillMetadata] = {}
        self._accessibility_cache: Dict[str, SkillAccessibilityStatus] = {}

    def discover_skills(self) -> List[str]:
        """
        Discover all available skills.

        Returns:
            List of skill names found in skills_root directory
        """
        if not self.skills_root.exists():
            return []

        skills = []
        for item in self.skills_root.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                skills.append(item.name)

        return sorted(skills)

    def load_skill_metadata(self, skill_name: str) -> Optional[SkillMetadata]:
        """
        Load and parse skill metadata from SKILL.md frontmatter.

        Args:
            skill_name: Name of the skill to load

        Returns:
            SkillMetadata if successful, None otherwise
        """
        if skill_name in self._skills_cache:
            return self._skills_cache[skill_name]

        skill_path = self.skills_root / skill_name
        skill_md = skill_path / "SKILL.md"

        if not skill_md.exists():
            return None

        try:
            with open(skill_md, "r") as f:
                content = f.read()

            # Extract YAML frontmatter
            frontmatter_match = re.match(
                r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL
            )
            if not frontmatter_match:
                return None

            frontmatter_str = frontmatter_match.group(1)
            metadata_dict = yaml.safe_load(frontmatter_str) or {}

            # Ensure required fields
            metadata_dict["path"] = skill_path
            metadata_dict["skill_md_path"] = skill_md
            metadata_dict.setdefault("name", skill_name)
            metadata_dict.setdefault("description", "")
            metadata_dict.setdefault("version", "1.0")
            metadata_dict.setdefault("category", "general")
            metadata_dict.setdefault("role", "engineer")
            metadata_dict.setdefault("model", "claude-haiku-4.5")
            metadata_dict.setdefault("effort", "low")
            metadata_dict.setdefault("thinking", False)

            # Extract nested metadata if it exists
            if "metadata" in metadata_dict:
                nested = metadata_dict.pop("metadata")
                for key, value in nested.items():
                    if key not in metadata_dict:
                        metadata_dict[key] = value

            # Extract known fields for SkillMetadata
            known_fields = {
                "name", "description", "license", "compatibility", "author",
                "version", "category", "role", "model", "effort", "thinking",
                "path", "skill_md_path"
            }
            extra_fields = {k: v for k, v in metadata_dict.items() if k not in known_fields}
            filtered_dict = {k: v for k, v in metadata_dict.items() if k in known_fields}
            filtered_dict["extra_fields"] = extra_fields

            metadata = SkillMetadata(**filtered_dict)
            self._skills_cache[skill_name] = metadata
            return metadata

        except Exception as e:
            # Log error but continue
            return None

    def validate_skill_metadata(self, skill_name: str) -> SkillAccessibilityStatus:
        """
        Validate skill metadata and accessibility.

        Args:
            skill_name: Name of the skill to validate

        Returns:
            SkillAccessibilityStatus with validation results
        """
        if skill_name in self._accessibility_cache:
            return self._accessibility_cache[skill_name]

        status = SkillAccessibilityStatus(
            name=skill_name,
            is_accessible=False,
            skill_md_exists=False,
            frontmatter_valid=False,
            metadata_complete=False,
        )

        skill_path = self.skills_root / skill_name
        skill_md = skill_path / "SKILL.md"

        # Check if skill_md exists
        if not skill_md.exists():
            status.errors.append(f"SKILL.md not found at {skill_md}")
            self._accessibility_cache[skill_name] = status
            return status

        status.skill_md_exists = True

        # Try to load metadata
        metadata = self.load_skill_metadata(skill_name)
        if metadata is None:
            status.errors.append("Failed to parse SKILL.md frontmatter")
            self._accessibility_cache[skill_name] = status
            return status

        status.frontmatter_valid = True

        # Check metadata completeness
        required_fields = ["name", "description", "version", "category"]
        missing_fields = []
        for field in required_fields:
            if not getattr(metadata, field, None):
                missing_fields.append(field)

        if missing_fields:
            status.metadata_complete = False
            status.warnings.append(f"Missing optional fields: {', '.join(missing_fields)}")
        else:
            status.metadata_complete = True

        # Check for additional validation issues
        valid_categories = [
            "general",
            "orchestration",
            "validation",
            "optimization",
            "monitoring",
            "integration",
        ]
        if metadata.category not in valid_categories:
            status.warnings.append(f"Category '{metadata.category}' is non-standard")

        valid_efforts = ["low", "medium", "high"]
        if metadata.effort and metadata.effort not in valid_efforts:
            status.errors.append(f"Invalid effort level: {metadata.effort}")
        
        # Skill is accessible if it has SKILL.md and valid frontmatter, regardless of other issues
        status.is_accessible = True

        self._accessibility_cache[skill_name] = status
        return status

    def validate_skill_frontmatter(self, skill_name: str) -> Tuple[bool, List[str]]:
        """
        Validate SKILL.md frontmatter format.

        Args:
            skill_name: Name of the skill to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        skill_md = self.skills_root / skill_name / "SKILL.md"

        if not skill_md.exists():
            return False, [f"SKILL.md not found"]

        errors = []
        try:
            with open(skill_md, "r") as f:
                content = f.read()

            # Check for frontmatter markers
            if not content.startswith("---"):
                errors.append("SKILL.md must start with ---")
            if "---" not in content[4:]:
                errors.append("SKILL.md missing closing --- marker")

            # Try to parse YAML
            frontmatter_match = re.match(
                r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL
            )
            if frontmatter_match:
                frontmatter_str = frontmatter_match.group(1)
                yaml.safe_load(frontmatter_str)
            else:
                errors.append("Could not extract YAML frontmatter")

            return len(errors) == 0, errors

        except yaml.YAMLError as e:
            return False, [f"YAML parse error: {str(e)}"]
        except Exception as e:
            return False, [f"Unexpected error: {str(e)}"]

    def get_all_skills_metadata(self) -> Dict[str, SkillMetadata]:
        """
        Load metadata for all discovered skills.

        Returns:
            Dictionary mapping skill names to SkillMetadata
        """
        result = {}
        for skill_name in self.discover_skills():
            metadata = self.load_skill_metadata(skill_name)
            if metadata:
                result[skill_name] = metadata

        return result

    def generate_accessibility_matrix(self) -> List[Dict[str, Any]]:
        """
        Generate accessibility matrix for all skills.

        Returns:
            List of dictionaries containing accessibility status for each skill
        """
        matrix = []
        for skill_name in self.discover_skills():
            status = self.validate_skill_metadata(skill_name)
            metadata = self.load_skill_metadata(skill_name)

            row = {
                "skill_name": skill_name,
                "accessible": status.is_accessible,
                "skill_md_exists": status.skill_md_exists,
                "frontmatter_valid": status.frontmatter_valid,
                "metadata_complete": status.metadata_complete,
                "category": metadata.category if metadata else "unknown",
                "version": metadata.version if metadata else "unknown",
                "role": metadata.role if metadata else "unknown",
                "model": metadata.model if metadata else "unknown",
                "effort": metadata.effort if metadata else "unknown",
                "errors": len(status.errors),
                "warnings": len(status.warnings),
            }
            matrix.append(row)

        return sorted(matrix, key=lambda x: x["skill_name"])

    def get_accessibility_stats(self) -> Dict[str, Any]:
        """
        Get accessibility statistics across all skills.

        Returns:
            Dictionary with accessibility statistics
        """
        matrix = self.generate_accessibility_matrix()

        total = len(matrix)
        accessible = sum(1 for m in matrix if m["accessible"])
        with_errors = sum(1 for m in matrix if m["errors"] > 0)
        with_warnings = sum(1 for m in matrix if m["warnings"] > 0)

        return {
            "total_skills": total,
            "accessible_skills": accessible,
            "skills_with_errors": with_errors,
            "skills_with_warnings": with_warnings,
            "accessibility_percentage": (accessible / total * 100) if total > 0 else 0,
        }

    def get_skills_by_category(self) -> Dict[str, List[str]]:
        """
        Group skills by category.

        Returns:
            Dictionary mapping category names to lists of skill names
        """
        result: Dict[str, List[str]] = {}
        for skill_name, metadata in self.get_all_skills_metadata().items():
            category = metadata.category
            if category not in result:
                result[category] = []
            result[category].append(skill_name)

        return {k: sorted(v) for k, v in sorted(result.items())}

    def get_skills_by_model(self) -> Dict[str, List[str]]:
        """
        Group skills by AI model.

        Returns:
            Dictionary mapping model names to lists of skill names
        """
        result: Dict[str, List[str]] = {}
        for skill_name, metadata in self.get_all_skills_metadata().items():
            model = metadata.model
            if model not in result:
                result[model] = []
            result[model].append(skill_name)

        return {k: sorted(v) for k, v in sorted(result.items())}

    def get_skills_by_effort(self) -> Dict[str, List[str]]:
        """
        Group skills by implementation effort.

        Returns:
            Dictionary mapping effort levels to lists of skill names
        """
        result: Dict[str, List[str]] = {}
        for skill_name, metadata in self.get_all_skills_metadata().items():
            effort = metadata.effort
            if effort not in result:
                result[effort] = []
            result[effort].append(skill_name)

        return {k: sorted(v) for k, v in sorted(result.items())}

    def check_skill_dependencies(
        self, skill_name: str
    ) -> Tuple[List[str], List[str]]:
        """
        Extract and validate skill dependencies (if specified in metadata).

        Args:
            skill_name: Name of the skill to check

        Returns:
            Tuple of (valid_dependencies, missing_dependencies)
        """
        metadata = self.load_skill_metadata(skill_name)
        if not metadata:
            return [], []

        # This would require parsing metadata for dependency information
        # For now, return empty lists as base skills don't have dependencies
        return [], []
