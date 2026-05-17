# Quick Start: Production Deployment

**Time to complete:** 15 minutes  
**Prerequisite:** Framework installed and tested locally

---

## Overview

This guide covers deploying the agentic-engineers framework to a production environment where the Orchestrator runs continuously, processing tasks autonomously.

---

## Step 1: Install the Framework

```bash
git clone https://github.com/niallyoung/agentic-engineers.git
cd agentic-engineers

# Install for your target harness
make install-opencode    # OpenCode (recommended)
make install-claude      # Claude Code

# Verify installation
make status-opencode
make verify
```

---

## Step 2: Run the Automation Controller

The AutomationController runs the Orchestrator in a continuous polling loop:

```bash
# Start the automation controller
bin/run-automation-controller.sh

# With custom settings
ORCHESTRATOR_POLL_INTERVAL=10 \
ORCHESTRATOR_IDLE_TIMEOUT=120 \
bin/run-automation-controller.sh
```

**Environment variables:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `ORCHESTRATOR_POLL_INTERVAL` | 30 | Seconds between queue polls |
| `ORCHESTRATOR_IDLE_TIMEOUT` | 60 | Seconds before idle shutdown |
| `QUEUE_DIR` | `artifacts/queue/` | Queue directory path |
| `ARTIFACTS_DIR` | `artifacts/` | Artifacts directory path |

---

## Step 3: Deployment Scenarios

### Scenario A: Standalone (Development/Testing)

```bash
# Run directly in terminal
bin/run-automation-controller.sh
```

### Scenario B: systemd Service (Linux Production)

```bash
# Create service file
cat > /etc/systemd/system/agentic-engineers.service <<'EOF'
[Unit]
Description=Agentic Engineers Orchestrator
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/agentic-engineers
ExecStart=/path/to/agentic-engineers/bin/run-automation-controller.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
systemctl enable agentic-engineers
systemctl start agentic-engineers
systemctl status agentic-engineers
```

### Scenario C: Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt
RUN make install

CMD ["bin/run-automation-controller.sh"]
```

```bash
docker build -t agentic-engineers .
docker run -d \
  -v ~/.config/opencode:/root/.config/opencode \
  -v $(pwd)/artifacts:/app/artifacts \
  agentic-engineers
```

### Scenario D: Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentic-engineers-orchestrator
spec:
  replicas: 1  # Single orchestrator per queue
  selector:
    matchLabels:
      app: agentic-engineers
  template:
    metadata:
      labels:
        app: agentic-engineers
    spec:
      containers:
      - name: orchestrator
        image: your-registry/agentic-engineers:latest
        command: ["bin/run-automation-controller.sh"]
        env:
        - name: ORCHESTRATOR_POLL_INTERVAL
          value: "30"
        volumeMounts:
        - name: queue
          mountPath: /app/artifacts/queue
      volumes:
      - name: queue
        persistentVolumeClaim:
          claimName: agentic-engineers-queue-pvc
```

---

## Step 4: Verify Production Health

```bash
# Check queue state
ls artifacts/queue/incoming/    # Pending tasks
ls artifacts/queue/processing/  # In-progress tasks
ls artifacts/queue/done/        # Completed tasks

# Check metrics
ls artifacts/metrics/           # Per-task metrics

# Run compliance audit
python3 src/orchestration/tools/protocol_audit.py
# Expected: Compliance Score: 100/100 ✅

# Run full test suite
make test
```

---

## Step 5: Monitor in Production

```bash
# Watch queue activity
watch -n 5 'ls -la artifacts/queue/incoming/ artifacts/queue/processing/'

# Monitor token usage (OpenCode)
watch -n 30 'opencode-tokens --session <session-id>'

# Check for stuck tasks (processing > 2 hours)
find artifacts/queue/processing/ -mmin +120 -name "*.yaml"
```

---

## Troubleshooting

**Task stuck in processing:**
```bash
# Check if agent is still running
ps aux | grep opencode

# Force move stuck task back to incoming
mv artifacts/queue/processing/stuck-task.yaml artifacts/queue/incoming/
```

**Queue not being polled:**
```bash
# Verify Orchestrator is running
systemctl status agentic-engineers

# Check logs
journalctl -u agentic-engineers -f

# Restart
systemctl restart agentic-engineers
```

**Quality gate failures:**
```bash
# Check HANDBACK for failed task
cat artifacts/queue/done/failed-task.yaml

# Review quality score and routing decision
grep -A5 "quality_score" artifacts/queue/done/failed-task.yaml
```

---

## Production Checklist

Before going live:

- [ ] `make test` passes (all 1047+ tests)
- [ ] `make verify` passes (SPEC compliance)
- [ ] `make status-opencode` shows all agents installed
- [ ] Queue directories exist: `artifacts/queue/incoming/`, `processing/`, `done/`
- [ ] Git hooks installed: `ls .git/hooks/` shows pre-commit, commit-msg, pre-push
- [ ] Token budget set and monitored
- [ ] Alerting configured for stuck tasks (>2 hours in processing)
- [ ] Log rotation configured for `logs/`

---

## Related Documentation

- [docs/PHASE-3-DEPLOYMENT-PLAYBOOK.md](PHASE-3-DEPLOYMENT-PLAYBOOK.md) — Detailed deployment playbook
- [docs/PHASE-3-PRODUCTION-READINESS-CHECKLIST.md](PHASE-3-PRODUCTION-READINESS-CHECKLIST.md) — Full readiness checklist
- [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Troubleshooting guide (30+ scenarios)
- [docs/BYPASS-PROCEDURES.md](BYPASS-PROCEDURES.md) — Emergency procedures
