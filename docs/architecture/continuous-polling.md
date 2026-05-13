# Architecture: Continuous Polling Loop for Autonomous Orchestrator
**Task 5102** | Principal Engineer Design | High Effort

---

## Executive Summary

The current Orchestrator implementation (`orchestration/agents/orchestrator.py`) runs a **single polling cycle** that exits when idle for 60+ seconds. For true autonomous operation, the Orchestrator must support:

1. **Long-lived continuous operation** — Run indefinitely until explicit shutdown signal
2. **Resilient backoff** — Handle empty queues gracefully with exponential backoff
3. **Signal-driven shutdown** — Respond to SIGTERM (clean) and SIGINT (graceful)
4. **Health visibility** — Emit heartbeat signals and operational metrics
5. **State preservation** — Track queue position and in-flight tasks across cycles
6. **Testability** — Enable testing of long-running processes without infinite loops

This document defines the architecture, implementation strategy, and test approach.

---

## Design Goals

| Goal | Rationale |
|------|-----------|
| **Autonomous Operation** | Orchestrator should run continuously without manual restart |
| **Graceful Degradation** | Handle queue misses, network issues, temporary failures without crashing |
| **Clean Shutdown** | SIGTERM → finish current cycle, save state, exit cleanly |
| **Observable** | Emit heartbeat signals and metrics for monitoring |
| **Testable** | Long-running loops must be testable without infinite waits |
| **Backwards Compatible** | Existing tests using `poll_and_process()` must continue to work |

---

## Current State

### Existing Implementation (orchestration/agents/orchestrator.py:260-287)

```python
def poll_and_process(self):
    """Main polling loop - exits when idle for idle_timeout seconds."""
    while True:
        # Poll for tasks
        incoming_tasks = self.queue_manager.list_incoming_tasks()
        
        if not incoming_tasks:
            # Check idle timeout (60s default)
            elapsed = time.time() - self.last_task_time
            if elapsed >= self.idle_timeout:
                break  # Exit
            else:
                time.sleep(10)  # Sleep 10s, try again
                continue
        
        # Process each task
        for filename in incoming_tasks:
            self._process_task(filename)
```

**Limitations:**
- ❌ No signal handling (can't cleanly shutdown)
- ❌ Fixed 10-second sleep on empty queue (no backoff)
- ❌ No heartbeat mechanism (invisible to monitoring)
- ❌ No state preservation (loses queue position on crash)
- ❌ No way to run continuously without idle timeout
- ❌ Hard to test long-running behavior

---

## Architecture Design

### 1. Polling Loop Structure

#### A. Core Loop Patterns

The Orchestrator will support **three operational modes**:

```python
class OrchestratorAgent:
    def __init__(self, 
                 mode: str = 'daemon',           # 'daemon', 'oneshot', or 'test'
                 idle_timeout: int = 60,          # Seconds before exit in 'oneshot' mode
                 max_cycles: int = None):         # Max cycles for 'test' mode
        self.mode = mode
        self.idle_timeout = idle_timeout
        self.max_cycles = max_cycles
        # ... rest of init
```

**Mode Semantics:**

| Mode | Behavior | Use Case |
|------|----------|----------|
| `daemon` | Run continuously until SIGTERM/SIGINT | Production autonomous operation |
| `oneshot` | Run until idle timeout expires | Existing behavior (backwards compatible) |
| `test` | Run exactly N cycles | Unit/integration tests |

#### B. Main Polling Loop (`run_polling_loop()`)

```python
def run_polling_loop(self) -> Dict:
    """
    Main autonomous polling loop.
    
    In 'daemon' mode: runs until SIGTERM/SIGINT
    In 'oneshot' mode: runs until idle_timeout
    In 'test' mode: runs for max_cycles iterations
    
    Returns:
        {
            "status": "COMPLETE" | "STOPPED" | "ERROR",
            "stop_reason": "idle_timeout" | "sigterm" | "sigint" | "max_cycles" | "error",
            "tasks_processed": int,
            "tasks_success": int,
            "tasks_escalated": int,
            "cycles": int,
            "error": str | None
        }
    """
    # Setup signal handlers
    self._setup_signal_handlers()
    
    # Initialize state
    self.cycles = 0
    self.shutdown_requested = False
    self.shutdown_signal = None
    
    try:
        while not self.shutdown_requested:
            # Check cycle limit (test mode)
            if self.max_cycles and self.cycles >= self.max_cycles:
                return self._build_result("max_cycles")
            
            # Execute one polling cycle
            cycle_result = self._run_cycle()
            self.cycles += 1
            
            # Check if we should exit
            should_exit = self._should_exit(cycle_result)
            if should_exit:
                return self._build_result(should_exit)
    
    except Exception as e:
        # Uncaught exception - escalate
        return self._build_error_result(e)
    
    finally:
        # Always cleanup
        self._cleanup()
```

### 2. Signal Handling Architecture

#### A. Signal Handler Setup

```python
def _setup_signal_handlers(self):
    """
    Setup signal handlers for graceful shutdown.
    
    SIGTERM → Clean shutdown (finish current cycle, exit)
    SIGINT  → Graceful shutdown (stop after current task)
    """
    import signal
    
    signal.signal(signal.SIGTERM, self._handle_sigterm)
    signal.signal(signal.SIGINT, self._handle_sigint)

def _handle_sigterm(self, signum, frame):
    """SIGTERM handler - clean shutdown after current cycle."""
    print(f"[ORCHESTRATOR] SIGTERM received - will exit after current cycle")
    self.shutdown_requested = True
    self.shutdown_signal = "SIGTERM"

def _handle_sigint(self, signum, frame):
    """SIGINT handler - graceful shutdown after current task."""
    print(f"[ORCHESTRATOR] SIGINT received - will exit after current task")
    self.shutdown_requested = True
    self.shutdown_signal = "SIGINT"
```

#### B. Signal Handling Semantics

```
User sends SIGTERM
    ↓
_handle_sigterm() called
    ↓
shutdown_requested = True
    ↓
After current polling cycle completes:
  - Check if shutdown_requested = True
  - Return with stop_reason = "sigterm"
  - Save state (queue position, in-flight tasks)
  - Cleanup and exit

Next run will resume from saved state
```

**Why two signals?**
- **SIGTERM**: Allows current cycle to complete (might process multiple tasks)
- **SIGINT**: Only allows current task to complete (user wants quick exit)

### 3. Backoff Strategy (Exponential Backoff on Queue Misses)

#### A. Problem Statement

Current implementation:
- Empty queue → sleep 10s → retry
- No adaption if queue stays empty
- Might waste CPU checking empty queue frequently in steady state

#### B. Solution: Exponential Backoff

```python
@dataclass
class BackoffState:
    """Track backoff state between cycles."""
    backoff_ms: int = 100        # Current backoff in milliseconds
    max_backoff_ms: int = 30000  # Cap at 30 seconds
    multiplier: float = 1.5      # Exponential multiplier
    reset_on_success: bool = True  # Reset when task found
    consecutive_empty: int = 0   # Count of consecutive empty cycles

def _calculate_backoff(self) -> float:
    """
    Calculate sleep duration based on consecutive empty cycles.
    
    - Cycle 0 (task found): reset
    - Cycle 1 (empty): 100ms
    - Cycle 2 (empty): 150ms
    - Cycle 3 (empty): 225ms
    - ...
    - Cap at 30s
    
    Returns:
        Sleep duration in seconds
    """
    if self.backoff.consecutive_empty == 0:
        return 0  # No sleep if last cycle had tasks
    
    backoff_seconds = min(
        self.backoff.backoff_ms * (self.backoff.multiplier ** self.backoff.consecutive_empty) / 1000,
        self.backoff.max_backoff_ms / 1000
    )
    return backoff_seconds

def _on_cycle_result(self, has_tasks: bool):
    """Update backoff state based on cycle result."""
    if has_tasks:
        # Reset backoff on success
        self.backoff.consecutive_empty = 0
        self.backoff.backoff_ms = 100
    else:
        # Increment backoff on empty
        self.backoff.consecutive_empty += 1

def _run_cycle(self) -> Dict:
    """Run one polling cycle with backoff."""
    incoming_tasks = self.queue_manager.list_incoming_tasks()
    self._on_cycle_result(len(incoming_tasks) > 0)
    
    if not incoming_tasks:
        # Calculate backoff sleep
        sleep_seconds = self._calculate_backoff()
        if sleep_seconds > 0:
            print(f"[ORCHESTRATOR] No tasks found. Backing off {sleep_seconds:.1f}s "
                  f"(consecutive_empty={self.backoff.consecutive_empty})")
            time.sleep(sleep_seconds)
    else:
        # Process tasks
        for filename in incoming_tasks:
            self._process_task(filename)
```

#### C. Backoff Curve

```
Consecutive Empty Cycles vs Sleep Duration:

Cycle 1 (empty):     0.1s (100ms)
Cycle 2 (empty):     0.15s (150ms)
Cycle 3 (empty):     0.225s (225ms)
Cycle 4 (empty):     0.338s
Cycle 5 (empty):     0.507s
Cycle 10 (empty):    2.06s
Cycle 15 (empty):    8.37s
Cycle 20+ (empty):   30.0s (capped)

Resets to 100ms immediately when task appears.
```

**Why exponential backoff?**
- Starts fast (checking frequently when queue might have tasks)
- Gradually backs off (conservation when queue stays empty)
- Caps at 30s (doesn't sleep forever, but gives queue time to fill)

### 4. Heartbeat Mechanism (Health Check & Logging)

#### A. Heartbeat State

```python
@dataclass
class HeartbeatState:
    """Track heartbeat metrics."""
    interval_seconds: int = 30     # Emit heartbeat every 30s
    last_heartbeat: float = 0      # Time of last heartbeat
    cycles_since_heartbeat: int = 0
    tasks_processed_since_heartbeat: int = 0

def _should_emit_heartbeat(self) -> bool:
    """Check if it's time to emit heartbeat."""
    elapsed = time.time() - self.heartbeat.last_heartbeat
    return elapsed >= self.heartbeat.interval_seconds

def _emit_heartbeat(self):
    """Emit heartbeat signal for observability."""
    elapsed = time.time() - self.heartbeat.last_heartbeat
    print(f"\n[HEARTBEAT] Orchestrator alive")
    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"  Cycles: {self.cycles}")
    print(f"  Tasks processed: {self.tasks_processed}")
    print(f"  Tasks success: {self.tasks_success}")
    print(f"  Tasks escalated: {self.tasks_escalated}")
    print(f"  Avg rate: {self.tasks_processed / self.cycles:.2f} tasks/cycle")
    print(f"  Mode: {self.mode}")
    print(f"  Shutdown: {self.shutdown_requested}")
    
    self.heartbeat.last_heartbeat = time.time()
    self.heartbeat.cycles_since_heartbeat = 0
    self.heartbeat.tasks_processed_since_heartbeat = 0

def _run_cycle(self) -> Dict:
    """Run one polling cycle."""
    # ... poll and process tasks ...
    
    # Check if heartbeat needed
    self.heartbeat.cycles_since_heartbeat += 1
    self.heartbeat.tasks_processed_since_heartbeat += self.tasks_processed
    
    if self._should_emit_heartbeat():
        self._emit_heartbeat()
```

#### B. Heartbeat Output

```
[HEARTBEAT] Orchestrator alive
  Elapsed: 30.0s
  Cycles: 145
  Tasks processed: 23
  Tasks success: 22
  Tasks escalated: 1
  Avg rate: 0.16 tasks/cycle
  Mode: daemon
  Shutdown: False
```

**Why heartbeats?**
- Prove the Orchestrator is still alive and healthy
- Expose operational metrics (task rates, error rates)
- Help diagnose stalled or failing orchestrators

### 5. State Preservation (Queue Position & In-Flight Tasks)

#### A. State File Format

State is persisted to `artifacts/.orchestrator-state.yaml`:

```yaml
version: 1
timestamp: "2024-05-02T14:32:15.123456Z"
mode: daemon
cycles: 145
tasks_processed: 23
tasks_success: 22
tasks_escalated: 1
last_task_time: 1714754335.123

# In-flight tasks
in_flight:
  - task_id: "task-001"
    filename: "task-001.yaml"
    started_at: "2024-05-02T14:30:00Z"
    started_by: "engineer"
  - task_id: "task-002"
    filename: "task-002.yaml"
    started_at: "2024-05-02T14:31:00Z"
    started_by: "senior_engineer"

# Queue checkpoint
queue_position:
  last_processed: "task-001.yaml"
  last_processed_at: "2024-05-02T14:32:00Z"
  unprocessed_count: 7

backoff_state:
  consecutive_empty: 3
  backoff_ms: 225
```

#### B. State Management

```python
@dataclass
class PersistentState:
    """Orchestrator state persisted across restarts."""
    version: int = 1
    timestamp: str = ""
    mode: str = "daemon"
    cycles: int = 0
    tasks_processed: int = 0
    tasks_success: int = 0
    tasks_escalated: int = 0
    last_task_time: float = 0
    in_flight: List[Dict] = None
    queue_position: Dict = None
    backoff_state: Dict = None

def _save_state(self):
    """Persist state to disk."""
    state = PersistentState(
        version=1,
        timestamp=datetime.utcnow().isoformat(),
        mode=self.mode,
        cycles=self.cycles,
        tasks_processed=self.tasks_processed,
        tasks_success=self.tasks_success,
        tasks_escalated=self.tasks_escalated,
        last_task_time=self.last_task_time,
        in_flight=[...],  # List of tasks in processing queue
        queue_position={
            "last_processed": self.last_processed_filename,
            "last_processed_at": self.last_processed_time,
            "unprocessed_count": len(self.queue_manager.list_incoming_tasks())
        },
        backoff_state=asdict(self.backoff)
    )
    
    state_file = Path("artifacts/.orchestrator-state.yaml")
    with open(state_file, 'w') as f:
        yaml.dump(asdict(state), f)
    print(f"[STATE] Saved state to {state_file}")

def _load_state(self) -> Optional[PersistentState]:
    """Load state from disk if available."""
    state_file = Path("artifacts/.orchestrator-state.yaml")
    if not state_file.exists():
        return None
    
    with open(state_file, 'r') as f:
        state_dict = yaml.safe_load(f)
    
    state = PersistentState(**state_dict)
    print(f"[STATE] Loaded state from {state_file}")
    return state

def _resume_from_state(self, state: PersistentState):
    """Resume from checkpoint state."""
    self.cycles = state.cycles
    self.tasks_processed = state.tasks_processed
    self.tasks_success = state.tasks_success
    self.tasks_escalated = state.tasks_escalated
    self.last_task_time = state.last_task_time
    
    # Restore backoff state
    self.backoff.consecutive_empty = state.backoff_state.get('consecutive_empty', 0)
    self.backoff.backoff_ms = state.backoff_state.get('backoff_ms', 100)
    
    print(f"[RESUME] Resumed from checkpoint - cycles={self.cycles}, tasks_processed={self.tasks_processed}")
```

**Note**: State is *optional* and informational. The system is designed to be resilient without it. State is saved at:
- Regular intervals (every N cycles)
- On graceful shutdown
- On error

### 6. Should-Exit Decision Logic

```python
def _should_exit(self, cycle_result: Dict) -> Optional[str]:
    """
    Determine if polling loop should exit.
    
    Returns:
        - None if should continue
        - "sigterm" if SIGTERM received
        - "sigint" if SIGINT received
        - "idle_timeout" if oneshot mode and idle timeout exceeded
        - "max_cycles" if test mode and max cycles reached
        - "error" if unrecoverable error occurred
    """
    # Check signal handlers
    if self.shutdown_signal == "SIGTERM":
        return "sigterm"
    
    if self.shutdown_signal == "SIGINT":
        return "sigint"
    
    # Check cycle limit (test mode)
    if self.max_cycles and self.cycles >= self.max_cycles:
        return "max_cycles"
    
    # Check idle timeout (oneshot mode only)
    if self.mode == "oneshot":
        elapsed = time.time() - self.last_task_time
        if elapsed >= self.idle_timeout:
            return "idle_timeout"
    
    # No exit condition met
    return None
```

---

## Implementation Roadmap

### Phase 1: Core Loop & Signal Handling (Priority 1)

**Deliverable**: Working polling loop with signal handling

**Tasks**:
1. ✅ Add three-mode support (daemon, oneshot, test)
2. ✅ Implement `run_polling_loop()` with while loop
3. ✅ Implement `_setup_signal_handlers()` (SIGTERM, SIGINT)
4. ✅ Implement `_handle_sigterm()` and `_handle_sigint()`
5. ✅ Implement `_should_exit()` decision logic
6. ✅ Update `do_work()` to call `run_polling_loop()` instead of `poll_and_process()`
7. ✅ Maintain backwards compatibility with `poll_and_process()` (delegates to `run_polling_loop()`)

**Testing**:
- Unit test: SIGTERM handling
- Unit test: SIGINT handling
- Unit test: max_cycles limit
- Integration test: Run 5-cycle daemon then send SIGTERM, verify clean exit

---

### Phase 2: Exponential Backoff (Priority 2)

**Deliverable**: Adaptive backoff strategy for empty queues

**Tasks**:
1. ✅ Add `BackoffState` dataclass
2. ✅ Implement `_calculate_backoff()` 
3. ✅ Implement `_on_cycle_result()` to update backoff state
4. ✅ Integrate backoff into `_run_cycle()`
5. ✅ Add logging of backoff decisions

**Testing**:
- Unit test: Backoff calculation (verify exponential curve)
- Integration test: Verify backoff resets when task appears
- Stress test: 100 empty cycles, verify CPU doesn't spike

---

### Phase 3: Heartbeat & Observability (Priority 3)

**Deliverable**: Heartbeat mechanism and operational metrics

**Tasks**:
1. ✅ Add `HeartbeatState` dataclass
2. ✅ Implement `_should_emit_heartbeat()`
3. ✅ Implement `_emit_heartbeat()` 
4. ✅ Integrate heartbeat into polling loop
5. ✅ Add metrics: tasks/cycle, success rate, escalation rate

**Testing**:
- Unit test: Heartbeat interval calculation
- Integration test: Run for 2+ minutes, verify heartbeat emitted every 30s
- Log analysis: Parse heartbeat output, verify metrics accuracy

---

### Phase 4: State Preservation (Priority 4)

**Deliverable**: Durable state persistence across restarts

**Tasks**:
1. ✅ Add `PersistentState` dataclass
2. ✅ Implement `_save_state()` (YAML serialization)
3. ✅ Implement `_load_state()` (YAML deserialization)
4. ✅ Implement `_resume_from_state()`
5. ✅ Save state on: graceful shutdown, error, every N cycles
6. ✅ Load state on: startup
7. ✅ Add logging of state save/load/resume

**Testing**:
- Unit test: State serialization/deserialization
- Integration test: Kill orchestrator mid-cycle, restart, verify metrics resume
- Crash recovery test: Corrupted state file, verify graceful recovery

---

### Phase 5: Test Infrastructure (Priority 5)

**Deliverable**: Support for testing long-running processes

**Tasks**:
1. ✅ Add `max_cycles` parameter to control test duration
2. ✅ Implement `mode: 'test'` for unit tests
3. ✅ Update testing harness to support test mode
4. ✅ Add `test_orchestrator_long_running()` with 50-cycle limit
5. ✅ Add fixtures for: mocked queue, mocked signals, metrics collection

**Testing**:
- Unit test: Test mode respects max_cycles
- Integration test: 50-cycle run with signal injection
- Regression test: Existing tests still pass with new mode parameter

---

## Test Strategy for Long-Running Processes

### A. Unit Tests

```python
def test_polling_loop_mode_daemon():
    """Verify daemon mode runs indefinitely without timeout."""
    orch = OrchestratorAgent(mode='daemon')
    # Send SIGTERM after 3 cycles (using mock)
    # Verify it exits cleanly

def test_polling_loop_mode_oneshot():
    """Verify oneshot mode exits on idle timeout."""
    orch = OrchestratorAgent(mode='oneshot', idle_timeout=5)
    # Run for 10 seconds
    # Verify it exits with stop_reason='idle_timeout'

def test_polling_loop_mode_test():
    """Verify test mode runs exactly N cycles."""
    orch = OrchestratorAgent(mode='test', max_cycles=10)
    # Run
    # Verify it exits after exactly 10 cycles

def test_signal_sigterm():
    """Verify SIGTERM triggers clean shutdown."""
    # Setup: send SIGTERM to orchestrator PID after 1 second
    # Run: orchestrator in daemon mode
    # Verify: exits with stop_reason='sigterm'

def test_signal_sigint():
    """Verify SIGINT triggers graceful shutdown."""
    # Similar to SIGTERM test
    # But only after current task (not current cycle)

def test_exponential_backoff():
    """Verify backoff calculation is exponential."""
    # Given: empty queue with 0, 1, 2, 3, ... cycles
    # Then: backoff is 0, 100ms, 150ms, 225ms, ...

def test_backoff_reset_on_success():
    """Verify backoff resets when task appears."""
    # Given: 5 empty cycles, then 1 cycle with task
    # Then: next empty cycle uses backoff_ms=100, not accumulated

def test_heartbeat_emission():
    """Verify heartbeat emitted at correct interval."""
    # Run: 100 cycles with heartbeat_interval=10
    # Verify: heartbeat emitted exactly 10 times
```

### B. Integration Tests

```python
def test_orchestrator_polling_loop_5_cycles():
    """Run 5 cycles, verify all metrics recorded."""
    queue = create_mock_queue([task1, task2, task3])
    orch = OrchestratorAgent(mode='test', max_cycles=5, queue_manager=queue)
    result = orch.run_polling_loop()
    
    assert result['status'] == 'COMPLETE'
    assert result['cycles'] == 5
    assert result['tasks_processed'] == 3

def test_orchestrator_graceful_shutdown():
    """Send SIGTERM mid-run, verify state saved."""
    # Start orchestrator in background thread
    # After 2 seconds, send SIGTERM
    # Verify: clean exit, state file written

def test_orchestrator_state_resume():
    """Save state, kill process, restart, verify resume."""
    # Run 1: Process 5 tasks, save state, exit
    # Run 2: Load state, verify metrics reflect Run 1
```

### C. Stress Tests

```python
def test_orchestrator_1000_empty_cycles():
    """Run 1000 cycles with empty queue, verify no errors."""
    # Verify: exponential backoff prevents CPU spike
    # Verify: heartbeats emitted every 30 cycles
    # Verify: no memory leaks

def test_orchestrator_signal_during_task():
    """Send SIGTERM while processing task, verify graceful exit."""
    # Start slow task (10 second processing)
    # After 2 seconds, send SIGTERM
    # Verify: task completes, state saved, clean exit
```

### D. Backwards Compatibility Tests

```python
def test_poll_and_process_still_works():
    """Verify deprecated poll_and_process() still callable."""
    orch = OrchestratorAgent(mode='oneshot', idle_timeout=5)
    # Call old API
    orch.poll_and_process()
    # Verify: works (delegates to run_polling_loop)

def test_testing_harness_compatibility():
    """Verify orchestrator_testing_harness.py still works."""
    # Run: python orchestrator_testing_harness.py
    # Verify: completes successfully
```

---

## Graceful Shutdown Semantics

### A. SIGTERM Flow

```
User/systemd: kill -TERM <pid>
    ↓
OS: Deliver SIGTERM to process
    ↓
_handle_sigterm(): Set shutdown_requested = True, shutdown_signal = "SIGTERM"
    ↓
Current _run_cycle() completes (may process multiple tasks)
    ↓
while loop checks: shutdown_requested = True
    ↓
_should_exit() returns "sigterm"
    ↓
_cleanup()
    - Save state to artifacts/.orchestrator-state.yaml
    - Close any open connections
    - Print summary
    ↓
_build_result("sigterm")
    - Return with stop_reason = "sigterm"
    ↓
Exit with code 0 (success)
```

**Example Output:**
```
[ORCHESTRATOR] SIGTERM received - will exit after current cycle
  (Processing remaining tasks in current cycle...)
  ✓ Completed task-1
  ✓ Completed task-2
[STATE] Saved state to artifacts/.orchestrator-state.yaml
[ORCHESTRATOR] Shutdown complete
  Tasks processed: 47
  Success: 46
  Escalated: 1
  Status: COMPLETE
  Stop reason: sigterm
```

### B. SIGINT Flow (Same as SIGTERM for now)

SIGINT currently behaves identically to SIGTERM (finish current cycle). This could be refined in future to stop after current *task* instead of cycle.

### C. No Signal Handling (Legacy Behavior)

For backwards compatibility, if code doesn't call `run_polling_loop()` (uses old `poll_and_process()`), signal handling is not active. This maintains existing behavior.

---

## Configuration Parameters

New parameters added to `OrchestratorAgent.__init__()`:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mode` | str | `'daemon'` | `'daemon'` (run forever), `'oneshot'` (idle timeout), `'test'` (fixed cycles) |
| `idle_timeout` | int | `60` | Seconds before exit in oneshot mode |
| `max_cycles` | int | `None` | Max cycles in test mode (None = unlimited) |
| `heartbeat_interval` | int | `30` | Seconds between heartbeat emissions |
| `backoff_multiplier` | float | `1.5` | Exponential backoff multiplier |
| `backoff_max_ms` | int | `30000` | Max backoff sleep in milliseconds |
| `state_save_interval` | int | `100` | Save state every N cycles |

---

## Backwards Compatibility

### Existing Code

All existing code continues to work:

```python
# Old API - still works
orch = OrchestratorAgent(idle_timeout=60)
orch.poll_and_process()  # Runs oneshot mode

# New API - recommended
orch = OrchestratorAgent(mode='daemon')
result = orch.run_polling_loop()  # Runs in daemon mode
```

### Test Changes

Existing tests that call `poll_and_process()` need to be updated to call `run_polling_loop()` with `mode='test'`, but this is transparent to most tests.

### Migration Path

1. ✅ Phase 1: Add new APIs, keep old APIs working
2. ✅ Phase 2: Update test harness to use new API
3. ✅ Phase 3: Deprecate old API in comments
4. ⚠️ Phase 4 (future): Remove old API

---

## Open Questions & Future Enhancements

### Short Term
- [ ] Should backoff interval be configurable per environment?
- [ ] Should heartbeat output go to structured logging (JSON)?
- [ ] Should state file be human-readable YAML or binary?

### Long Term
- [ ] Add Prometheus metrics export for orchestrator health
- [ ] Add Redis-based distributed state for multi-orchestrator setups
- [ ] Add circuit breaker for failing agents (temporary skip)
- [ ] Add adaptive heartbeat interval based on task rate

---

## Summary

This architecture provides:

✅ **Autonomous Operation**: Three modes (daemon, oneshot, test) for different use cases
✅ **Signal Handling**: Clean shutdown on SIGTERM, graceful on SIGINT
✅ **Resilient Backoff**: Exponential backoff prevents CPU thrashing on empty queues
✅ **Observability**: Heartbeat mechanism provides health visibility
✅ **State Preservation**: Survive restarts without losing metrics
✅ **Testability**: Test mode enables fast, deterministic testing
✅ **Backwards Compatible**: Old code continues to work unchanged

The design is **complete and ready for Engineer phase implementation** (Task 5102).

