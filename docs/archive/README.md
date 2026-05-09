# Documentation Archive

This directory contains archived documentation, session deliverables, and historical artifacts from the agentic-engineers project.

## Purpose

Files are archived when they:
- Document completed analysis or decisions that have been implemented
- Are session deliverables that served their purpose but are no longer actively maintained
- Contain outdated information superseded by newer documentation
- Are kept for historical reference but should not be the primary source

## Directory Structure

### `sessions/`
**Session deliverables and audit artifacts**

Contains summaries, audit reports, and analysis from specific engineering sessions:
- `AUDIT-FINAL-SUMMARY.md` — Comprehensive audit report from May 2025
- `AUDIT-RENDERING-PIPELINE.md` — Technical analysis of rendering pipeline  
- `STRUCTURE-RECOMMENDATION.md` — Proposed repository structure optimizations
- `CONSOLIDATION-ROADMAP.md` — Plan for documentation consolidation (this initiative)

**When to use:** Historical reference only. For current information, see `docs/` root and `docs/decisions/`.

### `phase5/` and `phase6-draft/`
**Phase implementation history**

Contains documentation from specific development phases. See `docs/PHASE-*.md` for current phase documentation.

### `legacy/`
**Superseded architecture and old guides**

Contains old implementation guides and architecture docs that have been superseded. Used only for historical context.

## Retrieving Archived Content

### Search within archive:
```bash
grep -r "search_term" docs/archive/
```

### View a specific archived file:
```bash
cat docs/archive/sessions/AUDIT-FINAL-SUMMARY.md
```

### Understanding what was archived and why:
This consolidation was performed to reduce root-level clutter and organize documentation by relevance:
- **Audit deliverables** archived because analysis was completed and implemented
- **Structure docs** archived in `docs/decisions/` as ADRs (Architecture Decision Records)
- **Planning docs** retained in `docs/` for ongoing reference

## Adding Content to Archive

When archiving new content:
1. Move files to appropriate subdirectory (`sessions/`, `phase5/`, `phase6-draft/`, `legacy/`)
2. Update this README.md with brief description
3. Commit with clear message: `archive: Move [filename] to archive/[subdirectory]`

## Current Tracking Effort

Total tracked markdown files: ~150 (target: <150)

Repository structure goals:
- ✅ Root: ≤4 .md files (README.md, TODO.md + essential docs only)
- ✅ `docs/`: Well-organized documentation with clear structure
- ✅ `docs/archive/`: All historical artifacts properly categorized
- ✅ All internal links updated to point to new locations
