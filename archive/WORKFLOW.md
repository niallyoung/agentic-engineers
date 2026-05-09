# Agentic Engineers Workflow — Agent Communication & Control Flow

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ENGINEERING WORK ARRIVES                            │
│                    (feature, bug, refactor, design, review)                 │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  GENERAL ORCHESTRATOR   │
                    │  (Task Router / Haiku)  │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              │        (6-POINT DECISION TREE)      │
              │                  │                  │
    ┌─────────▼─────────┐  ┌────▼────────┐  ┌─────▼────────┐
    │ SECURITY CRITICAL │  │ CROSS-SVC   │  │   CODE       │
    │                   │  │ ARCHITECTURE│  │   REVIEW     │
    │ Security Engineer │  │             │  │              │
    │     (Opus)        │  │ Principal   │  │ Lead Engineer│
    │                   │  │ Engineer    │  │   (Sonnet)   │
    │ HANDBACK:         │  │  (Opus)     │  │              │
    │ - threat_model    │  │             │  │ HANDBACK:    │
    │ - vulns/risks     │  │ HANDBACK:   │  │ - style_ok   │
    │ - severity_score  │  │ - arch_opts │  │ - patterns   │
    └─────────┬─────────┘  │ - roadmap   │  │ - maintainable
              │            │ - tradeoffs │  └─────┬────────┘
              │            └────┬───────┘        │
              │                 │                │
    ┌─────────▼────────────┐   │    ┌───────────▼──────────┐
    │  COMPLEX / UNSCOPED  │   │    │  SIMPLE / SCOPED     │
    │                      │   │    │   WITH PLAN          │
    │  Senior Engineer     │   │    │                      │
    │    (Sonnet)          │   │    │  Engineer (Haiku)    │
    │                      │   │    │                      │
    │ HANDBACK:            │   │    │ HANDBACK:            │
    │ - root_cause         │   │    │ - code_changes       │
    │ - solution_analysis  │   │    │ - tests_added        │
    │ - execution_plan     │   │    │ - quality_metrics    │
    │ - confidence: 0.88   │   │    │ - tokens_used        │
    └─────────┬────────────┘   │    └───────────┬──────────┘
              │                │                │
              │ (plan ready)   │                │ (work done)
              │                │                │
              └────────────────┼────────────────┘
                               │
                    ┌──────────▼───────────┐
                    │ QUALITY ORCHESTRATOR │
                    │  (Quality Master)    │
                    │    (Sonnet-4-6)      │
                    └──────────┬───────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │  PARALLEL
                │              │              │  DELEGATION
        ┌───────▼─────┐ ┌─────▼──────┐ ┌────▼────────┐
        │   Testing   │ │   Healing   │ │   Security  │
        │   Agent     │ │   Agent     │ │   Agent     │
        │  (Haiku)    │ │  (Sonnet)   │ │  (Opus)     │
        │             │ │             │ │             │
        │ HANDBACK:   │ │ HANDBACK:   │ │ HANDBACK:   │
        │ - tests_ok? │ │ - fixes_ok? │ │ - vulns_ok? │
        │ - coverage% │ │ - severity  │ │ - risk_score│
        │ - failures  │ │ - confidence│ │ - findings  │
        └───────┬─────┘ └─────┬──────┘ └────┬────────┘
                │             │             │
                │    ┌────────▼────────┐   │
                │    │   Metrics Agent │   │
                │    │   (Haiku)       │   │
                │    │                 │   │
                │    │ HANDBACK:       │   │
                │    │ - health_score  │   │
                │    │ - latency/error │   │
                │    │ - status: PASS  │   │
                │    └────────┬────────┘   │
                │             │             │
                └─────────────┼─────────────┘
                              │
                    ┌─────────▼──────────┐
                    │ AGGREGATE RESULTS  │
                    │                    │
                    │ If all PASS &      │
                    │ health >= 85:      │
                    │   → PROCEED        │
                    │                    │
                    │ If any FAIL or     │
                    │ health < 85:       │
                    │   → ESCALATE       │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │   FINAL DECISION   │
                    │  + AUDIT TRAIL     │
                    └────────────────────┘
```

---

## Example Flow: Feature Implementation with Quality Gate

### Scenario
Engineer commits a new feature: "Add OAuth token rotation to {service-name}"

```
═══════════════════════════════════════════════════════════════════════════════
STEP 1: WORK ARRIVES AT GENERAL ORCHESTRATOR
═══════════════════════════════════════════════════════════════════════════════

INPUT (DELEGATE block):
┌─────────────────────────────────────────────────────────────────────────────┐
│ task_id: 2026-04-30-feature-oauth-rotation                                  │
│ task_type: feature                                                          │
│ scope: "Add OAuth token rotation to {service-name}"                           │
│ context:                                                                    │
│   service: {service-name}                                                     │
│   files_changed: [lambda/auth/oauth_rotation.go, tests]                    │
│   estimated_complexity: high                                                │
│   has_plan: false                                                           │
│ timestamp: 2026-04-30T10:00:00Z                                             │
└─────────────────────────────────────────────────────────────────────────────┘

GENERAL ORCHESTRATOR DECISION TREE:
  • Security-scoped? NO
  • Cross-service architecture? NO
  • Code review task? NO
  • Complex + no plan? YES ← MATCH
  
ROUTING DECISION:
┌─────────────────────────────────────────────────────────────────────────────┐
│ → Route to: SENIOR ENGINEER (Sonnet-4-6)                                    │
│ → Reason: "Complex work without plan; need analysis + planning"             │
│ → Confidence: 0.88                                                          │
│ → Action: DELEGATE                                                          │
└─────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
STEP 2: SENIOR ENGINEER ANALYZES & PLANS
═══════════════════════════════════════════════════════════════════════════════

SENIOR ENGINEER receives DELEGATE:
  • Analyzes OAuth rotation requirements
  • Examines current DynamoDB idempotency implementation
  • Identifies potential race conditions in token lock
  • Compares 3 solution approaches:
    - Option 1: UpdateItem with atomic counter
    - Option 2: SNS FIFO MessageDeduplicationId (RECOMMENDED)
    - Option 3: DynamoDB Transactions
  • Creates detailed 6-phase execution plan (270 min estimated)
  • Assigns confidence: 0.95

HANDBACK to General Orchestrator:
┌─────────────────────────────────────────────────────────────────────────────┐
│ task_id: 2026-04-30-feature-oauth-rotation                                  │
│ status: analysis_complete_ready_for_execution                               │
│ agent: Senior Engineer                                                      │
│                                                                             │
│ root_cause_analysis:                                                        │
│   problem: Race condition in DDB idempotency lock                           │
│   root_cause: Conditional write has race window                            │
│   impact: Events processed 2-3x; data consistency issues                   │
│                                                                             │
│ solution_analysis:                                                          │
│   recommended_solution: "Option 2: SNS FIFO MessageDeduplicationId"        │
│   confidence: 0.95                                                          │
│   estimated_effort: 270 minutes                                             │
│                                                                             │
│ execution_plan:                                                             │
│   phases:                                                                   │
│     1. Understand SNS FIFO setup (30 min)                                   │
│     2. Design SNS dedup integration (45 min)                                │
│     3. Modify consumer (60 min)                                             │
│     4. Update idempotency logic (45 min)                                    │
│     5. Testing (60 min)                                                     │
│     6. Performance validation (30 min)                                      │
│                                                                             │
│ success_criteria:                                                           │
│   - Race condition eliminated (0 duplicate processing)                      │
│   - Event processed exactly once per SNS dedup ID                          │
│   - No performance regression (latency within 5% of baseline)              │
│   - Unit tests passing (>80% coverage)                                      │
│   - Concurrency tests passing (10 concurrent invocations)                   │
│   - Dev smoke test successful                                               │
│                                                                             │
│ assigned_agent: Engineer (Haiku-4-5)                                        │
└─────────────────────────────────────────────────────────────────────────────┘

GENERAL ORCHESTRATOR re-routes to ENGINEER with plan:
  → "Plan complete; execute this implementation"
  → Confidence: 0.93

═══════════════════════════════════════════════════════════════════════════════
STEP 3: ENGINEER EXECUTES PLANNED WORK
═══════════════════════════════════════════════════════════════════════════════

ENGINEER receives DELEGATE with detailed plan:
  • Phase 1: Reads SNS FIFO config, verifies deduplication enabled
  • Phase 2: Designs MessageDeduplicationId mapping
  • Phase 3: Modifies lambda/consumer/event_handler.go
  • Phase 4: Simplifies idempotency logic
  • Phase 5: Writes unit + integration + concurrency tests
  • Phase 6: Validates performance (no regression)
  • Runs: make test, make build

HANDBACK to Quality Orchestrator:
┌─────────────────────────────────────────────────────────────────────────────┐
│ task_id: 2026-04-30-feature-oauth-rotation                                  │
│ status: complete                                                            │
│ agent: Engineer (Haiku)                                                     │
│                                                                             │
│ deliverables:                                                               │
│   code:                                                                     │
│     - file: "lambda/auth/oauth_rotation.go"                                │
│       lines: 128                                                            │
│     - file: "lambda/auth/oauth_rotation_test.go"                           │
│       lines: 156                                                            │
│                                                                             │
│ tests:                                                                      │
│   coverage: 87%                                                             │
│   tests_passed: 24                                                          │
│   tests_failed: 0                                                           │
│   duration: 2.3s                                                            │
│                                                                             │
│ quality_metrics:                                                            │
│   code_quality: 9/10                                                        │
│   test_quality: 9/10                                                        │
│   documentation: 9/10                                                       │
│   overall: 92/100                                                           │
│                                                                             │
│ execution_notes:                                                            │
│   actual_duration: 268 minutes (vs 270 planned)                            │
│   tokens_used: 2380 (vs 2500 budget)                                        │
│   lint_violations: 0                                                        │
│   complexity_delta: -0.05 (simpler than expected)                          │
│                                                                             │
│ files_changed:                                                              │
│   lambda/auth/oauth_rotation.go                                             │
│   lambda/auth/oauth_rotation_test.go                                        │
│   lambda/models/message_dedup_id.go (new)                                   │
│   internal/consumer/idempotency_v2.go                                       │
│                                                                             │
│ confidence: 0.96                                                            │
└─────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
STEP 4: QUALITY ORCHESTRATOR COORDINATES QUALITY GATES
═══════════════════════════════════════════════════════════════════════════════

QUALITY ORCHESTRATOR spawns 4 PARALLEL DELEGATES:

┌─────────────────────────────────────────────────────────────────────────────┐
│                     PARALLEL DELEGATION (async)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ┌─TESTING AGENT──────────────────────────────────────────────────────────┐ │
│ │ DELEGATE:                                                              │ │
│ │   service: {service-name}                                               │ │
│ │   commit_sha: abc123def456                                            │ │
│ │   action: run_tests_measure_coverage                                  │ │
│ │                                                                        │ │
│ │ PROCESS:                                                              │ │
│ │   $ make test                                                         │ │
│ │   $ measure coverage                                                  │ │
│ │                                                                        │ │
│ │ HANDBACK:                                                             │ │
│ │   status: PASS                                                        │ │
│ │   tests_passed: 24/24                                                │ │
│ │   coverage: 87%                                                       │ │
│ │   flaky_tests: 0                                                      │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─HEALING AGENT──────────────────────────────────────────────────────────┐ │
│ │ DELEGATE:                                                              │ │
│ │   service: {service-name}                                               │ │
│ │   changes: [oauth_rotation.go, idempotency_v2.go]                    │ │
│ │   action: detect_and_autofix_issues                                   │ │
│ │                                                                        │ │
│ │ PROCESS:                                                              │ │
│ │   $ golangci-lint ./lambda/auth/                                      │ │
│ │   $ check config files                                                │ │
│ │   $ verify retry logic                                                │ │
│ │                                                                        │ │
│ │ HANDBACK:                                                             │ │
│ │   status: PASS                                                        │ │
│ │   issues_found: 0                                                     │ │
│ │   fixes_applied: 0                                                    │ │
│ │   severity: NONE                                                      │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─SECURITY AGENT─────────────────────────────────────────────────────────┐ │
│ │ DELEGATE:                                                              │ │
│ │   service: {service-name}                                               │ │
│ │   commit_sha: abc123def456                                            │ │
│ │   action: threat_model + scan                                         │ │
│ │                                                                        │ │
│ │ PROCESS:                                                              │ │
│ │   • STRIDE threat model on SNS FIFO dedup logic                       │ │
│ │   • Scan for hardcoded credentials                                    │ │
│ │   • Verify TLS on SNS messages                                        │ │
│ │   • Check authorization on token rotation endpoint                    │ │
│ │                                                                        │ │
│ │ HANDBACK:                                                             │ │
│ │   status: PASS                                                        │ │
│ │   credentials_found: 0                                                │ │
│ │   vulnerabilities: 0                                                  │ │
│ │   threat_model_risks: []                                              │ │
│ │   severity: NONE                                                      │ │
│ │   confidence: 0.98                                                    │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─METRICS AGENT──────────────────────────────────────────────────────────┐ │
│ │ DELEGATE:                                                              │ │
│ │   service: {service-name}                                               │ │
│ │   baseline: latency=120ms, error_rate=0.1%                            │ │
│ │   action: measure_system_health                                       │ │
│ │                                                                        │ │
│ │ PROCESS:                                                              │ │
│ │   • Measure p99 latency                                               │ │
│ │   • Measure error rate                                                │ │
│ │   • Measure resource usage                                            │ │
│ │   • Calculate health score                                            │ │
│ │                                                                        │ │
│ │ HANDBACK:                                                             │ │
│ │   status: PASS                                                        │ │
│ │   health_score: 92/100                                                │ │
│ │   p99_latency_ms: 118 (vs 120 baseline)                              │ │
│ │   error_rate: 0.09% (vs 0.1% baseline)                               │ │
│ │   severity: NONE                                                      │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

QUALITY ORCHESTRATOR AGGREGATES RESULTS:
┌─────────────────────────────────────────────────────────────────────────────┐
│ Testing:    PASS (24/24 tests, 87% coverage)                               │
│ Healing:    PASS (0 issues, 0 fixes)                                       │
│ Security:   PASS (0 vulns, 0 credentials)                                  │
│ Metrics:    PASS (health 92/100 ≥ 85 threshold)                            │
│                                                                             │
│ DECISION LOGIC:                                                             │
│   all_pass = (T:✓ AND H:✓ AND S:✓ AND M:✓)                               │
│   health_ok = (92 ≥ 85) ✓                                                  │
│   → FINAL_DECISION: PROCEED ✓                                              │
│   → CONFIDENCE: 0.95                                                        │
└─────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
STEP 5: QUALITY ORCHESTRATOR RETURNS HANDBACK
═══════════════════════════════════════════════════════════════════════════════

HANDBACK (Quality Orchestrator → General Orchestrator):
┌─────────────────────────────────────────────────────────────────────────────┐
│ task_id: 2026-04-30-feature-oauth-rotation                                  │
│ timestamp: 2026-04-30T15:30:00Z                                             │
│ status: complete                                                            │
│ final_decision: PROCEED                                                     │
│ confidence: 0.95                                                            │
│                                                                             │
│ audit_trail:                                                                │
│   testing:                                                                  │
│     status: PASS                                                            │
│     unit_tests: 24                                                          │
│     unit_failures: 0                                                        │
│     coverage: 87%                                                           │
│   healing:                                                                  │
│     status: PASS                                                            │
│     fixes_attempted: 0                                                      │
│     fixes_succeeded: 0                                                      │
│     escalations: []                                                         │
│   security:                                                                 │
│     status: PASS                                                            │
│     findings: 0                                                             │
│     severity_max: NONE                                                      │
│     confidence: 0.98                                                        │
│   metrics:                                                                  │
│     status: PASS                                                            │
│     health_score: 92                                                        │
│     p99_latency_ms: 118                                                     │
│     error_rate: 0.09%                                                       │
│                                                                             │
│ recommendation: |                                                           │
│   All quality gates passed. Code ready for merge to main.                  │
│   Security verified. Performance optimized. Tests comprehensive.            │
│                                                                             │
│ escalation_reasons: []                                                      │
│ next_step: "Lead Engineer code review → merge → deploy"                    │
└─────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
STEP 6: OPTIONAL - LEAD ENGINEER CODE REVIEW (if needed)
═══════════════════════════════════════════════════════════════════════════════

If quality gate flagged any review concerns, or organization policy requires:

LEAD ENGINEER receives task:
  • Reviews code style, patterns, architectural fit
  • Verifies error handling completeness
  • Checks performance characteristics
  • Validates security assumptions

HANDBACK:
  status: APPROVED | APPROVE_WITH_SUGGESTIONS | REWORK | ESCALATE
  review_score: 9/10
  notes: "Clean implementation, consistent with codebase patterns"

═══════════════════════════════════════════════════════════════════════════════
FINAL STATE: MERGE & DEPLOY
═══════════════════════════════════════════════════════════════════════════════

Workflow complete:
  ✓ Work analyzed by Senior Engineer → plan created
  ✓ Plan executed by Engineer → deliverables
  ✓ Quality gates checked by Testing, Healing, Security, Metrics agents
  ✓ Decision: PROCEED (all gates pass)
  ✓ Code ready for merge
  ✓ CI/CD deploys to dev/prod
  ✓ Monitoring enabled

Total time: ~4.5 hours (planning + execution + quality gates)
Total tokens: ~4,800 (2500 planning + 2380 execution + 1000 quality checks)
Quality score: 92/100
Confidence: 0.95
```

---

## Agent Communication Protocol

### DELEGATE Block (Input to Agent)

```yaml
---
handoff_type: DELEGATE
task_id: unique-task-identifier
timestamp: 2026-04-30T10:00:00Z

# What is this task about?
role: senior_engineer | engineer | security_engineer | etc.
scope: "Human-readable description of work"
task_type: feature | bugfix | refactor | design | review

# Context for the agent
context:
  service: {service-name}
  files_changed: [list of files]
  error_logs: [if applicable]
  constraints: [technical constraints]
  
# For scoped/planned work
has_plan: true | false
estimated_complexity: low | medium | high
execution_plan: [if has_plan == true]

# Budget/resources
token_budget: 2500
time_budget_minutes: 170
---
```

### HANDBACK Block (Output from Agent)

```yaml
---
handoff_type: HANDBACK
task_id: unique-task-identifier
timestamp: 2026-04-30T15:30:00Z
status: complete | analysis_complete_ready_for_execution | escalate

# What did the agent produce?
deliverables:
  code: [files created/modified]
  tests: [test files, coverage, pass/fail]
  documentation: [READMEs, comments]
  plan: [if analysis agent]

# Quality metrics
quality_metrics:
  score: 92/100
  code_quality: 9/10
  test_quality: 9/10
  no_regressions: true
  
# Resource usage
execution_notes:
  actual_duration: 268
  planned_duration: 270
  tokens_used: 2380
  token_budget: 2500
  
# Confidence in result
confidence: 0.96

# Next step
next_step: "Lead Engineer code review → merge"
escalation_reasons: [] | [if status == escalate]
---
```

### Communication Flow Rules

1. **DELEGATE Always Flows Downward**
   - General Orchestrator → Senior Engineer / Engineer / Security Engineer / etc.
   - Senior Engineer → Engineer (with plan)
   - Quality Orchestrator → Testing / Healing / Security / Metrics agents

2. **HANDBACK Always Flows Upward**
   - Agent → Orchestrator that sent DELEGATE
   - Orchestrator aggregates HANDBACKs from parallel agents
   - Final HANDBACK includes audit trail from all sub-agents

3. **No Lateral Communication**
   - Agents don't communicate directly with peers
   - All communication via orchestrator delegation

4. **Timeouts & Error Handling**
   - Quality Orchestrator timeout: 5 minutes (any agent timeout = ESCALATE)
   - If sub-agent fails: include error in HANDBACK, set severity HIGH
   - Orchestrator aggregates failures into escalation reason

---

## Decision Points in Flow

| Decision Point | Logic | Outcome |
|---|---|---|
| **General Orchestrator Routes** | 6-point decision tree on task type | Route to appropriate agent (Security, Principal, Lead, Senior, Engineer, Quality) |
| **Senior Engineer Plans** | Analyzes complexity, designs solutions | HANDBACK with plan + confidence |
| **Engineer Executes** | Follows plan or executes scoped work | HANDBACK with code + quality metrics |
| **Quality Orchestrator Aggregates** | All 4 sub-agents return results | PROCEED (all pass + health ≥85) or ESCALATE (any fail) |
| **Lead Engineer Reviews** | Spot-checks code against repo style | APPROVE / APPROVE_WITH_SUGGESTIONS / REWORK / ESCALATE |
| **Merge Decision** | Quality + Review gates pass | Ready for merge to main |

