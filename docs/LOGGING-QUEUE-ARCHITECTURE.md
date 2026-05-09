---
name: logging-queue-architecture
description: Structured logging, queue management, and alert routing for cron jobs
---

# Logging & Queue Architecture

## Current State

```
Cron Job
  └─ stdout/stderr
      └─ tee
          └─ data/logs/tokenadvisor-YYYY-MM-DD.log (text file)
              └─ [dead end - no processing]
```

**Problem:** Logs are written but never processed. No queue, no alerts, no routing.

---

## Proposed Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Cron Job (automated)                       │
│  (TokenAdvisor, Model Engineer, A/B Testing, Daily Summary)  │
└────────────────────────┬─────────────────────────────────────┘
                         ↓
            ┌────────────────────────┐
            │  Structured Log Output │
            │   (JSON + text file)   │
            └────────┬───────────────┘
                     ↓
         ┌───────────────────────┐
         │   Log File Queue      │
         │ data/logs/            │
         │  ├─ tokenadvisor...   │
         │  ├─ model-engineer... │
         │  ├─ ab-testing...     │
         │  └─ daily-summary...  │
         └────────┬──────────────┘
                  ↓
    ┌─────────────────────────────────┐
    │  Log Processor (lightweight)     │
    │  - Parse JSON/text logs         │
    │  - Extract alerts/errors        │
    │  - Route to outputs             │
    └─────┬────────┬────────┬─────────┘
          ↓        ↓        ↓        
      ┌────────┐┌────────┐┌────────┐
      │ Email  ││Metrics ││ Voice  │
      │Alerts  ││for DB  ││(later) │
      └────────┘└────────┘└────────┘
```

---

## Part 1: Structured Log Format

### Log File Locations

```
agentic-engineers/data/logs/
├── tokenadvisor-2026-04-25.log          (text + structured)
├── model-engineer-2026-04-25.log        (text + structured)
├── ab-testing-monitor-2026-04-25.log    (text + structured)
├── daily-email-summary-2026-04-25.log   (text + structured)
└── QUEUE/                               (new: processing queue)
    ├── pending/
    │   └── alert-tokenadvisor-001.json
    ├── processed/
    │   └── alert-tokenadvisor-001.json
    └── failed/
        └── alert-model-engineer-001.json
```

### Log Format: Hybrid Approach

**Recommended:** Write both text and structured JSON to same file

```
# tokenadvisor-2026-04-25.log

[2026-04-25T17:00:15Z] TokenAdvisor starting...
[2026-04-25T17:00:45Z] Aggregated 7-day metrics
[2026-04-25T17:01:22Z] Found inefficiency: Engineer over budget by 3%
[2026-04-25T17:02:11Z] TokenAdvisor complete

===== STRUCTURED LOG =====
{
  "timestamp": "2026-04-25T17:00:00Z",
  "job": "tokenadvisor",
  "status": "success",
  "duration_seconds": 126,
  "metrics": {
    "roles_analyzed": 5,
    "inefficiencies_found": 1,
    "outliers_flagged": 3
  },
  "alerts": [
    {
      "severity": "warning",
      "message": "Engineer over budget by 3%",
      "action": "review_routing",
      "should_email": true,
      "should_voice": false
    }
  ],
  "feeds_to": "model-engineer"
}
===== END STRUCTURED LOG =====
```

**Why hybrid:**
- Text for human readability + debugging
- JSON for machine processing + routing
- Single file = simpler, atomic logging

---

## Part 2: Queue System

### Simple File-Based Queue

```bash
# When alert generated:
agentic-engineers/data/logs/QUEUE/pending/
  alert-{job}-{timestamp}-{priority}.json

# Process script reads pending/ folder
# On success → move to processed/
# On failure → move to failed/
# Retry later from failed/
```

### Queue Processor Script

**Create:** `agentic-engineers/orchestration/scripts/process-log-queue.sh`

```bash
#!/bin/bash
# Process pending alerts from log queue

QUEUE_DIR="agentic-engineers/data/logs/QUEUE"
PENDING="$QUEUE_DIR/pending"
PROCESSED="$QUEUE_DIR/processed"
FAILED="$QUEUE_DIR/failed"

# Create directories
mkdir -p "$PENDING" "$PROCESSED" "$FAILED"

# Process each pending alert
for alert_file in "$PENDING"/*.json; do
    [ -f "$alert_file" ] || continue
    
    echo "Processing: $(basename $alert_file)"
    
    # Extract alert details
    JOB=$(jq -r '.job' "$alert_file")
    SEVERITY=$(jq -r '.severity' "$alert_file")
    MESSAGE=$(jq -r '.message' "$alert_file")
    SHOULD_EMAIL=$(jq -r '.should_email' "$alert_file")
    SHOULD_VOICE=$(jq -r '.should_voice' "$alert_file")
    
    # Route to destinations
    if [ "$SHOULD_EMAIL" = "true" ]; then
        # Send email (implement later)
        echo "EMAIL: [$SEVERITY] $JOB: $MESSAGE"
    fi
    
    if [ "$SHOULD_VOICE" = "true" ]; then
        # Voice alert (implement when TTS ready)
        echo "VOICE: $MESSAGE" >> /tmp/voice-queue.txt
    fi
    
    # Move to processed
    mv "$alert_file" "$PROCESSED/"
done
```

### Cron Schedule: Process Queue

```bash
# Run queue processor every 15 minutes
*/15 * * * * cd /home/user/git/ers/{service-name} && bash agentic-engineers/orchestration/scripts/process-log-queue.sh 2>&1 | tee -a agentic-engineers/data/logs/queue-processor-$(date +\%Y-\%m-\%d).log
```

---

## Part 3: Alert Routing Logic

### Alert Severity Levels

```json
{
  "severity": "critical|error|warning|info|debug",
  "should_email": true|false,
  "should_voice": true|false,
  "should_dashboard": true|false
}
```

### Routing Rules by Job

**TokenAdvisor:**
```
- "Engineer over budget" → email: true, voice: false (info only)
- "Escalation spike" → email: true, voice: false (requires action)
- "Distribution healthy" → email: false, voice: false (no alert needed)
```

**Model Engineer:**
```
- "New routing recommendation" → email: true, voice: false (review needed)
- "A/B test proposal generated" → email: true, voice: false (optional)
```

**A/B Testing:**
```
- "Significant result" → email: true, voice: true (time-sensitive, actionable)
- "Early stop detected" → email: true, voice: true (requires decision)
- "In progress" → email: false, voice: false (passive update)
```

**Daily Summary:**
```
- "Summary ready" → email: true, voice: false (scheduled report)
- "Errors detected" → email: true, voice: false (included in report)
```

---

## Part 4: Email Integration (Future)

### Email Template System

```
agentic-engineers/orchestration/templates/
├── email-alert.html
├── email-summary.html
└── email-error.html
```

### Email Delivery

```bash
# Simple implementation: use `mail` command
# Advanced: integrate with SendGrid, AWS SES, etc.

cat > email-body.txt <<EOF
Alert: Engineer over budget by 3%

Job: TokenAdvisor
Time: 2026-04-25 17:00:00 UTC
Severity: warning

Recommendation: Review task routing to Engineer role.

Full logs: agentic-engineers/data/logs/tokenadvisor-2026-04-25.log
EOF

mail -s "[ERS Alert] TokenAdvisor: Engineer over budget" niall.young@icloud.com < email-body.txt
```

---

## Part 5: Voice Integration (Future)

### Voice Queue (when TTS ready)

```
agentic-engineers/data/voice-queue/
├── pending/
│   └── voice-ab-testing-001.json
└── processed/
    └── voice-ab-testing-001.json
```

### Voice Alert Format

```json
{
  "timestamp": "2026-04-25T18:15:00Z",
  "message": "Significant result. Variant winning. P equals 0.03.",
  "voice": "Daniel",
  "priority": "high",
  "job": "ab-testing"
}
```

### Voice Processor (when TTS ready)

```bash
#!/bin/bash
# Process voice queue when TTS available

for voice_alert in agentic-engineers/data/voice-queue/pending/*.json; do
    MESSAGE=$(jq -r '.message' "$voice_alert")
    VOICE=$(jq -r '.voice' "$voice_alert")
    
    # Use TTS (Kokoro, OpenVoice, etc.)
    bash agentic-engineers/skills/voice-notify/scripts/voice-notify.sh "$MESSAGE" --voice "$VOICE"
    
    mv "$voice_alert" "agentic-engineers/data/voice-queue/processed/"
done
```

---

## Part 6: Dashboard Integration (Future)

### Metrics Export

```bash
# Queue processor also exports metrics to Prometheus
cat > agentic-engineers/data/prometheus/alerts.txt <<EOF
# HELP alert_count Total alerts generated
# TYPE alert_count counter
alert_count{job="tokenadvisor"} 1
alert_count{job="model_engineer"} 0
alert_count{job="ab_testing"} 1
alert_count{severity="warning"} 1
alert_count{severity="error"} 0
EOF
```

---

## Implementation Roadmap

### Phase 1: Structured Logging (Week 1)
- [x] Define log format (text + JSON)
- [ ] Update cron jobs to output structured JSON
- [ ] Create example alert JSON
- [ ] Commit to git

### Phase 2: File-Based Queue (Week 2)
- [ ] Create queue directory structure
- [ ] Write process-log-queue.sh
- [ ] Add to cron (every 15 min)
- [ ] Test with sample alerts

### Phase 3: Email Alerts (Week 3)
- [ ] Create email templates
- [ ] Implement mail routing
- [ ] Test email delivery
- [ ] Set alert rules per job

### Phase 4: Voice Integration (When TTS Ready)
- [ ] Create voice queue processor
- [ ] Integrate with Kokoro/OpenVoice
- [ ] Test with selected voices
- [ ] Schedule voice processor

### Phase 5: Dashboard Visualization (Week 5)
- [ ] Export metrics to Prometheus
- [ ] Create Grafana dashboard for alerts
- [ ] Show alert history + trends
- [ ] Link to detailed logs

---

## Quick Summary Table

| Component | Current | Proposed | Timeline |
|-----------|---------|----------|----------|
| Log format | Plain text | Text + JSON | Week 1 |
| Queue system | None | File-based | Week 2 |
| Email alerts | None | Integrated | Week 3 |
| Voice alerts | None | Ready (TTS needed) | TBD |
| Dashboard | None | Prometheus export | Week 5 |

---

## File Structure After Implementation

```
agentic-engineers/
├── orchestration/
│   ├── scripts/
│   │   ├── process-log-queue.sh (NEW)
│   │   └── ...
│   ├── templates/
│   │   ├── email-alert.html (NEW)
│   │   ├── email-summary.html (NEW)
│   │   └── email-error.html (NEW)
│   └── config/
│       ├── alert-rules.json (NEW)
│       └── *.cron
├── data/
│   ├── logs/
│   │   ├── tokenadvisor-YYYY-MM-DD.log (enhanced: text + JSON)
│   │   ├── model-engineer-YYYY-MM-DD.log
│   │   ├── ab-testing-YYYY-MM-DD.log
│   │   ├── queue-processor-YYYY-MM-DD.log (NEW)
│   │   └── QUEUE/ (NEW)
│   │       ├── pending/
│   │       ├── processed/
│   │       └── failed/
│   ├── voice-queue/ (NEW - for TTS alerts)
│   │   ├── pending/
│   │   └── processed/
│   └── prometheus/
│       └── alerts.txt (NEW)
└── skills/
    └── voice-notify/
        └── TODO.md (TTS research)
```

---

## Key Benefits

1. **Visibility:** Structured logging + dashboard
2. **Flexibility:** Routing rules per job/severity
3. **Durability:** File-based queue survives restarts
4. **Extensibility:** Easy to add email/voice/Slack later
5. **Debugging:** Full audit trail + failed alerts retained
6. **Scalability:** Can upgrade to proper queue system (Redis, RabbitMQ) later

---

**Ready to implement Phase 1 (structured logging)?**
