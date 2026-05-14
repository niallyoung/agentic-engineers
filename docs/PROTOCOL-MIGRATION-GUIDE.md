---
title: Protocol Migration Guide — Old → Simplified (Phase 3)
version: 1.0
status: APPROVED
---

# Protocol Migration Guide

## Overview

Phase 3 simplifies the DELEGATE/HANDBACK protocol into a minimal **Core** (7 fields)
plus optional **Extensions**. This migration is **100% backward compatible**.

## What Changed

### DELEGATE

| Before (old required) | After (Phase 3) | Notes |
|----------------------|-----------------|-------|
| `task_id` | Core ✅ | Pattern relaxed: any kebab-case 3-50 chars |
| `role` | Renamed → `agent` | Old `role` field treated as extension |
| `model` | Extension (optional) | Was required, now optional |
| `effort` | Extension (optional) | Was required, now optional |
| `estimated_hours` | Extension (optional) | Was required, now optional |
| `scope` | Core ✅ | >=15 words (unchanged) |
| `success_criteria` | Core ✅ | Unchanged |
| `plan` | Core ✅ | Simplified: array of strings (>=2 items) |
| `context` | Core ✅ | >=20 words (unchanged) |
| — | `skill` | New required core field |
| — | `agent` | New name for role |

### HANDBACK

| Before (old required) | After (Phase 3) | Notes |
|----------------------|-----------------|-------|
| `task_id` | Core ✅ | Unchanged |
| `status` | Core ✅ | Enum: success|failure|partial|blocked|escalate |
| `deliverables` | Extension (optional) | Was required, now optional |
| `tests` | Extension (optional) | Was required, now optional |
| `quality_score` | Part of `metrics.quality` | Moved into metrics object |
| — | `output` | New required core field (replaces deliverables+tests) |
| — | `metrics` | New required core field (quality+tokens+cost+duration) |

## No Action Required for Existing Code

Old DELEGATEs with `role`, `model`, `effort` fields are still accepted.
The core validator ignores fields it doesn't recognize; the extension validator
validates any optional fields loosely.

**Your old DELEGATEs still work unchanged.**

## Recommended Migration Steps

1. **Add `skill` field** to your DELEGATEs (required in Phase 3 core)
2. **Rename `role` → `agent`** (optional, both accepted)
3. **Move `model`/`effort` to extensions** — they're optional now
4. **Run core validator**: `CoreProtocolValidator().validate_delegate_core(your_delegate)`

## Validator Usage

```python
from skills.queue_management.scripts.core_protocol_validator import (
    CoreProtocolValidator,
    ExtensionValidator
)

validator = CoreProtocolValidator()
ext_validator = ExtensionValidator()

# Validate core (strict, fast)
valid, errors = validator.validate_delegate_core(my_delegate)

# Validate extensions (loose, fast)
ext_valid, ext_errors = ext_validator.validate_extensions(my_delegate)

# Both must pass for full compliance
is_valid = valid and ext_valid
```

## Backward Compatibility Test

```python
# Old-format delegate (with effort, model, role) still passes
old_delegate = {
    "task_id": "my-task-001",
    "skill": "code-review",      # add this new field
    "agent": "engineer",          # was "role"
    "scope": "...",
    "success_criteria": [...],
    "plan": [..., ...],
    "context": "...",
    # Extension fields (optional, still accepted):
    "effort": "high",
    "model": "claude-opus-4.7",
    "estimated_hours": 24,
}
```
