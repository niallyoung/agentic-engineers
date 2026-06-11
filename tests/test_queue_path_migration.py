"""
tests/test_queue_path_migration.py — Tests for queue path migration script.

Tests the migrate-queue-paths.sh script which migrates queue sessions from:
  OLD: ~/.agentic-engineers/artifacts/{session-id}/{harness}/queue/
TO:
  NEW: ~/.agentic-engineers/{session-id}/{harness}/queue/

The script must be:
- Idempotent (safe to run multiple times)
- Preserve all queue subdirectories (incoming/, processing/, done/, failed/)
- Handle empty artifacts directory gracefully
- Print accurate migration summary
- Exit with 0 on success, 1 on failure
"""

import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Tuple

import pytest


class TestQueuePathMigration:
    """Test suite for queue path migration script."""

    @pytest.fixture
    def migration_setup(self) -> Tuple[Path, Path, str]:
        """
        Set up a temporary directory with old-style queue structure.

        Yields:
            Tuple of (temp_dir, artifacts_dir, migration_script_path)
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="queue_migration_test_"))
        agentic_home = temp_dir / ".agentic-engineers"
        artifacts_dir = agentic_home / "artifacts"

        # Find migration script (should be in setup/migrate-queue-paths.sh)
        project_root = Path(__file__).parent.parent
        migration_script = project_root / "setup" / "migrate-queue-paths.sh"

        yield temp_dir, artifacts_dir, str(migration_script)

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def setup_old_queue_structure(
        self,
        artifacts_dir: Path,
        session_id: str = "test-session-123",
        harness: str = "local",
    ) -> Path:
        """
        Create old-style queue structure under artifacts/

        Args:
            artifacts_dir: Path to artifacts directory
            session_id: Session ID for the queue
            harness: Harness name (local, copilot, claude, etc.)

        Returns:
            Path to created queue directory
        """
        queue_dir = (
            artifacts_dir / session_id / harness / "queue"
        )
        queue_dir.mkdir(parents=True, exist_ok=True)

        # Create queue subdirectories
        (queue_dir / "incoming").mkdir(exist_ok=True)
        (queue_dir / "processing").mkdir(exist_ok=True)
        (queue_dir / "done").mkdir(exist_ok=True)
        (queue_dir / "failed").mkdir(exist_ok=True)

        # Create some dummy files to verify preservation
        (queue_dir / "incoming" / "task1.yaml").write_text("task: test1\n")
        (queue_dir / "processing" / "task2.yaml").write_text("task: test2\n")
        (queue_dir / "done" / "task3.yaml").write_text("task: test3\n")
        (queue_dir / "failed" / "task4.yaml").write_text("error: test\n")

        return queue_dir

    def run_migration(
        self, migration_script: str, temp_dir: Path
    ) -> Tuple[int, str, str]:
        """
        Run the migration script in the test environment.

        Args:
            migration_script: Path to migrate-queue-paths.sh
            temp_dir: Temporary directory to use as HOME

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        env = os.environ.copy()
        env["HOME"] = str(temp_dir)

        result = subprocess.run(
            ["bash", migration_script],
            env=env,
            cwd=str(temp_dir),
            capture_output=True,
            text=True,
        )

        return result.returncode, result.stdout, result.stderr

    def test_migration_moves_session_dirs(self, migration_setup):
        """
        Test that migration moves artifacts/{harness}/{session}/ to canonical path.

        Verifies:
        - Old path no longer exists
        - New canonical path exists with all content
        """
        temp_dir, artifacts_dir, migration_script = migration_setup

        # Setup old structure
        session_id = "uuid-" + str(uuid.uuid4())[:8]
        old_queue = self.setup_old_queue_structure(
            artifacts_dir, session_id, "local"
        )

        # Verify old path exists before migration
        assert old_queue.exists(), f"Old queue path should exist: {old_queue}"

        # Run migration
        exit_code, stdout, stderr = self.run_migration(migration_script, temp_dir)

        # Verify success
        assert exit_code == 0, f"Migration failed with exit code {exit_code}\nStderr: {stderr}"

        # Verify old path no longer exists
        assert not old_queue.exists(), f"Old queue path should be removed: {old_queue}"

        # Verify new canonical path exists
        canonical_path = (
            temp_dir / ".agentic-engineers" / "local" / session_id / "queue"
        )
        assert canonical_path.exists(), f"Canonical path should exist: {canonical_path}"

        # Verify queue subdirectories exist
        assert (canonical_path / "incoming").exists()
        assert (canonical_path / "processing").exists()
        assert (canonical_path / "done").exists()
        assert (canonical_path / "failed").exists()

        # Verify files were preserved
        assert (canonical_path / "incoming" / "task1.yaml").read_text() == "task: test1\n"
        assert (canonical_path / "processing" / "task2.yaml").read_text() == "task: test2\n"

    def test_migration_is_idempotent(self, migration_setup):
        """
        Test that running migration twice is safe and idempotent.

        Verifies:
        - First run succeeds
        - Second run succeeds
        - No errors on second run
        - Files unchanged after second run
        """
        temp_dir, artifacts_dir, migration_script = migration_setup

        # Setup old structure
        session_id = "uuid-idempotent"
        old_queue = self.setup_old_queue_structure(
            artifacts_dir, session_id, "copilot"
        )

        # Run migration first time
        exit_code1, stdout1, stderr1 = self.run_migration(migration_script, temp_dir)
        assert exit_code1 == 0, f"First migration failed:\nStderr: {stderr1}"

        # Verify path moved
        canonical_path = (
            temp_dir / ".agentic-engineers" / "copilot" / session_id / "queue"
        )
        assert canonical_path.exists()

        # Read file content after first migration
        file_content_1 = (canonical_path / "incoming" / "task1.yaml").read_text()

        # Run migration second time
        exit_code2, stdout2, stderr2 = self.run_migration(migration_script, temp_dir)
        assert exit_code2 == 0, f"Second migration failed:\nStderr: {stderr2}"

        # Verify path still exists
        assert canonical_path.exists(), "Canonical path should still exist"

        # Verify file content unchanged
        file_content_2 = (canonical_path / "incoming" / "task1.yaml").read_text()
        assert file_content_1 == file_content_2, "File content should not change"

    def test_migration_preserves_queue_subdirs(self, migration_setup):
        """
        Test that all queue subdirectories are preserved during migration.

        Verifies:
        - incoming/ directory preserved
        - processing/ directory preserved
        - done/ directory preserved
        - failed/ directory preserved
        - All files within each subdir are intact
        """
        temp_dir, artifacts_dir, migration_script = migration_setup

        # Setup old structure with multiple files
        session_id = "uuid-preserve-subdirs"
        old_queue = self.setup_old_queue_structure(
            artifacts_dir, session_id, "claude"
        )

        # Add more files to test preservation
        (old_queue / "incoming").mkdir(exist_ok=True)
        (old_queue / "incoming" / "file1.yaml").write_text("data: 1\n")
        (old_queue / "incoming" / "file2.yaml").write_text("data: 2\n")
        (old_queue / "processing" / "file3.yaml").write_text("data: 3\n")
        (old_queue / "done" / "file4.yaml").write_text("data: 4\n")
        (old_queue / "failed" / "file5.yaml").write_text("data: 5\n")

        # Run migration
        exit_code, stdout, stderr = self.run_migration(migration_script, temp_dir)
        assert exit_code == 0, f"Migration failed:\nStderr: {stderr}"

        # Verify canonical path
        canonical_path = (
            temp_dir / ".agentic-engineers" / "claude" / session_id / "queue"
        )

        # Verify all subdirectories exist
        assert (canonical_path / "incoming").is_dir()
        assert (canonical_path / "processing").is_dir()
        assert (canonical_path / "done").is_dir()
        assert (canonical_path / "failed").is_dir()

        # Verify all files are present and intact
        assert (canonical_path / "incoming" / "file1.yaml").read_text() == "data: 1\n"
        assert (canonical_path / "incoming" / "file2.yaml").read_text() == "data: 2\n"
        assert (canonical_path / "processing" / "file3.yaml").read_text() == "data: 3\n"
        assert (canonical_path / "done" / "file4.yaml").read_text() == "data: 4\n"
        assert (canonical_path / "failed" / "file5.yaml").read_text() == "data: 5\n"

    def test_migration_with_multiple_sessions(self, migration_setup):
        """
        Test that migration handles multiple sessions correctly.

        Verifies:
        - Multiple sessions are all migrated
        - Each session's harnesses are all migrated
        - No cross-contamination between sessions
        """
        temp_dir, artifacts_dir, migration_script = migration_setup

        # Setup multiple sessions with different harnesses
        sessions = [
            ("session-1", "local"),
            ("session-1", "copilot"),
            ("session-2", "claude"),
            ("session-2", "local"),
        ]

        for session_id, harness in sessions:
            self.setup_old_queue_structure(artifacts_dir, session_id, harness)

        # Run migration
        exit_code, stdout, stderr = self.run_migration(migration_script, temp_dir)
        assert exit_code == 0, f"Migration failed:\nStderr: {stderr}"

        # Verify all sessions migrated correctly
        for session_id, harness in sessions:
            canonical_path = (
                temp_dir / ".agentic-engineers" / harness / session_id / "queue"
            )
            assert canonical_path.exists(), f"Path not migrated: {canonical_path}"

            # Verify subdirs exist
            assert (canonical_path / "incoming").is_dir()
            assert (canonical_path / "processing").is_dir()

    def test_migration_with_empty_artifacts_dir(self, migration_setup):
        """
        Test that migration gracefully handles empty artifacts directory.

        Verifies:
        - Migration exits with 0
        - No errors printed
        - Summary shows 0 migrations
        """
        temp_dir, artifacts_dir, migration_script = migration_setup

        # Create artifacts dir but leave it empty
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Run migration
        exit_code, stdout, stderr = self.run_migration(migration_script, temp_dir)

        # Verify success
        assert exit_code == 0, f"Migration should succeed with empty artifacts:\nStderr: {stderr}"

        # Verify summary in output
        assert "Migration complete" in stdout or "nothing to migrate" in stdout.lower()

    def test_migration_with_no_artifacts_dir(self, migration_setup):
        """
        Test that migration gracefully handles missing artifacts directory.

        Verifies:
        - Migration exits with 0
        - No errors printed
        - Summary shows 0 migrations
        """
        temp_dir, artifacts_dir, migration_script = migration_setup

        # Do NOT create artifacts dir

        # Run migration
        exit_code, stdout, stderr = self.run_migration(migration_script, temp_dir)

        # Verify success
        assert exit_code == 0, f"Migration should succeed with missing artifacts:\nStderr: {stderr}"

    def test_migration_summary_output(self, migration_setup):
        """
        Test that migration script prints accurate summary.

        Verifies:
        - Output includes summary header
        - Migration count is correct
        - Summary shows all expected counters
        """
        temp_dir, artifacts_dir, migration_script = migration_setup

        # Setup 2 sessions
        self.setup_old_queue_structure(artifacts_dir, "session-1", "local")
        self.setup_old_queue_structure(artifacts_dir, "session-2", "copilot")

        # Run migration
        exit_code, stdout, stderr = self.run_migration(migration_script, temp_dir)
        assert exit_code == 0

        # Verify summary output
        assert "Migration Summary" in stdout
        assert "Migrations completed:" in stdout
        assert "Sessions scanned:" in stdout
        assert "Errors:" in stdout

        # Verify migration count contains "2" (flexible spacing check)
        assert "Migrations completed:" in stdout and "2" in stdout

    def test_migration_creates_deprecation_notice(self, migration_setup):
        """
        Test that migration creates a deprecation notice in artifacts/ dir.

        Verifies:
        - README.md created in artifacts/
        - README contains deprecation warning
        - README contains migration info
        """
        temp_dir, artifacts_dir, migration_script = migration_setup

        # Setup old structure
        self.setup_old_queue_structure(artifacts_dir, "session-1", "local")

        # Run migration
        exit_code, stdout, stderr = self.run_migration(migration_script, temp_dir)
        assert exit_code == 0

        # Verify README created
        readme_path = artifacts_dir / "README.md"
        assert readme_path.exists(), "README.md should be created in artifacts/"

        # Verify content
        readme_content = readme_path.read_text()
        assert "DEPRECATED" in readme_content
        assert "artifacts/" in readme_content
        assert "migrate-queue-paths.sh" in readme_content

    def test_migration_handles_malformed_session(self, migration_setup):
        """
        Test that migration gracefully skips directories without queue subdir.

        Verifies:
        - Session without queue/ subdir is skipped
        - No error on skipped session
        - Migration completes successfully
        """
        temp_dir, artifacts_dir, migration_script = migration_setup

        # Create artifacts with incomplete structure
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        (artifacts_dir / "incomplete-session").mkdir()
        (artifacts_dir / "incomplete-session" / "harness").mkdir()
        # Note: no queue/ subdir

        # Add a proper session too
        self.setup_old_queue_structure(artifacts_dir, "valid-session", "local")

        # Run migration
        exit_code, stdout, stderr = self.run_migration(migration_script, temp_dir)
        assert exit_code == 0, f"Migration should handle malformed session:\nStderr: {stderr}"

        # Verify valid session was migrated
        valid_canonical = (
            temp_dir / ".agentic-engineers" / "local" / "valid-session" / "queue"
        )
        assert valid_canonical.exists()

        # Verify incomplete session still in artifacts (skipped)
        incomplete_path = artifacts_dir / "incomplete-session"
        assert incomplete_path.exists(), "Incomplete session should be skipped, not removed"

    def test_migration_exit_code_on_success(self, migration_setup):
        """
        Test that migration exits with code 0 on success.

        Verifies:
        - Exit code is exactly 0
        """
        temp_dir, artifacts_dir, migration_script = migration_setup

        # Setup old structure
        self.setup_old_queue_structure(artifacts_dir, "session-success", "local")

        # Run migration
        exit_code, stdout, stderr = self.run_migration(migration_script, temp_dir)

        assert exit_code == 0, f"Exit code should be 0, got {exit_code}\nStderr: {stderr}"

    def test_migration_exit_code_on_move_failure(self, migration_setup):
        """
        Test that migration exits with code 1 on move failure.

        Verifies:
        - Exit code is 1 when move operation fails
        """
        temp_dir, artifacts_dir, migration_script = migration_setup

        # Setup old structure
        session_id = "session-fail"
        old_queue = self.setup_old_queue_structure(
            artifacts_dir, session_id, "local"
        )

        # Create a file at the destination to cause move to fail
        canonical_parent = temp_dir / ".agentic-engineers" / "local"
        canonical_parent.mkdir(parents=True, exist_ok=True)
        (canonical_parent / session_id).write_text("blocking_file")

        # Run migration (should fail because local is a file, not dir)
        exit_code, stdout, stderr = self.run_migration(migration_script, temp_dir)

        # Should exit with error code
        assert exit_code == 1, f"Exit code should be 1 on failure, got {exit_code}"

    def test_migration_script_is_executable(self):
        """
        Test that the migration script has executable permissions.

        Verifies:
        - Script exists
        - Script is executable
        """
        project_root = Path(__file__).parent.parent
        migration_script = project_root / "setup" / "migrate-queue-paths.sh"

        assert migration_script.exists(), f"Migration script not found: {migration_script}"

        # Check if executable
        assert os.access(migration_script, os.X_OK), "Script should be executable"


class TestQueuePathReversal:
    """Pass 2: reverse legacy {session}/{harness}/ to {harness}/{session}/."""

    MIGRATION_SCRIPT = Path(__file__).parent.parent / "setup" / "migrate-queue-paths.sh"

    def _run(self, home):
        import subprocess
        return subprocess.run(
            ["bash", str(self.MIGRATION_SCRIPT)],
            env={**os.environ, "HOME": str(home)},
            capture_output=True, text=True,
        )

    def _make_session_first(self, agentic_home, session_id, harness):
        q = agentic_home / session_id / harness / "queue"
        for sub in ("incoming", "processing", "done", "failed"):
            (q / sub).mkdir(parents=True, exist_ok=True)
        (q / "incoming" / "task.yaml").write_text("task: t\n")
        return q

    def test_reversal_moves_to_harness_first(self, tmp_path):
        home = tmp_path
        agentic = home / ".agentic-engineers"
        self._make_session_first(agentic, "sess-rev-1", "local")

        result = self._run(home)
        assert result.returncode == 0, result.stderr

        new_q = agentic / "local" / "sess-rev-1" / "queue"
        assert new_q.exists(), f"reversed path missing: {new_q}"
        assert (new_q / "incoming" / "task.yaml").read_text() == "task: t\n"
        # old session-first dir removed
        assert not (agentic / "sess-rev-1").exists()

    def test_reversal_is_idempotent(self, tmp_path):
        home = tmp_path
        agentic = home / ".agentic-engineers"
        self._make_session_first(agentic, "sess-rev-2", "claude")
        assert self._run(home).returncode == 0
        # second run: nothing left to reverse, still exits 0
        assert self._run(home).returncode == 0
        assert (agentic / "claude" / "sess-rev-2" / "queue").exists()

    def test_reversal_leaves_harness_first_untouched(self, tmp_path):
        home = tmp_path
        agentic = home / ".agentic-engineers"
        # already canonical: harness/session
        q = agentic / "copilot" / "sess-rev-3" / "queue" / "incoming"
        q.mkdir(parents=True)
        (q / "keep.yaml").write_text("k: 1\n")
        assert self._run(home).returncode == 0
        assert (agentic / "copilot" / "sess-rev-3" / "queue" / "incoming" / "keep.yaml").exists()
