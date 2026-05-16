# .githooks/commit-msg — Commit Message Validation Hook

## Overview

The `commit-msg` hook enforces comprehensive commit message standards across the agentic-engineers framework. It validates message format, length, task ID tracking, DELEGATE/HANDBACK protocol compliance, and detects potential secrets.

**Status:** ✅ Implemented and tested (49 test cases)

## Installation

The hook is automatically installed when you run:

```bash
git config core.hooksPath .githooks
```

Or during `make install`:

```bash
make install
```

## Validation Rules

### 1. Non-Empty Message

**Rule:** Commit message must not be empty.

**Examples:**
- ❌ Empty message
- ❌ Only comments (lines starting with `#`)
- ❌ Only whitespace
- ✅ Any meaningful message

### 2. Message Length

**Rule:** Subject line (first line) must be:
- **Minimum:** 10 characters
- **Maximum:** 72 characters (recommended)

**Examples:**
- ❌ `fix bug` (7 chars)
- ✅ `fix: resolve clock skew` (23 chars)
- ❌ `This is a very long commit message that exceeds the recommended seventy two character limit` (95 chars)

### 3. Conventional Commit Format (Encouraged)

**Rule:** Commit messages should follow conventional commit format (optional but encouraged):

```
type(scope): subject
```

**Valid Types:**
- `feat` — New feature
- `fix` — Bug fix
- `docs` — Documentation
- `style` — Code style (formatting, missing semicolons, etc.)
- `refactor` — Code refactoring
- `perf` — Performance improvement
- `test` — Test additions or fixes
- `chore` — Build, dependencies, tooling
- `ci` — CI/CD configuration
- `build` — Build system changes
- `revert` — Revert a previous commit

**Examples:**
- ✅ `feat(auth): add token grace period validation`
- ✅ `fix: resolve clock skew in mobile devices`
- ✅ `docs: update SPEC.md with new routing rules`
- ⚠️ `add feature without conventional format` (warning, but allowed)

### 4. Task ID Tracking (Optional)

**Rule:** Commit messages should include a task ID in the format `YYYY-MM-DD-kebab-case`.

**Examples:**
- ✅ `feat: 2026-05-16-hooks-commitmsg-implementation`
- ✅ `feat: add feature

Task: 2026-05-16-hooks-commitmsg-implementation`
- ⚠️ `feat: add feature without task ID` (warning, but allowed)

### 5. DELEGATE Block Validation

**Rule:** If a commit message contains a `DELEGATE` block, it must have all required fields:
- `task_id` (format: `YYYY-MM-DD-kebab-case`)
- `role` (valid agent role)
- `scope` (task description)
- `plan` (numbered steps)
- `success_criteria` (testable criteria)

**Example:**
```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-16-hooks-commitmsg-implementation
role: engineer
scope: Implement commit-msg hook for message format validation
plan:
  1. Create hook script
  2. Add validation rules
  3. Create tests
success_criteria:
  - Hook validates messages
  - All tests pass
  - Documentation complete
---
```

### 6. HANDBACK Block Validation

**Rule:** If a commit message contains a `HANDBACK` block, it must have all required fields:
- `task_id` (format: `YYYY-MM-DD-kebab-case`)
- `status` (one of: `complete`, `failed`, `partial`, `blocked`)
- `deliverables` (list of what was delivered)
- `tests` (test results)
- `quality_score` (0-100)

**Valid Status Values:**
- `complete` — Task fully completed
- `failed` — Task failed
- `partial` — Task partially completed
- `blocked` — Task blocked, awaiting input

**Example:**
```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-16-hooks-commitmsg-implementation
status: complete
deliverables:
  - .githooks/commit-msg
  - tests/test_commit_msg_hook.sh
  - docs/COMMIT_MSG_HOOK.md
tests:
  - All 49 validation tests pass
  - Hook validates messages correctly
quality_score: 95
---
```

### 7. SKIP_HOOKS Bypass Documentation

**Rule:** If a commit message mentions `SKIP_HOOKS`, it must include documented reason.

**Valid Formats:**
- ✅ `SKIP_HOOKS: Production emergency - critical security fix`
- ✅ `reason: Emergency fix required for production outage`
- ✅ `emergency: Critical security patch requires immediate deployment`
- ❌ `SKIP_HOOKS mentioned but no reason documented`

### 8. Secret Detection

**Rule:** Commit messages must not contain secrets in the form of key-value pairs.

**Detected Patterns:**
- `password: <secret>`
- `api_key: <secret>`
- `secret: <secret>`
- `token: <secret>`
- `private_key: <secret>`
- `aws_secret: <secret>`
- `github_token: <secret>`

**Examples:**
- ❌ `feat: add auth

password: secret123`
- ❌ `feat: add API integration

api_key: sk-1234567890`
- ✅ `feat: add token validation

Implements token validation with grace period`

## Bypass

To bypass the commit-msg hook validation (not recommended):

```bash
SKIP_COMMIT_MSG_HOOK=true git commit -m "your message"
```

**Note:** This should only be used in genuine emergencies. Document the reason in the commit message.

## Testing

Run the comprehensive test suite:

```bash
bash tests/test_commit_msg_hook.sh
```

**Test Coverage:**
- 10 test categories
- 49 test cases
- All validation rules covered
- Edge cases included

**Test Results:**
```
Tests run:    49
Tests passed: 49
Tests failed: 0
✅ All tests passed!
```

## Examples

### Good Commit Message

```
feat(auth): add token grace period validation

Implements 30-second grace period for token expiry validation
to account for clock skew on mobile devices.

Task: 2026-05-16-hooks-commitmsg-implementation

Changes:
- Add GRACE_PERIOD_SECS constant
- Update token validation logic
- Add comprehensive tests

Fixes: #123
```

### DELEGATE Example

```
feat: DELEGATE implementation

---
handoff_type: DELEGATE
task_id: 2026-05-16-hooks-commitmsg-implementation
role: engineer
effort: high
scope: Implement commit-msg hook with comprehensive validation
context:
  - File: .githooks/commit-msg
  - Requirement: Validate message format, length, task IDs, DELEGATE/HANDBACK blocks
plan:
  1. Create hook script with validation rules
  2. Implement message length checks (10-72 chars)
  3. Add conventional commit format validation
  4. Add task ID tracking (YYYY-MM-DD-kebab-case)
  5. Add DELEGATE/HANDBACK block validation
  6. Add secret detection
  7. Create comprehensive test suite (49 tests)
  8. Document all validation rules
success_criteria:
  - Hook validates all message types
  - All 49 tests pass
  - Documentation complete
  - No false positives on valid messages
---
```

### HANDBACK Example

```
feat: HANDBACK completion

---
handoff_type: HANDBACK
task_id: 2026-05-16-hooks-commitmsg-implementation
status: complete
deliverables:
  - .githooks/commit-msg (254 lines, comprehensive validation)
  - tests/test_commit_msg_hook.sh (49 test cases)
  - docs/COMMIT_MSG_HOOK.md (this file)
tests:
  - Empty message validation: PASS
  - Message length validation: PASS
  - Conventional commit format: PASS
  - Task ID tracking: PASS
  - DELEGATE block validation: PASS
  - HANDBACK block validation: PASS
  - SKIP_HOOKS bypass documentation: PASS
  - Secret detection: PASS
  - Multiline messages: PASS
  - Edge cases: PASS
  - Total: 49/49 tests passing
quality_score: 95
tokens_used: 1200
tokens_estimated: 1500
efficiency: 0.80
confidence: 0.95
notes: "Straightforward implementation with comprehensive validation rules. All edge cases covered. High confidence in solution."
---
```

## Hook Output

### Successful Validation

```
✓ Commit message does not follow conventional commit format
✓ Task ID detected: 2026-05-16-hooks-commitmsg-implementation
✓ DELEGATE block has all required fields
✓ DELEGATE task_id format is valid

─────────────────────────────────────────────────────────────────────────────
✅ commit-msg: validation passed
   Subject: feat: implement commit message validation
   Body: 5 line(s)
```

### Validation Failure

```
✗ Commit message is empty

─────────────────────────────────────────────────────────────────────────────
❌ commit-msg: 1 error(s) found

Fix the errors above and retry:
  git commit --amend

To bypass validation (not recommended):
  SKIP_COMMIT_MSG_HOOK=true git commit
```

## Integration with Git Workflow

The hook runs automatically when you commit:

```bash
# Hook runs automatically
git commit -m "feat: add feature"

# If validation fails, amend and retry
git commit --amend

# If you need to bypass (emergency only)
SKIP_COMMIT_MSG_HOOK=true git commit -m "emergency fix"
```

## Troubleshooting

### "Commit message too short"

**Problem:** Your commit message is less than 10 characters.

**Solution:** Provide a more descriptive message:
```bash
git commit --amend -m "feat: add feature description"
```

### "Does not follow conventional commit format"

**Problem:** Your message doesn't follow the `type(scope): subject` format.

**Solution:** Use conventional commit format:
```bash
git commit --amend -m "feat(scope): description"
```

### "No task ID found"

**Problem:** Your message doesn't include a task ID.

**Solution:** Add task ID to your message:
```bash
git commit --amend -m "feat: 2026-05-16-task-name"
```

### "DELEGATE block missing required fields"

**Problem:** Your DELEGATE block is incomplete.

**Solution:** Ensure all required fields are present:
- `task_id`
- `role`
- `scope`
- `plan`
- `success_criteria`

### "Commit message contains potential secrets"

**Problem:** The hook detected a potential secret.

**Solution:** Remove the secret and use environment variables instead:
```bash
# ❌ Don't do this
git commit -m "feat: add API integration

api_key: sk-1234567890"

# ✅ Do this instead
git commit -m "feat: add API integration

Uses API key from environment variable"
```

## Configuration

The hook is configured in `.git/config`:

```bash
[core]
    hooksPath = .githooks
```

This is set automatically by `make install`.

## Related Files

- `.githooks/pre-commit` — Pre-commit validation (SPEC compliance, secrets, YAML validity)
- `.githooks/pre-push` — Pre-push validation (agent YAML validation, test suite)
- `docs/SDLC-HOOKS.md` — Comprehensive hook reference with cross-harness matrix
- `tests/test_commit_msg_hook.sh` — Test suite (49 test cases)

## Specification

See `docs/SPEC.md` for the full agentic-engineers specification, including:
- DELEGATE/HANDBACK protocol details
- Agent roles and responsibilities
- Queue-based routing
- Metrics and observability

## Version History

- **2026-05-16** — Initial implementation with comprehensive validation rules and 49 test cases
  - Message length validation (10-72 chars)
  - Conventional commit format (encouraged)
  - Task ID tracking (YYYY-MM-DD-kebab-case)
  - DELEGATE/HANDBACK block validation
  - SKIP_HOOKS bypass documentation
  - Secret detection
  - Comprehensive test suite
  - Full documentation
