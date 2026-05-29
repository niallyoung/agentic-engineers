# GitHub CLI Skill

**Used by:** orchestrator
**Model:** claude-sonnet-4.6
**Effort:** low — use `gh` for all GitHub interactions; never use the web UI or REST API manually.

**Updated:** Apr 2026 — Smart CICD monitoring (monitor until green, auto-stop)

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

# Merge with admin override (REQUIRES HUMAN VERIFICATION)
# Only used when base branch protection blocks merge despite passing CI.
# CRITICAL: This must NEVER be done autonomously.
# Agents MUST ask the user for explicit confirmation with two-step verification:
#   1. User must confirm intent: "I want to merge the PR"
#   2. User must acknowledge understanding: "I understand this uses admin override"
# Only after BOTH confirmations should the agent proceed with:
gh pr merge <NUMBER> --squash --delete-branch --admin

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

## Smart CICD Workflow Monitoring

Monitor GitHub Actions workflows selectively: track only until each service shows green, then stop. Efficient approach for validating coordinated deployments without sustained overhead.

### Per-Repository Monitoring (Monitor Until Green)

For individual repos or focused validation:

```bash
# Monitor single repo until latest main branch run is green, then exit
repo="{example-service}"
until gh run list --repo "{your-org}/$repo" --branch main --limit 1 \
  --json conclusion --template '{{range .}}{{.conclusion}}{{end}}' | grep -q "success"; do
  status=$(gh run list --repo "{your-org}/$repo" --branch main --limit 1 \
    --json status,conclusion,name,number --template '{{range .}}#{{.number}}: {{.status}} ({{.conclusion}}){{end}}')
  echo "$repo: $status"
  sleep 5
done
echo "✅ $repo: Latest run green"
```

### Multi-Repo Monitoring (Coordinated Deployments)

For platform-wide migrations or coordinated changes across multiple services:

```bash
# Monitor all 8 services until each shows green, then exit
repos=("{service-name}" "{example-service}" "{example-service}" "{example-service}" "{service-name}" "{example-service}" "{service-name}" "{service-name}")
declare -A status

# Initialize: mark all as pending
for repo in "${repos[@]}"; do status[$repo]="pending"; done

# Loop until all green
while true; do
  all_green=true
  for repo in "${repos[@]}"; do
    if [ "${status[$repo]}" != "success" ]; then
      conclusion=$(gh run list --repo "{your-org}/$repo" --branch main --limit 1 \
        --json conclusion --template '{{range .}}{{.conclusion}}{{end}}')
      status[$repo]=$conclusion
      [ "$conclusion" != "success" ] && all_green=false
    fi
  done
  
  # Print status line
  echo "Status: $(echo "${status[@]}" | tr ' ' ', ')"
  
  # Exit if all green
  [ "$all_green" = true ] && break
  sleep 10
done

echo "✅ All services green"
```

### Using Monitor Tool (Until Green)

**All services — Optimized with 60s polling:**

```bash
# Monitor all 8 services with 60s check interval (conserves tokens/network)
repos=({service-name} {example-service} {example-service} {example-service} {service-name} {example-service} {service-name} {service-name})
until (for repo in "${repos[@]}"; do
  conclusion=$(gh run list --repo "{your-org}/$repo" --branch main --limit 1 --json conclusion --template '{{range .}}{{.conclusion}}{{end}}')
  [ "$conclusion" = "success" ] || exit 1
done); do
  for repo in "${repos[@]}"; do
    conclusion=$(gh run list --repo "{your-org}/$repo" --branch main --limit 1 --json conclusion,status --template '{{range .}}{{.conclusion}}:{{.status}}{{end}}')
    echo "$repo: ${conclusion:-pending}"
  done
  sleep 60
done
echo "✅ All services green"
```

**Single repo — faster polling:**

```bash
# Monitor single repo until green, auto-stop
Monitor(
  description: "Watch {example-service} until latest main branch run is green",
  command: "repo='{example-service}'; until gh run list --repo {your-org}/$repo --branch main --limit 1 --json conclusion --template '{{range .}}{{.conclusion}}{{end}}' | grep -q success; do gh run list --repo {your-org}/$repo --branch main --limit 1 --json status,conclusion,name,number --template '{{range .}}$repo: #{{.number}} - {{.status}} ({{.conclusion}}){{end}}'; sleep 5; done; echo '✅ $repo green'",
  timeout_ms: 300000,
  persistent: false
)
```

### When to Use Per-Repo Monitoring

- Single service deployment validation
- Quick CICD checks before/after code changes
- Verify specific fix didn't break a service

### When to Use Multi-Repo Monitoring

- **Platform-wide migrations** (e.g., arm64 Lambda rollout)
- **Coordinated feature releases** across multiple services
- **Infrastructure changes** affecting all backends
- **Dependency upgrades** across the platform

### Responding to Failures During Monitoring

When a repo fails to go green:

1. **Check failure reason**: `gh run view <RUN_ID> --repo owner/repo --log | grep -A 10 "FAILED\|Error|error:"`
2. **Investigate logs**: Review full job logs for root cause
3. **Fix and redeploy**: Correct issue, push commit (auto-triggers cloud CI)
4. **Resume monitoring**: Restart monitor — it will detect the new run and wait for green
5. **Verify clean runs**: Once green, monitor auto-exits

## Admin Merge Override Workflow (Branch Protection Bypass)

When a PR cannot merge despite passing all CI checks due to base branch protection policy, the `--admin` flag bypasses the protection **but only after human verification**.

### When to Use `--admin`

- All status checks are passing (green)
- Base branch policy blocks merge
- User explicitly requests the merge
- This is typically only needed for author self-merges on repos with strict protection

### Two-Step Verification (MANDATORY)

Agents MUST NEVER use `--admin` autonomously. Instead:

1. **Ask the user to confirm intent:**
   ```
   This PR cannot merge due to branch protection, but all checks pass.
   Do you want to merge with admin override?
   Please type: I want to merge the PR
   ```

2. **After user confirms, ask for acknowledgment:**
   ```
   I understand this uses admin privileges to override branch protection.
   Please type: I understand
   ```

3. **Only after BOTH confirmations**, execute:
   ```bash
   gh pr merge <NUMBER> --squash --delete-branch --admin
   ```

### Example User Flow

```
Agent: "This PR cannot merge due to branch protection, but all checks pass. Do you want to merge with admin override? Please type: I want to merge the PR"

User: "I want to merge the PR"

Agent: "I understand this uses admin privileges to override branch protection. Please type: I understand"

User: "I understand"

Agent: [executes gh pr merge 9 --squash --delete-branch --admin]
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
- If branch protection blocks a merge, **STOP and ask the user for explicit two-step verification before using `--admin`**:
  1. Ask: "Do you want to merge this PR with admin override? (Type: I want to merge the PR)"
  2. After user response, ask: "I understand this uses admin privileges and overrides branch protection. Proceed? (Type: I understand)"
  3. Only after BOTH confirmations, proceed with `gh pr merge <NUMBER> --squash --delete-branch --admin`
  4. **NEVER use `--admin` autonomously or without explicit human verification**

## References

- `gh --help`
- `gh pr --help`
- `gh run --help`
- GitHub CLI docs: https://cli.github.com/manual/
