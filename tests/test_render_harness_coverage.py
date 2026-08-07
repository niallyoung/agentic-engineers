"""
Render-correctness coverage evals.

Guarantees that `make render-all` produces a complete, well-formed distribution
for every harness:

  - all 8 specialist agents are rendered per harness (claude/copilot/opencode)
  - all 27 user-facing skills are rendered per harness
  - generated framework docs (CLAUDE.md, AGENTS.md, opencode.jsonc, pi SYSTEM.md)
    are present in dist/ after render
  - every rendered agent carries a non-empty model and description (never "—")

These complement the existing render-pipeline tests (which check naming
conventions and library wiring) by asserting *completeness and content* of the
rendered output the installers consume.

The module renders once (session-scoped) into the repo's real dist/ via
`make render-all`, then asserts against dist/. Rendering is idempotent and dist/
is gitignored, so this is safe.
"""

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST = REPO_ROOT / "dist"

# Canonical source format for a Claude model id. Two version shapes are valid:
#   - two-part  claude-haiku-4.5, claude-opus-4.8   (DOT separator)
#   - one-part  claude-opus-5, claude-sonnet-5, claude-fable-5
# The invariant is "the version separator is a DOT, never a hyphen". A
# single-part version has no separator at all, so it need not contain a dot.
CANONICAL_MODEL_RE = re.compile(r"^claude-(haiku|sonnet|opus|fable)-\d+(\.\d+)?$")

# The 8 canonical specialist roles (source basename without -agent.md).
EXPECTED_ROLES = {
    "orchestrator",
    "engineer",
    "senior-engineer",
    "lead-engineer",
    "quality-engineer",
    "principal-engineer",
    "security-engineer",
    "model-engineer",
}

# Harnesses that render one markdown file per agent into dist/<h>/agents/.
PER_FILE_AGENT_HARNESSES = ("claude", "copilot", "opencode")


def _source_skill_names():
    """User-facing skills = src/skills/*/SKILL.md, excluding the _meta tree."""
    names = set()
    for skill_md in (REPO_ROOT / "src" / "skills").glob("*/SKILL.md"):
        names.add(skill_md.parent.name)
    return names


def _frontmatter(text):
    """Return the YAML frontmatter block (between the first two '---') or ''."""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    if end == -1:
        return ""
    return text[3:end]


@pytest.fixture(scope="module", autouse=True)
def _render_all():
    """Render every harness once before this module's tests run."""
    result = subprocess.run(
        ["make", "render-all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "make render-all failed:\n"
        f"STDOUT:\n{result.stdout[-3000:]}\n\nSTDERR:\n{result.stderr[-3000:]}"
    )
    yield


def test_source_has_exactly_27_user_skills():
    names = _source_skill_names()
    assert len(names) == 27, (
        f"Expected 27 user-facing skills in src/skills/, found {len(names)}: "
        f"{sorted(names)}"
    )


def test_source_has_exactly_8_agents():
    agents = {
        p.stem.replace("-agent", "")
        for p in (REPO_ROOT / "src" / "agents").glob("*-agent.md")
    }
    assert agents == EXPECTED_ROLES, (
        f"src/agents/*-agent.md roles {sorted(agents)} != expected "
        f"{sorted(EXPECTED_ROLES)}"
    )


@pytest.mark.parametrize("harness", PER_FILE_AGENT_HARNESSES)
def test_harness_renders_all_8_agents(harness):
    agents_dir = DIST / harness / "agents"
    assert agents_dir.is_dir(), f"dist/{harness}/agents/ missing after render"

    rendered = list(agents_dir.glob("*.md"))
    # Map each rendered file back to a role by checking which expected role
    # its filename starts with (copilot uses <role>-agent.agent.md, others <role>.md).
    found_roles = set()
    for f in rendered:
        stem = f.name
        for role in EXPECTED_ROLES:
            if stem == f"{role}.md" or stem == f"{role}-agent.agent.md":
                found_roles.add(role)
    missing = EXPECTED_ROLES - found_roles
    assert not missing, (
        f"dist/{harness}/agents/ is missing rendered agents for roles: "
        f"{sorted(missing)} (found files: {sorted(p.name for p in rendered)})"
    )


@pytest.mark.parametrize("harness", PER_FILE_AGENT_HARNESSES)
def test_harness_renders_all_25_skills(harness):
    skills_dir = DIST / harness / "skills"
    assert skills_dir.is_dir(), f"dist/{harness}/skills/ missing after render"

    source = _source_skill_names()
    rendered = {
        p.name for p in skills_dir.iterdir() if p.is_dir() and (p / "SKILL.md").exists()
    }
    missing = source - rendered
    assert not missing, (
        f"dist/{harness}/skills/ is missing rendered skills (with SKILL.md): "
        f"{sorted(missing)}"
    )
    assert len(rendered) >= 23, (
        f"dist/{harness}/skills/ rendered only {len(rendered)} skills; expected >= 23"
    )


@pytest.mark.parametrize(
    "harness,docs",
    [
        ("claude", ["CLAUDE.md", "AGENTS.md"]),
        ("copilot", ["AGENTS.md"]),
        ("opencode", ["AGENTS.md", "opencode.jsonc"]),
    ],
)
def test_harness_renders_framework_docs(harness, docs):
    for doc in docs:
        path = DIST / harness / doc
        assert path.is_file(), f"dist/{harness}/{doc} not produced by render"
        assert path.stat().st_size > 0, f"dist/{harness}/{doc} is empty"


def test_pi_renders_system_and_config():
    agent_dir = DIST / "pi" / "agent"
    for doc in ("SYSTEM.md", "pi.yml", "AGENTS.md"):
        path = agent_dir / doc
        assert path.is_file(), f"dist/pi/agent/{doc} not produced by render"
        assert path.stat().st_size > 0, f"dist/pi/agent/{doc} is empty"


@pytest.mark.parametrize("harness", PER_FILE_AGENT_HARNESSES)
def test_rendered_agents_have_nonempty_model_and_description(harness):
    """Every rendered agent must carry a real model + description, never '—'/empty."""
    agents_dir = DIST / harness / "agents"
    for agent_file in agents_dir.glob("*.md"):
        fm = _frontmatter(agent_file.read_text(encoding="utf-8"))
        assert fm, f"{harness}/{agent_file.name}: no YAML frontmatter found"

        model_match = re.search(r"(?m)^model:\s*(.+)$", fm)
        assert model_match, f"{harness}/{agent_file.name}: missing 'model:' field"
        model_val = model_match.group(1).strip().strip("\"'")
        assert model_val and model_val != "—", (
            f"{harness}/{agent_file.name}: model is empty/em-dash ('{model_val}')"
        )

        desc_match = re.search(r"(?m)^description:\s*(.+)$", fm)
        assert desc_match, f"{harness}/{agent_file.name}: missing 'description:' field"
        desc_val = desc_match.group(1).strip().strip("\"'")
        assert desc_val and desc_val != "—", (
            f"{harness}/{agent_file.name}: description is empty/em-dash ('{desc_val}')"
        )


@pytest.mark.parametrize("harness", PER_FILE_AGENT_HARNESSES)
def test_rendered_models_are_harness_appropriate(harness):
    """
    Sanity-check the model id *shape* per harness:
      - opencode prefixes provider (github-copilot/...) and uses hyphenated versions
      - copilot uses dotted versioned ids (claude-<tier>-N.N)
      - claude uses bare aliases (haiku/sonnet/opus) or dotted ids
    """
    agents_dir = DIST / harness / "agents"
    for agent_file in agents_dir.glob("*.md"):
        fm = _frontmatter(agent_file.read_text(encoding="utf-8"))
        model_val = re.search(r"(?m)^model:\s*(.+)$", fm).group(1).strip().strip("\"'")

        if harness == "opencode":
            assert "/" in model_val, (
                f"opencode/{agent_file.name}: model '{model_val}' should be "
                "provider-prefixed (e.g. github-copilot/...)"
            )
        elif harness == "copilot":
            assert CANONICAL_MODEL_RE.match(model_val), (
                f"copilot/{agent_file.name}: model '{model_val}' is not a "
                "canonical versioned Claude id"
            )
        elif harness == "claude":
            assert re.match(r"^(haiku|sonnet|opus|fable)$", model_val) or re.match(
                r"^claude-(haiku|sonnet|opus|fable)", model_val
            ), f"claude/{agent_file.name}: unexpected model id '{model_val}'"
