"""Basic import test for spec-validator skill.

Ensures the skill can be imported and basic structure is present.
"""
import pytest


def test_skill_directory_exists():
    """Skill directory should exist."""
    from pathlib import Path
    skill_dir = Path(__file__).parent.parent
    assert skill_dir.exists()
    assert (skill_dir / "SKILL.md").exists()


def test_module_importable():
    """Skill module should be importable."""
    from importlib import import_module
    # Module with dashes requires import_module
    module = import_module("src.skills.spec-validator")
    assert module is not None


def test_scripts_directory_exists():
    """Scripts directory should exist."""
    from pathlib import Path
    scripts_dir = Path(__file__).parent.parent / "scripts"
    assert scripts_dir.exists()
