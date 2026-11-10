"""
The Security Engineer's defensive-only scope constraint must reach the prompt
each harness actually delivers.

The constraint used to live only in the ``model_guidance`` frontmatter key of
src/agents/security-engineer-agent.md. Every renderer drops that key (Claude
and OpenCode rebuild the frontmatter from a fixed key list, Copilot and Codex
likewise), so no rendered Security Engineer prompt carried the constraint at
all, while src/AGENTS.md stated that it "is enforced by the Security
Engineer's own system prompt". These tests pin the constraint to the agent
*body*, which all four renderers carry, and assert it on the rendered output
rather than on the source.

Rendering is done from a throwaway copy of the repo into temp directories:
the renderers have side effects on the tree they are pointed at (git hook
configuration) and on dist/, and neither belongs to a test.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Stable, single-line phrases from the constraint. Each must survive every
# renderer verbatim, so none of them spans a line break in the source.
SCOPE_HEADING = "## Defensive-Only Scope"
RESTRICTED_TOPICS = "offensive tooling, exploit development, attack automation"
EVERY_MODEL = "OUT OF SCOPE on every model"
REFUSAL_RULE = "refuse it in your own output"

SECURITY_MARKERS = (SCOPE_HEADING, RESTRICTED_TOPICS, EVERY_MODEL, REFUSAL_RULE)

# The Orchestrator's matching rule: restricted-topic requests are rejected at
# routing time rather than delegated.
ORCHESTRATOR_MARKERS = (RESTRICTED_TOPICS, "REJECT")

HARNESS_AGENT_FILE = {
    "claude": "agents/{role}.md",
    "copilot": "agents/{role}-agent.agent.md",
    "opencode": "agents/{role}.md",
    "codex": "agents/{role}.toml",
}


def _body(text):
    """Return ``text`` with a leading YAML frontmatter block removed."""
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    return text if end == -1 else text[end + 4:]


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    """Render all four harnesses from a copy of the repo; return {harness: dir}."""
    base = tmp_path_factory.mktemp("defensive-scope")
    repo = base / "repo"
    shutil.copytree(
        REPO_ROOT, repo,
        ignore=shutil.ignore_patterns(
            ".git", "dist", "__pycache__", ".pytest_cache", "*.pyc", "node_modules", "htmlcov"
        ),
    )
    subprocess.run(["git", "init", "-q", str(repo)], check=True)

    home = base / "home"
    home.mkdir()
    env = {
        **os.environ,
        "NO_COLOR": "1",
        "HOME": str(home),
        "XDG_CACHE_HOME": str(base / "xdg-cache"),
        "OPENCODE_MODELS_CACHE": str(base / "xdg-cache" / "opencode" / "models.json"),
        "OPENCODE_PROVIDER": "anthropic",
    }
    scripts = repo / "renderer" / "scripts"
    out = {h: base / "out" / h for h in HARNESS_AGENT_FILE}
    commands = {
        "claude": ["bash", str(scripts / "render-claude.sh"), str(repo), str(out["claude"])],
        "copilot": ["bash", str(scripts / "render-copilot.sh"), str(repo), str(out["copilot"])],
        "opencode": ["bash", str(scripts / "render-opencode.sh"), str(repo), str(out["opencode"])],
        "codex": [
            "python3", str(scripts / "render-codex.py"), str(repo), str(out["codex"]),
            "--skills-root", str(out["codex"] / "skills"),
        ],
    }
    for harness, cmd in commands.items():
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=repo, timeout=300)
        assert result.returncode == 0, (
            f"{harness} render failed:\nSTDOUT:\n{result.stdout[-2000:]}\n"
            f"STDERR:\n{result.stderr[-2000:]}"
        )
    return out


def _rendered_agent(rendered, harness, role):
    path = rendered[harness] / HARNESS_AGENT_FILE[harness].format(role=role)
    assert path.exists(), f"{harness} did not render {role} at {path}"
    return path.read_text(encoding="utf-8")


class TestSourceCarriesConstraintInBody:
    def test_constraint_is_in_the_security_engineer_body_not_only_frontmatter(self):
        source = (REPO_ROOT / "src" / "agents" / "security-engineer-agent.md").read_text()
        body = _body(source)
        for marker in SECURITY_MARKERS:
            assert marker in body, (
                f"{marker!r} is missing from the Security Engineer agent body. "
                "Frontmatter keys other than the renderers' fixed lists are dropped, "
                "so the constraint must live in the body."
            )

    def test_body_does_not_point_at_dropped_frontmatter(self):
        body = _body((REPO_ROOT / "src" / "agents" / "security-engineer-agent.md").read_text())
        assert "model_guidance" not in body, (
            "the body refers the reader to model_guidance, a frontmatter key no "
            "rendered prompt contains"
        )

    def test_constraint_sits_above_the_integration_section(self):
        # render-claude.sh deletes everything from '## Integration' onward.
        body = _body((REPO_ROOT / "src" / "agents" / "security-engineer-agent.md").read_text())
        assert body.index(SCOPE_HEADING) < body.index("\n## Integration")


@pytest.mark.parametrize("harness", sorted(HARNESS_AGENT_FILE))
class TestRenderedPromptsCarryConstraint:
    def test_security_engineer_prompt_carries_defensive_only_constraint(self, rendered, harness):
        text = _rendered_agent(rendered, harness, "security-engineer")
        # Codex embeds the prompt in a TOML string; the other three are
        # markdown whose frontmatter is not part of the delivered prompt.
        prompt = text if harness == "codex" else _body(text)
        for marker in SECURITY_MARKERS:
            assert marker in prompt, (
                f"{harness}: rendered Security Engineer prompt is missing {marker!r} — "
                "the defensive-only scope constraint is not being delivered"
            )

    def test_orchestrator_prompt_carries_reject_rule(self, rendered, harness):
        text = _rendered_agent(rendered, harness, "orchestrator")
        prompt = text if harness == "codex" else _body(text)
        for marker in ORCHESTRATOR_MARKERS:
            assert marker in prompt, (
                f"{harness}: rendered Orchestrator prompt is missing {marker!r} — "
                "restricted-topic requests would be routed instead of rejected"
            )
