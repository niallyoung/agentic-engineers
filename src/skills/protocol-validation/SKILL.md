---
name: protocol-validation
description: Canonical DELEGATE/HANDBACK schema validation for agentic-engineers. The single source of truth that the evaluation framework, renderer, and queue system all delegate to. Exposes validate_delegate() and validate_handback() returning (valid, errors).
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.7+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: validation
  role: orchestrator
  model: claude-haiku-4.5
  effort: high
  thinking: false
  dependencies: []
---

# protocol-validation

## Overview

`protocol-validation` is the **single canonical validator** for DELEGATE and
HANDBACK protocol blocks across the entire agentic-engineers platform. Before
this skill existed, the same HANDBACK/DELEGATE schema was validated in three
separate places that could drift apart:

- `src/skills/queue-management/scripts/core_protocol_validator.py`
- `renderer/validate_agents.py`
- `src/evals/skill_matrix/protocol.py` (the eval framework's copy)

Those copies now delegate to this skill, so there is exactly one place where the
protocol schema is defined and enforced.

**What it does:**

1. **Validate DELEGATE blocks** — 7 required core fields (`task_id`, `skill`,
   `agent`, `scope`, `success_criteria`, `plan`, `context`) plus loose
   extension fields (`effort`, `model`, `budget`, `priority`, `deadline`,
   `dependencies`, `parent_task_id`, `retry_context`).
2. **Validate HANDBACK blocks** — 4 required core fields (`task_id`, `status`,
   `output`, `metrics` with `quality`/`tokens`/`cost`/`duration_seconds`) plus
   loose extension fields (`retry_count`, `model_used`, `effort_actual`,
   `flags`, `error`, `children_created`, `children_results`).
3. **Return a simple result** — `(valid: bool, errors: list[str])` so callers
   can branch on validity and surface human-readable error messages.

**Why it matters:**

- **One source of truth** — evals, renderers, and the queue all enforce the
  exact same rules; no drift, no surprises.
- **Fast** — pure-Python field checks, no I/O on the hot path (<5ms).
- **Stable API** — `validate_delegate` / `validate_handback` are the contract;
  internals can change without breaking callers.

## Public API

```python
from protocol_validation import validate_delegate, validate_handback

valid, errors = validate_delegate(delegate_dict)
# valid: bool — True only when there are zero core AND extension errors
# errors: list[str] — human-readable messages, empty when valid

valid, errors = validate_handback(handback_dict)
```

The class-based validators (`CoreProtocolValidator`, `ExtensionValidator`) are
also exported for backward compatibility with callers that previously imported
them from `queue-management`.

## Validation rules

### DELEGATE — required core fields

| Field | Rule |
|-------|------|
| `task_id` | kebab-case, 3–50 chars |
| `skill` | must exist in `src/skills/` or `skills/` |
| `agent` | one of the 8 valid agent roles |
| `scope` | string, ≥15 words |
| `success_criteria` | non-empty array |
| `plan` | array, ≥2 steps, each step ≥3 words |
| `context` | string ≥20 words, or non-empty array |

### HANDBACK — required core fields

| Field | Rule |
|-------|------|
| `task_id` | non-empty string |
| `status` | one of `success`, `failure`, `partial`, `blocked`, `escalate` |
| `output` | key must be present (any value) |
| `metrics` | object with `quality` (0.0–1.0), `tokens` (int ≥0), `cost` (≥0), `duration_seconds` (≥0) |

Extension fields are validated loosely: if present they must have the right
type, but they never make an otherwise-valid block invalid by their absence.

## Usage

### As a library

```python
from protocol_validation import validate_handback

handback = {
    "task_id": "fix-type-error",
    "status": "success",
    "output": "Done.",
    "metrics": {"quality": 0.95, "tokens": 1200, "cost": 0.03, "duration_seconds": 42},
}
valid, errors = validate_handback(handback)
assert valid, errors
```

### Callers that delegate to this skill

- **Evaluation framework** (`src/skills/_meta/evaluation_framework/framework.py`)
  validates every captured HANDBACK against this skill before grading a test.
- **Renderer** (`renderer/validate_agents.py`) imports `validate_handback` for
  runtime HANDBACK dict validation.
- **Queue management** (`core_protocol_validator.py`) re-exports the canonical
  validators from this skill.

## Testing

```bash
python3 -m pytest src/skills/protocol-validation/tests/ -v
```

Tests cover valid and invalid cases for both DELEGATE and HANDBACK, including
core-field failures (missing/malformed required fields) and extension-field
failures (wrong types on optional fields).

## Directory layout

```
src/skills/protocol-validation/
├── SKILL.md
├── scripts/
│   ├── __init__.py
│   └── protocol_validation.py     # canonical validator + public API
└── tests/
    ├── __init__.py
    └── test_protocol_validation.py
```
