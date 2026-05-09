# Protocol Quick Reference

> **One-page cheat sheet.** Full details in [ORCHESTRATION-PROTOCOL.md](ORCHESTRATION-PROTOCOL.md).

---

## DELEGATE Essentials

**Required fields (9 core):**
`task_id` · `role` · `model` · `effort` · `estimated_hours` · `scope` · `success_criteria` · `plan` · `context`

**task_id format:** `YYYY-MM-DD-kebab-case`  
Example: `2026-05-09-add-jwt-validation`

**Effort bands:**
| Level | Hours | Min Role |
|-------|-------|----------|
| `low` | 1–4h | engineer |
| `medium` | 5–16h | engineer |
| `high` | 17–48h | senior_engineer |
| `max` | 49–120h | lead_engineer |
| `epic` | 121h+ | principal_engineer |

**scope:** ≥15 words + action verb + named subject  
**success_criteria:** Testable in 30s without reading implementation (not "good code")  
**plan:** Numbered steps, concrete actions, must include a testing step

---

## Validation Gates (enforced by pre-commit hook)

| Group | Type | Failure = |
|-------|------|-----------|
| **A — Structure** | Hard gate | Block immediately |
| **B — Content** | Quality gate | Refine before sending |
| **C — Routing** | Sanity gate | Re-route |

---

## HANDBACK Essentials

**Required fields (12):**
`task_id` · `handoff_type` · `status` · `deliverables` · `tests` · `quality_score` ·  
`effort_actual` · `tokens_in` · `tokens_out` · `duration_minutes` · `notes` · `agent`

**Status values:** `complete` · `failed` · `partial` · `blocked`

**Quality routing:**

| Score | Action | Who |
|-------|--------|-----|
| **90–100** | Merge immediately ✅ | Automated |
| **80–89** | Merge with notes ✅ | Automated |
| **70–79** | Lead Engineer review ⚠️ | Lead Engineer |
| **60–69** | Auto-rework 🔄 | Decision Engine |
| **<60** | Escalate 🚨 | Principal Engineer |
| **Critical** | Escalate immediately 🚨 | Principal Engineer |

> **Important:** Validator-computed score is **authoritative**. Agent self-score is for calibration only.

---

## Retry Rules

```
MAX_RETRIES = 2   (hard cap, no exceptions)

Retry 1 task_id: {original-id}-retry-1
Retry 2 task_id: {original-id}-retry-2
Escalated:       {original-id}-escalated
```

Each retry DELEGATE **must include** `retry_context` block:
```yaml
retry_context:
  original_task_id: ...
  retry_count: 1
  previous_quality_score: 65
  failure_reasons: [...]
  specific_failures: [...]
```

---

## Red Flags (pre-commit hook blocks these)

```
❌ task_id format invalid or reused in same session
❌ role not in valid list (engineer, senior_engineer, lead_engineer,
   principal_engineer, security_engineer, quality_engineer, model_engineer)
❌ scope < 15 words or vague ("implement it", "fix things")
❌ success_criteria aspirational ("good code", "clean code", "works well")
❌ secrets found in DELEGATE text (password, token, api_key, secret)
❌ effort:low with plan having >8 steps (under-estimation)
❌ effort:high/max with role:engineer (role too junior)
```

---

## Scoring Formula

```
composite = (layer1 × 0.40) + (layer2 × 0.35) + (layer3 × 0.25)
```

| Layer | Weight | What it measures |
|-------|--------|-----------------|
| Layer 1 | 40% | Format / structural integrity |
| Layer 2 | 35% | Content quality / criteria met |
| Layer 3 | 25% | Post-completion / QE assessment |

---

## Escalation Paths

| Trigger | Target |
|---------|--------|
| Score <60 | Principal Engineer |
| Critical finding (any score) | Principal Engineer immediately |
| Agent `status: blocked` | Role one level up |
| Retry count >2 | Principal Engineer |
| Engineer blocked | Senior Engineer |
| Senior blocked | Lead Engineer |
| Lead blocked | Principal Engineer |

**How to escalate:** Set `status: blocked` in HANDBACK with clear explanation.  
Orchestrator routes automatically to the appropriate higher role.

---

## Metrics (Automatic)

Stored at: `artifacts/metrics/YYYY-MM-DD-{task_id}-metrics.yaml`

Key collected: `tokens_in` · `tokens_out` · `duration_minutes` · `quality_score` · `retry_count`  
Key derived: `efficiency_score` = quality / (tokens/1000) · `rework_cost_ratio` = total_tokens / first_attempt_tokens

`flag_for_model_engineer: true` when cost overrun >50% or retry_count ≥ 2.

---

## Role Quick Map

| Role | Model | Use For |
|------|-------|---------|
| engineer | Haiku | Well-planned, well-scoped tasks |
| senior_engineer | Sonnet | Complex coding; no pre-written plan |
| lead_engineer | Sonnet | Code review; gray-zone HANDBACK decisions |
| quality_engineer | Sonnet | Post-implementation validation |
| principal_engineer | Opus | Cross-service architecture; escalations |
| security_engineer | Opus | Security scope only |
| model_engineer | Sonnet | Metrics analysis; routing optimization |

---

> Full protocol: `orchestration/ORCHESTRATION-PROTOCOL.md`  
> Onboarding: `orchestration/AGENT-ONBOARDING.md`  
> Status: `orchestration/PROTOCOL-IMPLEMENTATION-STATUS.md`
