#!/usr/bin/env python3
from __future__ import annotations

"""validate_skills.py - SKILL.md frontmatter compliance gate (Phase 5.1+).

Validates every active skill in src/skills/ against the canonical template
defined in src/skills/_meta/skill-template/SKILL.md.

Exit codes:
    0 -- All active skills pass validation
    1 -- One or more active skills have compliance failures
    2 -- Configuration / invocation error

Usage:
    python scripts/validate_skills.py
    python scripts/validate_skills.py --strict        # treat warnings as errors
    python scripts/validate_skills.py --json          # machine-readable output
    python scripts/validate_skills.py --skill queue-management  # single skill
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "src" / "skills"

# Skills listed in docs/SKILLS-AVAILABLE.md as active.
# Update this list whenever a skill is added or deprecated.
#
# SPEC-2026-005 framework slimdown, WP-0 (2026-08-11): pruned from 14 to the
# 8 skills that survive the slimdown (principal-engineer design authority:
# task-2026-08-11-framework-slimdown-design HANDBACK). Removed:
# harness-integration-tracker, consistency-checker, workflow-review,
# agent-creator, usage-tracking, file-sync, queue-todo-sync, model-engineer
# (all deleted in a later WP). Added: orchestrator, codex-agent-cleanup
# (both already active but were missing from this list).
ACTIVE_SKILLS: List[str] = [
    "orchestrator",
    "queue-management",
    "queue-query",
    "protocol-validator",
    "spec-validator",
    "spec-management",
    "skill-improvement-feedback",
    "codex-agent-cleanup",
]

# Required top-level frontmatter keys
REQUIRED_TOP_LEVEL: List[str] = [
    "name",
    "description",
    "license",
    "compatibility",
]

# Required metadata sub-keys
REQUIRED_METADATA: List[str] = [
    "author",
    "version",
    "category",
    "role",
    "model",
    "effort",
]

# Required directory structure
REQUIRED_DIRS: List[str] = ["scripts", "tests"]
REQUIRED_FILES: List[str] = ["SKILL.md", "__init__.py"]

# Allowed enum values -- warn (not error) on mismatch for forward-compatibility
ALLOWED_ROLES = {
    "engineer", "senior-engineer", "lead-engineer", "principal-engineer",
    "security-engineer", "quality-engineer", "orchestrator",
}
ALLOWED_EFFORTS = {"low", "medium", "high"}
ALLOWED_CATEGORIES = {
    "orchestration", "validation", "monitoring", "optimization", "observability",
    "scaffolding", "integration", "queue", "metrics", "maintenance",
    "hygiene", "management", "security", "task-management", "meta-skill",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SkillAuditResult:
    skill_name: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    @property
    def status(self) -> str:
        if self.errors:
            return "FAIL"
        if self.warnings:
            return "WARN"
        return "PASS"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _extract_frontmatter(skill_md: Path) -> Optional[str]:
    """Return the raw YAML frontmatter string, or None if not present."""
    try:
        content = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    return m.group(1) if m else None


def _has_key(frontmatter: str, key: str, *, indent: int = 0) -> bool:
    """Return True if ``key:`` appears at the given indent level."""
    prefix = r"^\s{" + str(indent) + r"}" if indent else r"^"
    return bool(re.search(rf"{prefix}{re.escape(key)}:", frontmatter, re.MULTILINE))


def _get_value(frontmatter: str, key: str, *, indent: int = 0) -> Optional[str]:
    """Return the value of ``key: value`` at the given indent, stripped."""
    prefix = r"^\s{" + str(indent) + r"}" if indent else r"^"
    m = re.search(
        rf"{prefix}{re.escape(key)}:\s*(.+)$", frontmatter, re.MULTILINE
    )
    return m.group(1).strip() if m else None


def _check_self_improvement_section(skill_dir: Path) -> Optional[str]:
    """Check if skill's SKILL.md has ## Self-Improvement section.

    Returns a warning string if the section is missing, None if present or
    if SKILL.md doesn't exist.
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None

    try:
        content = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None

    if "## Self-Improvement" not in content:
        return "SKILL.md missing ## Self-Improvement section"

    return None


# ---------------------------------------------------------------------------
# Core audit logic
# ---------------------------------------------------------------------------

def audit_skill(skill_name: str) -> SkillAuditResult:
    result = SkillAuditResult(skill_name=skill_name)
    skill_dir = SKILLS_DIR / skill_name

    # 1. Directory existence
    if not skill_dir.is_dir():
        result.errors.append(f"Directory not found: {skill_dir}")
        return result

    # 2/3/4. Required files/dirs -- a skill with no scripts/ directory is
    # PROSE-ONLY by design (the skills-first direction: a SKILL.md-only dir
    # is valid and does not need scaffolded __init__.py/tests/). A skill that
    # HAS a scripts/ dir is a Python skill and must have the full structure.
    is_prose_only = not (skill_dir / "scripts").is_dir()
    required_files = ["SKILL.md"] if is_prose_only else REQUIRED_FILES
    required_dirs = [] if is_prose_only else REQUIRED_DIRS

    for filename in required_files:
        if not (skill_dir / filename).exists():
            result.errors.append(f"Missing required file: {filename}")

    for dirname in required_dirs:
        if not (skill_dir / dirname).is_dir():
            result.errors.append(f"Missing required directory: {dirname}/")

    if not is_prose_only:
        tests_dir = skill_dir / "tests"
        if tests_dir.is_dir():
            test_files = list(tests_dir.glob("test_*.py"))
            if not test_files:
                result.errors.append("tests/ exists but contains no test_*.py files")

    # 5. SKILL.md frontmatter
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        # Already reported above; skip frontmatter checks
        return result

    fm = _extract_frontmatter(skill_md)
    if fm is None:
        result.errors.append("SKILL.md has no YAML frontmatter (missing --- delimiters)")
        return result

    # 5a. Required top-level keys
    for key in REQUIRED_TOP_LEVEL:
        if not _has_key(fm, key):
            result.errors.append(f"Frontmatter missing required key: {key}")

    # 5b. Required metadata keys
    for key in REQUIRED_METADATA:
        if not _has_key(fm, key, indent=2):
            result.errors.append(f"Frontmatter missing required metadata key: metadata.{key}")

    # 5c. License must be "Proprietary"
    license_val = _get_value(fm, "license")
    if license_val and license_val != "Proprietary":
        result.warnings.append(f"license should be 'Proprietary', got: {license_val!r}")

    # 5d. name must match directory name
    name_val = _get_value(fm, "name")
    if name_val and name_val != skill_name:
        result.errors.append(
            f"name field ({name_val!r}) does not match directory name ({skill_name!r})"
        )

    # 5e. Enum validation (warnings only for forward-compat)
    role_val = _get_value(fm, "role", indent=2)
    if role_val and role_val not in ALLOWED_ROLES:
        result.warnings.append(f"metadata.role {role_val!r} not in allowed set {sorted(ALLOWED_ROLES)}")

    effort_val = _get_value(fm, "effort", indent=2)
    if effort_val and effort_val not in ALLOWED_EFFORTS:
        result.warnings.append(f"metadata.effort {effort_val!r} not in allowed set {sorted(ALLOWED_EFFORTS)}")

    category_val = _get_value(fm, "category", indent=2)
    if category_val and category_val not in ALLOWED_CATEGORIES:
        result.warnings.append(
            f"metadata.category {category_val!r} not in allowed set {sorted(ALLOWED_CATEGORIES)}"
        )

    # 6. Check for ## Self-Improvement section
    self_improvement_warning = _check_self_improvement_section(skill_dir)
    if self_improvement_warning:
        result.warnings.append(self_improvement_warning)

    return result


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def _print_table(results: Dict[str, SkillAuditResult], *, strict: bool) -> None:
    width = 38
    print("=" * 75)
    print(f"  {'SKILL':<{width}} {'STATUS':<6}  ISSUES")
    print("=" * 75)
    for name, r in results.items():
        status = r.status
        if strict and r.warnings:
            status = "FAIL"
        issues = r.errors + (r.warnings if strict else [])
        first_issue = issues[0] if issues else "--"
        print(f"  {name:<{width}} {status:<6}  {first_issue}")
        for issue in issues[1:]:
            print(f"  {'':<{width}} {'':6}  {issue}")
    print("=" * 75)
    passing = sum(1 for r in results.values() if r.passed)
    total = len(results)
    print(f"\n  Total: {total}  |  Passing: {passing}  |  Failing: {total - passing}\n")


def _print_json(results: Dict[str, SkillAuditResult], *, strict: bool) -> None:
    out = {}
    for name, r in results.items():
        status = r.status
        if strict and r.warnings:
            status = "FAIL"
        out[name] = {
            "status": status,
            "errors": r.errors,
            "warnings": r.warnings,
        }
    print(json.dumps(out, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (exit 1 if any warnings)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Emit machine-readable JSON instead of table",
    )
    parser.add_argument(
        "--skill",
        metavar="SKILL_NAME",
        help="Validate a single skill instead of all active skills",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    skills_to_check = [args.skill] if args.skill else ACTIVE_SKILLS
    results: Dict[str, SkillAuditResult] = {}
    for skill in skills_to_check:
        results[skill] = audit_skill(skill)

    if args.output_json:
        _print_json(results, strict=args.strict)
    else:
        _print_table(results, strict=args.strict)

    # Determine exit code
    any_errors = any(not r.passed for r in results.values())
    any_warnings = any(r.warnings for r in results.values())
    if any_errors:
        return 1
    if args.strict and any_warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
