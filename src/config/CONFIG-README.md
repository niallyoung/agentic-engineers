# Configuration — System Setup & Locked Assignments

**This directory contains the immutable configuration for the agentic-engineers system.**

## Files

| File | Purpose |
|------|---------|
| **MODEL_ASSIGNMENTS_LOCKED.md** | Complete reference for model/effort/thinking assignments, progression hierarchy, optimization algorithm. READ THIS FIRST. |
| **QUICK_REFERENCE.md** | 1-page cheat sheet for routing decisions and escalation rules. Print this! |

## Key Configuration (DO NOT CHANGE)

- **8 roles** with fixed model assignments (Haiku 4.5, Sonnet 4.5/4.6, Opus 4.6/4.7)
- **Model progression:** Haiku → Sonnet 4.5 → Sonnet 4.6 → Opus 4.6 → Opus 4.7
- **Optimization metric:** Cost first, quality-gated (min = best_quality - 5 points)
- **Tunable parameters:** Effort (low/medium/high/max), Thinking (yes/no)

## When You Need This

- **Setting up the system?** Read MODEL_ASSIGNMENTS_LOCKED.md
- **During task routing?** Use QUICK_REFERENCE.md
- **Troubleshooting assignments?** Check MODEL_ASSIGNMENTS_LOCKED.md examples
- **Optimizing models?** Model Engineer walks the progression in MODEL_ASSIGNMENTS_LOCKED.md

## See Also

- `../MANIFEST.md` — Complete file listing of entire system (discovery tool)
- `../orchestration/AGENTS.md` — Role definitions & routing rules
- `../guides/CLAUDE.md` — Team context & integration
