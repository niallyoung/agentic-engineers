---
name: voice-notify-architecture
description: Voice notification architecture - when and where to use voice alerts
---

# Voice Notification Architecture

## Core Principle

**Voice-notify is for INTERACTIVE CONSOLE USE ONLY**

Not for:
- ❌ Cron jobs (background, automated)
- ❌ Email summaries (out-of-band reporting)
- ❌ Log files (passive monitoring)

## When to Use Voice-Notify

### ✅ Interactive Agent Work (Live)

```bash
# You are actively working with an agent in the terminal
# Agent completes a task → voice notification alerts you

python tokenadvisor.py --daily
# [Output: metrics analysis...]
# [Voice: "TokenAdvisor complete. Distribution healthy."]
```

**Use cases:**
- Manual script execution while you're at the terminal
- Debugging/testing agents locally
- Real-time feedback during development
- Immediate alerts when you're actively monitoring

### ✅ Console-Based Automation

When you're running automation directly from CLI (not cron):

```bash
# Running agent suite manually
bash orchestration/scripts/run-agents.sh
# [Each agent completes → voice alert notifies you]
```

---

## When NOT to Use Voice-Notify

### ❌ Cron Jobs (Background)

```bash
# WRONG - cron jobs run unattended
0 17 * * * python tokenadvisor.py && voice-notify.sh "Done"
#                                    ^^^^^^^^^^^^^^^^^^^^^^^^
#                                    You're not there to hear it!
```

**Why:** Cron jobs run in the background, scheduled. No one's listening. Voice alerts are lost.

**Correct approach:** Output to logs + optional email summary

```bash
# RIGHT - cron job outputs to log
0 17 * * * python tokenadvisor.py 2>&1 | tee tokenadvisor-$(date +%Y-%m-%d).log
```

### ❌ Automated Email/Report Pipeline

Voice-notify shouldn't be in:
- Daily email summaries
- Report generation jobs
- Data export scripts
- Scheduled analysis runs

**Correct approach:** These jobs should output to:
- Log files (`data/logs/*.log`)
- JSON reports (`data/reports/*.json`)
- Email messages (via separate mail service)
- Prometheus metrics (`data/prometheus/metrics.txt`)

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│           Agentic Engineers Framework            │
└──────────────────────────────────────────────────┘
          ↓                                    ↓
    ┌─────────────┐                    ┌─────────────┐
    │ Interactive │                    │    Cron     │
    │   (Manual)  │                    │  (Automated)│
    └─────────────┘                    └─────────────┘
          ↓                                    ↓
    ┌─────────────┐                    ┌─────────────┐
    │ stdout/logs │                    │ Log files   │
    │ voice alert │                    │ Email/JSON  │
    │   (speaker) │                    │ Prometheus  │
    └─────────────┘                    └─────────────┘
          ↑                                    ↑
    You at terminal                    Scheduled job
    (can hear alerts)                  (unattended)
```

---

## Implementation Guide

### Voice-Notify Integration Points

Only use voice-notify in these scenarios:

1. **Manual agent runs** (you execute the script directly)
   ```bash
   python agentic-engineers/skills/tokenadvisor/scripts/tokenadvisor.py --daily
   # [Completes → voice alert]
   ```

2. **Interactive debugging** (during development)
   ```bash
   bash agentic-engineers/skills/ab-testing/scripts/ab-testing.py --monitor
   # [Test results → voice alert]
   ```

3. **Direct script invocation with voice output**
   ```bash
   bash agentic-engineers/skills/voice-notify/scripts/voice-notify.sh "Message" --voice Daniel
   ```

### Cron Jobs: Output Strategy

Instead of voice alerts, cron jobs should:

```bash
# Cron job wrapper for TokenAdvisor
0 17 * * * \
  cd {workspace-root}/{service-name} && \
  python ./agentic-engineers/skills/tokenadvisor/scripts/tokenadvisor.py --daily \
    2>&1 | tee ./agentic-engineers/data/logs/tokenadvisor-$(date +\%Y-\%m-\%d).log
```

**Output destinations:**
- ✅ Log file: `data/logs/tokenadvisor-YYYY-MM-DD.log`
- ✅ JSON report: `data/reports/tokenadvisor-YYYY-MM-DD.json`
- ✅ Prometheus: `data/prometheus/metrics.txt`
- ✅ Email: Send summary via mail service
- ✅ Dashboard: Post metrics to Grafana

---

## Summary

| Use Case | Voice Alert | Output to Logs | Email/Report |
|----------|------------|----------------|--------------|
| Manual script run | ✅ YES | Optional | Optional |
| Interactive debugging | ✅ YES | Optional | Optional |
| Cron job (background) | ❌ NO | ✅ YES | ✅ YES |
| Scheduled reports | ❌ NO | ✅ YES | ✅ YES |
| Email summary | ❌ NO | ✅ YES | ✅ YES |

---

## Future: Audio Notifications via System Services

If we want automated alerts while you're NOT at the terminal:

- Use system notifications (OS X Notification Center)
- Use email alerts
- Use Slack/Discord webhooks
- Use push notifications

But NOT voice-notify (that's for interactive console use).
