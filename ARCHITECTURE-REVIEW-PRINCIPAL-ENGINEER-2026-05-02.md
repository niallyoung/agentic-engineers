# PRINCIPAL ENGINEER ARCHITECTURE REVIEW
## External Script Prevention Audit
### Task: src-review-principal-engineer-2026-05-02
### Review Date: 2026-05-02

---

## ⚠️ CRITICAL FINDING

**Architecture does NOT prevent external scripts. Critical loopholes found.**

---

## VIOLATIONS SUMMARY

| # | Severity | Location | Issue | Impact |
|----|----------|----------|-------|--------|
| 1 | CRITICAL | `orchestration/config/` | 6 production cron jobs | Bypass Orchestrator entirely |
| 2 | CRITICAL | `orchestration/scripts/` | 10 executable scripts | Direct invocation possible anytime |
| 3 | CRITICAL | `orchestration/install-automation.sh` | Cron installer | Automates bypass setup |
| 4 | HIGH | `orchestration/scripts/*.sh` | Embedded cron instructions | Encourages external invocation |

---

## VIOLATION #1: CRON JOB INFRASTRUCTURE

**Location:** `orchestration/config/` directory

**Files Found (6 total):**
- queue-processor.cron (runs every 5 minutes)
- metrics-etl.cron (runs every hour)
- tokenadvisor.cron (runs daily at 17:00 UTC)
- daily-email-summary.cron (runs daily at 22:00 UTC)
- model-engineer.cron (runs daily at 17:15 UTC)
- ab-testing-monitor.cron (runs daily at 18:00 UTC)

**Evidence:**

orchestration/config/queue-processor.cron:
```
*/5 * * * * cd /home/user/git/ers/{service-name} && bash agentic-engineers/orchestration/scripts/process-log-queue.sh 2>&1
```

orchestration/config/metrics-etl.cron:
```
0 * * * * cd /home/user/git/ers/{service-name} && python ./agentic-engineers/skills/metrics-etl/scripts/metrics-etl.py --aggregate --days 7
```

**Impact:**
- Cron jobs run external scripts directly without queue
- No DELEGATE/HANDBACK protocol
- No Orchestrator routing
- Runs 5 minutes to hourly automatically

**Bypass Method:** `bash orchestration/install-automation.sh` → User approves → Jobs added to system crontab

---

## VIOLATION #2: DIRECT SCRIPT EXECUTION INFRASTRUCTURE

**Location:** `orchestration/scripts/` directory (10 files)

**Files Found:**
- usage-tracking.sh (direct bash invocation)
- process-log-queue.sh (calls send-alert-email.sh directly)
- capture_token_usage.sh (external script)
- usage-budget.sh (external script)
- send-alert-email.sh (calls external msmtp)
- manage-credentials.sh (external script)
- setup-msmtp.sh (external setup)
- setup-msmtp-unattended.sh (external setup)
- analyze_usage_trends.py (Python script invocation)
- usage_budget_check.py (Python script invocation)

**Evidence - usage-tracking.sh (Lines 12-22):**
```bash
case "${1:-help}" in
    capture)
        VERBOSE=true bash "$SCRIPT_DIR/capture_token_usage.sh"
        ;;
    analyze)
        python3 "$SCRIPT_DIR/analyze_usage_trends.py" "${2:-}"
        ;;
    snapshot)
        bash "$SCRIPT_DIR/capture_token_usage.sh"
        echo ""
        python3 "$SCRIPT_DIR/analyze_usage_trends.py"
```

**Evidence - process-log-queue.sh (Line 77):**
```bash
if bash "$(dirname "$0")/send-alert-email.sh" "$RECIPIENT" "$SUBJECT" "$EMAIL_BODY" 2>&1; then
    log_message "    ✓ Email sent to $RECIPIENT"
```

**Impact:**
- All scripts are executable (chmod +x)
- Can be invoked directly anytime: `bash orchestration/scripts/process-log-queue.sh`
- Zero queue validation
- Zero audit trail
- Zero Orchestrator involvement

**Bypass Method:** Direct shell invocation (no authorization required)

---

## VIOLATION #3: CRON AUTOMATION INSTALLER

**Location:** `orchestration/install-automation.sh`

**Purpose:** Installs all 6 .cron files into user's system crontab

**Evidence (Lines 1-3):**
```bash
#!/bin/bash
# Install all agentic-agents automation into user's crontab
# Safe workflow: shows what will be installed, allows review, then installs
```

**Evidence (Lines 69-80):**
```bash
TEMP_CRONTAB=$(mktemp)
trap "rm -f $TEMP_CRONTAB" EXIT

# Get existing crontab (if any)
crontab -l > "$TEMP_CRONTAB" 2>/dev/null || true

# Add header if this is first installation
if ! grep -q "ERS Agentic Agents" "$TEMP_CRONTAB" 2>/dev/null; then
    echo "" >> "$TEMP_CRONTAB"
    echo "# ERS Agentic Agents — Automation Framework" >> "$TEMP_CRONTAB"
    echo "# Installed: $(date)" >> "$TEMP_CRONTAB"
```

**Impact:**
- Tool explicitly designed to install external scheduling
- Once installed, cron daemon runs jobs independently
- No way to stop without editing crontab manually

**Bypass Method:** `bash orchestration/install-automation.sh` → approve → system crontab updated

---

## VIOLATION #4: EMBEDDED CRON INSTRUCTIONS

**Location:** `orchestration/scripts/usage-tracking.sh` and `process-log-queue.sh`

**Evidence - usage-tracking.sh (Lines 35-53):**
Shows embedded cron job setup instructions directing users to add jobs to crontab.

**Evidence - process-log-queue.sh (Line 2):**
```bash
# Process pending alerts from log queue
# Run every 15 minutes via cron to route alerts to email/voice/dashboard
```

**Impact:**
- Scripts actively encourage cron setup
- Documentation suggests external invocation is intended
- Violates AGENTS.md spec: "no external cron/tools"

---

## AGENTS.MD SPEC VIOLATIONS

### Violation A: "No direct delegation from external sources"
**AGENTS.md Line 20:**
```
**Entry Rule:** All work flows through Orchestrator for routing. 
No direct delegation from external sources.
```

**Status:** ✗ VIOLATED

**Evidence:**
- 10 scripts in orchestration/scripts/ are directly invokable
- 6 cron jobs bypass Orchestrator queue entirely
- Install script automates external scheduling

---

### Violation B: "No external cron/tools"
**AGENTS.md Line 74:**
```
- Orchestrator runs in harness via polling loop (no external cron/tools)
```

**Status:** ✗ VIOLATED

**Evidence:**
- orchestration/config/ contains 6 production .cron files
- orchestration/install-automation.sh designed to install them
- Scripts reference running "every 15 minutes via cron"

---

## PROOF OF CONCEPT: 4 WAYS TO BYPASS ARCHITECTURE TODAY

### Method 1: Direct Invocation (Immediate)
```bash
bash orchestration/scripts/process-log-queue.sh
```

✅ **Works today.** No DELEGATE creation needed.

### Method 2: Cron Job Installation (3 commands)
```bash
bash orchestration/install-automation.sh
# User approves installation
crontab -l
```

✅ **Works today.** Simple and automated.

### Method 3: Manual Cron Setup (1 command)
```bash
crontab -e
# Paste any line from orchestration/config/*.cron
```

✅ **Works today.** Only requires crontab access.

### Method 4: CI/CD Integration (5 lines)
```yaml
name: Token Analysis
on: schedule
  - cron: '0 17 * * *'
jobs:
  analyze:
    - run: bash orchestration/scripts/usage-tracking.sh capture
```

✅ **Works today.** Easy GitHub Actions integration.

---

## CONFIDENCE ASSESSMENT

**Question:** Does this architecture PREVENT external scripts FOREVER with ZERO loopholes?

**Answer:** ❌ **NO**

**Confidence:** 0.05 (5% chance architecture prevents external scripts)

**Reasoning:**

✅ **What's Right:**
- Orchestrator.py polling mechanism IS implemented
- run_poll_cycle() method exists and works
- DELEGATE/HANDBACK protocol IS designed in AGENTS.md
- Core agent implementations ARE in place
- Orchestrator.py validates DELEGATE format correctly

❌ **What's Wrong:**
- External script infrastructure actively PROVIDED (10 scripts + 6 crons)
- No enforcement prevents new scripts being added tomorrow
- Easy to accidentally re-create cron jobs
- Documentation encourages external invocation (script help text)
- install-automation.sh makes bypasses convenient
- No pre-commit hook prevents regression

---

## REMEDIATION ROADMAP

### IMMEDIATE (MUST-DO) - Today

```bash
# 1. Delete external script infrastructure
rm -rf orchestration/scripts/
rm orchestration/config/*.cron
rm orchestration/install-automation.sh

# 2. Verify no subprocess imports in agents
grep -r "import subprocess" orchestration/agents/*.py
# Should return: (no results)
```

### SHORT-TERM (This Week) - Prevent Regression

Add pre-commit hook at `.git/hooks/pre-commit` to check:
- No files in orchestration/scripts/
- No .cron files in orchestration/config/
- No installation scripts

### MEDIUM-TERM (This Month) - Convert to Skills

For each script in orchestration/scripts/:
1. Create skill file in src/skills/
2. Add to SKILLS.md index
3. Define input/output specs
4. Register with agent
5. Skill ONLY callable via DELEGATE/HANDBACK

### LONG-TERM (This Quarter) - Documentation

- Create docs/ORCHESTRATOR-ENTRY-POINT.md
- Document single polling harness entry point
- Verify queue directory structure
- Prove no other invocation paths exist

---

## CODE LOCATIONS FOR REMEDIATION

### Files to DELETE:

```
orchestration/scripts/usage-tracking.sh
orchestration/scripts/process-log-queue.sh
orchestration/scripts/capture_token_usage.sh
orchestration/scripts/usage-budget.sh
orchestration/scripts/send-alert-email.sh
orchestration/scripts/manage-credentials.sh
orchestration/scripts/setup-msmtp.sh
orchestration/scripts/setup-msmtp-unattended.sh
orchestration/scripts/analyze_usage_trends.py
orchestration/scripts/usage_budget_check.py

orchestration/config/queue-processor.cron
orchestration/config/metrics-etl.cron
orchestration/config/tokenadvisor.cron
orchestration/config/daily-email-summary.cron
orchestration/config/model-engineer.cron
orchestration/config/ab-testing-monitor.cron

orchestration/install-automation.sh
```

---

## EXPLICIT CONFIRMATION

> **"Architecture prevents external scripts" = YES or NO?**

## **NO** ❌

**Confidence:** 0.05 (5%)

**Why:**
- 10 directly-invokable scripts in orchestration/scripts/
- 6 production-ready cron jobs in orchestration/config/
- Installer script (install-automation.sh) ready to set up external scheduling
- No enforcement mechanisms to prevent new scripts being added
- Documentation actively encourages cron setup

---

## FINAL SUMMARY

The agentic-engineers codebase demonstrates **strong architectural INTENT** for queue-based delegation through AGENTS.md, orchestrator.py, and DELEGATE/HANDBACK protocol. However, it **completely UNDERMINES this intent** by providing:

1. **6 production-ready cron jobs** that invoke scripts directly
2. **10 directly-executable scripts** that bypass the queue entirely
3. **An automation installer** that sets up external scheduling
4. **Embedded cron instructions** encouraging users to set up external invocation

This creates a **false sense of security** where the architecture LOOKS correct (queues, routing, agents) but actually provides **convenient escape hatches to external scripts**. These must be deleted immediately, and all logic must be moved to SKILLS.md with pre-commit hook enforcement to prevent regression.

---

**Review Completed:** 2026-05-02
**Confidence Level:** 0.05 (5%)
**Architecture Status:** ❌ NOT AIRTIGHT - Critical loopholes enable external scripts
