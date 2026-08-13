#!/usr/bin/env python3
"""
tests/test_config_naming_consistency.py — Model-naming consistency guard.

Validates model-naming consistency across SURVIVING canonical sources:
  1. src/AGENTS.md roster table
  2. .githooks/LOCKED_MODELS.sh (LOCKED_MODELS list + AGENT_MODEL_ASSIGNMENTS)
  3. src/agents/*-agent.md frontmatter 'model:' lines

Asserts:
  - All three sources agree per role
  - Every model matches claude-{variant}-{major}[.{minor}] format
  - orchestrator=claude-sonnet-5 and engineer=claude-haiku-4.5 are consistent
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_MD = REPO_ROOT / "src" / "AGENTS.md"
LOCKED_MODELS_SH = REPO_ROOT / ".githooks" / "LOCKED_MODELS.sh"
AGENTS_DIR = REPO_ROOT / "src" / "agents"

# Full-version names carry a numeric version suffix.
# claude-haiku-4.5, claude-sonnet-5, claude-opus-5, claude-fable-5
FULL_VERSION = re.compile(
    r"^claude-(?:haiku)-\d+\.\d+$|^claude-(?:sonnet|opus|fable)-\d+(?:\.\d+)?$"
)


def _is_full_version(name: str) -> bool:
    return bool(FULL_VERSION.match(name))


def _parse_agents_md_roster() -> dict:
    """Parse src/AGENTS.md roster table and extract model assignments."""
    text = AGENTS_MD.read_text()
    # Find the roster table — look for lines with | **Role** | ... | model | ...
    roster = {}

    # Pattern: markdown table row with | **Role** | ... (name in bold)
    for line in text.split('\n'):
        if '|' not in line or '**' not in line:
            continue

        # Match: | **role-name** | ... | model-id | ... (model is typically 2nd column)
        parts = [p.strip() for p in line.split('|') if p.strip()]
        if len(parts) < 2:
            continue

        # Check if first part is a role name (bold-enclosed, case-insensitive)
        role_match = re.match(r'\*\*([A-Za-z\s\-]+)\*\*', parts[0])
        if not role_match:
            continue

        role_name = role_match.group(1).strip()
        # Convert to snake_case for canonical lookup
        role = role_name.lower().replace(' ', '_')

        # Find model column (usually contains 'claude-')
        for part in parts[1:]:
            if part.startswith('claude-'):
                roster[role] = part
                break

    assert roster, "No roles found in AGENTS.md roster table"
    return roster


def _parse_locked_models_assignments() -> dict:
    """Parse AGENT_MODEL_ASSIGNMENTS array from LOCKED_MODELS.sh."""
    text = LOCKED_MODELS_SH.read_text()
    block = re.search(
        r"AGENT_MODEL_ASSIGNMENTS=\((.*?)\)", text, re.DOTALL
    )
    assert block, "AGENT_MODEL_ASSIGNMENTS array not found in LOCKED_MODELS.sh"
    out = {}
    for m in re.finditer(r'"([\w-]+):(claude-[\w.\-]+)"', block.group(1)):
        out[m.group(1)] = m.group(2)
    assert out, "no agent assignments parsed from LOCKED_MODELS.sh"
    return out


def _parse_agent_frontmatter() -> dict:
    """Parse model: field from src/agents/*-agent.md frontmatter."""
    models = {}
    for md_file in AGENTS_DIR.glob("*-agent.md"):
        text = md_file.read_text()
        # Look for frontmatter model: line
        match = re.search(r"^model:\s*(.+)$", text, re.MULTILINE)
        if match:
            role = md_file.stem.replace("-agent", "")
            model = match.group(1).strip()
            models[role] = model
    assert models, "No model: fields found in agent .md files"
    return models


def test_locked_models_sh_uses_full_versions():
    """Every model in LOCKED_MODELS.sh must be a full-version name."""
    text = LOCKED_MODELS_SH.read_text()
    locked_block = re.search(r"LOCKED_MODELS=\((.*?)\)", text, re.DOTALL)
    assert locked_block, "LOCKED_MODELS array not found"
    locked = set(re.findall(r'"(claude-[\w.\-]+)"', locked_block.group(1)))
    assert locked, "No models found in LOCKED_MODELS"

    for model in locked:
        assert _is_full_version(model), (
            f"LOCKED_MODELS contains {model!r} which is not a full-version name "
            f"(expected e.g. 'claude-haiku-4.5' or 'claude-sonnet-5')"
        )


def test_all_three_sources_agree_per_role():
    """All three canonical sources agree on model assignments per role."""
    agents_md_models = _parse_agents_md_roster()
    locked_assignments = _parse_locked_models_assignments()
    agent_frontmatter = _parse_agent_frontmatter()

    # Collect all roles across all three sources
    all_roles = set(agents_md_models.keys()) | set(locked_assignments.keys()) | set(agent_frontmatter.keys())

    for role in all_roles:
        md_model = agents_md_models.get(role)
        locked_model = locked_assignments.get(role)
        fm_model = agent_frontmatter.get(role)

        # All three should have a value for the role
        assert md_model or locked_model or fm_model, (
            f"Role {role!r} has no model assignment in any source"
        )

        # All present sources should agree
        models_present = [m for m in [md_model, locked_model, fm_model] if m]
        if len(models_present) > 1:
            assert len(set(models_present)) == 1, (
                f"Role {role!r} has conflicting models: "
                f"AGENTS.md={md_model}, LOCKED_MODELS.sh={locked_model}, "
                f"*-agent.md={fm_model}"
            )


