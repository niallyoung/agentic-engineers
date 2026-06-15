"""
Skill Renderer for the Claude Code harness.

Loads skill definitions from ``dist/claude/skills/`` (the rendered output
produced by ``make render-claude``) and validates that each skill is ready
to be surfaced in the Claude Code context.

The renderer is intentionally lightweight: it does NOT execute skills — it
confirms that the SKILL.md frontmatter is present, parses cleanly, and that
the required metadata fields are populated.  This makes it fast and suitable
for startup-time health checks.

Usage::

    from src.harnesses.claude_code.skill_renderer import SkillRenderer

    renderer = SkillRenderer()
    output = renderer.render("agent-creator")
    print(output.success, output.metadata)

    report = renderer.render_all()
    success_rate = report["success_rate"]
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# ---------------------------------------------------------------------------
# Core skill catalogue — the 14 skills expected in the Claude Code harness.
# Includes the 13 skills from the baseline catalogue plus doc-quality-monitor
# which shipped in a subsequent release.
# ---------------------------------------------------------------------------

CORE_SKILLS: List[str] = [
    "agent-creator",
    "consistency-checker",
    "cost-aggregation",
    "cost-budgeting",
    "doc-quality-monitor",
    "file-sync",
    "model-engineer",
    "model-selection",
    "protocol-validator",
    "queue-management",
    "spec-management",
    "spec-validator",
    "usage-tracking",
    "workflow-review",
]

# Required top-level or nested metadata fields for a skill to be considered
# renderable in the Claude Code context.
REQUIRED_METADATA_FIELDS: List[str] = ["name", "description"]


@dataclass
class SkillRenderOutput:
    """Result of rendering a single skill."""

    skill_name: str
    success: bool
    render_time_ms: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def is_accessible(self) -> bool:
        """Return True when the skill rendered without errors."""
        return self.success


class SkillRenderer:
    """Renders skills from the Claude Code harness output directory.

    Parameters
    ----------
    skills_root:
        Path to the rendered skills directory.  Defaults to
        ``<repo_root>/dist/claude/skills``.
    repo_root:
        Repository root used to resolve the default ``skills_root``.
        Defaults to the directory three levels above this file
        (``src/harnesses/claude_code/`` -> repo root).
    """

    def __init__(
        self,
        skills_root: Optional[Path] = None,
        repo_root: Optional[Path] = None,
    ) -> None:
        if repo_root is None:
            # src/harnesses/claude_code/__init__.py -> src/harnesses/claude_code
            # -> src/harnesses -> src -> repo_root
            repo_root = Path(__file__).resolve().parents[3]
        self._repo_root = repo_root

        if skills_root is None:
            skills_root = repo_root / "dist" / "claude" / "skills"
        self.skills_root = skills_root

        self._cache: Dict[str, SkillRenderOutput] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, skill_name: str, use_cache: bool = True) -> SkillRenderOutput:
        """Render a single skill and return the result.

        Args:
            skill_name: Directory name of the skill under ``skills_root``.
            use_cache: Return the cached result if available.

        Returns:
            :class:`SkillRenderOutput` describing success or failure.
        """
        if use_cache and skill_name in self._cache:
            return self._cache[skill_name]

        t_start = time.monotonic()
        result = self._render_skill(skill_name)
        result.render_time_ms = (time.monotonic() - t_start) * 1000

        self._cache[skill_name] = result
        return result

    def render_all(
        self,
        skill_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Render all skills and return an aggregate report.

        Args:
            skill_names: Skills to render.  Defaults to
                :data:`CORE_SKILLS`.

        Returns:
            Dictionary with ``skills``, ``total``, ``passed``, ``failed``,
            ``success_rate``, and ``accessible_skills`` keys.
        """
        if skill_names is None:
            skill_names = CORE_SKILLS

        results: Dict[str, SkillRenderOutput] = {}
        for name in skill_names:
            results[name] = self.render(name)

        total = len(results)
        passed = sum(1 for r in results.values() if r.success)
        failed = total - passed

        return {
            "skills": results,
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": passed / total if total else 0.0,
            "accessible_skills": passed,
        }

    def discover_available_skills(self) -> List[str]:
        """Return all skill directory names found under ``skills_root``.

        Only directories (not starting with ``.``) that contain a
        ``SKILL.md`` file are returned.
        """
        if not self.skills_root.exists():
            return []

        skills = []
        for item in sorted(self.skills_root.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                if (item / "SKILL.md").exists():
                    skills.append(item.name)
        return skills

    def verify_core_catalogue(self) -> Dict[str, Any]:
        """Verify that all :data:`CORE_SKILLS` are renderable.

        Returns:
            Report dict with ``all_core_skills_present`` boolean and a
            per-skill breakdown.
        """
        report = self.render_all(CORE_SKILLS)
        all_pass = report["success_rate"] == 1.0
        return {
            **report,
            "all_core_skills_present": all_pass,
            "core_skills_checked": len(CORE_SKILLS),
        }

    def clear_cache(self) -> None:
        """Clear the in-memory render cache."""
        self._cache.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _render_skill(self, skill_name: str) -> SkillRenderOutput:
        """Perform the actual render for a single skill."""
        skill_dir = self.skills_root / skill_name
        skill_md = skill_dir / "SKILL.md"

        if not skill_dir.exists():
            return SkillRenderOutput(
                skill_name=skill_name,
                success=False,
                error=f"Skill directory not found: {skill_dir}",
            )

        if not skill_md.exists():
            return SkillRenderOutput(
                skill_name=skill_name,
                success=False,
                error=f"SKILL.md not found in {skill_dir}",
            )

        # Parse frontmatter
        try:
            content = skill_md.read_text(encoding="utf-8")
        except OSError as exc:
            return SkillRenderOutput(
                skill_name=skill_name,
                success=False,
                error=f"Cannot read SKILL.md: {exc}",
            )

        metadata, parse_error = self._parse_frontmatter(content)
        if parse_error or metadata is None:
            return SkillRenderOutput(
                skill_name=skill_name,
                success=False,
                error=parse_error or "Failed to parse frontmatter",
            )

        # Validate required fields
        missing = self._check_required_fields(metadata)
        if missing:
            return SkillRenderOutput(
                skill_name=skill_name,
                success=False,
                metadata=metadata,
                error=f"Missing required metadata fields: {', '.join(missing)}",
            )

        return SkillRenderOutput(
            skill_name=skill_name,
            success=True,
            metadata=metadata,
        )

    def _parse_frontmatter(
        self, content: str
    ) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Extract and parse YAML frontmatter from a SKILL.md string.

        Returns:
            Tuple of (metadata_dict_or_None, error_message_or_None).
        """
        if not content.startswith("---"):
            return None, "SKILL.md does not begin with '---'"

        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not match:
            return None, "Could not locate closing '---' in SKILL.md"

        raw_yaml = match.group(1)
        try:
            data: Dict[str, Any] = yaml.safe_load(raw_yaml) or {}
        except yaml.YAMLError as exc:
            return None, f"YAML parse error: {exc}"

        # Flatten nested ``metadata:`` block if present (legacy format)
        if "metadata" in data and isinstance(data["metadata"], dict):
            nested = data.pop("metadata")
            for k, v in nested.items():
                data.setdefault(k, v)

        return data, None

    def _check_required_fields(
        self, metadata: Dict[str, Any]
    ) -> List[str]:
        """Return list of required field names that are absent or empty."""
        missing = []
        for field in REQUIRED_METADATA_FIELDS:
            value = metadata.get(field)
            if not value:
                missing.append(field)
        return missing
