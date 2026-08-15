"""
Orphan agent pruning — regression evals.

Background: task-2026-08-15-fix-renderer-bugs FIX 4. The agent-install loop
in all 4 renderers builds AGENT_MANIFEST from ONLY the CURRENT
list_source_agents() names each run and writes it unconditionally — it never
revisited what's already installed to prune a managed agent .md/.toml file
whose source was renamed/deleted from src/agents/ by a later slimdown round.
This is the exact same class of bug prune_orphaned_skills() (see
tests/test_install_orphan_pruning.py) already fixed for skills, mirrored here
for agents via prune_orphaned_agents() in renderer/lib/render-lib.sh (bash:
render-claude.sh, render-opencode.sh) and the Python twins in
render-copilot-agents.py and render-codex.py.

Safety invariant pinned by these tests — mirrors the existing "skipping agent
X — foreign" guard already used by every renderer's install loop (agents have
no per-file marker like skills' SKILL_MARKER; manifest membership itself IS
the ours-vs-foreign boundary, since a dest file is refused only when it
exists and is NOT listed in the manifest):
  - a name that was NEVER in AGENT_MANIFEST is FOREIGN => must never be
    touched, no matter what its name looks like.
  - a name that WAS in AGENT_MANIFEST and is still a current source agent is
    CURRENT => must never be touched.
  - a name that WAS in AGENT_MANIFEST and is NOT a current source agent is an
    ORPHAN => safe to prune.

All tests render into a per-test tmp_path — never $HOME — mirroring
tests/test_install_orphan_pruning.py's direct-script-invocation pattern.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

ORPHAN_NAME = "totally-fake-orphan-agent"
FOREIGN_NAME = "totally-foreign-agent"

# A currently-shipped source agent, present for every harness, used to prove
# the prune step never touches an agent that's still in src/agents/.
REAL_AGENT_NAME = "orchestrator"

# (render command prefix, home-dir subpath under tmp_path, manifest filename,
#  dest-filename builder for a given agent base name)
HARNESS_AGENT_RENDER: dict[str, tuple[list[str], str, str, Callable[[str], str]]] = {
    "claude": (
        ["bash", str(REPO_ROOT / "renderer/scripts/render-claude.sh")],
        ".claude",
        ".agentic-engine-claude",
        lambda name: f"{name}.md",
    ),
    "opencode": (
        ["bash", str(REPO_ROOT / "renderer/scripts/render-opencode.sh")],
        "opencode",
        ".agentic-engine-opencode",
        lambda name: f"{name}.md",
    ),
    "copilot": (
        ["bash", str(REPO_ROOT / "renderer/scripts/render-copilot.sh")],
        ".copilot",
        ".agentic-engine-copilot",
        lambda name: f"{name}.agent.md",
    ),
    "codex": (
        ["python3", str(REPO_ROOT / "renderer/scripts/render-codex.py")],
        ".codex",
        ".agentic-engine-codex",
        lambda name: f"{name}.toml",
    ),
}

# render-copilot-agents.py manages names by the FULL source-file stem
# ("orchestrator-agent", from src/agents/orchestrator-agent.md), unlike the
# other 3 renderers, which strip the "-agent" suffix. ORPHAN_NAME/
# FOREIGN_NAME are already plain synthetic names (no real source file to
# match), so they're harness-agnostic; only REAL_AGENT_NAME (which must
# match an actual currently-shipped src/agents/*-agent.md) needs a
# per-harness manifest-name mapping.
REAL_AGENT_MANIFEST_NAME = {
    "claude": REAL_AGENT_NAME,
    "opencode": REAL_AGENT_NAME,
    "copilot": f"{REAL_AGENT_NAME}-agent",
    "codex": REAL_AGENT_NAME,
}


def _render(cmd_prefix: list[str], home: Path) -> subprocess.CompletedProcess:
    """Invoke a renderer's install mode directly against `home` (never $HOME)."""
    cmd = list(cmd_prefix) + [str(REPO_ROOT), str(home)]
    # The bash renderers take an explicit MODE positional; codex's default
    # (no flag) is already install.
    if cmd_prefix[0] == "bash":
        cmd.append("install")
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode == 0, (
        f"render failed: {cmd}\n"
        f"STDOUT:\n{result.stdout[-3000:]}\n\nSTDERR:\n{result.stderr[-3000:]}"
    )
    return result


@pytest.mark.parametrize("harness", list(HARNESS_AGENT_RENDER))
class TestOrphanAgentPruning:
    def test_orphaned_managed_agent_is_pruned(self, tmp_path, harness):
        cmd_prefix, home_sub, manifest_name, dest_filename = HARNESS_AGENT_RENDER[harness]
        home = tmp_path / home_sub

        _render(cmd_prefix, home)
        agents_dir = home / "agents"
        assert agents_dir.is_dir(), f"{harness}: agents/ not created by first render"

        manifest = agents_dir / manifest_name
        assert manifest.is_file(), f"{harness}: no AGENT_MANIFEST written by first render"

        # An agent WE would have installed on a prior render (name listed in
        # the manifest) whose source has since been deleted from src/agents/.
        with manifest.open("a", encoding="utf-8") as f:
            f.write(f"{ORPHAN_NAME}\n")
        orphan_file = agents_dir / dest_filename(ORPHAN_NAME)
        orphan_file.write_text("orphaned managed agent content\n", encoding="utf-8")

        result = _render(cmd_prefix, home)

        assert not orphan_file.exists(), (
            f"{harness}: orphaned managed agent file was not pruned on re-render"
        )
        assert f"pruned 1 orphaned managed agent(s): {ORPHAN_NAME}" in result.stdout, (
            f"{harness}: missing/incorrect agent orphan-prune report line:\n{result.stdout[-1500:]}"
        )
        # The orphan name must not linger in the rewritten manifest either.
        assert ORPHAN_NAME not in manifest.read_text(encoding="utf-8").splitlines(), (
            f"{harness}: orphan name still present in AGENT_MANIFEST after prune"
        )

    def test_foreign_unmanaged_agent_survives(self, tmp_path, harness):
        cmd_prefix, home_sub, _manifest_name, dest_filename = HARNESS_AGENT_RENDER[harness]
        home = tmp_path / home_sub

        _render(cmd_prefix, home)
        agents_dir = home / "agents"

        # A user-owned agent file that was NEVER listed in the manifest —
        # must never be touched, even though its name is not a current
        # source agent either.
        foreign_file = agents_dir / dest_filename(FOREIGN_NAME)
        foreign_file.write_text("do not touch\n", encoding="utf-8")

        _render(cmd_prefix, home)

        assert foreign_file.exists(), (
            f"{harness}: foreign (unmanaged) agent file was wrongly removed by the prune step"
        )
        assert foreign_file.read_text(encoding="utf-8") == "do not touch\n", (
            f"{harness}: foreign agent file contents were altered by the prune step"
        )

    def test_current_source_agent_survives(self, tmp_path, harness):
        cmd_prefix, home_sub, _manifest_name, dest_filename = HARNESS_AGENT_RENDER[harness]
        home = tmp_path / home_sub

        _render(cmd_prefix, home)
        agents_dir = home / "agents"
        real_agent = agents_dir / dest_filename(REAL_AGENT_MANIFEST_NAME[harness])
        assert real_agent.is_file(), (
            f"{harness}: expected currently-shipped agent '{REAL_AGENT_NAME}' to be installed"
        )

        # Re-render with nothing planted: the prune step must be a no-op for
        # every agent that's still in src/agents/.
        result = _render(cmd_prefix, home)

        assert real_agent.is_file(), (
            f"{harness}: current source agent '{REAL_AGENT_NAME}' was pruned"
        )
        assert "pruned 0 orphaned managed agent(s)" in result.stdout, (
            f"{harness}: expected a 0-orphan agent report line on a clean re-render:\n{result.stdout[-1500:]}"
        )
