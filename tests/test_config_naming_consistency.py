#!/usr/bin/env python3
"""
tests/test_config_naming_consistency.py — Model-naming consistency guard.

config/models.yaml (via scripts/models.py) is the single source of truth. This guard
asserts that every GENERATED copy agrees with it, per role:
  1. src/AGENTS.md roster table
  2. .githooks/LOCKED_MODELS.sh (LOCKED_MODELS list + AGENT_MODEL_ASSIGNMENTS),
     evaluated by bash itself rather than scraped
  3. src/agents/*-agent.md frontmatter 'model:' lines

Asserts:
  - each copy equals the registry pin for every role (and covers every role)
  - every registry model matches the registry's own canonical shape
  - no model literal is hard-coded here: roles and pins come from the registry
"""

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import models as model_registry  # noqa: E402

AGENTS_MD = REPO_ROOT / "src" / "AGENTS.md"
LOCKED_MODELS_SH = REPO_ROOT / ".githooks" / "LOCKED_MODELS.sh"
AGENTS_DIR = REPO_ROOT / "src" / "agents"

REGISTRY = model_registry.load_registry(REPO_ROOT)
PINS = {role: cfg["model"] for role, cfg in REGISTRY["roles"].items()}
CANONICAL = model_registry.canonical_re(REGISTRY)


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


def _bash_array(name: str) -> list:
    """Evaluate LOCKED_MODELS.sh in bash and return the named array's elements."""
    out = subprocess.run(
        ["bash", "-c", f'source "{LOCKED_MODELS_SH}" && printf "%s\\n" "${{{name}[@]}}"'],
        capture_output=True, text=True, check=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def _locked_assignments() -> dict:
    out = {}
    for entry in _bash_array("AGENT_MODEL_ASSIGNMENTS"):
        agent, _, model = entry.partition(":")
        out[agent[: -len("-agent")] if agent.endswith("-agent") else agent] = model
    assert out, "no agent assignments evaluated from LOCKED_MODELS.sh"
    return out


def test_registry_models_use_canonical_shape():
    """Every registry model id is claude-<family>-<major>[.<minor>] (dot separator)."""
    for mid in REGISTRY["models"]:
        assert CANONICAL.match(mid), f"{mid!r} is not a canonical model id"


def test_locked_models_sh_matches_registry():
    """The generated LOCKED_MODELS array lists exactly the registry's models."""
    assert set(_bash_array("LOCKED_MODELS")) == set(REGISTRY["models"])


def test_all_sources_agree_with_registry_per_role():
    """AGENTS.md, LOCKED_MODELS.sh and agent frontmatter all equal the registry pin per role."""
    sources = {
        "src/AGENTS.md": {r.replace("_", "-"): m for r, m in _parse_agents_md_roster().items()},
        ".githooks/LOCKED_MODELS.sh": _locked_assignments(),
        "src/agents/*-agent.md": _parse_agent_frontmatter(),
    }
    for name, assigned in sources.items():
        assert set(assigned) == set(PINS), (
            f"{name} covers roles {sorted(assigned)} but the registry has {sorted(PINS)}"
        )
        for role, model in assigned.items():
            assert model == PINS[role], (
                f"{name}: role {role!r} is {model!r}, registry pin is {PINS[role]!r}; "
                f"run python3 scripts/models.py sync"
            )
