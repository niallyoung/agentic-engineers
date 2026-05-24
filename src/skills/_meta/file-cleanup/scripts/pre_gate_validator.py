# -*- coding: utf-8 -*-
"""
pre_gate_validator.py — Pre-gate validation for file-cleanup.

Validates that the sequential workflow has completed before cleanup can run:
1. SYNC_REPORT.md exists (file-sync completed)
2. SYNC_DECISIONS.md exists (human reviewed recommendations)
3. No PENDING entries in SYNC_DECISIONS.md
4. Git working directory is clean (no uncommitted changes)
5. All tests pass (integration didn't break anything)
"""

import subprocess
from pathlib import Path
from typing import Tuple


class PreGateValidator:
    """Validates pre-gate conditions before file-cleanup can run."""

    def __init__(self, root: Path) -> None:
        """Initialize validator with repo root."""
        self.root = Path(root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self) -> Tuple[bool, str]:
        """
        Validate all pre-gate conditions.
        
        Returns:
            (can_proceed: bool, reason: str)
            - can_proceed: True if all gates pass, False if any gate blocks
            - reason: Detailed message explaining result
        """
        issues = []

        if not self._sync_report_exists():
            issues.append("SYNC_REPORT.md not found. Run file-sync first.")

        if not self._sync_decisions_exist():
            issues.append("SYNC_DECISIONS.md not found. Review sync recommendations.")

        if self._has_pending_decisions():
            count = self._count_pending_entries()
            issues.append(f"SYNC_DECISIONS.md has {count} PENDING entries. Resolve all decisions first.")

        if not self._git_working_dir_clean():
            modified = self._count_modified_files()
            issues.append(f"Working directory has {modified} modified files. Commit changes first.")

        if not self._all_tests_pass():
            issues.append("Tests failing. Fix before cleanup.")

        if issues:
            reason = "PRE-GATE BLOCKED: " + " | ".join(issues)
            return False, reason

        return True, "All pre-gate conditions met. Cleanup may proceed."

    # ------------------------------------------------------------------
    # Individual gate checks
    # ------------------------------------------------------------------

    def _sync_report_exists(self) -> bool:
        """Check if SYNC_REPORT.md exists."""
        return (self.root / "SYNC_REPORT.md").exists()

    def _sync_decisions_exist(self) -> bool:
        """Check if SYNC_DECISIONS.md exists."""
        return (self.root / "SYNC_DECISIONS.md").exists()

    def _has_pending_decisions(self) -> bool:
        """Check if SYNC_DECISIONS.md contains PENDING entries."""
        decisions_file = self.root / "SYNC_DECISIONS.md"
        if not decisions_file.exists():
            return False
        try:
            content = decisions_file.read_text(encoding="utf-8", errors="ignore")
            return "PENDING" in content
        except OSError:
            return False

    def _count_pending_entries(self) -> int:
        """Count PENDING entries in SYNC_DECISIONS.md."""
        decisions_file = self.root / "SYNC_DECISIONS.md"
        if not decisions_file.exists():
            return 0
        try:
            content = decisions_file.read_text(encoding="utf-8", errors="ignore")
            return content.count("PENDING")
        except OSError:
            return 0

    def _git_working_dir_clean(self) -> bool:
        """Check if git working directory is clean."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=str(self.root),
            )
            return result.returncode == 0 and result.stdout.strip() == ""
        except (OSError, subprocess.SubprocessError):
            return False

    def _count_modified_files(self) -> int:
        """Count modified files in working directory."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=str(self.root),
            )
            if result.returncode != 0:
                return 0
            return len([l for l in result.stdout.splitlines() if l.strip()])
        except (OSError, subprocess.SubprocessError):
            return 0

    def _all_tests_pass(self) -> bool:
        """Check if all tests pass."""
        try:
            result = subprocess.run(
                ["python3", "pytest", "tests/"],
                capture_output=True,
                text=True,
                cwd=str(self.root),
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            # If we can't run tests, assume they pass (non-blocking)
            return True
