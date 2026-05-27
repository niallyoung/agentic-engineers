"""
Multi-Harness Backup Integration Tests

Tests verify that the backup-harnesses.sh script correctly backs up all harness
configurations before fresh install, while never touching ~/.agentic-engineers/.

Requirements:
- Backup all harness configs (copilot, claude, pi, opencode) with YYYYMMDD timestamp
- Use simple mv (no rsync, no complex logic)
- Never touch ~/.agentic-engineers/ (shared queue directory)
- Handle missing directories gracefully
- Handle existing backups (same-day runs)
"""

import os
import pytest
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime


class TestBackupHarnesses:
    """Test backup-harnesses.sh functionality."""

    @pytest.fixture
    def temp_home(self, tmp_path):
        """Create a temporary HOME directory with harness configs."""
        home = tmp_path / "fake_home"
        home.mkdir()
        
        # Create harness directories
        harnesses = {
            "copilot": home / ".copilot",
            "claude": home / ".claude",
            "pi": home / ".pi",
            "opencode": home / ".config" / "opencode",
        }
        
        for name, path in harnesses.items():
            path.mkdir(parents=True)
            # Add a test file to verify backup
            (path / f"{name}_config.json").write_text(f'{{"harness": "{name}"}}')
        
        # Create ~/.agentic-engineers/ (should NEVER be backed up)
        agentic_dir = home / ".agentic-engineers"
        agentic_dir.mkdir()
        (agentic_dir / "queue_state.json").write_text('{"sessions": []}')
        
        return home, harnesses, agentic_dir

    @pytest.fixture
    def backup_script(self):
        """Get path to backup-harnesses.sh script."""
        repo_root = Path(__file__).parent.parent
        script = repo_root / "renderer" / "scripts" / "backup-harnesses.sh"
        assert script.exists(), f"backup-harnesses.sh not found at {script}"
        return script

    def test_backup_all_harnesses_success(self, temp_home, backup_script):
        """Test backing up all four harnesses successfully."""
        home, harnesses, agentic_dir = temp_home
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # Run backup script with --force (non-interactive)
        result = subprocess.run(
            ["bash", str(backup_script), "--force", "copilot", "claude", "pi", "opencode"],
            cwd=str(home),
            env={**os.environ, "HOME": str(home)},
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, f"Backup failed: {result.stderr}"
        
        # Verify all harnesses were backed up
        assert (home / f".copilot.{timestamp}").exists()
        assert (home / f".claude.{timestamp}").exists()
        assert (home / f".pi.{timestamp}").exists()
        assert (home / ".config" / f"opencode.{timestamp}").exists()
        
        # Verify backup contents
        assert (home / f".copilot.{timestamp}" / "copilot_config.json").exists()
        assert (home / f".claude.{timestamp}" / "claude_config.json").exists()
        assert (home / f".pi.{timestamp}" / "pi_config.json").exists()
        assert (home / ".config" / f"opencode.{timestamp}" / "opencode_config.json").exists()
        
        # Verify original dirs are gone (moved, not copied)
        assert not harnesses["copilot"].exists()
        assert not harnesses["claude"].exists()
        assert not harnesses["pi"].exists()
        assert not harnesses["opencode"].exists()
        
        # CRITICAL: Verify ~/.agentic-engineers/ is UNTOUCHED
        assert agentic_dir.exists()
        assert (agentic_dir / "queue_state.json").exists()
        assert (agentic_dir / "queue_state.json").read_text() == '{"sessions": []}'

    def test_backup_skips_missing_harness(self, temp_home, backup_script):
        """Test that backup gracefully skips harnesses that don't exist."""
        home, harnesses, agentic_dir = temp_home
        
        # Remove copilot harness
        import shutil
        shutil.rmtree(harnesses["copilot"])
        
        # Run backup script with --force (non-interactive)
        result = subprocess.run(
            ["bash", str(backup_script), "--force", "copilot", "claude", "pi", "opencode"],
            cwd=str(home),
            env={**os.environ, "HOME": str(home)},
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, f"Backup failed: {result.stderr}"
        
        # Verify copilot was skipped
        timestamp = datetime.now().strftime("%Y%m%d")
        assert not (home / f".copilot.{timestamp}").exists()
        
        # Verify others were backed up
        assert (home / f".claude.{timestamp}").exists()
        assert (home / f".pi.{timestamp}").exists()
        assert (home / ".config" / f"opencode.{timestamp}").exists()
        
        # Verify output mentions skipped harness
        assert "copilot" in result.stdout.lower()
        assert "skipped" in result.stdout.lower() or "no existing" in result.stdout.lower()

    def test_backup_handles_existing_backup(self, temp_home, backup_script):
        """Test that backup skips if same-day backup already exists."""
        home, harnesses, agentic_dir = temp_home
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # Create existing backup manually
        existing_backup = home / f".copilot.{timestamp}"
        existing_backup.mkdir()
        (existing_backup / "existing_config.json").write_text('{"existing": true}')
        
        # Remove original to simulate previous backup
        import shutil
        shutil.rmtree(harnesses["copilot"])
        
        # Run backup script with --force (non-interactive)
        result = subprocess.run(
            ["bash", str(backup_script), "--force", "copilot"],
            cwd=str(home),
            env={**os.environ, "HOME": str(home)},
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, f"Backup failed: {result.stderr}"
        
        # Verify existing backup was preserved
        assert existing_backup.exists()
        assert (existing_backup / "existing_config.json").exists()
        
        # Verify output mentions existing backup
        assert "already exists" in result.stdout.lower() or "skipped" in result.stdout.lower()

    def test_backup_timestamp_format(self, temp_home, backup_script):
        """Test that backup uses correct YYYYMMDD timestamp format."""
        home, harnesses, agentic_dir = temp_home
        
        # Run backup script with --force (non-interactive)
        result = subprocess.run(
            ["bash", str(backup_script), "--force", "copilot"],
            cwd=str(home),
            env={**os.environ, "HOME": str(home)},
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, f"Backup failed: {result.stderr}"
        
        # Find backup directory
        backups = list(home.glob(".copilot.*"))
        assert len(backups) == 1, f"Expected 1 backup, found {len(backups)}"
        
        backup_dir = backups[0]
        timestamp = backup_dir.name.split(".")[-1]
        
        # Verify timestamp format: YYYYMMDD (8 digits)
        assert len(timestamp) == 8, f"Timestamp should be 8 digits, got: {timestamp}"
        assert timestamp.isdigit(), f"Timestamp should be numeric, got: {timestamp}"
        
        # Verify timestamp is valid date
        today = datetime.now().strftime("%Y%m%d")
        assert timestamp == today, f"Timestamp {timestamp} doesn't match today {today}"

    def test_backup_never_touches_agentic_engineers(self, temp_home, backup_script):
        """Test that ~/.agentic-engineers/ is NEVER modified during backup."""
        home, harnesses, agentic_dir = temp_home
        
        # Add more files to ~/.agentic-engineers/
        queue_dir = agentic_dir / "queue"
        queue_dir.mkdir()
        (queue_dir / "incoming" / "task1.yaml").parent.mkdir(parents=True)
        (queue_dir / "incoming" / "task1.yaml").write_text("task: test")
        (queue_dir / "active" / "task2.yaml").parent.mkdir(parents=True)
        (queue_dir / "active" / "task2.yaml").write_text("task: active")
        
        # Get checksums before backup
        before_checksums = {}
        for path in agentic_dir.rglob("*"):
            if path.is_file():
                before_checksums[str(path.relative_to(agentic_dir))] = path.read_text()
        
        # Run backup script with --force (non-interactive)
        result = subprocess.run(
            ["bash", str(backup_script), "--force", "copilot", "claude", "pi", "opencode"],
            cwd=str(home),
            env={**os.environ, "HOME": str(home)},
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, f"Backup failed: {result.stderr}"
        
        # Verify ~/.agentic-engineers/ structure unchanged
        assert agentic_dir.exists()
        assert (agentic_dir / "queue").exists()
        assert (agentic_dir / "queue" / "incoming").exists()
        assert (agentic_dir / "queue" / "active").exists()
        
        # Get checksums after backup
        after_checksums = {}
        for path in agentic_dir.rglob("*"):
            if path.is_file():
                after_checksums[str(path.relative_to(agentic_dir))] = path.read_text()
        
        # Verify ALL files unchanged
        assert before_checksums == after_checksums, \
            "~/.agentic-engineers/ was modified during backup!"

    def test_backup_with_no_arguments_defaults_to_all(self, temp_home, backup_script):
        """Test that running backup with no args backs up all harnesses."""
        home, harnesses, agentic_dir = temp_home
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # Run backup script with no arguments (but --force for non-interactive)
        result = subprocess.run(
            ["bash", str(backup_script), "--force"],
            cwd=str(home),
            env={**os.environ, "HOME": str(home)},
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, f"Backup failed: {result.stderr}"
        
        # Verify all four harnesses were backed up
        assert (home / f".copilot.{timestamp}").exists()
        assert (home / f".claude.{timestamp}").exists()
        assert (home / f".pi.{timestamp}").exists()
        assert (home / ".config" / f"opencode.{timestamp}").exists()

    def test_backup_single_harness(self, temp_home, backup_script):
        """Test backing up a single harness only."""
        home, harnesses, agentic_dir = temp_home
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # Run backup for copilot only (with --force for non-interactive)
        result = subprocess.run(
            ["bash", str(backup_script), "--force", "copilot"],
            cwd=str(home),
            env={**os.environ, "HOME": str(home)},
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, f"Backup failed: {result.stderr}"
        
        # Verify only copilot was backed up
        assert (home / f".copilot.{timestamp}").exists()
        assert not (home / f".claude.{timestamp}").exists()
        assert not (home / f".pi.{timestamp}").exists()
        assert not (home / ".config" / f"opencode.{timestamp}").exists()
        
        # Verify others still exist (not backed up)
        assert harnesses["claude"].exists()
        assert harnesses["pi"].exists()
        assert harnesses["opencode"].exists()

    def test_backup_invalid_harness_name(self, temp_home, backup_script):
        """Test that backup fails with invalid harness name."""
        home, harnesses, agentic_dir = temp_home
        
        # Run backup with invalid harness (with --force for non-interactive)
        result = subprocess.run(
            ["bash", str(backup_script), "--force", "invalid_harness"],
            cwd=str(home),
            env={**os.environ, "HOME": str(home)},
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 1, "Backup should fail with invalid harness"
        
        # Verify error message mentions valid harnesses
        assert "invalid_harness" in result.stdout.lower() or "invalid_harness" in result.stderr.lower()
        assert "copilot" in result.stdout.lower() or "copilot" in result.stderr.lower()

    def test_backup_interactive_prompt_accept(self, temp_home, backup_script):
        """Test backup proceeds when user confirms with 'y'."""
        home, harnesses, agentic_dir = temp_home
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # Run backup with user input "y" (accept)
        result = subprocess.run(
            ["bash", str(backup_script), "copilot"],
            cwd=str(home),
            env={**os.environ, "HOME": str(home)},
            input="y\n",  # Simulate user typing "y" + Enter
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, f"Backup failed: {result.stderr}"
        
        # Verify copilot was backed up
        assert (home / f".copilot.{timestamp}").exists()
        assert not harnesses["copilot"].exists()
        
        # Verify interactive prompt was shown
        assert "Backup copilot?" in result.stdout or "backup" in result.stdout.lower()
        assert "Source:" in result.stdout
        assert "Backup to:" in result.stdout
        assert "Size:" in result.stdout

    def test_backup_interactive_prompt_decline(self, temp_home, backup_script):
        """Test backup is skipped when user declines with 'n'."""
        home, harnesses, agentic_dir = temp_home
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # Run backup with user input "n" (decline)
        result = subprocess.run(
            ["bash", str(backup_script), "copilot"],
            cwd=str(home),
            env={**os.environ, "HOME": str(home)},
            input="n\n",  # Simulate user typing "n" + Enter
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, f"Backup failed: {result.stderr}"
        
        # Verify copilot was NOT backed up
        assert not (home / f".copilot.{timestamp}").exists()
        assert harnesses["copilot"].exists()
        
        # Verify skip message was shown
        assert "skipped" in result.stdout.lower()

    def test_backup_interactive_prompt_uppercase_Y(self, temp_home, backup_script):
        """Test backup proceeds when user confirms with uppercase 'Y'."""
        home, harnesses, agentic_dir = temp_home
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # Run backup with user input "Y" (accept, uppercase)
        result = subprocess.run(
            ["bash", str(backup_script), "claude"],
            cwd=str(home),
            env={**os.environ, "HOME": str(home)},
            input="Y\n",  # Simulate user typing "Y" + Enter
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, f"Backup failed: {result.stderr}"
        
        # Verify claude was backed up
        assert (home / f".claude.{timestamp}").exists()
        assert not harnesses["claude"].exists()

    def test_backup_force_flag_skips_prompts(self, temp_home, backup_script):
        """Test --force flag skips all interactive prompts."""
        home, harnesses, agentic_dir = temp_home
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # Run backup with --force flag (no input needed)
        result = subprocess.run(
            ["bash", str(backup_script), "--force", "copilot", "claude"],
            cwd=str(home),
            env={**os.environ, "HOME": str(home)},
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, f"Backup failed: {result.stderr}"
        
        # Verify both harnesses were backed up
        assert (home / f".copilot.{timestamp}").exists()
        assert (home / f".claude.{timestamp}").exists()
        
        # Verify no prompts were shown
        assert "Proceed with backup?" not in result.stdout
        assert "NON-INTERACTIVE mode" in result.stdout

    def test_backup_multiple_harnesses_interactive(self, temp_home, backup_script):
        """Test interactive prompts for multiple harnesses (mix of y/n)."""
        home, harnesses, agentic_dir = temp_home
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # Run backup with mixed responses: y, n, y (copilot yes, claude no, pi yes)
        result = subprocess.run(
            ["bash", str(backup_script), "copilot", "claude", "pi"],
            cwd=str(home),
            env={**os.environ, "HOME": str(home)},
            input="y\nn\ny\n",  # Accept copilot, decline claude, accept pi
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, f"Backup failed: {result.stderr}"
        
        # Verify copilot and pi were backed up, claude was not
        assert (home / f".copilot.{timestamp}").exists()
        assert not (home / f".claude.{timestamp}").exists()
        assert (home / f".pi.{timestamp}").exists()
        
        # Verify original states
        assert not harnesses["copilot"].exists()
        assert harnesses["claude"].exists()
        assert not harnesses["pi"].exists()
        
        # Verify summary shows correct counts
        assert "Backed up" in result.stdout
        assert "Skipped" in result.stdout


class TestBackupMakeTarget:
    """Test make clean-install target integration."""

    def test_make_clean_install_calls_backup(self):
        """Test that 'make clean-install' calls backup script."""
        repo_root = Path(__file__).parent.parent
        makefile = repo_root / "Makefile"
        
        # Read Makefile
        makefile_content = makefile.read_text()
        
        # Verify clean-install target exists
        assert "clean-install:" in makefile_content
        
        # Verify it calls backup-harnesses.sh
        assert "backup-harnesses.sh" in makefile_content
        
        # Verify it passes all harnesses
        clean_install_section = makefile_content.split("clean-install:")[1].split("\n\n")[0]
        assert "copilot" in clean_install_section
        assert "claude" in clean_install_section
        assert "pi" in clean_install_section
        assert "opencode" in clean_install_section
        
        # Verify it calls make install after backup
        assert "$(MAKE) install" in clean_install_section or "make install" in clean_install_section

    def test_make_install_unchanged(self):
        """Test that 'make install' is unchanged (no auto-backup)."""
        repo_root = Path(__file__).parent.parent
        makefile = repo_root / "Makefile"
        
        # Read Makefile
        makefile_content = makefile.read_text()
        
        # Extract install target (before clean-install)
        install_section = makefile_content.split("install:")[1].split("clean-install:")[0]
        
        # Verify install target does NOT call backup
        assert "backup-harnesses.sh" not in install_section
        assert "backup" not in install_section.lower() or "clean-install" in install_section


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
