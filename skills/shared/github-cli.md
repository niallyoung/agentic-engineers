# GitHub CLI Skill

**Used by:** orchestrator
**Model:** claude-sonnet-4-6
**Effort:** low — use `gh` for all GitHub interactions; never use the web UI or REST API manually.

Use this skill when querying GitHub state, checking CI status, inspecting pull requests, or managing issues across repositories.

## What This Role Does

- Queries repository state: PRs, issues, workflow runs, releases, tags
- Watches CI pipeline progress and reports pass/fail across repos
- Opens, views, and merges pull requests
- Creates issues and comments programmatically

## What This Role Does Not Do

- Does not push code or create commits — use `git` for that
- Does not modify GitHub Actions workflow YAML — escalate to engineer
- Does not manage branch protection rules, org settings, or secrets — escalate to platform team

## Default Input

- Repository reference: `owner/repo` or just `repo` if already in the repo directory
- Action: list, view, watch, create, merge

## Default Output

- Structured tabular or JSON output from `gh`
- Pass/fail summary when monitoring CI

## Authentication

```bash
# Check auth status
gh auth status

# Login (first time or after token expiry)
gh auth login
```

## Pull Requests

```bash
# List open PRs
gh pr list -R owner/repo

# View a PR
gh pr view <NUMBER> -R owner/repo

# View PR with comments
gh pr view <NUMBER> -R owner/repo --comments

# Check out a PR branch locally
gh pr checkout <NUMBER>

# Create a PR
gh pr create --title "feat(scope): description" --body "$(cat <<'EOF'
## Summary
- What changed and why

## Test plan
- [ ] Unit tests pass
- [ ] E2E tests pass
EOF
)"

# Merge (squash)
gh pr merge <NUMBER> --squash --delete-branch

# Approve
gh pr review <NUMBER> --approve
```

## Issues

```bash
# List open issues
gh issue list -R owner/repo

# View an issue
gh issue view <NUMBER> -R owner/repo

# Create an issue
gh issue create --title "Bug: description" --body "Steps to reproduce..."

# Close an issue
gh issue close <NUMBER>

# Comment on an issue
gh issue comment <NUMBER> --body "Investigation update..."
```

## Workflow Runs (CI/CD)

```bash
# List recent runs
gh run list -R owner/repo --limit 5

# Filter by branch
gh run list -R owner/repo --branch main --limit 3

# View a run's job summary
gh run view <RUN_ID> -R owner/repo

# Interactive watch (polls every 3 seconds)
gh run watch <RUN_ID> -R owner/repo

# Full logs
gh run view <RUN_ID> -R owner/repo --log

# Filter logs to failures
gh run view <RUN_ID> -R owner/repo --log | grep -A 20 "FAILED\|Error\|error:"

# Trigger a manual workflow dispatch
gh workflow run deploy.yaml -R owner/repo --ref main
```

## Releases and Tags

```bash
# List releases
gh release list -R owner/repo

# View a release
gh release view <TAG> -R owner/repo

# Create a release
gh release create v1.2.3 --title "v1.2.3" --notes "Release notes here"
```

## Repositories

```bash
# View repo details
gh repo view owner/repo

# Clone
gh repo clone owner/repo

# List repos in an org
gh repo list owner --limit 20
```

## Monitoring Multiple Repos

To check CI status across several repos after a coordinated push:

```bash
for repo in org/service-a org/service-b org/service-c; do
  echo "=== $repo ==="
  gh run list -R "$repo" --branch main --limit 1
done
```

## Quality Checklist

- [ ] Use `-R owner/repo` flag when not inside the repo directory
- [ ] Check `gh auth status` if commands return 401 errors
- [ ] Prefer `gh run watch` over polling `gh run list` manually
- [ ] For PR creation, always provide a meaningful body (not just title)
- [ ] Verify run ID before watching — use `gh run list` to confirm the latest run

## Escalation Rules

- If `gh auth login` fails or tokens expire repeatedly, escalate to platform team (may be a GitHub App / OIDC configuration issue)
- If a workflow cannot be triggered via `gh workflow run`, check that it has a `workflow_dispatch` trigger — if not, escalate to the engineer who owns that workflow
- If branch protection blocks a merge, escalate to lead-engineer

## References

- `gh --help`
- `gh pr --help`
- `gh run --help`
- GitHub CLI docs: https://cli.github.com/manual/
