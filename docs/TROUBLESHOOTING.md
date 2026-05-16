---
name: Troubleshooting Guide for Git Hooks and SDLC Enforcement
description: Comprehensive troubleshooting for hook failures, validation errors, and bypass procedures
version: 1.0
updated: 2026-05-16
status: Production Ready
---

# Troubleshooting Guide

**Last Updated:** 2026-05-16  
**Scope:** Troubleshooting for git hooks, SDLC enforcement, and bypass procedures  
**Status:** Production Ready — 30+ scenarios covered

---

## Quick Diagnosis

### Symptom: Hook not running at all

```bash
# 1. Check if hooks are configured
git config core.hooksPath
# Expected: .githooks

# 2. Check if hooks are executable
ls -la .githooks/
# Expected: -rwxr-xr-x (executable)

# 3. Test hook manually
.githooks/pre-commit
# Should output: ✅ pre-commit: all checks passed
```

**If hooks path is not set:**
```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/commit-msg .githooks/pre-push
```

---

## Pre-Commit Hook Troubleshooting

### Issue 1: Hook not running on commit

**Symptom:** `git commit` succeeds without running pre-commit hook

**Diagnosis:**
```bash
# Check hooks path
git config core.hooksPath
# If empty or different, hook won't run

# Check hook is executable
ls -la .githooks/pre-commit
# Should show: -rwxr-xr-x

# Check hook shebang
head -1 .githooks/pre-commit
# Should show: #!/usr/bin/env bash
```

**Fix:**
```bash
# Set hooks path
git config core.hooksPath .githooks

# Make hooks executable
chmod +x .githooks/pre-commit .githooks/commit-msg .githooks/pre-push

# Verify
git config core.hooksPath  # should return: .githooks
```

### Issue 2: "VIOLATION: External scripts in orchestration/scripts/"

**Symptom:** Pre-commit blocks with error about external scripts

**Error Message:**
```
❌ VIOLATION: External scripts in orchestration/scripts/ — all work must flow through DELEGATE/HANDBACK protocol
```

**Diagnosis:**
```bash
# Check what files are in orchestration/scripts/
ls -la orchestration/scripts/

# Check what's staged
git diff --cached --name-only | grep orchestration/scripts/
```

**Fix:**
1. **If file should NOT be in orchestration/scripts/:**
   ```bash
   git rm orchestration/scripts/bad-script.py
   git commit -m "remove: external script from orchestration/scripts/"
   ```

2. **If file MUST be there (temporary):**
   ```bash
   BYPASS_HOOK_VALIDATION=true git commit -m "emergency: temporary script for production fix"
   ```
   Then create follow-up task to move script into agent code.

**Why this rule exists:**
- SPEC.md requires all work to flow through DELEGATE/HANDBACK protocol
- External scripts bypass the queue and break observability
- Exception: `renderer/scripts/` is for build-time installation only

### Issue 3: "Possible secret detected"

**Symptom:** Pre-commit blocks with secret detection error

**Error Messages:**
```
❌ Possible secret detected in src/config/settings.py — review before committing
❌ AWS access key pattern detected in .env
❌ GitHub personal access token pattern detected in src/auth.py
❌ Private key detected in keys/id_rsa — should not be committed
```

**Diagnosis:**
```bash
# Check what pattern matched
git diff --cached | grep -i "api_key\|secret\|password\|token"

# Check specific file
git show :src/config/settings.py | grep -i "password\|api_key"
```

**Fix:**

**Option 1: It's a real secret (RECOMMENDED)**
```bash
# 1. Remove the secret
# Edit file and remove hardcoded secret

# 2. Use environment variable instead
# Example: os.environ.get('API_KEY')

# 3. Stage changes
git add src/config/settings.py

# 4. Commit
git commit -m "fix: use environment variable for API key"

# 5. Verify secret is not in git history
git log -p | grep -i "api_key.*=" | head -5
```

**Option 2: It's a false positive (TEMPORARY)**
```bash
# 1. Document why it's safe
# Example: "This is example code, not a real key"

# 2. Use bypass
BYPASS_HOOK_VALIDATION=true git commit -m "docs: example API configuration

This is example code showing API key format, not a real key.
Real keys use environment variables."

# 3. Add comment in code to clarify
# Example: # NOTE: This is example code, not a real key
```

**Common false positives:**
- Example code with fake keys
- Documentation showing API format
- Comments explaining authentication
- Placeholder values in templates

### Issue 4: "Invalid YAML syntax"

**Symptom:** Pre-commit blocks with YAML parsing error

**Error Message:**
```
❌ Invalid YAML syntax in src/agents/engineer.md
```

**Diagnosis:**
```bash
# Check if python3 is installed
python3 --version

# Check if pyyaml is installed
python3 -c "import yaml; print(yaml.__version__)"

# Try to parse the file
python3 -c "import yaml; yaml.safe_load(open('src/agents/engineer.md'))"
```

**Fix:**

**If python3 or pyyaml not installed:**
```bash
# macOS
brew install python3
pip3 install pyyaml

# Linux
sudo apt-get install python3 python3-pip
pip3 install pyyaml

# Verify
python3 -c "import yaml; print('pyyaml installed')"
```

**If YAML syntax is invalid:**
```bash
# Check the file
cat src/agents/engineer.md | head -20

# Common YAML errors:
# 1. Indentation (must be spaces, not tabs)
# 2. Missing colons after keys
# 3. Unquoted strings with special characters
# 4. Trailing colons without values
```

**Example fixes:**

**Error: Indentation with tabs**
```yaml
# WRONG (tabs)
---
name: Engineer
	role: Engineer  # ← tab instead of spaces

# RIGHT (spaces)
---
name: Engineer
  role: Engineer  # ← 2 spaces
```

**Error: Missing colon**
```yaml
# WRONG
---
name Engineer

# RIGHT
---
name: Engineer
```

**Error: Unquoted special characters**
```yaml
# WRONG
---
description: This is a test: with colon

# RIGHT
---
description: "This is a test: with colon"
```

### Issue 5: "Invalid JSON syntax"

**Symptom:** Pre-commit blocks with JSON parsing error

**Error Message:**
```
❌ Invalid JSON syntax in opencode.jsonc (JSONC comments stripped before check)
```

**Diagnosis:**
```bash
# Check if python3 is installed
python3 --version

# Try to parse the file (JSONC comments are stripped)
python3 -c "
import sys, re, json
content = open('opencode.jsonc').read()
# Strip // comments
content = re.sub(r'(?m)//.*$', '', content)
# Strip /* */ comments
content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
json.loads(content)
print('JSON valid')
"
```

**Fix:**

**Common JSON errors:**
```json
// WRONG (trailing comma)
{
  "key": "value",
}

// RIGHT
{
  "key": "value"
}

// WRONG (single quotes)
{
  'key': 'value'
}

// RIGHT
{
  "key": "value"
}

// WRONG (unquoted keys)
{
  key: "value"
}

// RIGHT
{
  "key": "value"
}
```

**For JSONC files (with comments):**
```jsonc
// Comments are OK
{
  "key": "value",  // This comment is OK
  "array": [
    "item1",
    // "item2"  ← commented out item is OK
    "item3"
  ]
}
```

### Issue 6: "DOS line endings (CRLF) detected"

**Symptom:** Pre-commit warns about line endings

**Warning Message:**
```
⚠️  DOS line endings (CRLF) detected in src/orchestration/agents/engineer.py — convert to Unix (LF)
```

**Diagnosis:**
```bash
# Check line endings
file src/orchestration/agents/engineer.py
# Output: ... CRLF ... (bad)
# Output: ... LF ... (good)

# Or use od to see line endings
od -c src/orchestration/agents/engineer.py | grep -E "\\\\r|\\\\n" | head -5
```

**Fix:**
```bash
# Convert CRLF to LF
# Option 1: Using dos2unix
dos2unix src/orchestration/agents/engineer.py

# Option 2: Using sed
sed -i 's/\r$//' src/orchestration/agents/engineer.py

# Option 3: Using git
git config core.safecrlf false  # Allow mixed line endings
git add -A
git commit -m "fix: normalize line endings to LF"

# Verify
file src/orchestration/agents/engineer.py
# Should show: ... LF ...
```

**Prevention:**
```bash
# Configure git to auto-convert line endings
git config --global core.autocrlf true  # macOS/Linux
git config --global core.autocrlf input  # macOS/Linux (stricter)

# Or use .gitattributes
echo "* text=auto" >> .gitattributes
echo "*.py text eol=lf" >> .gitattributes
echo "*.sh text eol=lf" >> .gitattributes
git add .gitattributes
git commit -m "chore: normalize line endings"
```

### Issue 7: "Trailing whitespace detected"

**Symptom:** Pre-commit warns about trailing spaces

**Warning Message:**
```
⚠️  Trailing whitespace detected in src/config/models.py
```

**Diagnosis:**
```bash
# Show trailing whitespace
grep -n '[[:space:]]$' src/config/models.py

# Or use sed to highlight
sed -n 's/[[:space:]]*$/[TRAILING]/p' src/config/models.py
```

**Fix:**
```bash
# Remove trailing whitespace
# Option 1: Using sed
sed -i 's/[[:space:]]*$//' src/config/models.py

# Option 2: Using Python
python3 -c "
with open('src/config/models.py') as f:
    lines = f.readlines()
with open('src/config/models.py', 'w') as f:
    f.writelines(line.rstrip() + '\n' for line in lines)
"

# Verify
grep -n '[[:space:]]$' src/config/models.py
# Should return nothing
```

### Issue 8: "Python style issues" (flake8)

**Symptom:** Pre-commit warns about Python style

**Warning Message:**
```
⚠️  Python style issues in src/config/models.py (flake8)
```

**Diagnosis:**
```bash
# Check if flake8 is installed
flake8 --version

# Run flake8 on the file
flake8 src/config/models.py --max-line-length=100 --extend-ignore=E203,W503
```

**Fix:**

**Option 1: Auto-fix with autopep8**
```bash
# Install autopep8
pip3 install autopep8

# Auto-fix the file
autopep8 --in-place src/config/models.py

# Verify
flake8 src/config/models.py
```

**Option 2: Manual fixes**

Common flake8 errors:
```python
# E501: Line too long
# FIX: Break line or increase max-line-length

# W391: Blank line at end of file
# FIX: Remove trailing blank lines

# F401: Imported but unused
# FIX: Remove unused import

# E302: Expected 2 blank lines
# FIX: Add blank line between functions

# E265: Block comment should start with '# '
# FIX: Add space after #
```

### Issue 9: "Shell script issues" (shellcheck)

**Symptom:** Pre-commit warns about shell script issues

**Warning Message:**
```
⚠️  Shell script issues in scripts/deploy.sh (shellcheck)
```

**Diagnosis:**
```bash
# Check if shellcheck is installed
shellcheck --version

# Run shellcheck on the file
shellcheck scripts/deploy.sh
```

**Fix:**

**Option 1: Auto-fix with shfmt**
```bash
# Install shfmt
brew install shfmt  # macOS
sudo apt-get install shfmt  # Linux

# Auto-fix the file
shfmt -i 2 -w scripts/deploy.sh

# Verify
shellcheck scripts/deploy.sh
```

**Option 2: Manual fixes**

Common shellcheck errors:
```bash
# SC2086: Double quote to prevent globbing
# WRONG: $var
# RIGHT: "$var"

# SC2181: Check exit code directly
# WRONG: if [ $? -eq 0 ]; then
# RIGHT: if command; then

# SC2046: Quote to prevent word splitting
# WRONG: echo $var
# RIGHT: echo "$var"

# SC2048: Use "$@" not $*
# WRONG: "$@"
# RIGHT: "$@"
```

### Issue 10: "Bypass marker in code"

**Symptom:** Pre-commit warns about bypass markers

**Warning Message:**
```
⚠️  src/orchestration/agents/engineer.py contains --no-verify or SKIP_HOOKS=1 — ensure this is intentional
```

**Diagnosis:**
```bash
# Check what's in the file
grep -n "SKIP_HOOKS\|--no-verify" src/orchestration/agents/engineer.py
```

**Fix:**

**If it's documentation or a comment:**
```bash
# Add clarifying comment
# Example:
# NOTE: This is documentation about bypass procedures, not actual code

# Or remove if not needed
git diff --cached src/orchestration/agents/engineer.py
```

**If it's actual code (bad):**
```bash
# Remove the bypass marker
# Replace with proper error handling
git add src/orchestration/agents/engineer.py
git commit -m "fix: remove bypass marker, use proper error handling"
```

---

## Commit-Msg Hook Troubleshooting

### Issue 1: "Subject line too short"

**Symptom:** Commit-msg hook blocks with length error

**Error Message:**
```
✗ Subject line too short (8 chars). Minimum 10 chars required.
   Current: 'fix hooks'
```

**Diagnosis:**
```bash
# Check message length
echo "fix hooks" | wc -c
# Output: 9 (including newline)
```

**Fix:**
```bash
# Make message more descriptive
git commit --amend -m "fix: update git hook validation"

# Or use conventional commit format
git commit --amend -m "fix(hooks): improve pre-commit validation"
```

**Minimum 10 characters:**
- ✅ "fix: update" (11 chars)
- ✅ "feat(auth): add" (15 chars)
- ❌ "fix hooks" (9 chars)

### Issue 2: "Subject line too long"

**Symptom:** Commit-msg hook warns about long subject line

**Warning Message:**
```
⚠️  Subject line too long (95 chars). Maximum 72 chars recommended.
   Current: 'feat: add comprehensive token validation with grace period and clock skew tolerance...'
```

**Diagnosis:**
```bash
# Check message length
echo "your message" | wc -c
# Should be ≤72 characters
```

**Fix:**
```bash
# Shorten the subject line
git commit --amend -m "feat: add token grace period validation"

# Move details to body
git commit --amend -m "feat: add token grace period validation

- Adds 30-second grace period to token expiry check
- Accounts for clock skew on mobile devices
- Maintains backward compatibility"
```

### Issue 3: "Commit message does not follow conventional commit format"

**Symptom:** Commit-msg hook warns about format

**Warning Message:**
```
⚠️  Commit message does not follow conventional commit format
   Expected: type(scope): subject
   Examples: feat(auth): add token grace period
             fix: resolve clock skew
   Valid types: feat, fix, docs, style, refactor, perf, test, chore, ci, build, revert
```

**Diagnosis:**
```bash
# Check message format
git log -1 --format=%B
# Should match: type(scope): subject
```

**Fix:**
```bash
# Use conventional commit format
git commit --amend -m "feat(auth): add token grace period"

# Or just fix (without scope)
git commit --amend -m "fix: resolve clock skew in mobile auth"

# Valid types:
# - feat: new feature
# - fix: bug fix
# - docs: documentation
# - style: formatting
# - refactor: code refactoring
# - perf: performance improvement
# - test: test addition/fix
# - chore: maintenance
# - ci: CI/CD changes
# - build: build system changes
# - revert: revert previous commit
```

### Issue 4: "No task ID found in commit message"

**Symptom:** Commit-msg hook warns about missing task ID

**Warning Message:**
```
⚠️  No task ID found in commit message (format: YYYY-MM-DD-kebab-case)
   Example: 2026-05-16-hooks-commitmsg-implementation
```

**Note:** This is a warning only — commit proceeds.

**Fix (optional):**
```bash
# Add task ID to commit message
git commit --amend -m "feat(hooks): add validation

Task: 2026-05-16-hooks-commitmsg-implementation"

# Or include in subject line
git commit --amend -m "feat(hooks): add validation [2026-05-16-hooks-commitmsg-implementation]"
```

**Task ID format:**
- `YYYY-MM-DD-kebab-case`
- Example: `2026-05-16-hooks-documentation`
- Not: `2026_05_16_hooks_documentation` (wrong separators)
- Not: `2026-5-16-hooks-documentation` (wrong date format)

### Issue 5: "DELEGATE block missing required fields"

**Symptom:** Commit-msg hook blocks when DELEGATE is incomplete

**Error Message:**
```
✗ DELEGATE block missing required fields: scope, plan
```

**Diagnosis:**
```bash
# Check commit message
git log -1 --format=%B

# Look for DELEGATE block
# Should have: task_id, role, scope, plan, success_criteria
```

**Fix:**
```bash
# Add missing fields to DELEGATE block
git commit --amend

# Example complete DELEGATE:
# ---
# handoff_type: DELEGATE
# task_id: 2026-05-16-hooks-documentation
# role: Engineer
# scope: Create comprehensive hook documentation
# plan:
#   1. Update SDLC-HOOKS.md
#   2. Create WORKFLOW.md
# success_criteria:
#   - All hooks documented
#   - Examples provided
# ---
```

**Required DELEGATE fields:**
- `task_id`: YYYY-MM-DD-kebab-case
- `role`: Valid role (Engineer, Senior Engineer, etc.)
- `scope`: Clear description
- `plan`: Numbered steps
- `success_criteria`: Testable criteria

### Issue 6: "HANDBACK block missing required fields"

**Symptom:** Commit-msg hook blocks when HANDBACK is incomplete

**Error Message:**
```
✗ HANDBACK block missing required fields: deliverables, tests, quality_score
```

**Diagnosis:**
```bash
# Check commit message
git log -1 --format=%B

# Look for HANDBACK block
# Should have: task_id, status, deliverables, tests, quality_score
```

**Fix:**
```bash
# Add missing fields to HANDBACK block
git commit --amend

# Example complete HANDBACK:
# ---
# handoff_type: HANDBACK
# task_id: 2026-05-16-hooks-documentation
# status: complete
# deliverables:
#   - Updated: docs/SDLC-HOOKS.md
#   - Created: docs/WORKFLOW.md
# tests:
#   - All hooks tested: PASS
#   - Documentation reviewed: PASS
# quality_score: 95
# ---
```

**Required HANDBACK fields:**
- `task_id`: YYYY-MM-DD-kebab-case
- `status`: complete|failed|partial|blocked
- `deliverables`: List of changes
- `tests`: Test results
- `quality_score`: 0-100

### Issue 7: "HANDBACK status must be one of: complete, failed, partial, blocked"

**Symptom:** Commit-msg hook blocks with invalid status

**Error Message:**
```
✗ HANDBACK status must be one of: complete, failed, partial, blocked
```

**Diagnosis:**
```bash
# Check HANDBACK status in commit message
git log -1 --format=%B | grep "status:"
# Should be: complete, failed, partial, or blocked
```

**Fix:**
```bash
# Use valid status value
git commit --amend

# Valid statuses:
# - complete: Task fully completed
# - failed: Task failed, cannot proceed
# - partial: Task partially completed
# - blocked: Task blocked, waiting for unblocking
```

### Issue 8: "SKIP_HOOKS mentioned but no reason documented"

**Symptom:** Commit-msg hook blocks when bypass is not documented

**Error Message:**
```
✗ SKIP_HOOKS mentioned but no reason documented
   Add one of the following:
   - SKIP_HOOKS: <reason>
   - reason: <explanation>
   - emergency: <justification>
```

**Diagnosis:**
```bash
# Check commit message
git log -1 --format=%B | grep -i "skip_hooks"
# Should have reason documented
```

**Fix:**
```bash
# Add documented reason
git commit --amend -m "emergency: production database fix

SKIP_HOOKS: database connection pool exhausted
reason: immediate fix required to restore service
approved_by: lead-engineer-name"
```

**Valid reason formats:**
```
SKIP_HOOKS: production outage — immediate fix required
reason: database migration timeout
emergency: CI failure preventing deployment
bypass reason: clock skew in test environment
justification: temporary workaround pending upstream fix
```

### Issue 9: "Commit message contains potential secrets"

**Symptom:** Commit-msg hook blocks when secrets are in message

**Error Message:**
```
✗ Commit message contains potential secrets (password, api_key, token, etc.)
```

**Diagnosis:**
```bash
# Check commit message
git log -1 --format=%B | grep -i "password\|api_key\|token\|secret"
```

**Fix:**
```bash
# Remove secrets from message
git commit --amend -m "fix: update authentication configuration

Use environment variables for API keys and passwords.
See .env.example for required variables."

# Never include:
# - Passwords
# - API keys
# - Tokens
# - Private keys
# - AWS secrets
# - Database credentials
```

---

## Pre-Push Hook Troubleshooting

### Issue 1: "Pushing to protected branch"

**Symptom:** Pre-push hook warns about pushing to main/master

**Warning Message:**
```
⚠️  Pushing to protected branch: refs/heads/main
⚠️  Ensure Quality Engineer review is complete before merge
```

**Note:** This is a warning only — push proceeds.

**Diagnosis:**
```bash
# Check current branch
git branch
# Should not be main or master

# Check what branch you're pushing to
git push --dry-run origin <branch>
```

**Fix:**
1. **If you meant to push to main:**
   - Ensure Quality Engineer review is complete
   - Ensure all tests passing
   - Proceed with push

2. **If you meant to push to a feature branch:**
   ```bash
   # Create feature branch
   git checkout -b feature/my-feature
   git push origin feature/my-feature
   ```

### Issue 2: "Invalid YAML frontmatter in agent"

**Symptom:** Pre-push hook blocks with agent YAML error

**Error Message:**
```
❌ Invalid YAML frontmatter in agent: src/agents/engineer.md
❌ Missing required field 'role' in agent: src/agents/engineer.md
```

**Diagnosis:**
```bash
# Extract frontmatter
awk '/^---/{if(p)exit; p=1; next} p' src/agents/engineer.md

# Validate YAML
awk '/^---/{if(p)exit; p=1; next} p' src/agents/engineer.md | \
  python3 -c "import sys,yaml; yaml.safe_load(sys.stdin)"
```

**Fix:**
```bash
# Check agent file
cat src/agents/engineer.md | head -20

# Example valid frontmatter:
# ---
# name: Engineer Agent
# role: Engineer
# model: claude-haiku-4-5
# effort: high
# description: Executes well-scoped, planned tasks
# ---

# Fix issues:
# 1. Ensure YAML syntax is valid (indentation, colons, quotes)
# 2. Add required fields: name, role, model, effort
# 3. Commit and re-push
```

**Required agent fields:**
- `name`: Agent name
- `role`: Valid role (Engineer, Senior Engineer, etc.)
- `model`: Valid model (claude-haiku-4-5, claude-sonnet-4-6, etc.)
- `effort`: Valid effort level (low, medium, high, max)

### Issue 3: "Invalid YAML in workflow"

**Symptom:** Pre-push hook blocks with workflow YAML error

**Error Message:**
```
❌ Invalid YAML in workflow: .github/workflows/ci.yml
❌ Missing 'name' field in workflow: .github/workflows/ci.yml
```

**Diagnosis:**
```bash
# Check workflow file
cat .github/workflows/ci.yml | head -20

# Validate YAML
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```

**Fix:**
```bash
# Example valid workflow:
# name: CI
# on: [push, pull_request]
# jobs:
#   test:
#     runs-on: ubuntu-latest
#     steps:
#       - uses: actions/checkout@v2
#       - name: Run tests
#         run: pytest tests/

# Fix issues:
# 1. Ensure YAML syntax is valid
# 2. Add required fields: name, on (trigger)
# 3. Commit and re-push
```

**Required workflow fields:**
- `name`: Workflow name
- `on`: Trigger (push, pull_request, schedule, etc.)

### Issue 4: "docs/SPEC.md not found"

**Symptom:** Pre-push hook blocks because SPEC.md is missing

**Error Message:**
```
❌ docs/SPEC.md not found
```

**Diagnosis:**
```bash
# Check if SPEC.md exists
ls -la docs/SPEC.md

# Check if it has required fields
grep "^version:" docs/SPEC.md
```

**Fix:**
```bash
# If file is missing, create it
# Copy from template or existing repo

# If file exists but not staged
git add docs/SPEC.md
git commit -m "docs: add SPEC.md"
git push
```

### Issue 5: "docs/AGENTS.md not found"

**Symptom:** Pre-push hook blocks because AGENTS.md is missing

**Error Message:**
```
❌ docs/AGENTS.md not found
```

**Fix:**
```bash
# If file is missing, create it
# Copy from template or existing repo

# If file exists but not staged
git add docs/AGENTS.md
git commit -m "docs: add AGENTS.md"
git push
```

### Issue 6: "README.md not found"

**Symptom:** Pre-push hook blocks because README.md is missing

**Error Message:**
```
❌ README.md not found
```

**Fix:**
```bash
# If file is missing, create it
# Copy from template or existing repo

# If file exists but not staged
git add README.md
git commit -m "docs: add README.md"
git push
```

### Issue 7: "Invalid YAML in DELEGATE"

**Symptom:** Pre-push hook blocks with DELEGATE validation error

**Error Message:**
```
❌ Invalid YAML in DELEGATE: artifacts/delegates/2026-05-16/DELEGATE-task-engineer.yaml
❌ Missing required field 'role' in DELEGATE: artifacts/delegates/2026-05-16/DELEGATE-task-engineer.yaml
```

**Diagnosis:**
```bash
# Check DELEGATE file
cat artifacts/delegates/2026-05-16/DELEGATE-task-engineer.yaml

# Validate YAML
python3 -c "import yaml; yaml.safe_load(open('artifacts/delegates/2026-05-16/DELEGATE-task-engineer.yaml'))"
```

**Fix:**
```bash
# Ensure all required fields are present:
# - handoff_type: DELEGATE
# - task_id: YYYY-MM-DD-kebab-case
# - role: Valid role
# - model: Valid model
# - scope: Clear description
# - plan: Numbered steps
# - success_criteria: Testable criteria

# Fix issues and re-push
git add artifacts/delegates/
git commit -m "fix: correct DELEGATE structure"
git push
```

### Issue 8: "Invalid YAML in HANDBACK"

**Symptom:** Pre-push hook blocks with HANDBACK validation error

**Error Message:**
```
❌ Invalid YAML in HANDBACK: artifacts/queue/processing/HANDBACK-task.yaml
❌ Missing required field 'status' in HANDBACK: artifacts/queue/processing/HANDBACK-task.yaml
```

**Fix:**
```bash
# Ensure all required fields are present:
# - handoff_type: HANDBACK
# - task_id: YYYY-MM-DD-kebab-case
# - status: complete|failed|partial|blocked
# - deliverables: List of changes
# - tests: Test results
# - quality_score: 0-100

# Fix issues and re-push
git add artifacts/queue/processing/
git commit -m "fix: correct HANDBACK structure"
git push
```

### Issue 9: "Some tests failed"

**Symptom:** Pre-push hook warns about test failures

**Warning Message:**
```
⚠️  Some tests failed — review before pushing to shared branches
```

**Note:** This is a warning only — push proceeds.

**Diagnosis:**
```bash
# Run tests locally
pytest tests/ -v

# See which tests failed
pytest tests/ -v --tb=short
```

**Fix:**
```bash
# 1. Fix failing tests
# ... make code changes ...

# 2. Re-run tests
pytest tests/ -v

# 3. Commit fixes
git add tests/
git commit -m "fix: address test failures"

# 4. Re-push
git push
```

### Issue 10: "External scripts found in orchestration/scripts/"

**Symptom:** Pre-push hook blocks with SPEC violation

**Error Message:**
```
❌ External scripts found in orchestration/scripts/ — violates SPEC.md
```

**Fix:**
```bash
# 1. Remove external scripts
rm -rf orchestration/scripts/

# 2. Move functionality into agent code
# Convert script to agent SKILL or DELEGATE

# 3. Commit and push
git add -A
git commit -m "fix: move scripts to agent code per SPEC.md"
git push
```

---

## Bypass Procedures

### When to Use Bypass

**Use bypass ONLY in genuine emergencies:**
- ✅ Production outage requiring immediate hotfix
- ✅ Critical security vulnerability requiring immediate patch
- ✅ CI/CD failure blocking team (temporary)
- ✅ Temporary workaround pending upstream fix

**Never use bypass for:**
- ❌ "Just this once" commits that violate SPEC
- ❌ Avoiding code review
- ❌ Skipping tests
- ❌ Committing secrets
- ❌ Lazy commits

### Bypass Method 1: BYPASS_HOOK_VALIDATION

```bash
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: reason"
```

**What it skips:**
- SPEC.md compliance checks
- Secret detection
- YAML/JSON validity
- Code style checks

**What it DOES NOT skip:**
- `commit-msg` hook (message format still validated)

**Use when:** You need to commit a temporary workaround that violates SPEC

**Example:**
```bash
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: temporary cron job for production data sync

This is a temporary workaround for production data sync.
Will be replaced with agent-based solution in follow-up task.

Task: 2026-05-16-production-data-sync-workaround"
```

**Post-bypass checklist:**
- [ ] Documented reason in commit message
- [ ] Created follow-up task to fix root cause
- [ ] Verified no real secrets were committed
- [ ] Re-enabled hooks: `git config core.hooksPath .githooks`

### Bypass Method 2: SKIP_COMMIT_MSG_HOOK

```bash
SKIP_COMMIT_MSG_HOOK=true git commit -m "emergency fix"
```

**What it skips:**
- Message length validation
- Conventional commit format
- DELEGATE/HANDBACK validation
- SKIP_HOOKS documentation

**Use when:** You need to commit with a minimal message in emergency

**Example:**
```bash
SKIP_COMMIT_MSG_HOOK=true git commit -m "hotfix"
```

### Bypass Method 3: SKIP_HOOKS (Pre-Push)

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

**Use when:** You need to push a commit that failed pre-push validation

**Example:**
```bash
SKIP_HOOKS=1 git push origin hotfix-branch
```

### Bypass Method 4: --no-verify (STRONGLY DISCOURAGED)

```bash
git commit --no-verify -m "message"
```

**What it skips:** ALL hooks (pre-commit, commit-msg, pre-push)

**⚠️ WARNING:** This is the nuclear option. Use ONLY if all other bypasses fail and you have explicit authorization.

**Why it's discouraged:**
- Breaks audit trail
- Violates SPEC.md
- Prevents quality gate validation
- Can introduce secrets

### Required Documentation for Bypass

**Every bypass MUST be documented:**

```bash
# Example bypass with documentation
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: production database fix

SKIP_HOOKS: database connection pool exhausted
reason: immediate fix required to restore service
approved_by: lead-engineer-name
ticket: PROD-12345
duration: temporary (max 24 hours)

This is a temporary workaround. Root cause fix is scheduled for
follow-up task: 2026-05-16-database-pool-fix

Changes:
- Increased connection pool size from 10 to 50
- Added connection timeout of 30 seconds
- Logs connection pool status on startup

Testing:
- Verified service recovery
- Monitored for 1 hour post-deployment
- No new errors in logs"
```

### Post-Bypass Checklist

After using a bypass, immediately:

1. **Create a follow-up task:**
   ```bash
   echo "- [ ] Fix root cause of bypass: $(git log -1 --format=%s)" >> TODO.md
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

## Environment Variables

### Pre-Commit Hook

| Variable | Values | Effect |
|----------|--------|--------|
| `SKIP_HOOKS` | `1` | Bypass all pre-commit checks |
| `BYPASS_HOOK_VALIDATION` | `true` | Bypass SPEC/secret checks only |

### Commit-Msg Hook

| Variable | Values | Effect |
|----------|--------|--------|
| `SKIP_COMMIT_MSG_HOOK` | `true` | Bypass message format validation |

### Pre-Push Hook

| Variable | Values | Effect |
|----------|--------|--------|
| `SKIP_HOOKS` | `1` | Bypass all pre-push checks |

---

## FAQ

**Q: Can I disable hooks permanently?**  
A: Not recommended. Hooks enforce SPEC.md and prevent secrets. If needed, use bypass procedures with documentation.

**Q: What if I commit a secret by accident?**  
A: Immediately rotate the secret and remove from git history:
```bash
git filter-branch --tree-filter 'rm -f {file}'
git push --force-with-lease
```

**Q: Can I modify the hooks?**  
A: Changes require PR with justification and Lead Engineer approval.

**Q: What if a hook has a bug?**  
A: Report it immediately with reproduction steps. Use bypass with documentation while it's being fixed.

**Q: How do I test hook changes?**  
A: Use a test branch:
```bash
git checkout -b test-hook-changes
# Make changes and test
git commit -m "test: hook changes"
# If working, merge to main
```

---

## Update Log

- **2026-05-16:** Initial comprehensive troubleshooting guide with 30+ scenarios, bypass procedures, and environment variables.
