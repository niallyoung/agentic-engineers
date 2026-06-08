"""
Source-of-truth integrity evals.

Validates the inputs the render pipeline consumes, independent of any harness:

  - all 8 src/agents/*-agent.md have required frontmatter
    (name, model, description, role, accepts, returns)
  - the src/AGENTS.md roster table lists all 8 roles with canonical dotted
    Claude model ids and a non-empty effort column (never blank)
  - every user-facing src/skills/*/SKILL.md has required frontmatter
    (name, description)

These guard against silent corruption of the single source of truth
(src/AGENTS.md was recently consolidated from docs/AGENTS.md).
"""

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_AGENTS = REPO_ROOT / "src" / "agents"
SRC_SKILLS = REPO_ROOT / "src" / "skills"
AGENTS_MD = REPO_ROOT / "src" / "AGENTS.md"

# Canonical roster as named in the AGENTS.md table (display form).
EXPECTED_TABLE_ROLES = {
    "Orchestrator",
    "Engineer",
    "Quality Engineer",
    "Senior Engineer",
    "Lead Engineer",
    "Principal Engineer",
    "Security Engineer",
    "Model Engineer",
}

AGENT_FILES = sorted(SRC_AGENTS.glob("*-agent.md"))

REQUIRED_AGENT_FIELDS = ("name", "model", "description", "role", "accepts", "returns")


def _parse_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{path.name}: missing leading '---' frontmatter"
    end = text.find("\n---", 3)
    assert end != -1, f"{path.name}: unterminated frontmatter"
    block = text[3:end]
    return yaml.safe_load(block) or {}


def test_exactly_8_agent_source_files():
    assert len(AGENT_FILES) == 8, (
        f"Expected 8 src/agents/*-agent.md files, found {len(AGENT_FILES)}: "
        f"{[p.name for p in AGENT_FILES]}"
    )


@pytest.mark.parametrize("agent_path", AGENT_FILES, ids=lambda p: p.name)
def test_agent_frontmatter_required_fields(agent_path):
    fm = _parse_frontmatter(agent_path)
    for field in REQUIRED_AGENT_FIELDS:
        assert field in fm, f"{agent_path.name}: missing required frontmatter '{field}'"
        assert fm[field], f"{agent_path.name}: frontmatter '{field}' is empty"


@pytest.mark.parametrize("agent_path", AGENT_FILES, ids=lambda p: p.name)
def test_agent_name_matches_filename(agent_path):
    fm = _parse_frontmatter(agent_path)
    expected = agent_path.stem.replace("-agent", "")
    assert fm["name"] == expected, (
        f"{agent_path.name}: frontmatter name '{fm['name']}' != filename role "
        f"'{expected}'"
    )


@pytest.mark.parametrize("agent_path", AGENT_FILES, ids=lambda p: p.name)
def test_agent_model_is_canonical_dotted_claude(agent_path):
    """Source agents use the LOCKED canonical dotted Claude format (claude-<tier>-N.N)."""
    fm = _parse_frontmatter(agent_path)
    model = str(fm["model"]).strip()
    assert re.match(r"^claude-(haiku|sonnet|opus)-\d+\.\d+$", model), (
        f"{agent_path.name}: model '{model}' is not canonical dotted Claude "
        "format (e.g. claude-sonnet-4.6)"
    )


@pytest.mark.parametrize("agent_path", AGENT_FILES, ids=lambda p: p.name)
def test_agent_accepts_returns_protocol(agent_path):
    fm = _parse_frontmatter(agent_path)
    assert "DELEGATE" in fm["accepts"], (
        f"{agent_path.name}: agent must accept DELEGATE (got {fm['accepts']})"
    )
    assert "HANDBACK" in fm["returns"], (
        f"{agent_path.name}: agent must return HANDBACK (got {fm['returns']})"
    )


# --------------------------------------------------------------------------- #
# src/AGENTS.md roster table integrity
# --------------------------------------------------------------------------- #

def _roster_rows():
    """
    Parse the roster table from src/AGENTS.md.

    Returns list of dict(role, model, effort) for the 8 specialist rows.
    The table header is: | Role | Model | Effort | Multi-Model? | Use When |
    """
    text = AGENTS_MD.read_text(encoding="utf-8")
    rows = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("| Role |") and "Model" in line and "Effort" in line:
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                break
            if set(line.replace("|", "").strip()) <= {"-", ":", " "}:
                continue  # separator row
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 3:
                continue
            role = cells[0].strip("*").strip()
            rows.append({"role": role, "model": cells[1], "effort": cells[2]})
    return rows


def test_agents_md_table_lists_all_8_roles():
    roles = {r["role"] for r in _roster_rows()}
    assert roles == EXPECTED_TABLE_ROLES, (
        f"src/AGENTS.md roster roles {sorted(roles)} != expected "
        f"{sorted(EXPECTED_TABLE_ROLES)}"
    )


def test_agents_md_table_models_are_canonical():
    for row in _roster_rows():
        model = row["model"]
        assert re.match(r"^claude-(haiku|sonnet|opus)-\d+\.\d+$", model), (
            f"src/AGENTS.md role '{row['role']}': model '{model}' is not a "
            "canonical dotted Claude id"
        )


def test_agents_md_table_effort_never_blank():
    valid_effort = {"low", "medium", "high", "max"}
    for row in _roster_rows():
        effort = row["effort"]
        assert effort and effort != "—", (
            f"src/AGENTS.md role '{row['role']}': effort is blank/em-dash"
        )
        assert effort in valid_effort, (
            f"src/AGENTS.md role '{row['role']}': effort '{effort}' not in "
            f"{sorted(valid_effort)}"
        )


# --------------------------------------------------------------------------- #
# Skill source integrity
# --------------------------------------------------------------------------- #

USER_SKILL_FILES = sorted(SRC_SKILLS.glob("*/SKILL.md"))


def test_24_user_skill_files_present():
    assert len(USER_SKILL_FILES) == 24, (
        f"Expected 24 user-facing src/skills/*/SKILL.md, found "
        f"{len(USER_SKILL_FILES)}: {[p.parent.name for p in USER_SKILL_FILES]}"
    )


@pytest.mark.parametrize(
    "skill_path", USER_SKILL_FILES, ids=lambda p: p.parent.name
)
def test_skill_frontmatter_required_fields(skill_path):
    fm = _parse_frontmatter(skill_path)
    for field in ("name", "description"):
        assert field in fm, (
            f"{skill_path.parent.name}/SKILL.md: missing required frontmatter "
            f"'{field}'"
        )
        assert str(fm[field]).strip(), (
            f"{skill_path.parent.name}/SKILL.md: frontmatter '{field}' is empty"
        )


# KNOWN SOURCE-INTEGRITY GAP (reported by this audit, NOT fixed here):
# [CLEARED 2026-06-08] All known skill name mismatches have been fixed.
_KNOWN_SKILL_NAME_MISMATCH = set()


@pytest.mark.parametrize(
    "skill_path", USER_SKILL_FILES, ids=lambda p: p.parent.name
)
def test_skill_name_matches_directory(skill_path, request):
    if skill_path.parent.name in _KNOWN_SKILL_NAME_MISMATCH:
        request.node.add_marker(
            pytest.mark.xfail(
                reason=(
                    "KNOWN GAP — SKILL.md 'name' does not match its directory; "
                    "audit reports, does not fix."
                ),
                strict=True,
            )
        )
    fm = _parse_frontmatter(skill_path)
    assert fm["name"] == skill_path.parent.name, (
        f"{skill_path.parent.name}/SKILL.md: name '{fm['name']}' != directory "
        f"'{skill_path.parent.name}'"
    )
