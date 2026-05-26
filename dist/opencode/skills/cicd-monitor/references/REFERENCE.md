# CI/CD Monitor — Reference Documentation

## Architecture

The `cicd-monitor` skill operates in a continuous polling loop:

```
┌─────────────────────────────────────────────────────┐
│ Monitor Phase (every 5 minutes)                     │
│ Fetch latest workflow runs from GitHub Actions      │
│ Compare against baseline (last known good commit)   │
└──────────────┬──────────────────────────────────────┘
               │
         ┌─────▼─────┐
         │ All pass? │
         └─────┬─────┘
            Yes│        No
              ✅        │
                   ┌────▼─────────────────┐
                   │ Analysis Phase       │
                   │ Parse error logs     │
                   │ Classify error type  │
                   │ Extract root cause   │
                   └────┬──────────────────┘
                        │
                   ┌────▼──────────────────┐
                   │ Escalation Phase      │
                   │ Route to specialist   │
                   │ Create DELEGATE       │
                   │ Set retry timer       │
                   └────┬──────────────────┘
                        │
                   ┌────▼──────────────────┐
                   │ Retry Phase           │
                   │ Monitor HANDBACK      │
                   │ Re-run workflow       │
                   │ Track attempt count   │
                   └───────────────────────┘
```

## Error Classification

| Error Type | Specialist | Example |
|-----------|-----------|---------|
| `build_failure` | Senior Engineer | Compilation errors, syntax errors |
| `test_failure` | Quality Engineer | Test assertion failures, timeout |
| `lint_failure` | Engineer | Format, linting, style violations |
| `security_failure` | Security Engineer | Security gate failures, CVE detected |
| `deploy_failure` | Principal Engineer | Deployment infrastructure issues |

## Integration with Orchestrator

When a failure is detected, the monitor creates a DELEGATE in the queue:

```yaml
task_id: fix-ci-{timestamp}
title: "Fix {workflow_name} failure on {branch}"
task_type: bug
severity: high
root_cause: "{parsed error from logs}"
assigned_to: "{Senior|Quality|Security}Engineer"
fix_strategy: "Analyze logs, identify root cause, implement fix, re-run"
expected_outcome: "All checks passing"
retry_count: 1
max_retries: 3
next_check_at: "{now + 5 minutes}"
```

The Orchestrator polls the queue and routes the DELEGATE to the assigned specialist.

## Usage Examples

### Monitor main branch after push

```bash
cd /Users/niall/git/agentic-engineers
scripts/monitor-workflows.py --branch main --repo niallyoung/agentic-engineers
```

### Verbose monitoring with custom intervals

```bash
scripts/monitor-workflows.py \
  --branch fix/build-failures \
  --repo niallyoung/agentic-engineers \
  --interval 3 \
  --retries 5 \
  --verbose
```

### Continuous polling (background)

```bash
while true; do
  scripts/monitor-workflows.py --branch main
  sleep 300  # 5 minute interval
done
```

## GitHub Actions Integration

Add to `.github/workflows/post-push-monitor.yml`:

```yaml
name: Post-Push CI Monitor
on:
  push:
    branches: [main, fix/*, feature/*]

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Wait for initial workflows
        run: sleep 180  # 3 minute grace period
      - name: Run CI monitor
        run: |
          python3 src/skills/_meta/cicd-monitor/scripts/monitor-workflows.py \
            --branch ${{ github.ref_name }} \
            --repo ${{ github.repository }} \
            --verbose
```

## Failure Escalation Flow

```
Workflow fails
    ↓
Monitor detects (within 5 min)
    ↓
Creates DELEGATE with error classification
    ↓
Orchestrator polls queue
    ↓
Routes to appropriate specialist:
  ├─ Build error → Senior Engineer
  ├─ Test error → Quality Engineer
  ├─ Lint error → Engineer
  ├─ Security error → Security Engineer
  └─ Deploy error → Principal Engineer
    ↓
Specialist analyzes & fixes
    ↓
HANDBACK with fix
    ↓
Monitor re-runs workflow
    ↓
If still failing (< 3 retries) → escalate to Principal Engineer
If passing → mark task done ✅
```

## Configuration

The monitor respects these environment variables:

- `CICD_CHECK_INTERVAL` — Polling interval in seconds (default: 300)
- `CICD_MAX_RETRIES` — Max retry attempts (default: 3)
- `CICD_QUEUE_DIR` — Queue directory (default: ~/.copilot/queue)
- `GH_TOKEN` — GitHub personal access token (for API access)

## Limitations

1. **GitHub API rate limits** — Monitor backs off if hitting rate limits
2. **Workflow log retention** — GitHub retains logs for 90 days
3. **Queue availability** — Monitor requires queue system to be operational
4. **Manual rerun** — If workflow is manually re-run via GitHub UI, monitor may create duplicate DELEGATEs

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Could not fetch workflows" | Verify `gh` CLI is installed and authenticated |
| "No workflows found" | Check branch name matches repository |
| "DELEGATE not created" | Verify queue directory exists: `~/.copilot/queue/incoming/` |
| "Duplicate fixes" | Clean up stale DELEGATEs from queue/done before re-running |

## Future Enhancements

- [ ] Deduplication of DELEGATEs for same error within 5 min window
- [ ] Slack/email notifications on high-severity failures
- [ ] Automatic rollback for deploy failures
- [ ] ML-based root cause prediction (using past failures)
- [ ] Integration with GitHub branch protection rules

