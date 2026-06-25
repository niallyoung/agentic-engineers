# Design Phase G: Orchestrator Auto-Polling Architecture

**Status:** Design Phase (Pre-Implementation)  
**Priority:** P1 (Blocker for autonomous operation)  
**Date:** 2026-06-25  
**Effort Estimate:** 20-30 engineer hours across 3-4 weeks  
**Owner:** Niall Young  

---

## Problem Statement

### Current State
- ✅ **OrchestratorSkill** (`src/skills/orchestrator/scripts/orchestrator_skill.py`) exists with `poll_queue()` and `run_idle_loop()` methods
- ✅ **orchestrator-scheduler** skill (`src/skills/orchestrator-scheduler/SKILL.md`) designed to invoke Orchestrator on schedule
- ✅ **Orchestrator Agent** (`src/agents/orchestrator-agent.md`) defined with full routing/quality logic
- ❌ **No automatic trigger** to start polling when DELEGATEs arrive
- ❌ **Manual invocation required** — users must run `/orchestrator-scheduler` manually
- ❌ **No harness startup hook** — Claude Code, OpenCode, Copilot don't auto-invoke orchestrator at session start

### Gap Analysis
DELEGATEs sit in `~/.agentic-engineers/{harness}/{session_id}/queue/incoming/` but nobody polls them without manual intervention.

**Evidence:**
1. `orchestrator-scheduler` SKILL exists but is invoked only via `/orchestrator-scheduler` command
2. No startup hooks in `src/harnesses/claude_code/INTEGRATION.md` or other harness configs
3. Continuous polling setup docs (2026-05-03) are archived; AutomationController removed 2026-05-17
4. Queue paths are isolated per session/harness, but no active poller is wired up
5. `OrchestratorSkill.run_idle_loop()` implements deep sleep and polling, but entry point is manual

### Root Causes
1. **Harness Integration Missing** — Claude Code, OpenCode, Copilot startup don't invoke orchestrator-scheduler
2. **No Cron/Timer** — No systemd service, no launchd agent, no harness-internal timer
3. **Session Detection Incomplete** — Scheduler detects session at runtime, but no harness tells it to run
4. **Queue Polling is Voluntary** — Tasks only process if explicitly invoked

---

## Design Goals

### Primary Goal
Achieve autonomous DELEGATE processing: when a DELEGATE is written to `queue/incoming/`, it is picked up and processed within 3-5 minutes without manual intervention.

### Secondary Goals
1. **Minimal harness changes** — No modifications to core Claude Code, Copilot, OpenCode startup logic
2. **Session-aware** — Each session's queue is processed independently
3. **Cost-conscious** — Polling uses Haiku model (cheapest), sleep/idle when queue empty
4. **Debugging-friendly** — Clear logs, easy to disable, easy to monitor
5. **Graceful shutdown** — SIGTERM/SIGINT handled cleanly, no orphaned tasks

---

## Solution Architecture

### Option A: Harness Startup Hook (Recommended)

**Mechanism:** Each harness (Claude Code, OpenCode, Copilot) runs orchestrator-scheduler at session start.

**Pros:**
- ✅ Native to harness, no external daemons
- ✅ Session ID automatically detected
- ✅ Automatic cleanup on harness exit
- ✅ Works offline/locally

**Cons:**
- ⚠️ Requires minimal harness changes (settings.json hook)
- ⚠️ Polling runs in-harness, uses harness resources

**Implementation:**
```yaml
# dist/claude/settings.json (or settings.local.json)
{
  "hooks": {
    "on_session_start": [
      "python3 -m src.skills.orchestrator_scheduler.scripts.orchestrator_scheduler --retry 3"
    ]
  }
}
```

**Flow:**
1. User starts Claude Code/OpenCode/Copilot
2. Session initialized with session_id, harness detected
3. Harness fires `on_session_start` hook
4. Orchestrator scheduler runs in background loop
5. Polls `queue/incoming/` every 180 seconds (or faster with file watch)
6. Processes DELEGATEs as they arrive
7. On harness exit → scheduler gracefully stops

---

### Option B: System Service (launchd/systemd)

**Mechanism:** Register a macOS launchd or Linux systemd service that runs orchestrator-scheduler.

**Pros:**
- ✅ Truly standalone (decoupled from harness)
- ✅ Runs even if harness crashed
- ✅ Professional operations (service status, restart)

**Cons:**
- ❌ Requires system-level setup (sudo)
- ❌ Cross-platform complexity (launchd vs systemd)
- ❌ Hard to debug permission/path issues

**Implementation:**
```bash
# macOS launchd agent
~/Library/LaunchAgents/com.agentic-engineers.orchestrator.plist

# Linux systemd service
~/.config/systemd/user/agentic-engineers-orchestrator.service
```

**Recommendation:** Defer to Phase 2 (enterprise deployments)

---

### Option C: Hybrid (Recommended for Phase 1)

**Mechanism:** Start with Option A (harness startup hook), add Option B as optional enterprise layer.

**Flow:**
1. **Default (Option A):** Harness fires hook → scheduler runs in-session
2. **Enterprise (Option B):** Optional systemd/launchd service for standalone operation

**Migration Path:**
- Week 1-2: Implement Option A (harness startup)
- Week 3-4: Add Option B (systemd/launchd templates)
- Document both paths, users choose based on deployment model

---

## Detailed Design

### 1. Harness Startup Hook Integration

#### 1.1 Claude Code (dist/claude/settings.json)

**Location:** `dist/claude/settings.json` or `~/.claude/settings.local.json`

**Change:**
```json
{
  "model": "haiku",
  "hooks": {
    "on_session_start": [
      "python3 -m src.skills.orchestrator_scheduler.scripts.orchestrator_scheduler --retry 3 --verbose"
    ],
    "on_session_end": []
  }
}
```

**Notes:**
- `--retry 3` ensures scheduler handles transient errors (missing session ID, queue path not found)
- `--verbose` enables DEBUG logging for troubleshooting
- Scheduler runs synchronously at startup; exits after one polling cycle
- Next cycle triggered by next harness command or manual invocation

#### 1.2 OpenCode / Copilot

**Location:** `dist/opencode/settings.json`, `dist/copilot/settings.json`

**Same pattern as Claude Code:**
```json
{
  "hooks": {
    "on_session_start": [
      "python3 -m src.skills.orchestrator_scheduler.scripts.orchestrator_scheduler --retry 3"
    ]
  }
}
```

---

### 2. Orchestrator-Scheduler Enhancements

#### 2.1 Current Behavior

**File:** `src/skills/orchestrator-scheduler/scripts/orchestrator_scheduler.py`

**Current flow:**
1. Detect session ID from environment variables
2. Load OrchestratorSkill
3. Call `poll_queue()` once
4. Return (processed_count, failed_count)
5. Exit

**Issue:** Only one polling cycle per invocation; no continuous loop.

#### 2.2 Proposed Behavior

**Option A1: Single-cycle mode (current, unchanged)**
```python
scheduler = OrchestratorScheduler()
processed, failed = scheduler.run()  # One cycle, exit
```

**Option A2: Continuous-mode flag (new, for daemon operation)**
```python
scheduler = OrchestratorScheduler()
processed, failed = scheduler.run_continuous(
    poll_interval_seconds=180,      # Check every 3 minutes
    idle_sleep_seconds=600,          # Deep sleep after 3 empty polls
    max_cycles=None                  # None = run forever
)
```

**Recommendation:** Implement both; CLI flag determines mode:
```bash
# Single cycle (harness startup hook)
python3 -m src.skills.orchestrator_scheduler.scripts.orchestrator_scheduler

# Continuous loop (background daemon)
python3 -m src.skills.orchestrator_scheduler.scripts.orchestrator_scheduler --daemon
```

#### 2.3 Implementation Plan

**File:** `src/skills/orchestrator-scheduler/scripts/orchestrator_scheduler.py`

**Changes:**
1. Add `run_continuous()` method to `OrchestratorScheduler` class
2. Implement polling loop with exponential backoff (reuse OrchestratorSkill.run_idle_loop())
3. Add `--daemon` flag to CLI
4. Keep `run()` method for single-cycle invocation (unchanged, backwards compatible)
5. Add signal handler for SIGTERM/SIGINT
6. Log each cycle with timestamps

**Pseudocode:**
```python
def run_continuous(self, poll_interval_seconds=180, max_cycles=None):
    """
    Continuous polling loop mode (for daemon/standalone operation).
    
    Calls poll_queue() repeatedly with smart backoff:
    - Fast poll (30s) when tasks are processing
    - Slow poll (180s) when queue is empty
    - Deep sleep after 3 consecutive empty polls
    """
    cycle_count = 0
    while True:
        if max_cycles and cycle_count >= max_cycles:
            logger.info(f"Max cycles ({max_cycles}) reached, exiting")
            break
        
        processed, failed = self.run()  # One cycle
        cycle_count += 1
        
        if processed == 0:
            # Queue empty, use backoff
            logger.debug(f"Queue empty (cycle {cycle_count}), sleeping {poll_interval_seconds}s")
            time.sleep(poll_interval_seconds)
        else:
            # Work found, fast loop
            logger.debug(f"Processed {processed} tasks, polling again (fast)")
            time.sleep(5)  # Brief pause before next cycle

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--daemon', action='store_true', help='Run in continuous daemon mode')
    parser.add_argument('--retry', type=int, default=1, help='Retry attempts')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    scheduler = OrchestratorScheduler()
    
    if args.daemon:
        scheduler.run_continuous()  # Loop forever
    else:
        scheduler.run()  # One cycle, exit
```

---

### 3. Harness Hook Integration

#### 3.1 Settings File Format

**Current:** `settings.json` (locked, for defaults)  
**Per-project:** `settings.local.json` (user-editable)

**Hook Execution:**
- Harness reads `hooks.on_session_start` array
- Executes each command with subprocess
- Waits for completion (or timeout after 30 seconds)
- Logs output/errors to session log

#### 3.2 Error Handling

**If orchestrator-scheduler fails to start:**
1. Log warning to console
2. Continue harness startup (non-blocking)
3. Do NOT crash the harness

**If queue path not found:**
1. Scheduler logs error (queue-isolation not initialized)
2. Gracefully skips polling
3. User manually invokes scheduler after queue is initialized

**If CLAUDE_SESSION_ID not set:**
1. Scheduler raises RuntimeError (message tells user to set env var)
2. Harness catches, logs warning
3. User can retry after env var is set

---

### 4. Queue Polling Loop Logic

#### 4.1 Polling Cycle Flow

**Per cycle (~5 minutes):**

```
Poll queue/incoming/
  ├─ Empty? → Sleep 180s (3 min), loop
  ├─ Found tasks?
  │   ├─ Claim task (move incoming → processing)
  │   ├─ Spawn sub-agent via Agent tool
  │   ├─ Wait for HANDBACK
  │   ├─ Route result (done/failed/escalate)
  │   └─ Repeat for next task
  └─ After 3 empty cycles → Deep sleep (with file watch)
```

**Wake conditions (from deep sleep):**
- New file created in `queue/incoming/` (inotify on Linux, FSEvents on macOS)
- Timeout after 600 seconds (10 minutes)
- SIGUSR1 signal (external wake)

#### 4.2 Backoff Strategy

**Purpose:** Prevent CPU thrashing when queue is idle.

**Exponential backoff:**
```
Consecutive empty cycles → Sleep duration
0 (task found) → 5 seconds (fast loop)
1 → 180 seconds (3 minutes)
2 → 180 seconds
3+ → Enter deep sleep (600 seconds max, wakeup on file event)
```

**Reset:** Counter resets to 0 when a task is found.

---

### 5. Session & Harness Detection

#### 5.1 Environment Variable Detection (Runtime)

**Priority order:**
1. `CLAUDE_SESSION_ID` (Claude harness)
2. `COPILOT_SESSION_ID` (Copilot harness)
3. `AGENTIC_SESSION_ID` (explicit override)
4. `CLAUDE_CODE_SESSION_ID` (Claude Code CLI)

**Code:**
```python
def _detect_session_id(self) -> str:
    session_id = (
        os.environ.get('CLAUDE_SESSION_ID') or
        os.environ.get('COPILOT_SESSION_ID') or
        os.environ.get('AGENTIC_SESSION_ID') or
        os.environ.get('CLAUDE_CODE_SESSION_ID')
    )
    if not session_id:
        raise RuntimeError("No session ID found in environment")
    return session_id
```

#### 5.2 Harness Detection (Runtime)

**Priority order:**
1. `AGENTIC_HARNESS` (explicit override)
2. Infer from which session ID env var is set
3. Default to "claude"

**Code:**
```python
def _detect_harness(self) -> str:
    if os.environ.get('AGENTIC_HARNESS'):
        return os.environ.get('AGENTIC_HARNESS')
    if os.environ.get('COPILOT_SESSION_ID'):
        return 'copilot'
    if os.environ.get('CLAUDE_SESSION_ID'):
        return 'claude'
    return 'claude'  # default
```

**Key:** Both detection methods read fresh from environment at invocation time (not cached).

---

## Implementation Phases

### Phase 1: Harness Startup Hook (Weeks 1-2)

**Objective:** Wire orchestrator-scheduler to harness startup; verify end-to-end DELEGATE → processing pipeline.

**Tasks:**

1. **Update settings files** (30 min)
   - Edit `dist/claude/settings.json`, `dist/opencode/settings.json`, `dist/copilot/settings.json`
   - Add `hooks.on_session_start` with orchestrator-scheduler invocation
   - Commit to main branch

2. **Enhance orchestrator-scheduler CLI** (3 hours)
   - Add `--daemon` flag support
   - Add `--retry` flag (already exists)
   - Implement `run_continuous()` method
   - Add signal handling (SIGTERM, SIGINT)
   - Test with `--max-cycles 5` for validation

3. **Verify queue path detection** (1 hour)
   - Test that queue-isolation skill initializes queue paths correctly
   - Confirm paths match canonical layout: `~/.agentic-engineers/{harness}/{session_id}/queue/`
   - Test with multiple sessions/harnesses

4. **End-to-end test** (4 hours)
   - Create test DELEGATE file manually in `queue/incoming/`
   - Start Claude Code session (trigger hook)
   - Verify orchestrator-scheduler starts, detects DELEGATE, processes it
   - Verify result appears in `queue/done/`
   - Log observations and timing

5. **Documentation** (2 hours)
   - Update `orchestrator-scheduler` SKILL.md with new `--daemon` mode
   - Document harness startup hook in each harness guide
   - Add troubleshooting section (session ID not found, queue path issues)

**Success Criteria:**
- ✅ Settings files updated with hooks
- ✅ `--daemon` flag implemented and tested
- ✅ Queue path detection verified for all harnesses
- ✅ End-to-end test passes: DELEGATE → processing → done
- ✅ Logs are clear and timestamped
- ✅ Documentation updated

**Exit Criteria for Phase 1:**
- Harness can invoke orchestrator-scheduler at startup
- Scheduler detects and processes queued DELEGATEs
- Session ID and harness detection working correctly
- DELEGATE processing time: <5 minutes from queue arrival to done/

---

### Phase 2: Continuous Polling Mode (Weeks 2-3)

**Objective:** Implement full daemon mode with backoff, idle detection, and robust error handling.

**Tasks:**

1. **Implement polling loop** (4 hours)
   - Implement `run_continuous()` with exponential backoff
   - Integrate with `OrchestratorSkill.run_idle_loop()` for deep sleep
   - Test with empty queue, task arrival detection
   - Verify backoff math (5s → 180s → 600s deep sleep)

2. **Signal handling** (2 hours)
   - Register SIGTERM/SIGINT handlers
   - Graceful shutdown: finish current cycle, exit cleanly
   - Test: send SIGTERM while sleeping, verify quick exit

3. **File system watch** (3 hours)
   - Implement inotify (Linux) / FSEvents (macOS) for incoming/ directory
   - Wake from deep sleep when new file created
   - Fallback to polling if watch unavailable
   - Test on both Linux and macOS

4. **Heartbeat & logging** (2 hours)
   - Emit structured log (JSON) every cycle with metrics
   - Log format: timestamp, cycle_num, tasks_processed, next_sleep_duration
   - Add `--verbose` flag for DEBUG-level output

5. **Testing** (4 hours)
   - Unit test: backoff calculation, signal handling
   - Integration test: daemon loop with task arrival
   - Stress test: high-frequency task creation, verify no CPU thrashing
   - Timing test: verify 3-5 minute DELEGATE processing latency

**Success Criteria:**
- ✅ Daemon mode runs indefinitely with proper backoff
- ✅ File watch wakes scheduler early when DELEGATE arrives
- ✅ SIGTERM/SIGINT handled gracefully
- ✅ Structured logs show cycle progress
- ✅ CPU usage < 1% when idle (with backoff)
- ✅ Tests pass (unit + integration + stress)

---

### Phase 3: Enterprise Service Layer (Week 4, Optional)

**Objective:** Add systemd/launchd templates for standalone operation (separate from harness).

**Tasks:**

1. **systemd service template** (2 hours)
   - `~/.config/systemd/user/agentic-engineers-orchestrator.service`
   - Start command: `python3 -m src.skills.orchestrator_scheduler --daemon`
   - Restart policy: on-failure
   - Documentation: install, start, status, logs

2. **launchd agent template** (2 hours)
   - `~/Library/LaunchAgents/com.agentic-engineers.orchestrator.plist`
   - Same behavior as systemd
   - Auto-start on login

3. **Installation script** (2 hours)
   - Detect OS (macOS vs Linux)
   - Install service file to correct location
   - Enable and start service
   - Verify queue path is accessible

4. **Documentation** (2 hours)
   - Enterprise deployment guide
   - Service management (start, stop, status, logs)
   - Troubleshooting section

**Success Criteria:**
- ✅ Service files install without errors
- ✅ Service auto-starts orchestrator-scheduler
- ✅ Service recovers from crashes (restart policy)
- ✅ Logs accessible via `journalctl` or `launchctl`

---

## Validation & Acceptance

### Functional Tests

**Test 1: Harness Startup Hook Fires**
```bash
# Start Claude Code
claude-code

# Expected: logs show orchestrator-scheduler invoked at session start
# Check: ~/.claude/logs/session.log contains "orchestrator-scheduler" message
```

**Test 2: DELEGATE Arrival Triggers Processing**
```bash
# Create test DELEGATE in queue/incoming/
mkdir -p ~/.agentic-engineers/claude/$(uuidgen)/queue/incoming

cat > ~/.agentic-engineers/claude/$(uuidgen)/queue/incoming/test-task.yaml <<EOF
handoff_type: DELEGATE
task_id: test-task-1
agent: engineer
scope: "Test DELEGATE for auto-polling validation (minimal scope)"
context:
  - "This is a test task"
plan:
  - "Echo: Hello from auto-polling"
success_criteria:
  - "Task completes without error"
EOF

# Expected within 5 minutes:
# - DELEGATE moves from incoming/ to processing/
# - Result appears in done/
# - Logs show task processed
```

**Test 3: Continuous Polling Detects Empty Queue**
```bash
# Monitor logs while orchestrator runs in daemon mode
tail -f ~/.agentic-engineers/logs/orchestrator-scheduler.log

# Expected pattern:
# [15:32:10] Queue empty (cycle 1), sleeping 180s
# [15:32:10] Queue empty (cycle 2), sleeping 180s
# [15:32:10] Queue empty (cycle 3), entering deep sleep (600s)
# [15:32:15] New DELEGATE detected in queue/incoming/, waking early
```

**Test 4: Signal Handling (SIGTERM)**
```bash
# Start orchestrator in daemon mode
python3 -m src.skills.orchestrator_scheduler --daemon &
PID=$!

# Wait 10 seconds
sleep 10

# Send SIGTERM
kill -TERM $PID

# Expected:
# - Process exits within 2 seconds
# - Current polling cycle completes
# - Exit code 0 (success)
# - Logs show "SIGTERM received, graceful shutdown"
```

### Performance Metrics

| Metric | Target | Acceptance |
|--------|--------|-----------|
| DELEGATE detection latency | 3-5 minutes | <10 minutes |
| CPU usage (idle) | <1% | <5% |
| Memory usage (idle) | <100 MB | <200 MB |
| Signal handling latency | <2 seconds | <5 seconds |
| Poll cycle overhead | <100 ms | <500 ms |

---

## Risk & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Session ID not set in environment | Medium | High | Add clear error message; document session detection in harness guide |
| Queue path not initialized | Low | High | Check queue-isolation skill is invoked before scheduler; graceful fallback |
| Scheduler crashes mid-polling | Low | Medium | Signal handler ensures graceful shutdown; test crash recovery |
| File watch unavailable (Windows) | High | Low | Fallback to polling (every 180s) if inotify/FSEvents fail |
| CPU thrashing with high task rate | Low | Medium | Exponential backoff + tests verify no CPU spike; tune backoff thresholds if needed |
| Multiple schedulers polling same queue | Low | High | Queue isolation ensures per-session queues; document multiple harnesses warning |

---

## Files Modified

### New Files
- `src/orchestration/ORCHESTRATOR_AUTO_POLLING.md` (this design doc)

### Modified Files
1. **Settings:**
   - `dist/claude/settings.json` — add `hooks.on_session_start`
   - `dist/opencode/settings.json` — add `hooks.on_session_start`
   - `dist/copilot/settings.json` — add `hooks.on_session_start`

2. **Orchestrator-Scheduler:**
   - `src/skills/orchestrator-scheduler/scripts/orchestrator_scheduler.py` — add `--daemon` flag, `run_continuous()` method
   - `src/skills/orchestrator-scheduler/SKILL.md` — update documentation

3. **Documentation:**
   - `docs/guides/harness-setup/claude.md` — add auto-polling section
   - `docs/guides/harness-setup/opencode.md` — add auto-polling section
   - `src/harnesses/claude_code/INTEGRATION.md` — add hook configuration section

### Optional (Phase 3)
- `templates/systemd/agentic-engineers-orchestrator.service`
- `templates/launchd/com.agentic-engineers.orchestrator.plist`
- `scripts/install-orchestrator-service.sh`

---

## Dependencies & Prerequisites

### Required Before Implementation
- ✅ `queue-isolation` skill fully functional (queue path detection)
- ✅ `orchestrator-scheduler` skill exists and works (manual invocation)
- ✅ `OrchestratorSkill` class has `poll_queue()` and `run_idle_loop()` methods
- ✅ Harness supports `hooks` configuration in settings.json

### Build & Test Infrastructure
- Python 3.11+ (for async, type hints)
- pytest (for unit/integration tests)
- pytest-timeout (for signal handling tests)
- pytest-mock (for file system mocking)

### Knowledge Requirements
- UNIX signal handling (SIGTERM, SIGINT)
- File system events (inotify, FSEvents)
- Queue isolation & session detection
- DELEGATE/HANDBACK protocol

---

## Success Criteria (Phase 1 MVP)

1. ✅ Harness startup hook invokes orchestrator-scheduler
2. ✅ Scheduler detects DELEGATE files in queue/incoming/
3. ✅ DELEGATEs processed within 5 minutes of arrival
4. ✅ Results appear in queue/done/ with HANDBACK
5. ✅ Session ID and harness detection work correctly
6. ✅ Clear, timestamped logs for troubleshooting
7. ✅ No harness crashes due to scheduler failures
8. ✅ Documentation updated

---

## Open Questions

1. **Harness Hook Support:** Do harness versions (Claude Code, OpenCode, Copilot) all support `hooks.on_session_start` in settings.json?
   - If not: need to implement hook support first (separate task)
   - If yes: proceed as designed

2. **Backward Compatibility:** Should settings files be shared between dist/ and ~/.{claude,copilot}/?
   - Current: dist/ is defaults, ~/.*.settings.local.json is user override
   - Clarify: does user override fully replace, or merge with defaults?

3. **File Watch Availability:** Should we require inotify/FSEvents, or fallback-only?
   - Recommendation: Try to use, fallback to polling on failure (handles Windows, older systems gracefully)

4. **Queue Path Initialization:** Should queue-isolation be invoked automatically, or must user initialize first?
   - Current: queue-isolation provides functions, but doesn't auto-initialize on first run
   - Recommendation: Orchestrator-scheduler should call `queue_isolation.init_queue_structure()` at startup

---

## Glossary

| Term | Definition |
|------|-----------|
| **DELEGATE** | Task request (YAML file in queue/incoming/) with task_id, agent, scope, plan, success_criteria |
| **HANDBACK** | Task result (YAML file in queue/done/) with status, output, metrics, tokens |
| **Session ID** | UUID identifying a unique user session in Claude Code/OpenCode/Copilot |
| **Harness** | Execution environment (claude, copilot, opencode, local, gpt) |
| **Queue Path** | Canonical directory: `~/.agentic-engineers/{harness}/{session_id}/queue/` |
| **Polling Cycle** | One iteration of: read queue, process tasks, sleep |
| **Backoff** | Exponential sleep increase when queue is empty (5s → 180s → 600s) |
| **Deep Sleep** | Long idle period with file watch wake trigger |
| **Signal Handler** | Code that catches SIGTERM/SIGINT and triggers graceful shutdown |

---

## References

- [orchestrator-scheduler SKILL](../skills/orchestrator-scheduler/SKILL.md)
- [orchestrator SKILL](../skills/orchestrator/SKILL.md)
- [OrchestratorSkill implementation](../skills/orchestrator/scripts/orchestrator_skill.py)
- [Queue isolation SKILL](_meta/queue-isolation/SKILL.md)
- [DELEGATE/HANDBACK Protocol](../../docs/QUEUE-PROTOCOL.md)
- [Orchestrator Agent](../../src/agents/orchestrator-agent.md)

---

## Version & Changelog

| Date | Author | Status | Notes |
|------|--------|--------|-------|
| 2026-06-25 | Niall Young | Draft | Design Phase G: Orchestrator Auto-Polling |

---

## Next Steps (Executive Handoff)

1. **Review & Approval** (1 day)
   - Principal Engineer reviews this design
   - Feedback incorporated (if any)
   - Approved for implementation

2. **Implementation Sprint** (3-4 weeks)
   - Phase 1: Harness startup hook (Week 1-2)
   - Phase 2: Continuous polling mode (Week 2-3)
   - Phase 3: Enterprise service layer (Week 4, optional)

3. **Testing & Validation** (ongoing)
   - Unit + integration tests per phase
   - End-to-end validation with real DELEGATEs
   - Performance benchmarking

4. **Deployment** (1 week)
   - Merge to main branch
   - Update all harness distributions (dist/claude, dist/opencode, dist/copilot)
   - Documentation deployment to guides/
   - Release notes prepared

---

**Document prepared for Design Phase Review. Ready for implementation upon approval.**
