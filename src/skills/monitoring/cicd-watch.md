# CI/CD Watch Skill

**Used by:** engineer, senior-engineer, lead-engineer, quality-engineer
**Model:** claude-sonnet-4-6
**Effort:** low — monitoring only; no code changes required.

Use this skill after pushing to main when you need to monitor GitHub Actions pipeline status across one or more repositories.

## What This Role Does

- Checks the status of recent GitHub Actions runs after a push
- Watches specific runs to completion
- Inspects logs for failures and determines root cause
- Guides the fix-and-repush cycle

## What This Role Does Not Do

- Does not re-run failed workflows arbitrarily (fix the root cause first)
- Does not modify CI/CD pipeline YAML (escalate to lead-engineer or platform team)
- Does not approve production deployments that require manual gates

## Default Input

- One or more repository names that were recently pushed
- Optional: specific run IDs to watch

## Default Output

- Pass/fail status for each repo's pipeline
- Failure investigation summary with the relevant log lines
- Next action (fix locally and repush, or escalate)

## Typical Pipeline Stages

After pushing to main, GitHub Actions typically runs:

1. **Lint + test** — fast, usually cached
2. **Deploy dev** — deploys to development environment
3. **Deploy prod** — deploys to production environment
4. **Tag release** — semantic versioning tag

Typical durations:
- Lint + test: 3-5 min
- Deploy dev: 5-10 min
- Deploy prod: 5-10 min
- Total: ~15-25 min per repo

## Key Commands

### List recent runs

```bash
gh run list -R your-org/your-repo --limit 5
# Fields: STATUS, TITLE, HEAD BRANCH, RUN NUMBER, CREATED

# Filter by branch
gh run list -R your-org/your-repo --branch main --limit 3
```

### Watch a run

```bash
gh run view <RUN_ID> -R your-org/your-repo
# Shows: name, status, conclusion, commit, created, updated, jobs

# Interactive watch (polls every 3 seconds)
gh run watch <RUN_ID> -R your-org/your-repo
```

### View logs

```bash
gh run view <RUN_ID> -R your-org/your-repo --log
# Shows full logs for all jobs in the run

# Filter to failures
gh run view <RUN_ID> -R your-org/your-repo --log | grep -A 50 "FAILED\|error"
```

### Trigger manual workflow (rare)

```bash
gh workflow run deploy.yaml -R your-org/your-repo --ref main
```

## Failure Investigation

If a run fails:

1. **View the run**
   ```bash
   gh run view <RUN_ID> -R your-org/your-repo
   ```

2. **Check which job failed**
   ```bash
   gh run view <RUN_ID> -R your-org/your-repo --log | grep -A 50 "FAILED\|error"
   ```

3. **Fix locally** — make the fix, commit, and push again
   ```bash
   git log main --oneline -1
   # Make fix
   git add <files>
   git commit -m "fix(scope): description"
   git push origin main
   ```

4. **Watch the new run**
   ```bash
   gh run list -R your-org/your-repo --branch main --limit 1
   gh run watch <NEW_RUN_ID> -R your-org/your-repo
   ```

## Quality Checklist

- [ ] All repos that were pushed are checked (not just the first one)
- [ ] Failure root cause is identified from logs before attempting a fix
- [ ] Fixes are committed and pushed — not retried without a change
- [ ] Lint failures are fixed locally first (`make verify`) before pushing again

## Escalation Rules

- If the same job fails repeatedly without a clear code cause (e.g., AWS credentials, IAM permissions, CDK bootstrap), escalate to lead-engineer or platform team
- If a deploy succeeds in dev but fails in prod with infrastructure differences, escalate

## References

- `gh run --help`
- `gh workflow --help`
- GitHub Actions docs: https://github.com/features/actions
