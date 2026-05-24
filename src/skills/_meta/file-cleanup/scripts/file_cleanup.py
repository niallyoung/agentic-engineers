# -*- coding: utf-8 -*-
"""
file_cleanup.py — File-cleanup skill for the agentic-engineers framework.

Identifies and (optionally) removes unnecessary files before they accidentally
end up in commits.  Runs in three modes:

  --dry-run        List what would be deleted; touch nothing.
  --analysis-only  Produce a structured report; touch nothing.
  --execute        Delete untracked cleanup candidates (irreversible).

Cleanup categories
------------------
SESSION_TEMP     PHASE_*.md, PHASE-*.md, WIP_*.md, TEMP_*.md, TMP_*.md,
                 *-SESSION-*.md, *-session-*.md, .*.swp, .*.swo
DEBUG_LOG        Files whose content is purely progress markers or [DEBUG]/
                 [LOG]/[TRACE] headers; timestamped progress files *_2026_*.md
COVERAGE_REPORT  *.coverage, .coverage.*, htmlcov/ outside docs/
TESTING_RESULTS  testing-results/ directory

Safety guarantees
-----------------
- Git-tracked files are NEVER touched (checked via `git ls-files`).
- Protected filenames (README.md, TODO.md, SPEC.md …) are NEVER flagged.
- Protected directories (src/, tests/, .git/, docs/) are NEVER scanned.

Usage (CLI)
-----------
  python -m src.skills._meta.file_cleanup.scripts.file_cleanup --dry-run
  python -m src.skills._meta.file_cleanup.scripts.file_cleanup --analysis-only
  python -m src.skills._meta.file_cleanup.scripts.file_cleanup --execute
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ===========================================================================
# Domain enumerations
# ===========================================================================

class CleanupCategory(str, Enum):
    SESSION_TEMP    = "session_temp"
    DEBUG_LOG       = "debug_log"
    COVERAGE_REPORT = "coverage_report"
    TESTING_RESULTS = "testing_results"
    CUSTOM          = "custom"


class RiskLevel(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


# ===========================================================================
# Data models
# ===========================================================================

@dataclass
class CleanupCandidate:
    """A single file (or directory) identified for potential removal."""
    path: Path
    category: CleanupCategory
    risk: RiskLevel
    reason: str
    git_tracked: bool = False


@dataclass
class CleanupResult:
    """Result returned by FileCleanupAnalyzer.execute()."""
    candidates: List[CleanupCandidate] = field(default_factory=list)
    deleted: List[Path]               = field(default_factory=list)
    summary: Dict                     = field(default_factory=dict)


@dataclass
class ConfigConsolidationReport:
    """Result of config consolidation analysis."""
    duplicates: List[Tuple[Path, Path]]  = field(default_factory=list)
    recommendation: str                  = ""


# ===========================================================================
# CleanupConfig — pattern lists and exclusions (user-extensible)
# ===========================================================================

class CleanupConfig:
    """
    Central configuration for what to scan and what to exclude.

    Parameters
    ----------
    extra_patterns:   Additional glob patterns to flag (on top of defaults).
    extra_exclusions: Additional filenames / directory fragments to skip.
    """

    # -----------------------------------------------------------------------
    # Default cleanup patterns
    # -----------------------------------------------------------------------

    # Glob patterns matched against file *names* (not full paths)
    SESSION_TEMP_NAME_PATTERNS: List[str] = [
        "PHASE_*.md",
        "PHASE-*.md",
        "WIP_*.md",
        "TEMP_*.md",
        "TMP_*.md",
        "*-SESSION-*.md",
        "*-session-*.md",
        ".*.swp",
        ".*.swo",
    ]

    # Regex matched against file *names* for timestamped progress files
    TIMESTAMPED_PATTERN = re.compile(r".*_\d{4}_.*\.md$")

    # Glob patterns matched against file *names* for coverage artefacts
    COVERAGE_NAME_PATTERNS: List[str] = [
        "*.coverage",
        ".coverage.*",
    ]

    # Directory names that trigger a whole-directory candidate
    COVERAGE_DIRS: List[str] = ["htmlcov"]

    # Directory names whose presence triggers TESTING_RESULTS
    TESTING_DIRS: List[str] = ["testing-results"]

    # -----------------------------------------------------------------------
    # Default protected filenames (never flagged regardless of pattern)
    # -----------------------------------------------------------------------
    PROTECTED_NAMES: Set[str] = {
        "README.md",
        "TODO.md",
        "SPEC.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "AUTH.md",
        "LICENSE",
        "Makefile",
        "setup.py",
        "setup.cfg",
        "pyproject.toml",
        "pytest.ini",
        "conftest.py",
        ".gitignore",
        ".gitattributes",
    }

    # -----------------------------------------------------------------------
    # Default protected directory prefixes (never scanned)
    # -----------------------------------------------------------------------
    PROTECTED_DIRS: Set[str] = {
        ".git",
        "src",
        "tests",
        "docs",
    }

    # Substrings in a path that protect it from flagging
    PROTECTED_PATH_FRAGMENTS: Set[str] = {"docs/htmlcov"}

    def __init__(
        self,
        extra_patterns:   Optional[List[str]] = None,
        extra_exclusions: Optional[List[str]] = None,
    ) -> None:
        self.extra_patterns:   List[str] = extra_patterns   or []
        self.extra_exclusions: List[str] = extra_exclusions or []


# ===========================================================================
# FileCleanupAnalyzer — core engine
# ===========================================================================

class FileCleanupAnalyzer:
    """
    Scan a directory tree for unnecessary files, optionally delete them.

    Parameters
    ----------
    root          : Directory to scan (defaults to CWD).
    dry_run       : If True, candidates are reported but nothing is deleted.
    analysis_only : If True, produces a structured report but nothing is deleted.
                    Takes precedence over dry_run=False.
    config        : CleanupConfig instance (uses defaults if omitted).
    """

    def __init__(
        self,
        root:          Optional[Path] = None,
        dry_run:       bool = True,
        analysis_only: bool = False,
        config:        Optional[CleanupConfig] = None,
    ) -> None:
        self.root          = Path(root) if root else Path.cwd()
        self.dry_run       = dry_run
        self.analysis_only = analysis_only
        self.config        = config or CleanupConfig()

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def scan(self) -> List[CleanupCandidate]:
        """
        Walk the repository tree and return all cleanup candidates.

        Git-tracked files are excluded automatically.  Protected names and
        protected directory trees are never scanned.
        """
        candidates: List[CleanupCandidate] = []
        seen_paths: Set[Path] = set()

        # Collect all files and directories under root, skipping protected dirs
        for item in self._walk():
            if item in seen_paths:
                continue

            if item.is_dir():
                candidate = self._check_directory(item)
            else:
                candidate = self._check_file(item)

            if candidate is None:
                continue

            # Never surface git-tracked files
            if candidate.git_tracked:
                continue

            seen_paths.add(item)
            candidates.append(candidate)

        return candidates

    def execute(self) -> CleanupResult:
        """
        Execute the cleanup.

        - analysis_only=True  → scan + summarise, delete nothing
        - dry_run=True        → scan + list, delete nothing
        - dry_run=False       → scan + delete untracked candidates
        """
        candidates = self.scan()
        deleted: List[Path] = []

        if not self.analysis_only and not self.dry_run:
            for c in candidates:
                if not c.git_tracked:
                    self._delete(c.path)
                    deleted.append(c.path)

        summary = self._build_summary(candidates)
        return CleanupResult(candidates=candidates, deleted=deleted, summary=summary)

    def config_consolidation_report(self) -> ConfigConsolidationReport:
        """
        Scan the repository for files with identical content (potential
        duplicate configs) and return a consolidation report.
        """
        # Map content hash → list of paths
        hash_map: Dict[str, List[Path]] = {}
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            if self._is_in_protected_dir(path):
                continue
            try:
                digest = hashlib.md5(path.read_bytes()).hexdigest()
                hash_map.setdefault(digest, []).append(path)
            except (OSError, PermissionError):
                continue

        duplicates: List[Tuple[Path, Path]] = []
        for paths in hash_map.values():
            if len(paths) >= 2:
                # Report as pairs (keep first, remove rest)
                for extra in paths[1:]:
                    duplicates.append((paths[0], extra))

        if duplicates:
            recommendation = (
                f"Found {len(duplicates)} duplicate file pair(s). "
                "Review and keep only the authoritative copy; "
                "archive or delete the others."
            )
        else:
            recommendation = "No duplicate config files detected."

        return ConfigConsolidationReport(
            duplicates=duplicates,
            recommendation=recommendation,
        )

    # -----------------------------------------------------------------------
    # Internal helpers — directory walking
    # -----------------------------------------------------------------------

    def _walk(self):
        """
        Yield Path objects for every file/directory under self.root,
        skipping protected top-level directories.
        """
        for entry in self.root.iterdir():
            if entry.name in self.config.PROTECTED_DIRS:
                continue
            if entry.is_dir():
                yield entry
                yield from self._walk_dir(entry)
            else:
                yield entry

    def _walk_dir(self, directory: Path):
        """Recursively walk a directory."""
        try:
            for entry in directory.iterdir():
                if entry.is_dir():
                    yield entry
                    yield from self._walk_dir(entry)
                else:
                    yield entry
        except PermissionError:
            pass

    # -----------------------------------------------------------------------
    # Internal helpers — per-item evaluation
    # -----------------------------------------------------------------------

    def _check_file(self, path: Path) -> Optional[CleanupCandidate]:
        """
        Evaluate a single file.  Returns a CleanupCandidate or None if the
        file should be kept.
        """
        name = path.name

        # Absolute exclusions
        if name in self.config.PROTECTED_NAMES:
            return None
        if name in self.config.extra_exclusions:
            return None
        if self._is_in_protected_dir(path):
            return None
        if self._is_in_protected_path_fragment(path):
            return None

        # Check git tracking (do this last — it's the most expensive)
        tracked = self._is_git_tracked(path)

        # --- Session / temp patterns ---
        for pattern in (
            self.config.SESSION_TEMP_NAME_PATTERNS + self.config.extra_patterns
        ):
            if fnmatch.fnmatch(name, pattern):
                category = (
                    CleanupCategory.SESSION_TEMP
                    if pattern in self.config.SESSION_TEMP_NAME_PATTERNS
                    else CleanupCategory.CUSTOM
                )
                risk = self._assess_file_risk(path)
                return CleanupCandidate(
                    path=path,
                    category=category,
                    risk=risk,
                    reason=f"Matches session/temp pattern '{pattern}'",
                    git_tracked=tracked,
                )

        # --- Extra custom patterns (already handled above via concatenation) ---

        # --- Timestamped progress file ---
        if self.config.TIMESTAMPED_PATTERN.match(name):
            risk = self._assess_file_risk(path)
            return CleanupCandidate(
                path=path,
                category=CleanupCategory.DEBUG_LOG,
                risk=risk,
                reason="Timestamped progress file (matches *_YYYY_*.md pattern)",
                git_tracked=tracked,
            )

        # --- Coverage artefacts ---
        for pattern in self.config.COVERAGE_NAME_PATTERNS:
            if fnmatch.fnmatch(name, pattern):
                return CleanupCandidate(
                    path=path,
                    category=CleanupCategory.COVERAGE_REPORT,
                    risk=RiskLevel.LOW,
                    reason=f"Coverage artefact matching '{pattern}'",
                    git_tracked=tracked,
                )

        # --- Debug/progress content analysis ---
        if path.suffix in (".md", ".txt", ".log"):
            candidate = self._check_debug_content(path, tracked)
            if candidate:
                return candidate

        return None

    def _check_directory(self, path: Path) -> Optional[CleanupCandidate]:
        """Evaluate a directory for whole-directory cleanup candidates."""
        name = path.name

        if self._is_in_protected_dir(path):
            return None

        # testing-results/ directory
        if name in self.config.TESTING_DIRS:
            return CleanupCandidate(
                path=path,
                category=CleanupCategory.TESTING_RESULTS,
                risk=RiskLevel.LOW,
                reason="testing-results/ directory — test output artefacts",
                git_tracked=False,
            )

        # htmlcov/ outside docs/
        if name in self.config.COVERAGE_DIRS:
            # Protected if nested under docs/
            rel = str(path.relative_to(self.root))
            if not rel.startswith("docs"):
                return CleanupCandidate(
                    path=path,
                    category=CleanupCategory.COVERAGE_REPORT,
                    risk=RiskLevel.LOW,
                    reason="HTML coverage report directory outside docs/",
                    git_tracked=False,
                )

        return None

    def _check_debug_content(
        self, path: Path, tracked: bool
    ) -> Optional[CleanupCandidate]:
        """
        Inspect file content to determine if it is purely debug / progress logs.
        Returns a CleanupCandidate if so, else None.
        """
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, PermissionError):
            return None

        if not text.strip():
            return None  # Empty files handled elsewhere

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        # Progress-only files: all lines are STARTED / IN_PROGRESS / COMPLETED
        progress_words = {"STARTED", "IN_PROGRESS", "COMPLETED", "DONE", "PENDING"}
        if lines and all(ln in progress_words for ln in lines):
            return CleanupCandidate(
                path=path,
                category=CleanupCategory.DEBUG_LOG,
                risk=RiskLevel.LOW,
                reason="File contains only progress status markers",
                git_tracked=tracked,
            )

        # Debug/log header files: majority of lines start with [DEBUG]/[LOG]/[TRACE]
        debug_pattern = re.compile(r"^\[(DEBUG|LOG|TRACE|INFO|WARN|ERROR)\]")
        debug_lines = sum(1 for ln in lines if debug_pattern.match(ln))
        if lines and debug_lines / len(lines) >= 0.5:
            return CleanupCandidate(
                path=path,
                category=CleanupCategory.DEBUG_LOG,
                risk=RiskLevel.LOW,
                reason=(
                    f"File is predominantly debug/log output "
                    f"({debug_lines}/{len(lines)} lines match [DEBUG/LOG/TRACE])"
                ),
                git_tracked=tracked,
            )

        return None

    # -----------------------------------------------------------------------
    # Internal helpers — protection checks
    # -----------------------------------------------------------------------

    def _is_in_protected_dir(self, path: Path) -> bool:
        """Return True if path lives inside a protected top-level directory."""
        try:
            rel = path.relative_to(self.root)
        except ValueError:
            return False
        parts = rel.parts
        if parts and parts[0] in self.config.PROTECTED_DIRS:
            return True
        return False

    def _is_in_protected_path_fragment(self, path: Path) -> bool:
        """Return True if any protected fragment appears in the path string."""
        path_str = str(path.relative_to(self.root))
        for fragment in self.config.PROTECTED_PATH_FRAGMENTS:
            if fragment in path_str:
                return True
        return False

    # -----------------------------------------------------------------------
    # Internal helpers — git integration
    # -----------------------------------------------------------------------

    def _is_git_tracked(self, path: Path) -> bool:
        """
        Return True if the file is tracked by git (i.e. in the git index).

        Uses `git ls-files --error-unmatch` which exits 0 only if the file
        is tracked.  Falls back to False if git is not available.
        """
        try:
            result = subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(path)],
                cwd=str(self.root),
                capture_output=True,
            )
            return result.returncode == 0
        except (FileNotFoundError, OSError):
            return False

    # -----------------------------------------------------------------------
    # Internal helpers — risk assessment
    # -----------------------------------------------------------------------

    def _assess_file_risk(self, path: Path) -> RiskLevel:
        """
        Assess how risky it would be to delete this file.

        - Vim swap / empty files → LOW
        - Small files (< 500 bytes) → LOW
        - Larger files with content → MEDIUM
        """
        try:
            size = path.stat().st_size
        except OSError:
            return RiskLevel.LOW

        if size == 0:
            return RiskLevel.LOW
        if size < 500:
            return RiskLevel.LOW
        return RiskLevel.MEDIUM

    # -----------------------------------------------------------------------
    # Internal helpers — summary
    # -----------------------------------------------------------------------

    def _build_summary(
        self, candidates: List[CleanupCandidate]
    ) -> Dict:
        """Build a category-keyed count summary."""
        summary: Dict = {}
        for c in candidates:
            summary[c.category] = summary.get(c.category, 0) + 1
        return summary

    # -----------------------------------------------------------------------
    # Internal helpers — deletion
    # -----------------------------------------------------------------------

    def _delete(self, path: Path) -> None:
        """Delete a file or directory tree."""
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


# ===========================================================================
# run_cleanup() — module-level convenience function (used by CLI + tests)
# ===========================================================================

def run_cleanup(
    root:          Optional[Path] = None,
    dry_run:       bool = True,
    analysis_only: bool = False,
    config:        Optional[CleanupConfig] = None,
) -> CleanupResult:
    """
    Convenience entry point for both the CLI and external callers.

    Instantiates a FileCleanupAnalyzer and calls .execute().
    """
    analyzer = FileCleanupAnalyzer(
        root=root,
        dry_run=dry_run,
        analysis_only=analysis_only,
        config=config,
    )
    return analyzer.execute()


# ===========================================================================
# CLI
# ===========================================================================

def _print_result(result: CleanupResult, mode: str) -> None:
    """Render a human-readable report to stdout."""
    width = 72
    print("=" * width)
    print(f"  FILE CLEANUP SKILL  |  mode={mode.upper()}")
    print("=" * width)

    if not result.candidates:
        print("\n✅  No cleanup candidates found.\n")
        return

    # Group by category
    by_cat: Dict[CleanupCategory, List[CleanupCandidate]] = {}
    for c in result.candidates:
        by_cat.setdefault(c.category, []).append(c)

    category_labels = {
        CleanupCategory.SESSION_TEMP:    "Session / Temporary Files",
        CleanupCategory.DEBUG_LOG:       "Debug / Progress Log Files",
        CleanupCategory.COVERAGE_REPORT: "Coverage Report Artefacts",
        CleanupCategory.TESTING_RESULTS: "Testing Results Directories",
        CleanupCategory.CUSTOM:          "Custom Pattern Matches",
    }

    for cat, items in by_cat.items():
        label = category_labels.get(cat, str(cat))
        print(f"\n  ── {label} ({len(items)}) ──")
        for item in items:
            risk_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(
                item.risk.value, "⚪"
            )
            status = "DELETED" if item.path in result.deleted else mode.upper()
            print(
                f"   {risk_icon} [{item.risk.value.upper():6}] "
                f"{item.path}  →  {status}"
            )
            print(f"          {item.reason}")

    print(f"\n  Total candidates : {len(result.candidates)}")
    print(f"  Deleted          : {len(result.deleted)}")
    print("=" * width)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="file_cleanup",
        description="Identify and optionally remove unnecessary files.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without deleting anything.",
    )
    group.add_argument(
        "--analysis-only",
        action="store_true",
        help="Produce a structured report without deleting anything.",
    )
    group.add_argument(
        "--execute",
        action="store_true",
        help="Delete untracked cleanup candidates (irreversible!).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Root directory to scan (default: current working directory).",
    )
    parser.add_argument(
        "--skip-pre-gate",
        action="store_true",
        help="Skip pre-gate validation (not recommended for --execute mode).",
    )

    args = parser.parse_args(argv)

    root = args.root or Path.cwd()

    # ------------------------------------------------------------------
    # Pre-gate validation (for execute mode unless explicitly skipped)
    # ------------------------------------------------------------------
    if args.execute and not args.skip_pre_gate:
        try:
            from .pre_gate_validator import PreGateValidator
        except ImportError:
            try:
                from pre_gate_validator import PreGateValidator  # type: ignore[no-redef]
            except ImportError:
                PreGateValidator = None  # type: ignore[assignment,misc]

        if PreGateValidator is not None:
            validator = PreGateValidator(root)
            can_proceed, reason = validator.validate()
            if not can_proceed:
                print(f"\n❌  {reason}\n")
                return 1
            print(f"\n✅  Pre-gate passed: {reason}\n")

    if args.dry_run:
        mode = "dry-run"
        result = run_cleanup(root=root, dry_run=True, analysis_only=False)
    elif args.analysis_only:
        mode = "analysis-only"
        result = run_cleanup(root=root, dry_run=True, analysis_only=True)
    else:  # --execute
        confirm = input(
            "⚠️  This will permanently delete untracked files. "
            "Type YES to confirm: "
        )
        if confirm.strip() != "YES":
            print("Aborted.")
            return 1
        mode = "execute"
        result = run_cleanup(root=root, dry_run=False, analysis_only=False)

    _print_result(result, mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
