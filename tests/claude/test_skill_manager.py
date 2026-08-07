"""Comprehensive test suite for skill_manager module."""

import pytest
from pathlib import Path
from typing import List, Dict

from src.harnesses.claude_code.skill_manager import (
    SkillManager,
    SkillMetadata,
    SkillAccessibilityStatus,
)


class TestSkillDiscovery:
    """Test skill discovery functionality."""

    def test_discover_skills_returns_list(self, skills_root: Path) -> None:
        """Test that discover_skills returns a list."""
        manager = SkillManager(skills_root)
        skills = manager.discover_skills()
        assert isinstance(skills, list)

    def test_discover_skills_returns_sorted_list(self, skills_root: Path) -> None:
        """Test that discover_skills returns sorted list."""
        manager = SkillManager(skills_root)
        skills = manager.discover_skills()
        assert skills == sorted(skills)

    def test_discover_skills_minimum_count(
        self, skills_root: Path, test_skills_list: List[str]
    ) -> None:
        """Test that minimum expected skills are discovered."""
        manager = SkillManager(skills_root)
        skills = manager.discover_skills()
        # All test skills should be present
        for skill in test_skills_list:
            assert skill in skills

    def test_discover_skills_with_invalid_root(self) -> None:
        """Test discover_skills with non-existent root."""
        manager = SkillManager(Path("/nonexistent/path"))
        skills = manager.discover_skills()
        assert skills == []


class TestSkillMetadataLoading:
    """Test skill metadata loading and parsing."""

    def test_load_skill_metadata_returns_object(self, skills_root: Path) -> None:
        """Test that load_skill_metadata returns SkillMetadata object."""
        manager = SkillManager(skills_root)
        metadata = manager.load_skill_metadata("agent-creator")
        assert isinstance(metadata, SkillMetadata)

    def test_load_skill_metadata_has_name(self, skills_root: Path) -> None:
        """Test that loaded metadata has name field."""
        manager = SkillManager(skills_root)
        metadata = manager.load_skill_metadata("agent-creator")
        assert metadata is not None
        assert metadata.name == "agent-creator"

    def test_load_skill_metadata_has_description(self, skills_root: Path) -> None:
        """Test that loaded metadata has non-empty description."""
        manager = SkillManager(skills_root)
        metadata = manager.load_skill_metadata("agent-creator")
        assert metadata is not None
        assert len(metadata.description) > 0

    def test_load_skill_metadata_has_version(self, skills_root: Path) -> None:
        """Test that loaded metadata has version field."""
        manager = SkillManager(skills_root)
        metadata = manager.load_skill_metadata("agent-creator")
        assert metadata is not None
        assert metadata.version is not None

    def test_load_skill_metadata_has_category(self, skills_root: Path) -> None:
        """Test that loaded metadata has category field."""
        manager = SkillManager(skills_root)
        metadata = manager.load_skill_metadata("agent-creator")
        assert metadata is not None
        assert len(metadata.category) > 0

    def test_load_skill_metadata_caching(self, skills_root: Path) -> None:
        """Test that metadata is cached on subsequent calls."""
        manager = SkillManager(skills_root)
        metadata1 = manager.load_skill_metadata("agent-creator")
        metadata2 = manager.load_skill_metadata("agent-creator")
        assert metadata1 is metadata2  # Same object reference

    def test_load_skill_metadata_nonexistent_skill(self, skills_root: Path) -> None:
        """Test that non-existent skill returns None."""
        manager = SkillManager(skills_root)
        metadata = manager.load_skill_metadata("nonexistent-skill")
        assert metadata is None

    def test_metadata_to_dict(self, skills_root: Path) -> None:
        """Test that metadata can be converted to dictionary."""
        manager = SkillManager(skills_root)
        metadata = manager.load_skill_metadata("agent-creator")
        assert metadata is not None
        d = metadata.to_dict()
        assert isinstance(d, dict)
        assert "name" in d
        assert "description" in d


class TestSkillValidation:
    """Test skill validation functionality."""

    def test_validate_skill_metadata_returns_status(self, skills_root: Path) -> None:
        """Test that validation returns SkillAccessibilityStatus."""
        manager = SkillManager(skills_root)
        status = manager.validate_skill_metadata("agent-creator")
        assert isinstance(status, SkillAccessibilityStatus)

    def test_validate_skill_metadata_accessible(self, skills_root: Path) -> None:
        """Test that valid skills are marked accessible."""
        manager = SkillManager(skills_root)
        status = manager.validate_skill_metadata("agent-creator")
        assert status.is_accessible is True

    def test_validate_skill_metadata_skill_md_exists(self, skills_root: Path) -> None:
        """Test that SKILL.md existence is correctly detected."""
        manager = SkillManager(skills_root)
        status = manager.validate_skill_metadata("agent-creator")
        assert status.skill_md_exists is True

    def test_validate_skill_metadata_frontmatter_valid(self, skills_root: Path) -> None:
        """Test that valid frontmatter is detected."""
        manager = SkillManager(skills_root)
        status = manager.validate_skill_metadata("agent-creator")
        assert status.frontmatter_valid is True

    def test_validate_skill_metadata_metadata_complete(self, skills_root: Path) -> None:
        """Test that complete metadata is detected."""
        manager = SkillManager(skills_root)
        status = manager.validate_skill_metadata("agent-creator")
        assert status.metadata_complete is True

    def test_validate_skill_metadata_caching(self, skills_root: Path) -> None:
        """Test that validation results are cached."""
        manager = SkillManager(skills_root)
        status1 = manager.validate_skill_metadata("agent-creator")
        status2 = manager.validate_skill_metadata("agent-creator")
        assert status1 is status2  # Same object reference

    def test_validate_skill_frontmatter_valid(self, skills_root: Path) -> None:
        """Test frontmatter validation for valid skill."""
        manager = SkillManager(skills_root)
        is_valid, errors = manager.validate_skill_frontmatter("agent-creator")
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_skill_frontmatter_nonexistent(self, skills_root: Path) -> None:
        """Test frontmatter validation for non-existent skill."""
        manager = SkillManager(skills_root)
        is_valid, errors = manager.validate_skill_frontmatter("nonexistent-skill")
        assert is_valid is False
        assert len(errors) > 0


class TestSkillMetadataRetrieval:
    """Test metadata retrieval and grouping functionality."""

    def test_get_all_skills_metadata_returns_dict(self, skills_root: Path) -> None:
        """Test that get_all_skills_metadata returns dictionary."""
        manager = SkillManager(skills_root)
        metadata_dict = manager.get_all_skills_metadata()
        assert isinstance(metadata_dict, dict)

    def test_get_all_skills_metadata_keys_are_skill_names(
        self, skills_root: Path
    ) -> None:
        """Test that keys in metadata dict are skill names."""
        manager = SkillManager(skills_root)
        metadata_dict = manager.get_all_skills_metadata()
        for key in metadata_dict.keys():
            assert isinstance(key, str)
            assert len(key) > 0

    def test_get_all_skills_metadata_values_are_metadata(
        self, skills_root: Path
    ) -> None:
        """Test that values in metadata dict are SkillMetadata."""
        manager = SkillManager(skills_root)
        metadata_dict = manager.get_all_skills_metadata()
        for value in metadata_dict.values():
            assert isinstance(value, SkillMetadata)

    def test_generate_accessibility_matrix_returns_list(self, skills_root: Path) -> None:
        """Test that accessibility matrix is a list."""
        manager = SkillManager(skills_root)
        matrix = manager.generate_accessibility_matrix()
        assert isinstance(matrix, list)

    def test_generate_accessibility_matrix_has_dicts(self, skills_root: Path) -> None:
        """Test that accessibility matrix contains dictionaries."""
        manager = SkillManager(skills_root)
        matrix = manager.generate_accessibility_matrix()
        assert all(isinstance(row, dict) for row in matrix)

    def test_generate_accessibility_matrix_sorted(self, skills_root: Path) -> None:
        """Test that accessibility matrix is sorted by skill name."""
        manager = SkillManager(skills_root)
        matrix = manager.generate_accessibility_matrix()
        names = [row["skill_name"] for row in matrix]
        assert names == sorted(names)

    def test_get_skills_by_category_returns_dict(self, skills_root: Path) -> None:
        """Test that get_skills_by_category returns dictionary."""
        manager = SkillManager(skills_root)
        by_category = manager.get_skills_by_category()
        assert isinstance(by_category, dict)

    def test_get_skills_by_model_returns_dict(self, skills_root: Path) -> None:
        """Test that get_skills_by_model returns dictionary."""
        manager = SkillManager(skills_root)
        by_model = manager.get_skills_by_model()
        assert isinstance(by_model, dict)

    def test_get_skills_by_effort_returns_dict(self, skills_root: Path) -> None:
        """Test that get_skills_by_effort returns dictionary."""
        manager = SkillManager(skills_root)
        by_effort = manager.get_skills_by_effort()
        assert isinstance(by_effort, dict)

    def test_get_accessibility_stats_returns_dict(self, skills_root: Path) -> None:
        """Test that get_accessibility_stats returns dictionary."""
        manager = SkillManager(skills_root)
        stats = manager.get_accessibility_stats()
        assert isinstance(stats, dict)

    def test_get_accessibility_stats_has_required_keys(self, skills_root: Path) -> None:
        """Test that stats have required keys."""
        manager = SkillManager(skills_root)
        stats = manager.get_accessibility_stats()
        required_keys = [
            "total_skills",
            "accessible_skills",
            "skills_with_errors",
            "skills_with_warnings",
            "accessibility_percentage",
        ]
        for key in required_keys:
            assert key in stats

    def test_check_skill_dependencies_returns_tuple(self, skills_root: Path) -> None:
        """Test that check_skill_dependencies returns tuple."""
        manager = SkillManager(skills_root)
        result = manager.check_skill_dependencies("agent-creator")
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestSkillManagerTypeHints:
    """Test type hints and return types."""

    def test_discover_skills_returns_list_of_strings(self, skills_root: Path) -> None:
        """Test that discover_skills returns List[str]."""
        manager = SkillManager(skills_root)
        skills = manager.discover_skills()
        assert all(isinstance(s, str) for s in skills)

    def test_get_all_skills_metadata_returns_correct_types(
        self, skills_root: Path
    ) -> None:
        """Test that metadata dict has correct types."""
        manager = SkillManager(skills_root)
        result = manager.get_all_skills_metadata()
        assert isinstance(result, dict)
        for key, value in result.items():
            assert isinstance(key, str)
            assert isinstance(value, SkillMetadata)

    def test_generate_accessibility_matrix_row_types(self, skills_root: Path) -> None:
        """Test that matrix rows have correct field types."""
        manager = SkillManager(skills_root)
        matrix = manager.generate_accessibility_matrix()
        for row in matrix:
            assert isinstance(row["skill_name"], str)
            assert isinstance(row["accessible"], bool)
            assert isinstance(row["skill_md_exists"], bool)
            assert isinstance(row["category"], str)
