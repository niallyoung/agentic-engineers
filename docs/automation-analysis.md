# Automation Analysis: Current Manual Checks vs. Workflow Opportunities

## Summary of Checks Performed (This Session)

| Check | Currently | Should be | Rationale |
|-------|-----------|-----------|-----------|
| **CI status polling** | Manual (gh pr checks) | ✅ Automated (GitHub UI) | Already auto-displays; I was manually polling—unnecessary |
| **Working tree cleanliness** | Manual (git status) | ✅ Automated (pre-push hook) | Pre-push already validates; hook should ENFORCE clean tree |
| **File permission fixes** | Manual (chmod) | ✅ Automated (pre-commit) | Already validated; should REJECT commits with bad perms |
| **Commit message validation** | Manual confirmation | ✅ Partially automated | commit-msg hook runs; conventional-commit warnings are informational only |
| **Tests passing** | Manual (pre-push runs tests) | ✅ Already automated | Full test suite runs pre-push; no improvement needed |
| **PR description updates** | Manual (gh pr edit) | ✅ Semi-automated | Could auto-generate from commit history + SPEC schema |
| **Branch/commit verification** | Manual (git log, git branch -vv) | ✅ Automated (pre-push) | Pre-push validates commit SHAs, refs—human review is just confirmation |
| **Merge decision** | Manual (user judgment) | ❌ Keep manual | Merge is a deliberate, irreversible action—humans should decide |

---

## HIGH-PRIORITY AUTOMATION GAPS

### 1. **Pre-Commit: File Permissions Enforcement** (MISSING)
**Current state:** pre-commit validates but only warns; hook allows commits with bad perms
**Gap:** Pre-commit should REJECT commits with executable .md/.yaml/.json files
**Impact:** Reduces churn (fewer "fix permission" commits)
**Implementation:**
```bash
# In .githooks/pre-commit (src/hooks/git/pre-commit.yml)
add new check: "File Permissions Audit"
  - Reject if .md, .yaml, .json, .config files are executable
  - Reject if scripts are NOT executable (+x)
  - Allow bypass with ENFORCE_PERMS=0 for git-related workflows
```

### 2. **Pre-Commit: Working Tree Enforcement** (PARTIAL)
**Current state:** Pre-push validates clean tree; pre-commit does not
**Gap:** Pre-commit should reject commits if working tree has uncommitted changes (outside the current commit)
**Impact:** Prevents accidental "dirty" commits
**Implementation:**
```bash
# In .githooks/pre-commit
add new check: "Staging Purity"
  - Assert: git diff --cached (only staged changes)
  - Reject if any uncommitted changes exist (git status --short, exclude staging area)
  - Exception: .gitignore'd files OK
```

### 3. **PR Body Generation (Automation Opportunity)**
**Current state:** Manual edit of PR title/body
**Gap:** PR body could be auto-generated from:
  - Commit messages (structured, conventional-commit format)
  - SPEC.md annotations (cross-referencing)
  - Test coverage reports (from CI)
  - Changelog entries
**Impact:** Reduces manual documentation burden; ensures consistency
**Implementation:**
```bash
# New skill: pr-body-generator
  - Input: branch name, commit range (feature/cleanup vs. main)
  - Parse commits with conventional-commit parser
  - Fetch test metrics from CI (coverage, # tests passing)
  - Fetch SPEC.md sections relevant to commits
  - Output: Markdown PR body (structured, scannable)
  - Can be triggered by CI workflow or pre-merge hook
```

### 4. **Commit Message Enforcement (PARTIAL)**
**Current state:** commit-msg hook validates format; warnings are informational only
**Gap:** Warnings should escalate to ERROR for missing task IDs; allow bypass with --no-verify (but log it)
**Impact:** Improves traceability (all commits linked to tasks)
**Implementation:**
```bash
# In .githooks/commit-msg
  - Task ID format required: YYYY-MM-DD-kebab-case
  - Conventional commit format (type(scope): subject) required
  - If missing: reject with clear message + example
  - Bypass: GIT_SKIP_HOOKS=1 (already logged by .githooks/pre-commit)
```

### 5. **Merge Strategy Automation** (NICE-TO-HAVE)
**Current state:** User manually selects merge method (squash/merge/rebase)
**Gap:** Policy could enforce "always squash" for feature branches
**Impact:** Cleaner main branch history; predictable merge behavior
**Implementation:**
```bash
# New GitHub workflow: enforce-merge-strategy.yml
  - Trigger: pull_request_target (when PR is ready to merge)
  - Check: branch name is `feature/*` or `fix/*`
  - Action: Require squash merge only (disable merge/rebase in branch protection)
  - Alternative: API call to enforce via GitHub API when PR is merged
```

---

## MEDIUM-PRIORITY IMPROVEMENTS

### 6. **Automated PR Description from Commits**
Add a GitHub Action that runs when PR is created/updated:
```yaml
# .github/workflows/auto-pr-body.yml
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  update-pr-body:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Generate PR body from commits
        run: |
          # Parse commit messages from base...head
          # Format as markdown with sections
          # Update PR body via GitHub API
```

### 7. **Merge Readiness Checklist (Semi-Automated)**
Create a GitHub Status Check that validates:
- ✅ All CI checks passing
- ✅ Conventional commits in message
- ✅ SPEC.md compliance verified
- ✅ No merge conflicts
- ✅ Branch is up-to-date with main

This could be a custom workflow or a 3rd-party app (e.g., Mergify, Probot).

---

## LOW-PRIORITY / NOT RECOMMENDED

### 8. **Auto-Merge on CI Green** (NOT RECOMMENDED)
**Reason:** Squash merges are destructive; human review of commits before merge is critical
**Alternative:** Auto-comment "Ready to merge (all checks green)" so human can decide

### 9. **Automated Branch Deletion** (MODERATE)
**Current:** Manual `gh pr merge --delete-branch`
**Gap:** Could be automated in a post-merge workflow
**Recommendation:** Implement in GitHub Actions (safe, reversible, audited)

---

## Implementation Priority (Immediate → Later)

| Priority | Item | Effort | Impact | Blocker? |
|----------|------|--------|--------|----------|
| **🔴 HIGH** | Pre-commit: file permissions REJECT | 30min | Medium | No |
| **🔴 HIGH** | Pre-commit: staging purity check | 45min | Medium | No |
| **🔴 HIGH** | Commit message task ID enforcement | 20min | High | No |
| **🟠 MED** | PR body auto-generation (skill + CI workflow) | 2-3h | High | No |
| **🟠 MED** | Merge strategy policy enforcement (GitHub API) | 1h | Medium | No |
| **🟡 LOW** | Post-merge automated branch cleanup | 30min | Low | No |

---

## Files to Modify

1. **src/hooks/git/pre-commit.yml** — Add file permissions + staging purity checks
2. **src/hooks/git/commit-msg.yml** — Escalate task ID + conventional-commit to errors
3. **New:** `.github/workflows/auto-pr-body.yml` — Generate PR body from commits
4. **New:** `src/skills/pr-body-generator/` — Skill for PR body generation (reusable)
5. **docs/HOOKS.md** — Document enforcement rules

---

## Decisions Needed

1. **Task ID enforcement:** Required (error) or optional (warning)?
   - Recommend: Required in pre-commit, allows `GIT_SKIP_HOOKS=1` bypass with audit trail
   
2. **File permissions:** Reject unknown executable state or just warn?
   - Recommend: Reject with --no-verify bypass available
   
3. **PR body generation:** Automated (CI workflow) or on-demand skill?
   - Recommend: Both (CI on PR creation, skill on-demand for updates)
   
4. **Merge method:** Enforce squash via GitHub branch protection or via workflow?
   - Recommend: GitHub branch protection (simpler, enforced at platform level)

