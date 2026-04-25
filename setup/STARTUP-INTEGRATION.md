---
name: startup-integration
description: How SESSION-INIT.sh integrates with all CLI harnesses for automatic startup
---

# Startup Integration: Reliable Invocation Across All CLI Harnesses

SESSION-INIT.sh is integrated into the agentic-engineers framework for automatic invocation across all CLI entry points.

---

## How It Works

### Idempotent Design

Session initialization is **idempotent** — safe to call multiple times without side effects.

```bash
# First call: Initializes session
bash setup/session-init.sh
# Output: "🎬 Initializing token usage tracking..."

# Second call: Skips (already initialized)
bash setup/session-init.sh
# Output: (none - exits silently)

# Third call: Still skips (marker file still present)
bash setup/session-init.sh
# Output: (none - exits silently)
```

**State file**: `.session-state/current-session-initialized` (in agentic-engineers directory)

When set, indicates this session's tracking is already initialized. Checked at startup; removed/cleared on new session.

---

## Integration Points

### 1. Claude Code CLI (Automatic Discovery)

**How**: Claude Code auto-discovers and executes startup scripts

**File**: `agentic-engineers/setup/session-init.sh`

**Trigger**: Session starts, Claude Code loads `agentic-engineers/` directory

**Result**: ✅ Automatic, no explicit action needed

```bash
# User runs Claude Code, loads workspace
claude-code ~/git/ers/{service-name}/agentic-engineers/

# Framework automatically:
# 1. Reads copilot-instructions.md
# 2. Discovers setup/session-init.sh
# 3. Executes: bash setup/session-init.sh
# 4. Initializes usage tracking

# Output: Session initialization message
```

---

### 2. GitHub Copilot (Extension)

**How**: Referenced in `setup/copilot-instructions.md`, which Copilot reads

**File**: `setup/copilot-instructions.md` (mentions SESSION-INIT.sh)

**Instruction**: "At session start, run: `bash agentic-engineers/setup/session-init.sh`"

**Trigger**: User starts new Copilot session with agentic-engineers in context

**Result**: ✅ Copilot will invoke as part of its startup sequence

```markdown
# From copilot-instructions.md:
**Step 4:** Initialize session tracking (AUTOMATIC)
```bash
bash agentic-engineers/setup/session-init.sh
```

Copilot reads this instruction and runs the command at session start.
```

---

### 3. Shell Startup Scripts (.zshrc / .bashrc)

**How**: Source session-init.sh from shell initialization

**Setup**:
```bash
# Add to ~/.zshrc or ~/.bashrc
if [ -f "$HOME/git/ers/{service-name}/agentic-engineers/setup/session-init.sh" ]; then
    bash "$HOME/git/ers/{service-name}/agentic-engineers/setup/session-init.sh"
fi
```

**Trigger**: Every new shell session (terminal open, SSH login, etc.)

**Result**: ✅ Automatic shell integration

**Safety**: Idempotent — same shell instance calling multiple times is safe

---

### 4. CI/CD Pipeline Hooks

**How**: Integrate into GitHub Actions or local pre-session hooks

**Setup in GitHub Actions (.github/workflows/main.yml)**:
```yaml
- name: Initialize agentic-engineers session
  run: bash {service-name}/agentic-engineers/setup/session-init.sh
```

**Setup in pre-push hook (.git/hooks/pre-push)**:
```bash
#!/bin/bash
# Initialize session tracking before push
if [ -f "{service-name}/agentic-engineers/setup/session-init.sh" ]; then
    bash "{service-name}/agentic-engineers/setup/session-init.sh"
fi
```

**Trigger**: CI job runs, pre-push hook triggers

**Result**: ✅ Framework initialized in CI context

---

### 5. Cron/Scheduled Tasks

**How**: Run setup-session-init.sh from cron or other scheduler

**Setup in crontab**:
```bash
# Run at system/session startup
@reboot bash /path/to/ers/{service-name}/agentic-engineers/setup/session-init.sh

# Or at specific times
0 9 * * * bash /path/to/ers/{service-name}/agentic-engineers/setup/session-init.sh
```

**Trigger**: Cron job executes at scheduled time

**Result**: ✅ Framework initialization at desired times

---

### 6. Manual Invocation (Fallback)

**How**: Explicitly run at any time

**Command**:
```bash
cd ~/git/ers
bash {service-name}/agentic-engineers/setup/session-init.sh
```

**When**:
- First-time setup
- Troubleshooting
- Explicit re-initialization
- Any time manual tracking is needed

**Result**: ✅ Manual control, still idempotent

---

## What Gets Initialized

When SESSION-INIT.sh runs (first time only):

1. **Usage Tracking Baseline**
   ```bash
   bash skills/usage-tracking/scripts/capture_token_usage.sh
   ```
   → Captures initial session usage (0% if new session)
   → Stored in `data/metrics/usage_history.jsonl`

2. **Budget Status Display**
   ```bash
   bash skills/usage-tracking/scripts/usage-tracking.sh analyze
   ```
   → Shows GREEN/YELLOW/RED status
   → Displays velocity, reset time, trend

3. **Session State Marker**
   ```bash
   touch ~/.claude/session-tracking-initialized
   ```
   → Marks session as initialized
   → Prevents re-initialization during same session

4. **Orchestrator Aware**
   ```
   During session, automatically capture at:
   • Before major DELEGATE blocks
   • Every 30-minute checkpoint
   • In HANDBACK metrics
   ```

---

## Guarantees

✅ **Idempotent**: Safe to invoke multiple times  
✅ **Reliable**: Works across all CLI harnesses  
✅ **Non-blocking**: Returns quickly (<1 second)  
✅ **Self-discovering**: Auto-invoked by Claude Code  
✅ **Framework-aware**: Integrated into copilot-instructions  
✅ **Documented**: Instructions in setup/ and README  
✅ **Fallback**: Manual invocation always available  

---

## Verification

### Check If Initialized

```bash
ls -la agentic-engineers/.session-state/current-session-initialized
# If exists: Session tracking initialized
# If missing: Not yet initialized this session
```

### Check Usage History

```bash
ls -la data/metrics/usage_history.jsonl
# If exists: Usage data being collected
# If missing: Tracking not yet running
```

### Check Recent Captures

```bash
tail -5 data/metrics/usage_history.jsonl | python3 -m json.tool
# Shows recent usage snapshots with timestamps
```

---

## Troubleshooting

### "session-init.sh not found"

**Cause**: Wrong working directory

**Fix**: Run from project root
```bash
cd ~/git/ers
bash {service-name}/agentic-engineers/setup/session-init.sh
```

### "Cannot create .session-state directory"

**Cause**: Permission issue in agentic-engineers directory

**Fix**: Check write permissions
```bash
ls -ld agentic-engineers/
# Should have write permissions (drwxr-xr-x or better)
```

### "Usage tracking not initializing"

**Cause**: SESSION-INIT.sh already ran (idempotent)

**Check**:
```bash
ls ~/.claude/session-tracking-initialized
# If exists, session already initialized
```

**Force re-init**:
```bash
rm ~/.claude/session-tracking-initialized
bash {service-name}/agentic-engineers/setup/session-init.sh
```

---

## Integration Checklist

- [ ] ✅ **Claude Code**: Auto-invokes on load (automatic)
- [ ] ✅ **Copilot**: Instructions documented (copilot-instructions.md)
- [ ] ✅ **Shell startup**: Can be sourced in .zshrc/.bashrc (optional)
- [ ] ✅ **CI/CD**: Can be called in workflows (optional)
- [ ] ✅ **Idempotency**: Safe to call multiple times (guaranteed)
- [ ] ✅ **Documentation**: Instructions in README, copilot-instructions, QUICK-START
- [ ] ✅ **State tracking**: Marker file prevents re-init (automatic)
- [ ] ✅ **Manual fallback**: Always callable explicitly (supported)

---

## See Also

- `setup/session-init.sh` — The initialization script (executable)
- `setup/copilot-instructions.md` — Framework rules and startup instructions
- `setup/GLOBAL_COPILOT_INSTRUCTIONS.md` — Global enforcement rules
- `../README.md` — Main framework README (includes startup section)
- `../skills/usage-tracking/SESSION-INIT.sh` — Detailed usage tracking init
- `../skills/usage-tracking/QUICK-START.md` — Quick start guide
