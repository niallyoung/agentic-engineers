---
name: file-sync
description: >
  Discovers and analyzes scripts in the repository, scoring them for utility
  and integration. Produces SYNC_REPORT.md with recommendations for integration,
  archival, or deletion of each script.
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: hygiene
  role: senior-engineer
  model: haiku-4-5
  effort: medium
  trigger: on-demand | pre-cleanup
  tdd_phase: GREEN  # All 41 tests passing
---

## Overview

**file-sync** analyzes all scripts in the repository and generates a
`SYNC_REPORT.md` that categorizes each script by value and integration status.

| Category | Meaning |
|----------|---------|
| HIGH_VALUE + unintegrated | Should be integrated (Makefile, CI, docs, imports) |
| HIGH_VALUE + integrated | Well-maintained — leave alone |
| MEDIUM + unintegrated | Optional — consider integrating or documenting |
| DEAD | Debug/temp code — clean up |

### Utility Score (0–10)

| Signal | Weight |
|--------|--------|
| Quality (docstring, type hints, error handling) | ~3 pts |
| Maturity (naming, LOC, no dev-markers) | ~3 pts |
| Relevance (CONTRIBUTING.md mention, core domain) | ~2.5 pts |
| Dependencies (minimal deps preferred) | ~1.5 pts |

### Integration Detection

Searches for references to each script in:
- `Makefile` targets
- `.github/workflows/` CI files
- Python `import` statements
- `*.md` documentation

## Invocation

```bash
python scripts/file_sync.py [--root <dir>] [--output <path>]
```

Output: `SYNC_REPORT.md` in the repository root.
