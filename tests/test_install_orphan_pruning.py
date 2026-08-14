"""
Orphan skill pruning — regression evals.

Background: task-2026-08-15-orphan-skill-pruning. All 4 renderers' install
loop iterates ONLY the current src/skills/ names ("for name in
$(list_source_skills); do ... done" / the Python equivalent) and syncs/marks
those — it never revisits what's already installed to prune marker-tagged
(managed) skill directories whose source was deleted by a later slimdown
round. Real-world damage found on the operator's machine: dozens of
orphaned-but-marked skill dirs had accumulated across all 4 harness skill
directories after several skill-set slimdown rounds (queue-management/
queue-query removal, cost/model-selection consolidation, etc.), while two
genuinely foreign (unmarked) skills the operator owns personally sat
alongside them untouched — proof the existing foreign-file guard was already
doing its job; only the orphan case was unhandled.

Safety invariant pinned by these tests — mirrors the existing "skipping
skill X — foreign" guard already used by every renderer's install loop, not a
reinvention of it:
  - a directory that does NOT carry the renderer's SKILL_MARKER is FOREIGN
    => must never be touched, no matter what its name looks like.
  - a directory that DOES carry the marker and is still a current source
    skill is CURRENT => must never be touched.
  - a directory that DOES carry the marker and is NOT a current source
    skill is an ORPHAN => safe to prune.

Renderers covered: claude, opencode, copilot (share the bash
prune_orphaned_skills() helper added to renderer/lib/render-lib.sh) and codex
(Python CodexRenderer.prune_orphaned_skills() in render-codex.py).

All tests render into a per-test tmp_path — never $HOME — mirroring the
direct-script-invocation pattern in tests/test_agents_md_nesting.py rather
than the shared `make install` fixture in tests/test_install_correctness.py,
so planting fake orphan/foreign dirs here can't interfere with other tests.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

ORPHAN_NAME = "totally-fake-orphan-skill"
FOREIGN_NAME = "totally-foreign-skill"

# A currently-shipped source skill, present for every harness, used to prove
# the prune step never touches a skill that's still in src/skills/.
REAL_SKILL_NAME = "orchestrator"

# (render command prefix, home-dir subpath under tmp_path, marker filename,
#  marker file contents)
HARNESS_RENDER = {
    "claude": (
        ["bash", str(REPO_ROOT / "renderer/scripts/render-claude.sh")],
        ".claude",
        ".agentic-engine-claude",
    ),
    "opencode": (
        ["bash", str(REPO_ROOT / "renderer/scripts/render-opencode.sh")],
        "opencode",
        ".agentic-engine-opencode",
    ),
    "copilot": (
        ["bash", str(REPO_ROOT / "renderer/scripts/render-copilot.sh")],
        ".copilot",
        ".agentic-engine-copilot",
    ),
    "codex": (
        ["python3", str(REPO_ROOT / "renderer/scripts/render-codex.py")],
        ".codex",
        ".agentic-engine-codex",
    ),
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


def _plant_orphan(skills_dir: Path, marker: str) -> Path:
    """A skill dir WE would have installed on a prior render (carries our
    marker) whose source has since been deleted from src/skills/."""
    orphan = skills_dir / ORPHAN_NAME
    orphan.mkdir(parents=True, exist_ok=True)
    (orphan / marker).write_text("2026-01-01T00:00:00Z\n", encoding="utf-8")
    (orphan / "SKILL.md").write_text("---\nname: orphan\n---\nstub\n", encoding="utf-8")
    return orphan


def _plant_foreign(skills_dir: Path) -> Path:
    """A user-owned dir with no marker at all — must never be touched, even
    though its name is not a current source skill either."""
    foreign = skills_dir / FOREIGN_NAME
    foreign.mkdir(parents=True, exist_ok=True)
    (foreign / "my-own-file.txt").write_text("do not touch\n", encoding="utf-8")
    return foreign


@pytest.mark.parametrize("harness", list(HARNESS_RENDER))
class TestOrphanSkillPruning:
    def test_orphaned_managed_skill_is_pruned(self, tmp_path, harness):
        cmd_prefix, home_sub, marker = HARNESS_RENDER[harness]
        home = tmp_path / home_sub

        _render(cmd_prefix, home)
        skills_dir = home / "skills"
        assert skills_dir.is_dir(), f"{harness}: skills/ not created by first render"

        orphan = _plant_orphan(skills_dir, marker)
        assert orphan.is_dir()

        result = _render(cmd_prefix, home)

        assert not orphan.exists(), (
            f"{harness}: orphaned marker-tagged skill dir was not pruned on re-render"
        )
        # The report line must be printed even though there is no separate
        # --dry-run flag on these scripts (DELEGATE requirement: dry-run-safe
        # reporting, always visible to the operator).
        assert "pruned 1 orphaned managed skill(s): " + ORPHAN_NAME in result.stdout, (
            f"{harness}: missing/incorrect orphan-prune report line:\n{result.stdout[-1500:]}"
        )

    def test_foreign_unmarked_dir_survives(self, tmp_path, harness):
        cmd_prefix, home_sub, _marker = HARNESS_RENDER[harness]
        home = tmp_path / home_sub

        _render(cmd_prefix, home)
        skills_dir = home / "skills"

        foreign = _plant_foreign(skills_dir)

        _render(cmd_prefix, home)

        assert foreign.exists(), (
            f"{harness}: foreign (unmarked) skill dir was wrongly removed by the prune step"
        )
        marker_file = foreign / "my-own-file.txt"
        assert marker_file.exists() and marker_file.read_text(encoding="utf-8") == "do not touch\n", (
            f"{harness}: foreign skill dir contents were altered by the prune step"
        )

    def test_current_source_skill_survives(self, tmp_path, harness):
        cmd_prefix, home_sub, _marker = HARNESS_RENDER[harness]
        home = tmp_path / home_sub

        _render(cmd_prefix, home)
        skills_dir = home / "skills"
        real_skill = skills_dir / REAL_SKILL_NAME
        assert real_skill.is_dir(), (
            f"{harness}: expected currently-shipped skill '{REAL_SKILL_NAME}' to be installed"
        )

        # Re-render with nothing planted: the prune step must be a no-op for
        # every skill that's still in src/skills/.
        result = _render(cmd_prefix, home)

        assert real_skill.is_dir(), (
            f"{harness}: current source skill '{REAL_SKILL_NAME}' was pruned"
        )
        assert (real_skill / "SKILL.md").is_file()
        assert "pruned 0 orphaned managed skill(s)" in result.stdout, (
            f"{harness}: expected a 0-orphan report line on a clean re-render:\n{result.stdout[-1500:]}"
        )
