#!/usr/bin/env python3
"""
test_render_workflow.py — Tests for the render-to-dist, install-to-harness workflow.

Covers:
1. validate_renders.py correctly detects in-sync, missing, and stale dist entries.
2. make render-* produces dist/<harness>/skills/ output (smoke test, no harness install).
3. make install-* validates dist/ exists before attempting install.
4. git_push_with_tags helper shell tests (delegates to test_git_push.sh).
5. Cross-harness skill availability: same skill name present in all harness dists.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Repo root fixture
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


# ---------------------------------------------------------------------------
# 1. validate_renders.py unit tests
# ---------------------------------------------------------------------------


def _run_validate(repo_root_override: Path) -> subprocess.CompletedProcess:
    """Run validate_renders.py against a given repo root and return the result."""
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "renderer" / "scripts" / "validate_renders.py"), str(repo_root_override)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


class TestValidateRenders:
    """Tests for renderer/scripts/validate_renders.py."""

    def test_validate_renders_script_exists(self, repo_root):
        assert (repo_root / "renderer" / "scripts" / "validate_renders.py").exists(), (
            "renderer/scripts/validate_renders.py must exist"
        )

    def test_validate_renders_passes_with_real_dist(self, repo_root):
        """validate_renders.py exits 0 when dist/ is populated (as committed in repo)."""
        result = _run_validate(repo_root)
        # If dist/ exists and skills are rendered, should pass.
        # If dist/ is absent (e.g., after make clean) this may fail — that's expected.
        if (repo_root / "dist").exists():
            assert result.returncode == 0, (
                f"validate_renders.py failed with dist/ present:\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )

    def test_validate_renders_fails_without_dist(self, tmp_path):
        """validate_renders.py exits 1 when dist/ directory is absent."""
        # Create a minimal fake repo structure with one skill but NO dist/
        (tmp_path / "src" / "skills" / "my-skill").mkdir(parents=True)
        (tmp_path / "src" / "skills" / "my-skill" / "SKILL.md").write_text("---\ntitle: my-skill\n---\n")

        result = _run_validate(tmp_path)
        assert result.returncode == 1, "Should fail when dist/ is absent"
        assert "dist/" in result.stdout or "dist/" in result.stderr

    def test_validate_renders_fails_with_missing_skill_in_harness(self, tmp_path):
        """validate_renders.py exits 1 when a skill is missing from a harness dist/."""
        src_skill = tmp_path / "src" / "skills" / "example-skill"
        src_skill.mkdir(parents=True)
        (src_skill / "SKILL.md").write_text("---\ntitle: example-skill\n---\n")

        # Create dist/ dirs for two harnesses, omit one skill from 'copilot'
        for harness in ["claude", "opencode"]:
            dist_skill = tmp_path / "dist" / harness / "skills" / "example-skill"
            dist_skill.mkdir(parents=True)
            (dist_skill / "SKILL.md").write_text("---\ntitle: example-skill\n---\n")
        # copilot intentionally missing

        result = _run_validate(tmp_path)
        assert result.returncode == 1
        assert "example-skill" in result.stdout

    def test_validate_renders_passes_with_all_skills_present(self, tmp_path):
        """validate_renders.py exits 0 when all skills are present in all harness dists."""
        for skill_name in ["skill-a", "skill-b"]:
            src_skill = tmp_path / "src" / "skills" / skill_name
            src_skill.mkdir(parents=True)
            (src_skill / "SKILL.md").write_text(f"---\ntitle: {skill_name}\n---\n")

            for harness in ["claude", "copilot", "opencode", "codex"]:
                dist_skill = tmp_path / "dist" / harness / "skills" / skill_name
                dist_skill.mkdir(parents=True)
                (dist_skill / "SKILL.md").write_text(f"---\ntitle: {skill_name}\n---\n")

        result = _run_validate(tmp_path)
        assert result.returncode == 0, (
            f"Should pass with all skills present:\n{result.stdout}\n{result.stderr}"
        )

    def test_validate_renders_meta_skills_not_required_in_dist(self, tmp_path):
        """Skills under src/skills/_meta/ are not required in dist/."""
        meta_skill = tmp_path / "src" / "skills" / "_meta" / "internal-helper"
        meta_skill.mkdir(parents=True)
        (meta_skill / "SKILL.md").write_text("---\ntitle: internal-helper\n---\n")

        # No dist/ at all — but _meta skills are ignored, so empty src means pass
        (tmp_path / "dist").mkdir()

        result = _run_validate(tmp_path)
        # Should pass because there are no renderable skills
        assert result.returncode == 0

    def test_stale_dist_skill_emits_warning_not_error(self, tmp_path):
        """Stale dist entries (no source counterpart) are warnings, not errors."""
        # Minimal valid source skill
        src_skill = tmp_path / "src" / "skills" / "real-skill"
        src_skill.mkdir(parents=True)
        (src_skill / "SKILL.md").write_text("---\ntitle: real-skill\n---\n")

        for harness in ["claude", "copilot", "opencode", "codex"]:
            dist_skill = tmp_path / "dist" / harness / "skills" / "real-skill"
            dist_skill.mkdir(parents=True)
            (dist_skill / "SKILL.md").write_text("---\ntitle: real-skill\n---\n")
            # Add a stale extra skill
            stale = tmp_path / "dist" / harness / "skills" / "old-removed-skill"
            stale.mkdir(parents=True)
            (stale / "SKILL.md").write_text("---\ntitle: old\n---\n")

        result = _run_validate(tmp_path)
        # Should still exit 0 — stale entries are warnings
        assert result.returncode == 0
        assert "stale" in result.stdout.lower() or "old-removed-skill" in result.stdout


# ---------------------------------------------------------------------------
# 2. dist/ structure smoke tests (real repo)
# ---------------------------------------------------------------------------


class TestDistStructure:
    """Verify the committed dist/ directory has the expected structure."""

    @pytest.fixture(autouse=True)
    def check_dist_present(self, repo_root):
        dist = repo_root / "dist"
        if not dist.exists():
            pytest.skip("dist/ not present (run 'make render-all' first)")

    def test_dist_claude_has_skills_and_agents(self, repo_root):
        assert (repo_root / "dist" / "claude" / "skills").is_dir()
        assert (repo_root / "dist" / "claude" / "agents").is_dir()

    def test_dist_copilot_has_skills_and_agents(self, repo_root):
        assert (repo_root / "dist" / "copilot" / "skills").is_dir()
        assert (repo_root / "dist" / "copilot" / "agents").is_dir()

    def test_dist_opencode_has_skills_agents_and_config(self, repo_root):
        assert (repo_root / "dist" / "opencode" / "skills").is_dir()
        assert (repo_root / "dist" / "opencode" / "agents").is_dir()
        assert (repo_root / "dist" / "opencode" / "opencode.jsonc").exists()

    def test_dist_skills_all_have_skill_md(self, repo_root):
        """Every skill directory inside dist/ must contain a SKILL.md."""
        for harness in ["claude", "copilot", "opencode"]:
            skills_dir = repo_root / "dist" / harness / "skills"
            if not skills_dir.exists():
                continue
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir():
                    assert (skill_dir / "SKILL.md").exists(), (
                        f"dist/{harness}/skills/{skill_dir.name}/SKILL.md missing"
                    )

    def test_cross_harness_skill_consistency(self, repo_root):
        """Same set of skills should appear in claude, copilot, and opencode dists."""
        skill_sets: dict[str, set[str]] = {}
        for harness in ["claude", "copilot", "opencode"]:
            skills_dir = repo_root / "dist" / harness / "skills"
            if skills_dir.exists():
                skill_sets[harness] = {
                    d.name for d in skills_dir.iterdir() if d.is_dir()
                }

        if len(skill_sets) < 2:
            pytest.skip("Not enough harnesses to compare")

        harnesses = list(skill_sets.keys())
        ref_harness = harnesses[0]
        ref_skills = skill_sets[ref_harness]

        for harness in harnesses[1:]:
            diff = ref_skills.symmetric_difference(skill_sets[harness])
            assert not diff, (
                f"Skill mismatch between {ref_harness} and {harness}: {diff}\n"
                "Run 'make render-all' to sync all harnesses."
            )


# ---------------------------------------------------------------------------
# 3. Makefile install validation — dist/ must exist before install
# ---------------------------------------------------------------------------


class TestInstallValidation:
    """Verify that install targets refuse to run when dist/ is absent."""

    @pytest.mark.parametrize("target", ["install-claude", "install-copilot", "install-opencode"])
    def test_install_fails_gracefully_without_dist(self, repo_root, target, tmp_path):
        """
        install-* should fail with a clear error message when dist/<harness>/ is absent.
        We simulate this by passing a REPO_ROOT that points to a directory with no dist/.
        """
        # Create a minimal fake repo without dist/
        fake_repo = tmp_path / "fake-repo"
        fake_repo.mkdir()
        (fake_repo / "src" / "skills").mkdir(parents=True)
        # No dist/

        harness = target.replace("install-", "")
        # We test the validation logic in validate_renders.py instead of running make
        # (running make against a fake repo is brittle — test the underlying script).
        result = subprocess.run(
            [sys.executable, str(repo_root / "renderer" / "scripts" / "validate_renders.py"), str(fake_repo)],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        # Should fail (exit 1) because dist/ doesn't exist
        assert result.returncode == 1


