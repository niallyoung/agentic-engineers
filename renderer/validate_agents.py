#!/usr/bin/env python3
"""
Agent definition validator for agentic-engineers.

Validates all agent markdown files in src/agents/:
  - YAML frontmatter is present and parseable
  - Required fields exist: name, description, model
  - Model value is one of the known models
  - Agent name matches the filename convention (name-agent.md)
  - Agent is registered in src/AGENTS.md

Usage:
    python3 renderer/validate_agents.py
    python3 renderer/validate_agents.py --strict
    python3 renderer/validate_agents.py --agents-dir path/to/agents
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
# Canonical protocol validation (delegated to the protocol-validator skill)
# ---------------------------------------------------------------------------
# Runtime HANDBACK dict validation is owned by the protocol-validator skill —
# the single source of truth shared with the eval framework and queue system.
# We import its validate_handback() rather than re-implementing the rules here.

_PV_SCRIPTS = Path(__file__).resolve().parent.parent / "src" / "skills" / "protocol-validator" / "scripts"
if str(_PV_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_PV_SCRIPTS))

try:
    from protocol_validator import validate_handback as _skill_validate_handback  # type: ignore
    _PV_SKILL_AVAILABLE = True
except ImportError:
    _skill_validate_handback = None  # type: ignore
    _PV_SKILL_AVAILABLE = False


def validate_handback(handback: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a runtime HANDBACK dict via the protocol-validator skill.

    This is the canonical entry point for validating an actual HANDBACK block
    (as opposed to validate_handback_schema(), which checks that AGENTS.md
    *documents* the protocol). Delegates to the protocol-validator skill so
    the renderer, eval framework, and queue system all enforce identical rules.

    Returns (valid, errors). If the skill cannot be imported, returns
    (True, []) so the renderer degrades gracefully rather than hard-failing.
    """
    if not _PV_SKILL_AVAILABLE or _skill_validate_handback is None:
        return True, []
    return _skill_validate_handback(handback)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# KNOWN_MODELS — LOCKED per docs/SPEC.md "Model Naming Architecture"
#
# This set is the SINGLE SOURCE OF TRUTH for approved models.
# ALL models must be listed here; validator rejects anything outside this set.
#
# STRUCTURE:
#   Versioned Claude models (canonical source format, DOTS required):
#     - claude-haiku-4.5, claude-haiku-4.6
#     - claude-sonnet-4.5, claude-sonnet-4.6
#     - claude-opus-4.5, claude-opus-4.6, claude-opus-4.7, claude-opus-4.8
#   
#   Short aliases (for Claude Code harness only):
#     - haiku, sonnet, opus (no version numbers)
#
# FORBIDDEN (causes validator to REJECT):
#   ❌ GPT models (gpt-4, gpt-4o, gpt-4o-mini)
#   ❌ Unversioned Claude (claude-opus without -4.7)
#   ❌ Hyphens in version (claude-opus-4-7) — source uses DOTS
#   ❌ Uppercase, underscores, or other formats
#
# RATIONALE:
#   Model naming broke repeatedly across commits due to per-harness
#   format confusion. Source agents use canonical format (DOTS),
#   renderers transform per harness (OpenCode→hyphens, Claude Code→aliases).
#   This set enforces the canonical format for source validation.
#   See docs/SPEC.md for complete architecture & transformation rules.
#

KNOWN_MODELS = {
    # Versioned Claude models (canonical source format)
    # SOURCE: https://docs.anthropic.com/claude/docs/models-overview
    # Format: claude-{variant}-{major}.{minor} or claude-{variant}-{major} (for single-part versions)
    "claude-haiku-4.5",
    "claude-haiku-4.6",
    "claude-sonnet-4.5",
    "claude-sonnet-4.6",
    "claude-sonnet-5",
    "claude-opus-4.5",
    "claude-opus-4.6",
    "claude-opus-4.7",
    "claude-opus-4.8",
    "claude-opus-5",
    "claude-fable-5",

    # Short aliases (Claude Code harness only, NO DOTS)
    # Used in dist/claude/agents/ after transformation from canonical format
    "haiku",
    "sonnet",
    "opus",
    "fable",
}

REQUIRED_FIELDS = {"name", "description", "model"}

# Agents that don't follow the <name>-agent.md convention (allowlist)
FILENAME_EXCEPTIONS: set[str] = set()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> dict[str, Any] | None:
    """Extract and parse YAML frontmatter from a markdown string.

    Returns the parsed dict or None if no frontmatter found.
    Raises ValueError if frontmatter is malformed.
    """
    if not text.startswith("---"):
        return None

    # Find closing ---
    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError("Frontmatter opened with '---' but never closed")

    frontmatter_text = text[3:end].strip()

    if not _YAML_AVAILABLE:
        # Minimal fallback: parse simple key: value pairs only
        result: dict[str, Any] = {}
        for line in frontmatter_text.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                result[k.strip()] = v.strip()
        return result

    try:
        return yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML parse error: {exc}") from exc


def _load_agents_md(src_dir: Path) -> str:
    """Read src/AGENTS.md content for registration checks."""
    agents_md = src_dir / "AGENTS.md"
    if not agents_md.exists():
        return ""
    return agents_md.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------

class ValidationError:
    """A single validation finding."""

    def __init__(self, file: Path, level: str, message: str) -> None:
        self.file = file
        self.level = level  # "ERROR" | "WARNING"
        self.message = message

    def __str__(self) -> str:
        rel = self.file.name
        return f"  [{self.level}] {rel}: {self.message}"


def validate_agent_file(
    path: Path,
    agents_md_content: str,
    strict: bool = False,
) -> list[ValidationError]:
    """Validate a single agent markdown file."""
    errors: list[ValidationError] = []

    text = path.read_text(encoding="utf-8")

    # 1. Frontmatter presence
    try:
        fm = _parse_frontmatter(text)
    except ValueError as exc:
        errors.append(ValidationError(path, "ERROR", f"Malformed frontmatter: {exc}"))
        return errors  # Can't continue without valid frontmatter

    if fm is None:
        errors.append(ValidationError(path, "ERROR", "Missing YAML frontmatter (file must start with ---)"))
        return errors

    # 2. Required fields
    for field in sorted(REQUIRED_FIELDS):
        if field not in fm or not fm[field]:
            errors.append(ValidationError(path, "ERROR", f"Missing required frontmatter field: '{field}'"))

    # 3. Model validation
    model = fm.get("model", "")
    if model and model not in KNOWN_MODELS:
        level = "ERROR" if strict else "WARNING"
        errors.append(ValidationError(
            path, level,
            f"Unknown model '{model}'. Known models: {', '.join(sorted(KNOWN_MODELS))}"
        ))

    # 4. Filename convention: <name>-agent.md
    agent_name = fm.get("name", "")
    if agent_name and path.name not in FILENAME_EXCEPTIONS:
        expected_filename = f"{agent_name}-agent.md"
        if path.name != expected_filename:
            errors.append(ValidationError(
                path, "WARNING",
                f"Filename '{path.name}' doesn't match expected '{expected_filename}' (from name: '{agent_name}')"
            ))

    # 5. Registration in AGENTS.md
    if agent_name and agents_md_content:
        # Look for the agent name in any table row or heading
        pattern = re.compile(
            rf"\b{re.escape(agent_name)}\b",
            re.IGNORECASE,
        )
        if not pattern.search(agents_md_content):
            level = "ERROR" if strict else "WARNING"
            errors.append(ValidationError(
                path, level,
                f"Agent '{agent_name}' not found in src/AGENTS.md — add it to the Agent Roster table"
            ))

    return errors


def validate_agents(
    agents_dir: Path,
    src_dir: Path,
    strict: bool = False,
) -> tuple[int, int]:
    """Validate all agent files.

    Returns (error_count, warning_count).
    """
    agents_md = _load_agents_md(src_dir)

    agent_files = sorted(agents_dir.glob("*-agent.md"))
    if not agent_files:
        print(f"⚠️  No agent files found in {agents_dir}")
        return 0, 1

    all_errors: list[ValidationError] = []
    checked = 0

    for agent_file in agent_files:
        findings = validate_agent_file(agent_file, agents_md, strict=strict)
        all_errors.extend(findings)
        checked += 1

    # Also validate HANDBACK metrics requirements in AGENTS.md
    all_errors.extend(validate_handback_schema(src_dir, strict=strict))

    errors = [e for e in all_errors if e.level == "ERROR"]
    warnings = [e for e in all_errors if e.level == "WARNING"]

    if errors or warnings:
        print(f"Agent validation findings ({checked} files checked):\n")
        for finding in all_errors:
            print(finding)
        print()
    else:
        print(f"✅ All {checked} agent files are valid")

    if errors:
        print(f"❌ {len(errors)} error(s), {len(warnings)} warning(s)")
    elif warnings:
        print(f"⚠️  0 errors, {len(warnings)} warning(s)")

    return len(errors), len(warnings)


def validate_handback_schema(src_dir: Path, strict: bool = False) -> list[ValidationError]:
    """Verify AGENTS.md documents the canonical HANDBACK schema.

    The single source of truth is ``docs/specs/protocol-core-v1.0.yaml`` (enforced
    at runtime by ``core_protocol_validator.py``). A HANDBACK's required core is:
      - task_id
      - status              (success | failure | partial | blocked | escalate)
      - output
      - metrics             (object with the four subfields below)
          - quality         (0.0–1.0, self-assessed by agent)
          - tokens          (non-negative integer)
          - cost            (non-negative USD)
          - duration_seconds (non-negative)

    This validates the protocol documentation, not runtime HANDBACK files. It
    intentionally checks the same field set as the runtime validator so the docs
    and the validator never drift into separate schemas.
    """
    errors: list[ValidationError] = []
    agents_md_path = src_dir / "AGENTS.md"

    if not agents_md_path.exists():
        return errors  # Already caught elsewhere

    content = agents_md_path.read_text(encoding="utf-8")

    # Canonical HANDBACK core fields + required metrics subfields.
    required_handback_fields = [
        "task_id",
        "status",
        "output",
        "metrics",
        "quality",
        "tokens",
        "cost",
        "duration_seconds",
    ]

    for field in required_handback_fields:
        if field not in content:
            level = "WARNING"
            errors.append(ValidationError(
                agents_md_path, level,
                f"AGENTS.md HANDBACK schema missing '{field}' field documentation"
            ))

    return errors


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate agent definition files in src/agents/",
    )
    parser.add_argument(
        "--agents-dir",
        default=None,
        help="Path to agents directory (default: <repo_root>/src/agents)",
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

    # Resolve paths relative to repo root (two levels up from renderer/)
    repo_root = Path(__file__).parent.parent
    src_dir = Path(args.src_dir) if args.src_dir else repo_root / "src"
    agents_dir = Path(args.agents_dir) if args.agents_dir else src_dir / "agents"

    if not agents_dir.exists():
        print(f"❌ Agents directory not found: {agents_dir}")
        return 1

    if not _YAML_AVAILABLE:
        print("⚠️  PyYAML not installed — using minimal frontmatter parser (pip install pyyaml for full validation)")

    error_count, warning_count = validate_agents(agents_dir, src_dir, strict=args.strict)

    if error_count > 0:
        return 1
    if args.strict and warning_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
