# Quality Validation Rules Reference

**Machine-enforced rules applied by `QualityValidator`**

This document is the authoritative reference for every validation rule applied
by the three-layer `QualityValidator` system.  It is generated from the
implementation in `orchestration/agents/quality_validator.py` and kept in sync
with code changes.

---

## Layer Overview

| Layer | When Applied | Focus | Weight in Score |
|-------|-------------|-------|----------------|
| **Layer 1** | Before routing | DELEGATE structural integrity | 40% |
| **Layer 2** | Before routing | Task quality for routing optimisation | 35% |
| **Layer 3** | After completion | HANDBACK post-completion validation | 25% |

Layer 2 is only run if Layer 1 score ≥ 50.  If Layer 1 fails catastrophically,
Layer 2 is skipped to avoid noisy false findings on top of fundamental errors.

---

## Layer 1 — Pre-routing Validation

Layer 1 validates the **structural integrity** of a DELEGATE block before it
reaches any agent.  These rules are non-negotiable.

### Rule 1.1 — `handoff_type` presence and value

| Attribute | Value |
|-----------|-------|
| Check ID | `handoff_type_missing` / `handoff_type_invalid` |
| Severity | ERROR |
| Score deduction | 15 |
| Field | `handoff_type` |

**Rationale:** Every block must declare its type so the queue processor can
distinguish DELEGATE from HANDBACK without content inspection.

**Rule:**
- `handoff_type` must be present → else `handoff_type_missing` (ERROR, −15)
- `handoff_type` must equal `"DELEGATE"` → else `handoff_type_invalid` (ERROR, −15)

---

### Rule 1.2 — `task_id` presence

| Attribute | Value |
|-----------|-------|
| Check ID | `task_id_missing` |
| Severity | CRITICAL |
| Score deduction | 25 |
| Field | `task_id` |

**Rationale:** Without a task_id there is no way to correlate HANDBACK with
DELEGATE, track retries, or de-duplicate queue entries.

**Rule:** `task_id` must be present and non-empty → else CRITICAL, −25.

---

### Rule 1.3 — `task_id` format

| Attribute | Value |
|-----------|-------|
| Check IDs | `task_id_format`, `task_id_too_long` |
| Severities | ERROR (format), WARNING (length) |
| Score deductions | 10 (format), 5 (length) |
| Field | `task_id` |

**Pattern:** `^[a-z0-9][a-z0-9\-]{0,62}[a-z0-9]$`

- Lowercase alphanumeric + hyphens only
- 2–64 characters
- No leading or trailing hyphens

Non-matching IDs → `task_id_format` (ERROR, −10).
IDs > 64 characters → `task_id_too_long` (WARNING, −5).

---

### Rule 1.4 — `role` validity

| Attribute | Value |
|-----------|-------|
| Check IDs | `role_missing`, `role_unknown` |
| Severities | ERROR (missing), WARNING (unknown) |
| Score deductions | 15 (missing), 8 (unknown) |
| Field | `role` |

**Valid roles:**
```
engineer, senior_engineer, lead_engineer, principal_engineer,
quality_engineer, model_engineer, security_engineer, orchestrator
```

- Missing `role` → ERROR, −15
- Unrecognised `role` → WARNING, −8 (routing will fall back to decision tree)

---

### Rule 1.5 — `scope` presence

| Attribute | Value |
|-----------|-------|
| Check ID | `scope_missing` |
| Severity | CRITICAL |
| Score deduction | 20 |
| Field | `scope` |

**Rule:** `scope` must be present and non-blank (not just whitespace) →
else CRITICAL, −20.

---

### Rule 1.6 — `effort` validity

| Attribute | Value |
|-----------|-------|
| Check IDs | `effort_missing`, `effort_invalid` |
| Severity | WARNING |
| Score deduction | 5 each |
| Field | `effort` |

**Valid values:** `low`, `medium`, `high`, `max`, `epic`

- Missing `effort` → WARNING, −5
- Unrecognised `effort` → WARNING, −5

---

### Rule 1.7 — Sensitive field detection

| Attribute | Value |
|-----------|-------|
| Check ID | `sensitive_field` |
| Severity | CRITICAL |
| Score deduction | 40 |
| Field | (offending field name) |

**Detected field names:** `password`, `secret`, `token`, `api_key`, `private_key`, `credential`

A DELEGATE containing any of these field names → CRITICAL, −40.

**Note:** Only the first offending field is reported per validation run to
avoid a flood of identical findings.

---

## Layer 2 — Routing Quality Validation

Layer 2 evaluates the **task quality** to enable intelligent routing decisions.
These rules are informational; a low L2 score routes the task to a senior
engineer for refinement rather than blocking it outright.

### Rule 2.1 — Scope word count (minimum)

| Attribute | Value |
|-----------|-------|
| Check IDs | `scope_too_brief` (ERROR), `scope_brief` (WARNING) |
| Score deductions | 20 (too_brief), 5 (brief) |
| Field | `scope` |

- Fewer than **5 words** → `scope_too_brief` (ERROR, −20)
- 5–14 words → `scope_brief` (WARNING, −5)
- 15+ words → no finding

---

### Rule 2.2 — Scope contains an action verb

| Attribute | Value |
|-----------|-------|
| Check ID | `scope_no_action_verb` |
| Severity | WARNING |
| Score deduction | 8 |
| Field | `scope` |

**Detected verbs (subset):** implement, create, add, fix, refactor, update, build,
design, integrate, review, test, migrate, remove, delete, investigate, analyse,
analyze, validate, configure, deploy.

If none of these words appear in the scope → WARNING, −8.

---

### Rule 2.3 — Plan required for high/max/epic effort

| Attribute | Value |
|-----------|-------|
| Check ID | `plan_required_for_high_effort` |
| Severity | ERROR |
| Score deduction | 20 |
| Field | `plan` |

Tasks with `effort: high`, `max`, or `epic` **must** include a `plan` field.

No plan + high effort → ERROR, −20.

---

### Rule 2.4 — Plan quality

| Attribute | Value |
|-----------|-------|
| Check ID | `plan_too_brief` |
| Severity | WARNING |
| Score deduction | 8 |
| Field | `plan` |

If a `plan` field is present but has fewer than 2 non-empty lines **and** fewer
than 10 words total → `plan_too_brief` (WARNING, −8).

---

### Rule 2.5 — Effort/role consistency

| Attribute | Value |
|-----------|-------|
| Check ID | `effort_role_mismatch` |
| Severity | WARNING |
| Score deduction | 5 |
| Field | `effort` |

`role: engineer` with `effort: max` or `effort: epic` is unusual.
Consider senior_engineer or lead_engineer for complex tasks.

→ WARNING, −5.

---

### Rule 2.6 — Success criteria for high-effort tasks

| Attribute | Value |
|-----------|-------|
| Check ID | `missing_success_criteria` |
| Severity | WARNING |
| Score deduction | 8 |
| Field | (none) |

For `effort: high`, `max`, or `epic`, one of the following fields should be
present: `success_criteria`, `deliverables`, `acceptance_criteria`.

None present → WARNING, −8.

---

## Layer 3 — Post-completion Validation

Layer 3 validates the **HANDBACK block** after an agent returns results.

### Rule 3.1 — `handoff_type` presence and value

| Attribute | Value |
|-----------|-------|
| Check IDs | `handback_type_missing`, `handback_type_invalid` |
| Severity | ERROR |
| Score deduction | 15 |
| Field | `handoff_type` |

`handoff_type` must equal `"HANDBACK"` → else ERROR, −15.

---

### Rule 3.2 — `task_id` presence

| Attribute | Value |
|-----------|-------|
| Check ID | `handback_task_id_missing` |
| Severity | CRITICAL |
| Score deduction | 25 |
| Field | `task_id` |

HANDBACK must include a `task_id` → else CRITICAL, −25.

---

### Rule 3.3 — `task_id` cross-reference

| Attribute | Value |
|-----------|-------|
| Check ID | `task_id_mismatch` |
| Severity | CRITICAL |
| Score deduction | 30 |
| Field | `task_id` |

If the original DELEGATE is provided, HANDBACK `task_id` must exactly match
the DELEGATE `task_id` → else CRITICAL, −30.

---

### Rule 3.4 — `status` validity

| Attribute | Value |
|-----------|-------|
| Check IDs | `handback_status_missing`, `handback_status_invalid` |
| Severities | ERROR |
| Score deductions | 15 (missing), 10 (invalid) |
| Field | `status` |

**Valid values:** `complete`, `failed`, `partial`

- Missing → ERROR, −15
- Invalid → ERROR, −10

---

### Rule 3.5 — `notes` presence

| Attribute | Value |
|-----------|-------|
| Check ID | `handback_notes_missing` |
| Severity | WARNING |
| Score deduction | 8 |
| Field | `notes` |

`notes` must be present and non-blank → else WARNING, −8.

---

### Rule 3.6 — Failed without explanation

| Attribute | Value |
|-----------|-------|
| Check ID | `failed_without_reason` |
| Severity | ERROR |
| Score deduction | 15 |
| Field | `notes` |

When `status: failed`, `notes` must contain at least 5 words explaining the
failure → else ERROR, −15.

---

### Rule 3.7 — Engineering HANDBACK includes `tests_passed`

| Attribute | Value |
|-----------|-------|
| Check ID | `tests_passed_missing` |
| Severity | WARNING |
| Score deduction | 5 |
| Field | (none) |

For engineering roles (`engineer`, `senior_engineer`, `lead_engineer`,
`principal_engineer`), the HANDBACK should include a `tests_passed` field
(e.g. `47/47`) → else WARNING, −5.

Only checked when the original DELEGATE is provided to determine the role.

---

## Composite Score Calculation

```
layer1_weight = 40
layer2_weight = 35
layer3_weight = 25

composite = (l1_score * layer1_weight + l2_score * layer2_weight + l3_score * layer3_weight)
            / (sum of weights for layers actually run)
```

If a layer is not run (e.g., Layer 3 when only validating a DELEGATE), its
weight is redistributed proportionally across layers that were run.

---

## Routing Decision Map

```
CRITICAL finding present OR score < 40  →  CRITICAL  →  escalate_with_analysis
80 ≤ score ≤ 100                        →  HIGH      →  direct_dispatch
60 ≤ score < 80                         →  MEDIUM    →  route_to_lead_engineer
40 ≤ score < 60                         →  LOW       →  route_to_principal_engineer
```

---

## Severity Reference

| Severity | Impact | Examples |
|----------|--------|---------|
| `critical` | Forces CRITICAL routing regardless of score | Missing task_id, task_id mismatch, secrets in DELEGATE |
| `error` | Significant score deduction | Missing handoff_type, invalid status, scope too brief |
| `warning` | Minor score deduction | Missing effort, brief plan, missing tests_passed |
| `info` | No score impact | Informational only (reserved for future use) |

---

## Quick Reference — Check IDs

### Layer 1
| Check ID | Severity | Deduction |
|----------|----------|-----------|
| `handoff_type_missing` | ERROR | −15 |
| `handoff_type_invalid` | ERROR | −15 |
| `task_id_missing` | CRITICAL | −25 |
| `task_id_format` | ERROR | −10 |
| `task_id_too_long` | WARNING | −5 |
| `role_missing` | ERROR | −15 |
| `role_unknown` | WARNING | −8 |
| `scope_missing` | CRITICAL | −20 |
| `effort_missing` | WARNING | −5 |
| `effort_invalid` | WARNING | −5 |
| `sensitive_field` | CRITICAL | −40 |

### Layer 2
| Check ID | Severity | Deduction |
|----------|----------|-----------|
| `scope_too_brief` | ERROR | −20 |
| `scope_brief` | WARNING | −5 |
| `scope_no_action_verb` | WARNING | −8 |
| `plan_required_for_high_effort` | ERROR | −20 |
| `plan_too_brief` | WARNING | −8 |
| `effort_role_mismatch` | WARNING | −5 |
| `missing_success_criteria` | WARNING | −8 |

### Layer 3
| Check ID | Severity | Deduction |
|----------|----------|-----------|
| `handback_type_missing` | ERROR | −15 |
| `handback_type_invalid` | ERROR | −15 |
| `handback_task_id_missing` | CRITICAL | −25 |
| `task_id_mismatch` | CRITICAL | −30 |
| `handback_status_missing` | ERROR | −15 |
| `handback_status_invalid` | ERROR | −10 |
| `handback_notes_missing` | WARNING | −8 |
| `failed_without_reason` | ERROR | −15 |
| `tests_passed_missing` | WARNING | −5 |
