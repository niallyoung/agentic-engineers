"""
Leaf roles must not be able to spawn sub-agents on Claude Code.

src/AGENTS.md states that Engineer and Quality Engineer are leaves. Before this
test existed that was prompt-only: render-claude.sh dropped the source `tools:`
key, so every rendered agent inherited the full tool set. The renderer now
writes `disallowedTools` for any agent whose source frontmatter declares
`tools: []`. These tests pin that on the rendered output, not on the source.

Rendering happens in a throwaway copy of the repo so the test never touches
dist/ or the git configuration of the working tree.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SPAWN_TOOLS = "disallowedTools: Agent, Task, SendMessage"


def _frontmatter(text: str) -> str:
    assert text.startswith("---\n"), "rendered agent has no frontmatter"
    end = text.index("\n---", 4)
    return text[4:end]


@pytest.fixture(scope="module")
def rendered_claude(tmp_path_factory):
    base = tmp_path_factory.mktemp("claude-tool-denial")
    repo = base / "repo"
    shutil.copytree(
        REPO_ROOT, repo,
        ignore=shutil.ignore_patterns(
            ".git", "dist", "__pycache__", ".pytest_cache", "*.pyc", "htmlcov"
        ),
    )
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    out = base / "out"
    result = subprocess.run(
        ["bash", str(repo / "renderer" / "scripts" / "render-claude.sh"), str(repo), str(out)],
        capture_output=True, text=True, cwd=repo, timeout=300,
        env={**os.environ, "NO_COLOR": "1", "HOME": str(base / "home"),
             "XDG_CACHE_HOME": str(base / "xdg-cache")},
    )
    assert result.returncode == 0, result.stdout[-1500:] + result.stderr[-1500:]
    agents = out / "agents"
    assert agents.is_dir(), f"no agents rendered:\n{result.stdout[-1500:]}"
    return agents


LEAVES = ("engineer", "quality-engineer")
SPAWNERS = ("orchestrator", "senior-engineer", "lead-engineer", "principal-engineer", "security-engineer")


@pytest.mark.parametrize("role", LEAVES)
def test_leaf_roles_deny_spawn_tools(rendered_claude, role):
    fm = _frontmatter((rendered_claude / f"{role}.md").read_text(encoding="utf-8"))
    assert SPAWN_TOOLS in fm.splitlines(), f"{role} frontmatter lacks the spawn denial:\n{fm}"


@pytest.mark.parametrize("role", SPAWNERS)
def test_spawner_roles_keep_default_tools(rendered_claude, role):
    fm = _frontmatter((rendered_claude / f"{role}.md").read_text(encoding="utf-8"))
    assert "disallowedTools" not in fm, f"{role} must keep spawn authority:\n{fm}"


def test_every_rendered_agent_is_classified(rendered_claude):
    """A new agent must be added to LEAVES or SPAWNERS, so its tool stance is decided."""
    names = {p.stem for p in rendered_claude.glob("*.md")}
    assert names == set(LEAVES) | set(SPAWNERS)
