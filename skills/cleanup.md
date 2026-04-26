---
name: Project Cleanup & Consolidation
description: Clean up temporary files, finished plans, and consolidate documentation after task completion
type: skill
delegable_to: [Orchestrator, Quality Engineer]
run_before: [git push, deployment]
---

# Cleanup & Consolidation Skill

**When to run**: Before every `git push` or deployment
**Purpose**: Keep repository clean, consolidate documentation, remove temporary artifacts

## Cleanup Phases

### Phase 1: Plans Directory
Clean up finished plans from `~/.claude/plans/`:

```bash
cd ~/.claude/plans

# Archive finished plans (move to archive/ subdirectory)
for plan in *.md; do
  # If plan is completed or old, move to archive
  [ -f "archive/$plan" ] && mv "$plan" "archive/$plan.backup-$(date +%s)"
  [ -f "$plan" ] && echo "  Review: $plan"
done

# Keep only active plans (referenced in current work)
```

**Decision matrix**:
- **Keep**: Plans referenced in active work ({service-name} two-way sync, etc.)
- **Archive**: Plans completed >7 days ago
- **Delete**: Duplicate or superseded versions

### Phase 2: Temporary Files
Remove temporary files created during work:

```bash
# Monitoring/audit scripts
rm -f /tmp/cicd-*.sh /tmp/*-monitor*.sh /tmp/{service-name}*.sh /tmp/final-monitor*.sh

# Temporary data files
rm -f /tmp/cli-check-*.txt /tmp/build-status*.txt

# Keep: Files referenced in active tasks
```

### Phase 3: Documentation Consolidation
Check for `.md` files that should be consolidated or deleted:

**In any repository**:
- Search: All `.md` files created/modified in current session
- Review each file:
  - **Is it a README.md in a subdirectory?** → Keep (standard pattern)
  - **Is it a skill in agentic-engineers/skills/?** → Keep (goes to git)
  - **Is it a plan in ~/.claude/plans/?** → Archive or keep (above)
  - **Is it ad-hoc documentation?** → Consolidate into existing README.md or CLAUDE.md
  - **Is it a TODO.md?** → Consolidate into project's existing TODO list
  - **Is it a standalone summary?** → Ask user to confirm deletion

**Consolidation rules**:

1. **New `.md` in repo root** (not README/CLAUDE)
   - Consolidate into existing README.md or CLAUDE.md
   - Example: "2026-04-27-IMPLEMENTATION-SUMMARY.md" → append to CLAUDE.md

2. **New architecture/pattern docs**
   - Move to agentic-engineers/skills/ (if not already there)
   - Add to skills/README.md or SKILLS-INDEX.md

3. **New procedure/runbook docs**
   - Consolidate into existing procedures documentation
   - Or create single ~/git/ers/RUNBOOKS.md if missing

4. **Duplicate documentation**
   - Keep single source of truth
   - Delete duplicates, update references

### Phase 4: Verify Changes

Before cleanup completes:

```bash
# What will be deleted?
git status --porcelain
git clean -n -d  # dry-run

# Confirm no critical files are removed
git ls-files | grep -E "\.md$" | sort
```

## Pre-Push Checklist

Before running `git push`:

```bash
# 1. Run cleanup
bash ~/.agents/agentic-engineers/skills/cleanup.sh

# 2. Verify no critical files deleted
git status

# 3. Check for uncommitted cleanup changes
git diff --name-status

# 4. If cleanup made changes, commit them
git add -A && git commit -m "chore: cleanup temporary files and consolidate documentation"

# 5. Now push
ERS_AUTO_PUSH=1 git push
```

## Cleanup Script Template

`~/.agents/agentic-engineers/skills/cleanup.sh`:

```bash
#!/bin/bash
set -e

echo "Phase 1: Plans cleanup..."
cd ~/.claude/plans
for plan in *.md; do
  age_days=$(( ($(date +%s) - $(stat -f%m "$plan")) / 86400 ))
  if [ $age_days -gt 7 ]; then
    echo "  Archive: $plan (${age_days}d old)"
    mkdir -p archive
    mv "$plan" "archive/$plan"
  fi
done
cd - > /dev/null

echo "Phase 2: Temp files cleanup..."
rm -f /tmp/cicd-*.sh /tmp/*-monitor*.sh /tmp/{service-name}*.sh
echo "  Removed monitoring scripts"

echo "Phase 3: Documentation review..."
cd /home/user/git/ers
find . -maxdepth 2 -name "*.md" -type f \
  ! -name "README.md" \
  ! -name "CLAUDE.md" \
  ! -name "TODO.md" \
  -newer ~/.claude/.last-cleanup-marker 2>/dev/null | while read file; do
  echo "  Review: $file"
  # Ask user for each non-standard .md found
done

echo ""
echo "Phase 4: Verification..."
git status --short | head -20
echo ""
echo "✅ Cleanup ready for review. Commit changes if appropriate:"
echo "   git commit -m 'chore: cleanup temporary files and consolidate documentation'"
```

## When to Ask User

Stop and ask before deleting:

- ❓ "This file looks important. Delete?"
  - `.md` files with substantial content not clearly temporary
  - Files with user-specific names
  - Files that might be referenced elsewhere

- ✅ **Safe to delete without asking**:
  - `/tmp/` files (temporary by nature)
  - Duplicate plans (if clearly superseded)
  - Old monitoring/audit scripts
  - Build artifacts

## Integration with Agentic-Engineers

### Pre-Push Hook

Add to orchestrator workflow:

```yaml
handoff_type: ORCHESTRATOR_CHECKPOINT
action: cleanup
when: before_push

steps:
  1. Run cleanup script
  2. Review changes (ask user if uncertain)
  3. Commit cleanup (if needed)
  4. Then proceed with push
```

### Automatic Cleanup

After every major task:

```bash
# After completing work
make verify
cleanup.sh
git add -A && git commit -m "chore: cleanup"
git push
```

## Cleanup Status Markers

Track when cleanup last ran:

```bash
# Mark last cleanup
touch ~/.claude/.last-cleanup-marker

# Find files modified after last cleanup
find . -newer ~/.claude/.last-cleanup-marker -name "*.md" -type f
```

## Per-Repository Cleanup Rules

### ~/git/ers/
- Keep: CLAUDE.md, Makefile, .github/workflows/*.yaml
- Consolidate: IMPLEMENTATION-SUMMARY.md into CLAUDE.md
- Archive: Old CICD monitoring scripts

### ~/git/ers/agentic-engineers/
- Keep: All skills in skills/*.md
- Keep: README.md, Makefile, SYSTEM.md, MANIFEST.md
- Consolidate: Duplicate skill documentation

### ~/.claude/plans/
- Keep: Active plans (< 7 days or referenced)
- Archive: Completed plans to archive/
- Delete: Superseded versions

## Checklist for Review

Before deleting ANY file, confirm:

- [ ] File is actually temporary/finished
- [ ] File is not referenced elsewhere
- [ ] Archive copy exists (if important)
- [ ] Git history preserves it (can recover if needed)
- [ ] No active work depends on this file

## Example Cleanup Session

```
Running cleanup...

Phase 1: Plans cleanup
  Archive: arm64-migration-plan.md (2d old)
  Keep: cheerful-booping-garden.md (active {service-name} work)

Phase 2: Temp files
  Removed: /tmp/cicd-monitor-120s.sh
  Removed: /tmp/{service-name}.sh
  Removed: /tmp/final-monitor.sh

Phase 3: Documentation review
  Review: ./IMPLEMENTATION-SUMMARY.md
    → Consolidate into CLAUDE.md? Ask user

Phase 4: Git status
  M CLAUDE.md (consolidated summary)
  D arm64-migration-plan.md
  D /tmp/cicd-monitor-120s.sh (already deleted)

Ready to commit:
  git commit -m "chore: cleanup temp files and consolidate documentation"
```

