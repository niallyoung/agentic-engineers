"""CHANGELOG.md validation tests to prevent versioning sync issues."""
import re
from pathlib import Path


class TestChangelogFormat:
    """Validate CHANGELOG.md format and versioning consistency."""

    def test_changelog_exists(self):
        """CHANGELOG.md must exist in repository root."""
        changelog = Path(__file__).parent.parent / "CHANGELOG.md"
        assert changelog.exists(), "CHANGELOG.md not found in repository root"

    def test_unreleased_section_has_no_version(self):
        """[Unreleased] section must not have a version number."""
        changelog = Path(__file__).parent.parent / "CHANGELOG.md"
        content = changelog.read_text()
        
        # Find [Unreleased] line
        unreleased_match = re.search(r'^## \[Unreleased\](.*)$', content, re.MULTILINE)
        assert unreleased_match, "[Unreleased] section not found"
        
        unreleased_line = unreleased_match.group(0)
        # Should be exactly "## [Unreleased]" with no version number
        assert unreleased_line == "## [Unreleased]", \
            f"[Unreleased] must have no version number. Found: {unreleased_line}"

    def test_version_entries_have_correct_format(self):
        """All version entries must follow ## [vX.Y.Z] - YYYY-MM-DD format."""
        changelog = Path(__file__).parent.parent / "CHANGELOG.md"
        content = changelog.read_text()
        
        # Find all version entries (excluding [Unreleased])
        version_pattern = r'^## \[(v\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$'
        matches = re.finditer(version_pattern, content, re.MULTILINE)
        
        versions = []
        for match in matches:
            versions.append((match.group(1), match.start()))
        
        assert len(versions) > 0, "No version entries found in CHANGELOG"
        
        # Extract just version numbers
        version_numbers = [v[0] for v in versions]
        
        # Verify format of each
        for version in version_numbers:
            parts = version.lstrip('v').split('.')
            assert len(parts) == 3, f"Version {version} must have format vX.Y.Z"
            for part in parts:
                assert part.isdigit(), f"Version {version} has non-numeric component"

    def test_versions_in_descending_order(self):
        """Version entries must be in descending order (newest first)."""
        changelog = Path(__file__).parent.parent / "CHANGELOG.md"
        content = changelog.read_text()
        
        # Find all version entries
        version_pattern = r'^## \[(v\d+\.\d+\.\d+)\]'
        matches = re.finditer(version_pattern, content, re.MULTILINE)
        
        versions = [match.group(1) for match in matches]
        assert len(versions) > 1, "Need at least 2 versions to verify ordering"
        
        # Convert to tuples for comparison
        def version_key(v):
            parts = v.lstrip('v').split('.')
            return tuple(int(p) for p in parts)
        
        # Verify each version is >= the next
        for i in range(len(versions) - 1):
            current = version_key(versions[i])
            next_version = version_key(versions[i + 1])
            assert current >= next_version, \
                f"Version {versions[i]} should come after {versions[i + 1]} (descending order)"

    def test_no_duplicate_versions(self):
        """No duplicate version entries allowed."""
        changelog = Path(__file__).parent.parent / "CHANGELOG.md"
        content = changelog.read_text()
        
        # Find all version entries
        version_pattern = r'^## \[(v\d+\.\d+\.\d+)\]'
        matches = re.finditer(version_pattern, content, re.MULTILINE)
        
        versions = [match.group(1) for match in matches]
        
        # Check for duplicates
        seen = set()
        for version in versions:
            assert version not in seen, f"Duplicate version entry found: {version}"
            seen.add(version)

    def test_unreleased_comes_before_all_versions(self):
        """[Unreleased] section must come before any version entries."""
        changelog = Path(__file__).parent.parent / "CHANGELOG.md"
        content = changelog.read_text()
        
        unreleased_pos = content.find("## [Unreleased]")
        first_version_pos = re.search(r'^## \[(v\d+\.\d+\.\d+)\]', content, re.MULTILINE)
        
        assert unreleased_pos != -1, "[Unreleased] section not found"
        
        if first_version_pos:
            assert unreleased_pos < first_version_pos.start(), \
                "[Unreleased] must come before any versioned entries"

    def test_changelog_has_expected_sections(self):
        """Each version entry should have standard sections."""
        changelog = Path(__file__).parent.parent / "CHANGELOG.md"
        content = changelog.read_text()
        
        # Find first version entry (skip [Unreleased] which may be empty)
        version_matches = re.finditer(
            r'^## \[(v\d+\.\d+\.\d+)\][^\n]*\n(.*?)(?=^## \[|$)',
            content,
            re.MULTILINE | re.DOTALL
        )
        
        version_sections = list(version_matches)
        assert len(version_sections) > 0, "Could not find any version entries"
        
        # Check first non-empty version section
        for version_match in version_sections:
            version_section = version_match.group(2).strip()
            if not version_section:
                continue
                
            # Should have at least one of: Added, Fixed, Changed, Removed, Security, Documentation
            valid_sections = ['Added', 'Fixed', 'Changed', 'Removed', 'Security', 'Documentation']
            has_section = any(f"### {section}" in version_section for section in valid_sections)
            
            assert has_section, \
                f"Version entry should have at least one of: {', '.join(valid_sections)}"
            break  # Only check first non-empty version


    def test_changelog_no_version_in_unreleased_content(self):
        """The [Unreleased] section content should not mention version numbers."""
        changelog = Path(__file__).parent.parent / "CHANGELOG.md"
        content = changelog.read_text()
        
        # Extract content between [Unreleased] and first [vX.Y.Z]
        unreleased_match = re.search(
            r'^## \[Unreleased\]\n(.*?)^## \[v\d+\.\d+\.\d+\]',
            content,
            re.MULTILINE | re.DOTALL
        )
        
        if unreleased_match:
            unreleased_section = unreleased_match.group(1)
            # Should not have version-like patterns in the section headers
            # (but may have them in entries)
            assert "- v" not in unreleased_section or \
                   "upgrade to v" in unreleased_section or \
                   "support v" in unreleased_section, \
                "Unreleased section should not reference specific versions"

    def test_changelog_is_valid_markdown(self):
        """CHANGELOG.md should be valid Markdown."""
        changelog = Path(__file__).parent.parent / "CHANGELOG.md"
        content = changelog.read_text()
        
        # Check for basic Markdown validity
        assert content.startswith("# "), "CHANGELOG should start with H1 heading"
        
        # Count heading levels
        h2_count = len(re.findall(r'^## ', content, re.MULTILINE))
        h3_count = len(re.findall(r'^### ', content, re.MULTILINE))
        
        assert h2_count > 0, "CHANGELOG should have H2 headings (version entries)"
        assert h3_count > 0, "CHANGELOG should have H3 headings (section titles)"
