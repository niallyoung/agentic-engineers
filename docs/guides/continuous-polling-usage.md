# Usage Guide: Continuous Polling Loop Automation (Phase 1)

⚠️ **DEPRECATED (2026-06-13)**: `AutomationController` class was removed on 2026-05-17. Continuous polling is now handled by the Orchestrator SKILL (`OrchestratorSkill.run_idle_loop()`), not a separate daemon. This document is archived for reference only. See `docs/design/spawn-sub-agent-pattern.md` for current architecture.

**Document**: Phase 1 implementation of continuous polling loop automation  
**Task ID**: `continuous-polling-automation-phase1`  
**Status**: DEPRECATED  
**Last Updated**: 2026-05-03 (archived 2026-06-13)  

---

## Overview

The AutomationController provides a production-ready continuous polling loop for autonomous Orchestrator operation. It handles:

- **While-True polling loop** with configurable intervals
- **Signal-driven graceful shutdown** (SIGTERM, SIGINT)
- **Comprehensive logging and metrics** for observability
- **Error handling and recovery** without data loss
- **Environment variable configuration** for easy deployment

---

## Quick Start

### Basic Usage

```python
from orchestration.agents.automation import AutomationController

# Create and run controller
controller = AutomationController()
result = controller.run()

print(f"Status: {result['status']}")
print(f"Metrics: {result['metrics']}")
```

### Command-Line Usage

```bash
# Run with default settings
python3 -m orchestration.agents.automation

# Run with custom settings
python3 -m orchestration.agents.automation \
  --daemon \
  --poll-interval 10 \
  --log-level DEBUG \
  --metrics-file /tmp/metrics.json

# Run in non-daemon mode with idle timeout
python3 -m orchestration.agents.automation \
  --idle-timeout 60 \
  --log-level INFO

# Run with max cycles (for testing)
python3 -m orchestration.agents.automation \
  --max-cycles 5 \
  --poll-interval 1 \
  --log-level DEBUG
```

---

## Configuration

### Environment Variables

#### Core Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `POLL_INTERVAL_SECONDS` | float | `5` | Seconds between polling cycles |
| `AUTOMATION_DAEMON_MODE` | bool | `true` | Run as daemon (true/false) |
| `AUTOMATION_IDLE_TIMEOUT` | int | `300` | Idle timeout before exit (seconds) |
| `AUTOMATION_MAX_CYCLES` | int | `None` | Maximum cycles before exit (None=unlimited) |
| `LOG_LEVEL` | str | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

#### Optional Configuration

| Variable | Type | Description |
|----------|------|-------------|
| `AUTOMATION_METRICS_FILE` | str | Path to write final metrics JSON (optional) |
| `ORCHESTRATOR_QUEUE_DIR` | str | Override default queue directory |

### Examples

#### Production Daemon Mode

```bash
export POLL_INTERVAL_SECONDS=5
export AUTOMATION_DAEMON_MODE=true
export LOG_LEVEL=INFO
export AUTOMATION_METRICS_FILE=/var/log/orchestrator-metrics.json

python3 -m orchestration.agents.automation
```

#### Development/Testing Mode

```bash
export POLL_INTERVAL_SECONDS=1
export AUTOMATION_DAEMON_MODE=false
export AUTOMATION_IDLE_TIMEOUT=30
export LOG_LEVEL=DEBUG

python3 -m orchestration.agents.automation
```

#### Testing with Max Cycles

```bash
export AUTOMATION_MAX_CYCLES=10
export POLL_INTERVAL_SECONDS=0.1
export LOG_LEVEL=DEBUG

python3 -m orchestration.agents.automation
```

---

## Operational Modes

### Daemon Mode (Default)

Runs indefinitely until receiving a shutdown signal.

```python
controller = AutomationController(
    daemon_mode=True,
    poll_interval=5
)
result = controller.run()
# Runs until SIGTERM or SIGINT received
```

**Use Cases**:
- Production autonomous operation
- Long-running background service
- Continuous queue polling

### Idle-Timeout Mode

Runs until queue has been idle for N seconds.

```python
controller = AutomationController(
    daemon_mode=False,
    idle_timeout=300  # 5 minutes
)
result = controller.run()
# Runs until 5 minutes of no tasks
```

**Use Cases**:
- Limited resource environments
- Testing automation
- Batch job processing

### Test Mode

Runs for exactly N cycles (useful for integration tests).

```python
controller = AutomationController(
    max_cycles=10,
    daemon_mode=False
)
result = controller.run()
# Runs for exactly 10 cycles, then exits
```

**Use Cases**:
- Unit testing
- Integration testing
- Validation runs

---

## Signal Handling

### SIGTERM (Graceful Shutdown)

**Behavior**: Finish current polling cycle, then exit cleanly

```bash
# In another terminal
kill -TERM <pid>
```

**Timeline**:
1. Signal received → set `shutdown_requested = True`
2. Current cycle completes
3. Metrics recorded
4. Process exits with code 0

**Data Safety**: All in-flight tasks are preserved; queue state unchanged

### SIGINT (Clean Exit)

**Behavior**: Exit immediately with cleanup

```bash
# Keyboard interrupt
Ctrl+C
```

**Timeline**:
1. Signal received → set `shutdown_requested = True`
2. Any running cycle finishes
3. Process exits with code 0

**Data Safety**: Same as SIGTERM

---

## Logging and Observability

### Log Levels

#### DEBUG
Full diagnostic output including cycle details and configuration.

```
[2026-05-03 13:05:31] [AutomationController] [DEBUG] Signal handlers installed (SIGTERM, SIGINT)
[2026-05-03 13:05:32] [AutomationController] [DEBUG] Sleeping 5s before next cycle...
```

#### INFO (Default)
Key events: startup, cycles completed, heartbeats, shutdown.

```
[2026-05-03 13:05:31] [AutomationController] [INFO] AutomationController starting
[2026-05-03 13:05:32] [AutomationController] [INFO] [Cycle 1] Processed 3 tasks in 0.42s
[2026-05-03 13:05:33] [AutomationController] [INFO] Heartbeat: {"cycles": 5, "tasks": 15, ...}
```

#### WARNING
Shutdown signals, recoverable errors.

```
[2026-05-03 13:05:31] [AutomationController] [WARNING] SIGTERM received - graceful shutdown after current cycle
[2026-05-03 13:05:31] [AutomationController] [WARNING] Error in polling cycle: Connection timeout
```

#### ERROR
Unrecoverable errors, exceptions.

```
[2026-05-03 13:05:31] [AutomationController] [ERROR] Unexpected error: queue not found
```

### Structured Metrics

Final metrics are emitted in JSON format and can be written to a file:

```json
{
  "status": "COMPLETE",
  "exit_reason": "idle_timeout",
  "metrics": {
    "start_time": "2026-05-03T13:05:31.123456",
    "end_time": "2026-05-03T13:15:31.654321",
    "total_duration_seconds": 600.531,
    "cycles_completed": 120,
    "cycle_duration_avg_seconds": 5.004,
    "cycle_duration_min_seconds": 4.521,
    "cycle_duration_max_seconds": 6.234,
    "tasks_processed": 45,
    "tasks_success": 40,
    "tasks_escalated": 5,
    "tasks_failed": 0,
    "error_count": 1,
    "errors": [
      {
        "timestamp": "2026-05-03T13:10:15.456789",
        "message": "Connection timeout during cycle"
      }
    ],
    "shutdown_reason": "idle_timeout",
    "shutdown_signal": "none"
  }
}
```

---

## Integration Examples

### Running as a Daemon Service

```bash
#!/bin/bash
# start-orchestrator.sh

export POLL_INTERVAL_SECONDS=5
export AUTOMATION_DAEMON_MODE=true
export LOG_LEVEL=INFO
export AUTOMATION_METRICS_FILE=/var/log/orchestrator-metrics.json

nohup python3 -m orchestration.agents.automation > /var/log/orchestrator.log 2>&1 &
echo $! > /var/run/orchestrator.pid
```

### Monitoring with Metrics File

```bash
#!/bin/bash
# monitor-orchestrator.sh

METRICS_FILE=/var/log/orchestrator-metrics.json

while true; do
  if [ -f "$METRICS_FILE" ]; then
    echo "=== Latest Metrics ==="
    jq '.metrics | {cycles: .cycles_completed, tasks: .tasks_processed, duration: .total_duration_seconds}' "$METRICS_FILE"
  fi
  sleep 60
done
```

### Docker Deployment

```dockerfile
FROM python:3.7

WORKDIR /app
COPY . .

ENV POLL_INTERVAL_SECONDS=5
ENV AUTOMATION_DAEMON_MODE=true
ENV LOG_LEVEL=INFO

CMD ["python3", "-m", "orchestration.agents.automation"]
```

### Kubernetes Deployment

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: orchestrator
spec:
  containers:
  - name: orchestrator
    image: agentic-engineers:latest
    env:
    - name: POLL_INTERVAL_SECONDS
      value: "5"
    - name: AUTOMATION_DAEMON_MODE
      value: "true"
    - name: LOG_LEVEL
      value: "INFO"
    volumeMounts:
    - name: queue-dir
      mountPath: /home/user/.copilot/queue
  volumes:
  - name: queue-dir
    emptyDir: {}
```

---

## Testing and Validation

### Unit Tests

Run comprehensive unit tests:

```bash
cd /home/user/agentic-engineers

# Run all automation tests
python3 -m pytest orchestration/agents/test_automation.py -v

# Run specific test class
python3 -m pytest orchestration/agents/test_automation.py::TestConfigurationAndValidation -v

# Run with coverage
python3 -m pytest orchestration/agents/test_automation.py --cov=orchestration.agents.automation
```

### Integration Tests

```bash
# Run integration tests only
python3 -m pytest orchestration/agents/test_automation.py::TestIntegrationWithRealQueue -v
```

### Manual Testing

```python
from orchestration.agents.automation import AutomationController
import json

# Run with 5 cycles
controller = AutomationController(
    poll_interval=1,
    max_cycles=5,
    log_level="DEBUG"
)

result = controller.run()

# Print results
print(json.dumps(result, indent=2))
```

---

## Troubleshooting

### Issue: High CPU Usage

**Cause**: Poll interval too short or rapid task creation  
**Solution**: Increase `POLL_INTERVAL_SECONDS`

```bash
export POLL_INTERVAL_SECONDS=10  # Increase from 5 to 10 seconds
```

### Issue: Tasks Not Being Processed

**Cause**: Queue directory misconfigured or permissions issue  
**Solution**: Verify queue directory and permissions

```bash
# Check queue directory
export ORCHESTRATOR_QUEUE_DIR=/custom/queue/path
python3 -m orchestration.agents.automation --log-level DEBUG

# Verify permissions
ls -la ~/.copilot/queue/
```

### Issue: Process Not Shutting Down on SIGTERM

**Cause**: Blocking operation in polling cycle  
**Solution**: Check logs and verify no long-running tasks

```bash
# Monitor in real-time
tail -f /var/log/orchestrator.log

# Send SIGTERM and watch shutdown
kill -TERM <pid>
```

### Issue: Metrics File Not Created

**Cause**: Invalid file path or permission denied  
**Solution**: Check path and permissions

```bash
# Use absolute path with write permissions
export AUTOMATION_METRICS_FILE=/tmp/orchestrator-metrics.json
python3 -m orchestration.agents.automation

# Verify file created
cat /tmp/orchestrator-metrics.json | jq .
```

---

## Performance Tuning

### For High Task Throughput

```bash
export POLL_INTERVAL_SECONDS=1      # Check queue frequently
export LOG_LEVEL=WARNING             # Reduce logging overhead
export AUTOMATION_METRICS_FILE=''    # Disable metrics file writing
```

**Expected**: Higher throughput, more CPU usage

### For Low Resource Environments

```bash
export POLL_INTERVAL_SECONDS=30      # Check queue less frequently
export LOG_LEVEL=ERROR               # Minimal logging
export AUTOMATION_DAEMON_MODE=false
export AUTOMATION_IDLE_TIMEOUT=600   # 10 minutes
```

**Expected**: Lower CPU/memory, slower task processing

### For Development

```bash
export POLL_INTERVAL_SECONDS=0.5     # Fast feedback
export LOG_LEVEL=DEBUG               # Full diagnostics
export AUTOMATION_MAX_CYCLES=50      # Auto-exit for testing
```

**Expected**: Useful debugging output, safe test termination

---

## Architecture Reference

See the following documents for architectural details:

- **Design**: `docs/architecture-continuous-polling-5102.md`
- **Roadmap**: `docs/implementation-roadmap-continuous-polling-5102.md`
- **Orchestrator**: `orchestration/agents/orchestrator.py`
- **AutomationController**: `orchestration/agents/automation.py`
- **Tests**: `orchestration/agents/test_automation.py`

---

## Success Criteria (Acceptance)

✅ AutomationController class implemented and integrated  
✅ While-True polling loop with signal handling working  
✅ Configurable poll interval via environment variables  
✅ Comprehensive test coverage (32 unit + integration tests)  
✅ All tests passing  
✅ Graceful shutdown without data loss  
✅ Production-ready with comprehensive logging  
✅ Usage documentation complete  

---

## Next Steps (Phase 2+)

- **Phase 2**: Exponential backoff strategy (reduce CPU usage on empty queues)
- **Phase 3**: Heartbeat & observability (emit metrics to monitoring system)
- **Phase 4**: State preservation (save queue position across restarts)
- **Phase 5**: Advanced resilience (handle network failures, queue corruption)

---

## Support and Feedback

For issues, questions, or improvements:

1. Check the troubleshooting section above
2. Review logs with `--log-level DEBUG`
3. Run tests to validate environment
4. Consult architecture documents for design decisions

---

*Phase 1 complete. Ready for production deployment.*
