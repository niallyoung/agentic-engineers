"""
Regression tests for Claude Code harness SkillRenderer.

AC2: All 14 core skills render correctly in the Claude Code skill catalogue.
AC5: 10+ regression tests (this file contributes 5 of them).
AC6: Zero regressions in existing tests.

The fixture ``skills_root`` points at ``dist/claude/skills`` — the rendered
output from ``make render-claude``.  CI runs the render step before running
tests, so this path is always populated on CI and on dev machines after
``make render-claude``.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator

import pytest

from src.harnesses.claude_code.skill_renderer import (
    CORE_SKILLS,
    SkillRenderOutput,
    SkillRenderer,
)

# Repository root: tests/harnesses/claude_code/ -> tests/harnesses -> tests -> repo
REPO_ROOT = Path(__file__).resolve().parents[3]
DIST_SKILLS_ROOT = REPO_ROOT / "dist" / "claude" / "skills"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def renderer() -> SkillRenderer:
    """SkillRenderer pointed at the real dist/claude/skills directory."""
    return SkillRenderer(skills_root=DIST_SKILLS_ROOT)


@pytest.fixture(scope="module")
def full_report(renderer: SkillRenderer) -> dict:
    """Pre-computed render_all() result for all CORE_SKILLS."""
    return renderer.render_all()


@pytest.fixture()
def tmp_skills_root() -> Generator[Path, None, None]:
    """Temporary directory with a valid minimal skill structure."""
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Create a valid skill
        skill_dir = root / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test\n",
            encoding="utf-8",
        )
        yield root


# ---------------------------------------------------------------------------
# AC2: Core skill catalogue renders correctly (>= 14 skills, 100% success)
# ---------------------------------------------------------------------------


class TestCoreSkillCatalogue:
    """AC2: All 14 core skills render correctly in the Claude Code catalogue."""

    def test_core_skills_list_has_14_entries(self) -> None:
        """CORE_SKILLS constant must list exactly 14 skills."""
        assert len(CORE_SKILLS) == 14, (
            f"Expected 14 core skills, got {len(CORE_SKILLS)}: {CORE_SKILLS}"
        )

    def test_render_all_returns_dict(self, full_report: dict) -> None:
        """render_all() must return a dictionary."""
        assert isinstance(full_report, dict)

    def test_render_all_covers_all_core_skills(self, full_report: dict) -> None:
        """render_all() must include a result for every CORE_SKILLS entry."""
        skills_dict = full_report["skills"]
        for skill_name in CORE_SKILLS:
            assert skill_name in skills_dict, (
                f"Missing core skill in render report: {skill_name}"
            )

    def test_all_core_skills_succeed(self, full_report: dict) -> None:
        """Every core skill must render successfully (AC2)."""
        skills_dict = full_report["skills"]
        failures = [
            name
            for name, result in skills_dict.items()
            if not result.success
        ]
        assert not failures, (
            f"Core skills failed to render: {failures}\n"
            + "\n".join(
                f"  {n}: {skills_dict[n].error}" for n in failures
            )
        )

    def test_render_success_rate_is_100_percent(self, full_report: dict) -> None:
        """Success rate for core skills must be 1.0 (100%)."""
        assert full_report["success_rate"] == 1.0, (
            f"Expected 100% success rate, got {full_report['success_rate']:.0%}. "
            f"Passed {full_report['passed']}/{full_report['total']}."
        )

    def test_verify_core_catalogue_returns_all_present(
        self, renderer: SkillRenderer
    ) -> None:
        """verify_core_catalogue() helper must report all_core_skills_present=True."""
        report = renderer.verify_core_catalogue()
        assert report["all_core_skills_present"] is True, (
            f"Core catalogue verification failed: {report}"
        )

    @pytest.mark.parametrize("skill_name", CORE_SKILLS)
    def test_individual_skill_renders_successfully(
        self, renderer: SkillRenderer, skill_name: str
    ) -> None:
        """Each individual core skill must render without errors."""
        result = renderer.render(skill_name)
        assert result.success is True, (
            f"Skill '{skill_name}' failed to render: {result.error}"
        )
        assert result.error is None

    @pytest.mark.parametrize("skill_name", CORE_SKILLS)
    def test_individual_skill_has_metadata(
        self, renderer: SkillRenderer, skill_name: str
    ) -> None:
        """Each successfully rendered skill must have non-empty metadata."""
        result = renderer.render(skill_name)
        assert result.metadata is not None
        assert isinstance(result.metadata, dict)
        assert len(result.metadata) > 0


# ---------------------------------------------------------------------------
# Unit tests for SkillRenderer mechanics
# ---------------------------------------------------------------------------


class TestSkillRendererUnit:
    """Unit tests for SkillRenderer — do not depend on dist/."""

    def test_render_output_dataclass_fields(self) -> None:
        """SkillRenderOutput has the expected fields."""
        out = SkillRenderOutput(skill_name="foo", success=True)
        assert out.skill_name == "foo"
        assert out.success is True
        assert out.render_time_ms == 0.0
        assert out.metadata is None
        assert out.error is None

    def test_is_accessible_matches_success(self) -> None:
        """SkillRenderOutput.is_accessible is an alias for success."""
        ok = SkillRenderOutput(skill_name="foo", success=True)
        assert ok.is_accessible is True
        bad = SkillRenderOutput(skill_name="foo", success=False)
        assert bad.is_accessible is False

    def test_renderer_initialises_with_default_path(self) -> None:
        """SkillRenderer resolves a default skills_root relative to the repo."""
        renderer = SkillRenderer()
        assert "dist" in str(renderer.skills_root)
        assert "claude" in str(renderer.skills_root)

    def test_renderer_accepts_custom_skills_root(self, tmp_path: Path) -> None:
        """SkillRenderer accepts an explicit skills_root."""
        renderer = SkillRenderer(skills_root=tmp_path)
        assert renderer.skills_root == tmp_path

    def test_render_nonexistent_skill_fails(self, tmp_path: Path) -> None:
        """Rendering a skill that doesn't exist must return success=False."""
        renderer = SkillRenderer(skills_root=tmp_path)
        result = renderer.render("no-such-skill")
        assert result.success is False
        assert result.error is not None

    def test_render_skill_missing_skill_md_fails(self, tmp_path: Path) -> None:
        """A directory without SKILL.md must fail gracefully."""
        skill_dir = tmp_path / "empty-skill"
        skill_dir.mkdir()
        renderer = SkillRenderer(skills_root=tmp_path)
        result = renderer.render("empty-skill")
        assert result.success is False
        assert "SKILL.md" in (result.error or "")

    def test_render_valid_minimal_skill(self, tmp_skills_root: Path) -> None:
        """A minimal valid SKILL.md renders successfully."""
        renderer = SkillRenderer(skills_root=tmp_skills_root)
        result = renderer.render("test-skill")
        assert result.success is True
        assert result.metadata is not None
        assert result.metadata.get("name") == "test-skill"

    def test_render_skill_returns_render_time(self, tmp_skills_root: Path) -> None:
        """Rendered result includes a non-negative render_time_ms."""
        renderer = SkillRenderer(skills_root=tmp_skills_root)
        result = renderer.render("test-skill")
        assert result.render_time_ms >= 0

    def test_render_uses_cache_on_second_call(self, tmp_skills_root: Path) -> None:
        """Second call with use_cache=True returns the cached object."""
        renderer = SkillRenderer(skills_root=tmp_skills_root)
        r1 = renderer.render("test-skill")
        r2 = renderer.render("test-skill", use_cache=True)
        assert r1 is r2  # Same object from cache

    def test_render_bypasses_cache_when_disabled(
        self, tmp_skills_root: Path
    ) -> None:
        """use_cache=False forces a fresh render."""
        renderer = SkillRenderer(skills_root=tmp_skills_root)
        r1 = renderer.render("test-skill")
        r2 = renderer.render("test-skill", use_cache=False)
        # Different objects (fresh read) but same logical content
        assert r1 is not r2
        assert r1.skill_name == r2.skill_name
        assert r1.success == r2.success

    def test_clear_cache_empties_cache(self, tmp_skills_root: Path) -> None:
        """clear_cache() makes subsequent renders rebuild from disk."""
        renderer = SkillRenderer(skills_root=tmp_skills_root)
        r1 = renderer.render("test-skill")
        renderer.clear_cache()
        r2 = renderer.render("test-skill")
        assert r1 is not r2

    def test_render_skill_missing_required_name_fails(
        self, tmp_path: Path
    ) -> None:
        """SKILL.md without 'name' field renders with failure."""
        skill_dir = tmp_path / "no-name"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\ndescription: A skill without a name\n---\n",
            encoding="utf-8",
        )
        renderer = SkillRenderer(skills_root=tmp_path)
        result = renderer.render("no-name")
        assert result.success is False
        assert "name" in (result.error or "").lower()

    def test_render_skill_missing_required_description_fails(
        self, tmp_path: Path
    ) -> None:
        """SKILL.md without 'description' field renders with failure."""
        skill_dir = tmp_path / "no-desc"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: no-desc\n---\n",
            encoding="utf-8",
        )
        renderer = SkillRenderer(skills_root=tmp_path)
        result = renderer.render("no-desc")
        assert result.success is False

    def test_render_skill_with_nested_metadata_block(
        self, tmp_path: Path
    ) -> None:
        """Nested ``metadata:`` block is flattened during render."""
        skill_dir = tmp_path / "nested-meta"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: nested-meta\ndescription: test\n"
            "metadata:\n  version: '2.0'\n  category: orchestration\n---\n",
            encoding="utf-8",
        )
        renderer = SkillRenderer(skills_root=tmp_path)
        result = renderer.render("nested-meta")
        assert result.success is True
        # Nested fields should be promoted to top level
        assert result.metadata is not None
        assert result.metadata.get("version") == "2.0"

    def test_render_all_empty_root_returns_zero(self, tmp_path: Path) -> None:
        """render_all() with no skills returns success_rate=0."""
        renderer = SkillRenderer(skills_root=tmp_path)
        report = renderer.render_all(skill_names=["no-such-skill"])
        assert report["passed"] == 0
        assert report["failed"] == 1
        assert report["success_rate"] == 0.0

    def test_discover_available_skills_finds_skills(
        self, tmp_skills_root: Path
    ) -> None:
        """discover_available_skills() lists directories with SKILL.md."""
        renderer = SkillRenderer(skills_root=tmp_skills_root)
        found = renderer.discover_available_skills()
        assert "test-skill" in found

    def test_discover_available_skills_empty_dir(self, tmp_path: Path) -> None:
        """discover_available_skills() returns [] when skills_root has no skills."""
        renderer = SkillRenderer(skills_root=tmp_path)
        found = renderer.discover_available_skills()
        assert found == []

    def test_discover_available_skills_nonexistent_root(
        self, tmp_path: Path
    ) -> None:
        """discover_available_skills() returns [] when skills_root doesn't exist."""
        renderer = SkillRenderer(skills_root=tmp_path / "does-not-exist")
        found = renderer.discover_available_skills()
        assert found == []

    def test_render_invalid_yaml_frontmatter_fails(
        self, tmp_path: Path
    ) -> None:
        """Invalid YAML in frontmatter results in success=False."""
        skill_dir = tmp_path / "bad-yaml"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: bad-yaml\n  bad indent: [unclosed\n---\n",
            encoding="utf-8",
        )
        renderer = SkillRenderer(skills_root=tmp_path)
        result = renderer.render("bad-yaml")
        assert result.success is False
        assert result.error is not None

    def test_render_no_frontmatter_fails(self, tmp_path: Path) -> None:
        """SKILL.md without frontmatter markers fails gracefully."""
        skill_dir = tmp_path / "no-frontmatter"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "# Just a heading\n\nNo frontmatter here.\n",
            encoding="utf-8",
        )
        renderer = SkillRenderer(skills_root=tmp_path)
        result = renderer.render("no-frontmatter")
        assert result.success is False
