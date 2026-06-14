"""
Tests for --type skill path in agent-creator (Wave 3 consolidation).

After merging skill-creator into agent-creator, the --type skill flag
must scaffold a valid agentskills.io-spec skill directory structure.

Gate: 3 new --type skill tests green before deprecating skill-creator.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts dir to path so we can import agent_creator directly
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from agent_creator import (
    CreationResult,
    CreationStatus,
    SkillConfig,
    SkillScaffoldGenerator,
    create_skill,
)


class TestSkillTypeFlag:
    """Tests for --type skill (SkillConfig + create_skill) path."""

    def test_skill_scaffold_creates_skill_md(self, tmp_path: Path) -> None:
        """create_skill must produce a SKILL.md with valid frontmatter in the output dir."""
        config = SkillConfig(
            name="my-test-skill",
            description="A test skill for unit testing.",
            category="utility",
        )
        result = create_skill(config, output_root=tmp_path)
        assert result.status == CreationStatus.SUCCESS, f"Expected SUCCESS, got {result.status}: {result.errors}"
        skill_md = tmp_path / "my-test-skill" / "SKILL.md"
        assert skill_md.exists(), "SKILL.md was not created"
        content = skill_md.read_text()
        assert "name: my-test-skill" in content
        assert "---" in content  # frontmatter delimiters present

    def test_skill_scaffold_creates_test_file(self, tmp_path: Path) -> None:
        """create_skill must create a tests/test_<skill>.py scaffold file."""
        config = SkillConfig(name="another-skill", description="Another skill.")
        result = create_skill(config, output_root=tmp_path)
        assert result.status == CreationStatus.SUCCESS
        test_file = tmp_path / "another-skill" / "tests" / "test_another_skill.py"
        assert test_file.exists(), f"Test scaffold not found at {test_file}"
        # The test scaffold should contain at least one test function
        content = test_file.read_text()
        assert "def test_" in content

    def test_skill_dry_run_returns_deliverables_without_writing(self, tmp_path: Path) -> None:
        """create_skill with dry_run=True must return DRY_RUN status and not write files."""
        config = SkillConfig(name="dry-run-skill", description="Dry run only.")
        result = create_skill(config, output_root=tmp_path, dry_run=True)
        assert result.status == CreationStatus.DRY_RUN, f"Expected DRY_RUN, got {result.status}"
        # Deliverables listed but no files written
        assert len(result.deliverables) > 0, "Deliverables should be planned even in dry run"
        skill_dir = tmp_path / "dry-run-skill"
        assert not skill_dir.exists(), "Skill directory should NOT be created in dry_run mode"

    def test_skill_config_invalid_name_fails(self, tmp_path: Path) -> None:
        """create_skill with an invalid name must return FAILED with errors."""
        config = SkillConfig(name="INVALID_NAME!", description="Bad name.")
        result = create_skill(config, output_root=tmp_path)
        assert result.status == CreationStatus.FAILED
        assert len(result.errors) > 0

    def test_skill_scaffold_generator_plan_files_returns_four_items(self) -> None:
        """SkillScaffoldGenerator.plan_files must return exactly 4 file paths."""
        gen = SkillScaffoldGenerator()
        config = SkillConfig(name="test-skill", description="Testing")
        from pathlib import Path as P
        files = gen.plan_files(config, P("/tmp/test-skill"))
        assert len(files) == 4, f"Expected 4 planned files, got {len(files)}"

    def test_skill_scaffold_generator_skill_md_contains_directory_structure(self) -> None:
        """Generated SKILL.md must include the directory structure section."""
        gen = SkillScaffoldGenerator()
        config = SkillConfig(name="my-skill", description="My skill description.")
        content = gen.generate_skill_md(config)
        assert "Directory Structure" in content
        assert "SKILL.md" in content
        assert "scripts/" in content
        assert "tests/" in content
