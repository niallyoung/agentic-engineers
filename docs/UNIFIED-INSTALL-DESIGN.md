# Unified Install System Design Document

**Date**: 2026-06-07  
**Status**: Implemented  
**Component**: Multi-harness installation system  

## Overview

The agentic-engineers project now uses a **unified installation system** that replaces the previous two separate code paths (`make install` vs `make fresh-install-*`). This provides:

✅ **Consistent behavior** across all install modes  
✅ **Safe by default** with automatic backup strategy  
✅ **Flexible** with flags for different use cases (interactive, non-interactive, CI/testing)  
✅ **Per-harness control** with prompt-per-harness support  
✅ **Better UX** with clear messaging and progress indicators

## Key Changes

### 1. New Unified Installer Script

**File**: `renderer/scripts/unified-install.sh`

This script replaces the previous separate flows and provides:

- Single code path for all install modes
- Consistent backup strategy (auto-backup by default, configurable)
- Per-harness installation with progress reporting
- Support for flags: `--interactive`, `--no-backup`, `--force`, `--quiet`

### 2. Updated Makefile Targets

| Target | Mode | Behavior |
|--------|------|----------|
| `make install` | Non-interactive | Render all, auto-backup existing dirs, install to all 4 harnesses |
| `make clean-install` | Interactive | Prompt for each harness (install?), prompt for backup, then install |
| `make fresh-install-{harness}` | Interactive | Prompt for single harness only |
| `make install-{harness}` | Direct | Low-level: render directly into the harness dir via the marker-aware render script (for advanced users) |

### 3. Backup Strategy

**Default behavior** (non-interactive):
- If harness dir exists → auto-backup with per-second timestamp suffix: `~/.copilot.YYYYMMDD-HHMMSS/` (unique per run — same-day re-installs never collide)
- The backup is a non-destructive **copy** (`cp -a`), NOT a move. The live dir is
  left in place so the install step (a marker-aware merge) can preserve files we
  do not manage — `config.json`, auth tokens, session/history state.
- Then install new version on top of the preserved dir
- Maintains consistent state; the timestamped copy is a safety snapshot

**Interactive behavior**:
- Ask user: "Install {harness}? (y/n)"
- If dir exists and will be modified, ask: "Backup before install? (y/n)"
- User can choose: backup, skip backup, or cancel

**CI/Testing behavior**:
- `make install BACKUP=never DESTDIR=/tmp/ae-test` skips backup
- Safe for sandbox/container environments

## Usage Examples

### Standard Install (Recommended)

Non-interactive, auto-backup, all 4 harnesses:

```bash
make install
# Output:
# ℹ️  Rendering all harnesses...
# ℹ️  Backing up copilot: ~/.copilot/ → ~/.copilot.20260607_143022/
# ℹ️  Installing copilot...
# ✅ copilot: Installed successfully
# ... (3 more harnesses)
# ✅ Installation complete!
```

### Interactive Install (One Harness)

```bash
make fresh-install-copilot
# Output:
# Install copilot? (y/n): y
# Backup copilot before install? (y/n): y
# ℹ️  Backing up copilot...
# ✅ Backed up to ~/.copilot.20260607_143022/
# ℹ️  Installing copilot...
# ✅ copilot: Installed successfully
```

### Interactive Install (All Harnesses)

```bash
make clean-install
# Output:
# Install copilot? (y/n): y
# Backup copilot before install? (y/n): y
# ... (repeats for each harness)
```

### Testing/CI (No Backup)

```bash
make install BACKUP=never DESTDIR=/tmp/ae-test
# Skips backup, installs to /tmp/ae-test instead of $HOME
```

### Direct Install (Advanced)

```bash
# Direct low-level targets (still available):
make install-copilot          # Just copilot (no backup, no prompts)
make render-copilot           # Just render phase
```

## Backup Management

### Understanding Backup Directories

Backups are created with timestamp suffix:

```
~/.copilot/                    # Current installation
~/.copilot.20260607_143022/    # Backup from June 7, 2026 at 2:30:22 PM
~/.copilot.20260607_100515/    # Backup from June 7, 2026 at 10:05:15 AM (if reused same day)
```

### Manual Restore (if needed)

```bash
# Restore a backup manually
rm -rf ~/.copilot/
mv ~/.copilot.20260607_143022/ ~/.copilot/
```

### Backup Rotation (Future)

Current: Backups are kept indefinitely  
Future: Add `make status` command to show backup history and manage retention

## Design Decisions

### 1. Why Auto-Backup by Default?

**Problem**: Old system had two separate code paths:
- `make install`: No backup (risky for prod)
- `make fresh-install-*`: Interactive backup only

**Solution**: Always backup by default (safe by default principle). Users who want to skip backup must explicitly use `--no-backup` flag or non-interactive testing mode.

### 2. Why Surgical Install (Marker-Based Foreign File Protection)?

**Problem**: Harness directories contain both our managed code AND user config files (settings, auth tokens, session state).

**Solution**: Use marker files (`.agentic-engine-{harness}`) to track which files are managed by us. Install only our files, leave user config untouched. This is now implemented consistently across **all four harnesses** — every `install-{harness}` target invokes that harness's marker-aware render script directly against the destination (no blind `rsync dist/ → dest/`), so user-authored agents, skills, configs (`config.json`, `opencode.jsonc`), and docs are never overwritten.

**Benefits**:
- Safe: No accidental overwrites of user data
- Flexible: Users can add custom skills/agents alongside ours
- Clear ownership: Marker files document which code is managed

### 3. Why Unified Script?

**Problem**: Previous system had separate implementations:
- `install-harness.sh`: Interactive per-harness
- `backup-harnesses.sh`: Backup logic
- Makefile install targets: blind `rsync dist/ → dest/` for Copilot/OpenCode/Pi
  (no foreign-file protection) vs. marker-aware render script for Claude

**Solution**: Single `unified-install.sh` with flags:
- `--interactive`: Prompt per harness
- `--force`: Skip all prompts
- `--no-backup`: Skip backup
- `--quiet`: Suppress verbose output

**Benefits**:
- DRY: Single code path = fewer bugs
- Maintainable: One place to update logic
- Consistent: Same behavior regardless of entry point

## Implementation Details

### Marker Files

Each harness uses marker files to track ownership:

**Copilot**: `~/.copilot/skills/<skill>/.agentic-engine-copilot` (per-skill marker) + `~/.copilot/agents/.agentic-engine-copilot` (agent manifest) + sentinel line in `AGENTS.md`  
**Claude**: `~/.claude/skills/<skill>/.agentic-engine-claude` + `~/.claude/agents/.agentic-engine-claude` (agent manifest) + sentinel line in `CLAUDE.md`/`AGENTS.md`  
**OpenCode**: Same per-skill marker + agent manifest; sentinel comments in `AGENTS.md` and `opencode.jsonc`  
**Pi**: `~/.pi/agent/.agentic-engine-pi`

### Installation Flow

```
1. Parse arguments (--interactive, --no-backup, etc.)
2. For each harness:
   a. If interactive: ask "Install {harness}? (y/n)"
   b. If no-backup skip: go to render
   c. If dir exists: back it up
   d. Render: make render-{harness}
   e. Install: make install-{harness} (marker-aware render directly into dest)
   f. Report: success/failure
3. Print summary and exit
```

### Error Handling

**Backup fails**: Stop that harness, report failure (the live config is untouched
because the backup is a non-destructive copy).
**Render fails**: Stop installation for that harness (continue others); roll back
from the backup snapshot if one was taken.
**Install fails**: Report error and roll back the harness dir from the backup
snapshot, so a partially-applied install never corrupts the user's config.

## Migration Guide

### For End Users

**Old way**:
```bash
make fresh-install-copilot
```

**New way** (same UX):
```bash
make fresh-install-copilot   # Identical! (now uses unified-install.sh)
```

**Breaking changes**: None! All old commands still work.

### For Developers

**Old code paths** (deprecated but still work):
- `renderer/scripts/install-harness.sh` — marked as deprecated, points to unified-install.sh
- `renderer/scripts/backup-harnesses.sh` — kept for backward compatibility

**New code path** (canonical):
- `renderer/scripts/unified-install.sh` — single source of truth

## Future Enhancements

1. **Rollback on failure**: Automatically restore backup if install fails
2. **Backup rotation**: Limit to last N backups per harness (default: 5)
3. **Restore command**: `make restore-{harness} DATE=YYYYMMDD`
4. **Diff before backup**: Show what will change before backing up
5. **Dry-run mode**: `make install --dry-run` to preview changes
6. **Per-file markers**: Upgrade Pi from single marker to per-file tracking

## Testing

### Manual Testing

```bash
# Test non-interactive install to temp location
make install DESTDIR=/tmp/ae-test-$(date +%s)

# Test interactive install
make clean-install   # (respond y/n to prompts)

# Test single harness
make fresh-install-claude
```

### Automated Testing

```bash
# Run existing test suite (unchanged)
make test

# Run linting (unchanged)
make lint
```

## Troubleshooting

### "Installation failed for copilot"

Check:
```bash
make render-copilot                         # Does rendering work?
make install BACKUP=never DESTDIR=/tmp/test # Does install work (no backup)?
```

### Restore from backup

```bash
ls -la ~/.copilot*                              # Find backups
rm -rf ~/.copilot && \
  mv ~/.copilot.YYYYMMDD-HHMMSS/ ~/.copilot/    # Restore specific backup
```

### Verify marker files

```bash
find ~/.copilot/skills -name ".agentic-engine-copilot"
find ~/.claude/skills -name ".agentic-engine-claude"
```

## Appendix: Comparison with Previous System

### Before (Two Separate Code Paths)

```
make install
├─ install-copilot      (direct rsync, no backup)
├─ install-claude       (rsync, no backup)
├─ install-pi           (direct copy, no backup)
└─ install-opencode     (direct copy, no backup)

make clean-install
├─ backup-harnesses.sh  (backup all, with prompts)
├─ install-copilot
├─ install-claude
├─ install-pi
└─ install-opencode

make fresh-install-copilot
├─ install-harness.sh   (interactive, single harness)
    ├─ Prompt: Install?
    ├─ Prompt: Backup?
    └─ make install-copilot
```

**Problems**:
- Two separate code paths = inconsistent behavior
- Backup logic lived in separate script
- No unified control or error handling
- Different UX between interactive/non-interactive

### After (Single Unified Script)

```
make install
└─ unified-install.sh --destdir $HOME copilot claude pi opencode
    ├─ Auto-backup (no prompts)
    └─ Install all 4

make clean-install
└─ unified-install.sh --interactive --destdir $HOME copilot claude pi opencode
    ├─ Prompt per harness
    ├─ Backup on demand
    └─ Consistent UX

make fresh-install-copilot
└─ unified-install.sh --interactive --destdir $HOME copilot
    ├─ Same as above, single harness
    └─ Consistent with all other install modes
```

**Benefits**:
- Single code path = consistent behavior
- Unified backup strategy
- Per-harness control
- Extensible with flags

---

**Implementation**: `renderer/scripts/unified-install.sh` + Makefile updates (Makefile lines 96-122)  
**Related files**:
- `renderer/scripts/install-harness.sh` (deprecated, now points to unified)
- `renderer/scripts/backup-harnesses.sh` (unchanged, still used by unified)
- `renderer/scripts/render-*.sh` (unchanged, render phase)

**Backward compatibility**: ✅ All old commands still work  
**Breaking changes**: None  
**Migration effort**: None (transparent to users)
