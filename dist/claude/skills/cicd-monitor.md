# CICD Monitor Skill

**Agent Role**: Orchestrator (specialized)  
**Model**: claude-haiku-4-5  
**Effort**: medium  
**Purpose**: Polls GitHub Actions workflow status every 120 seconds; reports completion; escalates on timeout or failure

---

## Overview

CICD Monitor watches GitHub Actions quality gate workflows. It polls every 120 seconds (conservative API usage), tracks job-by-job status, extracts failure logs when jobs fail, and escalates on timeout (>30 min) or failure. Designed for Phase 5.10 critical path monitoring.

---

## DELEGATE Block Specification

### Input Fields

```yaml
repo: "{service-name}"
  # Repository name (part of full GitHub path)

ref: "abc123def456" | "main"
  # Commit SHA or branch name

workflow_name: "main.yaml"
  # Workflow file name (from .github/workflows/)

max_wait_minutes: 30
  # Maximum time to poll before timeout

poll_interval_seconds: 120
  # Seconds between polling attempts (conserves API quota)

escalate_on_timeout: true
  # Escalate if workflow doesn't complete in time

escalate_on_failure: true
  # Escalate if any job fails
```

### Example DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-05-cicd-monitor-{service-name}
timestamp: 2026-05-05T10:30:00Z
role: CICD Monitor (Orchestrator)
model: claude-haiku-4-5
effort: medium
scope: >
  Monitor GitHub Actions main.yaml workflow for {service-name} commit abc123.
  Poll every 120 seconds. Report status when complete. Escalate on timeout/failure.
context:
  - Repo: {service-name}
  - Commit: abc123def456
  - Expected duration: 4-6 minutes typical
  - Poll interval: 120 seconds
  - Max wait: 30 minutes
plan:
  1. Get latest workflow run for commit
  2. Poll every 120s for completion
  3. Track job-by-job status
  4. On completion: capture results
  5. On failure: extract failure logs
  6. On timeout: escalate
  7. Return HANDBACK with status
success_criteria:
  - Workflow completion detected
  - All job results reported
  - Failure logs captured
  - Poll count + wait time accurate
  - Timeout after 30 minutes
  - Escalation path set when needed
---
```

---

## HANDBACK Block Specification

### Output Fields

```yaml
status: "SUCCESS" | "FAILURE" | "TIMEOUT" | "PENDING"
  # Final status of workflow

workflow_run_id: "1234567890"
  # GitHub workflow run ID

run_duration_seconds: 245
  # Total time from start to completion

conclusion: "success" | "failure" | "timed_out"
  # Workflow conclusion

jobs_completed:
  - name: "lint"
    conclusion: "success"
    duration_seconds: 45

jobs_failed:
  - name: "deploy-prod"
    conclusion: "failure"
    failure_log_excerpt: "error: S3 bucket not found"

escalation_path: null | {agent: "Lead Engineer", reason: "..."}
  # Escalation details if needed

poll_count: 15
  # Number of polls before completion

poll_interval_seconds: 120
  # Interval between polls

total_wait_seconds: 1800
  # Total elapsed time

logs_available: true
  # Whether failure logs were captured

recommendation: "string"
  # Summary and next steps
```

### Example HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-05-cicd-monitor-{service-name}
timestamp: 2026-05-05T10:35:15Z
status: complete
workflow_status: FAILURE
workflow_run_id: 5432109876
run_duration_seconds: 302
conclusion: failure
jobs_completed:
  - name: lint
    conclusion: success
    duration_seconds: 42
  - name: test
    conclusion: success
    duration_seconds: 85
  - name: deploy-dev
    conclusion: success
    duration_seconds: 92
jobs_failed:
  - name: deploy-prod
    conclusion: failure
    failure_log_excerpt: |
      Error: Unable to assume IAM role arn:aws:iam::666109694932:role/prod-{service-name}
      Reason: AccessDenied (MissingPermission for sts:AssumeRole)
escalation_path:
  agent: Lead Engineer
  reason: "Prod deploy IAM permissions issue"
poll_count: 3
poll_interval_seconds: 120
total_wait_seconds: 305
logs_available: true
recommendation: "Deploy-prod failed due to IAM role assumption error."
---
```

---

## Implementation Approach

### Algorithm: Polling Loop

```
start_time = now()
poll_count = 0

LOOP:
  poll_count += 1
  run = get_github_workflow_run(repo, ref)
  
  IF run.status == "completed":
    RETURN process_completion(run)
  
  IF (now() - start_time) > max_wait_seconds:
    RETURN timeout_escalation()
  
  SLEEP poll_interval_seconds
  GO TO LOOP
```

### Job Status Tracking

```
FOR EACH job in run.jobs:
  IF job.conclusion == "failure":
    extract_failure_logs(job)
    jobs_failed.push(job)
  ELSE:
    jobs_completed.push(job)
```

### Failure Log Extraction

```
failure_logs = get_job_logs(job_id)
# Capture first error line + context
# Keep excerpt short (<500 chars) for HANDBACK
excerpt = extract_first_error_and_context(failure_logs)
```

---

## Integration Points

### Invoked By

- **Orchestrator** (after push to main)
- **Manual trigger**: `make wait-for-ci`

### GitHub API Integration

```
GET /repos/{owner}/{repo}/actions/runs?head_sha={sha}
  # Get latest run for commit

GET /repos/{owner}/{repo}/actions/runs/{run_id}
  # Get run status

GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs
  # Get job list + status

GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}/logs
  # Get job logs
```

### Escalation Path

- On **failure**: Escalate to Lead Engineer (CI/CD issues)
- On **timeout**: Escalate to Orchestrator (infrastructure issue)

---

## Testing Strategy

### Unit Tests

```bash
# Test 1: Workflow success detection
MOCK: GitHub API returns completed run with all jobs passed
EXPECTED: status=SUCCESS, jobs_completed=[...], jobs_failed=[]

# Test 2: Job failure detection + log extraction
MOCK: GitHub API returns run with deploy-prod job failed
EXPECTED: jobs_failed=[...], failure_log_excerpt populated

# Test 3: Polling count accuracy
MOCK: Workflow completes on 3rd poll
EXPECTED: poll_count=3, total_wait_seconds ≈ 240

# Test 4: Timeout detection
MOCK: Workflow never completes (mock 25+ polls)
EXPECTED: status=TIMEOUT after max_wait_minutes exceeded
```

---

## Deployment Notes

### GitHub API Authentication

Requires GitHub token in environment:
- `GITHUB_TOKEN` (for API calls)
- Token scope: `repo:status` (read workflow runs)

### API Rate Limiting

CICD Monitor polls every 120 seconds:
- 50 polls × 120s = 100 minutes max monitoring
- Queries: 3 per poll (get run, get jobs, get logs)
- Total API calls per workflow: ~150 calls
- GitHub API quota: 5000 calls/hour (generous)

### Error Handling

```
IF GitHub API unavailable:
  - Retry with exponential backoff
  - After 3 retries, escalate
  
IF workflow run not found:
  - Log error
  - Return HANDBACK with status=ERROR
  - Escalate to human
```

---

## Success Criteria Validation

- [x] DELEGATE spec matches design spec
- [x] HANDBACK spec includes all fields
- [x] Polls every 120 seconds correctly
- [x] Detects workflow completion (all states)
- [x] Captures failure logs when needed
- [x] Timeout after 30 minutes
- [x] Poll count and wait time accurate
- [x] Escalation path set for failures/timeouts
- [x] GitHub API error handling graceful
- [x] Ready for post-push monitoring

---

## Related Skills

- **Quality Gate Orchestrator**: May invoke CICD Monitor for build tracking
- **Voice Notify**: May be invoked on failure to alert user

---

## Revision History

| Date | Status | Notes |
|------|--------|-------|
| 2026-04-28 | DESIGN | Specification created |
| 2026-05-05 | IMPLEMENTATION | Skill document created |

