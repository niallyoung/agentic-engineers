"""
Nested-AGENTS.md precedence contract — regression evals.

Background: the AGENTS.md convention (stewarded by AAIF/Linux Foundation since
Dec 2025; see docs/LANDSCAPE.md "Standards Alignment") treats nested AGENTS.md
files as a monorepo pattern where the nearest file to the edited path takes
precedence (documented behaviorally at https://agents.md/; formalized as an
open, unmerged community proposal in agentsmd/agents.md#135, "v1.0" has not
been tagged as of this writing). Our renderers emit exactly one AGENTS.md per
harness install (the root doc, protected by write_managed_doc()'s sentinel
check) — we do not build a nesting engine. What we DO owe the convention is
this: never destroy a user-authored AGENTS.md that happens to live deeper in
the install tree (e.g. inside an installed skill directory), since a user
placing one there is exactly the nested-precedence pattern the standard
describes.

A live test during implementation found that render-claude.sh, render-
opencode.sh (both `rsync -a --delete ...`) and render-codex.py's copy_skill()
(`shutil.rmtree()` + `shutil.copytree()`) all deleted such a file
unconditionally on re-render, because it is "extraneous" relative to the
skill's src/ contents (no src skill ships an AGENTS.md of its own). These
tests pin the fix: a nested, user-authored AGENTS.md placed inside an
installed skill directory must survive a re-render. See docs/RENDERING.md
"Nested AGENTS.md Precedence Contract" for the documented behavior.

Renderers covered: all four — claude, opencode, copilot (same rsync
--exclude fix, commit 1aa490f), and codex (stash/restore in copy_skill()).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

NESTED_MARKER_TEXT = "# user-authored nested AGENTS.md — must survive re-render\n"


def _first_installed_skill(skills_dir: Path) -> str:
    names = sorted(p.name for p in skills_dir.iterdir() if p.is_dir())
    assert names, f"no skills rendered under {skills_dir}"
    return names[0]


def _plant_and_rerender(render_cmd: list[str], skills_dir: Path) -> Path:
    """Render once, plant a nested AGENTS.md in the first installed skill,
    re-render, and return the path to the (hopefully still-present) file."""
    first = subprocess.run(render_cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert first.returncode == 0, (
        f"first render failed: {render_cmd}\n"
        f"STDOUT:\n{first.stdout[-2000:]}\n\nSTDERR:\n{first.stderr[-2000:]}"
    )

    skill_name = _first_installed_skill(skills_dir)
    nested = skills_dir / skill_name / "AGENTS.md"
    nested.write_text(NESTED_MARKER_TEXT, encoding="utf-8")

    second = subprocess.run(render_cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert second.returncode == 0, (
        f"second render failed: {render_cmd}\n"
        f"STDOUT:\n{second.stdout[-2000:]}\n\nSTDERR:\n{second.stderr[-2000:]}"
    )
    return nested


class TestNoSourceSkillShipsAgentsMd:
    """Precondition the fix relies on: if a src skill ever legitimately ships
    its own AGENTS.md, the "any nested AGENTS.md is foreign" assumption below
    breaks and the exclude/preserve logic would need to special-case it."""

    def test_no_src_skill_has_nested_agents_md(self):
        hits = list((REPO_ROOT / "src" / "skills").rglob("AGENTS.md"))
        assert not hits, (
            "src/skills/ now ships a nested AGENTS.md — the renderer fixes in "
            "render-claude.sh / render-opencode.sh / render-codex.py assume this "
            "never happens; revisit the exclude/preserve logic: "
            f"{[str(p) for p in hits]}"
        )


class TestClaudeRendererPreservesNestedAgentsMd:
    def test_nested_agents_md_survives_rerender(self, tmp_path):
        claude_home = tmp_path / ".claude"
        render_cmd = [
            "bash",
            str(REPO_ROOT / "renderer/scripts/render-claude.sh"),
            str(REPO_ROOT),
            str(claude_home),
            "install",
        ]
        nested = _plant_and_rerender(render_cmd, claude_home / "skills")
        assert nested.exists(), "render-claude.sh deleted a nested, user-authored AGENTS.md"
        assert nested.read_text(encoding="utf-8") == NESTED_MARKER_TEXT


class TestOpenCodeRendererPreservesNestedAgentsMd:
    def test_nested_agents_md_survives_rerender(self, tmp_path):
        oc_home = tmp_path / "opencode"
        render_cmd = [
            "bash",
            str(REPO_ROOT / "renderer/scripts/render-opencode.sh"),
            str(REPO_ROOT),
            str(oc_home),
            "install",
        ]
        nested = _plant_and_rerender(render_cmd, oc_home / "skills")
        assert nested.exists(), "render-opencode.sh deleted a nested, user-authored AGENTS.md"
        assert nested.read_text(encoding="utf-8") == NESTED_MARKER_TEXT


class TestCopilotRendererPreservesNestedAgentsMd:
    def test_nested_agents_md_survives_rerender(self, tmp_path):
        copilot_home = tmp_path / ".copilot"
        render_cmd = [
            "bash",
            str(REPO_ROOT / "renderer/scripts/render-copilot.sh"),
            str(REPO_ROOT),
            str(copilot_home),
            "install",
        ]
        nested = _plant_and_rerender(render_cmd, copilot_home / "skills")
        assert nested.exists(), "render-copilot.sh deleted a nested, user-authored AGENTS.md"
        assert nested.read_text(encoding="utf-8") == NESTED_MARKER_TEXT


class TestCodexRendererPreservesNestedAgentsMd:
    def test_nested_agents_md_survives_rerender(self, tmp_path):
        codex_home = tmp_path / ".codex"
        render_cmd = [
            "python3",
            str(REPO_ROOT / "renderer/scripts/render-codex.py"),
            str(REPO_ROOT),
            str(codex_home),
        ]
        nested = _plant_and_rerender(render_cmd, codex_home / "skills")
        assert nested.exists(), "render-codex.py's copy_skill() deleted a nested, user-authored AGENTS.md"
        assert nested.read_text(encoding="utf-8") == NESTED_MARKER_TEXT


@pytest.mark.parametrize(
    "script,expected_exclude",
    [
        ("render-claude.sh", "--exclude='AGENTS.md'"),
        ("render-opencode.sh", "--exclude='AGENTS.md'"),
        ("render-copilot.sh", "--exclude='AGENTS.md'"),
    ],
)
def test_rsync_skill_sync_excludes_agents_md(script, expected_exclude):
    """Static guard: the rsync --delete skill-sync line must exclude AGENTS.md
    so a future edit can't silently reintroduce the clobber bug."""
    content = (REPO_ROOT / "renderer" / "scripts" / script).read_text(encoding="utf-8")
    rsync_lines = [line for line in content.splitlines() if "rsync -a --delete" in line]
    assert rsync_lines, f"{script}: no `rsync -a --delete` skill-sync line found (script structure changed?)"
    for line in rsync_lines:
        assert expected_exclude in line, (
            f"{script}: rsync skill-sync line is missing {expected_exclude} — "
            f"nested AGENTS.md would be deleted on re-render:\n{line}"
        )


def test_codex_copy_skill_preserves_agents_md_source():
    """Static guard: copy_skill() must stash/restore AGENTS.md around the
    rmtree()+copytree() cycle (no rsync-exclude equivalent available here)."""
    content = (REPO_ROOT / "renderer" / "scripts" / "render-codex.py").read_text(encoding="utf-8")
    start = content.index("def copy_skill(")
    end = content.index("\ndef ", start + 1)
    body = content[start:end]
    assert "AGENTS.md" in body, (
        "copy_skill() no longer mentions AGENTS.md — the preserve/restore logic "
        "protecting nested user files across rmtree()+copytree() may have been removed"
    )
    assert "rglob" in body and "preserved" in body, (
        "copy_skill() no longer stashes files before rmtree() — nested AGENTS.md "
        "would be deleted on re-render"
    )
