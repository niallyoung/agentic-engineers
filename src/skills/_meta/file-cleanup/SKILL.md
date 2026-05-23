---
name: file-cleanup
description: >
  Identifies and removes unnecessary files before they accidentally end up in
  commits. Detects session/temp files, debug logs, coverage artefacts, and
  test-result directories. Respects git tracking — never deletes indexed files.
  Supports dry-run, analysis-only, and execute modes.
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: hygiene
  role: senior-engineer
  trigger: pre-commit | on-demand | CI
  tdd_phase: GREEN  # All 60 tests passing
---

## Overview

**file-cleanup** enforces repository hygiene by automatically identifying and
optionally removing files that should never enter a commit:

| Category | Examples |
|----------|---------|
| Session / Temp | `PHASE_*.md`, `WIP_*.md`, `TEMP_*.md`, `.*.swp` |
| Debug / Log | Progress-marker-only files, `[DEBUG]`/`[LOG]` header files, `*_2026_*.md` |
| Coverage Artefacts | `*.coverage`, `.coverage.*`, `htmlcov/` outside `docs/` |
| Testing Results | `testing-results/` directory |

### Safety Guarantees

1. **Git-tracked files are never touched** — `git ls-files --error-unmatch`
   is consulted before any deletion.
2. **Protected names** (`README.md`, `TODO.md`, `SPEC.md`, `CHANGELOG.md`,
   `LICENSE`, `Makefile`, `setup.py`, `pytest.ini` …) are hardcoded as safe.
3. **Protected directories** (`src/`, `tests/`, `docs/`, `.git/`) are
   never scanned.
4. HTML coverage reports inside `docs/` are preserved.

## Invocation

### Dry Run (default — safe to run anywhere)
```bash
python -m src.skills._meta.file_cleanup.scripts.file_cleanup --dry-run
# or from the skill directory:
python scripts/file_cleanup.py --dry-run
```

### Analysis Only (structured report, no changes)
```bash
python scripts/file_cleanup.py --analysis-only
```

### Execute (irreversible — prompts for confirmation)
```bash
python scripts/file_cleanup.py --execute
```

All modes accept an optional `--root <dir>` to scan a directory other than CWD.

## Python API

```python
from src.skills._meta.file_cleanup.scripts.file_cleanup import (
    FileCleanupAnalyzer, CleanupConfig, run_cleanup,
    CleanupCategory, RiskLevel,
)

# Scan only — returns List[CleanupCandidate]
analyzer = FileCleanupAnalyzer(root=Path("."), dry_run=True)
candidates = analyzer.scan()
for c in candidates:
    print(f"[{c.risk.value}] {c.path}  — {c.reason}")

# Full dry-run execution — returns CleanupResult
result = run_cleanup(root=Path("."), dry_run=True)
print(result.summary)   # {CleanupCategory.SESSION_TEMP: 3, ...}
print(result.deleted)   # [] in dry-run

# Config consolidation report
report = analyzer.config_consolidation_report()
for keeper, dup in report.duplicates:
    print(f"Duplicate: {dup}  (same content as {keeper})")

# Custom patterns / exclusions
cfg = CleanupConfig(
    extra_patterns=["MY_SCRATCH_*.md"],
    extra_exclusions=["WIP_keep_forever.md"],
)
result = run_cleanup(root=Path("."), dry_run=True, config=cfg)
```

## Architecture

```
file_cleanup.py
├── CleanupCategory (Enum)       — session_temp | debug_log | coverage_report | testing_results | custom
├── RiskLevel (Enum)             — low | medium | high
├── CleanupCandidate (dataclass) — path, category, risk, reason, git_tracked
├── CleanupResult (dataclass)    — candidates, deleted, summary
├── ConfigConsolidationReport    — duplicates, recommendation
├── CleanupConfig                — pattern lists + exclusions (user-extensible)
└── FileCleanupAnalyzer
    ├── scan()                   — walk tree, evaluate each item, return candidates
    ├── execute()                — scan + optionally delete; respects dry_run/analysis_only
    ├── config_consolidation_report() — MD5-based duplicate config detection
    ├── _walk() / _walk_dir()    — recursive walk skipping protected dirs
    ├── _check_file()            — pattern + content analysis per file
    ├── _check_directory()       — whole-directory candidates (testing-results, htmlcov)
    ├── _check_debug_content()   — content-based debug/progress log detection
    ├── _is_git_tracked()        — subprocess git ls-files integration
    ├── _assess_file_risk()      — LOW/MEDIUM based on file size
    └── _delete()                — unlink file or shutil.rmtree directory
```

## Test Coverage

```
60 tests — 13 test classes:

TestPhaseFilesDetection          (3)  PHASE_*.md, PHASE-*.md patterns
TestSessionTempFilesDetection    (7)  WIP_*, TEMP_*, TMP_*, SESSION, .swp/.swo
TestDebugLogFilesDetection       (4)  progress markers, [DEBUG] headers, timestamps
TestCoverageReportDetection      (5)  *.coverage, .coverage.*, htmlcov/
TestTestingResultsDetection      (2)  testing-results/ directory
TestPreservationOfRealDocs      (12)  README/TODO/SPEC/src/tests/.git protection
TestGitIntegration               (3)  tracked exclusion, untracked inclusion
TestDryRunMode                   (3)  list candidates, no deletion
TestAnalysisOnlyMode             (3)  structured report, no deletion
TestConfigConsolidation          (3)  MD5 duplicate detection, recommendation
TestRiskAssessment               (4)  LOW/MEDIUM per size, reason strings
TestExecuteMode                  (3)  delete file, skip tracked, list deleted
TestCleanupConfig                (2)  custom patterns, custom exclusions
TestRunCleanupEntrypoint         (3)  dry-run / analysis / execute via run_cleanup()
```

## Constraints

- Does **not** auto-move files — relocation is always manual.
- Does **not** run without explicit mode flag (no accidental execution).
- Does **not** touch files under `src/`, `tests/`, `docs/`, `.git/`.
- Does **not** delete git-tracked files under any circumstances.
- Python 3.7+ compatible; no third-party dependencies.

## SPAN Capture

After each run, capture a SPAN with:
- `candidates_found`: total cleanup candidates identified
- `candidates_deleted`: files actually deleted (0 in dry-run/analysis-only)
- `categories`: dict of category → count
- `mode`: dry-run | analysis-only | execute
- `git_tracked_skipped`: count of candidates excluded due to git tracking
