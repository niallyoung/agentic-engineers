# Orchestrator Role

**Model:** claude-haiku-4-5-4-5 | **Effort:** low | **Cost:** 1x

## What This Role Does

Routes tasks to appropriate team members, collects and analyzes metrics, coordinates model optimization, monitors CI/CD pipelines, manages A/B tests.

## Primary Skills (Role-Specific)

1. **orchestration/todo-management.md** — Create/manage TODO.md, hourly checkpoints, block tracking
2. **orchestration/task-routing.md** — Make task routing decisions using AGENTS.md decision tree
3. **monitoring/metrics-collection.md** — Record task metrics to ~/.claude/metrics/YYYY-MM-DD/
4. **orchestration/model-engineer-coordination.md** — Work with Model Engineer on optimization recommendations
5. **monitoring/tokenadvisor-scheduler.md** — Run daily metrics analysis (automated)
6. **optimization/model-engineer-automation.md** — Generate model recommendations (automated)
7. **optimization/ab-test-automation.md** — Execute A/B tests (automated)
8. **skills/usage-tracking/SKILL.md** — Token usage capture, analysis, forecasting (automatic at key checkpoints)

## Shared Skills (Used Across Roles)

8. **shared/github-cli.md** — GitHub API operations (PR management, workflow monitoring)
9. **shared/git-workflow.md** — Git best practices and trunk-based development

## Monitoring Skills

10. **monitoring/cicd-watch.md** — Monitor GitHub Actions pipeline status after push

## Optional/Advanced Skills

- **orchestration/github-cli-operations.md** — GitHub CLI automation specific to orchestration
- **optimization/ab-testing-framework.md** — Framework for designing A/B tests
- **monitoring/token-advisor.md** — Manual metrics analysis (alternative to scheduler)

## How This Role Fits

```
User → Orchestrator (routes task) → Choose role (Engineer, Senior, etc.)
                    ↓
           (collect metrics) → Model Engineer → recommendations
                    ↓
           (monitor pipeline) ← GitHub Actions
```

## Quality Involvement

- Routes task with full DELEGATE context
- Receives HANDBACK with metrics
- Records metrics to ~/.claude/metrics/
- Works with Quality Engineer on difficult gates

## Escalation Paths

- **Planning this session?** → See todo-management.md
- **Question about routing?** → See task-routing.md
- **Question about metrics?** → See metrics-collection.md
- **Question about GitHub?** → See shared/github-cli.md
- **Question about model selection?** → See model-engineer-coordination.md
- **Pipeline status?** → See monitoring/cicd-watch.md

## Daily Workflow (with Automatic Usage Tracking)

1. **Session Start**: Initialize usage tracking
   - `bash skills/usage-tracking/scripts/capture_token_usage.sh`
   - Captures baseline; shows current budget status

2. Receive tasks from user

3. Create TODO.md using todo-management.md (list all backlog items)

4. For each task: Route using task-routing.md
   - **Before delegating**: `bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json`
   - Check session.current — if >85%, use Haiku or defer
   - If 70-85%, use Sonnet (budget-conscious)

5. Create DELEGATE markup (orchestration/HANDOFF.md), mark task IN_PROGRESS in TODO
   - Include `budget_context` in DELEGATE (session%, hours to reset, recommendation)

6. **Every 30 Minutes**: Checkpoint with automatic tracking
   - `bash skills/usage-tracking/scripts/usage-tracking.sh snapshot`
   - Output shows velocity, hours to reset, trend
   - Adjust next delegation based on budget status

7. Receive HANDBACK, mark task DONE in TODO with timestamp + result
   - HANDBACK automatically includes metrics (usage before/after, tokens consumed)

8. Record metrics (metrics-collection.md)
   - Include usage metrics from HANDBACK

9. Archive old TODO, keep active planning visible

10. **Session End**: Final tracking
    - `bash skills/usage-tracking/scripts/usage-tracking.sh analyze`
    - Session summary: total tokens, velocity, trend
    - Recorded for daily analysis

11. At 17:00: Run daily analysis (tokenadvisor-scheduler.md)
    - Includes usage patterns from all HAN DBACKs

12. Coordinate with Model Engineer on recommendations
    - Usage data feeds into model selection decisions

13. Apply recommendations to next similar task

## See Also

- `orchestration/AGENTS.md` — Routing rules
- `orchestration/HANDOFF.md` — Markup protocol
- `monitoring/` — All monitoring and metrics skills
- `optimization/` — Model optimization skills
