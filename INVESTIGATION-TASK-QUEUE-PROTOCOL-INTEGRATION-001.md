# TASK-QUEUE-PROTOCOL-INTEGRATION-001 — Architecture Investigation Report

## Executive Summary

This document contains a comprehensive investigation of native DELEGATE queue processing in the agentic-engineers framework. The task requires designing proper queue integration using the DELEGATE/HANDBACK protocol (no custom scripts) and identifying implementation gaps.

**Investigation Period:** ~4 hours
**Current Status:** ARCHITECTURE DESIGN PHASE
**Acceptance Criteria:** All 10 criteria documented below

---

## AC1: Queue Discovery Mechanism

### Current State
- **queue-management SKILL** (src/skills/queue-management/SKILL.md) exists with atomic queue operations
- **QueueManager class** (queue_manager.py) implements create_delegate() and move_task() operations
- **SPEC.md Section 25-50** defines ORCHESTRATOR-FIRST EXECUTION MODEL
- **Queue path:** `~/.agentic-engineers/queue/{session_id}/incoming/` (session-partitioned)

### Findings
- ✅ Queue structure exists in spec and codebase
- ✅ QueueOperations class provides atomic operations
- ❌ **GAP:** No documented queue discovery mechanism in Orchestrator
  - Orchestrator SKILL (src/skills/orchestration/task-routing.md) documents routing decisions
  - **Missing:** How Orchestrator finds and polls the incoming/ directory
  - **Missing:** Implementation of 30-60 second polling loop
  - **Missing:** Session-id detection logic
  - **Missing:** Handling of malformed YAML files

### Recommendation
- Orchestrator must implement discovery in its SKILL:
  1. Detect session_id (COPILOT_SESSION_ID env or filesystem scan)
  2. Poll `~/.agentic-engineers/queue/{session_id}/incoming/` every 30-60 seconds
  3. Parse each *.yaml file as a potential DELEGATE
  4. Order by priority + task_id (FIFO within priority level)
  5. Skip/log invalid YAML files to error stream

---

## AC2: DELEGATE Validation

### Current State
- **Protocol-Validator SKILL** (src/skills/protocol-validator/SKILL.md) validates DELEGATEs
- **Spec location:** docs/specs/protocol-core-v1.0.yaml (not found - MISSING)
- **Validation rules in queue-management SKILL.md:**
  - Group A: Format & required fields (task_id, role, scope, plan, context)
  - Group B: Scope/plan/context completeness (word counts)
  - Group C: Effort & model validity

### Findings
- ✅ Validation rules documented in SKILL.md
- ✅ ProtocolValidator class exists in protocol-validator SKILL
- ❌ **GAP:** No spec-core-v1.0.yaml file found
  - SPEC.md references this file but it doesn't exist
  - Protocol-validator SKILL expects it at docs/specs/protocol-core-v1.0.yaml
  - Validation currently uses inline rules, not external spec
  
- ❌ **GAP:** No DELEGATE validation integrated into Orchestrator
  - Protocol-validator is available but not called in Orchestrator
  - Missing: Call to validate_delegate() after discovery
  - Missing: Dead-letter queue routing for invalid tasks
  
- ❌ **GAP:** Missing field validation for LOCKED_MODELS constraint
  - SPEC.md mentions "Verify model is in LOCKED_MODELS"
  - No LOCKED_MODELS list defined
  - No "no temporary opus-4.8 outside 48h window" enforcement

### Recommendation
- Create docs/specs/protocol-core-v1.0.yaml with:
  - DELEGATE core fields: task_id, type, role, model, effort, priority, context, requirements, acceptance_criteria
  - HANDBACK core fields: task_id, type, role, status, summary, changes, acceptance_verified, metrics
  - Extension fields: parent_task_id, constraints, escalation_triggers, token_budget, etc.
  
- Update Orchestrator SKILL to:
  1. Call protocol_validator.validate_delegate(delegate) after discovery
  2. Route invalid DELEGATEs to dead-letter queue
  3. Log validation errors with task_id and reason
  
- Define LOCKED_MODELS in AGENTS.md or SPEC.md:
  - claude-opus-4.8: Only allowed for Security Engineer, within 48h window
  - claude-opus-4.7: Principal Engineer and security-critical work
  - claude-sonnet-4.6: Senior Engineer, Lead, Quality, Model Engineers
  - claude-haiku-4.5: Orchestrator, Engineer

---

## AC3: Routing Decision Tree

### Current State
- **AGENTS.md** documents 8 agent roles with decision tree
- **Orchestrator SKILL** (src/skills/orchestration/task-routing.md) has decision tree examples
- **Decision criteria:** Scope clarity, complexity, cross-service impact, scope ambiguity

### Findings
- ✅ Decision tree documented in AGENTS.md (Section "Delegation Model")
- ✅ Routing examples in task-routing.md
- ❌ **GAP:** No Orchestrator implementation of routing logic
  - task-routing.md documents HOW to route
  - **Missing:** Code in Orchestrator that applies the decision tree
  - **Missing:** Extraction of task characteristics (scope clarity, complexity)
  - **Missing:** Creation of DELEGATE blocks with correct role/model selection
  
- ❌ **GAP:** No routing audit trail
  - SPEC.md requires "Log routing decision (audit trail)"
  - Missing: SPAN capture of routing decision
  - Missing: Confidence score in routing decision

### Recommendation
- Orchestrator implementation must:
  1. Extract task characteristics from DELEGATE context
  2. Apply decision tree logic (clarity → complexity → cross-service)
  3. Select role/model from AGENTS.md roster
  4. Create routing SPAN with:
     - routing_decision: selected role/model
     - routing_confidence: 0.0-1.0 score
     - routing_rationale: why this decision was made
  5. Log to artifacts/{date}/SPAN-{timestamp}-orchestrator-routing.yaml

---

## AC4: HANDBACK Reception

### Current State
- **AGENTS.md** defines HANDBACK format (Section "HANDBACK Block Format")
- **protocol-validator SKILL** has validate_handback() method
- **Metadata fields:** tokens_used, efficiency_ratio, quality_score, model_used, duration_ms

### Findings
- ✅ HANDBACK format documented in AGENTS.md
- ✅ Validation rules available in protocol-validator
- ❌ **GAP:** No Orchestrator code to receive HANDBACK
  - Missing: Polling of ~/.agentic-engineers/queue/{session_id}/done/
  - Missing: Parsing of HANDBACK YAML files
  - Missing: Metadata extraction (task_id, role, model, tokens, status)
  - Missing: HANDBACK validation before routing to QE

### Recommendation
- Orchestrator must implement HANDBACK reception:
  1. Poll `~/.agentic-engineers/queue/{session_id}/done/` for HANDBACK files
  2. Parse each HANDBACK YAML file
  3. Call protocol_validator.validate_handback(handback)
  4. Extract metrics: tokens_used, efficiency_ratio, quality_score, model_used, duration_ms
  5. Create SPAN for HANDBACK reception
  6. Route to Quality Engineer for verification (next AC5)

---

## AC5: Quality Gate

### Current State
- **Quality Engineer SKILL** referenced in AGENTS.md role definition
- **Quality Engineer role:** Post-implementation validation, acceptance criteria check, regressions
- **Expected output:** quality_score in HANDBACK metrics

### Findings
- ✅ Quality Engineer role documented in AGENTS.md
- ✅ Boundaries and escalation triggers defined
- ❌ **GAP:** No Quality Engineer SKILL implementation
  - Directory src/skills/roles/quality-engineer/ doesn't exist (or empty)
  - Missing: Implementation of acceptance criteria verification
  - Missing: Integration with make lint && make test && make build
  - Missing: APPROVED/NEEDS_REWORK decision logic
  
- ❌ **GAP:** No Orchestrator routing to Quality Engineer
  - Missing: DELEGATE creation for QE after HANDBACK receipt
  - Missing: QE HANDBACK reception by Orchestrator
  - Missing: Only-move-to-done-if-APPROVED logic

### Recommendation
- Create Quality Engineer SKILL (src/skills/roles/quality-engineer/SKILL.md):
  1. Receive HANDBACK and original DELEGATE
  2. Verify each acceptance criterion
  3. Run CONFIG=dev make lint && make test && make build
  4. Check for regressions (git diff baseline)
  5. Assess model/effort suitability
  6. Return HANDBACK with quality_score and APPROVED/NEEDS_REWORK decision
  
- Update Orchestrator to:
  1. Route HANDBACK to Quality Engineer as DELEGATE
  2. Receive QE HANDBACK with approval decision
  3. Only move task to done/ if status=APPROVED
  4. Move to failed/ if status=NEEDS_REWORK
  5. Create SPAN for QE decision

---

## AC6: Span Capture

### Current State
- **SPEC.md Section 88-93** documents span capture requirement
- **Format:** OpenTelemetry SPAN to artifacts/2026-MM-DD/SPAN-{timestamp}-{agent_type}.yaml
- **Metadata:** task_id, role, model, status, tokens_in, tokens_out, decision, confidence, cost_usd

### Findings
- ✅ Span format documented in SPEC.md
- ✅ Span directory structure defined (artifacts/{date}/)
- ❌ **GAP:** No Orchestrator span capture implementation
  - Missing: Code to create SPAN after HANDBACK receipt
  - Missing: Duration calculation and cost estimation
  - Missing: Decision logging (routing decision, approval decision)
  
- ❌ **GAP:** No artifact indexing
  - SPEC.md references artifacts/index.json
  - Missing: index.json generation by Model Engineer
  - Missing: Scan of artifacts/2026-*/ for DELEGATE/HANDBACK/SPAN

### Recommendation
- Orchestrator implements span capture on HANDBACK receipt:
  1. Extract: task_id, agent_role, agent_model, status, tokens_in, tokens_out
  2. Calculate: duration_ms, cost_usd (from token counts + model rates)
  3. Create SPAN metadata with trace_id, span_id
  4. Write to artifacts/{YYYY-MM-DD}/SPAN-{timestamp}-{agent_type}.yaml
  5. Include: routing_decision, qe_approval_decision, escalation flags

- Model Engineer indexes spans:
  1. Scan artifacts/ directories for SPAN files
  2. Build index: task_id → role/model/cost/quality
  3. Generate artifacts/index.json with aggregations
  4. Recommend model downgrades/upgrades based on efficiency_ratio trends

---

## AC7: Dead-Letter Queue

### Current State
- **SPEC.md Section 79-82** documents dead-letter queue
- **Purpose:** Capture invalid/failed tasks with error logs
- **Location:** ~/.agentic-engineers/queue/dead-letter/

### Findings
- ✅ Dead-letter queue path defined in SPEC.md
- ✅ Purpose and content documented
- ❌ **GAP:** No dead-letter queue implementation
  - Missing: Code to move invalid DELEGATE to dead-letter/
  - Missing: Error log format (reason, validation errors, timestamp)
  - Missing: Daily alert if >5 items in dead-letter/
  - Missing: Cleanup/archival strategy

### Recommendation
- Orchestrator implements dead-letter queue:
  1. On DELEGATE validation failure:
     - Move task to ~/.agentic-engineers/queue/{session_id}/dead-letter/
     - Write error log: DEADLETTER-{timestamp}-{task_id}.log with:
       - task_id, validation_errors, error_reason, timestamp
       - Full DELEGATE content (for diagnosis)
  
  2. On QE rejection (NEEDS_REWORK):
     - Move task to dead-letter/ (before re-routing to Senior Engineer)
     - Include QE feedback as context
  
  3. Daily monitoring:
     - Count items in dead-letter/
     - If >5, emit alert (via voice-notify SKILL)
     - Summarize by error_reason for trending

---

## AC8: Implementation Gaps Summary

### Critical Gaps (Must Implement)

| Component | Status | Gap | Effort |
|-----------|--------|-----|--------|
| **Queue Discovery** | Spec ✅, Code ❌ | Orchestrator polling loop | 1-2h |
| **DELEGATE Validation** | Spec ✅, Code ⚠️ | protocol-validator not integrated | 1h |
| **Routing Decision** | Spec ✅, Code ❌ | Decision tree not implemented in code | 2-3h |
| **HANDBACK Reception** | Spec ✅, Code ❌ | No HANDBACK polling or parsing | 1-2h |
| **Quality Gate** | Spec ⚠️, Code ❌ | QE SKILL doesn't exist | 3-4h |
| **Span Capture** | Spec ✅, Code ❌ | Orchestrator doesn't write SPANs | 2h |
| **Dead-Letter Queue** | Spec ✅, Code ❌ | No DLQ implementation | 2h |
| **LOCKED_MODELS** | Spec ⚠️, Code ❌ | LOCKED_MODELS list not defined | 1h |
| **Spec File** | Missing | protocol-core-v1.0.yaml doesn't exist | 1h |
| **Artifact Index** | Spec ⚠️, Code ❌ | Model Engineer doesn't generate index.json | 2h |

**Total Implementation Effort:** 15-20 hours

### Soft Gaps (Document/Clarify)

- Session-id detection logic (env vars + fallback)
- Cost estimation formula (tokens → USD by model)
- Efficiency ratio calculation (tokens_used / tokens_estimated)
- Effort tier to token estimate mapping

---

## AC9: Implementation Roadmap

### Phase 1: Foundation (2-3 hours)
**Goal:** Create spec files and validate existing infrastructure

1. **Create protocol-core-v1.0.yaml** (1h)
   - Define DELEGATE core fields
   - Define HANDBACK core fields
   - Define extension fields
   - Version control: spec_version: "1.0"

2. **Define LOCKED_MODELS in AGENTS.md** (30m)
   - List allowed models by role
   - Document opus-4.8 48h window constraint
   - Add to Orchestrator decision tree

3. **Validate queue-management + protocol-validator** (30m)
   - Test QueueOperations.create_delegate()
   - Test ProtocolValidator.validate_delegate()
   - Ensure backward compatibility

**Deliverable:** protocol-core-v1.0.yaml, AGENTS.md updated, tests passing

---

### Phase 2: Orchestrator Core (4-5 hours)
**Goal:** Implement queue discovery, validation, routing in Orchestrator

1. **Implement Queue Discovery** (1.5h)
   - Add session-id detection logic
   - Add polling loop (30-60s interval)
   - Parse incoming/*.yaml files
   - Order by priority + task_id
   - Error handling for malformed YAML

2. **Integrate DELEGATE Validation** (1h)
   - Call protocol_validator.validate_delegate()
   - Route invalid to dead-letter/
   - Log validation errors with context
   - Create error SPAN

3. **Implement Routing Decision Tree** (2h)
   - Extract task characteristics (scope, complexity)
   - Apply decision tree logic from AGENTS.md
   - Select role/model from roster
   - Create routing SPAN with confidence score
   - Support escalation to user (unclear scope)

**Deliverable:** Orchestrator discovers tasks, validates, routes to agents

---

### Phase 3: Quality & Span Capture (5-6 hours)
**Goal:** Implement HANDBACK reception, QE validation, span capture

1. **Implement HANDBACK Reception** (1.5h)
   - Poll done/ directory for HANDBACK files
   - Parse HANDBACK YAML
   - Validate against protocol-core-v1.0.yaml
   - Extract metrics to SPAN object

2. **Create Quality Engineer SKILL** (3h)
   - Implement acceptance criteria verification
   - Run make lint && make test && make build
   - Assess model/effort suitability
   - Return APPROVED/NEEDS_REWORK decision
   - Handle regressions detection

3. **Implement Span Capture** (1.5h)
   - Create SPAN on HANDBACK receipt
   - Calculate cost_usd from tokens + model rates
   - Write to artifacts/{date}/SPAN-{timestamp}-{type}.yaml
   - Log routing decision, approval decision, escalations

**Deliverable:** Tasks validated by QE, spans captured, metrics logged

---

### Phase 4: Dead-Letter & Monitoring (2-3 hours)
**Goal:** Implement error handling, alerting, artifact indexing

1. **Implement Dead-Letter Queue** (1.5h)
   - Move invalid/failed tasks to dead-letter/
   - Write error logs with validation reasons
   - Daily alert if >5 items
   - Cleanup/archival strategy

2. **Implement Artifact Indexing** (1.5h)
   - Create artifacts/index.json generation in Model Engineer
   - Scan artifacts/2026-*/ for DELEGATE/HANDBACK/SPAN
   - Build searchable index by: file_type, task_id, agent_type, status
   - Calculate aggregations: total_tokens, total_cost, critical_issues, escalations

3. **End-to-End Testing** (1h)
   - Test 5 queued tasks through entire flow
   - Verify DELEGATE → routing → execution → QE → span → done/
   - Check dead-letter queue handling
   - Validate index.json accuracy

**Deliverable:** Complete queue-to-protocol pipeline working, metrics tracked

---

## AC10: Proper DELEGATE Specification

### How to Create a DELEGATE Task

A DELEGATE is a YAML file placed in ~/.agentic-engineers/queue/{session_id}/incoming/ that specifies a task to be executed by an agent.

#### File Format

File name: `{SESSION_ID}/incoming/{TASK_ID}.yaml`

Example: `local/incoming/TASK-QUEUE-PROTOCOL-INTEGRATION-002.yaml`

#### Minimal DELEGATE

```yaml
---
task_id: TASK-FEATURE-X-001
type: DELEGATE
role: engineer
model: claude-haiku-4.5
effort: high
priority: normal

context:
  description: |
    Add Redis caching to the GetUser endpoint.
    Context: Cache key = userID, TTL = 1 hour, max 10K entries.
  repo: github.com/company/repo
  branch: feature/redis-cache
  commit: HEAD
  files:
    - src/services/user_service.py

requirements:
  - Add cache decorator to GetUser endpoint
  - Implement cache invalidation on user update
  - Monitor hit ratio (target: >80%)

acceptance_criteria:
  - "AC1: Cache hit ratio >80% in load test"
  - "AC2: No test failures, existing behavior preserved"
  - "AC3: Response time <10ms for cache hits"

constraints:
  - "No breaking changes to API contract"
  - "Backward compatible with existing clients"

escalation_triggers:
  - "Change touches >3 files → Senior Engineer"
  - "Test failures after 2 attempts → Senior Engineer"

repro: "make test FILTER=test_user_service"

skill_refs:
  - src/skills/roles/engineer.md

token_budget: 3000
estimated_cost: 0.03
```

#### Complete DELEGATE with All Fields

```yaml
---
task_id: TASK-PAYMENT-REFACTOR-001
type: DELEGATE
role: senior-engineer
model: claude-sonnet-4.6
effort: high
priority: high
status: incoming
parent_task_id: null

context:
  description: |
    Refactor payment processing pipeline to support new payment gateway.
    Current: Stripe only. New: Support Stripe + PayPal + Square.
    See SPEC.md Section 4.2 for requirements.
  repo: github.com/company/payments-service
  branch: feature/multi-gateway
  commit: HEAD
  files:
    - src/payments/processor.py
    - src/payments/gateway.py
    - tests/test_payments.py
  line_refs:
    - "src/payments/processor.py:45-120"
    - "src/payments/gateway.py:1-80"

requirements:
  - "Support Stripe, PayPal, Square gateways"
  - "Implement gateway factory pattern"
  - "Maintain backward compatibility"
  - "All existing tests must pass"
  - "New tests for each gateway"

acceptance_criteria:
  - "AC1: All payment methods work end-to-end"
  - "AC2: Existing Stripe customers unaffected"
  - "AC3: Test coverage ≥90%"
  - "AC4: No production incidents in 48h"

constraints:
  - "Do not modify PaymentRequest public API"
  - "Maintain PCI compliance"
  - "No external dependencies without review"

dependencies:
  - TASK-PCI-AUDIT-001
  - TASK-GATEWAY-SETUP-001

escalation_triggers:
  - "Cross-service API changes → Lead Engineer"
  - "PCI compliance questions → Security Engineer"
  - "Debugging root cause >2 services → Principal Engineer"
  - "Any auth/crypto implications → Security Engineer"

repro: "CONFIG=dev make test FILTER=test_payments && make build"

skill_refs:
  - src/skills/roles/senior-engineer.md
  - src/skills/patterns/payment-integration.md

token_budget: 15000
estimated_cost: 0.12
created_at: "2026-05-30T10:00:00Z"
version: "1.0"
```

#### Required vs Optional Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `task_id` | YES | string | Kebab-case identifier, must be unique |
| `type` | YES | string | Must be "DELEGATE" |
| `role` | YES | string | Target role (engineer, senior-engineer, etc.) |
| `model` | YES | string | Model to use (claude-haiku-4.5, claude-sonnet-4.6, etc.) |
| `effort` | YES | string | low, medium, high, max |
| `priority` | YES | string | low, normal, high, urgent |
| `context.description` | YES | string | What needs to be done and why (≥50 words) |
| `requirements` | YES | array | List of specific requirements |
| `acceptance_criteria` | YES | array | List of measurable success criteria |
| `escalation_triggers` | YES | array | When to escalate (routes higher) |
| `repro` | YES | string | Command to verify work completed |
| `skill_refs` | YES | array | SKILL files to reference |
| `token_budget` | YES | integer | Max tokens for this task |
| `estimated_cost` | YES | number | Dollar estimate |
| **Optional fields below** |
| `status` | NO | string | incoming (default), processing, done, failed |
| `parent_task_id` | NO | string | Parent task for sub-task chaining |
| `context.repo` | NO | string | Repository URL |
| `context.branch` | NO | string | Git branch name |
| `context.commit` | NO | string | Git commit SHA or HEAD |
| `context.files` | NO | array | Relevant file paths |
| `context.line_refs` | NO | array | Specific line ranges |
| `constraints` | NO | array | Non-functional constraints |
| `dependencies` | NO | array | Task dependencies |
| `created_at` | NO | string | ISO timestamp |
| `version` | NO | string | Protocol version |

#### Examples by Role

**Example 1: Engineer (Haiku, well-scoped)**
```yaml
task_id: TASK-LINT-FIX-001
role: engineer
model: claude-haiku-4.5
effort: high
scope: Fix linting errors in src/utils/validator.py (15 lines, already identified)
```

**Example 2: Senior Engineer (Sonnet, planning required)**
```yaml
task_id: TASK-AUTH-REFACTOR-001
role: senior-engineer
model: claude-sonnet-4.6
effort: high
scope: Refactor authentication flow (currently scattered across 5 files)
requirements:
  - Consolidate auth logic into single module
  - Support OAuth2 + session tokens
```

**Example 3: Security Engineer (Opus, threat modeling)**
```yaml
task_id: TASK-SECURITY-AUDIT-001
role: security-engineer
model: claude-opus-4.8
effort: max
requirements:
  - Threat model using STRIDE
  - Check OWASP Top 10 vulnerabilities
  - Review secrets handling
```

---

## Summary Table: All Acceptance Criteria

| AC # | Criterion | Status | Location | Notes |
|------|-----------|--------|----------|-------|
| AC1 | Queue discovery | Design ✅ | SPEC.md + queue-management SKILL | Orchestrator polling loop not coded |
| AC2 | DELEGATE validation | Design ✅ | protocol-validator SKILL | Needs protocol-core-v1.0.yaml file |
| AC3 | Routing decision tree | Design ✅ | AGENTS.md + task-routing.md | Decision tree not implemented in code |
| AC4 | HANDBACK reception | Design ✅ | AGENTS.md | Orchestrator doesn't parse/handle HANDBACKs |
| AC5 | Quality gate | Design ⚠️ | AGENTS.md | QE SKILL missing; no approval logic |
| AC6 | Span capture | Design ✅ | SPEC.md Section 88-93 | No code to write SPANs |
| AC7 | Dead-letter queue | Design ✅ | SPEC.md Section 79-82 | No code to move tasks to DLQ |
| AC8 | Implementation gaps | Analysis ✅ | This document | 10 critical gaps identified |
| AC9 | Implementation roadmap | Design ✅ | This document, 4 phases | 15-20 hours total effort |
| AC10 | DELEGATE specification | Design ✅ | This document, examples | Minimal + complete templates |

---

## Key Decisions Made

1. **Spec-Core-v1.0.yaml Creation** — MUST create formal protocol spec file
2. **Session-Partitioned Queues** — Use COPILOT_SESSION_ID for isolation
3. **Polling Interval** — 30-60 seconds (balance responsiveness vs. overhead)
4. **Quality Gate Placement** — QE validates all HANDBACKs before done/ move
5. **Artifact Organization** — Date-based directory structure (artifacts/YYYY-MM-DD/)
6. **Cost Calculation** — Base on tokens_used + model rates (lookup table)
7. **Escalation Strategy** — Unclear scope → user escalation (not retry)

---

## Open Questions for Principal Engineer Review

1. **Session Detection** — Should we support CLAUDE_SESSION_ID env var fallback?
2. **Cost Rates** — Where are model pricing rates defined? (src/TOKEN_METRICS.md?)
3. **Effort Mapping** — How do effort tiers map to token estimates?
4. **Parallel Execution** — Can Orchestrator fan out multiple DELEGATEs simultaneously?
5. **Retry Logic** — Should failed tasks auto-retry or go straight to dead-letter?
6. **Webhook Integration** — Should agents support webhook callbacks for HANDBACK?
7. **Database vs Files** — Should we eventually migrate queue from files to SQLite?

---

## Conclusion

The agentic-engineers framework has strong protocol and specification design (AGENTS.md, SPEC.md, queue-management SKILL, protocol-validator SKILL). However, the **Orchestrator implementation is not yet complete**. This investigation identifies 10 specific implementation gaps and provides a 4-phase roadmap for implementation.

**Key takeaway:** Design is solid, but code needs to follow. The roadmap should take 15-20 hours to complete, resulting in a fully functional, auditable queue-to-protocol pipeline.

---

**Investigation Completed:** 2026-05-30
**Investigator:** Security Engineer (claude-opus-4.8)
**Task ID:** TASK-QUEUE-PROTOCOL-INTEGRATION-001
