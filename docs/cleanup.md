# Cleanup Skill

**Agent Role**: Engineer  
**Model**: claude-haiku-4-5  
**Effort**: high  
**Purpose**: Archives completed phase plans; consolidates documentation; removes temp files; prepares for next phase

---

## Overview

Cleanup performs end-of-phase workspace management: archiving completed plans to `~/.claude/plans/archive/`, consolidating documentation into SKILLS-INDEX.md, removing temporary files, and preparing the workspace for the next phase. Includes dry-run mode for safe validation before destructive operations.

---

## DELEGATE Block Specification

### Input Fields

```yaml
phase: 5
  # Which phase to clean up

cleanup_scope: "plans" | "temp" | "docs" | "all"
  # What to clean:
  # plans = archive phase plans
  # temp = delete /tmp/ers-*.* files
  # docs = consolidate docs into SKILLS-INDEX.md
  # all = do all of the above

dry_run: true | false
  # true = show what would be done, don't apply
  # false = actually perform cleanup

consolidation_rules:
  plans: "archive to ~/.claude/plans/archive/"
  temp: "delete /tmp/ers-* patterns"
  docs: "consolidate to agentic-engineers/skills/SKILLS-INDEX.md"
```

### Example DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: 2026-06-02-cleanup-phase-5
timestamp: 2026-06-02T17:00:00Z
role: Cleanup Agent (Engineer)
model: claude-haiku-4-5
effort: high
scope: >
  Archive Phase 5 completed plans. Consolidate Phase 5.10 docs. Delete /tmp/ers-*
  temp files. Prepare workspace for Phase 6. Validate no critical files deleted.
context:
  - Phase: 5 (completed)
  - Plans to archive: ~/.claude/plans/phase-5-*.md
  - Docs to consolidate: skills/PHASE-5.10-* files
  - Temp pattern: /tmp/ers-*
plan:
  1. Dry-run to show what would be done
  2. Archive plans with timestamp
  3. Delete temp files
  4. Consolidate docs
  5. Validate nothing critical deleted
  6. Return HANDBACK with summary
success_criteria:
  - All Phase 5 plans archived with timestamp
  - All temp files deleted safely
  - Docs merged into SKILLS-INDEX.md
  - Git diff shows deliberate changes
  - No critical files in deleted list
---
```

---

## HANDBACK Block Specification

### Output Fields

```yaml
cleanup_scope: "all"

dry_run: false

plans_archived: 3
temp_files_deleted: 12
docs_consolidated: 2

actions:
  - type: archive
    source: "/home/user/.claude/plans/phase-5-quality-gates.md"
    destination: "/home/user/.claude/plans/archive/phase-5-quality-gates-2026-06-02.md"
    status: success

git_status:
  deleted:
    - "skills/PHASE-5.10-MONITORING-PLAN.md"
    - "skills/PHASE-5.10-AGENT-BASED-ORCHESTRATION.md"
  modified:
    - "skills/SKILLS-INDEX.md"

disk_freed_mb: 2.3

recommendation: "string"
```

### Example HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: 2026-06-02-cleanup-phase-5
timestamp: 2026-06-02T17:02:30Z
status: complete
cleanup_scope: all
dry_run: false
plans_archived: 3
temp_files_deleted: 12
docs_consolidated: 2
actions:
  - type: archive
    source: ~/.claude/plans/phase-5-quality-gates.md
    destination: ~/.claude/plans/archive/phase-5-quality-gates-2026-06-02.md
    status: success
  - type: delete
    pattern: /tmp/ers-*.txt
    count: 12
    status: success
  - type: consolidate
    from: [skills/PHASE-5.10-MONITORING-PLAN.md, skills/PHASE-5.10-AGENT-BASED-ORCHESTRATION.md]
    to: skills/SKILLS-INDEX.md
    status: success
git_status:
  deleted:
    - skills/PHASE-5.10-MONITORING-PLAN.md
    - skills/PHASE-5.10-AGENT-BASED-ORCHESTRATION.md
  modified:
    - skills/SKILLS-INDEX.md
disk_freed_mb: 2.3
recommendation: "Phase 5 workspace cleaned. Ready for Phase 6."
---
```

---

## Implementation Approach

### Algorithm: Safe Cleanup

```
IF dry_run:
  FOR EACH action:
    LOG "Would {action}"
  RETURN dry_run_summary()
ELSE:
  FOR EACH action:
    VALIDATE action is safe (not critical file)
    IF safe:
      apply_action()
    ELSE:
      escalate_to_human()
  RETURN cleanup_summary()
```

### Critical File Protection

```
PROTECTED_FILES = [
  "CLAUDE.md",
  "README.md",
  "agentic-engineers/AGENTS.md",
  "agentic-engineers/HANDOFF.md",
  "*.pyc", "*.pyo",
  "node_modules/", ".git/"
]

BEFORE DELETING:
  IF filename in PROTECTED_FILES:
    escalate to human
    RETURN error
```

---

## Testing Strategy

### Unit Tests

```bash
# Test 1: Dry-run shows what would be done
GIVEN: dry_run=true, plans to archive
EXPECTED: lists actions without applying

# Test 2: Archive with timestamp
GIVEN: plans to archive
EXPECTED: files copied to archive/ with -YYYY-MM-DD suffix

# Test 3: Doc consolidation
GIVEN: Phase 5.10 docs scattered
EXPECTED: merged into SKILLS-INDEX.md

# Test 4: Safe deletion (no critical files)
GIVEN: /tmp/ers-*.txt pattern
EXPECTED: temp files deleted, protected files kept
```

---

## Success Criteria Validation

- [x] Dry-run mode works correctly
- [x] Plans archived with timestamp
- [x] Temp files deleted safely
- [x] Docs consolidated into SKILLS-INDEX.md
- [x] Git diff shows deliberate changes
- [x] No critical files deleted
- [x] Disk space calculation accurate
- [x] Ready for end-of-phase cleanup runs

---

## Revision History

| Date | Status | Notes |
|------|--------|-------|
| 2026-04-28 | DESIGN | Specification created |
| 2026-05-05 | IMPLEMENTATION | Skill document created |

