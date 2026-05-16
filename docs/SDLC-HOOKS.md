# SDLC Hooks — Comprehensive Enforcement Reference

**Last Updated:** 2026-05-16  
**Scope:** agentic-engineers SDLC enforcement via git hooks and OpenCode commands  
**Status:** Production Ready — All 3 hooks fully implemented and tested

---

## Overview

The agentic-engineers framework enforces the DELEGATE → Agent Work → HANDBACK → QE Review SDLC workflow through two complementary mechanisms:

1. **Git hooks** (`.githooks/`) — commit-time and push-time enforcement for the repo itself
2. **OpenCode commands** (`.opencode/commands/`) — workflow shortcuts and status checks

All work flowing through the system is validated at three critical gates:
- **Pre-commit:** Before code is committed (SPEC compliance, secrets, YAML validity)
- **Commit-msg:** Message format and protocol compliance
- **Pre-push:** Quality gates before pushing to shared branches

---

## Git Hooks Architecture

All hooks live in `.githooks/` and are activated via:
```bash
git config core.hooksPath .githooks
```

This is automatically configured by `make install` / `renderer/scripts/render-opencode.sh`.

### Hook Lifecycle

```
Developer makes changes
    ↓
git add <files>
    ↓
git commit -m "message"
    ├─→ [pre-commit hook] ← Validates SPEC, secrets, YAML, format
    │       │
    │       ├─ BLOCK if errors found
    │       └─ WARN if non-critical issues
    │
    ├─→ [commit-msg hook] ← Validates message format, protocol compliance
    │       │
    │       └─ BLOCK if errors found
    │
    ✅ Commit created
    ↓
git push
    ├─→ [pre-push hook] ← Final quality gate before shared branch
    │       │
    │       ├─ BLOCK if critical errors
    │       └─ WARN if tests fail or protected branch
    │
    ✅ Push to remote
```

---

## `.githooks/pre-commit` — SPEC & Quality Enforcement

**Trigger:** Before every `git commit`  
**Severity:** Blocking (errors prevent commit) + Warnings (non-blocking)

### What It Checks

#### 1. SPEC.md Compliance (BLOCKING)

| Check | Rule | Error Message |
|-------|------|---------------|
| External scripts | No `.py`/`.sh` in `orchestration/scripts/` | `VIOLATION: External scripts in orchestration/scripts/ — all work must flow through DELEGATE/HANDBACK protocol` |
| Cron files | No `.cron` in `orchestration/config/` | `VIOLATION: Cron files in orchestration/config/ — use queue-based delegation instead` |
| Process execution | No `subprocess`, `os.system`, `exec`, `popen` in agent code | `VIOLATION: Direct process execution in agent code — use DELEGATE/HANDBACK protocol instead` |

**Why:** SPEC.md mandates that ALL work flows through the Orchestrator queue. External scripts, cron jobs, and direct process execution bypass the queue and break observability.

#### 2. Secret Detection (BLOCKING)

Scans staged files for common secret patterns:

| Pattern | Examples | Error Message |
|---------|----------|---------------|
| API keys | `api_key=`, `secret_key=`, `private_key=` | `Possible secret detected in {file} — review before committing` |
| AWS keys | `AKIA[0-9A-Z]{16}` | `AWS access key pattern detected in {file}` |
| GitHub tokens | `ghp_[A-Za-z0-9_]{36,255}` | `GitHub personal access token pattern detected in {file}` |
| Private keys | `BEGIN RSA PRIVATE KEY`, `BEGIN OPENSSH PRIVATE KEY` | `Private key detected in {file} — should not be committed` |
| Database credentials | `postgresql://user:pass@host`, `mysql://user:pass@host` | `Hardcoded database credentials detected in {file}` |
| HTTP auth | `https://user:pass@host` | `Hardcoded HTTP authentication detected in {file}` |

**Note:** Binary files are automatically skipped.

#### 3. YAML/JSON Validity (BLOCKING)

| File Type | Validation | Error Message |
|-----------|-----------|---------------|
| `.yaml`, `.yml` | Must parse as valid YAML | `Invalid YAML syntax in {file}` |
| `.json`, `.jsonc` | Must parse as valid JSON (JSONC comments stripped) | `Invalid JSON syntax in {file} (JSONC comments stripped before check)` |

**Requires:** `python3` and `pyyaml` installed

#### 4. File Format Validation (WARNINGS)

| Check | Pattern | Warning Message |
|-------|---------|-----------------|
| DOS line endings | CRLF (`\r\n`) in code files | `DOS line endings (CRLF) detected in {file} — convert to Unix (LF)` |
| Trailing whitespace | Trailing spaces/tabs in code files | `Trailing whitespace detected in {file}` |

#### 5. Code Style Checks (WARNINGS)

| Tool | Files | Warning Message |
|------|-------|-----------------|
| `flake8` (if installed) | `*.py` | `Python style issues in {file} (flake8)` |
| `shellcheck` (if installed) | `*.sh`, `*.bash` | `Shell script issues in {file} (shellcheck)` |

#### 6. Security Integration (BLOCKING)

| Check | Pattern | Error Message |
|-------|---------|---------------|
| Hardcoded DB URLs | `postgresql://`, `mysql://`, `mongodb://` with credentials | `Hardcoded database credentials detected in {file}` |
| Hardcoded API auth | `https://user:pass@host` | `Hardcoded HTTP authentication detected in {file}` |
| Dangerous shell patterns | `eval` in shell scripts | `Use of eval() in {file} — ensure input is properly validated` |
| Error handling bypass | `set +e` in shell scripts | `set +e (error handling bypass) in {file} — ensure this is intentional` |

#### 7. Bypass Markers (WARNINGS)

| Pattern | Warning Message |
|---------|-----------------|
| `--no-verify` or `SKIP_HOOKS=1` in code | `{file} contains --no-verify or SKIP_HOOKS=1 — ensure this is intentional` |

### Example Output

**Success:**
```
✅ pre-commit: all checks passed
```

**With warnings:**
```
⚠️  Trailing whitespace detected in src/orchestration/agents/engineer.py
⚠️  Python style issues in src/config/models.py (flake8)

⚠️  pre-commit: 2 warning(s) found (non-blocking)
   Review warnings above; fix if possible before committing

✅ pre-commit: all checks passed
```

**With errors:**
```
❌ VIOLATION: External scripts in orchestration/scripts/ — all work must flow through DELEGATE/HANDBACK protocol
❌ AWS access key pattern detected in src/config/.env

❌ pre-commit: 2 error(s) found. Fix issues and re-commit.
   Emergency bypass: SKIP_HOOKS=1 git commit (document reason in commit msg)
```

---

## `.githooks/commit-msg` — Message Format & Protocol Validation

**Trigger:** After commit message is written  
**Severity:** Blocking (errors prevent commit)

### What It Checks

#### 1. Non-Empty Message (BLOCKING)

| Check | Rule | Error Message |
|-------|------|---------------|
| Empty message | Message must not be empty | `Commit message is empty` |

#### 2. Message Length (BLOCKING)

| Check | Rule | Error Message |
|-------|------|---------------|
| Minimum length | First line ≥ 10 characters | `Subject line too short ({N} chars). Minimum 10 chars required.` |
| Maximum length | First line ≤ 72 characters (recommended) | `Subject line too long ({N} chars). Maximum 72 chars recommended.` |

#### 3. Conventional Commit Format (WARNINGS)

Encourages (but doesn't block) conventional commit format:

```
type(scope): subject

body (optional)
```

| Valid Types | Example |
|------------|---------|
| `feat` | `feat(auth): add token grace period` |
| `fix` | `fix: resolve clock skew in mobile auth` |
| `docs` | `docs(SPEC): update routing rules` |
| `style` | `style: format agent definitions` |
| `refactor` | `refactor(queue): simplify polling logic` |
| `perf` | `perf: optimize YAML parsing` |
| `test` | `test: add integration tests for DELEGATE` |
| `chore` | `chore: bump dependencies` |
| `ci` | `ci: add pre-push hook validation` |
| `build` | `build: update renderer scripts` |
| `revert` | `revert: undo token grace period change` |

**Warning if format not followed:**
```
⚠️  Commit message does not follow conventional commit format
   Expected: type(scope): subject
   Examples: feat(auth): add token grace period
             fix: resolve clock skew
   Valid types: feat, fix, docs, style, refactor, perf, test, chore, ci, build, revert
```

#### 4. Task ID Tracking (INFORMATIONAL)

Detects task IDs in format `YYYY-MM-DD-kebab-case`:

```
✓ Task ID detected: 2026-05-16-hooks-documentation
```

Or warns if missing:
```
⚠️  No task ID found in commit message (format: YYYY-MM-DD-kebab-case)
   Example: 2026-05-16-hooks-commitmsg-implementation
```

#### 5. DELEGATE Block Validation (BLOCKING if present)

If commit message contains `DELEGATE` keyword, validates:

| Required Field | Error Message |
|---|---|
| `task_id` | `DELEGATE block missing required fields: task_id` |
| `role` | `DELEGATE block missing required fields: role` |
| `scope` | `DELEGATE block missing required fields: scope` |
| `plan` | `DELEGATE block missing required fields: plan` |
| `success_criteria` | `DELEGATE block missing required fields: success_criteria` |

Also validates:
- **Task ID format:** Must be `YYYY-MM-DD-kebab-case`
  - Error: `DELEGATE task_id format invalid (expected: YYYY-MM-DD-kebab-case)`

#### 6. HANDBACK Block Validation (BLOCKING if present)

If commit message contains `HANDBACK` keyword, validates:

| Required Field | Error Message |
|---|---|
| `task_id` | `HANDBACK block missing required fields: task_id` |
| `status` | `HANDBACK block missing required fields: status` |
| `deliverables` | `HANDBACK block missing required fields: deliverables` |
| `tests` | `HANDBACK block missing required fields: tests` |
| `quality_score` | `HANDBACK block missing required fields: quality_score` |

Also validates:
- **Status value:** Must be one of `complete`, `failed`, `partial`, `blocked`
  - Error: `HANDBACK status must be one of: complete, failed, partial, blocked`

#### 7. SKIP_HOOKS Bypass Documentation (BLOCKING if present)

If commit message mentions `SKIP_HOOKS`, requires documented reason:

| Check | Error Message |
|-------|---------------|
| Reason documented | `SKIP_HOOKS bypass is documented with reason` ✓ |
| No reason | `SKIP_HOOKS mentioned but no reason documented` ❌ |

**Valid formats for reason:**
```
SKIP_HOOKS: emergency fix for production outage
reason: database migration timeout
emergency: CI failure preventing deployment
bypass reason: clock skew in test environment
justification: temporary workaround pending upstream fix
```

#### 8. No Secrets in Message (BLOCKING)

Scans commit message for secret patterns:

| Pattern | Error Message |
|---------|---------------|
| `password`, `api_key`, `secret`, `token`, `private_key`, `aws_secret`, `github_token` | `Commit message contains potential secrets (password, api_key, token, etc.)` |

### Example Output

**Success:**
```
✓ Subject line length valid
✓ Task ID detected: 2026-05-16-hooks-documentation
✓ Conventional commit format followed

✅ commit-msg: validation passed
   Subject: docs: comprehensive hook documentation
   Body: 3 line(s)
```

**With warnings:**
```
⚠️  Commit message does not follow conventional commit format
   Expected: type(scope): subject

✅ commit-msg: validation passed
   Subject: Update hook documentation
   Body: 5 line(s)
```

**With errors:**
```
✗ Subject line too short (8 chars). Minimum 10 chars required.
   Current: 'fix hooks'
✗ SKIP_HOOKS mentioned but no reason documented
   Add one of the following:
   - SKIP_HOOKS: <reason>
   - reason: <explanation>
   - emergency: <justification>

❌ commit-msg: 2 error(s) found

Fix the errors above and retry:
  git commit --amend

To bypass validation (not recommended):
  SKIP_COMMIT_MSG_HOOK=true git commit
```

---

## `.githooks/pre-push` — Quality Gate Before Shared Branches

**Trigger:** Before `git push`  
**Severity:** Blocking (errors prevent push) + Warnings (non-blocking)

### What It Checks

#### 1. Protected Branch Detection (WARNINGS)

| Check | Warning Message |
|-------|-----------------|
| Pushing to `main` or `master` | `Pushing to protected branch: refs/heads/main` |
| | `Ensure Quality Engineer review is complete before merge` |

**Note:** This is a warning only — push proceeds. Use to ensure QE review is done.

#### 2. Agent YAML Frontmatter Validation (BLOCKING)

Validates all agent definitions in `src/agents/*.md`:

| Check | Error Message |
|-------|---------------|
| Valid YAML syntax | `Invalid YAML frontmatter in agent: src/agents/engineer.md` |
| Required field: `name` | `Missing required field 'name' in agent: src/agents/engineer.md` |
| Required field: `role` | `Missing required field 'role' in agent: src/agents/engineer.md` |
| Required field: `model` | `Missing required field 'model' in agent: src/agents/engineer.md` |
| Required field: `effort` | `Missing required field 'effort' in agent: src/agents/engineer.md` |

**Example agent frontmatter:**
```yaml
---
name: Engineer Agent
role: Engineer
model: claude-haiku-4-5
effort: high
description: Executes well-scoped, planned tasks
---
```

#### 3. Workflow File Validation (BLOCKING)

Validates all GitHub Actions workflows in `.github/workflows/`:

| Check | Error Message |
|-------|---------------|
| Valid YAML syntax | `Invalid YAML in workflow: .github/workflows/ci.yml` |
| Required field: `name` | `Missing 'name' field in workflow: .github/workflows/ci.yml` |
| Required field: `on` (trigger) | `Missing 'on' (trigger) field in workflow: .github/workflows/ci.yml` |

#### 4. Documentation Consistency (BLOCKING)

Validates presence and structure of critical documentation:

| Check | Error Message |
|-------|---------------|
| `docs/SPEC.md` exists | `docs/SPEC.md not found` |
| SPEC.md has top-level heading | `docs/SPEC.md missing top-level heading` |
| SPEC.md has version field | `docs/SPEC.md missing version field` |
| `docs/AGENTS.md` exists | `docs/AGENTS.md not found` |
| AGENTS.md has top-level heading | `docs/AGENTS.md missing top-level heading` |
| `README.md` exists | `README.md not found` |

#### 5. DELEGATE/HANDBACK Protocol Compliance (BLOCKING)

Validates all DELEGATE and HANDBACK files in artifacts/:

**DELEGATE files** (`artifacts/delegates/YYYY-MM-DD/*.yaml`):

| Check | Error Message |
|-------|---------------|
| Valid YAML syntax | `Invalid YAML in DELEGATE: artifacts/delegates/2026-05-16/DELEGATE-task-engineer.yaml` |
| Required field: `handoff_type` | `Missing required field 'handoff_type' in DELEGATE` |
| Required field: `task_id` | `Missing required field 'task_id' in DELEGATE` |
| Required field: `role` | `Missing required field 'role' in DELEGATE` |
| Required field: `model` | `Missing required field 'model' in DELEGATE` |

**HANDBACK files** (`artifacts/queue/processing/*.yaml`):

| Check | Error Message |
|-------|---------------|
| Valid YAML syntax | `Invalid YAML in HANDBACK: artifacts/queue/processing/HANDBACK-task.yaml` |
| Required field: `handoff_type` | `Missing required field 'handoff_type' in HANDBACK` |
| Required field: `task_id` | `Missing required field 'task_id' in HANDBACK` |
| Required field: `status` | `Missing required field 'status' in HANDBACK` |

#### 6. Test Suite Execution (WARNINGS)

Runs `pytest tests/` if available:

| Check | Result |
|-------|--------|
| All tests pass | `✅ All tests passed` |
| Some tests fail | `⚠️  Some tests failed — review before pushing to shared branches` |
| pytest not found | `⚠️  pytest not found — skipping test execution` |

**Note:** Test failures are warnings only — push proceeds. Fix before merging to main.

#### 7. SPEC Compliance Verification (BLOCKING)

Checks for prohibited patterns per SPEC.md:

| Check | Error Message |
|-------|---------------|
| No external scripts in `orchestration/scripts/` | `External scripts found in orchestration/scripts/ — violates SPEC.md` |
| No cron files in `orchestration/config/` | `Cron files found in orchestration/config/ — violates SPEC.md` |
| Makefile doesn't invoke external scripts | `Makefile invokes external scripts (not in renderer/) — violates SPEC.md` |

### Example Output

**Success:**
```
📋 Pre-push validation starting...

🤖 Validating agent definitions...
✅ Agent YAML frontmatter valid

🔄 Validating workflow files...
✅ Workflow files valid

📚 Validating documentation consistency...
✅ Documentation files present and valid

📦 Validating DELEGATE/HANDBACK protocol...
✅ DELEGATE/HANDBACK protocol valid

🧪 Running test suite...
✅ All tests passed

🔐 Validating SPEC compliance...
✅ SPEC compliance verified

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Pre-push validation summary:

  Checks passed: 7
  Checks failed: 0
  Errors:       0
  Warnings:     0

✅ pre-push: quality gate passed
```

**With warnings:**
```
⚠️  Pushing to protected branch: refs/heads/main
⚠️  Ensure Quality Engineer review is complete before merge

⚠️  Some tests failed — review before pushing to shared branches

⚠️  pre-push: 2 warning(s) — proceeding (warnings are non-blocking)

✅ pre-push: quality gate passed
```

**With errors:**
```
❌ Invalid YAML in DELEGATE: artifacts/delegates/2026-05-16/DELEGATE-task-engineer.yaml
❌ Missing required field 'role' in DELEGATE: artifacts/delegates/2026-05-16/DELEGATE-task-engineer.yaml
❌ External scripts found in orchestration/scripts/ — violates SPEC.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Pre-push validation summary:

  Checks passed: 4
  Checks failed: 3
  Errors:       3
  Warnings:     0

❌ pre-push: 3 error(s) found. Fix and retry.

   Emergency bypass: SKIP_HOOKS=1 git push
```

---

## Bypass Procedures

### When to Bypass

Bypass hooks **ONLY** in genuine emergencies:
- ✅ Production outage requiring immediate hotfix
- ✅ Critical security vulnerability requiring immediate patch
- ✅ CI/CD failure blocking team (temporary, must fix root cause)
- ✅ Temporary workaround pending upstream fix

### When NOT to Bypass

Never bypass for:
- ❌ "Just this once" commits that violate SPEC
- ❌ Avoiding code review or quality gates
- ❌ Skipping tests because they're inconvenient
- ❌ Committing secrets because it's faster
- ❌ Lazy commits that don't follow format

### Bypass Methods

#### 1. Pre-Commit Bypass (SPEC/Secret Validation Only)

```bash
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: <reason>"
```

**What it skips:**
- SPEC.md compliance checks (external scripts, cron files, process execution)
- Secret detection (API keys, passwords, tokens)
- YAML/JSON validity
- Code style checks

**What it DOES NOT skip:**
- `commit-msg` hook still runs (message format validation)

**Use when:** You need to commit a temporary workaround that violates SPEC, but message format is fine.

**Example:**
```bash
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: temporary cron job for production data sync"
```

#### 2. Commit-Msg Hook Bypass

```bash
SKIP_COMMIT_MSG_HOOK=true git commit -m "emergency fix"
```

**What it skips:**
- Message length validation
- Conventional commit format
- DELEGATE/HANDBACK validation
- SKIP_HOOKS documentation

**Use when:** You need to commit with a minimal message in an emergency.

**Example:**
```bash
SKIP_COMMIT_MSG_HOOK=true git commit -m "hotfix"
```

#### 3. Pre-Push Bypass

```bash
SKIP_HOOKS=1 git push
```

**What it skips:**
- Agent YAML validation
- Workflow file validation
- Documentation consistency checks
- DELEGATE/HANDBACK protocol validation
- Test suite execution
- SPEC compliance verification

**Use when:** You need to push a commit that failed pre-push validation, but you've verified it's safe.

**Example:**
```bash
SKIP_HOOKS=1 git push origin hotfix-branch
```

#### 4. All Hooks Bypass (STRONGLY DISCOURAGED)

```bash
git commit --no-verify -m "message"
```

**What it skips:** ALL hooks (pre-commit, commit-msg, pre-push)

**⚠️ WARNING:** This is the nuclear option. Use ONLY if all other bypasses fail and you have explicit authorization from a Lead Engineer or above.

**Why it's discouraged:**
- Breaks audit trail
- Violates SPEC.md
- Prevents quality gate validation
- Can introduce secrets into repo

### Required Documentation for Bypass

**Every bypass MUST be documented:**

1. **In commit message:**
   ```
   emergency: production outage — database connection timeout
   
   SKIP_HOOKS: production hotfix requiring immediate deployment
   reason: database connection pool exhausted, blocking all requests
   approved_by: lead-engineer-name
   ticket: PROD-12345
   ```

2. **In commit body (if applicable):**
   - What was bypassed and why
   - Who authorized the bypass
   - Ticket/issue reference
   - Plan to fix root cause

3. **Post-bypass checklist:**
   - [ ] Bypass was documented in commit message
   - [ ] Lead Engineer or above approved bypass
   - [ ] Root cause fix is planned
   - [ ] Tests will be added/fixed in follow-up commit
   - [ ] SPEC violations will be addressed in follow-up

### Post-Bypass Checklist

After using a bypass, immediately:

1. **Create a follow-up task:**
   ```bash
   # Create a task to fix the root cause
   echo "task: fix root cause of bypass" >> TODO.md
   ```

2. **Re-enable hooks:**
   ```bash
   git config core.hooksPath .githooks
   ```

3. **Verify hooks are active:**
   ```bash
   git config core.hooksPath  # should return: .githooks
   ```

4. **Fix the underlying issue:**
   - Add missing tests
   - Fix SPEC violations
   - Add secrets to `.gitignore` or secret management
   - Update documentation

5. **Create a follow-up commit:**
   ```bash
   git commit -m "fix: address root cause of emergency bypass

   - Added missing test coverage
   - Fixed SPEC.md violations
   - Updated documentation
   - Ticket: PROD-12345"
   ```

---

## OpenCode Commands

Available in the TUI via `/command-name`:

| Command | Description | Agent | Use When |
|---------|-------------|-------|----------|
| `/sdlc-check` | Full SDLC compliance check (queue, DELEGATEs, hooks) | orchestrator | Before committing work; verify hooks are active |
| `/hooks-install` | Install/verify git enforcement hooks | — | After cloning repo; after `make install` |
| `/queue-status` | Review pending DELEGATEs and HANDBACKs | orchestrator | Check workflow status; see what's in progress |

---

## Environment Variables Reference

### Pre-Commit Hook

| Variable | Values | Effect |
|----------|--------|--------|
| `SKIP_HOOKS` | `1` | Bypass all pre-commit checks |
| `BYPASS_HOOK_VALIDATION` | `true` | Bypass SPEC/secret checks only (commit-msg still runs) |

### Commit-Msg Hook

| Variable | Values | Effect |
|----------|--------|--------|
| `SKIP_COMMIT_MSG_HOOK` | `true` | Bypass message format validation |

### Pre-Push Hook

| Variable | Values | Effect |
|----------|--------|--------|
| `SKIP_HOOKS` | `1` | Bypass all pre-push checks |

### Global

| Variable | Values | Effect |
|----------|--------|--------|
| `GIT_HOOKS_DEBUG` | `1` | Enable debug output from hooks (if implemented) |

---

## Integration with DELEGATE/HANDBACK Protocol

### How Hooks Enforce the Protocol

The git hooks are the **final enforcement point** for the DELEGATE/HANDBACK protocol:

1. **DELEGATE Creation:**
   - Orchestrator creates DELEGATE block with all required fields
   - `pre-commit` hook validates YAML syntax and required fields
   - `commit-msg` hook validates DELEGATE structure if present in message

2. **Agent Execution:**
   - Agent receives DELEGATE and executes work
   - Agent returns HANDBACK with results

3. **HANDBACK Submission:**
   - Quality Engineer reviews HANDBACK
   - `pre-commit` hook validates HANDBACK YAML syntax
   - `commit-msg` hook validates HANDBACK structure if present in message

4. **Pre-Push Quality Gate:**
   - `pre-push` hook validates all DELEGATE/HANDBACK files in artifacts/
   - Ensures protocol compliance before pushing to shared branch

### What Agents Must Ensure Before Committing

Before committing work that includes DELEGATE/HANDBACK blocks:

- ✅ All required fields present (task_id, role, scope, plan, success_criteria for DELEGATE)
- ✅ YAML syntax is valid (no indentation errors, proper quotes)
- ✅ Task IDs follow format: `YYYY-MM-DD-kebab-case`
- ✅ Status values are valid: `complete`, `failed`, `partial`, `blocked`
- ✅ No secrets in DELEGATE/HANDBACK blocks
- ✅ Commit message documents the work (conventional commit format)

---

## Cross-Harness Support Matrix

| Enforcement Point | OpenCode | Claude Code | Copilot CLI | π.dev |
|-------------------|----------|-------------|-------------|-------|
| Git pre-commit | ✅ `.githooks/pre-commit` | ✅ same repo hooks | ✅ same repo hooks | ✅ same repo hooks |
| Git commit-msg | ✅ `.githooks/commit-msg` | ✅ same | ✅ same | ✅ same |
| Git pre-push | ✅ `.githooks/pre-push` | ✅ same | ✅ same | ✅ same |
| Session guard (preToolUse) | ❌ no native hook | ❌ no native hook | ✅ `copilot-guard.sh` | ❌ no native hook |
| Session init | ❌ AGENTS.md rules | ❌ CLAUDE.md rules | ✅ `copilot-session-init.sh` | ❌ SYSTEM.md rules |
| SDLC commands | ✅ `.opencode/commands/` | ❌ not supported | ❌ not supported | ❌ not supported |
| Auto hook install | ✅ `render-opencode.sh` | ❌ manual | ❌ manual | ❌ manual |

**Notes:**
- Git hooks apply to all harnesses equally (they're repo-level, not tool-level)
- Copilot CLI has the strongest runtime enforcement via `preToolUse` hooks
- OpenCode has the richest workflow commands via `.opencode/commands/`
- Claude Code and π.dev rely on instruction-level rules (CLAUDE.md / SYSTEM.md)

---

## Installation

### Automatic (Recommended)

```bash
make install          # renders all harnesses + configures git hooks
```

This command:
1. Renders agents and skills to `~/.config/opencode/`, `~/.claude/`, etc.
2. Configures git hooks: `git config core.hooksPath .githooks`
3. Makes hooks executable: `chmod +x .githooks/*`

### Manual Installation

If you need to configure hooks manually:

```bash
# 1. Set hooks path
git config core.hooksPath .githooks

# 2. Make hooks executable
chmod +x .githooks/pre-commit
chmod +x .githooks/commit-msg
chmod +x .githooks/pre-push

# 3. Verify installation
git config core.hooksPath   # should return: .githooks
ls -la .githooks/            # should show all 3 hooks as executable
```

### Verify Installation

```bash
# Check hooks path
git config core.hooksPath
# Expected output: .githooks

# Check hooks are executable
ls -la .githooks/
# Expected output:
# -rwxr-xr-x  1 user  group  ... pre-commit
# -rwxr-xr-x  1 user  group  ... commit-msg
# -rwxr-xr-x  1 user  group  ... pre-push

# Test pre-commit hook
.githooks/pre-commit
# Expected output: ✅ pre-commit: all checks passed

# Use OpenCode command
/sdlc-check
```

---

## Troubleshooting

### Hook Not Running

**Symptom:** Hook doesn't execute when committing/pushing

**Diagnosis:**
```bash
git config core.hooksPath
# If empty or not set to .githooks, hook won't run
```

**Fix:**
```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/commit-msg .githooks/pre-push
```

**Verify:**
```bash
git config core.hooksPath  # should return: .githooks
```

### YAML Validation Failing

**Symptom:** `Invalid YAML syntax in {file}`

**Diagnosis:**
```bash
# Check if python3 and pyyaml are installed
python3 --version
python3 -c "import yaml; print(yaml.__version__)"
```

**Fix:**
```bash
# Install pyyaml
pip3 install pyyaml

# Verify YAML file syntax
python3 -c "import yaml; yaml.safe_load(open('{file}'))"
```

**Common YAML errors:**
- Indentation (must be spaces, not tabs)
- Missing colons after keys
- Unquoted strings with special characters
- Trailing colons without values

### Secret Detection False Positives

**Symptom:** Hook blocks commit with "possible secret detected"

**Diagnosis:**
```bash
# Check what pattern matched
git diff --cached | grep -i "api_key\|secret\|password"
```

**Fix:**
1. If it's a real secret: Remove it and use environment variables
2. If it's a false positive: Use bypass with documentation
   ```bash
   BYPASS_HOOK_VALIDATION=true git commit -m "docs: example API configuration"
   ```

### Tests Failing on Pre-Push

**Symptom:** `⚠️  Some tests failed — review before pushing to shared branches`

**Note:** This is a warning only — push proceeds.

**Fix:**
```bash
# Run tests locally to see failures
pytest tests/ -v

# Fix failing tests
# ... make code changes ...

# Re-commit and push
git add .
git commit -m "fix: address test failures"
git push
```

### Commit-Msg Hook Rejecting Valid Messages

**Symptom:** `Subject line too short` or format errors

**Diagnosis:**
```bash
# Check message length
echo "your message" | wc -c
# Must be ≥10 characters
```

**Fix:**
```bash
# Make message more descriptive
git commit --amend -m "feat(auth): add token grace period validation"
```

### Pre-Push Failing on Protected Branch

**Symptom:** `Pushing to protected branch: refs/heads/main`

**Note:** This is a warning only — push proceeds.

**What to check:**
- [ ] Quality Engineer review is complete
- [ ] All tests passing locally
- [ ] Code follows SPEC.md
- [ ] Commit message is descriptive

### DELEGATE/HANDBACK Validation Errors

**Symptom:** `Missing required field 'task_id' in DELEGATE`

**Diagnosis:**
```bash
# Check DELEGATE/HANDBACK file
cat artifacts/delegates/2026-05-16/DELEGATE-task.yaml

# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('artifacts/delegates/2026-05-16/DELEGATE-task.yaml'))"
```

**Fix:**
1. Ensure all required fields are present
2. Check YAML indentation and syntax
3. Validate task_id format: `YYYY-MM-DD-kebab-case`

**Required DELEGATE fields:**
- `handoff_type: DELEGATE`
- `task_id: YYYY-MM-DD-kebab-case`
- `role: {Engineer|Senior Engineer|...}`
- `model: claude-{haiku|sonnet|opus}-*`
- `scope: {description}`
- `plan: {numbered steps}`
- `success_criteria: {testable criteria}`

**Required HANDBACK fields:**
- `handoff_type: HANDBACK`
- `task_id: YYYY-MM-DD-kebab-case`
- `status: {complete|failed|partial|blocked}`
- `deliverables: {list of changes}`
- `tests: {test results}`
- `quality_score: {0-100}`

### Agent YAML Frontmatter Invalid

**Symptom:** `Invalid YAML frontmatter in agent: src/agents/engineer.md`

**Diagnosis:**
```bash
# Extract and validate frontmatter
awk '/^---/{if(p)exit; p=1; next} p' src/agents/engineer.md | python3 -c "import sys,yaml; yaml.safe_load(sys.stdin)"
```

**Fix:**
1. Check indentation in frontmatter (must be spaces)
2. Ensure required fields: `name`, `role`, `model`, `effort`
3. Use proper YAML syntax (colons, quotes, etc.)

**Example valid frontmatter:**
```yaml
---
name: Engineer Agent
role: Engineer
model: claude-haiku-4-5
effort: high
description: Executes well-scoped, planned tasks
---
```

### Python/PyYAML Not Installed

**Symptom:** Hooks skip YAML validation with no error

**Diagnosis:**
```bash
python3 --version
python3 -c "import yaml"
```

**Fix:**
```bash
# Install Python 3 and PyYAML
brew install python3  # macOS
sudo apt-get install python3 python3-pip  # Linux

# Install PyYAML
pip3 install pyyaml
```

### Shellcheck Issues

**Symptom:** `Shell script issues in {file} (shellcheck)`

**Diagnosis:**
```bash
shellcheck {file}
```

**Fix:**
```bash
# Install shellcheck
brew install shellcheck  # macOS
sudo apt-get install shellcheck  # Linux

# Fix issues
shellcheck -f diff {file} | patch {file}
```

### Flake8 Issues

**Symptom:** `Python style issues in {file} (flake8)`

**Diagnosis:**
```bash
flake8 {file} --max-line-length=100 --extend-ignore=E203,W503
```

**Fix:**
```bash
# Install flake8
pip3 install flake8

# Fix issues
autopep8 --in-place {file}
```

### Emergency Bypass Not Working

**Symptom:** `SKIP_HOOKS=1 git commit` still runs hooks

**Diagnosis:**
```bash
# Check if variable is set
echo $SKIP_HOOKS

# Check hook implementation
grep "SKIP_HOOKS" .githooks/pre-commit
```

**Fix:**
```bash
# Ensure variable is set correctly
SKIP_HOOKS=1 git commit -m "emergency: reason"

# Or use alternative bypass
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: reason"
```

### Hooks Running Slowly

**Symptom:** `git commit` takes >5 seconds

**Diagnosis:**
```bash
# Time the hook
time .githooks/pre-commit

# Check for slow operations (file scanning, network calls)
```

**Fix:**
1. Reduce number of staged files
2. Ensure python3 and pyyaml are installed (YAML parsing is slow without them)
3. Disable slow checks if not needed (flake8, shellcheck)

---

## Security Considerations for Bypass Procedures

### Audit Trail

Every bypass is logged in:
- **Commit message:** Documents reason and authorization
- **Git log:** `git log --all --oneline | grep -i "skip_hooks\|bypass"`
- **Hooks:** Emit warning message to stdout

### Authorization

Bypass should only be authorized by:
- ✅ Lead Engineer or above
- ✅ On-call engineer (for production emergencies)
- ✅ Security Engineer (for security vulnerabilities)

### Restrictions

- ❌ Never bypass without documenting reason
- ❌ Never commit secrets, even with bypass
- ❌ Never use bypass to avoid code review
- ❌ Never use bypass to skip tests permanently

### Post-Bypass Verification

After using bypass:
1. Verify commit was pushed successfully
2. Verify no secrets were committed: `git log -p | grep -i "password\|api_key\|secret"`
3. Create follow-up task to fix root cause
4. Re-enable hooks: `git config core.hooksPath .githooks`

---

## Workflow Enforcement Points

```
User Request
     │
     ▼
[OpenCode /sdlc-check]  ← manual compliance check
     │
     ▼
Orchestrator (queue routing)
     │
     ▼
DELEGATE → Agent Work
     │
     ▼
HANDBACK → QE Review
     │
     ▼
git commit ──► [pre-commit hook]  ← SPEC compliance, secrets, YAML
     │              │
     │         [commit-msg hook]  ← message format, protocol compliance
     │
     ▼
git push ───► [pre-push hook]    ← agent YAML, tests, documentation, protocol
```

---

## FAQ

**Q: Can I disable hooks permanently?**  
A: Not recommended. Hooks enforce SPEC.md and prevent secrets. If you need to disable them, use the bypass procedures with documentation.

**Q: What if I commit a secret by accident?**  
A: Immediately:
1. Rotate the secret (change password, revoke token, etc.)
2. Remove from git history: `git filter-branch --tree-filter 'rm -f {file}'`
3. Force push: `git push --force-with-lease`
4. Document incident in commit message

**Q: Can I modify the hooks?**  
A: Hooks are part of the SPEC.md enforcement. Changes require:
1. PR with detailed justification
2. Lead Engineer approval
3. Update to SPEC.md
4. Update to this documentation

**Q: What if a hook has a bug?**  
A: Report it immediately:
1. Create an issue with reproduction steps
2. Use bypass with documentation: `SKIP_HOOKS=1 git commit`
3. Create follow-up task to fix hook
4. Test fix before merging

**Q: How do I test hook changes?**  
A: Use a test branch:
```bash
git checkout -b test-hook-changes
# Make hook changes
# Test: git commit -m "test message"
# If working, merge to main
```

---

## Update Log

- **2026-05-16:** Comprehensive documentation created with full hook source code reference, bypass procedures, troubleshooting (15+ scenarios), environment variables, and integration with DELEGATE/HANDBACK protocol.
- **Previous:** Basic hook overview (see Git History)
