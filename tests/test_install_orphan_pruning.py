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


def _plant_cruft_and_nested_agents_md(skill_dir: Path) -> None:
    """Plant tests/__pycache__/.pytest_cache/*.pyc cruft an OLDER renderer
    version would have shipped into an already-installed managed skill dir
    before those patterns were excluded from the skill sync (rsync
    --exclude in the 3 bash renderers; the `ignore` callback in codex's
    copy_skill()) — invisible to `rsync --delete` in both directions because
    an EXCLUDED path is never treated as extraneous, so it was orphaned
    forever. Also plants a nested, user-authored AGENTS.md in the SAME dir,
    which must survive the exact same re-render untouched (nested-precedence
    contract, docs/RENDERING.md)."""
    (skill_dir / "tests").mkdir(parents=True, exist_ok=True)
    (skill_dir / "tests" / "test_foo.py").write_text("old test\n", encoding="utf-8")
    (skill_dir / "__pycache__").mkdir(parents=True, exist_ok=True)
    (skill_dir / "__pycache__" / "foo.pyc").write_text("bytecode\n", encoding="utf-8")
    (skill_dir / ".pytest_cache").mkdir(parents=True, exist_ok=True)
    (skill_dir / ".pytest_cache" / "marker").write_text("cache\n", encoding="utf-8")
    (skill_dir / "bar.pyc").write_text("loose pyc\n", encoding="utf-8")
    (skill_dir / "AGENTS.md").write_text("USER OWNED - DO NOT DELETE\n", encoding="utf-8")


@pytest.mark.parametrize("harness", list(HARNESS_RENDER))
class TestExcludedCruftCleanup:
    """FIX 3 regression pin (task-2026-08-15-fix-renderer-bugs).

    Background: the originally proposed fix was `rsync --delete-excluded`
    paired with `--filter='protect AGENTS.md'`. Empirical testing (required
    by the DELEGATE before touching the real renderer scripts) proved that
    combination unsafe on this project's actual `rsync`: macOS ships
    `openrsync` (BSD's replacement, protocol-29 "2.6.9 compatible") as
    /usr/bin/rsync, and in that implementation --delete-excluded silently
    disables ALL receiver-side protect/hide filter rules the instant it's
    present — not just the ones matching the same pattern. Shipping the
    suggested flags as-is would have deleted a user's nested AGENTS.md on
    every re-render. The shipped fix instead keeps the existing (already
    rsync-safe) plain --delete + --exclude invocation unchanged and adds a
    separate, rsync-implementation-independent cleanup pass
    (prune_excluded_cruft() in renderer/lib/render-lib.sh for the 3 bash
    renderers; codex's copy_skill() needs no equivalent step because it
    rmtree()s + rebuilds the whole skill dir from src on every render, so
    excluded cruft can never survive a re-render there in the first place —
    see the comment above copy_skill() in render-codex.py).

    Dual invariant pinned here, proven simultaneously in one re-render:
      (a) tests/__pycache__/.pytest_cache/*.pyc cruft planted into an
          ALREADY-INSTALLED managed skill dir is removed.
      (b) a nested user-authored AGENTS.md planted in the SAME dir survives
          the SAME re-render, byte-for-byte.
    """

    def test_cruft_removed_and_nested_agents_md_survives(self, tmp_path, harness):
        cmd_prefix, home_sub, _marker = HARNESS_RENDER[harness]
        home = tmp_path / home_sub

        _render(cmd_prefix, home)
        skill_dir = home / "skills" / REAL_SKILL_NAME
        assert skill_dir.is_dir(), (
            f"{harness}: expected currently-shipped skill '{REAL_SKILL_NAME}' to be installed"
        )

        _plant_cruft_and_nested_agents_md(skill_dir)
        assert (skill_dir / "tests").is_dir()
        assert (skill_dir / "__pycache__").is_dir()
        assert (skill_dir / ".pytest_cache").is_dir()
        assert (skill_dir / "bar.pyc").is_file()
        assert (skill_dir / "AGENTS.md").is_file()

        _render(cmd_prefix, home)

        assert not (skill_dir / "tests").exists(), f"{harness}: tests/ cruft survived re-render"
        assert not (skill_dir / "__pycache__").exists(), (
            f"{harness}: __pycache__/ cruft survived re-render"
        )
        assert not (skill_dir / ".pytest_cache").exists(), (
            f"{harness}: .pytest_cache/ cruft survived re-render"
        )
        assert not (skill_dir / "bar.pyc").exists(), f"{harness}: loose *.pyc cruft survived re-render"

        agents_md = skill_dir / "AGENTS.md"
        assert agents_md.is_file(), f"{harness}: nested user-authored AGENTS.md was wrongly removed"
        assert agents_md.read_text(encoding="utf-8") == "USER OWNED - DO NOT DELETE\n", (
            f"{harness}: nested AGENTS.md content was altered by the cruft-cleanup pass"
        )

        # The skill's own SKILL.md must still be present (proves the cleanup
        # pass didn't collaterally damage the managed skill it belongs to).
        assert (skill_dir / "SKILL.md").is_file()
