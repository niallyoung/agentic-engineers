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
# Constants
# ---------------------------------------------------------------------------

# KNOWN_MODELS — the set of model ids a source agent may declare.
#
# DERIVED from config/models.yaml through scripts/models.py (docs/SPEC.md, invariant
# I6); this module holds no model list and no version allowlist, so registering,
# re-pinning or retiring a model never needs an edit here. See docs/SPEC.md § "Model
# Naming & Harness Compatibility" for the naming architecture.
#
# ACCEPTED:
#   - Every non-retired registry model id (canonical source form, version separated
#     by a DOT: claude-{variant}-{major}.{minor}; single-part versions have no dot)
#
# The families' claude_alias values (haiku, sonnet, opus, fable) are NOT in KNOWN_MODELS:
# SPEC invariant I3 forbids floating aliases for assigned roles in source. They live in
# RENDERED_ALIASES and are accepted only when validating rendered output
# (validate_agent_file(..., rendered=True) / the --rendered CLI flag), which is where the
# AGENTIC_CLAUDE_MODEL_RENDER=alias override legitimately produces them.
#
# REJECTED (reported as a WARNING, or an ERROR under --strict):
#   - Non-Claude models, retired or unregistered ids
#   - Hyphenated versions (claude-opus-4-7) — a per-harness RENDER format, never a
#     valid source id
#   - Uppercase, underscores, or any other shape
#
# Without PyYAML the registry cannot be read: this fails loudly rather than
# validating against an empty or stale set.

_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "scripts")


def _load_known_models() -> set[str]:
    if _SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, _SCRIPTS_DIR)
    try:
        import models as model_registry  # exits with a clear message without PyYAML
    except SystemExit as exc:
        raise RuntimeError(
            "renderer/validate_agents.py needs PyYAML to read config/models.yaml "
            "(pip install pyyaml)"
        ) from exc
    reg = model_registry.load_registry()
    known = {
        mid for mid, m in (reg.get("models") or {}).items()
        if isinstance(m, dict) and m.get("status") != "retired"
    }
    return known


def _load_rendered_aliases() -> set[str]:
    import models as model_registry  # already importable (see _load_known_models)
    reg = model_registry.load_registry()
    return {
        f["claude_alias"] for f in (reg.get("families") or {}).values()
        if isinstance(f, dict) and f.get("claude_alias")
    }


KNOWN_MODELS = _load_known_models()
RENDERED_ALIASES = _load_rendered_aliases()

REQUIRED_FIELDS = {"name", "description", "model"}


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
    rendered: bool = False,
) -> list[ValidationError]:
    """Validate a single agent markdown file.

    rendered=False (default) validates SOURCE: only canonical registry ids are allowed
    and a bare floating alias is an ERROR (SPEC I3). rendered=True validates rendered
    output, where the family aliases may legitimately appear (AGENTIC_CLAUDE_MODEL_RENDER=alias).
    """
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
    if model and not rendered and model in RENDERED_ALIASES:
        errors.append(ValidationError(
            path, "ERROR",
            f"Floating alias '{model}' is not allowed in source (SPEC I3); "
            f"use the canonical registry id (e.g. claude-<family>-<major>.<minor>)"
        ))
    elif model and model not in KNOWN_MODELS and not (rendered and model in RENDERED_ALIASES):
        level = "ERROR" if strict else "WARNING"
        errors.append(ValidationError(
            path, level,
            f"Unknown model '{model}'. Known models: {', '.join(sorted(KNOWN_MODELS))}"
        ))

    # 4. Filename convention: <name>-agent.md
    agent_name = fm.get("name", "")
    if agent_name:
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
    rendered: bool = False,
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
        findings = validate_agent_file(agent_file, agents_md, strict=strict, rendered=rendered)
        all_errors.extend(findings)
        checked += 1

    # Also validate HANDBACK metrics requirements in AGENTS.md
    all_errors.extend(validate_handback_schema(src_dir))

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


def validate_handback_schema(src_dir: Path) -> list[ValidationError]:
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
            errors.append(ValidationError(
                agents_md_path, "WARNING",
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
    parser.add_argument(
        "--rendered",
        action="store_true",
        help="Validate RENDERED output: also accept the floating family aliases "
             "(AGENTIC_CLAUDE_MODEL_RENDER=alias). Never use for src/.",
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

    error_count, warning_count = validate_agents(agents_dir, src_dir, strict=args.strict, rendered=args.rendered)

    if error_count > 0:
        return 1
    if args.strict and warning_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
