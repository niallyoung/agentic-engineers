# Phase 4 — Metrics Tracking and Validation Strategy

**Owner:** Quality Engineer  
**Status:** Active  
**Phase Start:** Week 1 of consolidation validation  
**Review Window:** 4 weeks  
**Last Updated:** 2026-05-14

---

## Purpose

Phases 1–3 consolidated Engineer skills into shared baselines and updated role files to reference them. Phase 4 validates that the consolidation is actually working: Engineers use the skills, quality improves, and role boundaries are clear.

This document is the operational handbook for that validation. It defines **how QE collects data**, **what signals to watch**, and **when to escalate or intervene**.

**Key principle:** Phase 4 is *validation*, not *enforcement*. The goal is to learn whether consolidation is working — not to blame individuals. If a metric misses its target, the first question is always: "Is the skill reference clear enough?"

---

## Six Metrics at a Glance

| # | Metric | Target | Owner |
|---|--------|--------|-------|
| M1 | Engineer uses `cicd-watch` after push | 100% | QE |
| M2 | Senior uses `todo-management` when planning | 90%+ | QE |
| M3 | QE consults `quality-assessment-baseline` | 90%+ | QE |
| M4 | Lead + QE verdict agreement | 95%+ | Model Engineer |
| M5 | Pattern misapplications | <5% | Lead |
| M6 | Skill-related escalations | 0 | Orchestrator |

---

## Deliverable 1: Metrics Tracking Tables

Use one row per observed task (M1–M3, M5–M6) or per PR pair (M4). Copy raw data here weekly. Summaries go to the [Weekly Review section](#deliverable-2-weekly-review-cadence).

---

### M1 — Engineer Uses `cicd-watch` After Push

**Signal source:** Engineer HANDBACK `notes` field.  
**What counts as a positive signal:** Explicit mention of one of:
- Actions/CI status checked after push (`gh run watch`, `gh run list`)
- Pipeline failure identified and fixed
- "CI passed" / "pipeline green" confirmation
- Reference to `monitoring/cicd-watch.md`

**What does NOT count:** A passing `tests_passed` field alone — that confirms local tests, not pipeline watch.

**Sample size target:** Next 10–15 Engineer task HANDBACKs.

```
M1 TRACKING TABLE
=================
Date       | Task ID                         | Used cicd-watch | Evidence (HANDBACK notes excerpt)
-----------|---------------------------------|-----------------|-------------------------------------
YYYY-MM-DD | <task_id>                       | Y / N           | "<relevant quote from HANDBACK notes>"
YYYY-MM-DD | <task_id>                       | Y / N           | "<relevant quote from HANDBACK notes>"
```

**Running totals (update weekly):**

```
M1 WEEKLY SUMMARY
=================
Week | Tasks Observed | Y | N | Usage Rate | At Target?
-----|----------------|---|---|------------|------------
W1   |                |   |   |            | Y/N
W2   |                |   |   |            | Y/N
W3   |                |   |   |            | Y/N
W4   |                |   |   |            | Y/N
```

**Red flag threshold:** <80% in any week → see [Escalation Playbook — M1](#m1-engineer-cicd-watch-below-80).

---

### M2 — Senior Engineer Uses `todo-management` When Planning

**Signal source:** Senior Engineer HANDBACK `notes` or `deliverables` fields; or attached plan.md.  
**What counts as a positive signal:**
- Explicit mention of `TODO.md` created or updated
- HANDBACK `deliverables` includes `TODO.md` as an artefact
- HANDBACK notes contain a structured task breakdown (even if file not named)
- Reference to `orchestration/todo-management.md`

**Scope filter:** Only count Senior Engineer tasks involving design, decomposition, or multi-step planning. Routine code-only tasks (pure implementation delegated downstream) are excluded — those don't require todo-management. Mark as N/A if the task is pure implementation.

**Sample size target:** Next 5–8 Senior Engineer planning-scope tasks.

```
M2 TRACKING TABLE
=================
Date       | Task ID              | Is Planning Task? | Used TODO.md | TODOs Created | Evidence
-----------|----------------------|-------------------|--------------|---------------|----------
YYYY-MM-DD | <task_id>            | Y / N / N/A       | Y / N / N/A  | <count or N/A>| "<excerpt>"
YYYY-MM-DD | <task_id>            | Y / N / N/A       | Y / N / N/A  | <count or N/A>| "<excerpt>"
```

**Running totals (planning tasks only; exclude N/A rows):**

```
M2 WEEKLY SUMMARY
=================
Week | Planning Tasks | Y | N | Usage Rate | At Target?
-----|----------------|---|---|------------|------------
W1   |                |   |   |            | Y/N
W2   |                |   |   |            | Y/N
W3   |                |   |   |            | Y/N
W4   |                |   |   |            | Y/N
```

**Red flag threshold:** <75% over any two consecutive weeks → see [Escalation Playbook — M2](#m2-senior-todo-management-below-75).

---

### M3 — QE Consults `quality-assessment-baseline` in Assessments

**Signal source:** QE assessment records (HANDBACK YAML or structured assessment output).  
**What counts as a positive signal:** Assessment output meets ALL of:
1. All 8 dimensions scored (or explicitly marked `N/A` with explanation)
2. Overall score maps to one of the 4 score bands (90+, 80–89, 70–79, <70)
3. YAML format used (matches Section 4 of `shared/quality-assessment-baseline.md`)

**Self-assessment:** This metric applies to QE's own output. Track each post-approval assessment QE produces.

```
M3 TRACKING TABLE
=================
Date       | PR #   | All 8 dims scored | Score Band used   | YAML format | Compliant | Notes
-----------|--------|-------------------|-------------------|-------------|-----------|-------
YYYY-MM-DD | PR-xxx | Y / N             | 90+ / 80-89 / ... | Y / N       | Y / N     | ...
YYYY-MM-DD | PR-xxx | Y / N             | 90+ / 80-89 / ... | Y / N       | Y / N     | ...
```

**Running totals:**

```
M3 WEEKLY SUMMARY
=================
Week | Assessments | Compliant | Non-Compliant | Compliance Rate | At Target?
-----|-------------|-----------|---------------|-----------------|------------
W1   |             |           |               |                 | Y/N
W2   |             |           |               |                 | Y/N
W3   |             |           |               |                 | Y/N
W4   |             |           |               |                 | Y/N
```

**Red flag threshold:** <80% compliance in any week → see [Escalation Playbook — M3](#m3-qe-baseline-compliance-below-80).

---

### M4 — Lead + QE Verdict Agreement

**Signal source:** Cross-check Lead Engineer APPROVE/REWORK decision vs QE post-approval score.  
**What counts as agreement:**

| Lead Decision | QE Score | Agreement? |
|---------------|----------|------------|
| APPROVE (any) | ≥ 70 | ✅ Agreement |
| APPROVE unconditional | ≥ 80 | ✅ Strong agreement |
| APPROVE conditional (70–79 band) | 70–79 | ✅ Agreement — borderline acknowledged by both |
| REWORK | < 70 | ✅ Agreement |
| APPROVE | < 70 | ❌ Disagreement — Lead approved, QE scored poor |
| REWORK | ≥ 80 | ❌ Disagreement — Lead blocked, QE scored good |

**Note:** A Lead APPROVE on a 70–79 score ("Conditional Approval" per quality-assessment-baseline.md Section 2) paired with a QE 70–79 score is *agreement* — both roles recognise it is borderline.

```
M4 TRACKING TABLE
=================
Date       | PR #   | Lead Decision       | QE Score | QE Band  | Agree | Disagreement Reason (if N)
-----------|--------|---------------------|----------|----------|-------|----------------------------
YYYY-MM-DD | PR-xxx | APPROVE / REWORK    | <score>  | 90+ etc. | Y / N | <reason>
YYYY-MM-DD | PR-xxx | APPROVE / REWORK    | <score>  | 90+ etc. | Y / N | <reason>
```

**Running totals:**

```
M4 WEEKLY SUMMARY
=================
Week | PRs Reviewed | Agreements | Disagreements | Agreement Rate | At Target?
-----|--------------|------------|---------------|----------------|------------
W1   |              |            |               |                | Y/N
W2   |              |            |               |                | Y/N
W3   |              |            |               |                | Y/N
W4   |              |            |               |                | Y/N
```

**Red flag threshold:** <90% agreement in any two-week window → see [Escalation Playbook — M4](#m4-lead-qe-agreement-below-90).

---

### M5 — Pattern Misapplications

**Signal source:** Lead Engineer code review feedback; specifically review comments on:
- `patterns/api-resilience.md` implementations (retry logic, circuit breaker, token refresh)
- `patterns/event-consumer.md` implementations (SNS FIFO → SQS FIFO → Lambda + idempotency)

**What counts as a misapplication:**
- Missing retry logic where api-resilience pattern is used
- Missing idempotency key in event-consumer implementations
- Improper error handling (bare except, no logging)
- Pattern invoked but a key requirement silently omitted

**Severity rating:**
- **High:** Missing correctness guarantee (idempotency, retry, auth) — PR should not ship
- **Medium:** Partial implementation — works in happy path, fails under load/error
- **Low:** Minor deviation from pattern — cosmetic or non-critical

```
M5 TRACKING TABLE
=================
Date       | PR #   | Pattern Used        | Issues Found | Severity        | Example Issue
-----------|--------|---------------------|--------------|-----------------|---------------
YYYY-MM-DD | PR-xxx | api-resilience      | Y / N        | high/medium/low | "<description>"
YYYY-MM-DD | PR-xxx | event-consumer      | Y / N        | high/medium/low | "<description>"
```

**Running totals (PRs using one of the two patterns):**

```
M5 WEEKLY SUMMARY
=================
Week | Pattern PRs | PRs with Issues | Misapplication Rate | At Target?
-----|-------------|-----------------|---------------------|------------
W1   |             |                 |                     | Y/N
W2   |             |                 |                     | Y/N
W3   |             |                 |                     | Y/N
W4   |             |                 |                     | Y/N
```

**Red flag threshold:** >5% over a two-week window → see [Escalation Playbook — M5](#m5-pattern-misapplications-above-5).

---

### M6 — Skill-Related Escalations

**Signal source:** HANDBACK `notes` field; Orchestrator routing logs; HANDBACK `status: failed` with escalation reason.  
**What to look for:** Any escalation where the root cause is:
- "I don't have the skill for this" (missing skill reference)
- "Unclear which role should handle this" (role boundary confusion)
- "I don't know how to use [pattern/tool]" (skill not understood)

**What does NOT count:** Escalations due to task complexity, missing requirements, or ambiguous scope — those are expected and healthy.

```
M6 TRACKING TABLE
=================
Date       | Task ID              | Escalation | Stated Reason                     | Root Cause = Skill Gap? | Action Taken
-----------|----------------------|------------|-----------------------------------|------------------------|-------------
YYYY-MM-DD | <task_id>            | Y / N      | "<reason from HANDBACK>"          | Y / N                  | <fix applied>
YYYY-MM-DD | <task_id>            | Y / N      | "<reason from HANDBACK>"          | Y / N                  | <fix applied>
```

**Running totals:**

```
M6 WEEKLY SUMMARY
=================
Week | Tasks Observed | Escalations | Skill-Gap Escalations | Cumulative Skill Gaps | At Target?
-----|----------------|-------------|----------------------|-----------------------|------------
W1   |                |             |                      |                       | Y/N
W2   |                |             |                      |                       | Y/N
W3   |                |             |                      |                       | Y/N
W4   |                |             |                      |                       | Y/N
```

**Red flag threshold:** Any skill-gap escalation triggers immediate action. See [Escalation Playbook — M6](#m6-skill-related-escalation-occurs).

---

## Deliverable 2: Weekly Review Cadence

QE is responsible for running this cadence each week during the 4-week validation window.

---

### Monday: Data Collection

**Time required:** 30–45 minutes

1. Collect all completed Engineer HANDBACKs from the prior week.
   - Check `artifacts/` directory for HANDBACK YAML files dated in prior week
   - Check session store for completed task summaries
2. Append rows to M1, M2, M6 tracking tables from HANDBACK `notes` and `deliverables` fields.
3. Collect all QE assessments produced in the prior week.
   - Append rows to M3 tracking table (self-assessment of own output format compliance).
4. Collect all Lead Engineer code review decisions from the prior week.
   - Cross-reference with QE post-approval scores from M3 rows.
   - Append rows to M4 tracking table.
5. Collect all pattern-related PRs (api-resilience, event-consumer) from Lead review data.
   - Append rows to M5 tracking table.
6. Update all "Running totals" rows in each table.

**Tip:** Where HANDBACK YAML is available, the following fields are most useful:
```yaml
notes:       # Free-text — search for "Actions", "pipeline", "CI", "TODO.md", "cicd-watch"
deliverables:# List of artefacts — search for "TODO.md", "plan.md" entries
status:      # complete / partial / failed
```

---

### Wednesday: Analysis

**Time required:** 20–30 minutes

1. Calculate running weekly rates for all 6 metrics.
2. Compare each rate against its red flag threshold:

| Metric | Red Flag |
|--------|----------|
| M1 | <80% in current week |
| M2 | <75% over two consecutive weeks |
| M3 | <80% in current week |
| M4 | <90% over two-week window |
| M5 | >5% over two-week window |
| M6 | Any skill-gap escalation |

3. For each red flag triggered: note it in the table, determine intervention (see [Escalation Playbook](#deliverable-3-escalation-playbook)).
4. For metrics on track: note trend direction (improving / stable / degrading).
5. Record brief analysis note in [Weekly Analysis Log](#weekly-analysis-log).

---

### Friday: Intervention Planning (if needed)

**Time required:** 10–15 minutes (only if red flags triggered)

1. If any red flag was noted Wednesday: confirm the intervention approach and act on it.
2. Log the intervention in [Weekly Analysis Log](#weekly-analysis-log).
3. Set a follow-up observation marker in the next week's M tracking table to confirm whether the intervention worked.

---

### Weekly Analysis Log

Update this section each Wednesday with a brief note.

```
WEEKLY ANALYSIS LOG
===================

Week 1 (Dates: __ to __)
  M1: __% usage. [On track / Red flag — <description>]
  M2: __% usage. [On track / Red flag — <description>]
  M3: __% compliance. [On track / Red flag — <description>]
  M4: __% agreement. [On track / Red flag — <description>]
  M5: __% misapplication rate. [On track / Red flag — <description>]
  M6: __ skill-gap escalations. [On track / Red flag — <description>]
  Interventions: [None / <description>]
  Key observation: <1–2 sentences>

Week 2 (Dates: __ to __)
  M1: ...
  [continue pattern]

Week 3 (Dates: __ to __)
  ...

Week 4 (Dates: __ to __)
  ...
```

---

## Deliverable 3: Escalation Playbook

### M1 — Engineer cicd-watch Below 80%

**Trigger:** M1 usage rate <80% in any single week.

**Before escalating, check:**
- Is `monitoring/cicd-watch.md` correctly referenced in `skills/roles/engineer.md`?  
  (Expected: listed as skill #4 under "Primary Skills")
- Is the HANDBACK `notes` field the right signal? Could Engineers be checking CI without mentioning it?

**Intervention steps:**
1. Review the most recent 3–5 Engineer HANDBACKs that scored N on M1.
2. Check: Do those HANDBACKs show any other CI signal (tests_passed field, deliverables mentioning CI fixes)?
3. If no CI signal at all: Engineers may not be checking Actions after push.
   - **Action:** Add a one-line note to `skills/roles/engineer.md` under the cicd-watch skill reference: "After every `git push`: run `gh run watch` to confirm pipeline passes before closing the task."
   - **Confirm fix:** Check next week's M1 row — expect recovery within 1–2 Engineer tasks.
4. If CI signal exists but in different form: the measurement method may need adjustment. Update the "what counts" definition in M1.

**Escalation owner:** QE  
**Fix SLA:** Within 48 hours of red flag identification

---

### M2 — Senior todo-management Below 75%

**Trigger:** M2 usage rate <75% over any two consecutive weeks (planning tasks only).

**Before escalating, check:**
- Is `orchestration/todo-management.md` correctly referenced in `skills/roles/senior-engineer.md`?  
  (Expected: listed as skill #7 under "Specialist Skills")
- Are the tasks being measured correctly filtered to planning/decomposition tasks only? Confirm N/A rows are correct.

**Intervention steps:**
1. Review the most recent 3 Senior Engineer planning-scope HANDBACKs that scored N on M2.
2. Check: Are tasks decomposed in some other form (plan.md, structured notes) but not TODO.md?
3. If decomposition exists but not in TODO.md format:
   - **Action:** Add a note to `skills/roles/senior-engineer.md` under todo-management: "When decomposing a complex task into sub-tasks, create a `TODO.md` at project root per `orchestration/todo-management.md`. Include it in HANDBACK `deliverables`."
4. If no task decomposition at all:
   - **Action:** Pair with Senior Engineer: share a working example HANDBACK that includes TODO.md as a deliverable (see `artifacts/delegates/EXAMPLE-DELEGATE-bug-fix.yaml` for format reference).
   - **Confirm fix:** Check next 2 Senior Engineer planning tasks.

**Escalation owner:** QE  
**Fix SLA:** Within 1 week of red flag trigger

---

### M3 — QE Baseline Compliance Below 80%

**Trigger:** M3 compliance rate <80% in any single week.

**Note:** This is a self-assessment metric. If QE compliance is low, QE owns the fix directly.

**Root cause checklist:**
- Which of the 3 compliance criteria are failing?
  - Missing dimensions: Which of the 8 dimensions are being skipped? Are they being assessed informally but not included in YAML?
  - Score band missing: Is the overall score being computed but not mapped to 90+/80–89/70–79/<70?
  - YAML format missing: Is feedback given in prose but not structured YAML?

**Intervention steps:**
1. If dimensions are skipped: ensure the `shared/quality-assessment-baseline.md` Section 1 checklist is consulted at assessment start.
   - **Action:** Add a "pre-flight checklist" comment at the top of each new assessment session: "8 dimensions to score: test_coverage, test_quality, readability, error_handling, documentation, security, performance, architectural_consistency"
2. If score band is missing: the YAML template in Section 4 of the baseline is the fix — copy it to start each assessment.
3. If YAML format is missing: prose is not sufficient for trend tracking. Switch to YAML-first output.
   - **Confirm fix:** Review next 2 QE assessments for full compliance.

**Escalation owner:** QE (self-correcting)  
**Fix SLA:** Immediate — within the same week

---

### M4 — Lead + QE Agreement Below 90%

**Trigger:** M4 agreement rate <90% over any two-week window.

**Before escalating, check:**
- How many disagreements are there? 1–2 in two weeks may be noise. 3+ in two weeks signals a pattern.
- What is the disagreement direction? 
  - Lead APPROVE + QE <70 (most common type: Lead too lenient, or QE too strict)
  - Lead REWORK + QE ≥80 (Lead too strict, or QE too lenient)
  
**Intervention steps:**
1. Collect all disagreement rows from M4 tracking table.
2. Look for a pattern: Is it always the same dimension driving disagreement (e.g., Lead doesn't block on test_quality, QE scores it strictly)?
3. **Action:** Schedule a 30-minute sync between Lead Engineer and QE.
   - Agenda: Review 2–3 specific disagreement examples. Determine if the issue is:
     a. A threshold calibration issue (agreed fix: update the scoring table guidance in quality-assessment-baseline.md Section 2)
     b. A dimension interpretation issue (agreed fix: add a worked example to quality-assessment-baseline.md Section 5)
     c. A role boundary issue (agreed fix: clarify in quality-assessment-baseline.md Section 3 what Lead does/doesn't block for)
4. After sync, log the calibration decision in `shared/quality-assessment-baseline.md` Section 7 (change log).
5. **Confirm fix:** Monitor M4 for next 2 weeks.

**Escalation owner:** QE schedules; Lead Engineer + QE resolve  
**Fix SLA:** Sync within 1 week of red flag; calibration fix within same week

---

### M5 — Pattern Misapplications Above 5%

**Trigger:** M5 misapplication rate >5% over any two-week window.

**Note:** M5 is primarily tracked by Lead Engineer during code review. QE collects the data from Lead's review feedback.

**Before escalating, check:**
- Which pattern is misapplied more: `api-resilience` or `event-consumer`?
- What type of misapplication is most common (missing retry, missing idempotency, improper error handling)?

**Intervention steps:**
1. Identify the most common misapplication type from M5 table.
2. Check: Is the misapplication type covered in the pattern documentation?
   - `skills/patterns/api-resilience.md` — is the expected retry/circuit-breaker contract explicit?
   - `skills/patterns/event-consumer.md` — is the idempotency requirement explicit with an example?
3. If documentation is weak:
   - **Action:** Flag to Senior Engineer (pattern owner) to add a "Common Mistakes" section with before/after code examples.
4. If documentation is clear but misapplication persists:
   - **Action:** Senior Engineer creates a detailed annotated example PR showing correct pattern implementation. Reference this example in the role file: "See example PR #{number} for correct api-resilience implementation."
5. **Confirm fix:** Monitor M5 for next 3–5 pattern PRs.

**Escalation owner:** QE flags; Senior Engineer owns pattern fix  
**Fix SLA:** Within 1 week of red flag; pattern update within same week

---

### M6 — Skill-Related Escalation Occurs

**Trigger:** Any single escalation where root cause is a skill gap or role boundary confusion.

**This is the highest-priority signal.** It means the consolidation has a gap that needs immediate repair.

**Immediate response (within 24 hours):**
1. Identify which skill was missing or which role boundary was unclear.
2. Determine which role file should have provided the skill reference.
3. Check whether:
   - The skill file exists and is correctly referenced in the role file
   - The skill file exists but the reference is missing
   - The skill file does not exist (new skill needed)
   - The role boundary is ambiguous in both role files
4. Apply the appropriate fix:
   - Missing reference: Add skill to role file's "Primary Skills" or "Specialist Skills" section
   - Missing skill file: Create new skill file in appropriate directory and add reference
   - Ambiguous boundary: Update both affected role files' "When Escalated To" and "Escalation To" sections

**Post-fix validation:**
- After updating the role file, confirm the fix is sufficient: would an Engineer reading the updated role file know what to do without escalating?
- Log the fix in [Skill Gap Fix Log](#skill-gap-fix-log).

**Escalation owner:** QE (immediate); Orchestrator provides escalation reason data  
**Fix SLA:** Same day (24 hours maximum)

---

### Skill Gap Fix Log

Record each M6-triggered fix here for audit and pattern analysis.

```
SKILL GAP FIX LOG
=================

Date       | Task ID   | Missing Skill / Unclear Boundary | Role File Updated | Fix Applied
-----------|-----------|----------------------------------|-------------------|-------------
YYYY-MM-DD | <task_id> | <description>                    | <file>            | <what changed>
```

---

## Deliverable 4: Week 4 Report Template

Complete this report at the end of Week 4. Send to: Lead Engineer, Principal Engineer, Orchestrator, Model Engineer.

---

```markdown
# Phase 4 Validation Report — Week 4 Summary

**Period:** [Start Date] to [End Date]  
**Author:** Quality Engineer  
**Status:** [COMPLETE / PARTIAL — <reason>]

---

## Executive Summary

[2–3 sentences: Did the consolidation work? What is the headline finding?]

---

## Metric Results

| Metric | Target | 4-Week Result | Status |
|--------|--------|---------------|--------|
| M1 — Engineer cicd-watch usage | ≥90% final week | __% | ✅ / ⚠️ / ❌ |
| M2 — Senior todo-management usage | ≥85% over 4 weeks | __% | ✅ / ⚠️ / ❌ |
| M3 — QE baseline compliance | ≥85% over 4 weeks | __% | ✅ / ⚠️ / ❌ |
| M4 — Lead + QE agreement | ≥93% over 4 weeks | __% | ✅ / ⚠️ / ❌ |
| M5 — Pattern misapplications | ≤7% over 4 weeks | __% | ✅ / ⚠️ / ❌ |
| M6 — Skill-gap escalations | ≤1 (with immediate fix) | __ | ✅ / ⚠️ / ❌ |

Status key: ✅ Target met | ⚠️ Near miss (within 5% of target) | ❌ Target missed

---

## Trend Analysis

### M1 — Engineer cicd-watch
- Week 1: __%
- Week 2: __%
- Week 3: __%
- Week 4: __%
- Trend: [Improving / Stable / Degrading]
- Key observation: [1 sentence]

### M2 — Senior todo-management
[same structure]

### M3 — QE baseline compliance
[same structure]

### M4 — Lead + QE agreement
[same structure]

### M5 — Pattern misapplications
[same structure]

### M6 — Skill-gap escalations
- Total escalations observed: __
- Skill-gap root cause: __
- Fixes applied: [list or "none required"]

---

## Interventions Taken

[List each intervention from the Weekly Analysis Log, one per bullet:
- Week [N]: [What triggered it] → [What was done] → [Did it work?]
]

---

## Findings

### What's Working

[Metrics that hit target without intervention — evidence that consolidation is effective]

### What Needed Tuning

[Metrics that required intervention — what the gap was, how it was fixed]

### Outstanding Concerns

[Anything still below target, or patterns that suggest deeper issues]

---

## Recommendations

**Continue tracking (recommend if):** Any metric is improving but hasn't stabilised. Extend tracking by 2 more weeks with reduced cadence (bi-weekly review instead of weekly).

**Skill reference updates needed (recommend if):** Patterns in M1–M3 suggest skill files are unclear. Specific files to update: [list]

**Declare Phase 4 complete (recommend if):** All metrics are at or above their 4-week success threshold and no skill-gap escalations in final 2 weeks.

**Escalate to Principal Engineer (recommend if):** M4 agreement <90%, M5 >10%, or more than 1 M6 skill-gap escalation with no clear root cause.

---

## Appendix: Raw Tracking Tables

[Attach or link final state of all 6 tracking tables]
```

---

## Reference: Skill File Locations

| Skill | File | Used By |
|-------|------|---------|
| CI/CD Watch | `skills/monitoring/cicd-watch.md` | Engineer, Senior, Lead, QE |
| TODO Management | `skills/orchestration/todo-management.md` | Engineer, Senior, Lead, QE |
| Quality Assessment Baseline | `shared/quality-assessment-baseline.md` | Lead, QE |
| api-resilience pattern | `skills/patterns/api-resilience.md` | Senior (owns), Engineer (implements) |
| event-consumer pattern | `skills/patterns/event-consumer.md` | Senior (owns), Engineer (implements) |

---

## Reference: Role Files for Cross-Check

When a metric misses its target, the first check is always the role file for the relevant role.

| Role | File |
|------|------|
| Engineer | `skills/roles/engineer.md` |
| Senior Engineer | `skills/roles/senior-engineer.md` |
| Lead Engineer | `skills/roles/lead-engineer.md` |
| Quality Engineer | `skills/roles/quality-engineer.md` |

---

## Phase 4 Success Criteria

Phase 4 is complete when all of the following hold in the final week:

| Criterion | Threshold |
|-----------|-----------|
| M1 — cicd-watch | ≥90% in Week 4 |
| M2 — todo-management | ≥85% over Weeks 1–4 combined |
| M3 — QE baseline compliance | ≥85% over Weeks 1–4 combined |
| M4 — Lead + QE agreement | ≥93% over Weeks 1–4 combined |
| M5 — Pattern misapplications | ≤7% over Weeks 1–4 combined |
| M6 — Skill-gap escalations | ≤1 over 4 weeks (with same-day fix) |

If all criteria are met: **Declare Phase 4 complete. Skills consolidation validated.**

If any criterion is not met: **Extend tracking by 2 weeks with targeted intervention active.**
