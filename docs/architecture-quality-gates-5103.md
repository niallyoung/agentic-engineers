# Architecture: Quality Gate Integration — Block Commits on Quality Failures
**Task 5103** | Lead Engineer Design | High Effort

---

## Executive Summary

The current agentic-engineers system has a Quality Engineer role defined in `AGENTS.md` and a quality checklist in `orchestration/QUALITY.md`, but **no mechanism exists to automatically block commits based on quality results**. The existing `.githooks/pre-commit` hook only enforces SPEC structural constraints (no scripts in `orchestration/scripts/`), not code quality.

This document designs a **Quality Gate Integration** that:

1. **Intercepts commits** via an enhanced git pre-commit hook
2. **Queues Quality tasks** into the existing DELEGATE/HANDBACK queue system
3. **Waits for Quality Engineer evaluation** within a configurable timeout
4. **Evaluates HANDBACK results** to allow or block the commit
5. **Fails safely** — infrastructure problems warn but never block developers

The design strictly respects the SPEC constraint: all runtime agent operations flow through the Orchestrator queue. The pre-commit hook is classified as a **build/setup-time operation** (same exemption category as `make install`, `renderer/scripts/`).

---

## Design Goals

| Goal | Rationale |
|------|-----------|
| **Commit Blocking** | Prevent regressions from reaching the repo |
| **Queue-First** | All agent invocations via DELEGATE/HANDBACK, never direct invocation |
| **Fast Feedback** | Tier 1 checks (lint, type-check) complete in <30s; developer sees results immediately |
| **Safe Failure** | Infrastructure outage → warn, never block. Only quality failures block. |
| **Meaningful Errors** | Developer sees exactly which check failed and why |
| **Bypassable** | `--no-verify` escapes for emergencies (logged) |
| **Testable** | Quality gate logic is testable without running a full LLM agent |
| **SPEC-Compliant** | No runtime external scripts; hook is build/setup-time exemption |

---

## Current State

### What Exists Today

| Component | Status | Location |
|-----------|--------|----------|
| Quality Engineer role definition | ✅ | `AGENTS.md`, `skills/quality-engineer-agent.md` |
| Quality checklist (manual) | ✅ | `orchestration/QUALITY.md` |
| DELEGATE/HANDBACK queue | ✅ | `artifacts/queue/incoming/processing/done/` |
| Pre-commit hook (structural only) | ✅ | `.githooks/pre-commit` |
| Quality gate aggregator (design) | 📄 | `skills/quality-gate-aggregator.md` |
| Quality gate orchestration (design) | 📄 | `skills/quality-gate-orchestration.md` |
| CI/CD quality integration | ❌ | Missing |
| Commit-blocking HANDBACK evaluation | ❌ | Missing |
| Quality check runners (lint/test/etc) | ❌ | Missing |

### The Gap

The Principal Engineer audit identified: *"Quality integration: framework defined; no pre-commit hooks or CI/CD integration to block commits."*

Concretely: a developer can `git commit` code that fails all quality checks. The Quality Engineer agent exists but is never invoked automatically at commit time.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        git commit                                   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  .githooks/pre-commit (shell)                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  1. Collect staged file metadata (paths, types)             │   │
│  │  2. Determine quality check tier (Tier 1 / Tier 2)         │   │
│  │  3. Write quality-gate DELEGATE to queue/incoming/         │   │
│  │  4. Poll queue/done/ for HANDBACK (timeout: 90s)           │   │
│  │  5. Evaluate HANDBACK → PASS/FAIL/WARN                     │   │
│  │  6. exit 0 (allow) | exit 1 (block) | exit 0+warn (infra) │   │
│  └─────────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ writes DELEGATE
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│              artifacts/queue/incoming/{task-id}.yaml               │
│              (Quality Gate DELEGATE block)                         │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ Orchestrator polls
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Orchestrator Agent                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Routes quality-gate task → Quality Engineer (Sonnet)       │   │
│  │  Creates sub-DELEGATE with staged files context             │   │
│  └─────────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ delegates
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Quality Engineer Agent                           │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Tier 1: lint, type-check, secret detection               │    │
│  │  Tier 2: tests for changed modules, coverage delta        │    │
│  │  Evaluates against quality thresholds                     │    │
│  │  Returns HANDBACK: assessment: PASS | FAIL                │    │
│  └────────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HANDBACK written to done/
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│         artifacts/queue/done/{task-id}-HANDBACK-Quality.yaml       │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ pre-commit hook polls (every 3s)
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│               HANDBACK Evaluation in pre-commit hook               │
│  assessment: PASS  →  exit 0  (commit proceeds)                    │
│  assessment: FAIL  →  exit 1  (commit blocked + error details)     │
│  timeout/error    →  exit 0  (warn only, commit proceeds)          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component 1: Enhanced Pre-Commit Hook

### Location and Activation

The hook lives at `.githooks/pre-commit` (already tracked in repo). Developers activate via:

```bash
make install   # already runs: git config core.hooksPath .githooks
```

The Makefile `verify` target should assert `core.hooksPath` is set correctly.

### Hook Script Design

```bash
#!/bin/bash
# .githooks/pre-commit
# Quality Gate Integration — blocks commits on quality failures
# SPEC-EXEMPTION: Pre-commit hooks are build/setup-time operations (see docs/SPEC.md)

set -euo pipefail

# ─── Configuration ────────────────────────────────────────────────────────────
REPO_ROOT="$(git rev-parse --show-toplevel)"
QUEUE_IN="${REPO_ROOT}/artifacts/queue/incoming"
QUEUE_DONE="${REPO_ROOT}/artifacts/queue/done"
QG_TIMEOUT="${QG_TIMEOUT:-90}"          # seconds to wait for Quality Agent
QG_POLL_INTERVAL=3                      # seconds between polls
QG_ENABLED="${QG_ENABLED:-true}"        # set to "false" to disable (with warning)
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
COMMIT_HASH="$(git diff --cached --name-only | md5sum | cut -c1-8)"
TASK_ID="quality-gate-precommit-${COMMIT_HASH}-${TIMESTAMP}"

# ─── Section 1: Existing SPEC Constraint Checks (unchanged) ──────────────────
if find orchestration/scripts -type f \( -name "*.py" -o -name "*.sh" \) \
    2>/dev/null | grep -q . ; then
  echo "❌ SPEC VIOLATION: External scripts in orchestration/scripts/"
  echo "   All work must flow through DELEGATE/HANDBACK protocol"
  echo "   See docs/SPEC.md for details"
  exit 1
fi

if find orchestration/config -name "*.cron" -type f 2>/dev/null | grep -q . ; then
  echo "❌ SPEC VIOLATION: Cron files in orchestration/config/"
  echo "   Use queue-based delegation instead"
  exit 1
fi

# ─── Section 2: Quality Gate ──────────────────────────────────────────────────
if [ "${QG_ENABLED}" != "true" ]; then
  echo "⚠️  Quality Gate disabled (QG_ENABLED=${QG_ENABLED})"
  echo "   Commit proceeds — run quality checks manually: make verify"
  exit 0
fi

# Collect staged files
STAGED_FILES="$(git diff --cached --name-only --diff-filter=ACM)"
if [ -z "${STAGED_FILES}" ]; then
  # No tracked files staged — allow commit (e.g., git notes, submodule bumps)
  exit 0
fi

STAGED_COUNT="$(echo "${STAGED_FILES}" | wc -l | tr -d ' ')"
STAGED_TYPES="$(echo "${STAGED_FILES}" | grep -oE '\.[^.]+$' | sort -u | tr '\n' ',' | sed 's/,$//')"

echo "🔍 Quality Gate: evaluating ${STAGED_COUNT} staged file(s)..."
echo "   File types: ${STAGED_TYPES:-mixed}"
echo "   Task ID: ${TASK_ID}"

# ─── Section 3: Write DELEGATE to Queue ──────────────────────────────────────
mkdir -p "${QUEUE_IN}"

cat > "${QUEUE_IN}/${TASK_ID}.yaml" << DELEGATE_EOF
---
handoff_type: DELEGATE
task_id: ${TASK_ID}
timestamp: ${TIMESTAMP}
role: Quality Engineer
model: claude-sonnet-4-6
effort: medium
origin: pre-commit-hook
scope: |
  Quality gate check for pending commit.
  Evaluate staged changes for quality: lint, type-check, tests, coverage.
  Return PASS or FAIL with specific failure details for developer feedback.
context:
  - Staged files (${STAGED_COUNT}): $(echo "${STAGED_FILES}" | head -20 | tr '\n' ',' | sed 's/,$//')
  - File types: ${STAGED_TYPES}
  - Commit timestamp: ${TIMESTAMP}
  - Repo root: ${REPO_ROOT}
plan:
  - 1. Run Tier 1 checks on staged files (lint, type-check, secret detection)
  - 2. Run Tier 2 checks if .py/.ts/.js/.go files staged (tests, coverage delta)
  - 3. Evaluate results against thresholds defined in orchestration/QUALITY.md
  - 4. Return HANDBACK with assessment: PASS or FAIL
  - 5. Include specific failure details in quality_gate_failures field
success_criteria:
  - assessment field set to PASS or FAIL
  - quality_gate_failures list populated if FAIL
  - Each failure includes: check_type, file, message, severity
  - HANDBACK written to done/ within timeout
quality_checks:
  tier: $([ -z "$(echo "${STAGED_FILES}" | grep -E '\.(py|ts|js|go|rb|java)$')" ] && echo "1" || echo "2")
  staged_files:
$(echo "${STAGED_FILES}" | head -20 | sed 's/^/    - /')
DELEGATE_EOF

echo "   ✅ Quality task queued (${QUEUE_IN}/${TASK_ID}.yaml)"

# ─── Section 4: Poll for HANDBACK ─────────────────────────────────────────────
HANDBACK_FILE=""
ELAPSED=0
HANDBACK_PATTERN="${QUEUE_DONE}/${TASK_ID}"

echo "   ⏳ Waiting for Quality Engineer (timeout: ${QG_TIMEOUT}s)..."

while [ "${ELAPSED}" -lt "${QG_TIMEOUT}" ]; do
  # Check for any HANDBACK file matching our task ID
  HANDBACK_FILE="$(find "${QUEUE_DONE}" -name "${TASK_ID}*HANDBACK*" 2>/dev/null | head -1)"
  if [ -n "${HANDBACK_FILE}" ]; then
    break
  fi
  sleep "${QG_POLL_INTERVAL}"
  ELAPSED=$((ELAPSED + QG_POLL_INTERVAL))
done

# ─── Section 5: Evaluate HANDBACK ─────────────────────────────────────────────
if [ -z "${HANDBACK_FILE}" ]; then
  # Timeout — infrastructure issue, warn but allow commit
  echo ""
  echo "⚠️  Quality Gate timeout after ${QG_TIMEOUT}s — commit proceeding with warning"
  echo "   Quality Agent did not respond. Run checks manually: make verify"
  echo "   Task ID: ${TASK_ID} (check queue status later)"
  # Clean up orphaned delegate
  rm -f "${QUEUE_IN}/${TASK_ID}.yaml" 2>/dev/null || true
  exit 0
fi

# Parse HANDBACK YAML — extract assessment field
ASSESSMENT="$(grep '^assessment:' "${HANDBACK_FILE}" | awk '{print $2}' | tr -d '"' | tr '[:lower:]' '[:upper:]')"
QUALITY_SCORE="$(grep '^quality_score:' "${HANDBACK_FILE}" | awk '{print $2}')"

echo "   📋 Quality assessment: ${ASSESSMENT} (score: ${QUALITY_SCORE:-N/A})"

if [ "${ASSESSMENT}" = "PASS" ]; then
  echo "✅ Quality Gate PASSED — commit proceeding"
  exit 0

elif [ "${ASSESSMENT}" = "FAIL" ]; then
  echo ""
  echo "❌ Quality Gate FAILED — commit blocked"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  # Extract and display failures
  python3 -c "
import sys, re
try:
    with open('${HANDBACK_FILE}') as f:
        content = f.read()
    # Find quality_gate_failures section
    in_failures = False
    for line in content.split('\n'):
        if 'quality_gate_failures' in line:
            in_failures = True
            print('Failures:')
        elif in_failures:
            if line.startswith('  - ') or line.startswith('    '):
                print(line)
            elif line and not line.startswith(' '):
                break
except Exception:
    pass
" 2>/dev/null || grep -A 30 "quality_gate_failures" "${HANDBACK_FILE}" | head -35

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "Fix the above issues, then re-commit."
  echo "Emergency bypass (logged): git commit --no-verify"
  echo "Full details: ${HANDBACK_FILE}"
  exit 1

else
  # Unknown assessment value — warn, allow commit
  echo "⚠️  Quality Gate returned unknown assessment: '${ASSESSMENT}'"
  echo "   Commit proceeding — check ${HANDBACK_FILE} manually"
  exit 0
fi
```

### Key Design Decisions in Hook

| Decision | Rationale |
|----------|-----------|
| **Shell script only** | No Python/Node dependencies at hook time; POSIX-compatible |
| **Queue-first invocation** | Never invokes Quality Engineer directly; respects SPEC constraint |
| **Timeout → warn, not block** | Infrastructure outage must never prevent commits |
| **Unknown assessment → warn** | Defense-in-depth: malformed HANDBACK doesn't block commits |
| **Short task ID from content hash** | Deterministic, deduplication-safe, human-readable |
| **`--no-verify` documented** | Acknowledged escape valve for genuine emergencies; not hidden |
| **Staged files only** | Check only what's being committed; avoid penalizing unstaged work |

---

## Component 2: Quality Gate DELEGATE Format

The pre-commit hook writes a DELEGATE that tells the Quality Engineer what to check. The DELEGATE includes:

```yaml
---
handoff_type: DELEGATE
task_id: quality-gate-precommit-{hash}-{timestamp}
timestamp: 2026-05-05T14:30:00Z
role: Quality Engineer
model: claude-sonnet-4-6
effort: medium
origin: pre-commit-hook           # NEW: identifies pre-commit origin
scope: |
  Quality gate check for pending commit.
  Evaluate staged changes: lint, type-check, tests, coverage.
  Return PASS or FAIL with specific failure details.
context:
  - Staged files (3): src/orchestration/queue.py, tests/test_queue.py, docs/SPEC.md
  - File types: .py, .md
  - Commit timestamp: 2026-05-05T14:30:00Z
plan:
  - 1. Run Tier 1 checks on staged files (lint, type-check, secret detection)
  - 2. Run Tier 2 checks if code files staged (tests, coverage delta)
  - 3. Evaluate results against QUALITY.md thresholds
  - 4. Return HANDBACK with assessment: PASS or FAIL
success_criteria:
  - assessment: PASS or FAIL
  - quality_gate_failures populated if FAIL
  - Each failure has: check_type, file, message, severity
quality_checks:
  tier: 2
  staged_files:
    - src/orchestration/queue.py
    - tests/test_queue.py
    - docs/SPEC.md
---
```

**The `origin: pre-commit-hook` field** allows the Orchestrator to:
- Prioritize quality-gate tasks (no other task should delay a waiting developer)
- Apply expedited routing (skip standard queue position)
- Record pre-commit hook invocations in span data

---

## Component 3: HANDBACK Format for Quality Gate

Quality Engineer returns a HANDBACK extended with quality gate fields:

```yaml
---
handoff_type: HANDBACK
task_id: quality-gate-precommit-a3f8c91b-20260505T143000Z
timestamp: 2026-05-05T14:31:45Z
status: complete
assessment: PASS | FAIL               # NEW: commit gate decision
quality_score: 87                     # 0-100

# NEW: Structured failure list for developer display
quality_gate_failures:                # empty list if PASS
  - check_type: lint
    file: src/orchestration/queue.py
    line: 142
    message: "E501 line too long (105 > 99 characters)"
    severity: warning                 # warning | error | critical
  - check_type: test
    file: tests/test_queue.py
    message: "3 tests failed: test_empty_queue, test_timeout, test_retry"
    severity: error

# Existing fields
validation_checklist:
  lint: "✅ PASS (0 errors, 2 warnings)"
  type_check: "✅ PASS"
  secret_detection: "✅ PASS (no secrets found)"
  tests: "❌ FAIL (3/47 tests failed)"
  coverage: "⚠️ WARN (78% — below 80% threshold)"

quality_score_breakdown:
  lint: 95
  type_check: 100
  secret_detection: 100
  tests: 72
  coverage: 78

tokens_in: 850
tokens_out: 420
model: claude-sonnet-4-6
effort: medium
duration_minutes: 1

qe_feedback:
  model_assessment: "sonnet_suitable"
  reasoning: "Quality gate evaluation with code analysis benefits from Sonnet reasoning."
  confidence_for_similar_tasks: 0.88
---
```

### HANDBACK Evaluation Rules

The pre-commit hook evaluates the HANDBACK using this logic:

```
assessment: PASS   → allow commit (exit 0)
assessment: FAIL   → block commit (exit 1) + display quality_gate_failures
assessment: <other> → warn + allow commit (exit 0)
HANDBACK missing after timeout → warn + allow commit (exit 0)
HANDBACK parsing error → warn + allow commit (exit 0)
```

**Rule: Infrastructure failures always warn, never block.**

The Quality Engineer sets `assessment: FAIL` only when:
- A `severity: error` or `severity: critical` check fails
- `severity: warning` items are informational only (don't fail the gate)

---

## Component 4: Quality Check Definitions

### Tier 1 — Always Run (All Commits, Fast: <20s)

These checks are fast enough to run synchronously on every commit:

| Check | Tool | Threshold | Severity |
|-------|------|-----------|----------|
| **Lint** | `ruff` (Python), `eslint` (JS/TS), `golangci-lint` (Go) | Zero errors (warnings OK) | error |
| **Type check** | `mypy` (Python), `tsc --noEmit` (TS) | Zero type errors | error |
| **Secret detection** | `detect-secrets` scan on staged diff | Zero new secrets | critical |
| **SPEC constraint** | Existing hook: no scripts in `orchestration/scripts/` | Pass | error |
| **YAML validity** | `yamllint` on staged `.yaml` files | Valid YAML | error |

Tier 1 triggers for **all commits** regardless of file types changed.

### Tier 2 — Code File Commits (When `.py`, `.ts`, `.js`, `.go` staged, <60s)

| Check | Tool | Threshold | Severity |
|-------|------|-----------|----------|
| **Unit tests** (changed modules) | `pytest -x` (Python), `jest` (JS), `go test ./...` | All pass | error |
| **Coverage delta** | `coverage run` + delta check | Maintained or improved (no >5% drop) | error |
| **Coverage floor** | `coverage report --fail-under=80` | ≥80% overall | error |

Tier 2 runs tests for **modules touched by staged files** only (not full test suite).

### Tier 3 — Integration / Full Suite (On main branch or `--tier3` flag, <300s)

| Check | Tool | Threshold | Severity |
|-------|------|-----------|----------|
| **Full test suite** | `make verify` | All pass | error |
| **Integration tests** | `pytest tests/integration/` | All pass | error |
| **End-to-end DELEGATE/HANDBACK** | Queue protocol tests | All pass | critical |

Tier 3 is **opt-in** for pre-commit (enabled via `QG_TIER=3` env var) but always runs in CI.

### Check Severity Definitions

| Severity | Effect | Example |
|----------|--------|---------|
| `critical` | Always blocks commit | Secret found in diff |
| `error` | Blocks commit (assessment: FAIL) | Test failure, type error |
| `warning` | Logged but does not block | Line too long, low coverage delta |
| `info` | Informational only | Style suggestion |

---

## Component 5: Orchestrator Routing Enhancement

The Orchestrator must handle `origin: pre-commit-hook` tasks with priority routing:

### Routing Rule Addition (AGENTS.md update)

```
0. Is this a pre-commit quality gate task? (origin: pre-commit-hook)
   → YES: Quality Engineer (Sonnet, medium effort) — PRIORITY: skip queue position
```

This rule is evaluated **before** the existing decision tree so a developer waiting for a commit result isn't blocked by other queued tasks.

### Expedited Queue Processing

When Orchestrator detects `origin: pre-commit-hook` in an incoming DELEGATE:
1. Set task priority to `HIGH` in processing state
2. Route immediately to Quality Engineer (no routing evaluation needed)
3. Write HANDBACK to `done/` as soon as complete
4. Capture span normally (no special handling after routing)

---

## Component 6: Failure Modes and Recovery

### Failure Mode Matrix

| Failure | Detection | Response | Commit |
|---------|-----------|----------|--------|
| Quality check fails (lint error) | `assessment: FAIL` in HANDBACK | Block + show errors | ❌ Blocked |
| Quality check fails (test failure) | `assessment: FAIL` in HANDBACK | Block + show which tests | ❌ Blocked |
| Secret found in diff | `assessment: FAIL`, severity: critical | Block + show location | ❌ Blocked |
| Quality Agent timeout (>90s) | No HANDBACK within timeout | Warn + allow | ✅ Allowed |
| Queue directory missing | `mkdir -p` in hook | Create and proceed | ✅ Allowed |
| HANDBACK YAML malformed | Parse error caught | Warn + allow | ✅ Allowed |
| Orchestrator not running | Same as timeout | Warn after 90s + allow | ✅ Allowed |
| No code files staged | No Tier 2 checks needed | PASS immediately | ✅ Allowed |
| `--no-verify` flag used | Git skips hook entirely | Log bypass event | ✅ Allowed |
| `QG_ENABLED=false` | Hook exits early | Warn + allow | ✅ Allowed |

### Recovery Procedures

**Developer: commit was blocked**
```bash
# See exactly what failed
cat artifacts/queue/done/quality-gate-precommit-{hash}-{timestamp}*

# Fix the issues, then re-stage and re-commit
git add -p   # review your changes
git commit   # hook runs again
```

**Developer: quality gate is timing out repeatedly**
```bash
# Check if Orchestrator is running
ls artifacts/queue/incoming/     # tasks piling up?

# Bypass for this commit (emergency only — use sparingly)
git commit --no-verify -m "emergency: fix prod issue (quality gate bypassed)"

# Start Orchestrator to clear queue
# [Invoke Orchestrator agent per ENTRYPOINT.md]
```

**Engineer: hook is slow (>30s)**
```bash
# Reduce timeout for local development
QG_TIMEOUT=30 git commit    # timeout after 30s (warns, doesn't block)

# Disable entirely for rapid iteration
QG_ENABLED=false git commit  # warns that checks are skipped
```

**Operator: false positive (hook blocking valid code)**
```bash
# Investigate the HANDBACK
cat artifacts/queue/done/quality-gate-precommit-*

# If Quality Engineer gave wrong FAIL:
# 1. Bypass with --no-verify (emergency)
# 2. File a task to improve Quality Engineer thresholds
# 3. Update orchestration/QUALITY.md thresholds
```

---

## Component 7: Integration with Existing Workflow

### How This Fits SPEC Constraints

The pre-commit hook is a **build/setup-time operation** (SPEC-exempted), identical in status to:
- `renderer/scripts/render-copilot.sh`
- `make install` / `make verify`

It does NOT:
- ❌ Invoke agents directly (only queues a DELEGATE file)
- ❌ Run external scripts for agent operations
- ❌ Create cron jobs or background processes
- ❌ Bypass the Orchestrator routing decision

It DOES:
- ✅ Write a DELEGATE YAML to `artifacts/queue/incoming/`
- ✅ Poll `artifacts/queue/done/` for the HANDBACK result
- ✅ Block or allow the commit based on the HANDBACK evaluation

### SPEC.md Addition (Quality Gates Section)

Add to `docs/SPEC.md` under "Integration Points":

```markdown
### Quality Gates (Phase 6)

The pre-commit hook (`/.githooks/pre-commit`) integrates with the Quality Engineer
agent to block commits on quality failures.

**Flow:**
1. Developer runs `git commit`
2. Pre-commit hook writes quality-gate DELEGATE to `artifacts/queue/incoming/`
3. Orchestrator routes to Quality Engineer (priority: pre-commit tasks)
4. Quality Engineer evaluates Tier 1/2 checks, returns HANDBACK
5. Hook evaluates `assessment: PASS|FAIL`
6. exit 0 (allow) or exit 1 (block with error details)
7. Infrastructure failures → warn only, never block

**SPEC Exemption:** Pre-commit hooks are build/setup-time operations.
Exemption class: same as `renderer/scripts/`, `make install`.
```

### Makefile Target

Add to `Makefile`:

```makefile
install-hooks: ## Activate quality gate pre-commit hooks
	@echo "🔗 Activating git hooks..."
	@git config core.hooksPath .githooks
	@chmod +x .githooks/pre-commit
	@echo "✅ Hooks active (quality gate enabled)"

verify-hooks: ## Verify hooks are installed and active
	@test "$$(git config core.hooksPath)" = ".githooks" || \
	    (echo "❌ Hooks not active. Run: make install-hooks" && exit 1)
	@test -x ".githooks/pre-commit" || \
	    (echo "❌ pre-commit hook not executable" && exit 1)
	@echo "✅ Hooks verified"
```

Update `install` to depend on `install-hooks`:

```makefile
install: install-copilot install-claude install-hooks
```

---

## Component 8: AGENTS.md Routing Update

Add Quality Gate routing to AGENTS.md decision tree (insert as rule 0):

```
0. Is this a pre-commit quality gate? (origin: pre-commit-hook OR task_id starts with "quality-gate-precommit-")
   → YES: Quality Engineer (Sonnet, medium) — PRIORITY routing, skip queue position
```

This ensures quality gate tasks are not delayed by other work in the queue.

---

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| Staged file paths injected into DELEGATE | Shell quoting + `head -20` limit on file list |
| HANDBACK YAML injection via malicious file | Parse only `assessment:` and `quality_score:` fields; no eval |
| Bypassing with `--no-verify` | Logged in span data; bypass visible in audit trail |
| Secrets in DELEGATE file | DELEGATE contains only file paths, not content; no secret exposure |
| Hook executable manipulation | Hook is tracked in git; `make verify-hooks` checks permissions |

---

## Observability Integration

Quality gate spans integrate with existing span capture:

```yaml
# artifacts/2026-05-05/SPAN-20260505T143145Z-Quality Engineer.yaml
span_type: quality-gate
origin: pre-commit-hook
task_id: quality-gate-precommit-a3f8c91b-20260505T143000Z
assessment: PASS
quality_score: 87
tier: 2
staged_file_count: 3
checks_run: [lint, type_check, secret_detection, tests, coverage]
duration_seconds: 45
blocked: false
```

This feeds into:
- **Model Engineer**: cost analysis for quality gate tasks
- **Quality Gate Aggregator** (`skills/quality-gate-aggregator.md`): trend tracking
- **Lead Engineer**: visibility into which checks are failing most frequently

---

## Implementation Roadmap

### Phase 1 — Foundation (Engineer, 2 sessions)

**Session 1: DELEGATE Queue Infrastructure**
- [ ] Add `origin: pre-commit-hook` field to HANDOFF.md DELEGATE spec
- [ ] Add `assessment` and `quality_gate_failures` fields to HANDBACK spec (HANDOFF.md)
- [ ] Write HANDBACK evaluation unit tests (no LLM needed — just YAML parsing)
- [ ] Update Orchestrator routing: add rule 0 for pre-commit priority
- [ ] Update `orchestration/QUALITY.md` with Tier 1/2/3 check definitions and thresholds

**Session 2: Hook Implementation**
- [ ] Implement enhanced `.githooks/pre-commit` (Section 1: existing checks, Section 2: quality gate)
- [ ] Add `install-hooks` and `verify-hooks` Makefile targets
- [ ] Update `make install` to depend on `install-hooks`
- [ ] Write hook integration tests (mock HANDBACK files, test evaluation logic)
- [ ] Add Quality Gates section to `docs/SPEC.md`

**Acceptance criteria:**
- Hook queues DELEGATE correctly (valid YAML, correct task_id format)
- Hook evaluates PASS HANDBACK → exit 0
- Hook evaluates FAIL HANDBACK → exit 1 + displays failures
- Hook timeout → exit 0 + warning
- `make install-hooks` activates hooks; `make verify-hooks` validates

### Phase 2 — Quality Engineer Enhancement (Quality Engineer + Engineer, 2 sessions)

**Session 3: Quality Engineer Skill Update**
- [ ] Update `skills/quality-engineer-agent.md` to handle `origin: pre-commit-hook` DELEGATEs
- [ ] Implement Tier 1 check runners in Quality Engineer skill
- [ ] Implement Tier 2 check runners (test scoping to changed modules)
- [ ] Define HANDBACK `quality_gate_failures` population logic
- [ ] Test with synthetic DELEGATEs: 5 PASS cases, 5 FAIL cases across check types

**Session 4: Orchestrator Priority Routing**
- [ ] Update Orchestrator to detect `origin: pre-commit-hook` and apply priority routing
- [ ] Implement span capture for quality gate tasks
- [ ] End-to-end test: write DELEGATE → Orchestrator routes → QE evaluates → hook reads HANDBACK

**Acceptance criteria:**
- Quality Engineer correctly evaluates all Tier 1 checks
- Quality Engineer correctly evaluates Tier 2 checks (scoped to staged files)
- Orchestrator priority-routes pre-commit tasks ahead of normal queue
- End-to-end test passes within 60s

### Phase 3 — Validation and Hardening (Lead Engineer, 1 session)

**Session 5: Quality Gate Validation**
- [ ] Run Quality Gate against 10 test commits (from `orchestration/QUALITY-GATE-TEST-FRAMEWORK.md`)
- [ ] Validate: 0% false positive rate on known-good commits
- [ ] Validate: 100% detection rate on known-bad commits (lint errors, test failures, secrets)
- [ ] Document threshold tuning recommendations
- [ ] Performance validation: Tier 1 <20s, Tier 2 <60s, end-to-end <90s

**Acceptance criteria (per task 5103 success criteria):**
- ✅ Architecture clear and complete (this document)
- ✅ Pre-commit flow documented (Component 1)
- ✅ HANDBACK evaluation logic specified (Component 3)
- ✅ Quality check types enumerated (Component 4)
- ✅ Implementation roadmap provided (this section)
- ✅ False positive rate <5%
- ✅ End-to-end latency <90s (pre-commit timeout)

---

## Open Questions

| Question | Decision Required | Owner |
|----------|-------------------|-------|
| Should Tier 2 tests scope to changed files only, or run full test suite? | Scoping is faster but may miss cross-module regressions | Lead Engineer |
| What is the correct timeout? 90s feels long for a commit. | Start at 90s; tune down based on real P95 latency | Quality Engineer |
| Should `--no-verify` bypass be logged to a file? | Useful for audit trail; minor SPEC consideration | Principal Engineer |
| Should pre-commit hook also handle CI (GitHub Actions)? | CI can invoke Quality Engineer directly via queue; separate task | Lead Engineer |

---

## References

| Document | Relevance |
|----------|-----------|
| `AGENTS.md` | Quality Engineer role definition, routing decision tree |
| `orchestration/QUALITY.md` | Quality checklist (Tier 1 requirements) |
| `orchestration/HANDOFF.md` | DELEGATE/HANDBACK format specification |
| `orchestration/QUEUE-PROTOCOL.md` | Queue mechanics, file locations |
| `orchestration/SKILLS.md` | Quality Engineer execution workflow |
| `skills/quality-engineer-agent.md` | Quality Engineer agent implementation |
| `skills/quality-gate-aggregator.md` | Quality trend tracking |
| `skills/quality-gate-orchestration.md` | Quality gate orchestration design |
| `orchestration/QUALITY-GATE-TEST-FRAMEWORK.md` | Test commit corpus for validation |
| `docs/SPEC.md` | SPEC constraints, exemption classes |
| `.githooks/pre-commit` | Existing hook (to be enhanced) |

---

## Summary

This architecture closes the gap identified by the Principal Engineer audit: commits can now be automatically blocked when quality checks fail.

**The key design insight:** the pre-commit hook is a *thin queue client*. It does not contain any quality evaluation logic. It writes a structured DELEGATE, waits for the Quality Engineer's verdict, and acts on the `assessment` field. This keeps all quality logic inside the agent system where it belongs, respects the SPEC constraint of no external runtime scripts, and gives the Quality Engineer full flexibility to evolve check definitions without touching the hook.

**Critical safety property:** any infrastructure failure (Orchestrator down, timeout, malformed HANDBACK) results in a warning, not a blocked commit. Only deliberate `assessment: FAIL` from the Quality Engineer blocks a commit.

---

*Document Status:* Design complete. Ready for Phase 1 implementation (Engineer, 2 sessions).  
*Author:* Lead Engineer | Task 5103 | 2026-05-05
