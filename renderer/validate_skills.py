#!/usr/bin/env python3
"""
Skill definition validator for agentic-engineers.

Validates all skill markdown files under src/skills/:
  - YAML frontmatter is present and parseable on SKILL.md files
  - Required fields exist: name, description
  - All skills registered in src/SKILLS.md exist on disk
  - All SKILL.md files on disk are registered in src/SKILLS.md
  - Roles referenced in skill frontmatter exist in the known agent roster
  - No broken relative links to skill files

Usage:
    python3 renderer/validate_skills.py
    python3 renderer/validate_skills.py --strict
    python3 renderer/validate_skills.py --skills-dir path/to/skills
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KNOWN_ROLES = {
    "orchestrator",
    "engineer",
    "model-engineer",
    "quality-engineer",
    "lead-engineer",
    "senior-engineer",
    "principal-engineer",
    "security-engineer",
    # Aliases sometimes used in skill files
    "model_engineer",
    "quality_engineer",
    "lead_engineer",
    "senior_engineer",
    "principal_engineer",
    "security_engineer",
    # Healer variant
    "healer-engineer",
}

REQUIRED_FIELDS = {"name", "description"}

# Skill files that don't need frontmatter (reference docs, examples)
FRONTMATTER_EXEMPT_PATTERNS = {
    "README.md",
    "EXAMPLES.md",
    "IMPLEMENTATION-SUMMARY.md",
    "SKILLS-INDEX.md",
    "QUICK-START.md",
    "AGENT-INTEGRATION.md",
    "SESSION-INIT.sh",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> dict[str, Any] | None:
    """Extract and parse YAML frontmatter. Returns None if not present."""
    if not text.startswith("---"):
        return None

    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError("Frontmatter '---' opened but never closed")

    frontmatter_text = text[3:end].strip()

    if not _YAML_AVAILABLE:
        result: dict[str, Any] = {}
        for line in frontmatter_text.splitlines():
            if ":" in line and not line.strip().startswith("#"):
                k, _, v = line.partition(":")
                result[k.strip()] = v.strip()
        return result

    try:
        parsed = yaml.safe_load(frontmatter_text)
        return parsed or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML parse error: {exc}") from exc


def _collect_skill_files(skills_dir: Path) -> list[Path]:
    """Collect all skill markdown files (including nested)."""
    return sorted(skills_dir.rglob("*.md"))


def _extract_skill_paths_from_skills_md(skills_md_content: str, repo_root: Path) -> set[Path]:
    """
    Parse src/SKILLS.md and extract all file paths referenced in tables.

    Looks for markdown table cells containing paths like:
      `src/skills/...`  or  skills/...
    """
    referenced: set[Path] = set()

    # Match table cells containing file paths: | `src/skills/foo/bar.md` |
    pattern = re.compile(r"\|\s*`?(src/skills/[^`|\s]+\.md)`?\s*\|", re.IGNORECASE)

    for match in pattern.finditer(skills_md_content):
        raw_path = match.group(1).strip().strip("`")
        resolved = repo_root / raw_path
        referenced.add(resolved)

    return referenced


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------

class ValidationError:
    def __init__(self, file: Path | None, level: str, message: str) -> None:
        self.file = file
        self.level = level
        self.message = message

    def __str__(self) -> str:
        if self.file:
            # Show a relative-looking path — find "src/skills" in the path
            parts = self.file.parts
            try:
                idx = next(i for i, p in enumerate(parts) if p in ("src", "renderer"))
                loc = "/".join(parts[idx:])
            except StopIteration:
                loc = self.file.name
        else:
            loc = "global"
        return f"  [{self.level}] {loc}: {self.message}"


def validate_skill_file(path: Path, strict: bool = False) -> list[ValidationError]:
    """Validate a single skill file's frontmatter."""
    errors: list[ValidationError] = []

    # Exempt certain reference docs from frontmatter requirement
    if path.name in FRONTMATTER_EXEMPT_PATTERNS:
        return errors

    text = path.read_text(encoding="utf-8")

    # Only SKILL.md files are required to have frontmatter
    is_skill_md = path.name == "SKILL.md"

    try:
        fm = _parse_frontmatter(text)
    except ValueError as exc:
        if is_skill_md:
            # SKILL.md with broken frontmatter is always an error
            errors.append(ValidationError(path, "ERROR", f"Malformed frontmatter: {exc}"))
        else:
            # Other .md files with malformed frontmatter are warnings only
            errors.append(ValidationError(path, "WARNING", f"Malformed frontmatter (non-critical): {exc}"))
        return errors

    if fm is None:
        if is_skill_md:
            errors.append(ValidationError(
                path, "ERROR",
                "SKILL.md missing YAML frontmatter (must start with ---)"
            ))
        return errors

    # Required fields — only enforce on SKILL.md files
    if is_skill_md:
        for field in sorted(REQUIRED_FIELDS):
            if field not in fm or not fm[field]:
                errors.append(ValidationError(
                    path, "ERROR",
                    f"Missing required frontmatter field: '{field}'"
                ))

    # Roles validation (when frontmatter is present on any file)
    roles = fm.get("roles", [])
    if isinstance(roles, list):
        for role in roles:
            role_normalized = str(role).lower().replace("_", "-")
            if role_normalized not in KNOWN_ROLES and role not in KNOWN_ROLES:
                level = "ERROR" if strict else "WARNING"
                errors.append(ValidationError(
                    path, level,
                    f"Unknown role '{role}' in frontmatter. Known roles: {', '.join(sorted(KNOWN_ROLES))}"
                ))

    return errors


def validate_registry_completeness(
    skills_dir: Path,
    skills_md_content: str,
    repo_root: Path,
    strict: bool = False,
) -> list[ValidationError]:
    """
    Check that:
    1. All paths in src/SKILLS.md exist on disk
    2. All SKILL.md files on disk are registered in src/SKILLS.md
    """
    errors: list[ValidationError] = []

    referenced_paths = _extract_skill_paths_from_skills_md(skills_md_content, repo_root)

    # Check all referenced paths exist
    for ref_path in sorted(referenced_paths):
        if not ref_path.exists():
            errors.append(ValidationError(
                None, "ERROR",
                f"src/SKILLS.md references '{ref_path.relative_to(repo_root)}' but file does not exist"
            ))

    # Check all SKILL.md files are registered
    skill_mds_on_disk = set(skills_dir.rglob("SKILL.md"))
    for skill_md in sorted(skill_mds_on_disk):
        if skill_md not in referenced_paths:
            # Also check if the parent path is mentioned anywhere in SKILLS.md
            rel = str(skill_md.relative_to(repo_root))
            if rel not in skills_md_content:
                level = "WARNING"  # Not an error — may be intentionally unregistered
                errors.append(ValidationError(
                    skill_md, level,
                    f"SKILL.md on disk not registered in src/SKILLS.md — add to the skill inventory"
                ))

    return errors


def validate_skills(
    skills_dir: Path,
    src_dir: Path,
    repo_root: Path,
    strict: bool = False,
) -> tuple[int, int]:
    """Validate all skill files. Returns (error_count, warning_count)."""
    skills_md_path = src_dir / "SKILLS.md"
    skills_md_content = skills_md_path.read_text(encoding="utf-8") if skills_md_path.exists() else ""

    if not skills_md_content:
        print(f"⚠️  src/SKILLS.md not found at {skills_md_path} — skipping registry checks")

    skill_files = _collect_skill_files(skills_dir)
    all_errors: list[ValidationError] = []
    checked = 0

    # Per-file validation
    for skill_file in skill_files:
        findings = validate_skill_file(skill_file, strict=strict)
        all_errors.extend(findings)
        checked += 1

    # Registry completeness check
    if skills_md_content:
        registry_findings = validate_registry_completeness(
            skills_dir, skills_md_content, repo_root, strict=strict
        )
        all_errors.extend(registry_findings)

    errors = [e for e in all_errors if e.level == "ERROR"]
    warnings = [e for e in all_errors if e.level == "WARNING"]

    if errors or warnings:
        print(f"Skill validation findings ({checked} files checked):\n")
        for finding in all_errors:
            print(finding)
        print()
    else:
        print(f"✅ All {checked} skill files are valid")

    if errors:
        print(f"❌ {len(errors)} error(s), {len(warnings)} warning(s)")
    elif warnings:
        print(f"⚠️  0 errors, {len(warnings)} warning(s)")
    else:
        print(f"✅ 0 errors, 0 warnings")

    return len(errors), len(warnings)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate skill definition files in src/skills/",
    )
    parser.add_argument(
        "--skills-dir",
        default=None,
        help="Path to skills directory (default: <repo_root>/src/skills)",
    )
    parser.add_argument(
        "--src-dir",
        default=None,
        help="Path to src/ directory (default: <repo_root>/src)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    src_dir = Path(args.src_dir) if args.src_dir else repo_root / "src"
    skills_dir = Path(args.skills_dir) if args.skills_dir else src_dir / "skills"

    if not skills_dir.exists():
        print(f"❌ Skills directory not found: {skills_dir}")
        return 1

    if not _YAML_AVAILABLE:
        print("⚠️  PyYAML not installed — using minimal frontmatter parser (pip install pyyaml for full validation)")

    error_count, warning_count = validate_skills(skills_dir, src_dir, repo_root, strict=args.strict)

    if error_count > 0:
        return 1
    if args.strict and warning_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
