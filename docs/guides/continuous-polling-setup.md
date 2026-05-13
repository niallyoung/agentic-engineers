# Implementation Roadmap: Continuous Polling Loop Architecture (Task 5102)

## Overview

This document provides the detailed implementation roadmap for the continuous polling loop architecture designed for the Orchestrator agent. It breaks down the five-phase approach into actionable tasks with clear dependencies, testing requirements, and acceptance criteria.

**Estimated effort**: 40-60 engineer hours spread across 5 phases  
**Duration**: 4-6 weeks with parallel phase execution where possible  
**Risk level**: Low (backwards compatible design minimizes breaking changes)

---

## Phase 1: Core Polling Loop & Signal Handling (Priority 1)

**Objective**: Implement the foundational polling loop with graceful shutdown via signals.

**Deliverable**: `run_polling_loop()` method supporting daemon/oneshot/test modes with complete signal handling.

### Tasks

1. **Create run_polling_loop() method skeleton**
   - Location: `orchestration/agents/orchestrator.py`
   - Signature: `def run_polling_loop(self, mode='oneshot', idle_timeout=60, max_cycles=None)`
   - Accept modes: 'daemon', 'oneshot', 'test'
   - Validate mode parameter
   - Set instance variables: `self.polling_mode`, `self.max_cycles`
   - Acceptance criteria:
     - Method exists and accepts all parameters
     - ValueError raised for invalid modes
     - Parameters stored in instance

2. **Implement signal handler setup**
   - Create `_setup_signal_handlers()` method
   - Register SIGTERM: sets `self._shutdown_requested = True`
   - Register SIGINT: sets `self._shutdown_requested = True` with context preserved
   - Store original handlers to allow restoration
   - Acceptance criteria:
     - Signals can be sent to process and handled
     - Process doesn't crash on SIGTERM/SIGINT
     - Handlers restore original behavior on cleanup

3. **Implement basic polling loop structure**
   - Main loop: `while True:`
   - Check mode-specific exit conditions:
     - daemon: never exit (loop forever)
     - oneshot: exit if idle > idle_timeout
     - test: exit if cycles >= max_cycles
   - Increment cycle counter: `self.polling_cycles += 1`
   - Check `self._shutdown_requested` after each cycle
   - Exit cleanly if shutdown requested
   - Acceptance criteria:
     - Loop runs indefinitely in daemon mode
     - Loop exits after idle_timeout in oneshot mode
     - Loop exits after max_cycles in test mode
     - Loop exits cleanly when signals received

4. **Integrate with existing poll_and_process()**
   - Keep poll_and_process() for backwards compatibility
   - Delegate: `return self.run_polling_loop(mode='oneshot', idle_timeout=idle_timeout, max_cycles=None)`
   - Ensure all existing tests continue to pass
   - Acceptance criteria:
     - Existing code calling poll_and_process() works unchanged
     - No test failures in orchestrator_testing_harness.py
     - Legacy API preserved exactly

5. **Add debug logging for loop lifecycle**
   - Log startup: mode, idle_timeout, max_cycles, initial backoff
   - Log cycle: cycle number, time elapsed, queue size
   - Log shutdown: reason, cycles completed, duration
   - Use structured logging (include timestamp, cycle_num in all messages)
   - Acceptance criteria:
     - Logs show complete lifecycle of polling loop
     - Can trace execution with logs alone
     - No sensitive data in logs

6. **Test signal handling in isolation**
   - Unit test: test_signal_handling_sigterm()
     - Start loop in daemon mode
     - Send SIGTERM after 2 cycles
     - Verify graceful shutdown within 1 cycle
   - Unit test: test_signal_handling_sigint()
     - Start loop in daemon mode
     - Send SIGINT after 2 cycles
     - Verify graceful shutdown within 1 cycle
   - Unit test: test_mode_exit_logic()
     - Test daemon mode never exits
     - Test oneshot mode exits after idle_timeout
     - Test test mode exits after max_cycles
   - Acceptance criteria:
     - All 3 unit tests pass
     - Coverage > 90% for signal handling code

7. **Document API and usage patterns**
   - Update docstring for `run_polling_loop()`
   - Update docstring for `poll_and_process()`
   - Add code examples in AGENTS.md showing how to use new API
   - Acceptance criteria:
     - API documentation is clear and complete
     - Usage examples show all three modes
     - Readers can understand backwards compatibility

**Phase 1 Exit Criteria**:
- `run_polling_loop()` fully functional with all three modes
- Signal handling verified and tested
- `poll_and_process()` correctly delegates with backwards compatibility
- All Phase 1 tests passing (7 tests minimum)
- No new test failures in existing test suite

---

## Phase 2: Exponential Backoff Strategy (Priority 2)

**Objective**: Implement intelligent backoff to prevent CPU thrashing and reduce queue polling load.

**Deliverable**: Exponential backoff mechanism integrated into polling loop with configurable parameters.

**Dependencies**: Phase 1 must be complete (requires working polling loop)

### Tasks

1. **Define backoff state and parameters**
   - Instance variables needed:
     - `self.backoff_base_ms = 100` (milliseconds)
     - `self.backoff_multiplier = 1.5` (growth factor)
     - `self.backoff_max_ms = 30000` (milliseconds, 30 seconds)
     - `self.consecutive_empty_cycles = 0` (counter)
   - Environment variable support: `ORCHESTRATOR_BACKOFF_BASE_MS`, `ORCHESTRATOR_BACKOFF_MULTIPLIER`, `ORCHESTRATOR_BACKOFF_MAX_MS`
   - Acceptance criteria:
     - Parameters initialized in __init__()
     - Environment variables override defaults
     - Invalid values raise ValueError with helpful message

2. **Implement backoff calculation function**
   - Method: `_calculate_backoff_seconds()`
   - Formula: `min(base_ms * (multiplier ^ consecutive_empty_cycles) / 1000, max_ms / 1000)`
   - Return type: float (seconds)
   - Handle edge cases:
     - consecutive_empty_cycles = 0 → return base_ms / 1000
     - Large exponents don't overflow (Python handles big floats)
     - Always return <= max_ms / 1000
   - Acceptance criteria:
     - Function calculates correct values per formula
     - Never exceeds max backoff
     - Returns float suitable for time.sleep()

3. **Integrate sleep with backoff**
   - Modify polling loop after queue check
   - If queue empty AND not shutdown_requested:
     - Calculate backoff: `backoff_secs = self._calculate_backoff_seconds()`
     - Increment counter: `self.consecutive_empty_cycles += 1`
     - Sleep: `time.sleep(backoff_secs)` (interruptible by signals)
   - If queue has tasks:
     - Reset counter: `self.consecutive_empty_cycles = 0`
     - No sleep (process immediately)
   - Acceptance criteria:
     - Loop sleeps when queue empty
     - Sleep duration grows exponentially
     - Counter resets when task found

4. **Handle signal interruption during sleep**
   - Signals interrupt sleep() naturally (not blocking in Python)
   - After wake-up (signal or timeout), check `self._shutdown_requested`
   - Exit loop if shutdown requested
   - Continue to next cycle otherwise
   - Acceptance criteria:
     - SIGTERM/SIGINT while sleeping causes exit
     - No extra delays introduced
     - Loop responsive to signals

5. **Test backoff calculation**
   - Unit test: test_backoff_calculation()
     - Verify formula with inputs: 0, 1, 2, 5, 10 consecutive empty cycles
     - Check values: ~100ms, ~150ms, ~225ms, ~760ms, ~2437ms
     - Verify cap at 30s
   - Unit test: test_backoff_parameters_from_env()
     - Set environment variables
     - Verify parameters loaded correctly
     - Verify invalid values raise exceptions
   - Acceptance criteria:
     - Backoff calculation tested thoroughly
     - Math verified against formula
     - Environment variables work

6. **Test backoff behavior in loop**
   - Integration test: test_backoff_in_polling_loop()
     - Start loop in test mode (max_cycles=5)
     - Ensure queue stays empty
     - Measure sleep times between cycles
     - Verify exponential growth
   - Stress test: test_backoff_under_load()
     - Simulate rapid task creation and completion
     - Verify counter resets quickly
     - Verify no CPU thrashing
   - Acceptance criteria:
     - Backoff actually applied in loop
     - Sleep durations match calculations
     - Reset behavior verified

7. **Document backoff strategy and tuning**
   - Update docs/architecture-continuous-polling-5102.md with final parameters
   - Add troubleshooting section: "Backoff too aggressive?" / "Not responsive enough?"
   - Add tuning guide with examples
   - Update AGENTS.md with backoff explanation
   - Acceptance criteria:
     - Users can understand and tune backoff
     - Tuning guide provides specific examples
     - Performance implications documented

**Phase 2 Exit Criteria**:
- Backoff calculation correct and tested
- Backoff integrated into polling loop
- Exponential growth verified in practice
- Signal handling still works during sleep
- All Phase 2 tests passing (7 tests minimum)
- No performance regressions in existing tests

---

## Phase 3: Heartbeat & Observability (Priority 3)

**Objective**: Emit operational metrics regularly to enable monitoring and debugging.

**Deliverable**: Heartbeat emission with configurable interval and structured metrics.

**Dependencies**: Phase 1 must be complete (requires working polling loop)

### Tasks

1. **Define heartbeat metrics structure**
   - Metrics to include:
     - `timestamp`: ISO 8601 format
     - `mode`: current polling mode
     - `cycles_completed`: total cycles since startup
     - `tasks_processed`: total tasks this session
     - `tasks_succeeded`: count of successful tasks
     - `tasks_escalated`: count of escalated tasks
     - `avg_task_rate`: tasks/minute
     - `current_backoff_ms`: current sleep duration
     - `queue_size`: current queue depth (if available)
   - Format: structured dict or JSON string
   - Acceptance criteria:
     - All metrics defined and calculable
     - Timestamp accurate and parseable
     - Rates calculated reliably

2. **Implement heartbeat emission mechanism**
   - Method: `_emit_heartbeat()`
   - Calculate metrics based on instance state
   - Output format: structured (TBD: JSON or YAML)
   - Output destination: TBD (stdout, file, logging, metrics system)
   - Configurable interval: `self.heartbeat_interval_seconds = 30`
   - Acceptance criteria:
     - Heartbeat can be emitted on demand
     - Metrics calculated correctly
     - Format is consistent and parseable

3. **Integrate heartbeat into polling loop**
   - Track last heartbeat time: `self._last_heartbeat_time = None`
   - After each cycle, check: `time.time() - self._last_heartbeat_time > self.heartbeat_interval_seconds`
   - Emit heartbeat if interval exceeded
   - Update `self._last_heartbeat_time`
   - Acceptance criteria:
     - Heartbeats emitted regularly
     - Interval respected (within 1 second tolerance)
     - No performance impact on loop

4. **Add heartbeat configuration**
   - Parameter: `heartbeat_interval_seconds` in `run_polling_loop()`
   - Default: 30 seconds
   - Environment variable: `ORCHESTRATOR_HEARTBEAT_INTERVAL_SECONDS`
   - Allow disabling: heartbeat_interval_seconds = None or 0
   - Acceptance criteria:
     - Configurable via parameter and env var
     - Can be disabled
     - Defaults are sensible

5. **Test heartbeat emission**
   - Unit test: test_heartbeat_metrics_structure()
     - Call _emit_heartbeat()
     - Verify all expected metrics present
     - Verify data types correct
   - Integration test: test_heartbeat_timing()
     - Start loop in test mode with max_cycles=10
     - Set heartbeat_interval_seconds = 0.5
     - Verify heartbeat emitted approximately every 0.5s
     - Count heartbeats (should be ~10)
   - Acceptance criteria:
     - Heartbeat structure complete and correct
     - Timing verified within 10% tolerance
     - Can parse heartbeat output

6. **Integrate with observability system** (TBD)
   - Output destination TBD: investigate current observability (see open questions)
   - Likely options:
     - Structured logging (JSON to stdout)
     - Prometheus metrics
     - CloudWatch metrics
     - Metrics system (if one exists)
   - Choice depends on existing infrastructure
   - Acceptance criteria:
     - Heartbeat consumed by observability system
     - Metrics visible in monitoring dashboard
     - No integration bugs

7. **Document heartbeat and metrics**
   - Update docs/architecture-continuous-polling-5102.md
   - Document each metric and its meaning
   - Document output format and parsing
   - Add example heartbeats
   - Acceptance criteria:
     - Users understand heartbeat purpose
     - Metrics are self-documenting
     - Output format well-defined

**Phase 3 Exit Criteria**:
- Heartbeat mechanism implemented and integrated
- All metrics calculated and emitted correctly
- Timing verified
- Observability system integrated
- All Phase 3 tests passing (7 tests minimum)
- Heartbeats visible in logs/metrics

---

## Phase 4: State Preservation & Recovery (Priority 4)

**Objective**: Persist orchestrator state to enable recovery and debugging across restarts.

**Deliverable**: Checkpoint system that saves and restores orchestrator state.

**Dependencies**: Phase 1 and Phase 2 should be complete (optional, but recommended)

### Tasks

1. **Define checkpoint file format**
   - Format: YAML (human-readable, debuggable)
   - Location: `artifacts/.orchestrator-state.yaml`
   - Schema:
     ```yaml
     version: "1.0"
     timestamp: "2024-01-15T14:30:00Z"
     mode: "daemon"
     metrics:
       cycles_completed: 1234
       tasks_processed: 567
       tasks_succeeded: 560
       tasks_escalated: 7
     backoff_state:
       consecutive_empty_cycles: 3
       current_backoff_ms: 337.5
     in_flight_tasks:
       - id: "task-001"
         started_at: "2024-01-15T14:29:45Z"
         status: "processing"
     ```
   - Acceptance criteria:
     - Schema well-defined
     - All important state captured
     - YAML valid and parseable

2. **Implement checkpoint save functionality**
   - Method: `_save_checkpoint()`
   - Collect current state: metrics, backoff, in-flight tasks
   - Create YAML document
   - Write atomically to `artifacts/.orchestrator-state.yaml`
   - Handle missing artifacts/ directory
   - Acceptance criteria:
     - Checkpoint file created successfully
     - File contains valid YAML
     - All state captured
     - Atomic write (no partial files)

3. **Implement checkpoint load functionality**
   - Method: `_load_checkpoint()`
   - Read YAML from `artifacts/.orchestrator-state.yaml`
   - Parse and validate schema
   - Restore state: metrics, backoff, in-flight task list
   - Handle missing/corrupt files gracefully
   - Acceptance criteria:
     - Checkpoint read successfully
     - State restored correctly
     - Handles missing/corrupt files
     - No exceptions raised

4. **Integrate checkpoint with polling loop**
   - Save checkpoint after each cycle (or every N cycles to reduce I/O)
   - Load checkpoint on startup if available
   - Log checkpoint operations
   - Acceptance criteria:
     - Checkpoint saved regularly
     - Checkpoint loaded on startup
     - No performance impact

5. **Test checkpoint save/load cycle**
   - Unit test: test_checkpoint_schema()
     - Generate checkpoint
     - Verify YAML structure
     - Verify all fields present
   - Unit test: test_checkpoint_roundtrip()
     - Save state to checkpoint
     - Load state from checkpoint
     - Verify state matches (for all fields)
   - Unit test: test_checkpoint_recovery()
     - Start loop, run 5 cycles, save state
     - Simulate crash, restart
     - Verify state restored, loop continues
   - Acceptance criteria:
     - Save/load cycle preserves all state
     - Recovery works after simulated crash
     - No data loss

6. **Handle checkpoint corruption**
   - If file unreadable: log warning, continue with zeros
   - If YAML invalid: log error, continue with zeros
   - If schema version mismatch: log info, continue with zeros
   - Never crash due to checkpoint issues
   - Acceptance criteria:
     - System resilient to corrupt checkpoints
     - Appropriate logging at each error level
     - No data loss on recovery

7. **Document state preservation strategy**
   - Update docs/architecture-continuous-polling-5102.md
   - Explain why checkpoint is optional
   - Document recovery procedure
   - Show example checkpoint file
   - Acceptance criteria:
     - Purpose of state preservation clear
     - Users understand optional nature
     - Recovery procedure documented

**Phase 4 Exit Criteria**:
- Checkpoint system fully functional
- Save/load cycle tested and working
- Recovery tested after simulated crash
- System resilient to corruption
- All Phase 4 tests passing (7 tests minimum)
- Checkpoint file format stable

---

## Phase 5: Test Infrastructure & Documentation (Priority 5)

**Objective**: Build comprehensive test suite for long-running processes and finalize documentation.

**Deliverable**: Complete test suite with unit, integration, stress, and backwards compatibility tests.

**Dependencies**: All previous phases should be complete

### Tasks

1. **Create test fixtures and helpers**
   - Fixture: MockTaskQueue with controllable behavior
   - Fixture: MockAgent for testing task processing
   - Helper: assert_signal_handling() for signal tests
   - Helper: assert_backoff_behavior() for backoff tests
   - Helper: measure_loop_duration() for timing tests
   - Acceptance criteria:
     - Fixtures simplify test writing
     - Helpers reduce boilerplate
     - All helpers well-documented

2. **Write unit tests for all components**
   - Test signal handling (3 tests): SIGTERM, SIGINT, restoration
   - Test backoff calculation (2 tests): math, edge cases
   - Test mode logic (3 tests): daemon, oneshot, test
   - Test heartbeat (2 tests): structure, timing
   - Test checkpoint (3 tests): schema, save, load
   - Minimum: 13 unit tests
   - Acceptance criteria:
     - Coverage > 90% for all new code
     - Tests are deterministic (no flakes)
     - Tests run in < 5 seconds total

3. **Write integration tests**
   - Test: test_full_daemon_cycle_with_signals()
     - Start daemon, let it run for 3 cycles
     - Send SIGTERM
     - Verify graceful shutdown
   - Test: test_full_oneshot_lifecycle()
     - Start oneshot with idle_timeout=1s
     - No tasks, verify exit after timeout
     - Verify all metrics recorded
   - Test: test_full_test_mode_with_tasks()
     - Start test mode with max_cycles=10
     - Add 5 tasks
     - Verify processed correctly, mode exits
   - Minimum: 3 integration tests
   - Acceptance criteria:
     - Tests cover end-to-end scenarios
     - Tests are realistic
     - Tests verify all major components working together

4. **Write stress tests**
   - Test: test_high_frequency_task_creation()
     - Create 100 tasks rapidly
     - Verify all processed
     - Verify backoff resets properly
   - Test: test_prolonged_empty_queue()
     - Run for 60 cycles with empty queue
     - Verify backoff grows to max
     - Verify CPU not thrashing (measure)
   - Test: test_rapid_signal_handling()
     - Send multiple SIGTERMs/SIGINTs rapidly
     - Verify graceful shutdown
   - Minimum: 3 stress tests (may take longer)
   - Acceptance criteria:
     - System handles high load without crashing
     - Backoff prevents thrashing
     - Signal handling robust

5. **Write backwards compatibility tests**
   - Test: test_poll_and_process_still_works()
     - Call poll_and_process() (old API)
     - Verify works exactly as before
   - Test: test_idle_timeout_legacy_behavior()
     - Call poll_and_process(idle_timeout=2)
     - Verify exits after 2 seconds idle
   - Test: test_existing_tests_still_pass()
     - Run orchestrator_testing_harness.py
     - Verify all tests pass unchanged
   - Minimum: 3 backwards compatibility tests
   - Acceptance criteria:
     - Old API continues to work
     - No breaking changes
     - Existing tests pass without modification

6. **Create test documentation**
   - Document how to run tests: `pytest tests/orchestrator/`
   - Document how to run specific test groups
   - Document test fixtures and helpers
   - Document how to add new tests
   - Add example tests to AGENTS.md
   - Acceptance criteria:
     - New contributors can run and write tests easily
     - Test structure clear
     - Examples provided

7. **Final documentation and handoff**
   - Review and finalize docs/architecture-continuous-polling-5102.md
   - Review and finalize implementation roadmap (this document)
   - Create HANDOFF.md summarizing:
     - What was implemented
     - What was tested
     - Known limitations/future work
     - How to use the new API
   - Update AGENTS.md with orchestrator API
   - Acceptance criteria:
     - Documentation comprehensive and accurate
     - Handoff clear enough for next team member
     - All design decisions documented

**Phase 5 Exit Criteria**:
- All unit tests (13+) passing
- All integration tests (3+) passing
- All stress tests (3+) passing
- All backwards compatibility tests (3+) passing
- Total test coverage > 90% for polling loop code
- Documentation complete and reviewed
- Handoff document created
- Ready for production deployment

---

## Cross-Phase Considerations

### Testing Strategy Throughout

Each phase includes its own tests, but they must also:
- Not introduce regressions in previous phases
- Be runnable independently
- Contribute to overall coverage target (>90%)
- Be fast enough for CI/CD (ideally < 30 seconds per phase)

### Backwards Compatibility Throughout

- `poll_and_process()` must continue to work unchanged
- Existing test harness must pass without modification
- No breaking changes to OrchestratorAgent class interface
- Environment variables should be optional (defaults sufficient)

### Documentation Throughout

- Each phase includes docstring updates
- Docstrings should be clear enough for IDE tooltips
- Complex logic should have inline comments
- Architecture decisions documented in commit messages

---

## Success Metrics

### Code Quality
- [ ] All phases have >90% test coverage
- [ ] No critical issues in code review
- [ ] Linting passes: pylint, black, mypy
- [ ] All docstrings complete and accurate

### Functionality
- [ ] All requirements from Task 5102 met
- [ ] Daemon mode runs indefinitely until SIGTERM/SIGINT
- [ ] Oneshot mode behaves identically to original
- [ ] Test mode supports fixed cycle limits
- [ ] Backoff prevents CPU thrashing
- [ ] Heartbeat emitted regularly
- [ ] State preserved and recoverable

### Performance
- [ ] Loop overhead < 1% CPU when idle (with backoff)
- [ ] No memory leaks over 24-hour runtime
- [ ] Signal handling latency < 100ms
- [ ] Checkpoint I/O doesn't impact responsiveness

### Reliability
- [ ] All tests pass consistently (no flakes)
- [ ] Graceful shutdown under all conditions
- [ ] Recovery from checkpoint works reliably
- [ ] No orphaned processes

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Signal handling issues | Low | High | Extensive unit and integration testing |
| Backwards compatibility break | Low | High | Keep poll_and_process() delegating, test legacy code |
| CPU thrashing with backoff | Low | Medium | Stress tests to verify backoff math |
| State corruption on crash | Low | Medium | Atomic writes, graceful degradation on corrupt reads |
| Timing-dependent test flakes | Medium | Low | Generous timeouts, independent test runs |

---

## Dependencies & Prerequisites

### Required for starting Phase 1
- ✅ Architecture document review and approval
- ✅ Understanding of current poll_and_process() implementation
- ✅ Python signal handling knowledge

### Required for starting Phase 2
- ✅ Phase 1 complete and tested
- ✅ Basic polling loop verified

### Required for starting Phase 3
- ✅ Phase 1 complete (Phase 2 optional but recommended)
- ✅ Decision on observability output format

### Required for starting Phase 4
- ✅ Phase 1 complete (Phase 2 and 3 optional)
- ✅ YAML library available (standard in Python)

### Required for starting Phase 5
- ✅ Phases 1-4 complete
- ✅ All previous tests passing

---

## Estimated Timeline

Assuming one engineer, full-time, working sequentially:

| Phase | Effort | Timeline | Notes |
|-------|--------|----------|-------|
| Phase 1 | 12 hours | Days 1-2 | Core loop and signals |
| Phase 2 | 8 hours | Days 3-4 | Backoff math relatively straightforward |
| Phase 3 | 10 hours | Days 5-6 | Depends on observability system choice |
| Phase 4 | 12 hours | Days 7-8 | Checkpoint system requires careful testing |
| Phase 5 | 18 hours | Days 9-12 | Test writing is time-consuming but essential |
| **Total** | **60 hours** | **~2 weeks** | Assuming 30 hour work weeks or part-time |

**Parallelization opportunity**: Phases 2, 3, and 4 can run in parallel after Phase 1 completes (start Phase 2, 3, 4 simultaneously, then integrate in Phase 5).

---

## Open Questions for Engineer

1. **Observability output format** (Phase 3)
   - Should heartbeats go to stdout as JSON logs?
   - Should we integrate with Prometheus?
   - Should we use existing metrics system (if any)?
   - Action: Confirm with Principal Engineer before Phase 3

2. **Checkpoint frequency** (Phase 4)
   - Save after every cycle (safest but more I/O)?
   - Save every N cycles (faster but less recovery granularity)?
   - Save only on explicit request (manual checkpointing)?
   - Recommendation: Every 10 cycles as default, configurable

3. **Signal handling for task cleanup** (Phase 1)
   - If SIGINT received mid-task, should we:
     - Finish the task then shutdown?
     - Escalate the task and shutdown immediately?
     - Request task cancellation?
   - Recommendation: Finish task then shutdown (safest)

4. **Environment variable naming** (All phases)
   - Use ORCHESTRATOR_ prefix?
   - Use ERS_ prefix (if part of larger ERS system)?
   - Keep minimal (BACKOFF_MS)?
   - Recommendation: ORCHESTRATOR_ for clarity and consistency

---

## Definition of Done (Each Phase)

- [ ] All code changes merged to main branch
- [ ] All tests passing (unit, integration, backwards compat)
- [ ] Code review completed and approved
- [ ] Documentation updated
- [ ] No new linting/type checking errors
- [ ] Performance benchmarks acceptable
- [ ] Deployment checklist complete
- [ ] Handoff notes prepared

---

## References

- **Architecture Document**: docs/architecture-continuous-polling-5102.md
- **Current Implementation**: orchestration/agents/orchestrator.py (lines 260-330)
- **Test Harness**: orchestration/agents/orchestrator_testing_harness.py
- **System Overview**: SYSTEM.md, AGENTS.md, ENTRYPOINT.md
