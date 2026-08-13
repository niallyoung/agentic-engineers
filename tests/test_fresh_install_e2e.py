"""
End-to-end test for fresh install of the agentic-engineers framework.

Tests verify that:
1. Fresh install creates correct directory structure (agents/, skills/)
2. DESTDIR override installs in isolation from HOME
3. No orphaned/duplicate files from previous installs

NOTE (queue-removal, task-2026-08-13-queue-removal-code): this file used to
also cover queue initialization and a simulated DELEGATE -> processing ->
HANDBACK -> done walk through a hand-created ~/.copilot/queue/{session-id}/
directory tree, plus a separate TestQueueArtifactLocations class asserting
artifact file locations under that tree. None of it exercised real product
code — it manually created directories and asserted they existed. With
dispatch now a direct sub-agent spawn (no filesystem queue at all), those
tests validated a mechanism the framework no longer has, so they were
removed rather than retargeted. DELEGATE/HANDBACK schema round-tripping is
covered by tests/test_e2e_protocol_full_cycle.py.

Tests that require `make install-copilot` will be skipped in environments
where make is not available or the repo is not a git repository (CI/temp
copies).
"""
import os
import tempfile
import shutil
import uuid
from pathlib import Path
import subprocess
import pytest


def is_git_repo():
    """Check if current directory is in a git repository."""
    try:
        subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            check=True,
            timeout=5
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def has_make():
    """Check if make is available."""
    try:
        subprocess.run(['which', 'make'], capture_output=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


class TestFreshInstallE2E:
    """Test fresh install to a temporary home directory."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown test environment."""
        # Create temp directories for this test
        self.temp_repo = tempfile.mkdtemp(prefix="test-agentic-repo-")
        self.temp_home = tempfile.mkdtemp(prefix="test-agentic-home-")

        yield

        # Cleanup
        if os.path.exists(self.temp_repo):
            shutil.rmtree(self.temp_repo, ignore_errors=True)
        if os.path.exists(self.temp_home):
            shutil.rmtree(self.temp_home, ignore_errors=True)

    def _copy_repo_to_temp(self):
        """Copy repo to temp location for fresh install test."""
        repo_root = Path(__file__).parent.parent.absolute()

        # Copy entire repo
        for item in os.listdir(repo_root):
            src = os.path.join(repo_root, item)
            dst = os.path.join(self.temp_repo, item)

            # Skip certain directories
            if item in ['.git', '__pycache__', '.pytest_cache', 'htmlcov', '.DS_Store', 'dist']:
                continue

            # Skip symlinks (hyphenated skill packages may be symlinked)
            if os.path.islink(src):
                continue

            if os.path.isdir(src):
                try:
                    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'), symlinks=False)
                except (shutil.Error, FileNotFoundError):
                    # Skip if directory doesn't copy cleanly (e.g., broken symlinks)
                    pass
            else:
                try:
                    shutil.copy2(src, dst)
                except (IOError, OSError):
                    # Skip if file can't be copied
                    pass

    def _get_session_id(self):
        """Generate a test session ID."""
        return str(uuid.uuid4())

    @pytest.mark.skipif(not (has_make() and is_git_repo()), reason="make or git not available")
    def test_fresh_install_to_temp_home(self):
        """
        Verify that fresh install creates correct directory structure.

        SKIP CONDITION: This test is skipped in CI or environments where:
        - make is not available
        - Running outside a git repository (CI temp copies)

        Expected structure after install:
        ~/.copilot/
        ├── agents/
        │   └── *.agent.md (8 agents)
        └── skills/
            └── */
        """
        self._copy_repo_to_temp()

        # Initialize git in temp repo (for make install-copilot)
        subprocess.run(['git', 'init'], cwd=self.temp_repo, capture_output=True)

        # Simulate fresh install to temp home
        install_env = os.environ.copy()
        install_env['HOME'] = self.temp_home

        # Run make install-copilot with custom HOME
        result = subprocess.run(
            ['make', 'install-copilot'],
            cwd=self.temp_repo,
            env=install_env,
            capture_output=True,
            text=True,
            timeout=120
        )
        assert result.returncode == 0, f"Install failed:\n{result.stderr}"

        # Verify expected structure exists
        copilot_home = os.path.join(self.temp_home, '.copilot')
        assert os.path.exists(copilot_home), f"~/.copilot/ not created at {copilot_home}"

        # Check agents directory
        agents_dir = os.path.join(copilot_home, 'agents')
        assert os.path.isdir(agents_dir), f"agents/ directory not found at {agents_dir}"

        agent_files = [f for f in os.listdir(agents_dir) if f.endswith('.agent.md')]
        assert len(agent_files) >= 8, f"Expected at least 8 agents, found {len(agent_files)}: {agent_files}"

        # Check skills directory
        skills_dir = os.path.join(copilot_home, 'skills')
        assert os.path.isdir(skills_dir), f"skills/ directory not found at {skills_dir}"

        skills_count = len([d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))])
        assert skills_count > 0, "No skills found in skills/ directory"

    @pytest.mark.skipif(not (has_make() and is_git_repo()), reason="make or git not available")
    def test_install_with_destdir_override(self):
        """`make install-copilot DESTDIR=<dir>` installs under DESTDIR and, when
        DESTDIR != HOME, skips git-hook installation (sandbox-safe)."""
        self._copy_repo_to_temp()
        subprocess.run(['git', 'init'], cwd=self.temp_repo, capture_output=True)

        destdir = tempfile.mkdtemp(prefix="test-agentic-destdir-")
        try:
            install_env = os.environ.copy()
            # HOME deliberately differs from DESTDIR so the git-hook guard skips.
            install_env['HOME'] = self.temp_home

            result = subprocess.run(
                ['make', 'install-copilot', f'DESTDIR={destdir}'],
                cwd=self.temp_repo,
                env=install_env,
                capture_output=True,
                text=True,
                timeout=120,
            )
            assert result.returncode == 0, f"Install failed:\n{result.stderr}"

            # Files land under DESTDIR/.copilot, NOT under HOME/.copilot.
            destdir_copilot = os.path.join(destdir, '.copilot')
            assert os.path.isdir(os.path.join(destdir_copilot, 'agents')), \
                f"agents/ not installed under DESTDIR at {destdir_copilot}"
            assert os.path.isdir(os.path.join(destdir_copilot, 'skills')), \
                f"skills/ not installed under DESTDIR at {destdir_copilot}"
            assert not os.path.exists(os.path.join(self.temp_home, '.copilot')), \
                "Install leaked into HOME/.copilot despite DESTDIR override"
        finally:
            shutil.rmtree(destdir, ignore_errors=True)

    @pytest.mark.skipif(not (has_make() and is_git_repo()), reason="make or git not available")
    def test_no_stale_files_after_install(self):
        """
        Verify that no orphaned or duplicate files from previous installs remain.

        SKIP CONDITION: Skipped in CI.
        """
        self._copy_repo_to_temp()

        # Initialize git
        subprocess.run(['git', 'init'], cwd=self.temp_repo, capture_output=True)

        install_env = os.environ.copy()
        install_env['HOME'] = self.temp_home

        result = subprocess.run(
            ['make', 'install-copilot'],
            cwd=self.temp_repo,
            env=install_env,
            capture_output=True,
            text=True,
            timeout=120
        )
        assert result.returncode == 0, f"Install failed:\n{result.stderr}"

        copilot_home = os.path.join(self.temp_home, '.copilot')

        # Verify agents directory doesn't have duplicates
        agents_dir = os.path.join(copilot_home, 'agents')
        if os.path.exists(agents_dir):
            agent_files = os.listdir(agents_dir)
            unique_agents = set(agent_files)
            assert len(agent_files) == len(unique_agents), \
                "Duplicate agents found after install"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
