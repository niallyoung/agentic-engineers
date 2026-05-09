---
name: ERS CICD Monitoring & Failure Response
description: Efficient GitHub Actions build monitoring with immediate failure detection and sub-agent delegation
type: skill
delegable_to: [Orchestrator, Quality Engineer]
---

# ERS CICD Monitoring & Immediate Failure Response

## The Pattern

**Goal**: Monitor builds until green, fix issues immediately without waiting for full sleep intervals, conserve tokens.

**Approach**:
- **120-second sleep intervals** between checks (not active polling)
- **Immediate action on failure** (exit loop, delegate to sub-agent)
- **Checkpoint on success** (confirm all services green)
- **Token conservation** (SLEEP, don't poll during wait)

## Why 120 Seconds?

- **Cache efficiency**: Anthropic prompt cache has 5-minute TTL
  - Under 300s: cache stays warm (fast, cheaper)
  - 300s+: cache miss (slower, more tokens)
  - 120s picks the sweet spot within cache window
- **Build time alignment**: Most ERS services build in 3-5 minutes
  - 120s interval = 2-4 checks per build
  - Fine-grained enough to catch failures quickly
  - Not so frequent that we're constantly re-reading context

## Architecture: Token-Conserving Monitoring

```
Check #1 (now)
  ├─ Success → exit
  ├─ Failure → exit (delegate to QE)
  └─ Still running → sleep 120s
     ↓
Check #2 (after 120s sleep)
  ├─ Success → exit
  ├─ Failure → exit (delegate to QE)
  └─ Still running → sleep 120s
     ↓
Check #3 (after 120s sleep)
  ... and so on
```

**Key**: During the 120-second sleep, we do NOTHING. No polling. No token usage. Just wait.

## Implementation Pattern

### Shell Script (Background Task)

```bash
#!/bin/bash
# CICD monitoring: sleep 120s between checks, immediate action on failure

check_builds() {
  # Query GitHub for build status (single API call)
  event_conclusion=$(gh run list -R {your-org}/{service-name} -L 1 --json conclusion --template '{{range .}}{{.conclusion}}{{end}}')
  query_conclusion=$(gh run list -R {your-org}/{service-name} -L 1 --json conclusion --template '{{range .}}{{.conclusion}}{{end}}')
  
  # Check for failure (immediate exit if detected)
  if [ "$event_conclusion" = "failure" ]; then
    echo "❌ FAILURE DETECTED"
    return 1  # Signal failure
  fi
  
  if [ "$query_conclusion" = "failure" ]; then
    echo "❌ FAILURE DETECTED"
    return 1
  fi
  
  # Check for success (both green)
  if [ "$event_conclusion" = "success" ] && [ "$query_conclusion" = "success" ]; then
    echo "✅ SUCCESS"
    return 0
  fi
  
  # Still running
  return 2
}

# Main loop: check, sleep, repeat
while true; do
  check_builds
  result=$?
  
  [ $result -eq 0 ] && exit 0      # Success
  [ $result -eq 1 ] && exit 1      # Failure (delegate)
  
  # Still running: sleep 120s (NOT polling during this time)
  echo "💤 Sleeping 120 seconds..."
  sleep 120
done
```

### Confirming Token Conservation

When you start the monitor, you'll see:

```
✅ Confirmed: 120-second sleep intervals
✅ Confirmed: NOT actively polling during sleep
✅ Confirmed: Will exit immediately on failure or success
✅ Confirmed: Token-conserving approach
```

This confirms:
1. **We sleep** (not polling every few seconds)
2. **We check once** after sleep
3. **We act immediately** on success/failure (don't wait)

## Failure Detection & Response

When a build fails, the monitor exits with code 1 and outputs:

```
❌ {service-name} #43 FAILED
```

**At this point**, you (the Orchestrator) should:

1. **Stop this background task** (monitor has already exited)
2. **Investigate** using `{service-name}.md` or similar
3. **Delegate to Quality Engineer** using `{service-name}.md` DELEGATE format
4. **QE executes fixes**, runs `make verify`, commits
5. **Push triggers new build** (monitor resumes watching)
6. **Continue until green**

## Starting the Monitor

```bash
# Start monitoring (runs in background)
/path/to/cicd-monitor-120s.sh &

# Or using Bash background task:
bash /tmp/cicd-monitor-120s.sh &
```

## Checking Monitor Status

```bash
# See what it's doing
tail -f /private/tmp/claude-501/.../tasks/[task_id].output

# Current iteration count
grep "Check #" /private/tmp/claude-501/.../tasks/[task_id].output | tail -1
```

## Workflow Integration with agentic-engineers

```yaml
Orchestrator (watching builds)
  ├─ Starts monitor (120s sleep intervals)
  ├─ Monitor runs in background
  │
  ├─ [120s sleep... no token usage...]
  │
  └─ Monitor checks after sleep
      ├─ Success → confirm green, exit
      ├─ Failure → EXIT, trigger DELEGATE
      │    │
      │    ├─ Read failure details
      │    ├─ Use {service-name}.md or {service-name}.md
      │    └─ DELEGATE to Quality Engineer
      │         │
      │         ├─ QE investigates
      │         ├─ QE fixes issues
      │         ├─ QE pushes (triggers new build)
      │         └─ QE HANDBACK with metrics
      │
      └─ Orchestrator resumes monitoring
```

## Handling Multiple Services

For monitoring multiple services ({service-name}, {service-name}, etc.):

```bash
check_all_services() {
  local all_success=true
  
  for repo in {service-name} {service-name} {service-name} {service-name}; do
    conclusion=$(gh run list -R "{your-org}/$repo" -L 1 --json conclusion --template '{{range .}}{{.conclusion}}{{end}}')
    
    if [ "$conclusion" = "failure" ]; then
      echo "❌ $repo FAILED"
      return 1
    fi
    
    if [ "$conclusion" != "success" ]; then
      all_success=false
    fi
  done
  
  [ "$all_success" = true ] && return 0 || return 2
}
```

## Common Scenarios

### Scenario 1: Build Still Running
```
⏳ Still building... (event: in_progress, query: in_progress)
💤 Sleeping 120 seconds...
[after 120s]
⏳ Still building... (event: in_progress, query: in_progress)
💤 Sleeping 120 seconds...
```

**Action**: Continue waiting. Nothing to do.

### Scenario 2: Build Succeeds
```
⏳ Still building...
💤 Sleeping 120 seconds...
[after 120s]
✅ BOTH GREEN: {service-name} #25 + {service-name} #43
✅ SUCCESS - exiting
```

**Action**: Monitor exits. Confirm with user, move to next task.

### Scenario 3: Build Fails (Immediate Response)
```
⏳ Still building...
💤 Sleeping 120 seconds...
[after 120s]
❌ {service-name} #43 FAILED
[Monitor exits with code 1]
```

**Action**: 
1. Stop monitor
2. Check logs: `gh run view [run-id] -R {your-org}/{service-name} --log`
3. Investigate error
4. Use `{service-name}.md` to DELEGATE fixes to QE
5. QE fixes and pushes
6. Resume monitoring

## Token Impact Analysis

### Old Approach (Active Polling Every 15 Seconds)
```
Per hour:
- 60 min ÷ 0.25 min (15 sec) = 240 checks/hour
- Each check: ~5KB tokens (API calls + context)
- Total: ~1200KB tokens/hour = expensive

Per build (3 min avg):
- 3 min ÷ 0.25 min = 12 checks
- 12 checks × 5KB = 60KB tokens per build
```

### New Approach (120-Second Intervals)
```
Per hour:
- 60 min ÷ 2 min (120 sec) = 30 checks/hour
- Each check: ~5KB tokens
- Total: ~150KB tokens/hour = 8× more efficient

Per build (3 min avg):
- 3 min ÷ 2 min = 1.5 checks (usually 1)
- 1 check × 5KB = 5KB tokens per build
- Plus 1 check on failure: ~10KB total
```

**Savings**: ~85% token reduction on monitoring vs active polling.

## Scheduling with ScheduleWakeup

For longer waits (multiple builds or checking multiple branches):

```bash
# Orchestrator code
wakeup=$(ScheduleWakeup \
  delaySeconds=120 \
  reason="checking if {service-name} #43 build completed" \
  prompt="watch github builds until green, fix any issues")

# Returns a wakeup object that resumes after 120s
# During sleep: NO TOKEN USAGE
# After sleep: Resume and check again
```

## Automation Checklist

When implementing CICD monitoring:

- [ ] Create monitor script with 120s sleep intervals
- [ ] Confirm message shows "NOT actively polling"
- [ ] Monitor exits immediately on success/failure (doesn't wait)
- [ ] Background task ID is captured for status checking
- [ ] Tail command works to watch monitor output
- [ ] Failure detection triggers immediate DELEGATE to QE
- [ ] QE knows to use `{service-name}.md` for fixes
- [ ] Process documented in runbook for future use

## When to Use This Pattern

✅ **Use 120s monitoring for**:
- Watching GitHub Actions builds until complete
- Monitoring multiple ERS services in parallel
- Waiting for long-running deployments
- Allowing time for fixes without constant checking

❌ **Don't use for**:
- High-frequency data polling (needs <15s updates)
- Real-time dashboards (users expect <5s updates)
- Safety-critical systems (where delay could cause issues)

## Limitations & Gotchas

1. **120s is a minimum**: If you need faster detection, use ScheduleWakeup with 60s instead
2. **Sleep happens regardless**: Even if build finishes in 60s, we still sleep 120s (by design—batch efficiency)
3. **Multiple services**: Query multiple repos in single check to avoid N×API calls
4. **Token cache**: 5min TTL means we get cache hits if spaced <300s apart

## Troubleshooting

**Monitor seems stuck**:
```bash
# Check if background task is alive
jobs -l
ps aux | grep cicd-monitor-120s.sh

# Read output
cat /private/tmp/claude-501/.../tasks/[task_id].output
```

**Monitor exited unexpectedly**:
- Check exit code: success (0), failure (1), or error (2+)
- If success: builds are green ✅
- If failure: investigate and delegate
- If error: check script syntax

**Builds still running after 2+ hours**:
- Something is stuck in CI/CD
- Check GitHub Actions logs directly
- May need manual intervention (cancel build, restart)

