# agentic-engineers Agents Registry

Complete list of all 20 agents (13 SDLC + 5 Quality Gate + 2 Spec Review sub-agents).

---

## SDLC Orchestrator Agents (8)

### 1. General Orchestrator
- **Model:** Haiku 4.5
- **Effort:** low
- **Role:** Entry point router
- **Responsibility:** Classify incoming task, route to specialist agent
- **Delegates to:** Engineer, Senior Engineer, Lead Engineer, Principal Engineer, Security Engineer
- **Input (DELEGATE):** task_id, scope, complexity, has_plan, is_security_scoped
- **Output (HANDBACK):** routing_decision, confidence, reason
- **Success Criteria:** Correct routing 100% of time per 6-point tree
- **Status:** ✅ Stub complete, ready for implementation

### 2. Engineer Agent
- **Model:** Haiku 4.5
- **Effort:** high
- **Role:** Execution specialist
- **Responsibility:** Execute well-scoped tasks with pre-written plans
- **Delegates to:** Task executors, step runners
- **Input (DELEGATE):** task_id, scope, plan, success_criteria
- **Output (HANDBACK):** execution_results, quality_score, deliverables, confidence
- **Success Criteria:** 80-95% quality score on execution
- **Status:** ✅ Stub complete, ready for implementation

### 3. Senior Engineer Agent
- **Model:** Sonnet 4.6
- **Effort:** high
- **Role:** Analysis & planning specialist
- **Responsibility:** Analyze complex work, design solutions, create execution plans
- **Delegates to:** Analysis agents, design agents
- **Input (DELEGATE):** task_id, scope, context
- **Output (HANDBACK):** plan, root_cause_analysis, recommendation, confidence
- **Success Criteria:** 85-90% quality score on plan
- **Status:** ✅ Stub complete, ready for implementation

### 4. Lead Engineer Agent
- **Model:** Sonnet 4.6
- **Effort:** high
- **Role:** Code review & architectural guidance
- **Responsibility:** Review work against 8-point quality checklist, gate quality
- **Delegates to:** Review agents
- **Input (DELEGATE):** task_id, scope, work_to_review
- **Output (HANDBACK):** review_checklist (8 items), quality_score, decision (APPROVE/REJECT), confidence
- **Success Criteria:** 8/8 checklist items validated
- **Status:** ✅ Stub complete, ready for implementation

### 5. Principal Engineer Agent
- **Model:** Opus 4.7
- **Effort:** high
- **Role:** Cross-service architecture
- **Responsibility:** Design architecture options, analyze trade-offs, recommend approach
- **Delegates to:** Design agents, trade-off analysts
- **Input (DELEGATE):** task_id, scope, options_count
- **Output (HANDBACK):** options_analyzed, recommended_option, rationale, implementation_roadmap, confidence
- **Success Criteria:** 2+ options analyzed with clear trade-offs
- **Status:** ✅ Stub complete, ready for implementation

### 6. Quality Engineer Agent
- **Model:** Sonnet 4.6
- **Effort:** medium
- **Role:** Post-implementation quality gate
- **Responsibility:** Validate implementation quality, assess model fitness
- **Delegates to:** Assessment agents
- **Input (DELEGATE):** task_id, scope, quality_score_from_execution
- **Output (HANDBACK):** quality_score, model_assessment, decision, confidence
- **Success Criteria:** Accurate quality assessment + model fitness evaluation
- **Status:** ✅ Stub complete, ready for implementation

### 7. Model Engineer Agent
- **Model:** Haiku 4.5
- **Effort:** medium
- **Role:** Confidence scoring & model recommendations
- **Responsibility:** Calculate confidence, recommend model for next similar task
- **Delegates to:** (none - pure logic)
- **Input (DELEGATE):** task_id, quality_score, effort, complexity
- **Output (HANDBACK):** confidence (0.0-1.0), rank_1_model, rank_2_model, recommendation
- **Success Criteria:** Confidence algorithm correctly applied, recommendations accurate
- **Status:** ✅ Stub complete, ready for implementation

### 8. Security Engineer Agent
- **Model:** Opus 4.7
- **Effort:** max
- **Role:** Security analysis & threat modeling
- **Responsibility:** Perform threat modeling, identify vulnerabilities, assess security posture
- **Delegates to:** Threat analysis agents, vulnerability scanners
- **Input (DELEGATE):** task_id, scope, context
- **Output (HANDBACK):** security_score, vulnerabilities_found, severity, recommendations, confidence
- **Success Criteria:** All security issues identified, severity levels accurate
- **Status:** ✅ Stub complete, ready for implementation

---

## Quality Gate Sub-Agents (5)

### 9. Security Agent (QG)
- **Model:** Opus 4.7
- **Effort:** high
- **Role:** Credential & vulnerability scanning
- **Responsibility:** Scan code for hardcoded credentials, injection vulnerabilities, insecure patterns
- **Delegates to:** (none - scanning logic)
- **Input (DELEGATE):** task_id, scope, code_diff
- **Output (HANDBACK):** status (PASS/ESCALATE), credentials_found, vulnerabilities, severity, confidence
- **Success Criteria:** 0 false negatives on credential patterns, <2% false positives
- **Status:** ✅ Stub complete, ready for implementation

### 10. Testing Agent (QG)
- **Model:** Haiku 4.5
- **Effort:** medium
- **Role:** Test quality validation
- **Responsibility:** Parse test output, extract metrics, validate coverage
- **Delegates to:** (none - metric extraction)
- **Input (DELEGATE):** task_id, scope, test_output, coverage_report
- **Output (HANDBACK):** status (PASS/ESCALATE), tests_passed, tests_failed, coverage_pct, severity, confidence
- **Success Criteria:** Accurate test parsing, coverage measurement, no missed failures
- **Status:** ✅ Stub complete, ready for implementation

### 11. Metrics Agent (QG)
- **Model:** Haiku 4.5
- **Effort:** medium
- **Role:** System health scoring
- **Responsibility:** Score system health, validate latency/errors/capacity
- **Delegates to:** (none - scoring logic)
- **Input (DELEGATE):** task_id, scope, metrics_data
- **Output (HANDBACK):** status (PASS/ESCALATE), health_score, p99_latency, error_rate, severity, confidence
- **Success Criteria:** Accurate health scoring, thresholds properly applied
- **Status:** ✅ Stub complete, ready for implementation

### 12. Healing Agent (QG)
- **Model:** Sonnet 4.6
- **Effort:** medium
- **Role:** Config validation & auto-fix
- **Responsibility:** Identify config issues, apply auto-fixes, verify corrections
- **Delegates to:** Config validators, fix appliers
- **Input (DELEGATE):** task_id, scope, config_changes
- **Output (HANDBACK):** status (PASS/ESCALATE), issues_found, fixes_applied, severity, confidence
- **Success Criteria:** All config issues identified, fixes correctly applied
- **Status:** ✅ Stub complete, ready for implementation

### 13. Spec Engineer Agent (QG)
- **Model:** Sonnet 4.6
- **Effort:** medium
- **Role:** Spec drift detection
- **Responsibility:** Validate code against specification, detect drift types (TYPE_A/B/C/D)
- **Delegates to:** Consistency reviewer, architecture reviewer, completeness reviewer
- **Input (DELEGATE):** task_id, scope, code_changes, spec_ref
- **Output (HANDBACK):** status (PASS/ESCALATE), drift_types_found, severity, recommendations, confidence
- **Success Criteria:** All TYPE_A/D issues found, <2% false negatives
- **Status:** ⚠️ Needs full implementation (currently stub)

### 14. Quality Gate Orchestrator
- **Model:** Sonnet 4.6
- **Effort:** medium
- **Role:** Quality Gate aggregation & decision
- **Responsibility:** Delegate to 5 sub-agents in parallel, aggregate results, decide PROCEED/ESCALATE
- **Delegates to:** All 5 QG sub-agents
- **Input (DELEGATE):** task_id, scope, code_diff, test_output, metrics, config
- **Output (HANDBACK):** decision (PROCEED/ESCALATE), agents_passed, agents_escalated, audit_trail, confidence
- **Success Criteria:** <30s latency, 0% false positives, <2% false negatives
- **Status:** ✅ Stub complete, ready for implementation

---

## Spec Review Sub-Agents (2)

### 15. Consistency Reviewer Agent
- **Model:** Sonnet 4.6
- **Effort:** high
- **Role:** Spec internal consistency validation
- **Responsibility:** Check for contradictions, broken references, unclear definitions
- **Delegates to:** (none - textual analysis)
- **Input (DELEGATE):** task_id, spec_content, diff_from_previous
- **Output (HANDBACK):** issues_found (contradictions, broken_refs, unclear_defs), severity, confidence
- **Success Criteria:** All contradictions found, no false positives on valid ambiguity
- **Status:** ⚠️ Needs implementation

### 16. Architecture Reviewer Agent
- **Model:** Opus 4.7
- **Effort:** high
- **Role:** Architectural soundness validation
- **Responsibility:** Verify agent-to-agent delegation model, no external deps, clean interfaces
- **Delegates to:** (none - architecture analysis)
- **Input (DELEGATE):** task_id, spec_content, agent_definitions
- **Output (HANDBACK):** issues_found (violations, missing_delegations), severity, confidence
- **Success Criteria:** Self-contained constraint verified, all delegations clear
- **Status:** ⚠️ Needs implementation

### 17. Completeness Reviewer Agent
- **Model:** Sonnet 4.6
- **Effort:** medium
- **Role:** Spec completeness validation
- **Responsibility:** Verify all agents documented, protocols complete, no gaps
- **Delegates to:** (none - verification logic)
- **Input (DELEGATE):** task_id, spec_content
- **Output (HANDBACK):** missing_items (agents, protocols, examples), severity, confidence
- **Success Criteria:** 100% of agents documented, all protocols specified
- **Status:** ⚠️ Needs implementation

### 18. Security Reviewer Agent
- **Model:** Opus 4.7
- **Effort:** high
- **Role:** Spec security implications
- **Responsibility:** Review spec for security constraints, compliance implications, risk assessment
- **Delegates to:** (none - security analysis)
- **Input (DELEGATE):** task_id, spec_content, constraint_section
- **Output (HANDBACK):** security_issues, compliance_gaps, severity, recommendations, confidence
- **Success Criteria:** All security implications identified, constraints validated
- **Status:** ⚠️ Needs implementation

---

## Spec Review Orchestrator (Meta-Agent)

### 19. Spec Engineer Orchestrator
- **Model:** Sonnet 4.6
- **Effort:** medium
- **Role:** Spec review coordination
- **Responsibility:** Detect SPEC.md changes, delegate to 4 review agents in parallel, aggregate findings, decide APPROVED/NEEDS_REVISION
- **Delegates to:** Consistency Reviewer, Architecture Reviewer, Completeness Reviewer, Security Reviewer
- **Input (DELEGATE):** task_id, spec_content, previous_spec_version, diff
- **Output (HANDBACK):** decision (APPROVED/NEEDS_REVISION), issues_by_type, severity, recommendations, confidence
- **Success Criteria:** All review agents run, findings aggregated, decision clear
- **Status:** ⚠️ Needs full implementation (core spec review workflow)

---

## Summary by Status

### ✅ Ready for Implementation (14 agents)
All SDLC agents (8) + QG agents (5) + QG Orchestrator (1)
- Stubs complete with input/output validation
- Specifications documented
- Ready for Claude integration

### ⚠️ Needs Implementation (6 agents)
- Spec Engineer Agent (QG sub-agent) - needs review delegation logic
- Consistency Reviewer - needs contradiction detection
- Architecture Reviewer - needs architectural validation
- Completeness Reviewer - needs gap detection
- Security Reviewer - needs security analysis
- Spec Engineer Orchestrator - needs review workflow

---

## Agent Dependencies Graph

```
User Input
  ↓
GeneralOrchestrator (routing)
  ├─→ Engineer (execution)
  ├─→ SeniorEngineer (analysis)
  ├─→ LeadEngineer (review)
  ├─→ PrincipalEngineer (architecture)
  └─→ SecurityEngineer (threat modeling)
       ↓
QualityEngineer (post-impl QA)
       ↓
ModelEngineer (confidence)
       ↓
QualityGateOrchestrator (5 parallel)
  ├─→ SecurityAgentQG
  ├─→ TestingAgent
  ├─→ MetricsAgent
  ├─→ HealingAgent
  └─→ SpecEngineerAgent (delegates to)
       ├─→ ConsistencyReviewer
       ├─→ ArchitectureReviewer
       ├─→ CompletenessReviewer
       └─→ SecurityReviewer
            ↓
       SpecEngineerOrchestrator (aggregates)
            ↓
         HANDBACK
```

---

## Triggering Workflows

### SDLC Orchestrator
- **Triggered by:** New task, requirement, or code review request
- **Entry:** GeneralOrchestrator
- **Async:** Yes
- **Output:** HANDBACK block with deliverables

### Quality Gate
- **Triggered by:** Commit to main, PR merge request
- **Entry:** QualityGateOrchestrator
- **Async:** No (synchronous, <30s)
- **Output:** PROCEED/ESCALATE decision

### Spec Review
- **Triggered by:** Changes to SPEC.md detected
- **Entry:** SpecEngineerOrchestrator
- **Async:** Yes
- **Output:** APPROVED/NEEDS_REVISION + findings

---

## Model Distribution

```
Haiku 4.5 (Cheapest, structured work):
  - GeneralOrchestrator
  - Engineer
  - ModelEngineer
  - TestingAgent (QG)
  - MetricsAgent (QG)

Sonnet 4.6 (Mid-range, judgment calls):
  - SeniorEngineer
  - LeadEngineer
  - QualityEngineer
  - HealingAgent (QG)
  - SpecEngineerAgent (QG)
  - QualityGateOrchestrator
  - ConsistencyReviewer (Spec)
  - CompletenessReviewer (Spec)
  - SpecEngineerOrchestrator (Spec)

Opus 4.7 (Most capable, complex analysis):
  - PrincipalEngineer
  - SecurityEngineer
  - SecurityAgentQG (QG)
  - ArchitectureReviewer (Spec)
  - SecurityReviewer (Spec)
```

---

**Total Agents:** 20 (13 SDLC/QG + 7 Spec Review related)  
**Ready:** 14  
**Needs Implementation:** 6  
**Critical Path:** Complete Spec Engineer Orchestrator + 4 sub-agents for automated spec validation
