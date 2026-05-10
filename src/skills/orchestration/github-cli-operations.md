# GitHub CLI Skill

**Role Summary:** GitHub CLI (`gh`) automation enables PR/issue management, workflow monitoring, and CI inspection without leaving the terminal. Orchestrates GitHub Actions workflows and keeps code review smooth.

**Cost Tier:** Automation (no AI tokens)

---

## What This Does

- ✅ Monitor GitHub Actions workflows in real-time
- ✅ Create, list, and merge pull requests
- ✅ Close issues and add comments
- ✅ Check CI status before pushing
- ✅ View and resolve PR review comments
- ✅ Trigger manual workflow runs if needed

---

## Common Commands

### Workflow Monitoring

```bash
# Watch all runs on current repo
gh run list -L 10 --json status,conclusion,name,createdAt

# Watch specific repo
gh run list -R {your-org}/{service-name} -L 5

# Get specific run details
gh run view <run_id>

# Stream run logs
gh run view <run_id> --log
```

### Pull Request Management

```bash
# Create PR
gh pr create --title "fix: auth timeout" --body "Fixes issue #123"

# List open PRs
gh pr list -s open

# View PR
gh pr view <number>

# Merge PR
gh pr merge <number> --squash --delete-branch

# Close PR
gh pr close <number>
```

### Issue Management

```bash
# Create issue
gh issue create --title "Bug: JWT validation" --body "Details"

# Close issue
gh issue close <number>

# Add comment
gh issue comment <number> --body "Fixed in PR #456"
```

### Code Review

```bash
# View PR comments
gh api repos/{your-org}/{example-service}/pulls/123/comments

# Resolve comment
gh api -X PUT repos/{your-org}/{example-service}/pulls/comments/<comment_id>/replies \
  --input - << 'EOF'
{"body": "Fixed in commit abc123"}
EOF
```

---

## Pre-Push Workflow

Before pushing to main:

```bash
# Check latest run status
gh run list -R {your-org}/$(basename $(pwd)) -L 1

# If in_progress, wait and check again
gh run view <latest_run_id> --log
```

---

## CI Monitoring Loop

For long-running CI (after push):

```bash
# Stream latest run logs
gh run view $(gh run list -L 1 -q '.[] | .databaseId') --log

# Or check status periodically
while true; do
  gh run list -L 1 --json status,conclusion
  sleep 30
done
```

---

## Authentication

Requires GitHub CLI installed and authenticated:

```bash
# Login (if not already authenticated)
gh auth login

# Verify authentication
gh auth status
```

Uses existing SSH keys / GitHub Personal Access Token (set up once, reused).

---

## Integration Points

**After `git push origin main`:**
1. GitHub Actions CI starts automatically
2. Monitor with: `gh run list -R {your-org}/ers-<service>`
3. Check logs if failure: `gh run view <run_id> --log`
4. Review PR comments (if applicable): `gh api repos/.../pulls/<number>/comments`

**Before merging a PR:**
1. Check CI status: `gh pr view <number>`
2. Resolve comments: `gh api ...`
3. Merge when green: `gh pr merge <number> --squash`

---

## Skill Validation

This skill is correct if it can:
1. List recent workflow runs for any ERS service
2. Stream logs from a running workflow
3. Create a PR with title and body
4. Check PR status and review comments
5. Merge a PR with squash
6. Monitor CI until green without polling manually
