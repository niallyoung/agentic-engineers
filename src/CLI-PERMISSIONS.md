# CLI Permissions Matrix

> **Scope:** Documents which CLI tools each role may use, what operations are allowed/restricted/denied, and the OpenCode-specific permission model.  
> **Last Updated:** 2025-01-20  
> **Repo:** agentic-engineers  
> **Architecture:** Queue-based + OpenCode integration

---

## Permission Levels

| Symbol | Level | Meaning |
|--------|-------|---------|
| ✅ | ALLOW | Use freely without logging rationale |
| 🟡 | RESTRICT | Allowed, but log rationale first |
| 🔴 | DENY | Must escalate to human — do not run |

---

## Role Access Summary

| Tool | Orchestrator | Engineer | Model Eng | Quality Eng | Lead Eng | Senior Eng | Principal | Security |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `gh` (GitHub) | ✅ Read / 🟡 Write | ✅ Read / 🟡 Write | ✅ Read | ✅ Read / 🟡 Write | ✅ Read / 🟡 Write | ✅ Read / 🟡 Write | ✅ Full | ✅ Full |
| `git` (core) | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `bk` (Buildkite) | ✅ Read / 🟡 Write | ✅ Read / 🟡 Write | ✅ Read | ✅ Full | ✅ Read / 🟡 Write | ✅ Read / 🟡 Write | ✅ Full | ✅ Read |
| `acli` (Atlassian) | ✅ Read / 🟡 Write | ✅ Read | ✅ Read | ✅ Read / 🟡 Write | ✅ Read / 🟡 Write | ✅ Read / 🟡 Write | ✅ Full | ✅ Read |
| `python3 / pip` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `make` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `bash / shell` | ✅ Read-only | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `curl / wget` | 🟡 | 🟡 | ❌ | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 |
| `aws` (CLI) | ❌ | 🟡 | ❌ | 🟡 | 🟡 | 🟡 | ✅ | ✅ |
| `docker` | ❌ | 🟡 | ❌ | 🟡 | 🟡 | ✅ | ✅ | ✅ |
| File system (read) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| File system (write) | 🟡 | ✅ | ✅ Metrics only | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## GitHub CLI (`gh`)

### ✅ ALLOW — All roles

#### Read Operations (no logging required)
- `gh auth status` — Check authentication
- `gh pr view / list / diff / checks` — View PRs and CI status
- `gh issue view / list` — View issues
- `gh run view / list / watch` — Watch CI runs, view failures
- `gh run view --log-failed` — Get error logs from failed runs
- `gh repo view` — View repository info
- `gh search code / repos` — Search codebase
- `gh api <GET endpoint>` — Read-only API access
- `gh release view / list` — View releases

#### Write Operations — 🟡 RESTRICT (log rationale first)
- `gh pr create` — Create PRs (draft preferred; log what and why)
- `gh issue create` — Log bugs / findings
- `gh pr review --comment` — Add review feedback (non-binding comments only)
- `gh run rerun --failed` — Re-run failed CI after a fix

### 🔴 DENY — All roles (escalate to human)
- `gh pr merge` — No AI merges (human must approve own changes)
- `gh pr review --approve` — No AI approvals of own changes
- `gh pr close` / `gh issue close` — Closing items requires human judgement
- `gh repo delete / edit / transfer` — Repository management
- `gh release create / delete / edit` — Release management
- `gh run cancel` — Cancelling CI may affect other developers
- `gh api <DELETE/PUT/PATCH>` on production resources

---

## Git Core (`git`)

### ✅ ALLOW — All roles (except Model Engineer)
- `git status / log / diff / blame` — Read-only inspection
- `git add / commit` — Stage and commit changes
- `git push` — Push to feature branch (NOT to `main` or `production`)
- `git checkout / switch / branch` — Branch operations
- `git fetch / pull` — Sync from remote
- `git stash` — Temporary state management

### 🟡 RESTRICT — Must log rationale
- `git push --force-with-lease` — Force push with lease (never plain `--force`)
- `git rebase` — Rebasing (never on shared branches)
- `git cherry-pick` — Cherry-picking (document which commits and why)

### 🔴 DENY — All roles
- `git push origin main` / `git push origin production` — No direct main/prod pushes
- `git push --force` — Destructive; only `--force-with-lease` is allowed
- `git reset --hard <commit>` on shared branches — Rewrite of shared history

---

## Python / Make / Shell

### ✅ ALLOW — All roles
- `python3 -m pytest ...` — Run tests
- `python3 <script>` — Execute scripts within the repo
- `pip install -r requirements.txt` — Install dependencies
- `make <target>` — Run declared Makefile targets
- `bash <repo>/renderer/scripts/<script>.sh` — Renderer scripts only

### 🟡 RESTRICT — Log rationale
- `pip install <package>` — Ad-hoc installs (document why, update requirements.txt)
- `make install` — Full installation (log when and why triggered)
- Shell pipes with `eval` or variable expansion constructs — Security review required

### 🔴 DENY — All roles
- Shell commands with `${var@P}`, chained `${!var}`, or `eval`-like obfuscation — prompt injection risk
- `rm -rf` on paths outside the repo working directory
- Any command that writes to system paths (`/etc`, `/usr/local/bin`) without explicit human approval

---

## Buildkite CLI (`bk`) — CI/CD Monitoring

### ✅ ALLOW — All roles

#### Read Operations (no logging required)
- `bk auth status` — Check authentication
- `bk build list / view` — **List and view build details** ✅
- `bk build view <n>` — **Get build logs and errors** ✅
- `bk pipeline list / view / validate` — View pipeline config
- `bk agent list / view` — View agent status
- `bk cluster list / view` — View cluster status

**Use Case:** ✅ Agents can watch Buildkite jobs, detect failures, read error logs, orchestrate fixes

### 🟡 RESTRICT — Log rationale first

- `bk build create` — Trigger builds (only for own branch)
- `bk build cancel` — Cancel builds (only own builds, never others')

### 🔴 DENY — All roles (escalate to human)

- `bk build approve` — Approve block steps (human gates must be human-approved)
- `bk pipeline create / copy / update` — Infrastructure provisioning
- `bk agent pause / resume / stop` — Fleet management
- `bk cluster create / update / delete` — Cluster management
- `curl` with bk auth token — Uncontrolled API access

---

## Atlassian CLI (`acli`) — Jira & Confluence

### ✅ ALLOW — All roles

#### Jira — Read Requirements
- `acli auth status` — Check authentication
- `acli jira workitem view <KEY>` — **Read issue details** ✅
- `acli jira workitem search --jql "..."` — **Search issues by JQL** ✅
- `acli jira project list / view` — View projects
- `acli jira board search` — View boards
- `acli jira sprint list-workitems` — **Read sprint backlog** ✅

#### Confluence — Read Documentation
- `acli confluence page view` — **Read Confluence pages** ✅
- `acli confluence space list` — List spaces
- `acli confluence blog list` — List blog posts

**Use Case:** ✅ Agents can read requirements from Jira tickets and Confluence documentation

### 🟡 RESTRICT — Log rationale first

- `acli jira workitem create` — Create tickets (single, with context)
- `acli jira workitem comment create` — Add comments (single, useful info)
- `acli jira workitem transition --key <single>` — Update status (own items only)
- `acli jira workitem assign --key <single> --assignee "@me"` — Self-assign only
- `acli jira workitem edit --key <single>` — Edit single issue (own items)

### 🔴 DENY — All roles (escalate to human)

- `--yes` / `-y` flags — **NEVER ALLOWED** (bypasses confirmations)
- `--jql` with transition/edit — **Bulk operations BLOCKED**
- `acli confluence space create` — Infrastructure provisioning
- `acli confluence blog create` — Public content publishing
- Any `delete` command — Permanent data loss

**Safety Rules:**
- No bulk operations (no `--jql` with writes)
- No affecting other team members' work
- No server/API overload (use `--count` to preview scope)
- Read-heavy, write-light

---

## AWS CLI (`aws`)

### ✅ ALLOW — Principal, Security
- `aws <service> describe-*` / `list-*` / `get-*` — All read operations
- `aws logs filter-log-events` — CloudWatch log access for debugging

### 🟡 RESTRICT — Engineer, Senior, Lead, Quality (log rationale)
- `aws s3 cp / sync` — File operations on non-production buckets
- `aws cloudformation describe-*` — Stack inspection

### 🔴 DENY — Orchestrator, Model Eng
- All `aws` operations (no infrastructure access for coordination/optimization roles)

### 🔴 DENY — All roles
- `aws iam *` — IAM changes require human approval
- `aws s3 rm` / `aws s3 rb` — Deletion operations
- `aws ec2 terminate-instances` — Destructive instance operations
- Any operation against production environments without explicit human instruction

---

## OpenCode-Specific Permissions

OpenCode uses the `opencode.jsonc` config at `~/.config/opencode/`.

### Tool Permissions in `opencode.jsonc`

```jsonc
{
  "agents": {
    "orchestrator": {
      "tools": ["read", "write", "bash_readonly", "github_read", "buildkite_read", "atlassian_read"],
      "deny": ["bash_write", "aws", "docker", "github_merge"]
    },
    "engineer": {
      "tools": ["read", "write", "bash", "github_read", "github_write", "buildkite_read"],
      "deny": ["aws_destructive", "docker_build", "github_merge", "buildkite_admin"]
    },
    "model-engineer": {
      "tools": ["read", "write_metrics", "github_read", "buildkite_read", "atlassian_read"],
      "deny": ["bash", "github_write", "aws", "docker", "buildkite_write"]
    },
    "quality-engineer": {
      "tools": ["read", "bash_test_only", "github_read", "buildkite_full", "atlassian_read"],
      "deny": ["bash_write_prod", "aws_destructive", "github_merge"]
    },
    "lead-engineer": {
      "tools": ["read", "write", "bash", "github_full", "buildkite_read", "atlassian_write"],
      "deny": ["aws_destructive", "github_merge", "buildkite_admin"]
    },
    "senior-engineer": {
      "tools": ["read", "write", "bash", "github_read", "github_write", "buildkite_read", "atlassian_write"],
      "deny": ["aws_destructive", "github_merge", "buildkite_admin"]
    },
    "principal-engineer": {
      "tools": ["read", "write", "bash", "github_full", "buildkite_full", "atlassian_full", "aws_read"],
      "deny": ["github_merge", "aws_iam", "buildkite_cluster_admin"]
    },
    "security-engineer": {
      "tools": ["read", "bash", "aws_read", "github_read", "buildkite_read", "atlassian_read"],
      "deny": ["github_merge", "aws_iam", "aws_destructive", "buildkite_write"]
    }
  }
}
```

### OpenCode Queue Permissions

The queue directory (`~/.copilot/queue/`) operates under these rules:

| Operation | Orchestrator | All Other Roles |
|-----------|:---:|:---:|
| Read `incoming/` | ✅ | ✅ |
| Move `incoming/ → processing/` | ✅ | ❌ |
| Write `done/<task>-handback.yaml` | ✅ via agent | ✅ own task only |
| Delete queue files | 🟡 after COMPLETE | ❌ |

### OpenCode Agent Communication (DELEGATE/HANDBACK)

| Operation | Who Can Perform | Security Rules |
|-----------|-----------------|----------------|
| `DELEGATE` to another role | Any role to permitted target | Must follow escalation chain (Engineer → Senior → Lead → Principal) |
| `HANDBACK` results | Only the delegated agent | Task isolation enforced (cannot access unrelated tasks) |
| Read handover packet | Delegated agent only | No cross-agent packet reading |
| Modify task queue | Orchestrator only | Agents cannot manipulate queue state |
| Priority escalation | Lead+ roles | Must document rationale in handover packet |

**DELEGATE Security Rules:**
- Engineer can delegate to Senior Engineer or higher
- Senior Engineer can delegate to Lead Engineer or higher
- Lead Engineer can delegate to Principal Engineer
- Principal Engineer can delegate to Security Engineer (for security audits)
- Quality Orchestrator can delegate to Quality Engineer
- Orchestrator can delegate to any role
- **NO reverse delegation** (Senior cannot delegate down to Engineer)

---

## Secrets & Credentials

### 🔴 DENY — All roles, no exceptions
- Read or print `~/.aws/credentials` or environment variables containing secrets
- Write credentials, tokens, or API keys to any file in the repo
- Log secrets to stdout (even during debugging)
- Pass secrets as CLI arguments (visible in `ps` output)
- Commit `.env` files or any file containing real credentials

### Correct Approach
- Use environment variables from the shell session
- Reference AWS credentials via role-based access (IAM roles)
- Use `aws secretsmanager get-secret-value` — never hardcode values

---

## Security Implications

### Commit & Push Safety
- All code changes go through PR review (no direct merges)
- Branch protection rules prevent unauthorized force pushes
- AI agents cannot approve their own PRs
- Human review required for merging to main/master/production

### CI/CD Safety (Buildkite)
- Agents can monitor but not approve critical build steps
- Failed builds can be retried, not canceled arbitrarily
- Build logs are read-only to prevent tampering
- Pipeline configuration changes require human approval

### Atlassian Safety
- No bulk operations to prevent accidental mass updates
- No `--yes` flags to ensure human confirmation
- Single-item operations only (no JQL-based writes)
- Read-heavy access pattern minimizes risk

### OpenCode Queue Safety
- Task isolation prevents cross-contamination
- DELEGATE/HANDBACK protocol enforces role boundaries
- No direct queue manipulation
- Task history immutable (audit trail)
- No reverse delegation (prevents escalation bypass)

---

## Auditing & Maintenance

### Regular Audit Checklist

1. **Review tool access logs** — Check for unusual patterns in OpenCode queue logs
2. **Verify role assignments** — Ensure agents have minimum necessary permissions
3. **Check for permission violations** — Any denied operations that were attempted?
4. **Update permission matrix** — New tools (Buildkite, Atlassian) or roles added?
5. **Test escalation protocol** — Do denied operations properly escalate via DELEGATE?
6. **Audit DELEGATE chains** — Are escalations following the correct hierarchy?

### Permission Update Process

1. **Propose change** — Document why permission is needed (create Jira ticket)
2. **Security review** — Assess risk of granting permission (Security Engineer role)
3. **Update this document** — Reflect new permission in matrix
4. **Update `opencode.jsonc`** — Modify agent tool permissions
5. **Test in isolation** — Verify permission works as expected
6. **Monitor usage** — Watch for abuse or unexpected behavior (Quality Engineer)

### Maintenance Schedule

- **Weekly:** Review access logs for anomalies (Quality Engineer)
- **Monthly:** Full audit of permission matrix vs. actual usage (Lead Engineer)
- **Quarterly:** Security review of OpenCode queue permissions (Security Engineer)
- **Annually:** Complete overhaul and threat model reassessment (Principal Engineer)

---

## Tool Installation & Verification

### Required CLI Tools

```bash
# GitHub CLI
gh --version  # Should be 2.0+

# Buildkite CLI
bk --version  # Should be 1.0+

# Atlassian CLI
acli --version  # Should be 2.0+

# Git (standard)
git --version  # Should be 2.30+

# Python
python3 --version  # Should be 3.9+
```

### Verification Commands

```bash
# Test GitHub access
gh auth status
gh repo view REMOVED/agentic-engineers

# Test Buildkite access
bk auth status
bk pipeline list

# Test Atlassian access
acli auth status
acli jira project list

# Test Git access
git config user.name
git config user.email

# Test OpenCode queue access
ls ~/.copilot/queue/incoming/
```

### Permission Verification Script

Run this script to verify permissions are correctly enforced:

```bash
#!/bin/bash
# Permission verification script for agentic-engineers

echo "Testing read-only operations (should succeed)..."
gh pr list || echo "❌ GitHub read failed"
bk build list || echo "⚠️  Buildkite read failed (may not be configured)"
acli jira project list || echo "⚠️  Atlassian read failed (may not be configured)"

echo ""
echo "Testing restricted operations (should require confirmation)..."
# gh pr create --draft --title "Test" --body "Permission test"  # Commented - only run manually

echo ""
echo "Testing denied operations (should fail or escalate)..."
# gh pr merge  # Should be blocked by branch protection

echo ""
echo "✅ Permission verification complete"
```

---

## Summary: Use Case Matrix

| Use Case | Tools | Status | Notes |
|----------|-------|--------|-------|
| Read requirements from Jira | `acli jira` | ✅ ALLOWED | Read-only access |
| Read Confluence documentation | `acli confluence` | ✅ ALLOWED | Read-only access |
| Commit code changes | `git` | ✅ ALLOWED | Standard workflow |
| Push to GitHub | `git push` | ✅ ALLOWED | PR review required |
| Watch CI/CD builds (GitHub) | `gh run view/watch` | ✅ ALLOWED | Monitoring only |
| Watch CI/CD builds (Buildkite) | `bk build list/view` | ✅ ALLOWED | Monitoring only |
| Detect CI failures | `gh run view --log-failed`, `bk build view` | ✅ ALLOWED | Read logs |
| Orchestrate fixes after CI failure | Loop: detect → fix → commit → push | ✅ FULLY SUPPORTED | Autonomous |
| Approve PRs | `gh pr merge` | 🔴 DENIED | Human review only |
| Approve Buildkite block steps | `bk build approve` | 🔴 DENIED | Human gates only |
| Bulk update Jira | `acli --jql` with writes | 🔴 DENIED | No bulk ops |
| Delegate tasks (OpenCode) | `DELEGATE` via queue | ✅ ALLOWED | Per role escalation chain |
| Cancel others' builds | `bk build cancel` | 🔴 DENIED | Only own builds |

---

## Escalation: When Permissions Are Unclear

If a required operation falls into a grey area:

1. **Do not proceed** — stop and document what you need to do
2. **Report to Orchestrator** via `DELEGATE` with: tool, operation, justification, alternatives considered
3. **Orchestrator escalates** to human with the same information (or to Security Engineer for security-sensitive operations)
4. **Human approves or denies** — record the decision in TODO.md
5. **Update this document** — if approval is granted, update permission matrix for future reference

---

**Maintained by:** Model Engineer role  
**Security reviewed by:** Security Engineer role  
**Review frequency:** Monthly (Lead Engineer) + Quarterly (Security Engineer)  
**Last audit:** 2025-01-20
