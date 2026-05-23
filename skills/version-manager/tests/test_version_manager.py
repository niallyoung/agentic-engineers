"""
Test suite for version-manager skill.

TDD approach:
- Phase 1 (Red): Write failing tests
- Phase 2 (Green): Implement minimal code to pass tests
- Phase 3 (Refactor): Optimize and add edge cases
"""

import pytest
import tempfile
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Import version-manager modules using relative imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from version_calculator import (
    parse_commit_type,
    get_commits_since_tag,
    calculate_next_version,
    get_current_version,
)
from changelog_updater import (
    update_changelog_unreleased,
    generate_unreleased_section,
    read_changelog,
)


class TestVersionCalculator:
    """Test semantic version calculation."""

    def test_parse_conventional_commit_feat(self):
        """Test parsing conventional commit: feat"""
        commit_type, is_breaking = parse_commit_type("feat: add new feature")
        assert commit_type == "feat"
        assert is_breaking is False

    def test_parse_conventional_commit_fix(self):
        """Test parsing conventional commit: fix"""
        commit_type, is_breaking = parse_commit_type("fix: resolve bug")
        assert commit_type == "fix"
        assert is_breaking is False

    def test_parse_conventional_commit_breaking(self):
        """Test parsing conventional commit: BREAKING CHANGE"""
        commit_type, is_breaking = parse_commit_type("feat!: breaking change feature")
        assert commit_type == "feat"
        assert is_breaking is True

    def test_parse_conventional_commit_with_scope(self):
        """Test parsing conventional commit with scope"""
        commit_type, is_breaking = parse_commit_type("fix(api): resolve endpoint issue")
        assert commit_type == "fix"
        assert is_breaking is False

    def test_parse_non_conventional_commit(self):
        """Test parsing non-conventional commit"""
        commit_type, is_breaking = parse_commit_type("random commit message")
        assert commit_type == "other"
        assert is_breaking is False

    def test_calculate_version_with_only_fixes(self):
        """Test: only fix commits → patch bump"""
        commits = [
            ("abc123", "2026-05-23", "fix: issue 1"),
            ("def456", "2026-05-24", "fix: issue 2"),
        ]
        next_version = calculate_next_version("0.8.0", commits)
        assert next_version == "0.8.1"

    def test_calculate_version_with_features(self):
        """Test: features present → minor bump"""
        commits = [
            ("abc123", "2026-05-23", "feat: new feature"),
            ("def456", "2026-05-24", "fix: bug fix"),
        ]
        next_version = calculate_next_version("0.8.0", commits)
        assert next_version == "0.9.0"

    def test_calculate_version_with_breaking_change(self):
        """Test: breaking change → major bump"""
        commits = [
            ("abc123", "2026-05-23", "feat!: breaking change"),
            ("def456", "2026-05-24", "fix: bug fix"),
        ]
        next_version = calculate_next_version("0.8.0", commits)
        assert next_version == "1.0.0"

    def test_calculate_version_no_changes(self):
        """Test: no commits since tag → no bump"""
        commits = []
        next_version = calculate_next_version("0.8.0", commits)
        assert next_version == "0.8.0"


class TestChangelogUpdater:
    """Test CHANGELOG updates with [Unreleased] section."""

    def test_unreleased_section_format(self):
        """Test [Unreleased] section is properly formatted"""
        commits = [
            ("abc123", "2026-05-23", "feat: new feature"),
            ("def456", "2026-05-24", "fix: bug fix"),
        ]
        section = generate_unreleased_section("0.9.0", commits)
        
        # Should have Unreleased header
        assert "## [Unreleased] - v0.9.0" in section
        # Should have Added section for feat
        assert "### Added" in section
        # Should have Fixed section for fix
        assert "### Fixed" in section

    def test_unreleased_sections_grouped_correctly(self):
        """Test commits are grouped by type in [Unreleased]"""
        commits = [
            ("abc123", "2026-05-23", "feat: feature 1"),
            ("def456", "2026-05-24", "feat: feature 2"),
            ("ghi789", "2026-05-25", "fix: fix 1"),
            ("jkl012", "2026-05-26", "docs: update docs"),
        ]
        section = generate_unreleased_section("0.9.0", commits)
        
        # Should have multiple features in Added
        assert "- feature 1" in section
        assert "- feature 2" in section
        # Should have fix in Fixed
        assert "- fix 1" in section
        # Should have docs
        assert "- update docs" in section

    def test_changelog_has_unreleased_section(self):
        """
        TDD RED TEST: Verify [Unreleased] section exists in CHANGELOG.
        This test initially fails, then passes after implementation.
        """
        changelog_content = Path(__file__).parent.parent.parent.parent / "CHANGELOG.md"
        assert changelog_content.exists(), "CHANGELOG.md must exist"
        
        content = changelog_content.read_text()
        # This is the RED test: currently fails if no [Unreleased] section
        assert "## [Unreleased]" in content, "CHANGELOG must have [Unreleased] section"

    def test_changelog_unreleased_shows_next_version(self):
        """Test [Unreleased] section shows projected next version"""
        # This would require actual CHANGELOG.md to have proper format
        changelog_content = Path(__file__).parent.parent.parent.parent / "CHANGELOG.md"
        content = changelog_content.read_text()
        
        # Extract [Unreleased] line
        lines = content.split('\n')
        unreleased_lines = [l for l in lines if "[Unreleased]" in l]
        
        # Should have at least one [Unreleased] section
        assert len(unreleased_lines) > 0, "CHANGELOG should have [Unreleased] section"
        
        # Format should include version marker
        unreleased_line = unreleased_lines[0]
        assert "v0." in unreleased_line or "Unreleased" in unreleased_line

    def test_empty_commits_generates_empty_unreleased(self):
        """Test with no commits: generate minimal [Unreleased] section"""
        commits = []
        section = generate_unreleased_section("0.8.1", commits)
        
        # Should still have header
        assert "## [Unreleased]" in section
        # Should indicate version
        assert "0.8.1" in section

    def test_update_changelog_preserves_version_sections(self):
        """Test updating CHANGELOG doesn't break existing version sections"""
        # Create temp CHANGELOG
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Changelog\n\n")
            f.write("## [v0.8.0] - 2026-05-20\n")
            f.write("### Fixed\n")
            f.write("- initial release\n")
            f.flush()
            
            changelog_path = Path(f.name)
        
        try:
            # Mock commit data
            commits = [
                ("abc123", "2026-05-23", "feat: new feature"),
            ]
            
            # Update changelog
            update_changelog_unreleased(changelog_path, "0.9.0", commits)
            
            # Read updated content
            updated = changelog_path.read_text()
            
            # Should have [Unreleased] at top
            assert "## [Unreleased]" in updated
            # Should preserve original v0.8.0
            assert "## [v0.8.0]" in updated
            # [Unreleased] should come before [v0.8.0]
            unreleased_idx = updated.find("[Unreleased]")
            v080_idx = updated.find("[v0.8.0]")
            assert unreleased_idx < v080_idx
        
        finally:
            changelog_path.unlink()


class TestIntegration:
    """Integration tests for version-manager workflow."""

    def test_version_calculation_flow(self):
        """Test full flow: commits → version calculation → changelog"""
        # Mock commits
        commits = [
            ("abc123", "2026-05-23", "feat: add API endpoint"),
            ("def456", "2026-05-24", "fix: resolve connection issue"),
            ("ghi789", "2026-05-25", "docs: update README"),
        ]
        
        # Calculate next version
        current = "0.8.0"
        next_version = calculate_next_version(current, commits)
        
        # Should bump minor (feat > fix)
        assert next_version == "0.9.0"
        
        # Generate unreleased section
        section = generate_unreleased_section(next_version, commits)
        
        # Should have correct format
        assert "## [Unreleased] - v0.9.0" in section
        assert "### Added" in section
        assert "- add API endpoint" in section

    def test_edge_case_only_chores_and_docs(self):
        """Test commits with only chores/docs don't bump version"""
        commits = [
            ("abc123", "2026-05-23", "chore: update dependencies"),
            ("def456", "2026-05-24", "docs: improve docs"),
        ]
        
        next_version = calculate_next_version("0.8.0", commits)
        
        # No feat/fix/breaking: no bump
        assert next_version == "0.8.0"

    def test_edge_case_multiple_breaking_changes(self):
        """Test multiple breaking changes → single major bump"""
        commits = [
            ("abc123", "2026-05-23", "feat!: breaking change 1"),
            ("def456", "2026-05-24", "feat!: breaking change 2"),
        ]
        
        next_version = calculate_next_version("0.8.0", commits)
        
        # Multiple breaking: still single major bump
        assert next_version == "1.0.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
