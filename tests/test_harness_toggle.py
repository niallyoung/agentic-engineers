"""
Tests for `make harness-toggle` — the active-harness symlink toggle.

The target force-creates (ln -sfn) a symlink pointing at the chosen
harness's dist/<harness>/ directory. The link location defaults to
~/.agentic-engineers/active-harness but is overridable via ACTIVE_LINK
so these tests never touch the real home directory.

Covered:
  - creating the link for a valid harness
  - re-toggling force-replaces an existing link
  - missing HARNESS errors clearly (non-zero exit)
  - invalid HARNESS errors clearly (non-zero exit)
  - the resulting link path is printed
"""

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Harnesses the toggle must accept (mirrors the 4 install targets).
SUPPORTED_HARNESSES = ("claude", "copilot", "opencode", "pi")


def _make_toggle(active_link, harness=None, extra_args=()):
    """Run `make harness-toggle` with an overridden ACTIVE_LINK."""
    cmd = ["make", "harness-toggle", f"ACTIVE_LINK={active_link}"]
    if harness is not None:
        cmd.append(f"HARNESS={harness}")
    cmd.extend(extra_args)
    return subprocess.run(
        cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=60
    )


@pytest.fixture(scope="module", autouse=True)
def rendered_dists():
    """Ensure dist/claude and dist/opencode exist (render if missing)."""
    for harness in ("claude", "opencode"):
        if not (REPO_ROOT / "dist" / harness).is_dir():
            result = subprocess.run(
                ["make", f"render-{harness}"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
            assert result.returncode == 0, (
                f"make render-{harness} failed:\n{result.stdout}\n{result.stderr}"
            )


class TestHarnessToggleCreatesLink:
    def test_creates_symlink_to_harness_dist(self, tmp_path):
        link = tmp_path / "active-harness"
        result = _make_toggle(link, harness="claude")
        assert result.returncode == 0, (
            f"harness-toggle failed:\n{result.stdout}\n{result.stderr}"
        )
        assert link.is_symlink(), f"{link} is not a symlink"
        assert os.path.realpath(link) == os.path.realpath(
            REPO_ROOT / "dist" / "claude"
        )

    def test_creates_parent_directory_if_missing(self, tmp_path):
        link = tmp_path / "nested" / "dir" / "active-harness"
        result = _make_toggle(link, harness="opencode")
        assert result.returncode == 0, (
            f"harness-toggle failed:\n{result.stdout}\n{result.stderr}"
        )
        assert link.is_symlink()

    def test_prints_resulting_link(self, tmp_path):
        link = tmp_path / "active-harness"
        result = _make_toggle(link, harness="claude")
        assert result.returncode == 0
        assert str(link) in result.stdout, (
            f"expected link path in output:\n{result.stdout}"
        )
        assert "claude" in result.stdout


class TestHarnessToggleForceReplaces:
    def test_retoggle_replaces_existing_link(self, tmp_path):
        link = tmp_path / "active-harness"

        first = _make_toggle(link, harness="claude")
        assert first.returncode == 0, f"{first.stdout}\n{first.stderr}"
        assert os.path.realpath(link) == os.path.realpath(
            REPO_ROOT / "dist" / "claude"
        )

        second = _make_toggle(link, harness="opencode")
        assert second.returncode == 0, f"{second.stdout}\n{second.stderr}"
        assert link.is_symlink()
        assert os.path.realpath(link) == os.path.realpath(
            REPO_ROOT / "dist" / "opencode"
        ), "re-toggle must force-replace the existing symlink"


class TestHarnessToggleValidation:
    def test_missing_harness_fails(self, tmp_path):
        link = tmp_path / "active-harness"
        result = _make_toggle(link, harness=None)
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "HARNESS" in combined, (
            f"expected a clear HARNESS error:\n{combined}"
        )
        assert not link.exists() and not link.is_symlink()

    def test_invalid_harness_fails(self, tmp_path):
        link = tmp_path / "active-harness"
        result = _make_toggle(link, harness="not-a-harness")
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "not-a-harness" in combined, (
            f"expected the invalid name in the error:\n{combined}"
        )
        assert not link.exists() and not link.is_symlink()

    def test_error_lists_supported_harnesses(self, tmp_path):
        link = tmp_path / "active-harness"
        result = _make_toggle(link, harness="bogus")
        combined = result.stdout + result.stderr
        for harness in SUPPORTED_HARNESSES:
            assert harness in combined, (
                f"supported harness '{harness}' missing from error:\n{combined}"
            )
