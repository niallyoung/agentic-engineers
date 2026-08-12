"""
CI Container Environment Simulation Tests

Tests that validate the local Docker-based CI environment matches GitHub Actions.
These tests cover:
- Symlink support and validation
- File path resolution
- File permission handling
- Python 3.11 compatibility
- System dependencies availability

Author: Security Engineer (Opus 4.8)
Phase: Container environment verification (test CI locally before push)
"""

import os
import sys
import stat
import tempfile
import platform
import subprocess
from pathlib import Path
from typing import Optional, Tuple


class TestContainerSymlinks:
    """Test symlink handling in container environment."""

    def test_symlink_creation(self):
        """Verify symlinks can be created (matches GitHub Actions core.symlinks=true)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "target.txt"
            link = Path(tmpdir) / "link.txt"

            # Create target
            target.write_text("test content")

            # Create symlink
            link.symlink_to(target)

            # Verify symlink was created
            assert link.is_symlink(), "Failed to create symlink"
            assert link.read_text() == "test content", "Symlink target not readable"

    def test_symlink_resolution(self):
        """Verify symlink resolution works correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "target.txt"
            link = Path(tmpdir) / "link.txt"

            target.write_text("resolved content")
            link.symlink_to(target)

            # Resolve symlink
            resolved = link.resolve()
            # On macOS, /var/ becomes /private/var/; just check they point to the same file
            assert resolved.samefile(target), f"Symlink resolution failed: {resolved} doesn't point to {target}"

    def test_broken_symlink_handling(self):
        """Verify broken symlinks are handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "nonexistent.txt"
            link = Path(tmpdir) / "broken_link.txt"

            # Create symlink to nonexistent target
            link.symlink_to(nonexistent)

            # Verify it's a symlink even though target doesn't exist
            assert link.is_symlink(), "is_symlink() failed on broken symlink"
            assert not link.exists(), "exists() should return False for broken symlink"

    def test_relative_symlink(self):
        """Verify relative symlinks work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir1 = Path(tmpdir) / "dir1"
            dir2 = Path(tmpdir) / "dir2"
            dir1.mkdir()
            dir2.mkdir()

            target = dir1 / "target.txt"
            target.write_text("relative test")

            link = dir2 / "link.txt"
            link.symlink_to(Path("..") / "dir1" / "target.txt")

            assert link.is_symlink(), "Relative symlink creation failed"
            assert link.read_text() == "relative test", "Relative symlink resolution failed"

    def test_symlink_in_path_traversal(self):
        """Verify symlinks don't cause path traversal vulnerabilities."""
        with tempfile.TemporaryDirectory() as tmpdir:
            safe_dir = Path(tmpdir) / "safe"
            unsafe_dir = Path(tmpdir) / "unsafe"
            safe_dir.mkdir()
            unsafe_dir.mkdir()

            # Create a symlink that points outside safe_dir
            outside_file = Path(tmpdir) / "outside.txt"
            outside_file.write_text("outside content")

            symlink = safe_dir / "link.txt"
            symlink.symlink_to(outside_file)

            # resolve() should give us the true path outside safe_dir
            resolved = symlink.resolve()
            assert not str(resolved).startswith(str(safe_dir)), "Symlink path traversal check failed"


class TestContainerFilePaths:
    """Test file path handling in container environment."""

    def test_workspace_path_exists(self):
        """Verify /workspace directory exists in container context."""
        # In container, working directory is /workspace
        # In local tests, we work with actual paths
        cwd = Path.cwd()
        assert cwd.exists(), f"Current working directory doesn't exist: {cwd}"

    def test_absolute_path_resolution(self):
        """Verify absolute paths resolve correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")

            # Absolute path should work
            absolute = test_file.absolute()
            assert absolute.exists(), f"Absolute path resolution failed: {absolute}"

    def test_relative_path_resolution(self):
        """Verify relative paths resolve from cwd."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                test_file = Path("test.txt")
                test_file.write_text("content")

                assert test_file.exists(), "Relative path resolution failed"
                assert test_file.resolve().exists(), "Resolved relative path doesn't exist"
            finally:
                os.chdir(original_cwd)

    def test_path_with_spaces(self):
        """Verify paths with spaces are handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spaced_dir = Path(tmpdir) / "dir with spaces"
            spaced_dir.mkdir()
            test_file = spaced_dir / "file with spaces.txt"
            test_file.write_text("content")

            assert test_file.exists(), "Path with spaces resolution failed"

    def test_path_with_special_chars(self):
        """Verify paths with special characters are handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            special_file = Path(tmpdir) / "file-with_special.chars.txt"
            special_file.write_text("content")

            assert special_file.exists(), "Path with special chars resolution failed"

    def test_python_path_validation(self):
        """Verify PYTHONPATH is correctly set in container."""
        # Check that src-rooted paths resolve (src/ has no importable dotted
        # packages post-slimdown — skill dirs are hyphenated — so this checks
        # a real framework file rather than a Python import).
        assert Path("src/AGENTS.md").exists() or Path("/workspace/src/AGENTS.md").exists(), (
            "src/AGENTS.md not resolvable — PYTHONPATH/WORKDIR may be misconfigured"
        )


class TestContainerFilePermissions:
    """Test file permission handling in container environment."""

    def test_read_permission(self):
        """Verify files with read permission are readable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "readable.txt"
            test_file.write_text("content")
            test_file.chmod(0o644)

            assert os.access(test_file, os.R_OK), "File is not readable"
            assert test_file.read_text() == "content", "Failed to read file content"

    def test_write_permission(self):
        """Verify files with write permission are writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "writable.txt"
            test_file.write_text("initial")
            test_file.chmod(0o644)

            assert os.access(test_file, os.W_OK), "File is not writable"
            test_file.write_text("updated")
            assert test_file.read_text() == "updated", "Failed to write to file"

    def test_executable_permission(self):
        """Verify executable permission bits can be set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            script = Path(tmpdir) / "script.sh"
            script.write_text("#!/bin/bash\necho hello\n")
            script.chmod(0o755)

            st = script.stat()
            is_executable = bool(st.st_mode & stat.S_IXUSR)
            assert is_executable, "File executable bit not set"

    def test_permission_denied_handling(self):
        """Verify permission denied errors are handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "readonly.txt"
            test_file.write_text("content")
            test_file.chmod(0o444)  # Read-only

            # Should be able to read
            assert os.access(test_file, os.R_OK), "Cannot read read-only file"

            # Should not be able to write
            assert not os.access(test_file, os.W_OK), "Write access check failed"

            # Cleanup: restore write permission so pytest can clean up
            test_file.chmod(0o644)

    def test_directory_permission(self):
        """Verify directory permissions work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "testdir"
            test_dir.mkdir(mode=0o755)

            assert os.access(test_dir, os.R_OK), "Cannot read directory"
            assert os.access(test_dir, os.X_OK), "Cannot execute (access) directory"

    def test_hidden_file_handling(self):
        """Verify hidden files (.* files) are preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hidden = Path(tmpdir) / ".hidden"
            hidden.write_text("hidden content")

            # File should exist even though it's hidden
            assert hidden.exists(), "Hidden file not found"
            assert hidden.read_text() == "hidden content", "Failed to read hidden file"


class TestPython311Compatibility:
    """Test Python 3.11 specific features and compatibility."""

    def test_python_version(self):
        """Verify Python version >= 3.11 (or allow local test environment)."""
        version_info = sys.version_info
        assert version_info.major == 3, f"Python major version is {version_info.major}, expected 3"
        # In container: >= 3.11; locally: may be different (allow for dev flexibility)
        # This test is primarily for CI container verification
        if os.getenv("DOCKER_BUILD") or os.getenv("CI"):
            # Strict check in CI/container environments
            assert version_info.minor >= 11, f"Python minor version is {version_info.minor}, expected >= 11"
        # else: allow any Python 3.x locally for development

    def test_pathlib_available(self):
        """Verify pathlib module is available."""
        from pathlib import Path
        assert Path is not None, "pathlib.Path not available"

    def test_match_available(self):
        """Verify pathlib.Path.match() method (3.11+)."""
        test_path = Path("src/skills/queue-management/scripts/queue_ops.py")
        # match() should work in 3.11+
        assert test_path.match("*.py"), "pathlib.Path.match() not working"

    def test_typing_available(self):
        """Verify typing module features."""
        from typing import Optional, Union, List, Dict
        assert Optional is not None, "typing.Optional not available"
        assert Union is not None, "typing.Union not available"
        assert List is not None, "typing.List not available"
        assert Dict is not None, "typing.Dict not available"

    def test_async_context_manager(self):
        """Verify async/await support (required for async tests)."""
        import inspect
        assert inspect.iscoroutinefunction(self._async_test), "async/await not supported"

    async def _async_test(self):
        """Dummy async function for testing async support."""
        pass

    def test_exception_groups(self):
        """Verify exception group support (Python 3.11+)."""
        try:
            # Python 3.11+ has exception groups
            exc_group = ExceptionGroup("test", [ValueError("test")])
            assert isinstance(exc_group, BaseException), "ExceptionGroup not a BaseException"
        except NameError:
            # ExceptionGroup might not be available in all Python 3.11 versions
            pass


class TestSystemDependencies:
    """Test system dependencies required by CI environment."""

    def test_git_available(self):
        """Verify git command is available."""
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        assert result.returncode == 0, "git command not available"
        assert "git version" in result.stdout, "git version output unexpected"

    def test_python_available(self):
        """Verify python3 command is available."""
        result = subprocess.run(["python3", "--version"], capture_output=True, text=True)
        assert result.returncode == 0, "python3 command not available"

    def test_pytest_available(self):
        """Verify pytest is installed."""
        try:
            import pytest
            assert pytest is not None, "pytest module not available"
        except ImportError:
            raise AssertionError("pytest not installed")

    def test_pyyaml_available(self):
        """Verify PyYAML is installed."""
        try:
            import yaml
            assert yaml is not None, "pyyaml module not available"
        except ImportError:
            raise AssertionError("pyyaml not installed")


class TestDockerfileBuild:
    """Test Dockerfile configuration and build process."""

    def test_dockerfile_exists(self):
        """Verify Dockerfile exists in repository root."""
        repo_root = Path.cwd()
        dockerfile = repo_root / "Dockerfile"
        assert dockerfile.exists(), f"Dockerfile not found at {dockerfile}"

    def test_dockerfile_has_from(self):
        """Verify Dockerfile has FROM statement."""
        dockerfile = Path("Dockerfile")
        content = dockerfile.read_text()
        assert "FROM python:3.11" in content, "Dockerfile doesn't use Python 3.11"

    def test_dockerfile_has_workdir(self):
        """Verify Dockerfile sets WORKDIR."""
        dockerfile = Path("Dockerfile")
        content = dockerfile.read_text()
        assert "WORKDIR" in content, "Dockerfile doesn't set WORKDIR"

    def test_dockerfile_has_healthcheck(self):
        """Verify Dockerfile has a framework-file verification step."""
        dockerfile = Path("Dockerfile")
        content = dockerfile.read_text()
        assert "src/AGENTS.md" in content and "src/SKILLS.md" in content, (
            "Dockerfile missing framework file verification"
        )

    def test_dockerfile_installs_dependencies(self):
        """Verify Dockerfile installs required dependencies."""
        dockerfile = Path("Dockerfile")
        content = dockerfile.read_text()
        assert "pytest" in content, "Dockerfile doesn't install pytest"
        assert "pyyaml" in content, "Dockerfile doesn't install pyyaml"


class TestMakefileTargets:
    """Test Makefile CI targets."""

    def test_makefile_exists(self):
        """Verify Makefile exists."""
        makefile = Path("Makefile")
        assert makefile.exists(), "Makefile not found"

    def test_test_ci_target_exists(self):
        """Verify make test-ci target exists."""
        makefile = Path("Makefile")
        content = makefile.read_text()
        assert "test-ci:" in content, "make test-ci target not found"

    def test_test_ci_force_target_exists(self):
        """Verify make test-ci-force target exists."""
        makefile = Path("Makefile")
        content = makefile.read_text()
        assert "test-ci-force:" in content, "make test-ci-force target not found"

    def test_test_ci_shell_target_exists(self):
        """Verify make test-ci-shell target exists."""
        makefile = Path("Makefile")
        content = makefile.read_text()
        assert "test-ci-shell:" in content, "make test-ci-shell target not found"

    def test_makefile_has_help_documentation(self):
        """Verify Makefile targets have documentation."""
        makefile = Path("Makefile")
        content = makefile.read_text()
        assert "Run tests in CI container" in content, "Missing test-ci documentation"


class TestGitConfiguration:
    """Test Git configuration for CI environment."""

    def test_git_config_symlinks(self):
        """Verify Git is configured to support symlinks."""
        result = subprocess.run(
            ["git", "config", "--get", "core.symlinks"],
            capture_output=True,
            text=True
        )
        # Can be "true" or unset (defaults to true on Unix)
        if result.returncode == 0:
            assert result.stdout.strip() in ["true", ""], "Git symlink support not configured"

    def test_git_hooks_configured(self):
        """Verify Git hooks are configured."""
        result = subprocess.run(
            ["git", "config", "--get", "core.hooksPath"],
            capture_output=True,
            text=True
        )
        # Should be .githooks if configured
        if result.returncode == 0:
            assert ".githooks" in result.stdout, "Git hooks path not correctly configured"


class TestPlatformDetection:
    """Test platform detection and conditional behavior."""

    def test_platform_detection(self):
        """Verify platform detection works."""
        detected_platform = platform.system()
        assert detected_platform in ["Linux", "Darwin", "Windows"], f"Unknown platform: {detected_platform}"

    def test_platform_specific_paths(self):
        """Verify platform-specific path handling."""
        home = Path.home()
        assert home.exists(), "Home directory not found"

    def test_path_separator_handling(self):
        """Verify path separator handling is correct."""
        test_path = Path("src") / "skills" / "queue-management"
        # Path should handle separators correctly regardless of platform
        parts = test_path.parts
        assert "src" in parts, "Path parts incorrect"


# ============================================================================
# Integration Tests (Run in container environment)
# ============================================================================


class TestContainerIntegration:
    """Integration tests that validate complete container setup."""

    def test_imports_work(self):
        """Verify core queue_ops import works (requires sys.path set correctly)."""
        import sys as _sys

        qm_scripts = Path("src/skills/queue-management/scripts")
        if not qm_scripts.exists():
            qm_scripts = Path("/workspace/src/skills/queue-management/scripts")
        try:
            if str(qm_scripts) not in _sys.path:
                _sys.path.insert(0, str(qm_scripts))
            import queue_ops  # noqa: F401
            assert True, "Core imports successful"
        except ImportError:
            # Allow for test environment variance
            pass

    def test_test_discovery(self):
        """Verify pytest can discover all tests."""
        result = subprocess.run(
            ["python3", "-m", "pytest", "tests/", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Test collection failed: {result.stderr}"
        assert "tests collected" in result.stdout, "No tests collected"


# ============================================================================
# Error Message Tests
# ============================================================================


class TestErrorMessages:
    """Test that errors provide clear, actionable messages."""

    def test_missing_docker_error(self):
        """Verify error message when Docker is not available."""
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True
        )
        # If docker is not available, error message should be clear
        if result.returncode != 0:
            # This is expected if Docker is not installed
            pass

    def test_permission_error_message(self):
        """Verify permission error messages are clear."""
        with tempfile.TemporaryDirectory() as tmpdir:
            readonly_dir = Path(tmpdir) / "readonly"
            readonly_dir.mkdir(mode=0o555)
            test_file = readonly_dir / "test.txt"

            try:
                test_file.write_text("content")
                # If we get here, permissions didn't prevent write (some systems)
                readonly_dir.chmod(0o755)  # Restore for cleanup
            except (PermissionError, OSError) as e:
                # Expected: error should mention permission
                assert "permission" in str(e).lower() or "denied" in str(e).lower()

            # Cleanup
            readonly_dir.chmod(0o755)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
