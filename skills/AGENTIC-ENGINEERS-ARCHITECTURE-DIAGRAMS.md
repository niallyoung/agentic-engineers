---
name: Agentic Engineers Architecture Diagrams
description: Comprehensive ASCII diagrams showing SDLC flow, agent coordination, and quality gates
type: architecture-diagrams
date: 2026-04-28
---

# Agentic Engineers Architecture Diagrams

Complete visual reference for how the agentic-engineers framework orchestrates quality gates, routes tasks, and coordinates multi-agent workflows.

---

## 1. FULL SDLC WORKFLOW WITH QUALITY GATE LOOP

Example: Credential Detection & Escalation

```
                                 Developer
                                    │
                                    ↓
                    ┌───────────────────────────────┐
                    │  Edit Code + Commit           │
                    │  feat: add auth handler       │
                    │  (with hardcoded secret ⚠️)   │
                    └───────────────────┬───────────┘
                                        │
                                        ↓
                    ┌───────────────────────────────┐
                    │  Pre-Commit Hook              │
                    │  • lint ✅                    │
                    │  • test ✅                    │
                    │  • commit-msg ✅             │
                    └───────────────────┬───────────┘
                                        │
                                        ↓
                    ┌───────────────────────────────┐
                    │  git push                     │
                    │  ↓                            │
                    │  Pre-Push Hook                │
                    │  • E2E tests ✅               │
                    │  • quality gates ⏳           │
                    └───────────────────┬───────────┘
                                        │
                    ┌───────────────────┴──────────────────┐
                    │                                      │
                    ↓                                      ↓
        ┌──────────────────┐                  ┌──────────────────┐
        │ Quality Pass ✅  │                  │ Quality FAIL ❌  │
        │ → Proceed        │                  │ Hardcoded Secret │
        │   to GitHub      │                  └────────┬─────────┘
        │   Actions        │                           │
        └──────────────────┘                           ↓
                    │                    ┌──────────────────────────────┐
                    │                    │ QUALITY GATE WORKFLOW        │
                    │                    │ (quality-gate-orchestration) │
                    │                    └──────────────────────────────┘
                    │                                   │
                    │          ┌────────────────────────┴────────────────────┐
                    │          │                                             │
                    │          ↓                                             ↓
                    │    ┌──────────────┐                          ┌──────────────────┐
                    │    │ PHASE 1      │                          │ PHASE 2: DECISION│
                    │    │ Parallel     │                          │                  │
                    │    │ Checks       │──────────────────────→   │ Issues Found? ❌ │
                    │    │              │                          │ → Go to Phase 3  │
                    │    │ • Tests      │                          └────────┬─────────┘
                    │    │ • Security   │                                   │
                    │    │ • Compliance │                                   ↓
                    │    │              │                          ┌──────────────────┐
                    │    │ 🔴 FOUND:    │                          │ PHASE 3: HEAL    │
                    │    │ Credential   │                          │                  │
                    │    │ Pattern      │                          │ For each issue:  │
                    │    │ (WARN)       │                          │                  │
                    │    └──────────────┘                          │ 1. Diagnose      │
                    │                                              │    (confidence   │
                    │                                              │     + risk)      │
                    │                                              │                  │
                    │                                              │ 2. Route:        │
                    │                                              │    HIGH + LOW    │
                    │                                              │    → Healer      │
                    │                                              │    LOW + HIGH    │
                    │                                              │    → Escalate    │
                    │                                              │                  │
                    │                                              │ 3. Re-validate   │
                    │                                              │                  │
                    │                                              └────────┬─────────┘
                    │                                                       │
                    │          ┌────────────────────┬───────────────────────┘
                    │          │                    │
                    │          ↓ (Secret = WARN,    ↓ (No auto-fix for
                    │          no auto-fix needed) │  security issues)
                    │                              │
                    │          ESCALATE to          ESCALATE to
                    │          Security Engineer    Security Engineer
                    │          (HIGH risk)          (create review issue)
                    │                              │
                    │                              ↓
                    │                    ┌──────────────────────────┐
                    │                    │ PHASE 4: Final Decision  │
                    │                    │                          │
                    │                    │ Decision: ESCALATE ⚠️    │
                    │                    │ (Security review needed) │
                    │                    └────────────┬─────────────┘
                    │                                 │
                    └─────────────┬───────────────────┘
                                  │
                        ┌─────────┴──────────┐
                        │                    │
                        ↓                    ↓
            ┌──────────────────┐  ┌──────────────────┐
            │ GitHub Actions   │  │ Security Engineer│
            │ Quality Gate Job │  │ Reviews PR ✓     │
            │                  │  │ Approves Fix     │
            │ Status: PASS ✅  │  │ or Requests      │
            │ (assuming fix    │  │ Changes          │
            │  approved)       │  └────────┬─────────┘
            └────────┬─────────┘           │
                     │                    │
                     ↓                    ↓
            ┌──────────────────┐  ┌──────────────────┐
            │ deploy-prod      │  │ Developer Fixes  │
            │ Deployment ✅    │  │ Remove Hardcoded │
            │                  │  │ Secret           │
            │ Live in Prod ✓   │  │ git push again   │
            └──────────────────┘  └────────┬─────────┘
                     ▲                     │
                     └─────────────────────┘
```

---

## 2. ORCHESTRATOR COMPONENT & AGENT COORDINATION DIAGRAM

Task routing, agent selection, and delegation flow.

```
                              ┌─────────────────────┐
                              │  User (Developer)   │
                              │  Gives task         │
                              └──────────┬──────────┘
                                         │
                                         ↓
                        ┌────────────────────────────────┐
                        │   ORCHESTRATOR (Haiku)         │
                        │   Task Routing & Coordination  │
                        │                                │
                        │  Skills Used:                  │
                        │  • todo-management.md          │
                        │  • task-routing.md             │
                        │  • metrics-collection.md       │
                        │  • cicd-watch.md               │
                        └────────────┬───────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
          1. Check Task        2. Route Task     3. Monitor
          Routing Decision   To Right Agent      Progress
                │                │                │
                ↓                ↓                ↓
    ┌───────────────────┐  ┌──────────────────┐  ┌──────────────┐
    │  Complexity?      │  │  Select Agent:   │  │ Run Quality  │
    │  • Low → Engineer │  │ • Haiku Engineer │  │ Gate Monitor │
    │  • Med → Senior   │  │ • Sonnet Senior  │  │ (cicd-watch) │
    │  • High → Lead    │  │ • Opus Principal │  │              │
    │  • Complex → Opus │  │                  │  │ Track: ✅/❌ │
    └───────────────────┘  └────────┬─────────┘  └──────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
            ↓                       ↓                       ↓
    ┌──────────────┐       ┌──────────────┐       ┌──────────────────┐
    │  ENGINEER    │       │ SENIOR       │       │  LEAD/PRINCIPAL  │
    │  (Haiku)     │       │ ENGINEER     │       │  (Opus)          │
    │              │       │ (Sonnet)     │       │                  │
    │ High-Effort: │       │              │       │ Responsibilities:│
    │ • Implement  │       │ Effort:      │       │ • Architecture   │
    │ • Test       │       │ • Design     │       │ • Cross-service  │
    │ • Doc        │       │ • Plan       │       │ • Escalations    │
    │              │       │ • Implement  │       │ • Decisions      │
    │ Cost: Low ✓  │       │ • Test       │       │                  │
    │              │       │              │       │ Cost: High       │
    │ Models: L    │       │ Cost: Medium │       │ Models: O        │
    └──────┬───────┘       └──────┬───────┘       └────────┬─────────┘
           │                      │                        │
           │    ┌────────────────┬┴────────────┬──────────┐│
           │    │                │             │          ││
           │    ↓                ↓             ↓          ↓│
           │  ┌──────┐        ┌──────┐   ┌──────────┐  ┌──────┐
           │  │Skills│        │Skills│   │  Skills  │  │Priv. │
           │  │Used: │        │Used: │   │  Used:   │  │Agent │
           │  │      │        │      │   │          │  │Ops   │
           │  │ Impl │        │ Plan │   │ Security │  │only  │
           │  │ Test │        │ Code │   │ Review   │  │      │
           │  │ Doc  │        │ Review   │ Ops      │  │      │
           └──┤      │        │      │   │ Design   │  └──────┘
              └──────┘        └──────┘   └──────────┘


                         ↓ DELEGATION FLOW ↓

    ┌─────────────────────────────────────────────────────┐
    │  DELEGATE Markup (JSON):                            │
    │  {                                                  │
    │    "role": "Engineer",                              │
    │    "model": "claude-haiku-4-5",                     │
    │    "effort": "high",                                │
    │    "budget_context": {                              │
    │      "session_percent": 45,                         │
    │      "hours_to_reset": 12,                          │
    │      "recommendation": "Haiku safe"                 │
    │    },                                               │
    │    "scope": "Implement feature X",                  │
    │    "acceptance_criteria": [...]                     │
    │  }                                                  │
    └────────┬────────────────────────────────────────────┘
             │
             ↓
    ┌─────────────────────────────────────────────────────┐
    │  AGENT EXECUTES TASK                                │
    │  • Reads CLAUDE.md for project context              │
    │  • Accesses skills from                             │
    │    agentic-engineers/skills/                        │
    │  • Performs work                                    │
    │  • Collects metrics                                 │
    └────────┬────────────────────────────────────────────┘
             │
             ↓
    ┌─────────────────────────────────────────────────────┐
    │  HANDBACK Markup (JSON):                            │
    │  {                                                  │
    │    "status": "COMPLETE" | "BLOCKED",                │
    │    "result": "...",                                 │
    │    "metrics": {                                     │
    │      "tokens_used": 5234,                           │
    │      "duration_minutes": 23,                        │
    │      "files_changed": 4                             │
    │    },                                               │
    │    "blockers": [...] (if any)                       │
    │  }                                                  │
    └────────┬────────────────────────────────────────────┘
             │
             ↓
    ┌─────────────────────────────────────────────────────┐
    │  ORCHESTRATOR RECEIVES HANDBACK                     │
    │  • Update TODO.md (task DONE)                       │
    │  • Record metrics to ~/.claude/metrics/             │
    │  • Check for blockers                               │
    │  • If blocked: Route to next agent                  │
    │  • If complete: Return to user                      │
    └─────────────────────────────────────────────────────┘
```

---

## 3. SEQUENCE DIAGRAM: Quality Gate Flow

Credential detection → Escalation → Developer fix → Re-validation.

```
Developer        Orchestrator         Quality Gate         Issue Diagnostic        Security
   │                  │                    │                   Engine              Engineer
   │                  │                    │                      │                   │
   │  Commit + Push   │                    │                      │                   │
   ├─────────────────>│                    │                      │                   │
   │                  │                    │                      │                   │
   │                  │ PHASE 1: Run Tests,Security,Compliance   │                   │
   │                  ├───────────────────>│                      │                   │
   │                  │                    │ • test-unit.md       │                   │
   │                  │                    │ • test-integration.md│                   │
   │                  │                    │ • test-e2e.md       │                   │
   │                  │                    │ • security-semantic.md                  │
   │                  │                    │ • security-dependency.md               │
   │                  │                    │ • security-secret.md │                   │
   │                  │                    │ • requirement-verify.md │               │
   │                  │                    │ • spec-compliance.md │                   │
   │                  │                    │                      │                   │
   │                  │                    ├──────────────────────┤                   │
   │                  │                    │  FOUND: Hardcoded    │                   │
   │                  │                    │  AWS Credential      │                   │
   │                  │                    │  Type: WARN          │                   │
   │                  │                    │  Severity: HIGH RISK │                   │
   │                  │                    │<──────────────────────                   │
   │                  │<───────────────────┤                      │                   │
   │                  │ Results: FAIL      │                      │                   │
   │                  │                    │                      │                   │
   │                  │ PHASE 2: Decision? │                      │                   │
   │                  │ Issues found? YES  │                      │                   │
   │                  │ → Go to Phase 3    │                      │                   │
   │                  │                    │                      │                   │
   │                  │ PHASE 3: Analyze Issue for Healing        │                   │
   │                  ├───────────────────────────────────────────>│                   │
   │                  │                    │                      │ Analyze:          │
   │                  │                    │                      │ • Root Cause:     │
   │                  │                    │                      │   security_finding│
   │                  │                    │                      │ • Confidence: HIGH│
   │                  │                    │                      │ • Risk Level: HIGH│
   │                  │                    │                      │ • Auto-fix? NO    │
   │                  │                    │                      │   (high risk)     │
   │                  │<───────────────────────────────────────────┤                   │
   │                  │ Result: Escalate   │                      │                   │
   │                  │ (not eligible for  │                      │                   │
   │                  │  Healer auto-fix)  │                      │                   │
   │                  │                    │                      │                   │
   │                  │ PHASE 4: Final Decision                   │                   │
   │                  │ Type: SECURITY_ISSUE                      │                   │
   │                  │ Decision: ESCALATE ┼───────────────────────────────────────>│
   │                  │ Target: Security Engineer                 │                   │
   │                  │ Reason: Hardcoded credential needs        │                   │
   │                  │         expert review                     │                   │
   │                  │                    │                      │                   │
   │                  │ GitHub Actions Job Status: FAIL ❌        │                   │
   │                  │ Blocks deploy-prod                        │                   │
   │                  │                    │                      │                   │
   │ ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←│                   │
   │ GitHub Actions Notification:                                │                   │
   │ Quality gates FAILED                  │                      │                   │
   │ Prod deployment BLOCKED               │                      │                   │
   │                    │                    │                      │                   │
   │                    │                    │                      │         Reviews & Requests Changes
   │                    │                    │                      │                   │
   │  Developer removes hardcoded secret    │                      │                   │
   │  git push                              │                      │                   │
   ├─────────────────────────────────────────────────────────────────────────────────>│
   │                  │                    │                      │                   │
   │                  │ (CYCLE REPEATS)    │                      │                   │
   │                  │ PHASE 1: Tests,    │                      │                   │
   │                  │ Security, Compliance
   │                  ├───────────────────>│                      │                   │
   │                  │ • All tests: PASS ✅                      │                   │
   │                  │ • Security: PASS ✅ (credential removed)   │                   │
   │                  │ • Compliance: PASS ✅                      │                   │
   │                  │                    │                      │                   │
   │                  │ PHASE 2: Decision? │                      │                   │
   │                  │ All checks GREEN   │                      │                   │
   │                  │ → PROCEED ✅       │                      │                   │
   │                  │                    │                      │                   │
   │                  │ PHASE 4: Final     │                      │                   │
   │                  │ Decision: PROCEED  │                      │                   │
   │                  │                    │                      │                   │
   │ GitHub Actions: PASS ✅               │                      │                   │
   │ Prod deployment: PROCEED ✓            │                      │                   │
   │ Live in Production ✓                  │                      │                   │
   │                    │                    │                      │                   │
```

---

## 4. QUALITY GATE SKILL ECOSYSTEM

How quality-gate-orchestration coordinates 12 sub-skills in parallel.

```
                        quality-gate-orchestration
                       (Master Orchestrator Skill)
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
              PHASE 1:        PHASE 2:        PHASE 3:        PHASE 4:
            PARALLEL        INITIAL         SELF-HEALING     FINAL
            CHECKS          GATE            LOOP             DECISION
              │             DECISION         │                 │
              │               │              │                 │
    ┌─────────┼─────────┐    │        ┌──────┼──────┐        │
    │         │         │    │        │             │        │
    ↓         ↓         ↓    ↓        ↓             ↓        ↓
┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐
│TESTING │ │SECURITY│ │COMPLIANCE All        │ Issue    │ │ESCALATE│
│Layer   │ │Layer   │ │Layer    GREEN?       │ Diag.    │ │Decision│
└────────┘ └────────┘ └────────┘ │          │ Engine   │ │        │
    │         │         │         │ YES→    └──────────┘ └────────┘
    │         │         │         │ PROCEED        │
    │         │         │         │                ↓
    │         │         │         │         ┌──────────────┐
    │         │         │         │         │Healer Engineer
    │         │         │         │  NO→    │              │
    │         │         │         │  PHASE3 │• Analyze fix │
    │         │         │         │         │• Create PR   │
    ↓         ↓         ↓         ↓         │• Auto-merge? │
 ┌────────┐ ┌────────┐ ┌──────────────────┐ └──────────────┘
 │test-   │ │security│ │requirement-      │
 │unit-   │ │semantic│ │mapping.md        │
 │orch.md │ │-scan   │ │& verification    │
 └────────┘ └────────┘ └──────────────────┘

 ┌────────┐ ┌────────┐ ┌──────────────────┐
 │test-   │ │security│ │spec-compliance   │
 │integration  │dependency │-verification  │
 │-orch.md│ │-scan   │ │.md               │
 └────────┘ └────────┘ └──────────────────┘

 ┌────────┐ ┌────────┐
 │test-   │ │security│
 │e2e-    │ │secret- │
 │orch.md │ │detection│
 └────────┘ └────────┘

 ┌────────┐
 │test-   │
 │business│
 │-logic  │
 └────────┘


          ↓ SUB-AGENT COORDINATION ↓

    If Issue Found & Eligible for Healing:
    
    ┌───────────────────────────────────────┐
    │ issue-diagnostic-engine.md            │
    │ INPUT: {findings, issue_type}         │
    │ OUTPUT:                               │
    │  • root_cause: "dependency_conflict"  │
    │  • confidence: "HIGH"                 │
    │  • risk_level: "LOW"                  │
    │  • suggested_fix: "..."               │
    │  • auto_fixable: true                 │
    └───────────────────┬───────────────────┘
                        │
        ┌───────────────┴──────────────┐
        │                              │
   HIGH + LOW              LOW + HIGH
   (Auto-Fix)            (Escalate)
        │                    │
        ↓                    ↓
   ┌──────────────┐     ┌────────────┐
   │healer-       │     │Escalate to │
   │engineer.md   │     │Human       │
   │              │     │(Lead/Sec)  │
   │• Creates PR  │     │            │
   │• Auto-merges │     │            │
   │• Re-validates│     │            │
   └──────────────┘     └────────────┘
```

---

## 5. ORCHESTRATOR ROUTING TABLE

Agent selection based on task complexity and scope.

```
TASK COMPLEXITY  │ SCOPE CLEAR? │ ARCHITECTURAL? │ ROUTED TO      │ MODEL
─────────────────┼──────────────┼────────────────┼────────────────┼──────────
Low              │ YES          │ NO             │ Engineer       │ Haiku
                 │              │                │ (High Effort)  │ Low Cost
─────────────────┼──────────────┼────────────────┼────────────────┼──────────
Medium           │ YES          │ NO             │ Engineer       │ Haiku
                 │              │                │ (High Effort)  │ Low Cost
─────────────────┼──────────────┼────────────────┼────────────────┼──────────
Medium           │ NO           │ YES            │ Senior         │ Sonnet
                 │              │                │ Engineer       │ Medium
─────────────────┼──────────────┼────────────────┼────────────────┼──────────
High             │ YES          │ Single Svc     │ Senior         │ Sonnet
                 │              │                │ Engineer       │ Medium
─────────────────┼──────────────┼────────────────┼────────────────┼──────────
High             │ YES          │ Cross-Svc     │ Lead           │ Sonnet
                 │              │ Tactical       │ Engineer       │ Medium
─────────────────┼──────────────┼────────────────┼────────────────┼──────────
High             │ YES          │ Cross-Svc     │ Principal      │ Opus
                 │              │ Strategic      │ Engineer       │ High Cost
─────────────────┼──────────────┼────────────────┼────────────────┼──────────
ANY              │ NO           │ ANY            │ Human          │ —
                 │              │                │ (Clarify)      │ —
```

---

## 6. ORCHESTRATOR TASK LIFECYCLE

Complete cycle from user input to completion.

```
User Input
   │
   ├─→ TODO.md: Add task (pending)
   │
   ↓
Orchestrator routes task
   │
   ├─→ Consult task-routing.md decision tree
   ├─→ Select role (Engineer/Senior/Lead/Principal)
   ├─→ Select model (Haiku/Sonnet/Opus)
   ├─→ Create DELEGATE markup
   ├─→ TODO.md: Task = IN_PROGRESS
   │
   ↓
Spawn Agent with DELEGATE context
   │
   ├─→ Agent reads CLAUDE.md (project context)
   ├─→ Agent accesses skills/ directory
   ├─→ Agent executes task
   ├─→ Agent collects metrics (tokens, time, files)
   │
   ↓
Agent completes or hits blocker
   │
   ├─→ Create HANDBACK markup (status, result, metrics)
   ├─→ Return to Orchestrator
   │
   ↓
Orchestrator receives HANDBACK
   │
   ├─→ TODO.md: Task = DONE (with timestamp)
   ├─→ Record metrics to ~/.claude/metrics/YYYY-MM-DD/
   ├─→ If blocked: Route to next agent (repeat cycle)
   ├─→ If complete: Return to user
   │
   ↓
Complete
```

---

## Key Architecture Insights

### 1. **Skill-Based Modularity**
- Each quality check is a reusable skill (.md file)
- quality-gate-orchestration orchestrates them in parallel
- Skills can be used independently or in combination

### 2. **Intelligent Agent Routing**
- Task complexity determines which agent (model) works on it
- Scope clarity affects routing decision
- Cross-service impact escalates to higher-cost models
- Cheap agents (Haiku) handle well-scoped work
- Expensive agents (Opus) only on high-risk decisions

### 3. **Self-Healing Feedback Loop**
- **Phase 1**: Detect issues (parallel checks)
- **Phase 2**: Decide if issues warrant healing
- **Phase 3**: Route to Healer (if LOW risk) or escalate (if HIGH risk)
- **Phase 4**: Decide deployment readiness (PROCEED/WARN/BLOCK/ESCALATE)

### 4. **Cost Optimization**
- Orchestrator (Haiku) routes tasks to minimize token spend
- Engineer (Haiku) handles straightforward implementation
- Senior (Sonnet) handles design and planning
- Principal (Opus) handles only strategic decisions

### 5. **Complete Traceability**
- Metrics collected at every step
- Decisions logged to TODO.md
- Quality gate results in JSON format (.jsonl audit trails)
- Complete traceability from issue detection to resolution

---

**Diagram Generated**: 2026-04-28  
**Format**: ASCII art (terminal-friendly, version control friendly)  
**Use Cases**: Architecture review, onboarding, CI/CD documentation
