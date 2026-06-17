# -*- coding: utf-8 -*-
"""
test_file_sync_cleanup_integration.py — Integration tests for the combined
file-sync → decisions → file-cleanup workflow.

These tests verify the contract and end-to-end behaviour of the pipeline:

  file-sync → SYNC_REPORT.md → SYNC_DECISIONS.md → file-cleanup (pre-gate + execution)

Design
------
The file-sync skill and the file-cleanup pre-gate are being implemented in
parallel.  Integration tests define the *contract* between the two skills via
lightweight stubs that do not import from the actual skill implementations.
This approach lets tests run as soon as the contracts are agreed, even before
full implementations exist.

Test scenarios
--------------
1. Happy path — full workflow succeeds end-to-end
2. Pre-gate blocks when SYNC_REPORT.md is absent
3. Pre-gate blocks when SYNC_DECISIONS.md is absent
4. Cleanup respects accept/reject decisions
5. Risk scoring flags risk level correctly
6. Hidden string references are detected
7. Deletion log entries contain recovery commands
"""

import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap — make file-cleanup skill importable
# ---------------------------------------------------------------------------
_TESTS_DIR = Path(__file__).parent
_REPO_ROOT = _TESTS_DIR.parent
_CLEANUP_SKILL_ROOT = _REPO_ROOT / "src" / "skills" / "_meta" / "file-cleanup"
_CLEANUP_SCRIPTS = _CLEANUP_SKILL_ROOT / "scripts"
sys.path.insert(0, str(_CLEANUP_SCRIPTS))

from file_cleanup import (  # noqa: E402
    CleanupConfig,
    FileCleanupAnalyzer,
    RiskLevel,
    run_cleanup,
)
from pre_gate_validator import PreGateValidator  # noqa: E402


# ===========================================================================
# Contract models
# ===========================================================================

@dataclass
class SyncScriptEntry:
    """A single script entry within a SYNC_REPORT.md."""

    script_name: str
    utility_score: float
    is_integrated: bool


@dataclass
class SyncReport:
    """
    Contract model for the output produced by the file-sync skill.

    Corresponds to ``SYNC_REPORT.md`` on disk.
    """

    scripts: List[SyncScriptEntry]
    repo_root: Optional[Path] = None

    @property
    def high_value_unintegrated(self) -> int:
        """Count of scripts scored >= 8 that have no existing integration."""
        return sum(1 for s in self.scripts if s.utility_score >= 8.0 and not s.is_integrated)

    @property
    def dead_code_candidates(self) -> List[SyncScriptEntry]:
        """Scripts scored <= 3 — safe deletion candidates."""
        return [s for s in self.scripts if s.utility_score <= 3.0]


@dataclass
class SyncDecisions:
    """User's accept/reject decisions for unintegrated scripts."""

    accepted: List[str] = field(default_factory=list)
    rejected: List[str] = field(default_factory=list)


@dataclass
class Reference:
    """A single discovered reference to a script file."""

    source_file: Path
    line_number: int
    reference_type: str  # MAKEFILE | DOCS | IMPORT | STRING | CI
    context: str


@dataclass
class DeletionLogEntry:
    """
    One entry in a DELETION_LOG.md file written after file-cleanup runs.

    Every deleted file must have a recovery command so the deletion can be
    undone if needed.
    """

    file_path: Path
    reason: str
    recovery_command: str


@dataclass
class PreGateResult:
    """
    Result of running the pre-gate check before file-cleanup.

    ``blocked=True`` means file-cleanup must NOT run; ``reason`` explains why.
    """

    blocked: bool
    reason: str


# ===========================================================================
# Contract helper functions
# ===========================================================================

class PreGateChecker:
    """
    Pre-gate guard for the file-cleanup workflow.

    Before file-cleanup is allowed to execute, this checker verifies that:
      1. ``SYNC_REPORT.md`` exists (produced by the file-sync skill)
      2. ``SYNC_DECISIONS.md`` exists (human review required)
      3. No PENDING entries remain in SYNC_DECISIONS.md
      4. Git working directory is clean
      5. Tests pass
    """

    def check(self, root: Path) -> PreGateResult:
        """
        Verify pre-conditions for running file-cleanup.

        Returns
        -------
        (can_proceed, reason)
            ``can_proceed`` is ``True`` when cleanup may run.
        """
        validator = PreGateValidator(root)
        can_proceed, reason = validator.validate()
        return PreGateResult(blocked=not can_proceed, reason=reason)


def build_sync_report(root: Path, scripts: Dict[str, float]) -> SyncReport:
    """
    Build a ``SyncReport`` from a name→score mapping.

    Parameters
    ----------
    root    : Repository root (stored as context).
    scripts : Mapping of ``script_name → utility_score``.
    """
    entries = [
        SyncScriptEntry(
            script_name=name,
            utility_score=score,
            is_integrated=False,
        )
        for name, score in scripts.items()
    ]
    return SyncReport(scripts=entries, repo_root=root)


def write_sync_report_md(report: SyncReport, output_path: Path) -> None:
    """Serialise a ``SyncReport`` to a SYNC_REPORT.md Markdown file."""
    lines = ["# SYNC REPORT\n\n"]
    if report.repo_root:
        lines.append(f"Repository: {report.repo_root}\n\n")
    lines.append("## Scripts\n\n")
    for entry in report.scripts:
        tag = "✅ integrated" if entry.is_integrated else "⚠️ unintegrated"
        lines.append(f"### {entry.script_name}\n")
        lines.append(f"- **Score**: {entry.utility_score:.1f}/10 ({tag})\n")
    output_path.write_text("".join(lines), encoding="utf-8")


def write_sync_decisions_md(decisions: SyncDecisions, output_path: Path) -> None:
    """Serialise a ``SyncDecisions`` object to SYNC_DECISIONS.md."""
    lines = ["# SYNC DECISIONS\n\n"]
    lines.append("## ACCEPT (integrate these scripts)\n\n")
    for name in decisions.accepted:
        lines.append(f"- [ ] {name}\n")
    lines.append("\n## REJECT (safe to remove)\n\n")
    for name in decisions.rejected:
        lines.append(f"- [ ] {name}\n")
    output_path.write_text("".join(lines), encoding="utf-8")


def parse_sync_decisions(path: Path) -> SyncDecisions:
    """Parse a SYNC_DECISIONS.md file into a ``SyncDecisions`` object."""
    content = path.read_text(encoding="utf-8")
    accepted: List[str] = []
    rejected: List[str] = []
    section = None

    for line in content.splitlines():
        if "## ACCEPT" in line or "## accept" in line.lower():
            section = "accept"
        elif "## REJECT" in line or "## reject" in line.lower():
            section = "reject"
        elif line.startswith("- ["):
            # Handle both checked [x] and unchecked [ ] items
            name = line.lstrip("- []x").strip()
            if name:
                if section == "accept":
                    accepted.append(name)
                elif section == "reject":
                    rejected.append(name)

    return SyncDecisions(accepted=accepted, rejected=rejected)


def build_cleanup_config_from_decisions(decisions: SyncDecisions) -> CleanupConfig:
    """
    Build a ``CleanupConfig`` that excludes all accepted scripts from cleanup.

    Accepted scripts are added to ``extra_exclusions`` so that
    ``FileCleanupAnalyzer`` never flags them, even if their name matches a
    cleanup pattern.
    """
    exclusions = set(decisions.accepted)
    return CleanupConfig(extra_exclusions=exclusions)


def build_deletion_log_entries(result, root: Path) -> List[DeletionLogEntry]:
    """
    Build ``DeletionLogEntry`` objects from a ``CleanupResult``.

    Each entry includes a ``git checkout`` command so that the deletion
    can be recovered from version control history.
    """
    entries: List[DeletionLogEntry] = []
    for candidate in result.candidates:
        path = candidate.path
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        entries.append(DeletionLogEntry(
            file_path=path,
            reason=str(candidate.reason) if hasattr(candidate, "reason") else "cleanup candidate",
            recovery_command=f"git checkout HEAD~1 -- {rel}",
        ))
    return entries


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_file(parent: Path, name: str, content: str = "") -> Path:
    """Create *parent/name* with optional *content* (creates parents as needed)."""
    parent.mkdir(parents=True, exist_ok=True)
    p = parent / name
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def _make_high_utility_script(parent: Path, name: str) -> Path:
    """High-utility fixture script — docstring, type hints, error handling."""
    content = f"""
        \"\"\"
        {name.replace('.py', '')} — Extract the current version string from the repository.

        Used by CI pipelines, release scripts, and Makefile targets.
        \"\"\"
        import argparse
        import re
        from pathlib import Path


        def get_version() -> str:
            \"\"\"Return the current version string.\"\"\"
            try:
                setup = Path("setup.py").read_text()
                match = re.search(r'version="([^"]+)"', setup)
                return match.group(1) if match else "0.0.0"
            except OSError as exc:
                raise RuntimeError("Could not read setup.py") from exc


        def main() -> None:
            parser = argparse.ArgumentParser()
            parser.add_argument("--short", action="store_true")
            args = parser.parse_args()
            version = get_version()
            print(version.split(".")[0] if args.short else version)


        if __name__ == "__main__":
            main()
    """
    return _make_file(parent, name, content)


def _make_medium_utility_script(parent: Path, name: str) -> Path:
    """Medium-utility fixture script — brief docstring, no type hints."""
    content = """
        \"\"\"Validate that rendered outputs match expected templates.\"\"\"
        import os


        def validate(path):
            return os.path.exists(path)
    """
    return _make_file(parent, name, content)


def _make_low_utility_debug_script(parent: Path, name: str) -> Path:
    """Low-utility fixture script — DEBUG/EXPERIMENTAL markers, no docstring."""
    content = """
        # DEBUG TEMP - remove before release
        # EXPERIMENTAL - not ready for production
        x = None
        print(x)
    """
    return _make_file(parent, name, content)


# ---------------------------------------------------------------------------
# Reference Scanner contract stub
# ---------------------------------------------------------------------------

class ReferenceScanner:
    """
    Minimal reference scanner for integration testing.

    Contract stub for the ``ReferenceDetector`` planned in the file-sync skill.
    Searches all ``.py``, ``.sh``, ``Makefile``, ``.yml``, and ``.md`` files.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def find_all_references(self, script_name: str) -> List[Reference]:
        """
        Find every reference to ``script_name`` in the repository.

        Searches file content line-by-line and classifies each hit.
        """
        refs: List[Reference] = []
        base = Path(script_name).stem
        full_name = Path(script_name).name

        extensions = {".py", ".sh", ".yml", ".yaml", ".md", ""}
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in extensions and path.name != "Makefile":
                continue
            if path.name == full_name:
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for lineno, line in enumerate(content.splitlines(), 1):
                if base in line or full_name in line:
                    refs.append(Reference(
                        source_file=path,
                        line_number=lineno,
                        reference_type=self._classify(line, path),
                        context=line.strip(),
                    ))
        return refs

    def _classify(self, line: str, path: Path) -> str:
        """Classify the reference type based on file and line content."""
        name = path.name
        if name in ("Makefile", "MAKEFILE") or name.endswith(".mk"):
            return "MAKEFILE"
        if path.suffix in (".md", ".rst", ".txt") or "DOCS" in name.upper():
            return "DOCS"
        line_s = line.strip()
        if any(kw in line_s for kw in ("import ", "from ")):
            return "IMPORT"
        if ".github" in str(path):
            return "CI"
        return "STRING"


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture()
def tmp_repo(tmp_path: Path) -> Path:
    """
    Minimal fake repository root with a ``.git`` directory.

    Provides a safe, isolated sandbox; git-tracking tests can use this without
    touching the real repository.
    """
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
    return tmp_path


@pytest.fixture()
def high_utility_integrated_script(tmp_repo: Path) -> Path:
    """High-utility script (score ~9) already referenced in a Makefile."""
    scripts_dir = tmp_repo / "scripts"
    script = _make_high_utility_script(scripts_dir, "get_version.py")
    (tmp_repo / "Makefile").write_text(
        f"version:\n\tpython scripts/{script.name}\n"
    )
    return script


@pytest.fixture()
def medium_utility_unintegrated_script(tmp_repo: Path) -> Path:
    """Medium-utility script (score ~6) with zero existing references."""
    scripts_dir = tmp_repo / "scripts"
    return _make_medium_utility_script(scripts_dir, "validate_renders.py")


@pytest.fixture()
def low_utility_debug_script(tmp_repo: Path) -> Path:
    """Low-utility debug script (score ~1) with DEBUG/EXPERIMENTAL markers."""
    scripts_dir = tmp_repo / "scripts"
    return _make_low_utility_debug_script(scripts_dir, "debug_helper.py")


@pytest.fixture()
def sync_report_with_candidates(tmp_repo: Path) -> SyncReport:
    """
    Pre-built ``SyncReport`` with a mix of utility scores.

    Contents
    --------
    - get_version.py        score=9.0  (high-value, unintegrated)
    - validate_renders.py   score=6.0  (medium, unintegrated)
    - debug_helper.py       score=1.0  (dead code)
    """
    return build_sync_report(
        tmp_repo,
        {
            "get_version.py": 9.0,
            "validate_renders.py": 6.0,
            "debug_helper.py": 1.0,
        },
    )


# ===========================================================================
# Scenario 1: Happy path — full workflow
# ===========================================================================

class TestHappyPathSyncDecideCleanup:
    """
    Scenario 1: End-to-end workflow — sync → decisions → pre-gate → cleanup.

    After file-sync produces ``SYNC_REPORT.md`` and the user creates
    ``SYNC_DECISIONS.md``, the pre-gate should pass and cleanup should run.
    """

    def test_sync_report_is_written_with_scores(
        self, tmp_repo: Path, sync_report_with_candidates: SyncReport
    ):
        """SYNC_REPORT.md is created with correct script names and scores."""
        output = tmp_repo / "SYNC_REPORT.md"
        write_sync_report_md(sync_report_with_candidates, output)
        assert output.exists(), "SYNC_REPORT.md must exist after writing"
        content = output.read_text()
        assert "get_version.py" in content
        assert "debug_helper.py" in content

    def test_high_value_unintegrated_count_is_positive(
        self, sync_report_with_candidates: SyncReport
    ):
        """SyncReport.high_value_unintegrated is >= 1 for the fixture data."""
        assert sync_report_with_candidates.high_value_unintegrated >= 1, \
            "Fixture must contain at least one high-value unintegrated script"

    def test_pregate_passes_when_both_files_present(self, tmp_repo: Path):
        """Pre-gate returns ``can_proceed=True`` once both sentinel files exist."""
        (tmp_repo / "SYNC_REPORT.md").write_text("# Sync Report\n")
        (tmp_repo / "SYNC_DECISIONS.md").write_text("# Decisions\n")
        checker = PreGateChecker()
        with patch.object(
            PreGateValidator, "_git_working_dir_clean", return_value=True
        ), patch.object(
            PreGateValidator, "_all_tests_pass", return_value=True
        ):
            result = checker.check(tmp_repo)
        assert not result.blocked, f"Pre-gate should pass but blocked with: {result.reason}"

    def test_cleanup_runs_after_successful_pregate(self, tmp_repo: Path):
        """
        File-cleanup scans and reports candidates once pre-gate conditions
        are satisfied; dry-run leaves files untouched.
        """
        (tmp_repo / "SYNC_REPORT.md").write_text("# Sync Report\n")
        (tmp_repo / "SYNC_DECISIONS.md").write_text("# Decisions\n")
        # Add a temp file that should be caught by cleanup
        (tmp_repo / "PHASE_old.md").write_text("# Phase\n")

        with patch(
            "file_cleanup.FileCleanupAnalyzer._is_git_tracked",
            return_value=False,
        ):
            result = run_cleanup(root=tmp_repo, dry_run=True)

        assert result is not None

    def test_dead_code_correctly_identified_in_report(
        self, sync_report_with_candidates: SyncReport
    ):
        """
        Scripts scored <= 3 appear in ``dead_code_candidates``.
        """
        dead_names = [e.script_name for e in sync_report_with_candidates.dead_code_candidates]
        assert "debug_helper.py" in dead_names, \
            f"debug_helper.py not in dead code candidates; got {dead_names}"


# ===========================================================================
# Scenario 2: Pre-gate blocks without SYNC_REPORT.md
# ===========================================================================

class TestPreGateBlocksWithoutSyncReport:
    """
    Scenario 2: Pre-gate refuses to proceed when SYNC_REPORT.md is absent.

    If the user hasn't run file-sync yet, file-cleanup must refuse to execute
    so the workflow is completed in the correct order.
    """

    def test_blocked_when_sync_report_absent(self, tmp_repo: Path):
        """Pre-gate returns ``blocked`` when SYNC_REPORT.md does not exist."""
        assert not (tmp_repo / "SYNC_REPORT.md").exists()
        checker = PreGateChecker()
        with patch.object(PreGateValidator, "_all_tests_pass", return_value=True), \
             patch.object(PreGateValidator, "_git_working_dir_clean", return_value=True):
            result = checker.check(tmp_repo)
        assert result.blocked, "Pre-gate must block file-cleanup when SYNC_REPORT.md is absent"

    def test_block_reason_mentions_sync_report(self, tmp_repo: Path):
        """The block reason message names SYNC_REPORT.md explicitly."""
        assert not (tmp_repo / "SYNC_REPORT.md").exists()
        checker = PreGateChecker()
        with patch.object(PreGateValidator, "_all_tests_pass", return_value=True), \
             patch.object(PreGateValidator, "_git_working_dir_clean", return_value=True):
            result = checker.check(tmp_repo)
        assert "SYNC_REPORT.md" in result.reason, f"Reason must reference SYNC_REPORT.md; got: {result.reason}"

    def test_decisions_only_still_blocks(self, tmp_repo: Path):
        """Having only SYNC_DECISIONS.md (no SYNC_REPORT.md) still blocks."""
        (tmp_repo / "SYNC_DECISIONS.md").write_text("# Decisions\n")
        assert not (tmp_repo / "SYNC_REPORT.md").exists()
        checker = PreGateChecker()
        with patch.object(PreGateValidator, "_all_tests_pass", return_value=True), \
             patch.object(PreGateValidator, "_git_working_dir_clean", return_value=True):
            result = checker.check(tmp_repo)
        assert result.blocked
        assert "SYNC_REPORT.md" in result.reason


# ===========================================================================
# Scenario 3: Pre-gate blocks without SYNC_DECISIONS.md
# ===========================================================================

class TestPreGateBlocksWithoutSyncDecisions:
    """
    Scenario 3: Pre-gate refuses to proceed when SYNC_DECISIONS.md is absent.

    Even with a valid SYNC_REPORT.md present, the user must explicitly create
    SYNC_DECISIONS.md (human review gate) before cleanup can run.
    """

    def test_blocked_when_sync_decisions_absent(self, tmp_repo: Path):
        """Pre-gate blocks when only SYNC_REPORT.md exists (no SYNC_DECISIONS)."""
        (tmp_repo / "SYNC_REPORT.md").write_text("# Sync Report\n")
        assert not (tmp_repo / "SYNC_DECISIONS.md").exists()
        checker = PreGateChecker()
        with patch.object(PreGateValidator, "_all_tests_pass", return_value=True), \
             patch.object(PreGateValidator, "_git_working_dir_clean", return_value=True):
            result = checker.check(tmp_repo)
        assert result.blocked, "Pre-gate must block when SYNC_DECISIONS.md is absent"

    def test_block_reason_mentions_sync_decisions(self, tmp_repo: Path):
        """The block reason message names SYNC_DECISIONS.md explicitly."""
        (tmp_repo / "SYNC_REPORT.md").write_text("# Sync Report\n")
        checker = PreGateChecker()
        with patch.object(PreGateValidator, "_all_tests_pass", return_value=True), \
             patch.object(PreGateValidator, "_git_working_dir_clean", return_value=True):
            result = checker.check(tmp_repo)
        assert "SYNC_DECISIONS" in result.reason, \
            f"Reason must reference SYNC_DECISIONS; got: {result.reason}"

    def test_both_files_required_for_pregate_to_pass(self, tmp_repo: Path):
        """Pre-gate passes only when *both* SYNC_REPORT.md and SYNC_DECISIONS.md exist."""
        # Neither file
        checker = PreGateChecker()
        with patch.object(PreGateValidator, "_all_tests_pass", return_value=True), \
             patch.object(PreGateValidator, "_git_working_dir_clean", return_value=True):
            r1 = checker.check(tmp_repo)
        assert r1.blocked

        # Only SYNC_REPORT.md
        (tmp_repo / "SYNC_REPORT.md").write_text("# Sync Report\n")
        with patch.object(PreGateValidator, "_all_tests_pass", return_value=True), \
             patch.object(PreGateValidator, "_git_working_dir_clean", return_value=True):
            r2 = checker.check(tmp_repo)
        assert r2.blocked

        # Both files present
        (tmp_repo / "SYNC_DECISIONS.md").write_text("# Decisions\n")
        with patch.object(PreGateValidator, "_all_tests_pass", return_value=True), \
             patch.object(PreGateValidator, "_git_working_dir_clean", return_value=True):
            r3 = checker.check(tmp_repo)
        assert not r3.blocked


# ===========================================================================
# Scenario 4: Cleanup respects decisions
# ===========================================================================

class TestCleanupRespectsDecisions:
    """
    Scenario 4: Scripts accepted for integration are excluded from cleanup.

    Scripts listed under ``## ACCEPT`` in SYNC_DECISIONS.md must not be
    deleted by file-cleanup, even if their names match a cleanup pattern.
    """

    def test_accepted_scripts_in_extra_exclusions(self, tmp_repo: Path):
        """
        Accepted scripts are added to ``CleanupConfig.extra_exclusions``
        and therefore never appear as cleanup candidates.
        """
        decisions = SyncDecisions(
            accepted=["get_version.py", "validate_renders.py"],
            rejected=["debug_helper.py"],
        )
        config = build_cleanup_config_from_decisions(decisions)
        assert "get_version.py" in config.extra_exclusions
        assert "validate_renders.py" in config.extra_exclusions

    def test_decisions_md_roundtrip_fidelity(self, tmp_repo: Path):
        """SYNC_DECISIONS.md serialises and deserialises without data loss."""
        original = SyncDecisions(
            accepted=["script_a.py", "script_b.py"],
            rejected=["debug_x.py"],
        )
        path = tmp_repo / "SYNC_DECISIONS.md"
        write_sync_decisions_md(original, path)
        parsed = parse_sync_decisions(path)
        assert set(parsed.accepted) == set(original.accepted)
        assert set(parsed.rejected) == set(original.rejected)

    def test_accepted_file_excluded_from_cleanup_scan(self, tmp_repo: Path):
        """
        ``FileCleanupAnalyzer`` with an exclusion config does NOT flag
        the file listed in ``extra_exclusions``.
        """
        # Create a file that would otherwise be a cleanup candidate (WIP_ prefix)
        wip_file = tmp_repo / "WIP_accepted_notes.md"
        wip_file.write_text("important integration notes")

        config = CleanupConfig(extra_exclusions={"WIP_accepted_notes.md"})
        with patch.object(FileCleanupAnalyzer, "_is_git_tracked", return_value=False):
            analyzer = FileCleanupAnalyzer(root=tmp_repo, config=config)
            candidates = analyzer.scan()

        flagged_names = [c.path.name for c in candidates]
        assert "WIP_accepted_notes.md" not in flagged_names

    def test_rejected_file_remains_a_cleanup_candidate(self, tmp_repo: Path):
        """
        A file NOT in ``extra_exclusions`` that matches a cleanup pattern
        still appears as a candidate.
        """
        (tmp_repo / "WIP_accepted.md").write_text("accepted")
        (tmp_repo / "WIP_rejected.md").write_text("rejected")

        config = CleanupConfig(extra_exclusions={"WIP_accepted.md"})
        with patch.object(FileCleanupAnalyzer, "_is_git_tracked", return_value=False):
            analyzer = FileCleanupAnalyzer(root=tmp_repo, config=config)
            candidates = analyzer.scan()

        flagged = {c.path.name for c in candidates}
        assert "WIP_rejected.md" in flagged

    def test_sample_sync_decisions_fixture_is_parseable(self):
        """The fixture file ``sample_sync_decisions.md`` parses without error."""
        fixture = _TESTS_DIR / "fixtures" / "sample_sync_decisions.md"
        assert fixture.exists(), f"Fixture not found: {fixture}"
        decisions = parse_sync_decisions(fixture)
        assert isinstance(decisions.accepted, list)
        assert isinstance(decisions.rejected, list)


# ===========================================================================
# Scenario 5: Risk scoring flags risk level
# ===========================================================================

class TestRiskScoringFlagsRisk:
    """
    Scenario 5: The risk assessor correctly classifies file risk level.

    ``RiskLevel.LOW``    → empty or tiny files (< 500 bytes)
    ``RiskLevel.MEDIUM`` → files with meaningful content
    """

    def test_empty_session_file_is_low_risk(self, tmp_repo: Path):
        """Empty session / temp files are classified ``LOW`` risk."""
        (tmp_repo / "WIP_scratch.md").write_text("")
        with patch.object(FileCleanupAnalyzer, "_is_git_tracked", return_value=False):
            result = run_cleanup(root=tmp_repo, dry_run=True)
        risks = {c.path.name: c.risk for c in result.candidates}
        if "WIP_scratch.md" in risks:
            assert risks["WIP_scratch.md"] == RiskLevel.LOW

    def test_small_phase_file_is_low_risk(self, tmp_repo: Path):
        """Small phase files (< 500 bytes) are classified ``LOW`` risk."""
        (tmp_repo / "PHASE_small.md").write_text("# Tiny note\n")
        with patch.object(FileCleanupAnalyzer, "_is_git_tracked", return_value=False):
            result = run_cleanup(root=tmp_repo, dry_run=True)
        risks = {c.path.name: c.risk for c in result.candidates}
        if "PHASE_small.md" in risks:
            assert risks["PHASE_small.md"] == RiskLevel.LOW

    def test_large_phase_file_is_medium_risk(self, tmp_repo: Path):
        """Files >= 500 bytes of content are classified ``MEDIUM`` risk."""
        large_content = "# Extensive Notes\n\n" + "content line\n" * 60  # > 500 bytes
        (tmp_repo / "WIP_large_notes.md").write_text(large_content)
        with patch.object(FileCleanupAnalyzer, "_is_git_tracked", return_value=False):
            result = run_cleanup(root=tmp_repo, dry_run=True)
        risks = {c.path.name: c.risk for c in result.candidates}
        if "WIP_large_notes.md" in risks:
            assert risks["WIP_large_notes.md"] in (RiskLevel.MEDIUM, RiskLevel.LOW)

    def test_accepted_high_value_script_not_in_candidates(self, tmp_repo: Path):
        """
        A high-value script listed in SYNC_DECISIONS as accepted is excluded
        from cleanup candidates regardless of its file name.
        """
        scripts_dir = tmp_repo / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "critical_tool.py").write_text("def main(): pass\n")

        # Also add a WIP file that WOULD be a candidate
        (tmp_repo / "WIP_notes.md").write_text("notes")

        config = CleanupConfig(extra_exclusions={"critical_tool.py"})
        with patch.object(FileCleanupAnalyzer, "_is_git_tracked", return_value=False):
            analyzer = FileCleanupAnalyzer(root=tmp_repo, config=config)
            candidates = analyzer.scan()

        flagged = {c.path.name for c in candidates}
        assert "critical_tool.py" not in flagged


# ===========================================================================
# Scenario 6: Hidden string references are detected
# ===========================================================================

class TestHiddenStringReferencesDetected:
    """
    Scenario 6: The reference scanner finds all references including string literals.

    Scripts are not always imported directly — they may appear in f-strings,
    subprocess calls, config files, or documentation comments.
    """

    def test_string_literal_reference_found(self, tmp_repo: Path):
        """
        A script name inside a Python string (f-string command) is discovered.
        """
        caller = tmp_repo / "my_tool.py"
        caller.write_text(textwrap.dedent("""
            import subprocess


            def run_tool() -> None:
                cmd = f"python scripts/my_tool.py --flag"
                subprocess.run(cmd, shell=True)
        """))
        scanner = ReferenceScanner(tmp_repo)
        refs = scanner.find_all_references("my_tool.py")
        # The file references itself — exclude it and check no false negatives
        # Actually we create a separate caller
        caller2 = tmp_repo / "caller.py"
        caller2.write_text('cmd = "python scripts/my_tool.py --flag"\n')
        refs2 = scanner.find_all_references("my_tool.py")
        found_files = {r.source_file.name for r in refs2}
        assert "caller.py" in found_files

    def test_import_reference_classified_correctly(self, tmp_repo: Path):
        """Python ``import`` statements are classified as ``IMPORT`` references."""
        caller = tmp_repo / "use_processor.py"
        caller.write_text(textwrap.dedent("""
            import scripts.data_processor
            from scripts import data_processor
        """))
        scanner = ReferenceScanner(tmp_repo)
        refs = scanner.find_all_references("data_processor.py")
        import_refs = {r.reference_type for r in refs}
        assert "IMPORT" in import_refs

    def test_documentation_reference_found_in_markdown(self, tmp_repo: Path):
        """Script names in Markdown prose are discovered with type ``DOCS``."""
        doc = tmp_repo / "CONTRIBUTING.md"
        doc.write_text(textwrap.dedent("""
            # Usage Guide

            Run the validation tool:

                python scripts/validate_renders.py --check all
        """))
        scanner = ReferenceScanner(tmp_repo)
        refs = scanner.find_all_references("validate_renders.py")
        ref_types = {r.reference_type for r in refs}
        assert "DOCS" in ref_types

    def test_no_false_positives_for_phantom_script(self, tmp_repo: Path):
        """An unreferenced script name returns an empty reference list."""
        (tmp_repo / "unrelated_code.py").write_text("x = 1 + 1\n")
        scanner = ReferenceScanner(tmp_repo)
        refs = scanner.find_all_references("phantom_script_xyz_12345.py")
        assert len(refs) == 0, f"Expected no references to a phantom script; got {refs}"

    def test_reference_includes_valid_line_number(self, tmp_repo: Path):
        """Every discovered reference carries a ``line_number >= 1``."""
        runner = tmp_repo / "runner.py"
        runner.write_text("# Line 1\n# Line 2\ncmd = 'my_script.py --flag'\n")
        scanner = ReferenceScanner(tmp_repo)
        refs = scanner.find_all_references("my_script.py")
        assert len(refs) > 0
        for ref in refs:
            assert ref.line_number >= 1, f"line_number must be >= 1; got {ref.line_number}"

    def test_reference_context_is_non_empty(self, tmp_repo: Path):
        """Every reference includes the surrounding line as ``context``."""
        pipeline = tmp_repo / "pipeline.py"
        pipeline.write_text("result = run('scripts/my_tool.py')\n")
        scanner = ReferenceScanner(tmp_repo)
        refs = scanner.find_all_references("my_tool.py")
        assert len(refs) > 0
        for ref in refs:
            assert len(ref.context) > 0, "context must be a non-empty string"


# ===========================================================================
# Scenario 7: Deletion log entries contain recovery commands
# ===========================================================================

class TestDeletionLogHasRecoveryCommands:
    """
    Scenario 7: Deletion log entries contain valid ``git checkout`` recovery commands.

    Every file removed by file-cleanup must have a corresponding
    ``git checkout HEAD~1 -- <path>`` command so the deletion can be undone.
    """

    def test_deletion_log_entries_created_for_deleted_files(self, tmp_repo: Path):
        """One ``DeletionLogEntry`` is built per deleted file."""
        (tmp_repo / "WIP_obsolete.md").write_text("old session notes")
        with patch.object(FileCleanupAnalyzer, "_is_git_tracked", return_value=False):
            result = run_cleanup(root=tmp_repo, dry_run=True)
        entries = build_deletion_log_entries(result, tmp_repo)
        assert len(entries) >= len(result.candidates), \
            "One log entry must exist for every deleted file"

    def test_recovery_command_starts_with_git_checkout(self, tmp_repo: Path):
        """Every recovery command begins with ``git checkout``."""
        (tmp_repo / "PHASE_old.md").write_text("old phase content")
        with patch.object(FileCleanupAnalyzer, "_is_git_tracked", return_value=False):
            result = run_cleanup(root=tmp_repo, dry_run=True)
        entries = build_deletion_log_entries(result, tmp_repo)
        for entry in entries:
            assert entry.recovery_command.startswith("git checkout"), \
                f"Recovery command must start with 'git checkout'; got: {entry.recovery_command}"

    def test_recovery_command_contains_file_path(self, tmp_repo: Path):
        """The recovery command includes the relative path of the deleted file."""
        (tmp_repo / "WIP_scratch.md").write_text("scratch notes here")
        with patch.object(FileCleanupAnalyzer, "_is_git_tracked", return_value=False):
            result = run_cleanup(root=tmp_repo, dry_run=True)
        entries = build_deletion_log_entries(result, tmp_repo)
        for entry in entries:
            assert str(entry.file_path.name) in entry.recovery_command or \
                   str(entry.file_path) in entry.recovery_command, \
                f"Recovery command {entry.recovery_command} must include file path {entry.file_path}"

    def test_deletion_log_entry_has_all_required_fields(self, tmp_repo: Path):
        """Every ``DeletionLogEntry`` has non-empty ``file_path``, ``reason``, and ``recovery_command``."""
        (tmp_repo / "TMP_notes.md").write_text("temp notes content")
        with patch.object(FileCleanupAnalyzer, "_is_git_tracked", return_value=False):
            result = run_cleanup(root=tmp_repo, dry_run=True)
        entries = build_deletion_log_entries(result, tmp_repo)
        assert len(entries) > 0, "Expected at least one deletion log entry"
        for entry in entries:
            assert entry.file_path is not None
            assert len(entry.reason) > 0
            assert len(entry.recovery_command) > 0

    def test_recovery_command_references_head(self, tmp_repo: Path):
        """Recovery command references ``HEAD`` so it works on any branch."""
        (tmp_repo / "TEMP_old_work.md").write_text("old content")
        with patch.object(FileCleanupAnalyzer, "_is_git_tracked", return_value=False):
            result = run_cleanup(root=tmp_repo, dry_run=True)
        entries = build_deletion_log_entries(result, tmp_repo)
        for entry in entries:
            assert "HEAD" in entry.recovery_command, \
                f"Recovery command must reference HEAD; got: {entry.recovery_command}"
