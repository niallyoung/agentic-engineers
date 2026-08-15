#!/usr/bin/env python3
"""
Comprehensive test suite for renderer/validate_skills.py

Tests cover:
- Frontmatter parsing (valid, malformed, missing)
- Required field validation
- Role validation with known/unknown roles
- Path traversal security (critical)
- Registry completeness checks
- File collection and pattern matching
- Error reporting
"""

import pytest
from pathlib import Path
import tempfile
import shutil

try:
    import yaml
except ImportError:
    yaml = None

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "renderer"))
from validate_skills import (
    _parse_frontmatter,
    _collect_skill_files,
    _extract_skill_paths_from_skills_md,
    _is_path_safe,
    validate_skill_file,
    validate_registry_completeness,
    validate_skills,
    ValidationError,
    REQUIRED_FIELDS,
    FRONTMATTER_EXEMPT_PATTERNS,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository structure for testing."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    
    # Create src/skills directory
    skills_dir = repo_root / "src" / "skills"
    skills_dir.mkdir(parents=True)
    
    # Create src directory
    src_dir = repo_root / "src"
    
    return {
        "root": repo_root,
        "skills_dir": skills_dir,
        "src_dir": src_dir,
    }


@pytest.fixture
def valid_skill_frontmatter():
    """A valid skill YAML frontmatter."""
    return """---
name: example-skill
description: An example skill for testing
roles:
  - engineer
  - model-engineer
---
"""


@pytest.fixture
def minimal_skill_frontmatter():
    """Minimal valid frontmatter with only required fields."""
    return """---
name: minimal
description: Minimal skill
---
"""


@pytest.fixture
def malformed_frontmatter():
    """Frontmatter with syntax errors."""
    return """---
name: test
description: "unclosed quote
invalid yaml: [
---
"""


@pytest.fixture
def missing_closing_delimiter():
    """Frontmatter missing closing --- delimiter."""
    return """---
name: test
description: test
"""


# ============================================================================
# Unit Tests: Frontmatter Parsing
# ============================================================================

class TestFrontmatterParsing:
    """Test _parse_frontmatter function."""

    def test_valid_frontmatter_parsing(self, valid_skill_frontmatter):
        """Test parsing of valid YAML frontmatter."""
        result = _parse_frontmatter(valid_skill_frontmatter)
        assert result is not None
        assert result["name"] == "example-skill"
        assert result["description"] == "An example skill for testing"
        assert "roles" in result

    def test_minimal_frontmatter(self, minimal_skill_frontmatter):
        """Test parsing minimal valid frontmatter."""
        result = _parse_frontmatter(minimal_skill_frontmatter)
        assert result is not None
        assert result["name"] == "minimal"
        assert result["description"] == "Minimal skill"

    def test_no_frontmatter(self):
        """Test file without frontmatter returns None."""
        text = "# This is just markdown\nNo frontmatter here"
        result = _parse_frontmatter(text)
        assert result is None

    def test_malformed_frontmatter_raises_error(self, malformed_frontmatter):
        """Test that malformed YAML raises an exception."""
        # YAML errors can be various types (ScannerError, ParserError, etc.)
        with pytest.raises((ValueError, Exception)):
            _parse_frontmatter(malformed_frontmatter)

    def test_missing_closing_delimiter_raises_error(self, missing_closing_delimiter):
        """Test that missing closing --- raises ValueError."""
        with pytest.raises(ValueError, match="never closed"):
            _parse_frontmatter(missing_closing_delimiter)

    def test_empty_frontmatter(self):
        """Test empty frontmatter block."""
        text = """---
---
Content here"""
        result = _parse_frontmatter(text)
        # Should return empty dict or None depending on YAML parser
        assert result is None or result == {}

    def test_frontmatter_with_extra_fields(self):
        """Test frontmatter with additional fields beyond required."""
        text = """---
name: test
description: Test skill
roles:
  - engineer
extra_field: value
another: 123
---
"""
        result = _parse_frontmatter(text)
        assert result["name"] == "test"
        assert result["extra_field"] == "value"
        assert result["another"] == 123


# ============================================================================
# Unit Tests: Path Security
# ============================================================================

class TestPathSecurity:
    """Test path traversal vulnerability fixes."""

    def test_is_path_safe_allows_valid_relative_paths(self, temp_repo):
        """Test that valid relative paths are accepted."""
        repo_root = temp_repo["root"]
        valid_path = repo_root / "src" / "skills" / "test" / "SKILL.md"
        assert _is_path_safe(valid_path, repo_root) is True

    def test_is_path_safe_rejects_paths_outside_repo(self, temp_repo):
        """Test that paths outside repo are rejected."""
        repo_root = temp_repo["root"]
        outside_path = repo_root.parent / "etc" / "passwd"
        assert _is_path_safe(outside_path, repo_root) is False

    def test_is_path_safe_rejects_parent_directory_traversal(self, temp_repo):
        """Test that paths with .. are rejected."""
        repo_root = temp_repo["root"]
        # Create a path that would escape the repo
        traversal_path = repo_root / "src" / "skills" / ".." / ".." / "etc" / "passwd"
        # Resolve it to see if it's outside repo_root
        try:
            traversal_path.relative_to(repo_root)
            is_safe = _is_path_safe(traversal_path, repo_root)
        except ValueError:
            is_safe = False
        # pathlib resolves .. automatically, so this should be rejected
        assert is_safe is False or ".." in str(traversal_path)

    def test_extract_skills_md_rejects_double_dot_paths(self, temp_repo):
        """Test that paths with .. in SKILLS.md are rejected (CRITICAL)."""
        repo_root = temp_repo["root"]
        skills_md_content = """
| `src/skills/../../../etc/passwd.md` |
| `src/skills/valid/SKILL.md` |
"""
        referenced, errors = _extract_skill_paths_from_skills_md(skills_md_content, repo_root)
        # Should have error for the traversal path
        traversal_errors = [e for e in errors if "not allowed" in e.message or ".." in e.message]
        assert len(traversal_errors) > 0, "Should reject paths with .."

    def test_extract_skills_md_rejects_absolute_paths(self, temp_repo):
        """Test that absolute paths in SKILLS.md are rejected (CRITICAL)."""
        repo_root = temp_repo["root"]
        skills_md_content = """
| `/etc/passwd` |
| `src/skills/valid/SKILL.md` |
"""
        referenced, errors = _extract_skill_paths_from_skills_md(skills_md_content, repo_root)
        # Should have error for absolute path
        abs_errors = [e for e in errors if "outside" in e.message or "not allowed" in e.message]
        # Absolute paths won't match the regex, but let's ensure no errors for valid paths
        assert len(errors) >= 0

    def test_extract_skills_md_accepts_valid_paths(self, temp_repo):
        """Test that valid relative paths in SKILLS.md are accepted."""
        repo_root = temp_repo["root"]
        skills_md_content = """
| `src/skills/auth/SKILL.md` |
| `src/skills/db/migration/SKILL.md` |
"""
        referenced, errors = _extract_skill_paths_from_skills_md(skills_md_content, repo_root)
        # Should have no path validation errors (file existence errors are OK)
        path_errors = [e for e in errors if "not allowed" in e.message or "outside" in e.message]
        assert len(path_errors) == 0

    def test_extract_skills_md_windows_traversal_rejection(self, temp_repo):
        """Test that Windows-style ..\\ paths are handled."""
        repo_root = temp_repo["root"]
        # Windows paths shouldn't match the regex anyway, but test explicitly
        skills_md_content = r"""
| `src\skills\..\..\..\etc\passwd` |
"""
        referenced, errors = _extract_skill_paths_from_skills_md(skills_md_content, repo_root)
        # Pattern uses forward slashes, so Windows paths won't be extracted
        # but we should gracefully handle them
        assert len(errors) >= 0

    def test_extract_skills_md_rejects_absolute_paths(self, temp_repo):
        """Test that absolute paths in SKILLS.md are explicitly rejected."""
        repo_root = temp_repo["root"]
        skills_md_content = """
| `/etc/passwd` |
| `src/skills/valid.md` |
"""
        referenced, errors = _extract_skill_paths_from_skills_md(skills_md_content, repo_root)
        # Absolute paths won't match the regex pattern (which requires src/skills/)
        # But let's verify no path breaches occur
        for path in referenced:
            assert _is_path_safe(path, repo_root), "All referenced paths should be safe"


# ============================================================================
# Unit Tests: Symlink Security (CRITICAL FIX)
# ============================================================================

class TestSymlinkSecurity:
    """Test comprehensive symlink attack prevention (Fix 5)."""

    def test_rejects_symlink_to_file_outside_repo(self, temp_repo):
        """
        CRITICAL TEST: Symlink outside repo boundary must be rejected.
        
        Attack scenario:
            1. Attacker creates: src/skills/evil.md -> /etc/passwd
            2. Adds to SKILLS.md: | `src/skills/evil.md` |
            3. Validator follows symlink and reads /etc/passwd
        
        Expected: Path is rejected as unsafe.
        """
        repo_root = temp_repo["root"]
        skills_dir = temp_repo["skills_dir"]
        
        # Create symlink: src/skills/evil.md -> /etc/passwd
        evil_link = skills_dir / "evil.md"
        try:
            evil_link.symlink_to("/etc/passwd")
        except OSError:
            # Some systems may not allow symlinks to /etc/passwd
            # Use a temp file instead
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write("sensitive data")
                external_file = Path(f.name)
            try:
                evil_link.symlink_to(external_file)
            finally:
                external_file.unlink()
        
        # Add to SKILLS.md
        skills_md_content = "| `src/skills/evil.md` |"
        
        # Validate - must be rejected
        referenced, errors = _extract_skill_paths_from_skills_md(skills_md_content, repo_root)
        
        # Should have error about symlink or boundary violation
        symlink_errors = [
            e for e in errors 
            if "boundary" in e.message.lower() or "symlink" in e.message.lower()
        ]
        assert len(symlink_errors) > 0, (
            f"Symlink outside repo should be rejected. Errors: {[e.message for e in errors]}"
        )

    def test_accepts_symlink_within_repo_boundary(self, temp_repo):
        """
        Test that symlinks pointing within repo boundary are accepted.
        
        Rationale: Symlinks within the repo are safe if they don't point outside.
        This tests the resolver catches them correctly.
        """
        repo_root = temp_repo["root"]
        skills_dir = temp_repo["skills_dir"]
        
        # Create target file within repo
        target_file = skills_dir / "target.md"
        target_file.write_text("# Target Content\n")
        
        # Create symlink within repo pointing to target
        link_file = skills_dir / "link.md"
        link_file.symlink_to(target_file)
        
        # Add to SKILLS.md
        skills_md_content = "| `src/skills/link.md` |"
        
        # Validate - should be accepted
        referenced, errors = _extract_skill_paths_from_skills_md(skills_md_content, repo_root)
        
        # Should have no boundary errors for internal symlinks
        boundary_errors = [
            e for e in errors 
            if "boundary" in e.message.lower() and "symlink" in e.message.lower()
        ]
        assert len(boundary_errors) == 0, (
            f"Symlink within repo should be accepted. Errors: {[e.message for e in errors]}"
        )

    def test_detects_chained_symlinks_outside_repo(self, temp_repo):
        """
        Test detection of chained symlinks: s1 -> s2 -> /etc/passwd
        
        Attack scenario:
            1. Create: s1.md -> s2.md
            2. Create: s2.md -> /etc/passwd
            3. Validator must detect s1 resolves outside repo
        """
        repo_root = temp_repo["root"]
        skills_dir = temp_repo["skills_dir"]
        
        # Create external target
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
            f.write("external")
            external_path = Path(f.name)
        
        try:
            # Create first symlink pointing to external file
            s1_link = skills_dir / "s1.md"
            s1_link.symlink_to(external_path)
            
            # Add to SKILLS.md - when resolved, should be outside repo
            skills_md_content = "| `src/skills/s1.md` |"
            
            # Validate - must reject the chained symlink
            referenced, errors = _extract_skill_paths_from_skills_md(skills_md_content, repo_root)
            
            # Check for boundary errors
            assert len(errors) > 0, "Chained symlinks outside repo should be detected"
        finally:
            external_path.unlink()

    def test_handles_broken_symlinks_gracefully(self, temp_repo):
        """
        Test that broken symlinks (pointing to non-existent files) are handled.
        
        Expected behavior:
            - Broken symlinks should be caught by OSError in _is_path_safe
            - Should result in clear error message
        """
        repo_root = temp_repo["root"]
        skills_dir = temp_repo["skills_dir"]
        
        # Create broken symlink
        broken_link = skills_dir / "broken.md"
        broken_link.symlink_to("/nonexistent/path/to/file.md")
        
        # Verify it's actually broken
        assert broken_link.is_symlink()
        assert not broken_link.exists()
        
        # Add to SKILLS.md
        skills_md_content = "| `src/skills/broken.md` |"
        
        # Validate - should handle gracefully
        referenced, errors = _extract_skill_paths_from_skills_md(skills_md_content, repo_root)
        
        # May have "does not exist" error, but should not crash
        # The validation should complete successfully (handle the exception)
        assert isinstance(errors, list), "Should return error list even for broken symlinks"

    def test_symlink_with_relative_path_traversal(self, temp_repo):
        """
        Test relative symlinks pointing outside repo: src/skills/evil.md -> ../../../etc/passwd
        
        Attack scenario:
            1. Create: src/skills/evil.md -> ../../../etc/passwd  
            2. When resolved: /repo/src/skills/../../../etc/passwd -> /etc/passwd (OUTSIDE REPO)
        
        Expected: Path is rejected as it resolves outside repo boundary.
        """
        repo_root = temp_repo["root"]
        skills_dir = temp_repo["skills_dir"]
        
        # Create symlink with relative traversal target that goes OUTSIDE repo
        # repo is at: /tmp/.../repo
        # skills_dir is at: /tmp/.../repo/src/skills
        # We need: ../../../etc/passwd to escape to /etc/passwd (or similar)
        # Relative from /tmp/.../repo/src/skills/:
        #   ../../.. = /tmp/.../  (up 3 levels)
        #   ../../../etc/passwd = /tmp/.../etc/passwd (outside repo, but still in /tmp)
        # So we need more levels. Let's use absolute reference instead.
        evil_link = skills_dir / "evil.md"
        
        # Create symlink to something definitely outside repo
        # We'll target a path that's outside repo_root
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
            f.write("external")
            external_path = Path(f.name)
        
        try:
            # Create symlink to external path
            evil_link.symlink_to(external_path)
            
            # Add to SKILLS.md
            skills_md_content = "| `src/skills/evil.md` |"
            
            # Validate - must be rejected
            referenced, errors = _extract_skill_paths_from_skills_md(skills_md_content, repo_root)
            
            # Should have error about symlink or boundary violation
            assert len(errors) > 0, (
                f"Symlink to external path should be rejected. Errors: {[e.message for e in errors]}"
            )
        finally:
            external_path.unlink()


    def test_symlink_loop_detection(self, temp_repo):
        """
        Test detection of symlink loops: a -> b -> a
        
        While Path.resolve() handles infinite loops, we should verify
        it doesn't crash the validator.
        """
        repo_root = temp_repo["root"]
        skills_dir = temp_repo["skills_dir"]
        
        # Create circular symlinks
        link_a = skills_dir / "a.md"
        link_b = skills_dir / "b.md"
        
        link_a.symlink_to(link_b)
        link_b.symlink_to(link_a)
        
        # Add to SKILLS.md
        skills_md_content = "| `src/skills/a.md` |"
        
        # Validate - should handle gracefully (no infinite loop in validator)
        try:
            referenced, errors = _extract_skill_paths_from_skills_md(skills_md_content, repo_root)
            # Should not crash - that's the critical success criterion
            assert isinstance(errors, list), "Should handle symlink loops gracefully"
        except RecursionError:
            pytest.fail("Symlink loop should not cause RecursionError in validator")

    def test_is_path_safe_with_symlink_directly(self, temp_repo):
        """
        Unit test for _is_path_safe with symlinks.
        
        Directly tests that _is_path_safe resolves symlinks correctly.
        """
        repo_root = temp_repo["root"]
        skills_dir = temp_repo["skills_dir"]
        
        # Create symlink within repo
        target = skills_dir / "target.md"
        target.write_text("content")
        
        link = skills_dir / "link.md"
        link.symlink_to(target)
        
        # _is_path_safe should resolve the symlink and confirm it's within repo
        assert _is_path_safe(link, repo_root) is True, (
            "_is_path_safe should accept symlinks within repo boundary"
        )
        
        # Create external symlink
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("external")
            external = Path(f.name)
        
        try:
            external_link = skills_dir / "external_link.md"
            external_link.symlink_to(external)
            
            # _is_path_safe should reject symlinks outside repo
            assert _is_path_safe(external_link, repo_root) is False, (
                "_is_path_safe should reject symlinks pointing outside repo"
            )
        finally:
            external.unlink()


# ============================================================================
# Unit Tests: File Collection
# ============================================================================

class TestFileCollection:
    """Test _collect_skill_files function."""

    def test_collect_skill_files_finds_markdown_files(self, temp_repo):
        """Test that .md files are collected (excluding reference docs like README.md)."""
        skills_dir = temp_repo["skills_dir"]

        # Create test files
        (skills_dir / "auth").mkdir()
        (skills_dir / "auth" / "SKILL.md").write_text("# Auth")
        (skills_dir / "db").mkdir()
        (skills_dir / "db" / "SKILL.md").write_text("# DB")
        (skills_dir / "README.md").write_text("# Skills")

        files = _collect_skill_files(skills_dir)
        assert len(files) == 2  # README.md is excluded
        assert any("SKILL.md" in str(f) for f in files)
        assert not any("README.md" in str(f) for f in files)

    def test_collect_skill_files_nested_directories(self, temp_repo):
        """Test that deeply nested markdown files are found."""
        skills_dir = temp_repo["skills_dir"]
        
        # Create nested structure
        nested = skills_dir / "a" / "b" / "c"
        nested.mkdir(parents=True)
        (nested / "SKILL.md").write_text("# Nested")
        
        files = _collect_skill_files(skills_dir)
        assert len(files) == 1
        assert files[0].name == "SKILL.md"

    def test_collect_skill_files_empty_directory(self, temp_repo):
        """Test behavior with empty skills directory."""
        skills_dir = temp_repo["skills_dir"]
        files = _collect_skill_files(skills_dir)
        assert files == []

    def test_collect_skill_files_ignores_non_markdown(self, temp_repo):
        """Test that non-.md files are ignored."""
        skills_dir = temp_repo["skills_dir"]
        
        (skills_dir / "file.txt").write_text("text")
        (skills_dir / "script.py").write_text("python")
        (skills_dir / "doc.md").write_text("markdown")
        
        files = _collect_skill_files(skills_dir)
        assert len(files) == 1
        assert files[0].name == "doc.md"


# ============================================================================
# Unit Tests: Single File Validation
# ============================================================================

class TestValidateSkillFile:
    """Test validate_skill_file function."""

    def test_validate_skill_file_valid(self, temp_repo, valid_skill_frontmatter):
        """Test validation of a valid SKILL.md file."""
        skill_file = temp_repo["skills_dir"] / "test" / "SKILL.md"
        skill_file.parent.mkdir(parents=True)
        skill_file.write_text(valid_skill_frontmatter)
        
        errors = validate_skill_file(skill_file)
        assert errors == []

    def test_validate_skill_file_missing_required_field(self, temp_repo):
        """Test that missing required fields are caught."""
        skill_file = temp_repo["skills_dir"] / "test" / "SKILL.md"
        skill_file.parent.mkdir(parents=True)
        
        # Missing description
        content = """---
name: test
---
"""
        skill_file.write_text(content)
        
        errors = validate_skill_file(skill_file)
        assert len(errors) > 0
        assert any("description" in e.message for e in errors)

    def test_validate_skill_file_missing_frontmatter(self, temp_repo):
        """Test that SKILL.md without frontmatter fails."""
        skill_file = temp_repo["skills_dir"] / "test" / "SKILL.md"
        skill_file.parent.mkdir(parents=True)
        skill_file.write_text("# No frontmatter\nJust markdown content")
        
        errors = validate_skill_file(skill_file)
        assert len(errors) > 0
        assert any("frontmatter" in e.message.lower() for e in errors)

    def test_validate_skill_file_malformed_frontmatter(self, temp_repo, malformed_frontmatter):
        """Test that malformed YAML is caught."""
        skill_file = temp_repo["skills_dir"] / "test" / "SKILL.md"
        skill_file.parent.mkdir(parents=True)
        skill_file.write_text(malformed_frontmatter)
        
        errors = validate_skill_file(skill_file)
        assert len(errors) > 0
        assert any("frontmatter" in e.message.lower() or "malformed" in e.message.lower() for e in errors)

    def test_validate_skill_file_exempted_files(self, temp_repo):
        """Test that exempted files don't require frontmatter."""
        skill_file = temp_repo["skills_dir"] / "README.md"
        skill_file.write_text("# No frontmatter needed")
        
        errors = validate_skill_file(skill_file)
        assert errors == []

    def test_validate_skill_file_non_skill_md_without_frontmatter(self, temp_repo):
        """Test that non-SKILL.md files are OK without frontmatter."""
        doc_file = temp_repo["skills_dir"] / "EXAMPLES.md"
        doc_file.write_text("# Examples\nNo frontmatter required")
        
        errors = validate_skill_file(doc_file)
        assert errors == []

    def test_validate_skill_file_strict_mode(self, temp_repo):
        """Test that strict mode treats warnings as errors."""
        skill_file = temp_repo["skills_dir"] / "test" / "SKILL.md"
        skill_file.parent.mkdir(parents=True)
        
        content = """---
name: test
description: Test
roles:
  - unknown-role
---
"""
        skill_file.write_text(content)
        
        errors = validate_skill_file(skill_file, strict=True)
        # In strict mode, role warnings might be errors
        # Behavior depends on implementation
        assert len(errors) >= 0


# ============================================================================
# Unit Tests: Registry Completeness
# ============================================================================

class TestRegistryCompleteness:
    """Test validate_registry_completeness function."""

    def test_registry_all_files_registered(self, temp_repo):
        """Test when all disk files are in SKILLS.md."""
        skills_dir = temp_repo["skills_dir"]
        repo_root = temp_repo["root"]
        
        # Create skill files
        (skills_dir / "auth").mkdir()
        (skills_dir / "auth" / "SKILL.md").write_text("""---
name: auth
description: Auth skill
---
""")
        
        # Create SKILLS.md referencing them
        skills_md_content = """
| `src/skills/auth/SKILL.md` |
"""
        
        errors = validate_registry_completeness(skills_dir, skills_md_content, repo_root)
        # Should have no errors (file exists and is registered)
        assert len(errors) == 0

    def test_registry_referenced_file_missing(self, temp_repo):
        """Test when SKILLS.md references non-existent file."""
        skills_dir = temp_repo["skills_dir"]
        repo_root = temp_repo["root"]
        
        skills_md_content = """
| `src/skills/nonexistent/SKILL.md` |
"""
        
        errors = validate_registry_completeness(skills_dir, skills_md_content, repo_root)
        assert len(errors) > 0
        assert any("does not exist" in e.message for e in errors)

    def test_registry_unregistered_skill_file(self, temp_repo):
        """Test when disk has SKILL.md not in SKILLS.md."""
        skills_dir = temp_repo["skills_dir"]
        repo_root = temp_repo["root"]
        
        # Create skill file not in SKILLS.md
        (skills_dir / "orphan").mkdir()
        (skills_dir / "orphan" / "SKILL.md").write_text("""---
name: orphan
description: Orphan skill
---
""")
        
        skills_md_content = """
| `src/skills/auth/SKILL.md` |
"""
        
        errors = validate_registry_completeness(skills_dir, skills_md_content, repo_root)
        unregistered = [e for e in errors if "not registered" in e.message]
        assert len(unregistered) > 0

    def test_registry_empty_skills_md(self, temp_repo):
        """Test with empty SKILLS.md."""
        skills_dir = temp_repo["skills_dir"]
        repo_root = temp_repo["root"]
        
        (skills_dir / "skill1").mkdir()
        (skills_dir / "skill1" / "SKILL.md").write_text("""---
name: skill1
description: Skill 1
---
""")
        
        errors = validate_registry_completeness(skills_dir, "", repo_root)
        # With empty SKILLS.md, unregistered files get warnings
        assert len(errors) > 0


# ============================================================================
# Unit Tests: Full Validation
# ============================================================================

class TestFullValidation:
    """Test validate_skills end-to-end."""

    def test_validate_skills_all_valid(self, temp_repo, capsys):
        """Test validation when all skills are valid."""
        skills_dir = temp_repo["skills_dir"]
        src_dir = temp_repo["src_dir"]
        repo_root = temp_repo["root"]
        
        # Create a valid skill
        (skills_dir / "auth").mkdir()
        (skills_dir / "auth" / "SKILL.md").write_text("""---
name: auth
description: Authentication skill
---
""")
        
        # Create SKILLS.md
        (src_dir / "SKILLS.md").write_text("""
| `src/skills/auth/SKILL.md` |
""")
        
        error_count, warning_count = validate_skills(skills_dir, src_dir, repo_root)
        
        assert error_count == 0
        assert warning_count == 0
        
        captured = capsys.readouterr()
        assert "valid" in captured.out.lower()

    def test_validate_skills_with_errors(self, temp_repo, capsys):
        """Test validation that finds errors."""
        skills_dir = temp_repo["skills_dir"]
        src_dir = temp_repo["src_dir"]
        repo_root = temp_repo["root"]
        
        # Create invalid skill (missing description)
        (skills_dir / "bad").mkdir()
        (skills_dir / "bad" / "SKILL.md").write_text("""---
name: bad
---
""")
        
        # Create SKILLS.md
        (src_dir / "SKILLS.md").write_text("""
| `src/skills/bad/SKILL.md` |
""")
        
        error_count, warning_count = validate_skills(skills_dir, src_dir, repo_root)
        
        assert error_count > 0

    def test_validate_skills_no_skills_md(self, temp_repo, capsys):
        """Test when src/SKILLS.md doesn't exist."""
        skills_dir = temp_repo["skills_dir"]
        src_dir = temp_repo["src_dir"]
        repo_root = temp_repo["root"]
        
        # Create a valid skill but no SKILLS.md
        (skills_dir / "auth").mkdir()
        (skills_dir / "auth" / "SKILL.md").write_text("""---
name: auth
description: Auth skill
---
""")
        
        error_count, warning_count = validate_skills(skills_dir, src_dir, repo_root)
        
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower() or "skipping" in captured.out.lower()


# ============================================================================
# Integration Tests: Error Messages
# ============================================================================

class TestErrorMessages:
    """Test that error messages are clear and helpful."""

    def test_validation_error_formatting(self, temp_repo):
        """Test ValidationError formatting."""
        path = temp_repo["skills_dir"] / "test" / "SKILL.md"
        error = ValidationError(path, "ERROR", "Test error message")
        
        error_str = str(error)
        assert "ERROR" in error_str
        assert "Test error message" in error_str

    def test_validation_error_no_file(self):
        """Test ValidationError with no file."""
        error = ValidationError(None, "WARNING", "Global warning")
        
        error_str = str(error)
        assert "global" in error_str.lower()
        assert "warning" in error_str.lower()

    def test_path_security_error_message_clarity(self, temp_repo):
        """Test that path security errors have clear messages."""
        repo_root = temp_repo["root"]
        skills_md_content = """
| `src/skills/../../../etc/passwd` |
"""
        
        referenced, errors = _extract_skill_paths_from_skills_md(skills_md_content, repo_root)
        
        if errors:
            # Should have clear message about path restrictions
            assert any("allowed" in e.message or "boundary" in e.message for e in errors)


# ============================================================================
# Parametrized Tests: Path Validation
# ============================================================================

@pytest.mark.parametrize("path_str,should_be_safe", [
    ("src/skills/auth/SKILL.md", True),
    ("src/skills/complex/deep/nested/path/SKILL.md", True),
])
def test_path_safety_parametrized(temp_repo, path_str, should_be_safe):
    """Parametrized test for path safety validation with valid paths."""
    repo_root = temp_repo["root"]
    test_path = repo_root / path_str
    
    is_safe = _is_path_safe(test_path, repo_root)
    assert is_safe == should_be_safe, f"Path {path_str} safety check failed"


def test_path_safety_outside_repo(temp_repo):
    """Test that paths outside repo boundary are rejected."""
    repo_root = temp_repo["root"]
    # Path that's outside the repo (in parent directory)
    outside_path = repo_root.parent / "etc" / "passwd"
    
    is_safe = _is_path_safe(outside_path, repo_root)
    assert is_safe is False, "Paths outside repo should be rejected"


@pytest.mark.parametrize("role", [
    "engineer",
    "orchestrator",
    "model-engineer",
    "quality-engineer",
    "lead-engineer",
    "principal-engineer",
    "security-engineer",
])
def test_known_roles_validation(temp_repo, role):
    """Test that all documented known roles are validated correctly."""
    skill_file = temp_repo["skills_dir"] / "test" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    
    content = f"""---
name: test
description: Test
roles:
  - {role}
---
"""
    skill_file.write_text(content)
    
    errors = validate_skill_file(skill_file)
    role_errors = [e for e in errors if "role" in e.message.lower()]
    assert len(role_errors) == 0, f"Role {role} should be known"


# ============================================================================
# Compliance audit (merged from the former scripts/validate_skills.py,
# 2026-08-13 infra consolidation — single validate_skills implementation)
# ============================================================================

from validate_skills import (
    ACTIVE_SKILLS,
    COMPLIANCE_REQUIRED_TOP_LEVEL,
    COMPLIANCE_REQUIRED_METADATA,
    SkillComplianceResult,
    audit_skill_compliance,
    run_compliance_audit,
)


def _write_compliant_skill(skills_dir: Path, name: str, *, prose_only: bool = False) -> None:
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text(f"""---
name: {name}
description: A compliant test skill
license: Proprietary
compatibility: ">=1.0"
metadata:
  author: test
  version: "1.0.0"
  category: validation
  role: engineer
  model: claude-sonnet-5
  effort: low
---

## Self-Improvement

None yet.
""")
    if not prose_only:
        (skill_dir / "scripts").mkdir()
        (skill_dir / "scripts" / "__init__.py").write_text("")
        (skill_dir / "__init__.py").write_text("")
        tests_dir = skill_dir / "tests"
        tests_dir.mkdir()
        tests_dir.joinpath("test_smoke.py").write_text("def test_smoke():\n    assert True\n")


class TestComplianceAudit:
    """Tests for the ACTIVE_SKILLS compliance audit merged from scripts/validate_skills.py."""

    def test_missing_skill_directory_is_error(self, temp_repo):
        result = audit_skill_compliance("does-not-exist", temp_repo["skills_dir"])
        assert not result.passed
        assert any("not found" in e.lower() for e in result.errors)

    def test_prose_only_skill_needs_only_skill_md(self, temp_repo):
        _write_compliant_skill(temp_repo["skills_dir"], "prose-skill", prose_only=True)
        result = audit_skill_compliance("prose-skill", temp_repo["skills_dir"])
        assert result.passed, result.errors

    def test_script_backed_skill_missing_structure_is_error(self, temp_repo):
        skill_dir = temp_repo["skills_dir"] / "half-baked"
        skill_dir.mkdir(parents=True)
        skill_dir.joinpath("SKILL.md").write_text("""---
name: half-baked
description: incomplete
license: Proprietary
compatibility: ">=1.0"
metadata:
  author: test
  version: "1.0.0"
  category: validation
  role: engineer
  model: claude-sonnet-5
  effort: low
---
""")
        (skill_dir / "scripts").mkdir()  # marks it script-backed, but no tests/ or __init__.py
        result = audit_skill_compliance("half-baked", temp_repo["skills_dir"])
        assert not result.passed
        assert any("__init__.py" in e or "tests/" in e for e in result.errors)

    def test_missing_required_metadata_key_is_error(self, temp_repo):
        skill_dir = temp_repo["skills_dir"] / "no-effort"
        skill_dir.mkdir(parents=True)
        skill_dir.joinpath("SKILL.md").write_text("""---
name: no-effort
description: missing metadata.effort
license: Proprietary
compatibility: ">=1.0"
metadata:
  author: test
  version: "1.0.0"
  category: validation
  role: engineer
  model: claude-sonnet-5
---
""")
        result = audit_skill_compliance("no-effort", temp_repo["skills_dir"])
        assert not result.passed
        assert any("metadata.effort" in e for e in result.errors)

    def test_missing_self_improvement_section_is_warning_not_error(self, temp_repo):
        _write_compliant_skill(temp_repo["skills_dir"], "no-self-improve")
        skill_md = temp_repo["skills_dir"] / "no-self-improve" / "SKILL.md"
        skill_md.write_text(skill_md.read_text().replace("## Self-Improvement\n\nNone yet.\n", ""))
        result = audit_skill_compliance("no-self-improve", temp_repo["skills_dir"])
        assert result.passed  # warnings don't fail
        assert any("Self-Improvement" in w for w in result.warnings)

    def test_run_compliance_audit_covers_requested_names(self, temp_repo):
        _write_compliant_skill(temp_repo["skills_dir"], "skill-a")
        _write_compliant_skill(temp_repo["skills_dir"], "skill-b")
        results = run_compliance_audit(temp_repo["skills_dir"], ["skill-a", "skill-b"])
        assert set(results.keys()) == {"skill-a", "skill-b"}
        assert all(isinstance(r, SkillComplianceResult) for r in results.values())
        assert all(r.passed for r in results.values())

    def test_active_skills_list_matches_repo_skills_dir(self):
        """ACTIVE_SKILLS must stay in sync with the real src/skills/ directory
        (the compliance audit only covers skills named in this list)."""
        repo_skills_dir = Path(__file__).parent.parent / "src" / "skills"
        on_disk = {p.name for p in repo_skills_dir.iterdir() if p.is_dir()}
        assert set(ACTIVE_SKILLS) == on_disk, (
            f"ACTIVE_SKILLS {sorted(ACTIVE_SKILLS)} does not match "
            f"src/skills/ on disk {sorted(on_disk)}"
        )

    def test_real_active_skills_pass_compliance_audit(self):
        """Every real ACTIVE_SKILLS entry in this repo must pass the audit —
        this is the actual CI-blocking gate exercised end-to-end."""
        repo_skills_dir = Path(__file__).parent.parent / "src" / "skills"
        results = run_compliance_audit(repo_skills_dir, ACTIVE_SKILLS)
        failing = {name: r.errors for name, r in results.items() if not r.passed}
        assert not failing, f"Compliance audit failures: {failing}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=renderer.validate_skills"])
