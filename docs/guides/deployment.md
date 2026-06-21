# Production Deployment Guide: Continuous Polling Loop Automation

## Overview

This guide provides complete instructions for deploying the **Continuous Polling Loop Automation** system to production. The system continuously polls a task queue, reads DELEGATE files, spawns agents, and collects metrics.

**Key Components:**
- `Orchestrator`: Task orchestration and delegation with polling loop
- `QueueManager`: Queue state management
- Entrypoint script: Production-ready startup wrapper

**Architecture:** [See docs/architecture/continuous-polling.md](../architecture/continuous-polling.md)

---

## Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended) or macOS 10.15+
- **Python**: 3.8 or higher
- **Disk Space**: Minimum 2GB for queue and logs
- **Memory**: Minimum 512MB (1GB+ recommended)
- **CPU**: Single core minimum (multi-core for high throughput)

### Software Dependencies
```bash
# Verify Python 3.8+
python3 --version

# Verify pip
pip3 --version

# Install required packages (if not already installed)
pip3 install pyyaml  # For YAML parsing
pip3 install pytest  # For testing
```

### Project Setup
```bash
# Clone repository
git clone <repo-url> /opt/orchestrator
cd /opt/orchestrator

# Verify structure
ls -la
# Should see: bin/, orchestration/, data/, docs/, etc.

# Set project root environment variable
export PROJECT_ROOT=/opt/orchestrator
```

---

## Installation

### 1. Copy Project Files

```bash
# Copy application to production location
sudo cp -r /path/to/agentic-engineers /opt/orchestrator

# Set permissions
sudo chown -R orchestrator:orchestrator /opt/orchestrator
sudo chmod -R 755 /opt/orchestrator
sudo chmod +x /opt/orchestrator/bin/run-automation-controller.sh
```

### 2. Create Required Directories

```bash
# Create queue directories
mkdir -p /opt/orchestrator/data/queue/{incoming,done}
mkdir -p /opt/orchestrator/logs

# Set permissions
chmod 755 /opt/orchestrator/data/queue/{incoming,done}
chmod 755 /opt/orchestrator/logs
```

### 3. Configure Environment

```bash
# Copy production configuration
cp /opt/orchestrator/.env.production /opt/orchestrator/.env

# Edit configuration for your environment
vim /opt/orchestrator/.env
```

Key configuration options:
- `POLL_INTERVAL_SECONDS`: Adjust based on expected task frequency
- `LOG_LEVEL`: Set to `INFO` for production
- `AUTOMATION_DAEMON_MODE`: Set to `true` for continuous running
- `METRICS_FILE`: Point to your metrics collection system

### 4. Test Installation

```bash
# Test entrypoint script
cd /opt/orchestrator
./bin/run-automation-controller.sh --help

# Run a test cycle with max_cycles limit
AUTOMATION_MAX_CYCLES=5 ./bin/run-automation-controller.sh
```

---

## Deployment Scenarios

### Scenario 1: Standalone Server

**Best for:** Single-node deployments with moderate load

```bash
# 1. SSH to production server
ssh orchestrator@prod-server.example.com

# 2. Navigate to project
cd /opt/orchestrator

# 3. Source environment
source .env

# 4. Run in background with nohup
nohup ./bin/run-automation-controller.sh > /tmp/automation.log 2>&1 &
echo $! > /tmp/automation.pid

# 5. Monitor
tail -f /tmp/automation.log
```

### Scenario 2: Systemd Service

**Best for:** Production systems with service management

```bash
# 1. Create systemd service file
sudo tee /etc/systemd/system/orchestrator-automation.service << EOF
[Unit]
Description=Orchestrator Continuous Polling Automation
After=network.target

[Service]
Type=simple
User=orchestrator
WorkingDirectory=/opt/orchestrator
EnvironmentFile=/opt/orchestrator/.env
ExecStart=/opt/orchestrator/bin/run-automation-controller.sh
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 2. Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable orchestrator-automation.service
sudo systemctl start orchestrator-automation.service

# 3. Check status
sudo systemctl status orchestrator-automation.service

# 4. View logs
sudo journalctl -u orchestrator-automation.service -f
```

### Scenario 3: Docker Container

**Best for:** Containerized/Kubernetes deployments

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /opt/orchestrator

# Copy application
COPY . .

# Install dependencies
RUN pip install pyyaml

# Create non-root user
RUN useradd -m orchestrator
RUN chown -R orchestrator:orchestrator /opt/orchestrator

USER orchestrator

# Set entrypoint
ENTRYPOINT ["/opt/orchestrator/bin/run-automation-controller.sh"]

# Health check (monitors log output)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD test -n "$(find /opt/orchestrator/logs -name 'automation-*.log' -mmin -1)" || exit 1
```

Build and run:
```bash
# Build image
docker build -t orchestrator-automation:latest .

# Run container
docker run -d \
  --name orchestrator-automation \
  -v /opt/queue:/opt/orchestrator/data/queue \
  -v /opt/logs:/opt/orchestrator/logs \
  -e POLL_INTERVAL_SECONDS=5 \
  -e LOG_LEVEL=INFO \
  orchestrator-automation:latest

# Check logs
docker logs -f orchestrator-automation
```

### Scenario 4: Kubernetes Deployment

**Best for:** Cloud-native/orchestrated environments

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator-automation
spec:
  replicas: 1
  selector:
    matchLabels:
      app: orchestrator-automation
  template:
    metadata:
      labels:
        app: orchestrator-automation
    spec:
      containers:
      - name: automation
        image: orchestrator-automation:latest
        imagePullPolicy: IfNotPresent
        env:
        - name: POLL_INTERVAL_SECONDS
          value: "5"
        - name: LOG_LEVEL
          value: "INFO"
        - name: AUTOMATION_DAEMON_MODE
          value: "true"
        volumeMounts:
        - name: queue
          mountPath: /opt/orchestrator/data/queue
        - name: logs
          mountPath: /opt/orchestrator/logs
        resources:
          limits:
            memory: "1Gi"
            cpu: "1"
          requests:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: queue
        hostPath:
          path: /mnt/queue
      - name: logs
        hostPath:
          path: /mnt/logs
```

Deploy:
```bash
kubectl apply -f k8s-deployment.yaml
```

---

## Configuration Tuning

### Performance Tuning

#### For High-Throughput Environments
```bash
# Reduce polling interval to check queue more frequently
POLL_INTERVAL_SECONDS=2

# Increase log level to reduce I/O
LOG_LEVEL=WARNING
```

#### For Low-Resource Environments
```bash
# Increase polling interval to reduce CPU usage
POLL_INTERVAL_SECONDS=10

# Enable structured logging for efficient parsing
STRUCTURED_LOGGING=true
```

#### For Debug/Testing
```bash
# Short intervals and debug logging
POLL_INTERVAL_SECONDS=1
LOG_LEVEL=DEBUG
AUTOMATION_MAX_CYCLES=100  # For testing
```

---

## Monitoring & Observability

### Health Check Endpoint

The entrypoint script provides health monitoring capabilities:

```bash
# Check health status via logs
tail -f /opt/orchestrator/logs/automation-*.log
```

### Logging

Logs are written to:
- **Console**: Real-time visibility
- **File**: `/opt/orchestrator/logs/automation-{timestamp}.log`

Monitor logs in real-time:
```bash
# Tail logs
tail -f /opt/orchestrator/logs/automation-*.log

# Search for errors
grep ERROR /opt/orchestrator/logs/automation-*.log

# Follow log file as it grows
tail -f /opt/orchestrator/logs/automation-*.log | grep -E "ERROR|WARN"
```

### Metrics Collection

Metrics are collected and stored for analysis:
- **Directory**: `/opt/orchestrator/metrics/` (for local backup and analysis)

View logs for metrics tracking:
```bash
# Monitor metrics via logs
tail -f /opt/orchestrator/logs/automation-*.log | grep -i metric
```

---

## Backup & Recovery

### Queue Backup

```bash
# Backup queue directories
tar -czf /backups/queue-$(date +%Y%m%d-%H%M%S).tar.gz \
  /opt/orchestrator/data/queue/

# Backup logs
tar -czf /backups/logs-$(date +%Y%m%d-%H%M%S).tar.gz \
  /opt/orchestrator/logs/

# Backup metrics
tar -czf /backups/metrics-$(date +%Y%m%d-%H%M%S).tar.gz \
  /opt/orchestrator/metrics/
```

### Recovery Procedure

```bash
# 1. Stop the automation controller
sudo systemctl stop orchestrator-automation.service

# 2. Restore from backup
tar -xzf /backups/queue-YYYYMMDD-HHMMSS.tar.gz -C /

# 3. Verify restored files
ls -la /opt/orchestrator/data/queue/

# 4. Restart the service
sudo systemctl start orchestrator-automation.service

# 5. Monitor recovery
sudo journalctl -u orchestrator-automation.service -f
```

---

## Scaling Considerations

### Single Instance
- Simple to manage
- No distributed coordination needed
- Sufficient for moderate task volumes (< 1000 tasks/day)

### Multiple Instances (Recommended)
- Use shared NFS or S3 for queue directory
- Implement distributed locking to prevent duplicate processing
- Load balance incoming DELEGATE files
- Monitor for task duplication

```bash
# Example: Multiple instances with NFS
# /opt/orchestrator/data/queue -> NFS mount
# ORCHESTRATOR_QUEUE_DIR=/mnt/nfs/queue

# Each instance reads from same queue
# Requires file locking to prevent race conditions
```

---

## Maintenance

### Regular Tasks

**Daily:**
- Monitor logs for errors
- Check disk space
- Review metrics for anomalies

**Weekly:**
- Archive old logs
- Review performance metrics
- Test recovery procedures

**Monthly:**
- Review and optimize configuration
- Update dependencies
- Full system backup

### Log Rotation

```bash
# Setup logrotate for automatic rotation
sudo tee /etc/logrotate.d/orchestrator << EOF
/opt/orchestrator/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 orchestrator orchestrator
    sharedscripts
}
EOF
```

### Dependency Updates

```bash
# Check for updates
pip3 list --outdated

# Update dependencies carefully in test environment first
pip3 install --upgrade pyyaml
```

---

## Troubleshooting

For common issues and solutions, see: **[docs/troubleshooting-continuous-polling.md](troubleshooting-continuous-polling.md)**

---

## Support

For issues or questions:
1. Check troubleshooting guide
2. Review logs with debug logging enabled
3. Verify configuration against this guide
4. Contact infrastructure team

---

## Appendix: Quick Reference

```bash
# Start automation (systemd)
sudo systemctl start orchestrator-automation.service

# Stop automation (graceful shutdown)
sudo systemctl stop orchestrator-automation.service

# Restart automation
sudo systemctl restart orchestrator-automation.service

# Check status
sudo systemctl status orchestrator-automation.service

# View logs
sudo journalctl -u orchestrator-automation.service -f

# Manual run (useful for debugging)
cd /opt/orchestrator
source .env
./bin/run-automation-controller.sh

# Run with debug logging
LOG_LEVEL=DEBUG ./bin/run-automation-controller.sh

# Run with max cycles (for testing)
AUTOMATION_MAX_CYCLES=10 ./bin/run-automation-controller.sh

# Find latest metrics
ls -lt /opt/orchestrator/metrics/ | head -5
```

---

**Document Version**: 1.0
**Last Updated**: 2024-05-03
**Status**: Production Ready
