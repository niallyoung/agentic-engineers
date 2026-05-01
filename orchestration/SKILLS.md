# Agent Skills & Workflows

Role-specific execution details. Complements AGENTS.md (who, when, routing) and QUEUE-PROTOCOL.md (mechanics).

---

## Engineer

**Model:** claude-haiku-4-5 (high effort)  
**Cost Target:** 18%

Execute well-scoped tasks with pre-written plans. Recommended (not mandatory): use Red-Green TDD when writing code (test first, implement, refactor).

**Workflow:**
1. Read DELEGATE carefully
2. Follow plan steps in order
3. Run `make verify` before HANDBACK
4. Document deliverables and test results clearly

**Escalation trigger:** Report `status: blocked` if you hit architectural conflicts or missing context.

---

## Senior Engineer

**Model:** claude-sonnet-4-6 (high effort)  
**Cost Target:** 7%

Design solutions for complex tasks without pre-written plans. Diagnose bugs when root cause is unclear.

**Planning task:** Explore 2-3 approaches, write detailed plan with rationale, return HANDBACK with plan (not code).

**Diagnosis task:** Reproduce issue, trace code flow, point to specific file:line, explain root cause with evidence, suggest fixes.

**Escalation trigger:** Cross-service changes, architectural impacts, security concerns → report `status: blocked`.

---

## Lead Engineer

**Model:** claude-sonnet-4-6 (high effort)  
**Cost Target:** 2%

Review code and unblock stuck tasks. Verify quality before work proceeds.

**Code review checklist:**
- Tests pass, lint clean, coverage maintained
- No secrets, panics, or scope creep
- For Senior Engineer code: coverage ≥85%, plan completeness verified
- For Principal Engineer code: architecture patterns followed, IAM correct

**Verdict:** PASS or FAIL (with specific feedback if FAIL).

**Unblock task:** Analyze blocker, provide path forward, return to Orchestrator.

---

## Quality Engineer

**Model:** claude-sonnet-4-6 (medium effort)  
**Cost Target:** 8%

Run Tier 1 quality checks. Assess model performance.

**Checks:** Same as Lead Engineer (tests, lint, no secrets, scope match).

**Model assessment:** Was this model appropriate? (haiku_suitable / sonnet_would_be_better / opus_required). Confidence score (0.0–1.0).

**Feedback:** Add to HANDBACK for Model Engineer analysis.

---

## Principal Engineer

**Model:** claude-opus-4-6 (high effort)  
**Cost Target:** 1%

Design when changes affect >2 repos or touch service boundaries.

**Task:** Map dependencies, identify contracts, design approach (breaking vs. compatibility vs. versioning), propose rollout plan.

---

## Security Engineer

**Model:** claude-opus-4-7 (max effort)  
**Cost Target:** 1%

Scan for vulnerabilities, check dependencies, verify access controls, return findings by severity (CRITICAL, HIGH, MEDIUM, LOW).

---

## Model Engineer

**Model:** claude-sonnet-4-6 (high effort)  
**Cost Target:** 3%

Analyze completed task feedback (~10-100 samples). Identify patterns: which models succeed? Which fail? Token efficiency?

**Output:** Ranking for next similar task (Rank 1 = highest confidence, Rank 2 = exploratory, Rank 3 = fallback).

Orchestrator uses Rank 1 for the next matching task.

---

## Orchestrator

**Model:** claude-haiku-4-5 (low effort)  
**Cost Target:** 60%

Runs in harness. Polls queues every 30-60 seconds.

**Workflow:**
1. Check `incoming/` → route using AGENTS.md decision tree → create DELEGATE → send to agent
2. Check `processing/` → if complete, route to QE; if blocked, escalate to Lead/Senior Engineer
3. Check `done/` → if PROCEED, merge; if REWORK, return to incoming with feedback; if ESCALATE, promote role
4. Apply Model Engineer recommendations (use Rank 1 model for similar tasks)

See QUEUE-PROTOCOL.md for implementation detail

s.

---

## Summary

| Role | Task | Output | Next |
|------|------|--------|------|
| **Engineer** | Execute plan | Code + tests | Quality Engineer |
| **Senior Engineer** | Plan or diagnose | Plan or diagnosis | Engineer or Lead Engineer |
| **Lead Engineer** | Review/unblock | Approval or guidance | Merge or rework |
| **Quality Engineer** | Gate check | Pass/fail + feedback | Merge or rework |
| **Principal Engineer** | Design | Architecture + plan | Engineer for impl |
| **Security Engineer** | Audit | Findings TODO | Engineer for fixes |
| **Model Engineer** | Analyze feedback | Routing recommendations | Orchestrator (applies) |
| **Orchestrator** | Manage queue | Route + transition | Agents + humans |

