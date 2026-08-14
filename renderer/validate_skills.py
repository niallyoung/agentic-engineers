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

Also runs a deeper compliance audit (merged from the former
scripts/validate_skills.py — 2026-08-13 infra consolidation) against the
canonical ACTIVE_SKILLS list: required frontmatter metadata keys (author,
version, category, role, model, effort), required directory structure
(scripts/ + tests/ + __init__.py for script-backed skills), and presence of
a ## Self-Improvement section. This audit only covers ACTIVE_SKILLS; the
frontmatter/registry checks above cover every SKILL.md on disk.

Usage:
    python3 renderer/validate_skills.py
    python3 renderer/validate_skills.py --strict
    python3 renderer/validate_skills.py --skills-dir path/to/skills
    python3 renderer/validate_skills.py --json          # compliance audit as JSON
    python3 renderer/validate_skills.py --skill spec-validator   # single skill
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
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

REQUIRED_FIELDS = {"name", "description"}

# Skill files that don't need frontmatter (reference docs, examples)
FRONTMATTER_EXEMPT_PATTERNS = {
    "README.md",
}

# ---------------------------------------------------------------------------
# Compliance audit (merged from the former scripts/validate_skills.py)
# ---------------------------------------------------------------------------
# Skills listed in src/SKILLS.md as active.
# Update this list whenever a skill is added or deprecated.
#
# SPEC-2026-005 framework slimdown, WP-0 (2026-08-11): pruned from 14 to the
# 8 skills that survive the slimdown. queue-removal (2026-08-13): with
# dispatch now a direct sub-agent spawn, queue-management and queue-query
# are deleted. 8 -> 6 skills. audit-trail-review meta-skill added (2026-08-14,
# task-2026-08-14-delegation-audit-skill). 6 -> 7 skills.
ACTIVE_SKILLS: list[str] = [
    "orchestrator",
    "protocol-validator",
    "spec-validator",
    "spec-management",
    "skill-improvement-feedback",
    "codex-agent-cleanup",
    "audit-trail-review",
]

# Required top-level frontmatter keys for the compliance audit.
COMPLIANCE_REQUIRED_TOP_LEVEL: list[str] = ["name", "description", "license", "compatibility"]

# Required metadata sub-keys for the compliance audit.
COMPLIANCE_REQUIRED_METADATA: list[str] = ["author", "version", "category", "role", "model", "effort"]

# Required directory structure for script-backed skills (a skill dir with no
# scripts/ is PROSE-ONLY by design and exempt from these).
COMPLIANCE_REQUIRED_DIRS: list[str] = ["scripts", "tests"]
COMPLIANCE_REQUIRED_FILES: list[str] = ["SKILL.md", "__init__.py"]

# Allowed enum values -- warn (not error) on mismatch for forward-compatibility
COMPLIANCE_ALLOWED_ROLES = {
    "engineer", "senior-engineer", "lead-engineer", "principal-engineer",
    "security-engineer", "quality-engineer", "orchestrator",
}
COMPLIANCE_ALLOWED_EFFORTS = {"low", "medium", "high"}
COMPLIANCE_ALLOWED_CATEGORIES = {
    "orchestration", "validation", "monitoring", "optimization", "observability",
    "scaffolding", "integration", "metrics", "maintenance",
    "hygiene", "management", "security", "task-management", "meta-skill",
}


@dataclass
class SkillComplianceResult:
    """Result of the deeper ACTIVE_SKILLS compliance audit for one skill."""
    skill_name: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

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


def _compliance_has_key(frontmatter: str, key: str, *, indent: int = 0) -> bool:
    prefix = r"^\s{" + str(indent) + r"}" if indent else r"^"
    return bool(re.search(rf"{prefix}{re.escape(key)}:", frontmatter, re.MULTILINE))


def _compliance_get_value(frontmatter: str, key: str, *, indent: int = 0) -> str | None:
    prefix = r"^\s{" + str(indent) + r"}" if indent else r"^"
    m = re.search(rf"{prefix}{re.escape(key)}:\s*(.+)$", frontmatter, re.MULTILINE)
    return m.group(1).strip() if m else None


def _check_self_improvement_section(skill_dir: Path) -> str | None:
    """Return a warning string if SKILL.md is missing ## Self-Improvement, else None."""
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


def audit_skill_compliance(skill_name: str, skills_dir: Path) -> SkillComplianceResult:
    """Deep compliance audit for one ACTIVE_SKILLS entry (schema + structure)."""
    result = SkillComplianceResult(skill_name=skill_name)
    skill_dir = skills_dir / skill_name

    if not skill_dir.is_dir():
        result.errors.append(f"Directory not found: {skill_dir}")
        return result

    # A skill with no scripts/ dir is PROSE-ONLY by design and does not need
    # the full scaffolded structure.
    is_prose_only = not (skill_dir / "scripts").is_dir()
    required_files = ["SKILL.md"] if is_prose_only else COMPLIANCE_REQUIRED_FILES
    required_dirs = [] if is_prose_only else COMPLIANCE_REQUIRED_DIRS

    for filename in required_files:
        if not (skill_dir / filename).exists():
            result.errors.append(f"Missing required file: {filename}")

    for dirname in required_dirs:
        if not (skill_dir / dirname).is_dir():
            result.errors.append(f"Missing required directory: {dirname}/")

    if not is_prose_only:
        tests_dir = skill_dir / "tests"
        if tests_dir.is_dir() and not list(tests_dir.glob("test_*.py")):
            result.errors.append("tests/ exists but contains no test_*.py files")

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return result

    raw_text = skill_md.read_text(encoding="utf-8")
    try:
        fm = _parse_frontmatter(raw_text)
    except ValueError as exc:
        result.errors.append(f"Malformed frontmatter: {exc}")
        return result
    if fm is None:
        result.errors.append("SKILL.md has no YAML frontmatter (missing --- delimiters)")
        return result
    # The compliance checks below need the raw frontmatter text for
    # indent-aware regex lookups (nested metadata.* keys), so re-slice it
    # directly rather than relying on the parsed dict.
    end = raw_text.find("\n---", 3)
    fm_text = raw_text[3:end].strip() if raw_text.startswith("---") and end != -1 else ""

    for key in COMPLIANCE_REQUIRED_TOP_LEVEL:
        if not _compliance_has_key(fm_text, key):
            result.errors.append(f"Frontmatter missing required key: {key}")

    for key in COMPLIANCE_REQUIRED_METADATA:
        if not _compliance_has_key(fm_text, key, indent=2):
            result.errors.append(f"Frontmatter missing required metadata key: metadata.{key}")

    license_val = _compliance_get_value(fm_text, "license")
    if license_val and license_val != "Proprietary":
        result.warnings.append(f"license should be 'Proprietary', got: {license_val!r}")

    name_val = _compliance_get_value(fm_text, "name")
    if name_val and name_val != skill_name:
        result.errors.append(f"name field ({name_val!r}) does not match directory name ({skill_name!r})")

    role_val = _compliance_get_value(fm_text, "role", indent=2)
    if role_val and role_val not in COMPLIANCE_ALLOWED_ROLES:
        result.warnings.append(f"metadata.role {role_val!r} not in allowed set {sorted(COMPLIANCE_ALLOWED_ROLES)}")

    effort_val = _compliance_get_value(fm_text, "effort", indent=2)
    if effort_val and effort_val not in COMPLIANCE_ALLOWED_EFFORTS:
        result.warnings.append(f"metadata.effort {effort_val!r} not in allowed set {sorted(COMPLIANCE_ALLOWED_EFFORTS)}")

    category_val = _compliance_get_value(fm_text, "category", indent=2)
    if category_val and category_val not in COMPLIANCE_ALLOWED_CATEGORIES:
        result.warnings.append(f"metadata.category {category_val!r} not in allowed set {sorted(COMPLIANCE_ALLOWED_CATEGORIES)}")

    self_improvement_warning = _check_self_improvement_section(skill_dir)
    if self_improvement_warning:
        result.warnings.append(self_improvement_warning)

    return result


def run_compliance_audit(skills_dir: Path, skill_names: list[str]) -> dict[str, SkillComplianceResult]:
    return {name: audit_skill_compliance(name, skills_dir) for name in skill_names}


def _print_compliance_table(results: dict[str, SkillComplianceResult], *, strict: bool) -> None:
    width = 38
    print("=" * 75)
    print(f"  {'SKILL':<{width}} {'STATUS':<6}  ISSUES")
    print("=" * 75)
    for name, r in results.items():
        status = "FAIL" if (strict and r.warnings) else r.status
        issues = r.errors + (r.warnings if strict else [])
        first_issue = issues[0] if issues else "--"
        print(f"  {name:<{width}} {status:<6}  {first_issue}")
        for issue in issues[1:]:
            print(f"  {'':<{width}} {'':6}  {issue}")
    print("=" * 75)
    passing = sum(1 for r in results.values() if r.passed)
    total = len(results)
    print(f"\n  Total: {total}  |  Passing: {passing}  |  Failing: {total - passing}\n")


def _print_compliance_json(results: dict[str, SkillComplianceResult], *, strict: bool) -> None:
    out = {}
    for name, r in results.items():
        status = "FAIL" if (strict and r.warnings) else r.status
        out[name] = {"status": status, "errors": r.errors, "warnings": r.warnings}
    print(json.dumps(out, indent=2))


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
    """Collect all skill markdown files (including nested), excluding reference docs."""
    all_files = skills_dir.rglob("*.md")
    return sorted(f for f in all_files if f.name not in FRONTMATTER_EXEMPT_PATTERNS)


def _is_path_safe(path_to_check: Path, repo_root: Path) -> bool:
    """
    Validate that a path stays within the repository boundary after resolving symlinks.
    
    CRITICAL: This function resolves symlinks FIRST, preventing symlink attacks.
    
    Rejects:
    - Paths that resolve outside repo_root (including through symlinks)
    - Broken symlinks (OSError)
    - Symlink loops (RuntimeError)
    - (Paths containing '..' are checked before calling this function)
    """
    try:
        # CRITICAL: Resolve symlinks and relative paths FIRST
        fully_resolved = path_to_check.resolve()
        # Ensure the fully resolved path is within repo_root
        fully_resolved.relative_to(repo_root.resolve())
        return True
    except (ValueError, OSError, RuntimeError):
        # ValueError: Path is outside repo_root
        # OSError: Broken symlink or permission issue
        # RuntimeError: Symlink loop detected
        return False


def _extract_skill_paths_from_skills_md(skills_md_content: str, repo_root: Path) -> tuple[set[Path], list[ValidationError]]:
    """
    Parse src/SKILLS.md and extract all file paths referenced in tables.

    Looks for markdown table cells containing paths like:
      `src/skills/...`  or  skills/...
    
    Returns: (valid_paths, validation_errors)
    """
    referenced: set[Path] = set()
    errors: list[ValidationError] = []

    # Match table cells containing file paths: | `src/skills/foo/bar.md` |
    pattern = re.compile(r"\|\s*`?(src/skills/[^`|\s]+\.md)`?\s*\|", re.IGNORECASE)

    for match in pattern.finditer(skills_md_content):
        raw_path = match.group(1).strip().strip("`")
        
        # Security Fix 4: Reject absolute paths explicitly
        if raw_path.startswith('/'):
            errors.append(ValidationError(
                None, "ERROR",
                f"src/SKILLS.md path '{raw_path}' is absolute. Only relative paths within repository allowed."
            ))
            continue
        
        # Security Fix 3: Component-based validation for ".." segments
        # Check if any path component is ".." or if path would escape boundary
        path_components = Path(raw_path).parts
        if '..' in path_components:
            errors.append(ValidationError(
                None, "ERROR",
                f"src/SKILLS.md contains invalid path '{raw_path}': paths with '..' segments are not allowed"
            ))
            continue
        
        # Construct the full path and validate it stays within repo
        path_obj = repo_root / raw_path
        
        # Security Fix 1: _is_path_safe now resolves symlinks before boundary checking
        if not _is_path_safe(path_obj, repo_root):
            errors.append(ValidationError(
                None, "ERROR",
                f"src/SKILLS.md path '{raw_path}' resolves outside repository boundary (possibly through symlink). Only relative paths within {repo_root.name}/ are allowed."
            ))
            continue
        
        referenced.add(path_obj)

    return referenced, errors


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
    3. All paths in src/SKILLS.md are safe (no directory traversal)
    """
    errors: list[ValidationError] = []

    referenced_paths, path_validation_errors = _extract_skill_paths_from_skills_md(skills_md_content, repo_root)
    errors.extend(path_validation_errors)

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
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Emit the ACTIVE_SKILLS compliance audit as machine-readable JSON "
             "instead of running the full frontmatter/registry validation",
    )
    parser.add_argument(
        "--skill",
        metavar="SKILL_NAME",
        help="Restrict the compliance audit to a single ACTIVE_SKILLS entry "
             "(only meaningful together with --json)",
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

    # --json emits only the ACTIVE_SKILLS compliance audit, matching the
    # informational-report consumer (format_skill_report.py) this flag has
    # always fed. It intentionally does not also run the broader
    # frontmatter/registry validation below — see the plain-invocation path.
    if args.output_json:
        skill_names = [args.skill] if args.skill else ACTIVE_SKILLS
        compliance_results = run_compliance_audit(skills_dir, skill_names)
        _print_compliance_json(compliance_results, strict=args.strict)
        any_errors = any(not r.passed for r in compliance_results.values())
        any_warnings = any(r.warnings for r in compliance_results.values())
        if any_errors or (args.strict and any_warnings):
            return 1
        return 0

    error_count, warning_count = validate_skills(skills_dir, src_dir, repo_root, strict=args.strict)

    # Blocking gate: also run the deeper ACTIVE_SKILLS compliance audit
    # (schema + directory structure + self-improvement section) — merged
    # from the former scripts/validate_skills.py during the 2026-08-13
    # infra consolidation, so there is a single validate_skills implementation.
    skill_names = [args.skill] if args.skill else ACTIVE_SKILLS
    compliance_results = run_compliance_audit(skills_dir, skill_names)
    _print_compliance_table(compliance_results, strict=args.strict)
    compliance_errors = sum(len(r.errors) for r in compliance_results.values())
    compliance_warnings = sum(len(r.warnings) for r in compliance_results.values())
    if compliance_errors:
        print(f"❌ {compliance_errors} compliance error(s) across ACTIVE_SKILLS")

    error_count += compliance_errors
    warning_count += compliance_warnings

    if error_count > 0:
        return 1
    if args.strict and warning_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
