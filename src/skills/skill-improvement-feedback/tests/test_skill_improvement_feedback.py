"""Tests for skill-improvement-feedback meta-skill."""

from pathlib import Path


def test_skill_md_exists():
    """Assert SKILL.md exists."""
    skill_dir = Path(__file__).parent.parent
    skill_md = skill_dir / "SKILL.md"
    assert skill_md.exists(), f"SKILL.md not found at {skill_md}"


def test_skill_md_contains_self_improvement_section():
    """Assert SKILL.md contains ## Self-Improvement section."""
    skill_dir = Path(__file__).parent.parent
    skill_md = skill_dir / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    assert "## Self-Improvement" in content, "## Self-Improvement section not found in SKILL.md"


def test_yaml_example_in_skill_md():
    """Assert SKILL.md example block includes skill_feedback YAML example."""
    skill_dir = Path(__file__).parent.parent
    skill_md = skill_dir / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    assert "skill_feedback:" in content, "skill_feedback: not found in SKILL.md"
    assert "effectiveness_score:" in content, "effectiveness_score not found in SKILL.md"
