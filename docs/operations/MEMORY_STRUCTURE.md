# Memory Structure — Project Memory Organization

This document explains how Claude's memory system is used in the ERS project ecosystem.

---

## Memory Location & Structure

### ERS Project Memory (Primary)

**Location:** `~/.claude/projects/-Us{service-name}/memory/`

This is the active memory for the ERS platform work. Per Claude's memory system design, project memories live in this location (not duplicated elsewhere).

**Contains:**

| File | Type | Purpose | Updated |
|------|------|---------|---------|
| `MEMORY.md` | Index | Consolidated memory index + key facts | 2026-04-24 |
| `feedback_no_coauthor.md` | feedback | Never add Co-Authored-By trailers to commits | 2026-03-12 |
| `feedback_no_no_verify.md` | feedback | Hard rule: never pass --no-verify to git | 2026-04-18 |
| `feedback_local_first.md` | feedback | Prefer local-first development patterns | 2026-03-12 |
| `feedback_voice_volume.md` | feedback | Prefix `say` commands with `[[volm 0.7]]` | 2026-04-17 |
| `project_not_live.md` | project | ERS not yet live in production (pre-launch) | 2026-03-14 |
| `project_ers_code_dash.md` | project | {service-name} is local Go TUI dashboard | 2026-04-15 |

### Why NOT Consolidated into agentic-engineers/

Claude's memory system expects project memories to live in `~/.claude/projects/<project>/memory/`. Moving them to `agentic-engineers/` breaks the memory system's ability to automatically load project context.

**Safe to reference** from agentic-engineers (as this document does), but NOT safe to move.

---

## Loading Project Memory

When starting work on the ERS project:

1. Claude automatically loads `~/.claude/projects/-Us{service-name}/memory/MEMORY.md`
2. Specific feedback/project memories are recalled as relevant to the task
3. This provides persistent context across sessions

**Do not move these files.** The memory system relies on this location.

---

## Adding New Memories

When you want to save knowledge for future ERS project sessions:

Use the `mcp__openbrain__capture_thought` tool (or equivalent memory system) to save to `~/.claude/projects/-Us{service-name}/memory/`.

Examples:
- Feedback on what worked / what didn't: `feedback_*.md`
- Project context (status, decisions, constraints): `project_*.md`
- Lessons learned from sessions: Add to `MEMORY.md`

---

## Other Project Memories

Similar structure exists for other projects under `~/.claude/projects/`:

- `-Us{service-name}/memory/` — AWS org project
- `-Us{service-name}/memory/` — Azure project
- `-Us{service-name}/memory/` — ERS app subproject
- etc.

Each maintains its own memory separate from the main ERS memory.

---

## Related Files

- `../COMPLETED_PLANS.md` — Completed work and lessons learned
- `../METRICS.md` — Metrics schema and collection
- `agentic-engineers/guides/` — Current operational guides
- ERS platform CLAUDE.md — Root project instructions

---

## Summary

✅ **Project memory is properly distributed:**
- ~/.claude/projects/ — Persistent context (DO NOT MOVE)
- agentic-engineers/ — Operational documentation (reference only)
- ERS repos — Code + CLAUDE.md instructions

This design ensures memory persistence, automation, and discoverability.
