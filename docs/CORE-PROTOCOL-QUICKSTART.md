---
title: Core Protocol Quickstart
version: 1.0
status: APPROVED
---

# Core Protocol Quickstart (30 minutes)

## The Basics

The protocol has two parts:
- **Core** (9 required fields) — must always be present, strictly validated
- **Extensions** (optional fields) — add when needed, loosely validated

## DELEGATE (send work to an agent)

```yaml
handoff_type: DELEGATE               # protocol identifier
spec_version: "1.0"                  # protocol spec version
task_id: my-task-2026-05-13          # kebab-case, 3-50 chars
skill: code-review                    # skill name from skills/
agent: engineer                       # who handles it
scope: "Review the authentication module for security issues and test coverage gaps in the OAuth2 flow"  # >=15 words
success_criteria:                     # >=1 item
  - "No high-severity security issues found"
  - "Test coverage >=85% on auth module"
plan:                                 # >=2 steps, >=3 words each
  - "Read auth module source code"
  - "Identify security vulnerabilities"
  - "Check test coverage gaps"
  - "Write review findings"
context: >                            # >=20 words
  The auth module handles OAuth2 login, token refresh, and session management.
  Recent changes added a new provider integration that needs security review.
```

## HANDBACK (return results)

```yaml
handoff_type: HANDBACK               # protocol identifier
spec_version: "1.0"                  # protocol spec version
task_id: my-task-2026-05-13          # must match DELEGATE task_id
status: success                       # success|failure|partial|blocked|escalate
output:                               # any structured output
  findings: []
  recommendations: []
metrics:
  quality: 0.92                       # 0.0-1.0
  tokens: 4500
  cost: 0.023
  duration_seconds: 45.2
```

## Adding Extensions

```yaml
# Extend DELEGATE with optional fields
task_id: my-task-2026-05-13
# ... core fields ...
effort: high            # low|medium|high|max
model: claude-opus-5    # any string
priority: 8             # 1-10
parent_task_id: parent-task-001
budget: 5.0
```

## Validation Rules

| Field | Rule |
|-------|------|
| task_id | kebab-case, 3-50 chars |
| scope | >=15 words |
| plan | >=2 steps, >=3 words each |
| context | >=20 words |
| metrics.quality | 0.0–1.0 float |
| metrics.tokens | non-negative integer |

## Common Mistakes

- ❌ `scope: "Fix it"` — too short (<15 words)
- ❌ `plan: ["Do everything"]` — needs >=2 steps
- ❌ `context: "Context here"` — too short (<20 words)
- ✅ Extensions with unknown fields are ignored by core validation

## See Also
- `docs/specs/protocol-core-v1.0.yaml` — full schema definition
- `docs/PROTOCOL.md` — full reference
