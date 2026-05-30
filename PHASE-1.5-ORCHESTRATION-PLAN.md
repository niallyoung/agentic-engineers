# Phase 1.5 Security Hardening — Framework-Based Implementation

**Status:** Ready for Orchestrator Delegation  
**Date:** 2026-05-30  
**Approach:** Queue-based DELEGATE/HANDBACK protocol (NOT subagents)

---

## Overview

All 5 critical security fixes will be implemented via proper DELEGATE routing through the Orchestrator. Each DELEGATE goes to the appropriate specialist role, which executes the work, collects metrics, and returns a HANDBACK.

**Key Principle:** Framework demonstrates itself by using itself to fix itself.

---

## DELEGATEs (In Execution Order)

### DELEGATE #1: Queue Path Enforcement (Quality Engineer)

**File:** `~/.agentic-engineers/local-session/opencode/queue/incoming/TASK-PHASE-1.5-FIX-1.yaml`

```yaml
---
task_id: TASK-PHASE-1.5-FIX-1
type: DELEGATE
role: quality-engineer
model: claude-sonnet-4.6
effort: medium
priority: normal

context:
  description: |
    Implement FIX #1: Queue Path Enforcement (Runtime + Git Hook)
    
    PROBLEM: SPEC.md contains contradictory queue paths:
    - Line 21: artifacts/queue/
    - Lines 37, 72: ~/.copilot/queue/{session-id}/incoming/
    - Lines 504-546: ~/.agentic-engineers/{session-id}/{harness}/queue/ (CANONICAL)
    
    This enables queue injection/poisoning attacks if paths are not enforced.
    
    SOLUTION: Implement runtime validator + git hook that enforces canonical path.
    
  repo: agentic-engineers
  branch: feature/spec-audit-phase1-security-assessment
  commit: cfbd7f7  # Current head (PHASE-1.5-SECURITY-HARDENING.md)
  files:
    - src/skills/_meta/queue-path-validator/
    - .githooks/pre-push
    - src/orchestration/delegate-schema.yaml
  line_refs:
    - "PHASE-1.5-SECURITY-HARDENING.md:26-61"  # FIX #1 spec

requirements:
  - Create src/skills/_meta/queue-path-validator/SKILL.md (skill specification)
  - Create src/skills/_meta/queue-path-validator/scripts/queue_path_validator.py (TDD implementation)
  - Create src/skills/_meta/queue-path-validator/tests/test_queue_path_validator.py (5+ tests, RED-GREEN)
  - Update .githooks/pre-push with queue path validation checks
  - All tests passing before HANDBACK
  - No CI failures

acceptance_criteria:
  - "AC1: Runtime validator accepts canonical path: ~/.agentic-engineers/{session-id}/{harness}/queue/"
  - "AC2: Runtime validator rejects legacy paths: artifacts/queue/ and ~/.copilot/queue/"
  - "AC3: Runtime validator blocks path injection attempts (traversal, shell metacharacters)"
  - "AC4: Git hook validates all DELEGATE/HANDBACK files use canonical paths"
  - "AC5: All 5+ test cases passing, make test shows green"
  - "AC6: No linting errors (make lint passes)"

constraints:
  - Must follow TDD (RED phase first, then GREEN)
  - Python 3.7 compatible (no dataclasses, no f-strings in type hints)
  - No external dependencies beyond standard library
  - Test file must be created BEFORE implementation file

escalation_triggers:
  - Test failures after 2 fix attempts → escalate to Senior Engineer
  - Complexity spans > 1 file type (validator + hook + tests) beyond scope → escalate to Lead Engineer

repro: "cd src/skills/_meta/queue-path-validator && python -m pytest tests/ -v"

skill_refs:
  - src/skills/roles/quality-engineer.md
  - PHASE-1.5-SECURITY-HARDENING.md (lines 26-61)
  - src/AGENTS.md (routing rules, HANDBACK format)

token_budget: 6000
estimated_cost: 0.09
```

---

### DELEGATE #2: Audit Trail via spec_version (Security Engineer)

**File:** `~/.agentic-engineers/local-session/opencode/queue/incoming/TASK-PHASE-1.5-FIX-2.yaml`

```yaml
---
task_id: TASK-PHASE-1.5-FIX-2
type: DELEGATE
role: security-engineer
model: claude-opus-4.7
effort: high
priority: normal

context:
  description: |
    Implement FIX #2: Audit Trail via spec_version Field (DELEGATE/HANDBACK/SPAN)
    
    PROBLEM: Removing version stamps breaks audit trail. No linkage to spec versions.
    Cannot answer: "Which SPEC version authorized this model selection? Did spec drift occur?"
    
    SOLUTION: Add spec_version field to DELEGATE and HANDBACK schemas.
    Enable audit queries: "Which tasks executed under spec v1.0?"
    
  repo: agentic-engineers
  branch: feature/spec-audit-phase1-security-assessment
  commit: cfbd7f7
  files:
    - src/skills/_meta/spec-version-validator/
    - src/orchestration/delegate-schema.yaml
    - src/orchestration/handback-schema.yaml
  line_refs:
    - "PHASE-1.5-SECURITY-HARDENING.md:64-109"  # FIX #2 spec

requirements:
  - Create src/skills/_meta/spec-version-validator/SKILL.md (skill specification)
  - Create src/skills/_meta/spec-version-validator/scripts/spec_version_validator.py (implementation)
  - Create src/skills/_meta/spec-version-validator/tests/test_spec_version_validator.py (5+ tests, TDD)
  - Update src/orchestration/delegate-schema.yaml with spec_version field (required, pattern validation)
  - Update src/orchestration/handback-schema.yaml with spec_version field (required, must match DELEGATE)
  - All tests passing
  - Schema validation passes (YAML valid, field presence verified)

acceptance_criteria:
  - "AC1: DELEGATE schema includes spec_version field with pattern '^\\d+\\.\\d+(-.+)?$'"
  - "AC2: HANDBACK schema includes spec_version field that must match DELEGATE"
  - "AC3: Validator rejects mismatched spec_versions (HANDBACK != DELEGATE)"
  - "AC4: Audit queries work: find_tasks_by_spec_version() returns correct tasks"
  - "AC5: Format validation: '1.0', '1.1', '1.1-2026-05-28' accepted; 'v1.0', '1', '1.0.0' rejected"
  - "AC6: All 5+ test cases passing"

constraints:
  - Must follow TDD (tests first)
  - Pattern validation: `\d+\.\d+(-.+)?` (major.minor with optional suffix)
  - No external dependencies
  - Python 3.7 compatible

escalation_triggers:
  - Schema migration breaks existing DELEGATEs → escalate to Principal Engineer
  - Audit query performance issues → escalate to Lead Engineer

repro: "cd src/skills/_meta/spec-version-validator && python -m pytest tests/ -v"

skill_refs:
  - src/skills/roles/security-engineer.md
  - PHASE-1.5-SECURITY-HARDENING.md (lines 64-109)

token_budget: 8000
estimated_cost: 0.15
```

---

### DELEGATE #3: Agent Definition Verification (Security Engineer)

**File:** `~/.agentic-engineers/local-session/opencode/queue/incoming/TASK-PHASE-1.5-FIX-3.yaml`

```yaml
---
task_id: TASK-PHASE-1.5-FIX-3
type: DELEGATE
role: security-engineer
model: claude-opus-4.7
effort: high
priority: normal

context:
  description: |
    Implement FIX #3: Agent Definition Verification (Tri-Level: Git + Field + Runtime)
    
    PROBLEM: No mechanism verifies AGENTS.md matches SPEC.md definitions.
    ATTACK: SPEC says Security Engineer = Opus-4.7, but implementation uses Sonnet-4.6.
    Security work silently underfunded without awareness.
    
    SOLUTION: Tri-level verification:
    1. Git hook: Verify model_verification_sha in DELEGATE/HANDBACK
    2. Schema field: Add model_verification_sha to DELEGATE schema
    3. Runtime: Orchestrator verifies model exists in AGENTS.md before invoking
    
  repo: agentic-engineers
  branch: feature/spec-audit-phase1-security-assessment
  commit: cfbd7f7
  files:
    - src/skills/_meta/agent-definition-verifier/
    - src/orchestration/agent-verification.py
    - .agents_verification_sha
    - .githooks/pre-push
    - src/orchestration/delegate-schema.yaml
  line_refs:
    - "PHASE-1.5-SECURITY-HARDENING.md:112-154"  # FIX #3 spec

requirements:
  - Create src/skills/_meta/agent-definition-verifier/SKILL.md
  - Create src/skills/_meta/agent-definition-verifier/scripts/agent_definition_verifier.py
  - Create src/skills/_meta/agent-definition-verifier/tests/test_agent_definition_verifier.py (5+ tests, TDD)
  - Create src/orchestration/agent-verification.py (SHA256 generation)
  - Generate .agents_verification_sha file (format: agent_sha256={hex}\ngenerated_at={timestamp}\n)
  - Update .githooks/pre-push with agent verification checks
  - Update src/orchestration/delegate-schema.yaml with model_verification_sha field
  - All tests passing

acceptance_criteria:
  - "AC1: Verification SHA generated correctly as 64-char hex (SHA256 of agents-manifest.yaml)"
  - "AC2: SHA matches for unmodified AGENTS.md; changes when AGENTS.md modified"
  - "AC3: DELEGATE with matching SHA accepted; mismatched SHA rejected"
  - "AC4: Model downgrade attacks blocked (model not in AGENTS.md = task rejected)"
  - "AC5: Git hook validates model_verification_sha in all DELEGATE/HANDBACK files"
  - "AC6: All 5+ test cases passing"

constraints:
  - Must follow TDD
  - SHA256 format: 64-character hex string
  - No external dependencies
  - Python 3.7 compatible

escalation_triggers:
  - AGENTS.md structure changes require design decision → escalate to Lead Engineer
  - Runtime integration with Orchestrator required → escalate to Principal Engineer

repro: "cd src/skills/_meta/agent-definition-verifier && python -m pytest tests/ -v"

skill_refs:
  - src/skills/roles/security-engineer.md
  - PHASE-1.5-SECURITY-HARDENING.md (lines 112-154)

token_budget: 10000
estimated_cost: 0.15
```

---

### DELEGATE #4: Security-Critical DELEGATE Fields (Lead Engineer)

**File:** `~/.agentic-engineers/local-session/opencode/queue/incoming/TASK-PHASE-1.5-FIX-4.yaml`

```yaml
---
task_id: TASK-PHASE-1.5-FIX-4
type: DELEGATE
role: lead-engineer
model: claude-sonnet-4.6
effort: high
priority: normal

context:
  description: |
    Implement FIX #4: Security-Critical DELEGATE Fields
    
    PROBLEM: No way to flag security tasks. Security work routed to general engineers, underfunded.
    
    SOLUTION: Add 3 fields to DELEGATE schema:
    - security_scope: [none|auth|crypto|pii|secrets|injection|supply_chain]
    - approval_gate: [none|lead_engineer|principal_engineer|security_engineer|cto]
    - audit_required: boolean
    
    Routing rules: If security_scope set → route to Security Engineer minimum.
    If approval_gate set → enforce approval before execution.
    
  repo: agentic-engineers
  branch: feature/spec-audit-phase1-security-assessment
  commit: cfbd7f7
  files:
    - src/skills/_meta/security-field-validator/
    - src/orchestration/delegate-schema.yaml
  line_refs:
    - "PHASE-1.5-SECURITY-HARDENING.md:157-201"  # FIX #4 spec

requirements:
  - Create src/skills/_meta/security-field-validator/SKILL.md
  - Create src/skills/_meta/security-field-validator/scripts/security_field_validator.py
  - Create src/skills/_meta/security-field-validator/tests/test_security_field_validator.py (10+ tests, TDD)
  - Update src/orchestration/delegate-schema.yaml with 3 new security fields
  - Implement routing logic: If security_scope != none → Security Engineer, etc.
  - All tests passing

acceptance_criteria:
  - "AC1: Non-security tasks default to security_scope=none, approval_gate=none"
  - "AC2: Auth/crypto/pii/secrets/injection/supply_chain tasks routed to Security Engineer"
  - "AC3: Approval gates enforced: principal_engineer → Principal Engineer, cto → escalate"
  - "AC4: Invalid combinations rejected (security_scope set but approval_gate=none)"
  - "AC5: Validation rule: If security_scope set, approval_gate must be set; if approval_gate set, audit_required=true"
  - "AC6: All 10+ test cases passing"

constraints:
  - Must follow TDD
  - Enum validation for all fields
  - Python 3.7 compatible

escalation_triggers:
  - Orchestrator routing logic needs hardening → escalate to Principal Engineer
  - Performance impact of security checks → escalate to Model Engineer

repro: "cd src/skills/_meta/security-field-validator && python -m pytest tests/ -v"

skill_refs:
  - src/skills/roles/lead-engineer.md
  - PHASE-1.5-SECURITY-HARDENING.md (lines 157-201)

token_budget: 8000
estimated_cost: 0.09
```

---

### DELEGATE #5: Orchestrator Enforcement Decorator (Senior Engineer)

**File:** `~/.agentic-engineers/local-session/opencode/queue/incoming/TASK-PHASE-1.5-FIX-5.yaml`

```yaml
---
task_id: TASK-PHASE-1.5-FIX-5
type: DELEGATE
role: senior-engineer
model: claude-sonnet-4.6
effort: high
priority: normal

context:
  description: |
    Implement FIX #5: Weak Orchestrator Enforcement Decorator
    
    PROBLEM: No runtime enforcement. DELEGATEs can bypass field requirements.
    
    SOLUTION: Implement @enforce_delegate_requirement decorator.
    
    Usage:
    @enforce_delegate_requirement('security_scope', allowed_values=['auth','crypto'])
    @enforce_delegate_requirement('approval_gate', required=True)
    def route_to_security_engineer(delegate):
        # Won't execute if requirements not met
        ...
    
    What it does:
    - Pre-checks DELEGATE fields before function execution
    - Rejects DELEGATEs that violate requirements
    - Logs rejection with clear error message
    - Raises DelegateRequirementViolation exception
    
  repo: agentic-engineers
  branch: feature/spec-audit-phase1-security-assessment
  commit: cfbd7f7
  files:
    - src/skills/_meta/orchestrator-enforcer/
    - src/orchestration/decorators.py
  line_refs:
    - "PHASE-1.5-SECURITY-HARDENING.md:230-260"  # FIX #5 spec

requirements:
  - Create src/skills/_meta/orchestrator-enforcer/SKILL.md
  - Create src/skills/_meta/orchestrator-enforcer/scripts/orchestrator_enforcer.py
  - Create src/skills/_meta/orchestrator-enforcer/tests/test_orchestrator_enforcer.py (10+ tests, TDD)
  - Create DelegateRequirementViolation exception class
  - Implement decorator factory: enforce_requirement(field_name, allowed_values, required)
  - Support stacking multiple decorators
  - All tests passing

acceptance_criteria:
  - "AC1: Correctly-formed DELEGATE passes through decorator unchanged"
  - "AC2: DELEGATE missing required field is rejected with clear error"
  - "AC3: DELEGATE with invalid field value is rejected"
  - "AC4: Stacked decorators all enforce constraints independently"
  - "AC5: Error message includes field name, current value, allowed values, task_id"
  - "AC6: Exception includes DELEGATE metadata for debugging"
  - "AC7: All 10+ test cases passing"

constraints:
  - Must follow TDD
  - Support stacking decorators
  - Error messages must include actionable context
  - Python 3.7 compatible
  - No external dependencies

escalation_triggers:
  - Decorator performance concerns → escalate to Principal Engineer
  - Integration with Orchestrator requires architectural changes → escalate to Lead Engineer

repro: "cd src/skills/_meta/orchestrator-enforcer && python -m pytest tests/ -v"

skill_refs:
  - src/skills/roles/senior-engineer.md
  - PHASE-1.5-SECURITY-HARDENING.md (lines 230-260)

token_budget: 8000
estimated_cost: 0.09
```

---

## Execution Order

### Tier 0 (Can run in parallel — no dependencies)

- **TASK-PHASE-1.5-FIX-1** (Queue Path Enforcement) → Quality Engineer
- **TASK-PHASE-1.5-FIX-2** (Audit Trail spec_version) → Security Engineer
- **TASK-PHASE-1.5-FIX-3** (Agent Definition Verification) → Security Engineer
- **TASK-PHASE-1.5-FIX-4** (Security-Critical Fields) → Lead Engineer
- **TASK-PHASE-1.5-FIX-5** (Enforcement Decorator) → Senior Engineer

**Trigger:** All 5 DELEGATEs written to queue simultaneously. Agents execute in parallel.

### Tier 1 (After all Tier 0 complete)

- **Consolidation DELEGATE** → Lead Engineer
  - Integrate all 5 HANDBACKs
  - Run full test suite
  - Verify no regressions
  - Produce final commit

---

## Expected HANDBACKs

Each agent returns a HANDBACK with:

```yaml
---
task_id: TASK-PHASE-1.5-FIX-N
type: HANDBACK
role: [quality-engineer|security-engineer|lead-engineer|senior-engineer]
status: COMPLETE  # or PARTIAL / BLOCKED / ESCALATE

summary: |
  One-paragraph summary of what was implemented.

changes:
  - file: src/skills/_meta/queue-path-validator/SKILL.md
    lines: "1-150"
    description: Skill spec for queue path validation
  - file: src/skills/_meta/queue-path-validator/scripts/queue_path_validator.py
    lines: "1-200"
    description: Runtime validator implementation
  # ... etc

acceptance_verified:
  - "AC1: PASS — [how verified]"
  - "AC2: PASS — [how verified]"
  - "AC3: PASS — [how verified]"

metrics:
  tokens_used: 5240
  tokens_estimated: 6000
  efficiency_ratio: 0.87
  model_used: claude-sonnet-4.6
  duration_ms: 35000
  quality_score: 0.92

issues: []
escalation: null
```

---

## Quality Gates

After all HANDBACKs received:

1. **Lead Engineer Consolidation**
   - Verifies all acceptance criteria met
   - Runs `make test` (all tests passing)
   - Runs `make lint` (no errors)
   - Produces single atomic commit
   - Verifies CI passes

2. **Lead Engineer Code Review**
   - 8-point review (correctness, safety, patterns, performance, security surface, maintainability, test coverage, docs)
   - Signs off on final implementation

3. **Security Engineer Final Audit**
   - Verifies security fixes actually solve the threat models
   - No new vulnerabilities introduced
   - Compliance with framework patterns

---

## Success Criteria

✅ All 5 FIXes implemented  
✅ 35+ test cases passing  
✅ All CI checks green  
✅ Single atomic commit  
✅ PR #24 updated with implementation details  
✅ Ready to merge to main  

---

## Framework Demonstration Value

This implementation **proves the framework works end-to-end:**

- ✅ Queue-based routing (all tasks via DELEGATE)
- ✅ Role specialization (each role appropriate for task)
- ✅ Parallel execution (5 independent tasks run simultaneously)
- ✅ Metrics collection (efficiency, quality, model fit)
- ✅ Escalation handling (LEADs consolidation, SECURITY reviews)
- ✅ ACK protocol (every agent ACKs before work)
- ✅ TDD workflow (tests first, then implementation)
- ✅ Model optimization (right model for right task)

---

## Next Steps After PR #24 Merges

1. **OpenCode Integration (Priority 1)**
   - Create harness compatibility checker
   - Fix queue path detection for OpenCode
   - Wire Orchestrator into OpenCode CLI

2. **README Updates (Priority 1)**
   - Document "AGENTS with SKILLS" philosophy
   - Explain why queue-first architecture
   - Vision: reducing footprint over time

3. **Feature/Cleanup Branch (Priority 2)**
   - Switch back to feature/cleanup
   - Apply same framework principles
   - Skill cleanup, slop cleanup, generalization
