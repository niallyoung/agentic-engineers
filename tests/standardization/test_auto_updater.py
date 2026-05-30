"""
Unit tests for the automated skill updater.

Tests:
- Frontmatter reconstruction
- Section extraction and addition
- Preservation of existing content
- Update report generation
- Batch updates
"""

import pytest
from pathlib import Path
import tempfile
import yaml
from src.standardization.auto_updater import SkillAutoUpdater


@pytest.fixture
def temp_skill_dir():
    """Create a temporary skill directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def minimal_skill_content():
    """Minimal skill content."""
    return """---
name: minimal-skill
description: A minimal test skill.
---

## Overview

This is the overview.

## Invocation

This is the invocation.
"""


@pytest.fixture
def skill_without_metadata():
    """Skill without metadata section."""
    return """---
name: no-metadata-skill
description: A skill without metadata.
---

## Overview

Overview content.

## Invocation

Invocation content.
"""


@pytest.fixture
def skill_with_existing_sections():
    """Skill with many existing sections."""
    return """---
name: rich-skill
description: A skill with rich content.
---

## Overview

Rich overview.

## Invocation

Rich invocation details.

## Configuration

Configuration options.

## Examples

Example usage.
"""


class TestFrontmatterReconstruction:
    """Tests for frontmatter reconstruction."""

    def test_basic_frontmatter_reconstruction(self):
        """Test reconstruction of basic frontmatter."""
        updater = SkillAutoUpdater()

        frontmatter = {
            "name": "test-skill",
            "description": "Test skill description",
            "license": "Proprietary",
            "compatibility": "agentic-engineers framework",
            "metadata": {
                "author": "agentic-engineers",
                "version": "1.0",
                "category": "testing",
                "role": "engineer",
            },
        }

        result = updater._reconstruct_frontmatter(frontmatter)

        assert "---" in result
        assert "name: test-skill" in result
        assert "category: testing" in result
        assert "role: engineer" in result

    def test_frontmatter_with_optional_fields(self):
        """Test reconstruction with optional fields."""
        updater = SkillAutoUpdater()

        frontmatter = {
            "name": "test-skill",
            "description": "Test skill",
            "metadata": {
                "author": "agentic-engineers",
                "version": "1.0",
                "category": "testing",
                "role": "engineer",
                "schedule": "0 18 * * *",
                "tdd_phase": "GREEN",
            },
        }

        result = updater._reconstruct_frontmatter(frontmatter)

        assert "schedule:" in result
        assert "tdd_phase:" in result

    def test_frontmatter_yaml_format(self):
        """Test that reconstructed frontmatter is valid YAML."""
        updater = SkillAutoUpdater()

        frontmatter = {
            "name": "test-skill",
            "description": "Test description",
            "metadata": {
                "author": "agentic-engineers",
                "version": "1.0",
                "category": "testing",
                "role": "engineer",
            },
        }

        result = updater._reconstruct_frontmatter(frontmatter)

        # Extract YAML content (between --- delimiters)
        lines = result.split("\n")
        # Skip first --- and find second ---
        yaml_lines = []
        for i, line in enumerate(lines[1:]):
            if line.startswith("---"):
                break
            yaml_lines.append(line)

        yaml_content = "\n".join(yaml_lines)

        # Should parse without error
        parsed = yaml.safe_load(yaml_content)
        assert parsed["name"] == "test-skill"


class TestSectionExtraction:
    """Tests for markdown section extraction."""

    def test_extract_basic_sections(self):
        """Test extraction of basic sections."""
        updater = SkillAutoUpdater()

        content = """## Overview

Overview content.

## Invocation

Invocation content.

## Configuration

Configuration content.
"""
        sections = updater._extract_sections(content)

        assert "Overview" in sections
        assert "Invocation" in sections
        assert "Configuration" in sections
        assert "Overview content" in sections["Overview"]

    def test_extract_nested_content(self):
        """Test extraction of sections with nested content."""
        updater = SkillAutoUpdater()

        content = """## Overview

Some overview text.

### Subsection

This is nested.

## Invocation

Invocation text.
"""
        sections = updater._extract_sections(content)

        assert "Overview" in sections
        assert "Subsection" in sections["Overview"]

    def test_empty_section_handling(self):
        """Test handling of empty sections."""
        updater = SkillAutoUpdater()

        content = """## Overview

## Invocation

Content here.
"""
        sections = updater._extract_sections(content)

        assert "Overview" in sections
        assert "Invocation" in sections


class TestSkillUpdate:
    """Tests for skill updating."""

    def test_add_missing_metadata(self, temp_skill_dir, skill_without_metadata):
        """Test addition of missing metadata."""
        skill_path = temp_skill_dir / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text(skill_without_metadata)

        updater = SkillAutoUpdater()
        result = updater.update_skill(skill_path)

        assert result is not None
        assert len(result.changes_made) > 0

        # Check that metadata was added
        updated_content = skill_path.read_text()
        updated_frontmatter, _ = updater._parse_frontmatter(updated_content)

        assert updated_frontmatter is not None
        assert "metadata" in updated_frontmatter

    def test_preserve_existing_content(self, temp_skill_dir, skill_with_existing_sections):
        """Test preservation of existing content."""
        skill_path = temp_skill_dir / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text(skill_with_existing_sections)

        updater = SkillAutoUpdater()
        result = updater.update_skill(skill_path)

        assert result is not None

        # Check that original content is preserved
        updated_content = skill_path.read_text()
        assert "Rich overview" in updated_content
        assert "Rich invocation" in updated_content
        assert "Configuration options" in updated_content

    def test_add_missing_sections(self, temp_skill_dir, minimal_skill_content):
        """Test addition of missing sections."""
        skill_path = temp_skill_dir / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text(minimal_skill_content)

        updater = SkillAutoUpdater()
        result = updater.update_skill(skill_path)

        assert result is not None
        assert len(result.sections_added) > 0

        # Check that sections were added
        updated_content = skill_path.read_text()
        sections = updater._extract_sections(updated_content)

        # Should now have additional sections
        assert len(sections) > 2

    def test_update_returns_none_for_missing_file(self, temp_skill_dir):
        """Test that update returns None for missing file."""
        skill_path = temp_skill_dir / "nonexistent" / "SKILL.md"

        updater = SkillAutoUpdater()
        result = updater.update_skill(skill_path)

        assert result is None


class TestBatchUpdates:
    """Tests for batch updating of multiple skills."""

    def test_update_multiple_skills(self, temp_skill_dir):
        """Test updating multiple skills."""
        # Create multiple skills
        for i in range(3):
            skill_path = temp_skill_dir / f"skill-{i}" / "SKILL.md"
            skill_path.parent.mkdir(parents=True)

            content = f"""---
name: skill-{i}
description: Test skill {i}.
---

## Overview

Overview for skill {i}.

## Invocation

Invocation for skill {i}.
"""
            skill_path.write_text(content)

        updater = SkillAutoUpdater()
        results = updater.update_all_skills(temp_skill_dir)

        assert len(results) == 3

    def test_batch_update_report(self, temp_skill_dir):
        """Test batch update report generation."""
        # Create skills
        for i in range(2):
            skill_path = temp_skill_dir / f"skill-{i}" / "SKILL.md"
            skill_path.parent.mkdir(parents=True)

            content = f"""---
name: skill-{i}
description: Test skill {i}.
---

## Overview

Overview.

## Invocation

Invocation.
"""
            skill_path.write_text(content)

        updater = SkillAutoUpdater()
        updater.update_all_skills(temp_skill_dir)
        report = updater.generate_update_report()

        assert report["total_skills_updated"] == 2
        assert report["total_changes_made"] >= 0
        assert "average_changes_per_skill" in report
        assert len(report["skills"]) == 2


class TestContentPreservation:
    """Tests for content preservation during updates."""

    def test_preserve_complex_markdown(self, temp_skill_dir):
        """Test preservation of complex markdown."""
        skill_path = temp_skill_dir / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)

        content = """---
name: complex-skill
description: Skill with complex content.
---

## Overview

- Bullet point 1
- Bullet point 2

```python
def example():
    pass
```

## Invocation

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
"""
        skill_path.write_text(content)

        updater = SkillAutoUpdater()
        result = updater.update_skill(skill_path)

        updated_content = skill_path.read_text()

        # Check preservation
        assert "Bullet point 1" in updated_content
        assert "def example():" in updated_content
        assert "Column 1" in updated_content

    def test_preserve_special_characters(self, temp_skill_dir):
        """Test preservation of special characters."""
        skill_path = temp_skill_dir / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)

        content = """---
name: special-skill
description: Skill with special chars: @#$%^&*()
---

## Overview

Special chars in content: @#$%^&*()

## Invocation

Code: `x & y | z`
"""
        skill_path.write_text(content)

        updater = SkillAutoUpdater()
        result = updater.update_skill(skill_path)

        updated_content = skill_path.read_text()

        # Check that special chars are preserved
        assert "@#$%^&*()" in updated_content
        assert "x & y | z" in updated_content


class TestUpdateTracking:
    """Tests for update tracking."""

    def test_updated_skill_tracking(self, temp_skill_dir, minimal_skill_content):
        """Test tracking of updated skills."""
        skill_path = temp_skill_dir / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text(minimal_skill_content)

        updater = SkillAutoUpdater()
        result = updater.update_skill(skill_path)

        assert result is not None
        assert result.skill_name == "test-skill"
        assert result.skill_path == skill_path
        assert len(result.changes_made) > 0

    def test_changes_tracking(self, temp_skill_dir, skill_without_metadata):
        """Test detailed tracking of changes."""
        skill_path = temp_skill_dir / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text(skill_without_metadata)

        updater = SkillAutoUpdater()
        result = updater.update_skill(skill_path)

        # Should track what was changed
        assert any("metadata" in change.lower() for change in result.changes_made)
        assert len(result.content_before) > 0
        assert len(result.content_after) > 0
