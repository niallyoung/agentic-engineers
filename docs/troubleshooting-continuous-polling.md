# Troubleshooting Guide: Continuous Polling Loop Automation

## Quick Diagnostic Checklist

Before diving into specific issues, run through these checks:

```bash
# 1. Verify script is executable
ls -la /opt/orchestrator/bin/run-automation-controller.sh

# 2. Check Python version
python3 --version  # Should be 3.8+

# 3. Verify project structure
ls -la /opt/orchestrator/  # Should see: bin/, orchestration/, data/, docs/

# 4. Check queue directories
ls -la /opt/orchestrator/data/queue/  # Should have: incoming/, done/

# 5. Verify permissions
id orchestrator  # Should be a valid user

# 6. Check disk space
df -h /opt/orchestrator  # Should have > 1GB free

# 7. Verify Python path
python3 -c "import sys; print(sys.path)"

# 8. Test import
python3 -c "from orchestration.agents.automation import AutomationController; print('OK')"
```

---

## Common Issues & Solutions

### Issue 1: "ModuleNotFoundError: No module named 'orchestration'"

**Symptoms:**
```
ModuleNotFoundError: No module named 'orchestration'
```

**Causes:**
- `PYTHONPATH` not set correctly
- Running from wrong directory
- Project files not installed

**Solutions:**

```bash
# Option 1: Set PYTHONPATH explicitly
export PYTHONPATH=/opt/orchestrator:$PYTHONPATH
./bin/run-automation-controller.sh

# Option 2: Run from project root
cd /opt/orchestrator
./bin/run-automation-controller.sh

# Option 3: Verify installation
python3 -c "import sys; sys.path.insert(0, '/opt/orchestrator'); from orchestration.agents.automation import AutomationController"

# Option 4: Check if files exist
ls -la /opt/orchestrator/orchestration/agents/automation.py
```

**Prevention:**
- Always source `.env` before running
- Run from project root
- Check entrypoint script sets PYTHONPATH

---

### Issue 2: "Queue directory not found or not writable"

**Symptoms:**
```
ERROR: Queue directory not found
ERROR: Permission denied writing to queue
```

**Causes:**
- Queue directory doesn't exist
- Wrong ownership
- Insufficient permissions
- Disk space full

**Solutions:**

```bash
# Check queue directory exists
ls -la /opt/orchestrator/data/queue/

# Create if missing
mkdir -p /opt/orchestrator/data/queue/{incoming,done}

# Fix ownership
sudo chown -R orchestrator:orchestrator /opt/orchestrator/data

# Fix permissions
sudo chmod 755 /opt/orchestrator/data/queue/{incoming,done}
sudo chmod 755 /opt/orchestrator/logs
sudo chmod 755 /opt/orchestrator/metrics

# Check disk space
df -h /opt/orchestrator
# If < 10%, free up space or increase volume

# Verify writable
touch /opt/orchestrator/data/queue/test.txt && rm /opt/orchestrator/data/queue/test.txt
echo "Queue directory is writable"
```

**Prevention:**
- Check permissions in deployment checklist
- Monitor disk space weekly
- Use `umask 0002` to ensure group writability

---

### Issue 3: "Polling loop not processing tasks"

**Symptoms:**
- DELEGATE files stay in `incoming` directory
- No HANDBACK files created
- `tasks_processed: 0` in metrics

**Causes:**
- OrchestratorAgent not processing queue
- Agent spawning failing silently
- Invalid DELEGATE file format
- AgentInvoker not available

**Solutions:**

```bash
# 1. Enable debug logging
LOG_LEVEL=DEBUG ./bin/run-automation-controller.sh

# 2. Check DELEGATE file format
head -20 /opt/orchestrator/data/queue/incoming/DELEGATE-*.yaml
# Should have: handoff_type: DELEGATE, task_id, role, etc.

# 3. Verify OrchestratorAgent initialization
python3 << 'EOF'
from orchestration.agents.orchestrator import OrchestratorAgent
agent = OrchestratorAgent(queue_dir="/opt/orchestrator/data/queue")
print(f"Queue dir: {agent.queue_dir}")
print(f"Available: {agent.queue_manager is not None}")
EOF

# 4. Check AgentInvoker is available
python3 -c "from orchestration.agents.invoke_agent import AgentInvoker; print('AgentInvoker available')"

# 5. Test queue reading directly
python3 << 'EOF'
from orchestration.agents.orchestrator import QueueManager
qm = QueueManager("/opt/orchestrator/data/queue")
tasks = qm.list_pending_tasks()
print(f"Pending tasks: {len(tasks)}")
for task in tasks[:3]:
    print(f"  - {task}")
EOF

# 6. Check for errors in logs
grep -E "ERROR|FAILED|Exception" /opt/orchestrator/logs/automation-*.log | tail -20
```

**Prevention:**
- Use provided sample DELEGATE files for testing
- Validate DELEGATE format before deploying
- Test with small batch before going to production

---

### Issue 4: "High CPU usage / Spinning loop"

**Symptoms:**
- CPU usage > 50% constantly
- `automation` process consuming resources
- High frequency polling without sleep

**Causes:**
- `POLL_INTERVAL_SECONDS` too low
- Queue always empty causing busy loop
- Backoff not working correctly
- Infinite loop in agent processing

**Solutions:**

```bash
# 1. Check current poll interval
grep POLL_INTERVAL /opt/orchestrator/.env
# Default should be 5 seconds

# 2. Increase poll interval
echo "POLL_INTERVAL_SECONDS=10" >> /opt/orchestrator/.env
sudo systemctl restart orchestrator-automation.service

# 3. Monitor CPU after change
top -p $(pgrep -f "run-automation-controller")

# 4. Check if queue is genuinely empty
find /opt/orchestrator/data/queue/incoming -type f | wc -l
# If 0, then polling is correct (sleep between cycles)

# 5. Check for infinite loops in logs
grep -c "Cycle" /opt/orchestrator/logs/automation-*.log
# High count = many cycles = spinning

# 6. Profile the process
python3 -m cProfile -s cumtime bin/run-automation-controller.sh 2>&1 | tail -30

# 7. Temporary fix: Stop and restart with higher interval
POLL_INTERVAL_SECONDS=30 ./bin/run-automation-controller.sh
```

**Prevention:**
- Set `POLL_INTERVAL_SECONDS` to 5-10 seconds for most workloads
- Monitor CPU usage in first week of deployment
- Alert if CPU > 40% for extended period

---

### Issue 5: "Graceful shutdown not working / Process hangs"

**Symptoms:**
- `SIGTERM` doesn't shut down process
- Process doesn't respond to signals
- Stuck in polling cycle
- Manual `kill -9` required

**Causes:**
- Signal handlers not installed
- Thread blocking operations
- Unresponsive agent processing
- Sleep interrupted incorrectly

**Solutions:**

```bash
# 1. Get process PID
PID=$(pgrep -f "run-automation-controller")
echo "Process PID: $PID"

# 2. Send SIGTERM (graceful)
kill -TERM $PID
sleep 5
# Wait up to 5 seconds for graceful shutdown

# 3. Check if process still running
if ps -p $PID > /dev/null; then
    echo "Process still running, forcing kill..."
    kill -9 $PID
fi

# 4. Verify shutdown
ps -p $PID && echo "Failed to kill" || echo "Process terminated"

# 5. Check logs for shutdown reason
tail -50 /opt/orchestrator/logs/automation-*.log | grep -E "shutdown|SIGTERM|SIGINT"

# 6. Test signal handling in isolation
python3 << 'EOF'
import signal
import time

def handler(sig, frame):
    print(f"Received signal {sig}")
    exit(0)

signal.signal(signal.SIGTERM, handler)
print(f"PID: {os.getpid()}, waiting for signal...")
while True:
    time.sleep(1)
EOF

# In another terminal: kill -TERM <pid>
# Process should exit immediately
```

**Prevention:**
- Always use `systemctl stop` instead of `kill -9`
- Monitor shutdown logs
- Set `SIGTERM_TIMEOUT=30` to allow graceful shutdown

---

### Issue 6: "Metrics file not created / Metrics empty"

**Symptoms:**
- No metrics file in `/opt/orchestrator/metrics/`
- Metrics file exists but is empty or invalid JSON
- Cannot parse metrics

**Causes:**
- `METRICS_FILE` path wrong or not writable
- Metrics not being collected
- Metrics directory doesn't exist
- Insufficient permissions

**Solutions:**

```bash
# 1. Check metrics configuration
grep METRICS_FILE /opt/orchestrator/.env

# 2. Verify metrics directory exists and is writable
mkdir -p /opt/orchestrator/metrics
chmod 755 /opt/orchestrator/metrics
touch /opt/orchestrator/metrics/test.json && rm /opt/orchestrator/metrics/test.json

# 3. Check latest metrics file
ls -lrt /opt/orchestrator/metrics/ | tail -5

# 4. Validate metrics JSON
python3 -m json.tool < /opt/orchestrator/metrics/metrics-*.json | head -50

# 5. If empty, check if controller ran
grep -E "cycles_completed|tasks_processed" /opt/orchestrator/logs/automation-*.log

# 6. Run controller with explicit metrics file
METRICS_FILE=/tmp/test-metrics.json ./bin/run-automation-controller.sh
cat /tmp/test-metrics.json

# 7. Check for write errors in logs
grep -i "metrics\|write\|permission" /opt/orchestrator/logs/automation-*.log
```

**Prevention:**
- Always create metrics directory before starting
- Verify METRICS_FILE is set in .env
- Check metrics file after first run

---

### Issue 7: "Health check endpoint not responding"

**Symptoms:**
```
curl: (7) Failed to connect to localhost port 9090
Health check endpoint not found
```

**Causes:**
- Health check disabled (`HEALTH_CHECK_PORT=0`)
- Port blocked by firewall
- Process crashed
- Port already in use

**Solutions:**

```bash
# 1. Check health check configuration
grep HEALTH_CHECK_PORT /opt/orchestrator/.env

# 2. Enable health check if disabled
echo "HEALTH_CHECK_PORT=9090" >> /opt/orchestrator/.env

# 3. Check if port is listening
netstat -tuln | grep 9090
# or
lsof -i :9090

# 4. Check if port is in use by something else
ps aux | grep 9090

# 5. Try different port
HEALTH_CHECK_PORT=9091 ./bin/run-automation-controller.sh

# 6. Check firewall rules
sudo ufw allow 9090/tcp

# 7. Test from localhost
curl -v http://127.0.0.1:9090/health

# 8. Check for errors in logs
grep -i "health\|endpoint\|server" /opt/orchestrator/logs/automation-*.log
```

**Prevention:**
- Verify port 9090 is available before deployment
- Configure firewall to allow monitoring traffic
- Document port requirements

---

### Issue 8: "Memory usage growing / Memory leak"

**Symptoms:**
- Process memory usage increases over time
- Eventually causes OOM (Out of Memory)
- Server becomes unresponsive

**Causes:**
- Memory leak in AutomationController
- OrchestratorAgent holding references
- Queue not being cleaned up
- Logs not being rotated

**Solutions:**

```bash
# 1. Monitor memory usage
watch -n 5 'ps -o pid,vsz,rss,comm -p $(pgrep -f run-automation-controller)'

# 2. Check memory over time
ps aux | grep run-automation-controller

# 3. Profile memory
python3 -m tracemalloc << 'EOF'
import sys
sys.path.insert(0, '/opt/orchestrator')
from orchestration.agents.automation import AutomationController
import tracemalloc

tracemalloc.start()
controller = AutomationController(max_cycles=10)
result = controller.run()
current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024 / 1024:.1f} MB")
print(f"Peak: {peak / 1024 / 1024:.1f} MB")
EOF

# 4. Rotate old logs to free space
find /opt/orchestrator/logs -name "*.log" -mtime +7 -delete

# 5. Set restart schedule (systemd)
# Add to [Service] section:
# Restart=on-failure
# RestartSec=300

# 6. Or use cron for periodic restart
# 0 2 * * * /bin/systemctl restart orchestrator-automation.service

# 7. Monitor with memory limit
# Add to .env:
# MEMORY_LIMIT=1024  # MB
```

**Prevention:**
- Implement log rotation
- Schedule periodic restarts (if needed)
- Monitor memory weekly
- Test with high task volumes

---

### Issue 9: "DELEGATE files not moving to done directory"

**Symptoms:**
- Files remain in `incoming` directory
- No corresponding files in `done` directory
- Possible duplicate processing

**Causes:**
- QueueManager not moving files
- Permission issues
- File locking problems
- Network issues (if NFS)

**Solutions:**

```bash
# 1. Check file permissions
ls -la /opt/orchestrator/data/queue/incoming/
ls -la /opt/orchestrator/data/queue/done/

# 2. Test file movement manually
cp /opt/orchestrator/data/queue/incoming/DELEGATE-test.yaml \
   /opt/orchestrator/data/queue/done/DELEGATE-test.yaml
echo "Movement successful"

# 3. Check QueueManager directly
python3 << 'EOF'
from orchestration.agents.orchestrator import QueueManager
qm = QueueManager("/opt/orchestrator/data/queue")
tasks = qm.list_pending_tasks()
print(f"Pending: {len(tasks)}")
EOF

# 4. Check for NFS issues
df /opt/orchestrator/data/queue
# Verify mount is active and responsive

# 5. Check for file locking
fuser /opt/orchestrator/data/queue/done/DELEGATE-*.yaml

# 6. Review logs for move operations
grep -E "moving\|moving task\|done directory" /opt/orchestrator/logs/automation-*.log

# 7. Manually clean up stale files
ls -la /opt/orchestrator/data/queue/incoming/ | wc -l
# If > 1000, consider cleanup strategy
```

**Prevention:**
- Regular cleanup of old files
- Monitor queue directory size
- Implement file archive strategy

---

### Issue 10: "Task failure rate high / Many escalations"

**Symptoms:**
- `tasks_failed` or `tasks_escalated` increasing
- Agents not completing successfully
- Agent spawn failures

**Causes:**
- Agent resources exhausted
- Invalid task configuration
- Agent code errors
- Dependency missing

**Solutions:**

```bash
# 1. Check failure metrics
python3 << 'EOF'
import json
with open("/opt/orchestrator/metrics/metrics-*.json") as f:
    m = json.load(f)["metrics"]
    print(f"Processed: {m['tasks_processed']}")
    print(f"Success: {m['tasks_success']}")
    print(f"Failed: {m['tasks_failed']}")
    print(f"Escalated: {m['tasks_escalated']}")
    if m['tasks_processed'] > 0:
        print(f"Success Rate: {m['tasks_success']/m['tasks_processed']*100:.1f}%")
EOF

# 2. Review agent logs
ls -lrt /opt/orchestrator/logs/agent-* | tail -10
grep -i error /opt/orchestrator/logs/agent-*.log

# 3. Check DELEGATE file format
head -20 /opt/orchestrator/data/queue/done/HANDBACK-*.yaml | grep -A 5 "status:"

# 4. Increase agent resources
# Modify .env or Docker resource limits

# 5. Test agent directly
python3 -m orchestration.agents.invoke_agent --help

# 6. Review agent implementation for bugs
python3 -c "from orchestration.agents.invoke_agent import AgentInvoker; print('OK')"
```

**Prevention:**
- Validate DELEGATE format before deployment
- Monitor failure rate continuously
- Alert on > 5% failure rate
- Test agents in staging first

---

## Performance Optimization

### Tuning for High Throughput

```bash
# Reduce polling interval
POLL_INTERVAL_SECONDS=2

# Increase batch processing
BATCH_SIZE=10  # If supported

# Optimize logging
LOG_LEVEL=WARNING

# Enable metrics caching
METRICS_CACHE_INTERVAL=60
```

### Tuning for Low Resources

```bash
# Increase polling interval
POLL_INTERVAL_SECONDS=30

# Reduce logging verbosity
LOG_LEVEL=ERROR

# Enable memory-efficient mode
EFFICIENT_MODE=true
```

---

## Getting Help

If issue persists after troubleshooting:

1. **Collect diagnostic information:**
   ```bash
   # Gather all relevant information
   echo "=== System Info ===" && uname -a
   echo "=== Python ===" && python3 --version
   echo "=== Disk ===" && df -h /opt/orchestrator
   echo "=== Processes ===" && ps aux | grep automation
   echo "=== Recent Logs ===" && tail -100 /opt/orchestrator/logs/automation-*.log
   echo "=== Configuration ===" && cat /opt/orchestrator/.env
   ```

2. **Create bug report with:**
   - Full error message and stack trace
   - Steps to reproduce
   - Configuration and environment
   - Logs and diagnostic output

3. **Contact infrastructure team with details**

---

**Document Version**: 1.0
**Last Updated**: 2024-05-03
**Status**: Production Ready
