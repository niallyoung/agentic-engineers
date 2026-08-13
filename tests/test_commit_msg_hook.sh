#!/usr/bin/env bash
# tests/test_commit_msg_hook.sh — Comprehensive tests for .githooks/commit-msg
#
# Tests all validation rules:
#   1. Message length validation
#   2. Format validation
#   3. Task ID tracking
#   4. DELEGATE/HANDBACK validation
#   5. SKIP_HOOKS bypass documentation
#   6. Secret detection
#
# Run: bash tests/test_commit_msg_hook.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Temporary test directory
TEST_DIR=$(mktemp -d)
trap "rm -rf $TEST_DIR" EXIT

# Hook path
HOOK_PATH="./.githooks/commit-msg"

# Test helper functions
test_case() {
  local name=$1
  local expected_exit=$2
  local message=$3
  
  ((TESTS_RUN++))
  
  # Create temporary commit message file
  local msg_file="$TEST_DIR/commit_msg_$$"
  echo -n "$message" > "$msg_file"
  
  # Run hook
  local exit_code=0
  bash "$HOOK_PATH" "$msg_file" > "$TEST_DIR/output_$$" 2>&1 || exit_code=$?
  
  # Check result
  if [ "$exit_code" -eq "$expected_exit" ]; then
    echo -e "${GREEN}✓${NC} $name"
    ((TESTS_PASSED++))
    return 0
  else
    echo -e "${RED}✗${NC} $name (expected exit $expected_exit, got $exit_code)"
    echo "   Message: $message"
    echo "   Output:"
    sed 's/^/     /' "$TEST_DIR/output_$$"
    ((TESTS_FAILED++))
    return 1
  fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Testing .githooks/commit-msg"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ────────────────────────────────────────────────────────────────────────────────
# 1. EMPTY MESSAGE TESTS
# ────────────────────────────────────────────────────────────────────────────────

echo -e "${BLUE}1. Empty Message Tests${NC}"
test_case "Empty message should fail" 1 ""
test_case "Only comments should fail" 1 "# This is a comment"
test_case "Only whitespace should fail" 1 "   "
echo ""

# ────────────────────────────────────────────────────────────────────────────────
# 2. MESSAGE LENGTH TESTS
# ────────────────────────────────────────────────────────────────────────────────

echo -e "${BLUE}2. Message Length Tests${NC}"
test_case "Too short (5 chars)" 1 "short"
test_case "Minimum length (10 chars)" 0 "1234567890"
test_case "Good length (20 chars)" 0 "This is a good message"
test_case "Maximum length (72 chars)" 0 "This is exactly seventy two characters long for a commit message"
test_case "Too long (73+ chars)" 1 "This is a commit message that exceeds the recommended seventy two character limit"
echo ""

# ────────────────────────────────────────────────────────────────────────────────
# 3. CONVENTIONAL COMMIT FORMAT TESTS
# ────────────────────────────────────────────────────────────────────────────────

echo -e "${BLUE}3. Conventional Commit Format Tests${NC}"
test_case "Valid: feat with scope" 0 "feat(auth): add token grace period"
test_case "Valid: fix without scope" 0 "fix: resolve clock skew in mobile"
test_case "Valid: docs" 0 "docs: update SPEC.md with new rules"
test_case "Valid: refactor" 0 "refactor: consolidate hook validation"
test_case "Valid: test" 0 "test: add commit message hook tests"
test_case "Valid: chore" 0 "chore: update dependencies"
test_case "Invalid type" 0 "invalid: this should warn but pass"
test_case "No colon" 0 "feat auth add token grace period"
echo ""

# ────────────────────────────────────────────────────────────────────────────────
# 4. TASK ID TRACKING TESTS
# ────────────────────────────────────────────────────────────────────────────────

echo -e "${BLUE}4. Task ID Tracking Tests${NC}"
test_case "Valid task ID in subject" 0 "feat: 2026-05-16-hooks-commitmsg-implementation"
test_case "Valid task ID in body" 0 "feat: add commit message validation

Task: 2026-05-16-hooks-commitmsg-implementation
Implements comprehensive message format validation"
test_case "Invalid task ID format" 0 "feat: 2026-5-16-invalid-format"
test_case "No task ID" 0 "feat: add some feature without task ID"
echo ""

# ────────────────────────────────────────────────────────────────────────────────
# 5. DELEGATE VALIDATION TESTS
# ────────────────────────────────────────────────────────────────────────────────

echo -e "${BLUE}5. DELEGATE Block Validation Tests (Canonical Schema)${NC}"
test_case "Valid DELEGATE block with agent field" 0 "feat: DELEGATE implementation

---
handoff_type: DELEGATE
task_id: 2026-05-16-hooks-commitmsg-implementation
agent: engineer
scope: Implement commit-msg hook for canonical schema validation
plan:
  1. Create hook script
  2. Add validation rules
success_criteria:
  - Hook validates messages
  - Tests pass
---"

test_case "DELEGATE missing agent field (should fail)" 1 "feat: DELEGATE implementation

---
handoff_type: DELEGATE
task_id: 2026-05-16-test
scope: Implement commit-msg hook
plan:
  1. Create hook script
success_criteria:
  - Hook validates messages
---"

test_case "DELEGATE with deprecated role field (warns but passes)" 0 "feat: DELEGATE with deprecated role

---
handoff_type: DELEGATE
task_id: 2026-05-16-test
agent: engineer
role: engineer
scope: Test implementation with forward-compat
plan:
  1. Create script
success_criteria:
  - Tests pass
---"

test_case "DELEGATE with canonical fields" 0 "feat: DELEGATE with all fields

---
handoff_type: DELEGATE
task_id: 2026-05-16-test
agent: engineer
scope: Test implementation with complete fields here
plan:
  1. Create script
success_criteria:
  - Tests pass
---"
echo ""

# ────────────────────────────────────────────────────────────────────────────────
# 6. HANDBACK VALIDATION TESTS
# ────────────────────────────────────────────────────────────────────────────────

echo -e "${BLUE}6. HANDBACK Block Validation Tests (Canonical Schema)${NC}"
test_case "Valid HANDBACK block with output and metrics" 0 "feat: HANDBACK completion

---
handoff_type: HANDBACK
task_id: 2026-05-16-hooks-commitmsg-implementation
agent: engineer
status: success
output: Implementation complete, all tests pass
metrics:
  quality: 0.95
  tokens: 1500
  cost: 0.05
  duration_seconds: 120
---"

test_case "HANDBACK missing output (should fail)" 1 "feat: HANDBACK incomplete

---
handoff_type: HANDBACK
task_id: 2026-05-16-test
agent: engineer
status: success
metrics:
  quality: 0.95
  tokens: 1500
  cost: 0.05
  duration_seconds: 120
---"

test_case "HANDBACK invalid status value (should fail)" 1 "feat: HANDBACK with invalid status

---
handoff_type: HANDBACK
task_id: 2026-05-16-test
agent: engineer
status: invalid_status
output: Some work done
metrics:
  quality: 0.95
  tokens: 1500
  cost: 0.05
  duration_seconds: 120
---"

test_case "HANDBACK with canonical status: success" 0 "feat: HANDBACK success

---
handoff_type: HANDBACK
task_id: 2026-05-16-test
agent: engineer
status: success
output: Work completed successfully
metrics:
  quality: 0.95
  tokens: 1500
  cost: 0.05
  duration_seconds: 120
---"

test_case "HANDBACK with canonical status: failure" 0 "feat: HANDBACK failure

---
handoff_type: HANDBACK
task_id: 2026-05-16-test
agent: engineer
status: failure
output: Work failed
metrics:
  quality: 0.1
  tokens: 500
  cost: 0.01
  duration_seconds: 60
---"

test_case "HANDBACK with canonical status: partial" 0 "feat: HANDBACK partial

---
handoff_type: HANDBACK
task_id: 2026-05-16-test
agent: engineer
status: partial
output: Work partially complete
metrics:
  quality: 0.5
  tokens: 1000
  cost: 0.03
  duration_seconds: 90
---"

test_case "HANDBACK with canonical status: blocked" 0 "feat: HANDBACK blocked

---
handoff_type: HANDBACK
task_id: 2026-05-16-test
agent: engineer
status: blocked
output: Work blocked on dependency
metrics:
  quality: 0.0
  tokens: 500
  cost: 0.01
  duration_seconds: 30
---"

test_case "HANDBACK with canonical status: escalate" 0 "feat: HANDBACK escalate

---
handoff_type: HANDBACK
task_id: 2026-05-16-test
agent: engineer
status: escalate
output: Work escalated to senior engineer
metrics:
  quality: 0.0
  tokens: 800
  cost: 0.02
  duration_seconds: 45
---"

test_case "HANDBACK with deprecated fields (forward-compat)" 0 "feat: HANDBACK deprecated fields

---
handoff_type: HANDBACK
task_id: 2026-05-16-test
agent: engineer
status: success
output: Work done
deliverables:
  - file.txt
tests:
  - test passes
quality_score: 0.95
metrics:
  quality: 0.95
  tokens: 1500
  cost: 0.05
  duration_seconds: 120
---"
echo ""

# ────────────────────────────────────────────────────────────────────────────────
# 7. SKIP_HOOKS BYPASS DOCUMENTATION TESTS
# ────────────────────────────────────────────────────────────────────────────────

echo -e "${BLUE}7. SKIP_HOOKS Bypass Documentation Tests${NC}"
test_case "SKIP_HOOKS with reason" 0 "feat: emergency fix with SKIP_HOOKS

SKIP_HOOKS: Production emergency - critical security fix"

test_case "SKIP_HOOKS with documented reason" 0 "feat: bypass validation

reason: Emergency fix required for production outage
SKIP_HOOKS: documented"

test_case "SKIP_HOOKS without reason" 1 "feat: bypass validation

SKIP_HOOKS mentioned but no reason"

test_case "SKIP_HOOKS with justification" 0 "feat: emergency deployment

SKIP_HOOKS: Critical security patch requires immediate deployment"
echo ""

# ────────────────────────────────────────────────────────────────────────────────
# 8. SECRET DETECTION TESTS
# ────────────────────────────────────────────────────────────────────────────────

echo -e "${BLUE}8. Secret Detection Tests${NC}"
test_case "Message with password keyword" 1 "feat: add authentication

password: secret123"

test_case "Message with api_key keyword" 1 "feat: add API integration

api_key: sk-1234567890"

test_case "Message with token keyword" 1 "feat: add token validation

token: ghp_1234567890"

test_case "Message with private_key keyword" 1 "feat: add encryption

private_key: -----BEGIN PRIVATE KEY-----"  # pragma: allowlist secret

test_case "Message with aws_secret keyword" 1 "feat: add AWS integration

aws_secret: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

test_case "Normal message without secrets" 0 "feat: add secure authentication

Implements token validation with grace period"
echo ""

# ────────────────────────────────────────────────────────────────────────────────
# 9. MULTILINE MESSAGE TESTS
# ────────────────────────────────────────────────────────────────────────────────

echo -e "${BLUE}9. Multiline Message Tests${NC}"
test_case "Valid multiline with body" 0 "feat: implement message validation

This commit adds comprehensive validation to the commit-msg hook.

Features:
- Message length validation
- Format validation
- Task ID tracking
- Protocol validation
- Secret detection

Tests:
- All validation rules tested
- Edge cases covered"

test_case "Valid multiline with task ID in body" 0 "feat: add validation

Task: 2026-05-16-hooks-commitmsg-implementation

Implements comprehensive message format validation with
multiple validation rules and detailed error reporting."

test_case "Multiline with comments" 0 "feat: add feature

This is the body.
# This is a comment and should be ignored
More body content."
echo ""

# ────────────────────────────────────────────────────────────────────────────────
# 10. EDGE CASES
# ────────────────────────────────────────────────────────────────────────────────

echo -e "${BLUE}10. Edge Cases${NC}"
test_case "Message with special characters" 0 "feat: add support for special chars: @#$%^&*()"
test_case "Message with emoji" 0 "feat: add feature 🎉"
test_case "Message with numbers" 0 "feat: fix issue #123 and #456"
test_case "Message with URLs" 0 "feat: update docs at https://example.com"
test_case "Message with code snippets" 0 "feat: add function foo() to validate()"
echo ""

# ────────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ────────────────────────────────────────────────────────────────────────────────

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Tests run:    $TESTS_RUN"
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
if [ "$TESTS_FAILED" -gt 0 ]; then
  echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
else
  echo -e "Tests failed: ${GREEN}0${NC}"
fi
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
  echo -e "${GREEN}✅ All tests passed!${NC}"
  exit 0
else
  echo -e "${RED}❌ Some tests failed${NC}"
  exit 1
fi
