---
name: Phase G - Harness-Native Queue Cooperation
description: Queue coordination via harness idle-loop integration without external daemons
version: 1.1
date: 2026-06-26
status: G-1 COMPLETE, G-2 COMPLETE (G-3 optional, deferred)
owner: Niall Young
effort_hours: 40-60
phases: 3
---

> **Status (2026-06-26):** Phases **G-1** and **G-2** are **COMPLETE** and merge-ready.
> Phase **G-3** (continuous external daemon mode) is intentionally **deferred** —
> G-2 delivers continuous in-process polling without any external daemon, so G-3
> is optional for the autonomous-queue-processing milestone. See
> [Phase G Completion Status](#phase-g-completion-status) below for metrics.

# Phase G: Harness-Native Queue Cooperation (AGENTS with SKILLS Compliant)

**Problem:** DELEGATEs queue in `~/.agentic-engineers/{harness}/{session}/queue/incoming/` but never process because no component invokes the orchestrator-scheduler SKILL.

**Solution:** Each harness integrates queue polling into its idle-loop. When idle (user not typing, no active task), invoke `/orchestrator-scheduler --poll-once` SKILL. This keeps all orchestration within the "AGENTS with SKILLS" rule—no external daemons, no system services, no startup hooks outside the framework.

**Design Principle:** The framework must orchestrate itself. All coordination happens via SKILLS that harnesses invoke.

---

## Executive Summary

### Key Innovation: Harness Idle-Loop Cooperation

Traditional queue automation (cron, systemd, launchd) violates SPEC.md constraints ("no external daemons"). Instead:

1. **Harness Idle Detection** — Each harness has an idle-loop that detects: user not typing, no task in progress
2. **Skill Invocation** — On idle, harness invokes `/orchestrator-scheduler --poll-once` SKILL  
3. **Queue Processing** — Scheduler polls `queue/incoming/`, processes DELEGATEs via Agent tool, moves results to `queue/done/`
4. **Continuation** — Harness returns to idle state; next idle-loop invokes scheduler again
5. **Natural Coordination** — Multiple harnesses share a session queue; scheduler serializes processing via file-based locking

### SPEC.md Compliance

✅ **No external daemons** — Polling runs inside harness, not as separate service  
✅ **No startup hooks** — Idle-loop integration is built into harness, not settings.json  
✅ **All work through SKILLS** — Orchestrator-scheduler is a SKILL, not a script or cron job  
✅ **AGENTS with SKILLS** — Framework orchestrates itself via agent-invoked skills  
✅ **Session-first model** — Each harness+session pair manages its own queue  

---

## Phase G Completion Status

### Phase G-1: Harness Idle-Loop Integration — ✅ COMPLETE

Each harness now wires its idle-loop to `orchestrator-scheduler --poll-once`, and
DELEGATE auto-processing works end-to-end (incoming → processing → done) with no
manual invocation.

| Metric | Result |
|--------|--------|
| Harnesses wired | 3 — Claude Code, OpenCode, Copilot CLI |
| Harness idle-loop tests | 303 (Claude) + 163 (OpenCode) + 101 (Copilot CLI) = **567 passing** |
| Scheduler tests | **21 passing** (`orchestrator-scheduler`) |
| Backoff-engine tests | **43 passing** (`BackoffPoller`) |
| Infrastructure tests | 21 scheduler + 43 backoff = **64 passing** |
| DELEGATE auto-processing | ✅ Working end-to-end across all 3 harnesses |

### Phase G-2: Continuous In-Process Polling — ✅ COMPLETE

G-2 adds the continuous polling engine (`src/harnesses/shared/backoff_poller.py`)
beneath the single-shot `--poll-once` call: adaptive exponential backoff plus a
file-watch on `queue/incoming/` that wakes immediately on DELEGATE arrival.

| Metric | Result |
|--------|--------|
| Backoff engine | **43 tests passing** (`tests/harnesses/shared/test_backoff_poller.py`) |
| Harness integration | **60 tests** — 14 new G-2 integration + 46 backoff-integration |
| Performance | 5 DELEGATEs processed in **71 ms**; backoff overhead **< 2 ms** per cycle |
| Backoff ladder | 5s → 30s → 180s → 600s (capped); resets to 5s on work/file-watch |

### G-2 Implementation Complete — No External Daemon

Phase G-2 delivers **continuous** queue polling **without any external daemon,
cron job, or system service** — a hard SPEC.md constraint. The mechanism:

- **All polling is in-process** within the harness idle-loop. The harness owns
  the cadence; `BackoffPoller` owns the *decision* of how long to wait and *when*
  to poll. No separate process, no systemd/launchd, no startup hook.
- **File-watch wakes immediately on queue arrival.** While sleeping, the poller
  scans `queue/incoming/` in short slices (`watch_poll_seconds`, default 0.5s) and
  wakes the instant a new DELEGATE file appears — resetting backoff to level 0.
- **Exponential backoff (5s → 600s) prevents thrashing.** Every empty poll
  advances the backoff one rung (5 → 30 → 180 → 600s, capped). Any processed
  DELEGATE or detected file resets to 5s, so an idle session settles into a cheap
  10-minute deep-sleep cadence yet still reacts within a poll-slice of new work.

Because polling runs inside the harness, **Phase G-3** (an *external* daemon mode
with systemd/launchd templates) is **optional and deferred** — G-1 + G-2 already
provide fully autonomous, continuous queue processing.

---

## Architecture

### Layer 1: Harness Idle-Loop Detection

Each harness (Claude Code, OpenCode, Copilot, local CLI) has an **idle-loop** that wakes every N seconds to check:

```
Harness Idle-Loop Cycle:
  ├─ Check: User typing?
  ├─ Check: Task in progress?
  ├─ Check: Message queue empty?
  └─ Decision:
     ├─ If any activity → Continue serving user (no skill invocation)
     └─ If all idle → Invoke `/orchestrator-scheduler --poll-once` SKILL
```

**Poll Interval:** 180-300 seconds (3-5 minutes)  
**Timeout:** Skill invocation returns within 30 seconds (or timeout)  
**Blocking:** Harness waits for scheduler to complete before returning to idle  

### Layer 2: orchestrator-scheduler SKILL

**File:** `src/skills/orchestrator-scheduler/scripts/orchestrator_scheduler.py`

**Purpose:** Single-cycle queue polling triggered by harness idle-loop.

```python
def run(self, max_wait_seconds=30):
    """
    One polling cycle, return within max_wait_seconds.
    
    Steps:
    1. Detect session ID from environment (CLAUDE_SESSION_ID, etc.)
    2. Initialize OrchestratorSkill with current session
    3. Call poll_queue(max_wait=max_wait_seconds) 
    4. Return (processed_count, failed_count)
    5. Harness continues idle-loop
    """
```

**Key Behavior:**
- Reads session ID fresh from environment each invocation (not cached)
- Processes ONE batch of DELEGATEs (no continuous loop)
- Returns quickly (within 30s timeout) so harness doesn't hang
- On next idle-loop cycle (~3-5 min later), invoked again
- Multiple invocations create natural polling rhythm

### Layer 3: OrchestratorSkill Queue Polling

**File:** `src/skills/orchestrator/scripts/orchestrator_skill.py`

**Method:** `poll_queue(max_wait_seconds=30)`

```python
def poll_queue(self, max_wait_seconds=30):
    """
    Process all available DELEGATEs in current session's queue.
    
    1. Acquire session-specific lock (~/.agentic-engineers/{harness}/{session}/queue/.lock)
    2. Scan queue/incoming/ for DELEGATE files
    3. For each DELEGATE:
       a. Move incoming/task.yaml → processing/task.yaml (atomic)
       b. Parse DELEGATE, spawn sub-agent via Agent tool
       c. Wait for HANDBACK (blocking)
       d. Move processing/task.yaml → done/task.yaml with HANDBACK
       e. Update metrics
    4. Release lock
    5. Return (total_processed, total_failed)
    6. Exit (harness continues, will invoke again on next idle cycle)
    """
```

**Multi-Harness Coordination:**
- File-based lock prevents concurrent polling of same queue
- Lock held only during polling cycle (not during agent execution)
- If lock held, skip this cycle (another harness is processing)
- Try again on next idle-loop invocation

### Layer 4: Multi-Harness Session Sharing

When multiple harnesses (Claude Code + OpenCode) share a session:

```
Session: abc-def-ghi

Harness A (Claude):          Harness B (OpenCode):
  Idle-Loop ──┐             Idle-Loop ──┐
              │                        │
              ├→ Invoke Scheduler      ├→ Invoke Scheduler
              │   (acquire lock)       │   (wait for lock)
              ├→ Process DELEGATEs     │   (skip, lock held)
              ├→ Release lock          │
              │                        ├→ Next cycle (acquire lock)
              │                        ├→ Process remaining DELEGATEs
              │                        └─ Release lock
```

**Natural Serialization:** File locks ensure only one harness processes queue at a time. No explicit coordination needed.

---

## Detailed Design

### 1. Harness Idle-Loop Integration

#### 1.1 Claude Code Harness

**File:** `src/harnesses/claude_code/idle_loop.py`

**Responsibilities:**
- Detect user inactivity (no keystrokes, no API calls, no message queue entries)
- Measure idle duration
- Invoke `/orchestrator-scheduler --poll-once` SKILL when idle threshold reached
- Handle SKILL timeout gracefully

**Pseudocode:**

```python
class ClaudeIdleLoop:
    def __init__(self, poll_interval_seconds=180):
        self.poll_interval = poll_interval_seconds
        self.last_activity_time = time.time()
        self.idle_threshold = poll_interval_seconds
        self.scheduler_skill = SkillInvoker("orchestrator-scheduler")
    
    def on_user_activity(self):
        """Called whenever user types, clicks, or sends message."""
        self.last_activity_time = time.time()
    
    def check_idle(self) -> tuple[int, int]:
        """
        Check if idle; if so, invoke scheduler.
        Returns (tasks_processed, tasks_failed).
        """
        idle_duration = time.time() - self.last_activity_time
        
        if idle_duration < self.idle_threshold:
            return (0, 0)  # Not idle yet
        
        try:
            # Invoke scheduler SKILL (blocking, ~30s timeout)
            result = self.scheduler_skill.invoke(
                args=["--poll-once"],
                timeout_seconds=30
            )
            processed = result.get("processed", 0)
            failed = result.get("failed", 0)
            logger.info(f"Queue polling: {processed} processed, {failed} failed")
            return (processed, failed)
        except TimeoutError:
            logger.warning("Scheduler timed out; will retry on next idle cycle")
            return (0, 0)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            return (0, 0)  # Continue, don't crash harness
```

**Integration Point:** Harness main loop calls `idle_loop.check_idle()` every 30-60 seconds.

#### 1.2 OpenCode & Copilot Harnesses

**Same pattern as Claude.** Each harness gets its own `idle_loop.py` with same interface.

#### 1.3 Local CLI (planned — not yet shipped)

**File:** `src/harnesses/cli/idle_loop.py` (future; `src/harnesses/cli/` is not yet wired)

**Behavior:** 
- CLI waits for next user command
- After returning result and before waiting for next command, invokes scheduler
- No continuous loop; scheduler runs once per command cycle

### 2. Orchestrator-Scheduler SKILL Enhancements

#### 2.1 Current State (as of 2026-06-25)

**File:** `src/skills/orchestrator-scheduler/SKILL.md`

The skill already exists and has `run()` method that performs one polling cycle. Current usage is manual: `/orchestrator-scheduler`.

#### 2.2 New Flag: --poll-once

**Purpose:** Explicit single-cycle mode (same as current behavior, but named flag).

**CLI:**

```bash
# Manual invocation (single cycle)
/orchestrator-scheduler --poll-once

# Programmatic invocation from harness
scheduler_skill.invoke(args=["--poll-once"], timeout_seconds=30)
```

**Implementation:**

```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--poll-once",
        action="store_true",
        help="Single polling cycle (default if no flag specified)"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Continuous daemon mode (for future enterprise deployments)"
    )
    args = parser.parse_args()
    
    scheduler = OrchestratorScheduler()
    
    if args.daemon:
        # Future: continuous loop with backoff
        scheduler.run_continuous()
    else:
        # Single cycle (poll-once or default)
        processed, failed = scheduler.run()
        print(f"Processed: {processed}, Failed: {failed}")
        sys.exit(0)
```

**Return Format (JSON):**

```json
{
  "processed": 3,
  "failed": 0,
  "queue_empty": false,
  "elapsed_seconds": 2.4,
  "next_check_seconds": 180
}
```

#### 2.3 Session & Harness Detection (Runtime)

**Already implemented.** Scheduler reads fresh from environment each invocation:

```python
def _detect_session_id(self) -> str:
    """Read from environment at runtime (not cached)."""
    session_id = (
        os.environ.get('CLAUDE_SESSION_ID') or
        os.environ.get('COPILOT_SESSION_ID') or
        os.environ.get('AGENTIC_SESSION_ID') or
        os.environ.get('CLAUDE_CODE_SESSION_ID')
    )
    if not session_id:
        raise RuntimeError(
            "No session ID found. Set CLAUDE_SESSION_ID, "
            "COPILOT_SESSION_ID, or AGENTIC_SESSION_ID"
        )
    return session_id
```

### 3. File-Based Locking for Multi-Harness Coordination

#### 3.1 Lock File Location

**Path:** `~/.agentic-engineers/{harness}/{session_id}/queue/.lock`

**Format:** Plain text file with:
```
PID
timestamp
harness_name
```

**Example:**
```
12345
2026-06-25T14:32:10Z
claude
```

#### 3.2 Lock Acquisition Algorithm

```python
def acquire_lock(lock_path, timeout_seconds=5, retry_interval=0.1):
    """
    Attempt to acquire session queue lock.
    
    Returns: LockHandle (context manager) or raises LockTimeoutError
    """
    start_time = time.time()
    
    while True:
        try:
            # Atomic create (fails if exists)
            fd = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY
            )
            # Write PID, timestamp, harness
            with os.fdopen(fd, 'w') as f:
                f.write(f"{os.getpid()}\n")
                f.write(f"{datetime.utcnow().isoformat()}Z\n")
                f.write(f"{os.environ.get('AGENTIC_HARNESS', 'unknown')}\n")
            
            logger.debug(f"Lock acquired: {lock_path}")
            return LockHandle(lock_path)
        
        except FileExistsError:
            # Lock held by another harness
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                logger.debug("Lock timeout; skipping this cycle")
                raise LockTimeoutError()
            
            time.sleep(retry_interval)  # Brief wait, try again
```

#### 3.3 Lock Release

```python
def release_lock(lock_path):
    """Release lock file."""
    try:
        os.remove(lock_path)
        logger.debug(f"Lock released: {lock_path}")
    except FileNotFoundError:
        pass  # Already removed
```

#### 3.4 Stale Lock Cleanup

**Problem:** If harness crashes, lock file remains.

**Solution:** Scheduler checks lock age on startup:

```python
def acquire_lock_with_stale_cleanup(lock_path, stale_age_seconds=300):
    """
    Acquire lock, cleaning up stale locks (age > stale_age_seconds).
    """
    if os.path.exists(lock_path):
        age = time.time() - os.path.getmtime(lock_path)
        if age > stale_age_seconds:
            logger.warning(
                f"Stale lock detected (age: {age}s); removing: {lock_path}"
            )
            os.remove(lock_path)
    
    return acquire_lock(lock_path)
```

### 4. Queue Polling Logic

#### 4.1 Poll Cycle Flow

**One cycle (triggered by harness idle-loop):**

```
1. Detect session ID from environment
2. Initialize OrchestratorSkill
3. Try to acquire queue lock (5s timeout)
   - If locked: skip this cycle (another harness has it), return (0, 0)
   - If acquired: proceed
4. List queue/incoming/*.yaml files
   - If empty: release lock, return (0, 0)
5. For each DELEGATE file:
   a. Atomic move: incoming/task.yaml → processing/task.yaml
   b. Parse DELEGATE YAML
   c. Spawn sub-agent via Agent tool (blocking)
   d. Receive HANDBACK
   e. Append HANDBACK to processing/task.yaml
   f. Atomic move: processing/task.yaml → done/task.yaml
   g. Increment processed counter
6. Release lock
7. Return (total_processed, total_failed)
```

**Timing:**
- Acquire lock: <100ms
- Per DELEGATE: 10-60 seconds (depends on agent work)
- Release lock: <10ms
- Total per cycle: ~30 seconds (or timeout)

#### 4.2 Error Handling

**Scenario: DELEGATE file corrupt or unparseable**

```python
try:
    delegate = yaml.safe_load(open(incoming_file))
except yaml.YAMLError as e:
    logger.error(f"Corrupt DELEGATE: {incoming_file}: {e}")
    # Move to quarantine/ for inspection
    shutil.move(incoming_file, quarantine_path)
    failed_count += 1
    continue
```

**Scenario: Sub-agent crashes or times out**

```python
try:
    handback = agent_tool.invoke(delegate, timeout_seconds=300)
except TimeoutError:
    logger.error(f"Agent timeout for task {task_id}")
    # Move back to incoming/ for retry on next cycle
    shutil.move(processing_file, incoming_file)
    failed_count += 1
    continue
except Exception as e:
    logger.error(f"Agent error for task {task_id}: {e}")
    # Move to failed/ with error details
    with open(failed_file, 'w') as f:
        yaml.dump({
            'delegate': delegate,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }, f)
    failed_count += 1
    continue
```

### 5. Session & Harness Detection

#### 5.1 Environment Variables (Runtime)

Scheduler reads fresh from environment **at invocation time**:

| Priority | Variable | Harness | Notes |
|----------|---|---|---|
| 1 | `CLAUDE_SESSION_ID` | Claude Code | Set by Claude harness |
| 2 | `COPILOT_SESSION_ID` | Copilot/VS Code | Set by Copilot extension |
| 3 | `AGENTIC_SESSION_ID` | Any | Generic override |
| 4 | `CLAUDE_CODE_SESSION_ID` | Local CLI | Set by local CLI |

**Implementation:**

```python
def _detect_session_id(self) -> str:
    """Detect session ID from environment (runtime read, not cached)."""
    session_id = (
        os.environ.get('CLAUDE_SESSION_ID') or
        os.environ.get('COPILOT_SESSION_ID') or
        os.environ.get('AGENTIC_SESSION_ID') or
        os.environ.get('CLAUDE_CODE_SESSION_ID')
    )
    if not session_id:
        raise RuntimeError(
            "No session ID in environment. "
            "Set CLAUDE_SESSION_ID, COPILOT_SESSION_ID, or AGENTIC_SESSION_ID"
        )
    return session_id

def _detect_harness(self) -> str:
    """Detect harness from environment or infer from session env var."""
    if os.environ.get('AGENTIC_HARNESS'):
        return os.environ.get('AGENTIC_HARNESS')
    if os.environ.get('COPILOT_SESSION_ID'):
        return 'copilot'
    if os.environ.get('CLAUDE_SESSION_ID'):
        return 'claude'
    return 'claude'  # default
```

#### 5.2 Queue Path Construction

**Canonical path:**

```
~/.agentic-engineers/{harness}/{session_id}/queue/
  ├─ incoming/
  │   ├─ task1.yaml
  │   └─ task2.yaml
  ├─ processing/
  │   └─ (empty or in-progress)
  ├─ done/
  │   ├─ task0.yaml (with HANDBACK)
  │   └─ task-1.yaml (with HANDBACK)
  └─ .lock (temporary, session-wide)
```

---

## Implementation Phases

### Phase G-1: Harness Idle-Loop Integration (Weeks 1-2)

**Objective:** Wire harness idle-loop → orchestrator-scheduler SKILL invocation. Verify end-to-end DELEGATE → processing pipeline.

**Tasks:**

1. **Understand current idle-loop implementation** (2 hours)
   - Review Claude Code, OpenCode, Copilot idle-loop detection
   - Identify where idle-loop callback currently fires
   - Confirm no blocking issues with skill invocation during idle

2. **Implement idle-loop integration (Harness-agnostic)** (6 hours)
   - Create `src/skills/orchestrator-scheduler/harness_idle_loop.py` (base class)
   - Define SkillInvoker interface for calling `/orchestrator-scheduler --poll-once`
   - Implement signal handling for skill timeout (SIGALRM on Unix)
   - Create concrete implementations:
     - `src/harnesses/claude_code/idle_loop.py`
     - `src/harnesses/opencode/idle_loop.py`
     - `src/harnesses/copilot_cli/idle_loop.py`

3. **Enhance orchestrator-scheduler SKILL** (4 hours)
   - Add `--poll-once` flag (explicit, documented)
   - Implement clean timeout behavior (return within 30s)
   - Add JSON output for harness consumption
   - Update `SKILL.md` with new flag and return format

4. **Test queue-lock mechanism** (4 hours)
   - Implement file-based lock in `OrchestratorSkill.poll_queue()`
   - Test lock acquisition/release with single harness
   - Test stale lock cleanup
   - Unit test: lock timeout scenarios

5. **End-to-end validation** (4 hours)
   - Create test DELEGATE manually in `queue/incoming/`
   - Start Claude Code → idle-loop fires → scheduler processes DELEGATE
   - Verify DELEGATE moves from incoming/ → processing/ → done/
   - Observe timing (should complete within 3-5 min)
   - Logs show clean progression

6. **Documentation** (2 hours)
   - Update `orchestrator-scheduler` SKILL.md with idle-loop integration
   - Document harness idle-loop callback in each harness guide
   - Add troubleshooting: "DELEGATE not processing" checklist

**Success Criteria:**
- ✅ Idle-loop invokes scheduler SKILL
- ✅ Scheduler processes one DELEGATE batch per invocation
- ✅ Session ID detected correctly
- ✅ Queue lock acquired/released cleanly
- ✅ DELEGATE → processing → done flow works
- ✅ Logs are clear and timestamped
- ✅ No harness crashes due to scheduler failures
- ✅ Documentation updated

**Exit Criteria for Phase G-1:**
- Harness idle-loop invokes scheduler SKILL automatically
- Scheduler detects and processes queued DELEGATEs
- Single-harness end-to-end test passes
- DELEGATE processing latency: <5 minutes from arrival

---

### Phase G-2: Multi-Harness Coordination (Weeks 2-3)

**Objective:** Verify file-based locking works correctly when multiple harnesses share a session queue.

**Tasks:**

1. **Multi-harness queue isolation test** (3 hours)
   - Set up two harnesses (Claude Code + OpenCode) with same session ID
   - Create DELEGATEs in shared queue
   - Start both harnesses simultaneously
   - Verify: only one processes queue at a time (lock-based serialization)
   - Observe: second harness skips this cycle, retries on next idle

2. **Stale lock cleanup test** (2 hours)
   - Start harness, create lock file
   - Kill harness (simulates crash)
   - Verify lock file remains
   - Start scheduler again; confirm stale lock detected and cleaned
   - Verify scheduler proceeds with polling after cleanup

3. **Concurrent task processing test** (4 hours)
   - Create 5 DELEGATEs in queue
   - Start scheduler with max_wait=60 seconds
   - Verify all 5 processed in one cycle (not one-per-cycle)
   - Measure performance: tasks/second, total elapsed
   - Verify lock held only during polling cycle, released before agent execution

4. **Error handling test** (3 hours)
   - Corrupt DELEGATE YAML; verify quarantine/error handling
   - Agent timeout (10s task, 5s timeout); verify retry-on-next-cycle
   - Lock file unwritable; verify graceful failure
   - Queue path missing; verify clear error message

5. **Performance benchmarking** (2 hours)
   - Baseline: lock acquisition/release overhead
   - Per-DELEGATE processing time (empty agent)
   - Concurrent harness stress test (10 harnesses, same queue)
   - Verify no CPU thrashing, lock contention manageable

**Success Criteria:**
- ✅ Lock-based serialization prevents concurrent polling
- ✅ Stale lock cleanup works
- ✅ Multiple DELEGATEs processed per cycle
- ✅ Error handling is graceful (no crashes)
- ✅ Performance acceptable (lock overhead <10ms)

---

### Phase G-3: Continuous Daemon Mode (Optional, Week 4)

**Objective:** Add daemon mode for enterprise deployments (systemd/launchd services). Not required for MVP, but documented for future.

**Tasks:**

1. **Daemon mode CLI flag** (2 hours)
   - Add `--daemon` flag to orchestrator-scheduler
   - Implement `run_continuous()` method with exponential backoff
   - Backoff strategy: 5s (work found) → 180s (queue empty) → 600s (deep sleep)

2. **File watch for early wakeup** (3 hours)
   - Implement inotify (Linux) / FSEvents (macOS) for incoming/ directory
   - Wake from deep sleep when new DELEGATE file created
   - Fallback to polling if file watch unavailable (Windows)

3. **Signal handling** (2 hours)
   - Register SIGTERM/SIGINT handlers
   - Graceful shutdown: finish current cycle, exit cleanly
   - Test: send SIGTERM while sleeping, verify quick exit

4. **systemd/launchd templates** (3 hours)
   - Create `templates/systemd/agentic-engineers-orchestrator.service`
   - Create `templates/launchd/com.agentic-engineers.orchestrator.plist`
   - Document installation and management

**Success Criteria:**
- ✅ Daemon mode runs indefinitely with proper backoff
- ✅ File watch wakes scheduler early
- ✅ SIGTERM/SIGINT handled gracefully
- ✅ Daemon templates work on both Linux and macOS

**Note:** Phase G-3 is optional for MVP. Phase G-1 and G-2 are sufficient for autonomous queue processing.

---

## Coordination Patterns

### Pattern 1: Single-Harness Session

```
Session: abc-def-ghi
Harness: Claude Code (only)

Idle-Loop Cycle 1 (t=180s):
  ├─ Check idle (user not typing)
  ├─ Invoke: /orchestrator-scheduler --poll-once
  │   ├─ Acquire lock
  │   ├─ Queue empty
  │   └─ Release lock
  └─ Return (0, 0), resume idle

Idle-Loop Cycle 2 (t=360s):
  ├─ DELEGATE arrives (external system creates it)
  ├─ Check idle
  ├─ Invoke: /orchestrator-scheduler --poll-once
  │   ├─ Acquire lock
  │   ├─ Found: incoming/task-1.yaml
  │   ├─ Move: incoming/task-1.yaml → processing/task-1.yaml
  │   ├─ Spawn sub-agent (Engineer)
  │   ├─ Agent processes, returns HANDBACK
  │   ├─ Move: processing/task-1.yaml → done/task-1.yaml
  │   └─ Release lock
  └─ Return (1, 0), resume idle
```

### Pattern 2: Multi-Harness Session (Sequential)

```
Session: abc-def-ghi
Harness A: Claude Code
Harness B: OpenCode

Initial Queue: [DELEGATE-1, DELEGATE-2, DELEGATE-3]

Harness A Cycle (t=180s):
  ├─ Invoke scheduler
  ├─ Acquire lock (succeeds)
  ├─ Process DELEGATE-1
  ├─ Process DELEGATE-2
  ├─ Release lock
  └─ Return (2, 0)

Harness B Cycle (t=180s, concurrent):
  ├─ Invoke scheduler
  ├─ Try acquire lock (held by A, timeout=5s)
  ├─ Wait 100ms, retry
  ├─ Wait 100ms, retry
  ├─ Timeout → skip this cycle
  └─ Return (0, 0), try again on next cycle

Harness B Cycle (t=360s):
  ├─ Invoke scheduler
  ├─ Acquire lock (succeeds, A idle)
  ├─ Process DELEGATE-3
  ├─ Release lock
  └─ Return (1, 0)
```

### Pattern 3: Stale Lock Recovery

```
Session: abc-def-ghi
Harness: Claude Code

Scenario: Harness crashes, lock file remains

Harness restart (t=0):
  ├─ Idle-loop starts
  ├─ Invoke scheduler (t=180s)
  │   ├─ Check lock file
  │   ├─ Lock age: 300s (5 minutes, stale)
  │   ├─ Log warning: "Stale lock detected, age: 300s"
  │   ├─ Remove stale lock
  │   ├─ Acquire new lock
  │   ├─ Process queue normally
  │   └─ Release lock
  └─ Return (processed, failed)
```

---

## Data Structures

### DELEGATE File Format (Input)

**File:** `~/.agentic-engineers/{harness}/{session}/queue/incoming/task-{uuid}.yaml`

```yaml
---
handoff_type: DELEGATE
task_id: task-abc-123
agent: engineer
model: claude-haiku-4.5
scope: "Implement feature X with constraints Y and Z (>=15 words)"
context:
  - "File: src/component/module.py (lines 10-50)"
  - "Error: previous attempt failed due to Z"
plan:
  - "Step 1: Read current implementation"
  - "Step 2: Identify root cause"
  - "Step 3: Implement fix"
  - "Step 4: Add tests"
success_criteria:
  - "AC1: Feature works as specified"
  - "AC2: Tests pass"
  - "AC3: No regressions"
created_timestamp: 2026-06-25T14:30:00Z
created_by: user-email@example.com
```

### HANDBACK File Format (Output)

**File:** `~/.agentic-engineers/{harness}/{session}/queue/done/task-{uuid}.yaml`

Appended to original DELEGATE file:

```yaml
---
handoff_type: DELEGATE
task_id: task-abc-123
...
(original DELEGATE content)
...
---
handoff_type: HANDBACK
task_id: task-abc-123
status: success
output: "Feature implemented. Tests pass. No regressions detected."
deliverables:
  - "src/component/module.py (modified)"
  - "tests/test_module.py (new)"
metrics:
  quality: 0.92
  tokens_in: 3200
  tokens_out: 1840
  cost: 0.045
  duration_seconds: 42
model_used: claude-haiku-4.5
completed_timestamp: 2026-06-25T14:31:30Z
```

### Lock File Format

**File:** `~/.agentic-engineers/{harness}/{session}/queue/.lock`

```
12345
2026-06-25T14:30:10Z
claude
```

- Line 1: Process ID (harness)
- Line 2: Timestamp (ISO 8601)
- Line 3: Harness name (for debugging)

### Scheduler Return Format (JSON)

```json
{
  "processed": 3,
  "failed": 0,
  "queue_empty": false,
  "elapsed_seconds": 2.4,
  "session_id": "abc-def-ghi",
  "harness": "claude",
  "tasks": [
    {
      "task_id": "task-1",
      "status": "success",
      "agent": "engineer",
      "duration_seconds": 40
    },
    {
      "task_id": "task-2",
      "status": "success",
      "agent": "engineer",
      "duration_seconds": 45
    },
    {
      "task_id": "task-3",
      "status": "success",
      "agent": "engineer",
      "duration_seconds": 38
    }
  ]
}
```

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Lock file prevents access after crash | Low | High | Stale lock cleanup (age > 300s) |
| Multiple harnesses fight over queue | Low | Medium | File-based lock serialization + tests |
| Scheduler times out, blocks harness | Medium | Medium | 30s timeout + skill wrapper timeout |
| Session ID not set in environment | Medium | High | Clear error message + harness must set env var |
| Queue path not initialized | Low | High | Check/create queue-isolation at scheduler startup |
| DELEGATE file corrupt/unparseable | Low | Low | Quarantine to dedicated folder, log error |
| Agent crash during processing | Low | Medium | Task moved back to incoming/ for retry |
| Performance degradation with many DELEGATEs | Low | Medium | Benchmark per cycle; tune if needed |

---

## SPEC.md Compliance Checklist

- ✅ **No external daemons** — Polling runs inside harness via idle-loop, not as separate service
- ✅ **No system services** — No systemd/launchd required for MVP; optional Phase G-3
- ✅ **No startup hooks** — Idle-loop integration is harness-internal, not settings.json hook
- ✅ **AGENTS with SKILLS** — Orchestrator-scheduler is a SKILL, invoked by harness
- ✅ **All work through queue** — DELEGATEs queue in `queue/incoming/`, processed by scheduler
- ✅ **Session-first model** — Each harness+session pair manages own queue
- ✅ **No external scripts** — All orchestration logic in SKILL (Python), not shell scripts
- ✅ **File-based coordination** — Multi-harness coordination via queue locks, no process messaging

---

## Testing Strategy

### Unit Tests

**File:** `tests/orchestration/test_harness_queue_cooperation.py`

- Test idle-loop detection (idle vs. active)
- Test lock acquisition/release
- Test stale lock cleanup
- Test session ID detection from environment
- Test queue path construction
- Test YAML parsing (corrupt handling)
- Test error scenarios (agent timeout, missing queue)

### Integration Tests

**File:** `tests/integration/test_e2e_queue_processing.py`

- Test single-harness queue processing (1 DELEGATE → done)
- Test single-harness batching (5 DELEGATEs → all done in one cycle)
- Test multi-harness serialization (2 harnesses, shared queue)
- Test error handling (corrupt DELEGATE, agent timeout)
- Test performance (throughput, latency benchmarks)

### Manual Validation

**Scenario 1: Single Harness**

```bash
# Terminal 1: Create DELEGATE
mkdir -p ~/.agentic-engineers/claude/test-session/queue/incoming
cat > ~/.agentic-engineers/claude/test-session/queue/incoming/task-1.yaml <<EOF
handoff_type: DELEGATE
task_id: task-1
agent: engineer
scope: "Test DELEGATE for idle-loop processing"
context: []
plan: []
success_criteria: []
EOF

# Terminal 2: Start Claude Code with test session ID
export CLAUDE_SESSION_ID=test-session
claude-code  # Start harness

# Expected: Within 3-5 minutes, scheduler invokes, processes DELEGATE
# Check: ~/.agentic-engineers/claude/test-session/queue/done/task-1.yaml exists
```

**Scenario 2: Multi-Harness**

```bash
# Terminal 1: Start Claude Code
export CLAUDE_SESSION_ID=shared-session
claude-code

# Terminal 2: Start OpenCode
export COPILOT_SESSION_ID=shared-session
opencode

# Terminal 3: Create 3 DELEGATEs
for i in 1 2 3; do
  cat > ~/.agentic-engineers/claude/shared-session/queue/incoming/task-$i.yaml <<EOF
handoff_type: DELEGATE
task_id: task-$i
agent: engineer
scope: "Test DELEGATE $i"
...
EOF
done

# Expected: Scheduler invokes in one harness, processes all 3
# Second harness skips (lock held), retries next cycle
# All 3 should end up in queue/done/ within 5-10 minutes total
```

---

## Files to Create/Modify

### New Files

1. `src/orchestration/PHASE_G_HARNESS_COOPERATION.md` (this file)
2. `src/harnesses/claude_code/idle_loop.py` — Claude Code idle-loop integration
3. `src/harnesses/opencode/idle_loop.py` — OpenCode idle-loop integration
4. `src/harnesses/copilot_cli/idle_loop.py` — Copilot CLI idle-loop integration
5. `src/harnesses/shared/backoff_poller.py` — shared backoff + file-watch engine (G-2)
6. `tests/orchestration/test_harness_queue_cooperation.py` — Unit tests
7. `tests/integration/test_e2e_queue_processing.py` — Integration tests

> **Note:** `src/harnesses/pi/` and `src/harnesses/cli/` idle-loop integrations are
> not yet wired (π.dev has an empty stub; Codex was recently wired into
> `make install`). Their idle-loop infrastructure is planned for a future release.

### Modified Files

1. `src/skills/orchestrator-scheduler/SKILL.md`
   - Add `--poll-once` flag documentation
   - Add JSON return format specification
   - Add idle-loop integration section

2. `src/skills/orchestrator-scheduler/scripts/orchestrator_scheduler.py`
   - Add `--poll-once` CLI flag
   - Ensure 30s timeout enforcement
   - Add JSON output format

3. `src/skills/orchestrator/scripts/orchestrator_skill.py`
   - Add file-based lock acquisition/release
   - Implement stale lock cleanup
   - Update `poll_queue()` signature to use lock

4. `docs/guides/harness-queue-polling.md` (shipped)
   - Explain harness idle-loop → scheduler SKILL coordination
   - Document multi-harness queue sharing
   - Troubleshooting section

5. Each harness idle-loop module (`src/harnesses/{claude_code,opencode,copilot_cli}/idle_loop.py`)
   - Integrate idle-loop into harness event loop
   - Call `check_idle()` each tick; delegate cadence to `BackoffPoller`

---

## Success Criteria (Phase G-1 MVP)

1. ✅ Harness idle-loop invokes `/orchestrator-scheduler --poll-once` SKILL
2. ✅ Scheduler detects DELEGATE files in `queue/incoming/`
3. ✅ DELEGATEs processed within 5 minutes of arrival
4. ✅ Results appear in `queue/done/` with HANDBACK
5. ✅ Session ID detected correctly from environment
6. ✅ File-based lock prevents concurrent polling
7. ✅ Stale lock cleanup works
8. ✅ Clear, timestamped logs for debugging
9. ✅ No harness crashes due to scheduler failures
10. ✅ SPEC.md compliance verified (no external daemons, AGENTS with SKILLS only)
11. ✅ Documentation updated
12. ✅ End-to-end test passes (single harness, multiple harnesses)

---

## Success Criteria (Phase G-2 Multi-Harness)

1. ✅ Multiple harnesses can share a session queue
2. ✅ Lock serialization prevents concurrent polling
3. ✅ Stale lock cleanup handles harness crashes
4. ✅ All DELEGATEs eventually processed (no starvation)
5. ✅ Performance acceptable (lock overhead <10ms)
6. ✅ Error handling graceful (no data corruption)

---

## Open Questions

### Q1: How do harnesses currently implement idle-loop detection?

**Answer to be determined** by reviewing:
- Claude Code harness idle detection mechanism
- OpenCode harness idle detection mechanism  
- Copilot harness idle detection mechanism

### Q2: Where should idle_loop.py live?

**Resolved (shipped):**
- Shared engine: `src/harnesses/shared/backoff_poller.py`
- Harness-specific implementation: `src/harnesses/{claude_code,opencode,copilot_cli}/idle_loop.py`

### Q3: Should --poll-once be explicit or default?

**Proposal:** Default (no flag needed), with `--daemon` flag for continuous mode.

```bash
# Both equivalent (single cycle)
/orchestrator-scheduler
/orchestrator-scheduler --poll-once

# Continuous daemon mode (Phase G-3)
/orchestrator-scheduler --daemon
```

### Q4: What idle threshold (N seconds) triggers scheduler?

**Proposal:** 180-300 seconds (3-5 minutes).
- Too short: excessive scheduler invocations, CPU overhead
- Too long: slow DELEGATE processing latency
- Baseline: 180 seconds (3 minutes)

### Q5: Can user manually invoke `/orchestrator-scheduler` while idle-loop is active?

**Answer:** Yes. Skill invocation is idempotent. If user invokes manually, scheduler processes queue immediately (or skips if lock held). Idle-loop continues on next cycle.

### Q6: What if user workflow requires low-latency DELEGATE processing?

**Options:**
1. User manually invokes `/orchestrator-scheduler --poll-once`
2. Idle threshold reduced via settings (advanced config)
3. Phase G-3: Daemon mode with file watch (instant wake on new DELEGATE)

---

## Glossary

| Term | Definition |
|------|-----------|
| **Idle-Loop** | Harness background cycle that detects inactivity and invokes scheduler SKILL |
| **Poll Cycle** | One execution of scheduler: acquire lock, process DELEGATEs, release lock |
| **DELEGATE** | Task request (YAML file) queued in `queue/incoming/` |
| **HANDBACK** | Task result (YAML file) in `queue/done/` with outcome and metrics |
| **Session ID** | UUID identifying unique harness session (CLAUDE_SESSION_ID, COPILOT_SESSION_ID) |
| **Harness** | Execution environment (claude, copilot, opencode, cli) |
| **Queue Path** | `~/.agentic-engineers/{harness}/{session}/queue/` |
| **Lock File** | `~/.agentic-engineers/{harness}/{session}/queue/.lock` — prevents concurrent polling |
| **Stale Lock** | Lock file older than 300 seconds; indicates harness crash |
| **Polling Cycle** | Invocation of scheduler SKILL; processes all available DELEGATEs |
| **Multi-Harness Coordination** | Scheduling multiple harnesses to share one session queue via file locks |

---

## References

- [ORCHESTRATOR_AUTO_POLLING.md](ORCHESTRATOR_AUTO_POLLING.md) — Earlier design iteration
- [orchestrator-scheduler SKILL](../skills/orchestrator-scheduler/SKILL.md)
- [orchestrator SKILL](../skills/orchestrator/SKILL.md)
- [DELEGATE/HANDBACK Protocol](../../docs/QUEUE-PROTOCOL.md)
- [SPEC.md - Orchestrator-First Execution Model](../../docs/SPEC.md)
- [Orchestrator Agent](../../src/agents/orchestrator-agent.md)

---

## Version & Changelog

| Date | Author | Status | Version | Notes |
|------|--------|--------|---------|-------|
| 2026-06-25 | Niall Young | Design Phase | 1.0 | Phase G: Harness-Native Queue Cooperation (AGENTS with SKILLS compliant) |
| 2026-06-26 | Niall Young | G-1 + G-2 Complete | 1.1 | Shipped: idle-loop integration across Claude Code, OpenCode, Copilot CLI; `BackoffPoller` continuous in-process polling (5s→600s) + file-watch. 567 harness + 64 infra tests passing. Paths corrected `dist/*/harness/` → `src/harnesses/`. G-3 (external daemon) deferred. |

---

## Next Steps (Executive Handoff)

### Immediate (Day 1)

1. **Review & Approval** (4 hours)
   - Principal Engineer reviews design
   - Feedback incorporated
   - Design approved for implementation

### Week 1-2: Phase G-1 Implementation

1. Analyze existing harness idle-loop implementations
2. Create harness idle-loop integration classes
3. Enhance orchestrator-scheduler with `--poll-once` flag
4. Implement file-based locking in OrchestratorSkill
5. Write unit tests for lock/session detection
6. Conduct end-to-end validation (single harness)
7. Update documentation

### Week 2-3: Phase G-2 Validation

1. Multi-harness coordination testing
2. Stale lock cleanup validation
3. Error handling scenarios
4. Performance benchmarking
5. Stress testing (high DELEGATE volume)

### Week 4: Phase G-3 (Optional)

1. Daemon mode implementation
2. systemd/launchd templates
3. File watch (inotify/FSEvents)
4. Signal handling (SIGTERM/SIGINT)

### Deployment

1. Merge to main branch (Phase G-1 + G-2)
2. Update harness distributions (dist/claude, dist/opencode, dist/copilot)
3. Bump orchestration version to 5.11
4. Release notes: autonomous queue processing enabled

---

**Document prepared for Design Phase Review. Ready for implementation upon approval.**
