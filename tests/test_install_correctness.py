"""
Install-pipeline correctness evals.

After `make install DESTDIR=<tmp>` the installed harness trees must:

  - match dist/<harness>/ content byte-for-byte (excluding per-harness marker
    files, whose timestamps legitimately differ)
  - carry a managed-files marker (.agentic-engine-<harness>) so the installer
    can later remove only its own files
  - preserve foreign (user-authored) files on re-install (non-regression)

All tests run against a temporary DESTDIR, never the live ~/ harness dirs.
The install is performed once (session-scoped) because it is slow.
"""

import filecmp
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# (harness key, dist subdir, installed subdir relative to DESTDIR, marker filename)
HARNESS_LAYOUT = {
    "claude": ("claude", ".claude", ".agentic-engine-claude"),
    "copilot": ("copilot", ".copilot", ".agentic-engine-copilot"),
    "opencode": ("opencode", ".config/opencode", ".agentic-engine-opencode"),
}

# Files that legitimately differ between dist/ and installed/ (marker
# timestamps, and settings.json, whose claude-delegate-guard.py hook command
# embeds the DESTDIR-specific absolute install path rather than dist/'s).
IGNORED_NAMES = {
    ".agentic-engine-claude",
    ".agentic-engine-copilot",
    ".agentic-engine-opencode",
    "settings.json",
}


@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    """Render + install all 4 harnesses into a throwaway DESTDIR."""
    destdir = tmp_path_factory.mktemp("pe-install")
    result = subprocess.run(
        ["make", "install", f"DESTDIR={destdir}", "BACKUP=never"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "make install failed:\n"
        f"STDOUT:\n{result.stdout[-3000:]}\n\nSTDERR:\n{result.stderr[-3000:]}"
    )
    return destdir


def _diff_trees(dist_dir: Path, installed_dir: Path):
    """
    Return a list of mismatches between dist_dir and installed_dir, ignoring
    marker files. Each mismatch is a human-readable string.

    Only checks that every dist file exists and is identical in installed_dir
    (installed may legitimately contain extra files such as markers).
    """
    mismatches = []
    for dist_file in dist_dir.rglob("*"):
        if not dist_file.is_file():
            continue
        if dist_file.name in IGNORED_NAMES:
            continue
        rel = dist_file.relative_to(dist_dir)
        target = installed_dir / rel
        if not target.exists():
            mismatches.append(f"missing in install: {rel}")
        elif not filecmp.cmp(dist_file, target, shallow=False):
            mismatches.append(f"content differs: {rel}")
    return mismatches


@pytest.mark.parametrize("harness", list(HARNESS_LAYOUT))
def test_installed_matches_dist(installed, harness):
    dist_sub, install_sub, _marker = HARNESS_LAYOUT[harness]
    dist_dir = REPO_ROOT / "dist" / dist_sub
    installed_dir = installed / install_sub

    assert dist_dir.is_dir(), f"dist/{dist_sub}/ does not exist after install"
    assert installed_dir.is_dir(), f"{install_sub}/ not created by install"

    mismatches = _diff_trees(dist_dir, installed_dir)
    assert not mismatches, (
        f"{harness}: installed tree diverges from dist/{dist_sub}/:\n  "
        + "\n  ".join(mismatches[:30])
    )


@pytest.mark.parametrize("harness", list(HARNESS_LAYOUT))
def test_managed_marker_written(installed, harness):
    _dist_sub, install_sub, marker = HARNESS_LAYOUT[harness]
    install_dir = installed / install_sub

    # The marker lives in the agents dir for the per-agent harnesses. Search
    # for it anywhere under the install root.
    markers = list(install_dir.rglob(marker))
    assert markers, (
        f"{harness}: managed-files marker '{marker}' not written anywhere under "
        f"{install_sub}/"
    )


@pytest.mark.parametrize(
    "harness",
    ["claude", "copilot", "opencode"],
)
def test_all_8_agents_installed(installed, harness):
    _dist_sub, install_sub, _marker = HARNESS_LAYOUT[harness]
    agents_dir = installed / install_sub / "agents"
    assert agents_dir.is_dir(), f"{harness}: agents/ not installed"
    agent_md = [p for p in agents_dir.glob("*.md")]
    assert len(agent_md) == 8, (
        f"{harness}: expected 8 installed agents, found {len(agent_md)}: "
        f"{sorted(p.name for p in agent_md)}"
    )


@pytest.mark.parametrize(
    "harness",
    ["claude", "copilot", "opencode"],
)
def test_all_8_skills_installed(installed, harness):
    _dist_sub, install_sub, _marker = HARNESS_LAYOUT[harness]
    skills_dir = installed / install_sub / "skills"
    assert skills_dir.is_dir(), f"{harness}: skills/ not installed"
    installed_skills = [
        p for p in skills_dir.iterdir() if p.is_dir() and (p / "SKILL.md").exists()
    ]
    assert len(installed_skills) == 8, (
        f"{harness}: expected 8 installed skills, found "
        f"{len(installed_skills)}"
    )


def test_foreign_files_preserved_on_reinstall(tmp_path):
    """Re-installing must not delete user-authored (foreign) files."""
    destdir = tmp_path / "reinstall"
    destdir.mkdir()

    def _install():
        r = subprocess.run(
            ["make", "install-claude", f"DESTDIR={destdir}", "BACKUP=never"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, (
            f"install-claude failed:\nSTDOUT:\n{r.stdout[-2000:]}\n"
            f"STDERR:\n{r.stderr[-2000:]}"
        )

    _install()

    # Drop a foreign agent + a local override file the framework must never own.
    foreign_agent = destdir / ".claude" / "agents" / "user-custom-agent.md"
    foreign_agent.write_text("# my own agent\n", encoding="utf-8")
    local_override = destdir / ".claude" / "AGENTS.md.local"
    local_override.write_text("user override rules\n", encoding="utf-8")

    _install()

    assert foreign_agent.exists(), (
        "re-install removed a user-authored agent (foreign-file protection broken)"
    )
    assert foreign_agent.read_text(encoding="utf-8") == "# my own agent\n", (
        "re-install overwrote a user-authored agent"
    )
    assert local_override.exists(), "re-install removed AGENTS.md.local override"


def test_install_honors_destdir_does_not_touch_home(installed):
    """
    Belt-and-braces: the install fixture used a tmp DESTDIR, so the test simply
    asserts the tmp tree was populated and the DESTDIR is not $HOME.
    """
    assert str(installed) != os.path.expanduser("~"), "DESTDIR must not be HOME"
    assert (installed / ".claude").exists()
    assert (installed / ".copilot").exists()
    assert (installed / ".config" / "opencode").exists()
