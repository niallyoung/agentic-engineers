#!/usr/bin/env python3
"""Test Makefile model registry targets (models-sync, models-check).

Tests the integration of model registry management into the Makefile,
ensuring that generated targets stay current and drift is detected.
"""

import subprocess
import tempfile
import shutil
from pathlib import Path

import pytest


class TestMakefileModelsTargets:
    """Test models-sync and models-check Makefile targets."""

    def test_models_sync_in_help(self):
        """models-sync target appears in make help."""
        result = subprocess.run(
            ["make", "help"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"make help failed: {result.stderr}"
        assert "models-sync" in result.stdout, "models-sync not in make help"
        assert "Regenerate derived model registry targets" in result.stdout

    def test_models_check_in_help(self):
        """models-check target appears in make help."""
        result = subprocess.run(
            ["make", "help"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"make help failed: {result.stderr}"
        assert "models-check" in result.stdout, "models-check not in make help"
        assert "Validate model registry" in result.stdout

    def test_models_check_passes_on_clean_tree(self):
        """make models-check passes on a synced tree (no drift)."""
        result = subprocess.run(
            ["make", "models-check"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"make models-check failed: {result.stderr}\nstdout: {result.stdout}"
        assert "Model registry check passed" in result.stdout

    def test_models_check_fails_on_drift(self):
        """make models-check fails when a role pin is changed without sync (temp copy)."""
        repo_root = Path(__file__).parent.parent

        # Create a temp copy of the repo
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir) / "test-repo"
            # Copy the entire repo
            shutil.copytree(repo_root, tmpdir_path, dirs_exist_ok=True)

            # Edit a role pin in config/models.yaml (change engineer pin)
            models_yaml = tmpdir_path / "config" / "models.yaml"
            content = models_yaml.read_text(encoding="utf-8")
            # Change engineer pin from claude-haiku-4.5 to claude-sonnet-5
            modified = content.replace(
                'model: claude-haiku-4.5',
                'model: claude-sonnet-5',
                1  # Only replace the first occurrence (engineer role)
            )
            models_yaml.write_text(modified, encoding="utf-8")

            # Don't run sync - this should cause drift
            # Now run models-check on the modified repo
            result = subprocess.run(
                ["make", "models-check"],
                cwd=tmpdir_path,
                capture_output=True,
                text=True,
            )

            # models-check should fail because generated targets are stale
            assert result.returncode != 0, (
                f"make models-check should have failed on drift, but passed.\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
            assert "error" in result.stderr.lower() or "stale" in result.stderr.lower(), (
                f"Expected error or stale in stderr, got:\nstderr: {result.stderr}\nstdout: {result.stdout}"
            )

    def test_models_sync_produces_zero_diff_when_idempotent(self):
        """Running models-sync twice produces zero diff (idempotent)."""
        repo_root = Path(__file__).parent.parent

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir) / "test-repo"
            shutil.copytree(repo_root, tmpdir_path, dirs_exist_ok=True)

            # Run sync once
            result1 = subprocess.run(
                ["make", "models-sync"],
                cwd=tmpdir_path,
                capture_output=True,
                text=True,
            )
            assert result1.returncode == 0, f"First sync failed: {result1.stderr}"

            # Run sync again
            result2 = subprocess.run(
                ["make", "models-sync"],
                cwd=tmpdir_path,
                capture_output=True,
                text=True,
            )
            assert result2.returncode == 0, f"Second sync failed: {result2.stderr}"
            # Second sync should show zero files updated (idempotent)
            assert "0 file(s) updated" in result2.stdout, (
                f"Second sync should be idempotent (0 files), got: {result2.stdout}"
            )


class TestLockedModelsShBanner:
    """Test that LOCKED_MODELS.sh has the correct GENERATED banner."""

    def test_locked_models_sh_has_generated_banner(self):
        """LOCKED_MODELS.sh contains the GENERATED banner."""
        repo_root = Path(__file__).parent.parent
        locked_sh = repo_root / ".githooks" / "LOCKED_MODELS.sh"

        content = locked_sh.read_text(encoding="utf-8")
        assert "GENERATED from config/models.yaml" in content, (
            "LOCKED_MODELS.sh should contain GENERATED banner"
        )
        assert "do not edit" in content, "LOCKED_MODELS.sh should warn not to edit"

    def test_locked_models_arrays_source_correctly(self):
        """LOCKED_MODELS and AGENT_MODEL_ASSIGNMENTS arrays can be sourced."""
        repo_root = Path(__file__).parent.parent
        locked_sh = repo_root / ".githooks" / "LOCKED_MODELS.sh"

        # Test sourcing the script and checking arrays are populated
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source {locked_sh} && "
                "declare -p LOCKED_MODELS | grep -q 'declare -ax' && "
                "declare -p AGENT_MODEL_ASSIGNMENTS | grep -q 'declare -ax'",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Failed to source LOCKED_MODELS.sh or arrays not exported: "
            f"stderr={result.stderr}"
        )
