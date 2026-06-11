# CI/CD Watch Skill

**Used by:** engineer, senior-engineer, lead-engineer, quality-engineer
**Model:** claude-sonnet-4.6
**Effort:** low — monitoring only; no code changes required.

**This is a CORE behaviour, not an optional skill.** Every merge to main (and
every direct push to main) MUST be followed by watching the resulting CI runs
to completion. A merge is not "done" until all workflows on main are green.

## What This Role Does

- Watches all GitHub Actions runs triggered by a merge/push until completion
- Inspects logs for failures and determines root cause
- Drives the fix loop: **fix on a new branch → PR → merge → watch again**,
  repeating until main is green
- Reports final pipeline state (green, or escalated with root cause)

## What This Role Does Not Do

- Does not re-run failed workflows arbitrarily (fix the root cause first)
- Does not push fixes directly to main — fixes always go through a new
  branch + PR so the PR-level Quality Gate validates them before merge
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

3. **Fix on a new branch + PR** — never push fixes directly to main
   ```bash
   git checkout -b fix/<short-description> origin/main
   # Make fix, verify locally (make verify / targeted pytest)
   git add <files>
   git commit -m "fix(scope): description"
   git push -u origin fix/<short-description>
   gh pr create --base main --title "fix(scope): description" --body "..."
   ```

4. **Watch the PR checks, merge, then watch main again**
   ```bash
   gh pr checks <PR_NUMBER> --watch
   # After merge:
   gh run list -R your-org/your-repo --branch main --limit 1
   gh run watch <NEW_RUN_ID> -R your-org/your-repo --exit-status
   ```

5. **Repeat** steps 1–4 until every workflow on main is green. Do not start
   new work while main is red.

## Quality Checklist

- [ ] Every merge/push to main is followed by a CI watch to completion (core behaviour)
- [ ] All repos that were pushed are checked (not just the first one)
- [ ] Failure root cause is identified from logs before attempting a fix
- [ ] Fixes go through a new branch + PR — never pushed directly to main
- [ ] Fixes are committed and pushed — not retried without a change
- [ ] Lint failures are fixed locally first (`make verify`) before pushing again
- [ ] The watch/fix loop repeats until all workflows on main are green

## Escalation Rules

- If the same job fails repeatedly without a clear code cause (e.g., AWS credentials, IAM permissions, CDK bootstrap), escalate to lead-engineer or platform team
- If a deploy succeeds in dev but fails in prod with infrastructure differences, escalate

## References

- `gh run --help`
- `gh workflow --help`
- GitHub Actions docs: https://github.com/features/actions
