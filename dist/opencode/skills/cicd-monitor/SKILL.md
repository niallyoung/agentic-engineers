---
name: cicd-monitor
description: Post-push CI/CD health monitor that checks GitHub Actions workflows for failures, escalates issues, and initiates automatic or manual fixes with retry timers (3-5 min intervals).
license: Proprietary
metadata:
  author: agentic-engineers
  version: "1.0"
  category: monitoring
  role: orchestrator
---

## Overview

This skill continuously monitors CI/CD pipeline health after code is pushed to a branch. It detects workflow failures, analyzes root causes, escalates issues to the appropriate specialist, and sets automatic retry timers to prevent manual polling.

## When to Use

- **Immediately after `git push`** — Invoked by the Orchestrator or pre-push hook
- **Periodic health checks** — Scheduled via cron or CI/CD workflow (3-5 minute intervals)
- **Failure escalation** — When GitHub Actions workflows fail, automatically create DELEGATEs
- **Retry orchestration** — Track in-flight fixes and re-run checks after remediation

## Workflow

1. **Monitor phase** (runs every 3-5 min):
   - Fetch latest workflow runs for the current branch
   - Identify FAILED/ERROR conclusions
   - Compare against baseline (previous successful run)

2. **Analysis phase** (on failure):
   - Parse workflow logs for error messages
   - Categorize: build failure, test failure, lint failure, deploy failure
   - Extract stack traces or error output

3. **Escalation phase**:
   - **Build/compilation errors** → Senior Engineer (compile-time diagnostic)
   - **Test failures** → Quality Engineer (identify flaky tests, root cause analysis)
   - **Lint/format failures** → Engineer (trivial fixes)
   - **Security gate failures** → Security Engineer
   - **Deploy failures** → DevOps (infrastructure issues)

4. **Retry phase**:
   - Create DELEGATE with fix requirements
   - Set retry timer (3-5 min interval)
   - On fix completion: re-run workflow
   - If still failing after 3 retries: escalate to Principal Engineer

## Usage

### Manual invocation (after push)

```bash
scripts/monitor-workflows.py --branch main --repo owner/repo
```

### Integrated into CI/CD

The skill is invoked post-push via GitHub Actions workflow or OpenCode CI pipeline:
- Triggers automatically 2-3 minutes after a push is detected
- Sets internal timer for next check (5 min)
- Escalates via DELEGATE if failures found

### Arguments

- `--branch` — Branch to monitor (default: current branch)
- `--repo` — Repository (default: infer from .git)
- `--interval` — Check interval in minutes (default: 5)
- `--retries` — Max retry attempts before escalation (default: 3)
- `--verbose` — Debug output

## Integration Points

- **GitHub API** — Fetch workflow runs and logs
- **Orchestrator** — Create and route DELEGATEs for fixes
- **Queue system** — Track in-flight fixes via HANDBACK monitoring
- **Pre-push hooks** — Can be triggered automatically before push completes

## Output

Creates DELEGATE to appropriate specialist:
```yaml
task_id: fix-ci-failure-{run_id}
title: "Fix {workflow_name} failure on {branch}"
category: bug
severity: high
root_cause: "{parsed error message}"
fix_specialist: "{Senior|Quality|Security}Engineer"
retry_attempt: 1/3
next_check_at: "{now + 5 min}"
```

## See Also

- [Monitoring Reference](references/REFERENCE.md) — Detailed API integration
- [Error Classification](references/ERROR_CATEGORIES.md) — Failure type mapping

