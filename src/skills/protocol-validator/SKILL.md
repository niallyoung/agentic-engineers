---
name: protocol-validator
description: Runtime protocol validation for DELEGATEs/HANDBACKs against protocol-core-v1.0.yaml. Validates core fields, extensions, and unknown fields with forward-compatibility support. <5ms validation time.
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.8+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: validation
  role: orchestrator
  model: claude-haiku-4.5
  effort: high
  thinking: false
  dependencies:
    - queue-management (for CoreProtocolValidator)
    - PyYAML (for spec loading)
---

# protocol-validator

## Overview

Protocol-Validator skill provides runtime validation of DELEGATE and HANDBACK messages against
the canonical protocol specification (`docs/specs/protocol-core-v1.0.yaml`). It validates both core
(required) fields and extension (optional) fields with forward-compatibility support for unknown
future fields.

**What it does:**

1. **Load Spec at Runtime** — Load `docs/specs/protocol-core-v1.0.yaml` once, cache in memory
2. **Validate Core Fields** — Strict validation of 7 required DELEGATE fields and 4 required HANDBACK fields
3. **Validate Extensions** — Loose validation of optional fields; unknown fields logged as warnings
4. **Forward-Compatibility** — Schema evolution supported; future fields don't break current validators
5. **Performance** — <5ms per validation (core <1ms, extensions <2ms)
6. **Enum Drift Detection** — Scan codebase for HANDBACK status enum divergence (success/failure/etc.)
7. **Protocol Divergence Detection** — Detect multiple independent escalation/validation implementations

**Why it matters:**

- **Decoupled Validation** — Extracted from orchestrator, can be called by any agent
- **Runtime Spec Updates** — Protocol improvements via DELEGATE/HANDBACK loaded dynamically
- **Unknown Field Handling** — Allows schema to evolve without breaking old code
- **Traceability** — All validations logged with context (task_id, field, reason)
- **Integration Ready** — Works with consistency-checker and orchestrator

---

## Invocation

### Programmatic Interface

```python
from skills.protocol_validator.scripts import ProtocolValidator

# Initialize validator (loads spec once, cached)
validator = ProtocolValidator(spec_path="docs/specs/protocol-core-v1.0.yaml")

# Validate DELEGATE
delegate = {
    "task_id": "feature-x-001",
    "skill": "queue-management",
    "agent": "senior-engineer",
    "scope": "Implement feature X with comprehensive testing and documentation across all modules",
    "success_criteria": ["All tests pass", "Code reviewed and approved"],
    "plan": ["Design API", "Implement core logic", "Write tests", "Document"],
    "context": "Feature X is critical for Q3 roadmap. See SPEC.md for detailed requirements and acceptance criteria.",
}

result = validator.validate_delegate(delegate)
if result.valid:
    print(f"✅ DELEGATE '{delegate['task_id']}' is valid")
else:
    print(f"❌ Validation errors: {result.errors}")
    print(f"⚠️  Warnings (unknown fields): {result.warnings}")

# Validate HANDBACK
handback = {
    "task_id": "feature-x-001",
    "status": "success",
    "output": {"feature_implemented": True, "tests_passing": 1203},
    "metrics": {
        "quality": 0.96,
        "tokens": 45000,
        "cost": 0.32,
        "duration_seconds": 3600,
    }
}

result = validator.validate_handback(handback)
if result.valid:
    print(f"✅ HANDBACK for '{handback['task_id']}' is valid")
else:
    print(f"❌ Validation errors: {result.errors}")
```

### CLI Interface

```bash
# Validate a DELEGATE from file
python -m skills.protocol_validator --delegate path/to/delegate.yaml

# Validate a HANDBACK from file
python -m skills.protocol_validator --handback path/to/handback.yaml

# Validate and get JSON output for integration
python -m skills.protocol_validator --delegate path/to/delegate.yaml --json

# Load custom spec
python -m skills.protocol_validator --delegate path/to/delegate.yaml --spec path/to/custom-spec.yaml
```

---

## Protocol Specification

The validator loads specification from `docs/specs/protocol-core-v1.0.yaml`. Protocol version 1.0 defines:

### DELEGATE Core Fields (7 required)

| Field | Type | Rules |
|-------|------|-------|
| `task_id` | string | Kebab-case, 3-50 chars, matches `^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$` |
| `skill` | string | Must exist in `skills/` directory |
| `agent` | string | One of: orchestrator, engineer, senior-engineer, lead-engineer, principal-engineer, security-engineer, quality-engineer, model-engineer |
| `scope` | string | ≥15 words, describes what will be done to what |
| `success_criteria` | array | ≥1 items, each describing a measurable outcome |
| `plan` | array | ≥2 items, each ≥3 words (minimum 9 chars), describes steps |
| `context` | string or array | String: ≥20 words OR Array: ≥1 items of strings |

### HANDBACK Core Fields (4 required)

| Field | Type | Rules |
|-------|------|-------|
| `task_id` | string | Must match a DELEGATE task_id |
| `status` | string | One of: success, failure, partial, blocked, escalate |
| `output` | any | Any structured output from the task |
| `metrics` | object | Required subfields: quality (0.0-1.0), tokens (≥0), cost (≥0), duration_seconds (≥0) |

### Extension Fields (Optional, Forward-Compatible)

Extensions are validated with loose rules. Unknown fields are logged as warnings but don't fail validation.

**DELEGATE extensions:** parent_task_id, effort, model, budget, deadline, retry_context, dependencies, priority

**HANDBACK extensions:** children_created, children_results, retry_count, model_used, effort_actual, flags, error

---

## Implementation Details

### Validation Result Format

```python
class ValidationResult:
    valid: bool  # True if no core errors
    errors: List[str]  # Core validation failures (if valid=False, these block execution)
    warnings: List[str]  # Extension validation issues or unknown fields (informational only)
    duration_ms: float  # Validation execution time
    field_types: Dict[str, str]  # Inferred types for each field (for debugging)
```

### Performance Characteristics

- **Spec Loading** — Once at initialization, <10ms
- **Core Validation** — <1ms (7 field checks, 6 regex/enum checks, 1 existence check)
- **Extension Validation** — <2ms (loose checks, early exit on unknown fields)
- **Total per Call** — <5ms (cached spec, no I/O)

### Caching & Memory

- Spec loaded once at initialization, cached in process memory (~5KB)
- Regex patterns compiled once, cached
- No disk I/O after initialization
- Thread-safe: validator instance can be shared across threads

### Forward-Compatibility

The validator is designed to support schema evolution:

1. **Unknown Fields** — Logged as warnings, don't cause validation failure
2. **New Spec Versions** — Load new spec, validate against it (supports major version bumps)
3. **Field Deprecation** — Old code validates against old spec, new code against new spec
4. **Gradual Migration** — consistency-checker can report schema version mismatch

---

## Integration

### With Queue-Management

```python
from skills.queue_management.scripts import QueueOperations
from skills.protocol_validator.scripts import ProtocolValidator

queue = QueueOperations(session_id="my-session")
validator = ProtocolValidator()

# Validate before queueing
delegate = {...}
result = validator.validate_delegate(delegate)
if not result.valid:
    print(f"Validation failed: {result.errors}")
    raise ValueError("Invalid DELEGATE")

queue.create_delegate(**delegate)
```

### With Orchestrator

The Orchestrator should:
1. Initialize validator at startup
2. Call `validator.validate_delegate()` before routing
3. Call `validator.validate_handback()` before accepting completion
4. Log validation results (valid DELEGATEs don't need logging; failures logged with context)

### With Consistency-Checker

The consistency-checker uses protocol-validator to check queue integrity:
1. Load all DELEGATEs from queue
2. Run `validator.validate_delegate()` on each
3. Aggregate results: count passes/failures/warnings
4. Report: schema compliance percentage, unknown fields, deprecated patterns

---

## Testing

### Unit Tests

```python
# tests/test_protocol_validator.py

def test_validate_delegate_core_all_required_fields_present():
    """All 7 core fields present => valid"""

def test_validate_delegate_missing_task_id():
    """Missing task_id => error"""

def test_validate_delegate_invalid_task_id_format():
    """task_id not kebab-case => error"""

def test_validate_delegate_scope_word_count():
    """scope must be >=15 words"""

def test_validate_delegate_plan_step_count():
    """plan must have >=2 steps, each >=3 words"""

def test_validate_handback_core_all_required_fields():
    """All 4 core fields present => valid"""

def test_validate_handback_metrics_quality_range():
    """quality must be 0.0-1.0"""

def test_validate_extensions_unknown_field_logged_as_warning():
    """Unknown field foo => warning, not error"""

def test_validate_extensions_forward_compatibility():
    """New schema fields handled gracefully"""

def test_validate_performance_under_5ms():
    """Validation completes in <5ms"""
```

### Coverage Target

- **Line Coverage** — ≥95%
- **Branch Coverage** — ≥90%
- **Critical Paths** — 100% (core validation, performance)

---

## Error Messages

Validation errors are designed to be actionable and context-aware:

```
"task_id: must be kebab-case, 3-50 chars (got 'TaskID001')"
"scope: must be >=15 words (13 provided)"
"plan[1]: each step must be >=3 words (got 'Test it')"
"skill: unknown skill 'foo-bar' (not found in skills/)"
"agent: invalid agent 'agent-xyz' (must be one of [...] )"
"metrics.quality: must be 0.0-1.0 (got 1.5)"
```

Warnings are informational:

```
"Unknown field 'foo_bar' in DELEGATE (will be ignored)"
"Extension field 'deprecated_field' is no longer recommended (see MIGRATION-GUIDE.md)"
```

---

## References

- `docs/specs/protocol-core-v1.0.yaml` — Canonical protocol specification
- `skills/queue-management/` — CoreProtocolValidator reference impl
- `docs/CORE-PROTOCOL-QUICKSTART.md` — Protocol 101
- `docs/PROTOCOL-MIGRATION-GUIDE.md` — Migration from older versions

---

## Version History

### v1.0 (Current)
- Initial release with Phase 4 implementation
- Core + Extension validation
- Forward-compatibility for unknown fields
- <5ms performance target met
