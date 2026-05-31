# Strategic Framework Improvement Initiative
## 4-Phase Comprehensive Redesign Plan

**Status:** Planning (awaiting approval)  
**Principal Engineer Lead:** @niallyoung  
**Scope:** Audit SPEC.md, prevent drift, improve skills, design Principles+Rules hybrid  
**Timeline:** 4 phases over 2-4 weeks (12-20 hours)  
**Success Criteria:** 3x Security Engineer sign-off on final design

---

## Overview

This initiative restructures the agentic-engineers framework from a Rules-heavy (~95%) to a Principles+Rules hybrid (~50/50) architecture, with three critical foundations:

1. **Phase 1 (CRITICAL):** Audit SPEC.md for drift, document all discrepancies
2. **Phase 2 (HIGH):** Implement automated drift prevention (spec-verify)
3. **Phase 3 (MEDIUM):** Improve skills based on learnings (spec-extract, spec-review)
4. **Phase 4 (STRATEGIC):** Design Principles+Rules framework with Security sign-off

---

## Phase 1: SPEC.md Audit & Update (CRITICAL) — 2-4 hours

### Core Evaluation Approach

**Principle-Based Evaluation (Primary):**
- Start with principles: transparency, accuracy, completeness
- Evaluate each SPEC section: "Does this reflect the actual system design?"
- Use spec-extract skill to validate (acknowledge skill might have limitations)
- When spec-* skills reveal gaps → document as potential skill improvement opportunity, not necessarily spec error
- Flexible: some apparent "drift" may be intentional design decisions needing documentation, not fixes

**Rules-Based Fallback (When Ambiguous):**
- Only apply hard rules if principle-based evaluation is inconclusive
- Known rules: version stamps should not exist, queue paths must be accurate, protocol schema must match implementation
- If a change violates a clear rule, document but also evaluate: "Is this rule still valid? Does principle suggest we should update the rule?"

### Key Tasks

1. **Evaluate entire branch of commits** leading up to current SPEC.md
   - Understand intent: was queue path change intentional?
   - Review commit messages: do they explain drift or is drift unintentional?
   - Assess: is this a bug or a deliberate design change?

2. **Use spec-extract/spec-review skills** to validate
   - Run spec-extract against current SPEC.md
   - Compare extracted spec against implementation
   - When skills reveal gaps: document as "spec-* skill limitation" not necessarily "SPEC error"
   - Example: if spec-extract can't parse a certain format, that's a skill gap, not a spec bug

3. **Principle-based evaluation** for each drift
   - Queue path drift: Is transparency served by old path reference? NO → fix
   - Version stamps: Are they useful for clarity? NO (git provides history) → remove
   - Agent definitions: Do they match implementation intent? Verify and document reasoning
   - Protocol schema: Does SPEC match actual protocol? If not, which is authoritative?

4. **Document all findings** with intent analysis
   - Intentional design choices (keep as-is, document why)
   - Unintentional drift (correct)
   - Ambiguous cases (note as "needs clarification")
   - Spec-skill limitations (mark for Phase 3 improvement)

5. **Correct known drift:** queue path, version stamps
   - Queue path `~/.copilot/` → `~/.agentic-engineers/artifacts/queue/{session-id}/{harness}/`
   - Remove version/date stamps (lines 4-5, 13-14, 280)

### Known Drift Issues (Prioritized)

**Definite Fixes (Clear Rules):**
- ❌ Queue path incorrect in SPEC.md (uses old `~/.copilot/` path) → VIOLATES transparency principle
- ❌ Version/date stamps present → VIOLATES "git is source of truth" principle
- ❌ Missing `{harness}` in queue path specification → VIOLATES completeness principle

**Evaluate (Principles-First):**
- ❓ Agent models accuracy: Do definitions match implementation intent?
- ❓ Skill structure: Is SKILL.md frontmatter spec accurate?
- ❓ Protocol fields: Are all required/optional fields documented?
- ❓ Cost projections: Do they reflect current model prices?

**Spec-Skill Feedback (Phase 3 Improvement):**
- 📝 Document any gaps found by spec-extract/spec-review
- 📝 Note: "Skill couldn't detect X → needs enhancement"
- 📝 These gaps inform Phase 3 skill improvements

### Acceptance Criteria
- ✅ Queue path corrected (principle: transparency)
- ✅ Version/date stamps removed (principle: rely on git history)
- ✅ Agent definitions verified and intent documented
- ✅ Protocol schema verified (identify authoritative source)
- ✅ SPEC-DRIFT-AUDIT.md documents:
  - All intentional design choices with rationale
  - All unintentional drift with corrections
  - All ambiguous cases with clarification needed
  - All spec-* skill limitations found (for Phase 3)
- ✅ PR #24 with comprehensive analysis showing principle-based reasoning
- ✅ Acknowledge: some "drift" may reveal spec-* skill gaps, not spec errors

---

## Phase 2: Spec Drift Prevention (HIGH) — 2-3 hours (after Phase 1)

### Core Approach

**Principle-Based Validation (Primary):**
- spec-verify applies guiding principles to detect drift
- Principles: transparency (spec must match implementation), completeness (all specs documented), consistency (no contradictions)
- Self-learning: when drift is detected, evaluate root cause
  - Is it a spec error? OR
  - Is it a detection skill limitation?
- Flexible enforcement: warn on principle violations, fail on clear rule violations

**Rules-Based Guardrails (When Ambiguous):**
- Hard rules: queue paths must be in standard format, version stamps forbidden, protocol schema immutable
- When principle-based evaluation is inconclusive, apply rules
- Example: "Principle says SPEC should match implementation, but spec-verify can't determine if they match" → apply rule "implementation is authoritative"

### Key Tasks
1. Create spec-verify that validates SPEC against implementation using principles
2. Detect drift via principle-based rules (transparency, completeness, consistency)
3. Self-learning loop: when drift found, evaluate "Is this detection accurate or is the detector flawed?"
4. Integrate into pre-push hook with flexible fail modes (warn vs. block)
5. CI/CD workflow with clear error reporting

### Deliverables
- spec-verify script (Python, ~150-200 lines, principle-based detection)
- Pre-push hook integration (principle-first, rule fallback)
- CI/CD workflow with flexible exit codes
- Documentation (docs/SPEC-VERIFICATION.md) explaining principle + rule approach

### Acceptance Criteria
- ✅ spec-verify detects queue path drift (principle: transparency)
- ✅ spec-verify detects version stamps (principle: git is authoritative)
- ✅ spec-verify can distinguish: "SPEC error" vs. "Detection skill limitation"
- ✅ Warns on principle violations, blocks on clear rule violations
- ✅ Runs in <5 seconds
- ✅ Bypassable with documented justification

---

## Phase 3: Skills Improvement (MEDIUM) — 2-3 hours (parallel with Phase 2)

### Core Approach

**Iterative Learning from Phase 1-2 Findings:**
- Phase 1 identified spec-* skill limitations (what couldn't they detect?)
- Phase 2 spec-verify logs what it couldn't determine (detection gaps)
- Phase 3 fixes those gaps by enhancing spec-extract and spec-review
- Self-learning: each iteration improves skill accuracy

**Principle-Based Evaluation of Improvements:**
- Principles for spec-extract: accuracy (find what's really in code), completeness (don't miss items), clarity (confidence scores)
- Principles for spec-review: precision (avoid false positives), actionability (suggest real fixes), honesty (admit uncertainties)
- Acknowledge: some "drift" may be intentional design choices, not skill errors

### Key Tasks
1. Analyze Phase 1 audit: where did spec-* skills fail to detect drift?
2. Analyze Phase 2 spec-verify: what detection limitations were found?
3. Enhance spec-extract to catch missed patterns
   - Queue path detection (all variants)
   - Protocol schema parsing (extract from code, not just docs)
   - Confidence scoring: when uncertain, return low confidence + note reason
   - Document limitations: "Can't detect X because Y"

4. Enhance spec-review to improve accuracy
   - Root cause analysis: is drift intentional or accidental?
   - Distinguish: spec error vs. skill limitation vs. intentional design choice
   - Repair suggestions: when confident, suggest fixes; when uncertain, ask for clarification
   - Admit unknowns: "Pattern unclear" rather than guessing

5. Document SPEC-DRIFT-PATTERNS.md with learnings
   - Patterns spec-* skills now detect
   - Patterns still challenging for skills (flagged for future improvement)
   - Prevention strategies (what guards would help most?)

6. Build test suite that validates improvements
   - Real examples from Phase 1 (did skill improvements catch them?)
   - Synthetic examples (edge cases)
   - Negative tests: skill should NOT flag intentional design choices

### Deliverables
- Enhanced spec-extract skill (~200-300 lines, with confidence scoring)
- Enhanced spec-review skill (~250-350 lines, with honesty about limitations)
- SPEC-DRIFT-PATTERNS.md (patterns learned, limitations acknowledged)
- Comprehensive test suite (15-20 tests, real + synthetic)
- Meta-commentary: where spec-* skills still have gaps

### Acceptance Criteria
- ✅ spec-extract detects 90%+ of spec elements (but admits what it can't)
- ✅ spec-extract returns confidence scores and explains low-confidence cases
- ✅ spec-review catches most drift correctly (within skill limits)
- ✅ spec-review distinguishes: error vs. limitation vs. intentional choice
- ✅ SPEC-DRIFT-PATTERNS.md documents all patterns, including skill gaps
- ✅ 15+ test cases (real examples from Phase 1, edge cases)
- ✅ All tests passing
- ✅ Skills improve from baseline but acknowledge remaining limitations

---

## Phase 4: Principles + Rules Hybrid Framework (STRATEGIC) — 4-8 hours (2-3 iterations)

### Core Approach

**Self-Learning & Adaptive Principles:**
- Principles should be flexible enough to handle novel situations, yet provide clear guidance
- As framework is applied, refine principles based on real decisions
- Rules should be minimal guardrails (only when principles ambiguous or safety-critical)
- Acknowledge: Principles may need iteration; gather feedback from Security Engineers

**Principle-Based Evaluation of Phase 1-3 Decisions:**
- Evaluate Phase 1 SPEC corrections using principles: Did we apply principles consistently?
- Evaluate Phase 2 spec-verify design: Are detection rules aligned with principles?
- Evaluate Phase 3 skill improvements: Do improvements strengthen or weaken principle-based guidance?
- Example: "Phase 1 removed version stamps. Is this decision grounded in principle (transparency) or just a rule?"

### Key Tasks
1. Identify 15-20 core principles across organization/roles (grounded in Phase 1-3 decisions)
   - What principles guided our SPEC corrections?
   - What principles should guide spec-verify?
   - What principles should guide skill improvements?
   - Organize by scope: org-wide, role-specific, decision-specific

2. Analyze current rules (in src/, .githooks/, .github/workflows/)
   - Categorize by function: safety, quality, efficiency, compliance
   - For each rule: which principle(s) does it serve?
   - Can this rule be replaced by principle-based guidance?
   - If not, why does principle alone insufficient?

3. Design hybrid model with decision trees (10+ scenarios)
   - Apply principles first: "What guidance do principles give?"
   - If ambiguous, apply rules: "Which rule clarifies this?"
   - Document both branches: principle path + rule guardrail

4. Iterate with 3x Security Engineers (minimum 2 rounds)
   - **Round 1:** "Do these principles + rules work?" Expect major feedback
   - **Round 2:** Refined design based on feedback. "Are we missing edge cases?" Expect nuanced feedback
   - **Final:** "Does this framework improve decision-making compared to rules-only?" Request sign-off

5. Test with case studies from Phase 1-3
   - Did principles guide same decisions as rules would have?
   - Where did principles diverge from rules? Is that good?
   - Would future engineers apply principles consistently?

### Deliverables
- PRINCIPLES.md (15-20 principles with rationale, grounded in Phase 1-3)
- PRINCIPLES-APPLICATION.md (10+ decision trees showing principle+rule flow)
- RULES-TO-PRINCIPLES-MAPPING.md (identify 30%+ replaceable rules)
- Case studies from Phase 1-3 re-evaluated (confirming framework works)
- Design PR with iterative feedback incorporated
- 3x Security Engineer sign-off document

### Acceptance Criteria
- ✅ 15-20 principles documented (grounded in framework decisions)
- ✅ 10+ decision trees (principle-first, rule fallback)
- ✅ 30%+ of rules identified as replaceable by principles
- ✅ Phase 1-3 decisions validated using new framework
- ✅ 3x Security Engineer sign-off: "Framework is superior + more adaptive than rules-only"
- ✅ Framework acknowledges principle limitations + future refinement needs
- ✅ Zero regressions in safety or quality guardrails

---

## Execution with Parallel Sub-Agents

**Parallelization Strategy:** Launch specialized agents in parallel where possible

```
Phase 1 ──────────────────────────────────────────────────┐
  Main Agent: Principal Engineer (lead)                    │
  Tasks:                                                   │
  - Audit SPEC.md (main thread)                           │
  - Fix queue path, remove version stamps                 │
  - Evaluate intent (commit history analysis)             │
  └─ Parallel: Launch Security Engineer to validate       │
     security implications of SPEC changes               │
                                                          │
  Parallel Sub-Agent: Security Engineer ────────────────┐ │
  Tasks:                                                │ │
  - Review drift findings for security impact          │ │
  - Validate: are we removing important constraints?   │ │
  - Assess: does SPEC maintain security baseline?      │ │
  └─ Rejoin Phase 1: consensus on corrections          │ │
                                                        │ │
Phase 1 Complete ◄────────────────────────────────────┘ │
  │                                                       │
  ├─► Phase 2 ──────────────────────────────────────────┬┘
  │   Main Agent: Principal Engineer (spec-verify design)
  │   Parallel:
  │   - Security Engineer: Validates spec-verify rules
  │   - Quality Engineer: Tests spec-verify accuracy
  │
  ├─► Phase 3 ──────────────────────────────────────────┐
  │   Main Agent: Senior Engineer (skill enhancement)   │
  │   Parallel:                                         │
  │   - Quality Engineer: Comprehensive test suite      │
  │   - Lead Engineer: Code review of improvements      │
  │
  └─► Phase 4 ──────────────────────────────────────────┐
      Main Agent: Principal Engineer (framework design) │
      Parallel:                                         │
      - Security Engineer (Round 1 review)            │
      - Security Engineer (Round 2 review)            │
      - Security Engineer (Final sign-off)            │
      - Quality Engineer: Equivalence testing          │
```

### Speed Optimizations

**Phase 1:** 1.5-2 hours
- Principal Engineer + Security Engineer parallel (merge findings)
- Fewer open questions, faster turnaround

**Phase 2:** 1-1.5 hours
- Lean spec-verify (MVP: detect queue path + version stamps)
- Parallel testing by Quality Engineer

**Phase 3:** 1.5-2 hours
- Focused skill improvements (only learnings from Phase 1)
- Parallel test suite development

**Phase 4:** 2-3 hours (iterative with parallel reviews)
- Design in parallel with first Security review
- Round 2 feedback processed immediately
- Parallel equivalence testing

**Total Aggressive Timeline:** 6-9 hours (vs. 12-20 baseline)

### Equivalence Testing Strategy

**Goal:** Prove new Principles+Rules framework produces same safety/quality outcomes as old Rules-only approach

**Test Approach:**
1. **Equivalence baseline:** Document all current rules and their enforcement
2. **Framework mapping:** Map each rule to principle(s)
3. **Case study validation:** Run 10+ real scenarios through both systems
   - Old: "Apply rule X" → decision
   - New: "Apply principle Y" → decision
   - Compare: Do both lead to same conclusion?
4. **Difference analysis:** Document cases where new framework differs
   - Analyze: Is difference justified by better principle reasoning?
   - Is difference a regression (new framework worse)?
   - Is difference an improvement (new framework clearer/more adaptive)?
5. **Test coverage:** 20+ equivalence tests proving framework safety

**Deliverable:** EQUIVALENCE-TESTING.md showing proof that Principles+Rules ≥ Rules-only

---

## Known Issues & Clarifications

1. **Queue Path:** Currently in SPEC as `~/.copilot/queue/`, should be `~/.agentic-engineers/artifacts/queue/`
2. **Version Stamps:** Line 4, 5, 13-14 in SPEC.md need removal
3. **Skill Reference:** Only 1 SKILL.md found, need to verify if spec-extract/spec-review exist
4. **Security Review:** Phase 4 requires 3x Security Engineer involvement (budget 2-3 review rounds)

---

## Success Definition

By completion:
1. ✅ SPEC.md is 100% accurate and drift-free
2. ✅ Automated spec-verify prevents future drift
3. ✅ Skills improved with learnings from audit
4. ✅ Principles+Rules hybrid designed and approved
5. ✅ 3x Security Engineers sign-off: framework is superior + equivalent
6. ✅ EQUIVALENCE-TESTING.md proves new framework ≥ old approach
7. ✅ Zero regressions in existing enforcement
8. ✅ Framework improves decision quality and consistency
9. ✅ Completed in ~6-9 hours using parallel sub-agents
