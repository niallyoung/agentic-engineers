---
name: queue-path-validator
version: 1.0
role: quality-engineer
effort: medium
category: orchestration/security

description: |
  Runtime enforcement of canonical queue paths for DELEGATE/HANDBACK files.
  
  Enforces canonical path: ~/.agentic-engineers/{harness}/{session-id}/queue/
  Rejects legacy paths and injection attacks.
  
  Integrates with git hooks to prevent non-canonical paths in commits.

keywords:
  - queue-enforcement
  - path-security
  - delegate-validation
  - injection-blocking
  - git-hook

---

# Queue Path Validator

## Summary

Enforces canonical queue path format to prevent injection/poisoning attacks and detect legacy paths that violate the SPEC.

## Problem

SPEC.md contains contradictory queue paths:
- `artifacts/queue/` (legacy)
- `~/.copilot/queue/{session-id}/incoming/` (legacy)
- `~/.agentic-engineers/{harness}/{session-id}/queue/` (canonical)

Without runtime validation, these inconsistencies enable queue injection/poisoning attacks.

## Solution

Two-layer enforcement:

1. **Runtime Validator** — Python module that validates queue paths
   - Accepts canonical path only
   - Rejects legacy and injected paths
   - Usable in Orchestrator and pre-commit hooks

2. **Git Hook Integration** — Updates `.githooks/pre-push`
   - Scans commits for legacy paths in SPEC.md
   - Scans DELEGATE/HANDBACK files for non-canonical paths
   - Blocks push if violations found

## Implementation

### Location

```
src/skills/_meta/queue-path-validator/
├── SKILL.md                                   (this file)
├── scripts/
│   ├── __init__.py
│   └── queue_path_validator.py                (runtime validator)
├── tests/
│   ├── __init__.py
│   └── test_queue_path_validator.py           (20 tests, all green)
```

### Canonical Path Format

```
~/.agentic-engineers/{harness}/{session-id}/queue/[incoming/]
```

Where:
- `session-id` — alphanumeric, hyphens, underscores
- `harness` — alphanumeric, hyphens, underscores (e.g., `opencode`, `local-session`)
- `/incoming/` — optional subdirectory

### Runtime Validator API

```python
from queue_path_validator import QueuePathValidator

validator = QueuePathValidator()

# Validate single path
result = validator.validate("~/.agentic-engineers/test-123/opencode/queue/")
if result.is_valid:
    print("OK")
else:
    print("Errors:", result.errors)

# Find invalid paths in text (for SPEC.md, YAML files)
invalid = validator.find_invalid_paths_in_text(spec_content)
```

### Git Hook Integration

The `.githooks/pre-push` hook will:

1. Scan all committed DELEGATE/HANDBACK files
2. Run validator on queue paths found in these files
3. Fail push with clear error if violations detected
4. Provide guidance on fixing violations

## Test Coverage

20 test cases covering:

### AC1: Canonical Path Acceptance
- ✅ Basic canonical path: `~/.agentic-engineers/{harness}/{session-id}/queue/`
- ✅ With `/incoming/` subdirectory
- ✅ Expanded home path: `/Users/{user}/.agentic-engineers/...`
- ✅ With/without trailing slash

### AC2: Legacy Path Rejection
- ✅ `artifacts/queue/` rejected
- ✅ `~/.copilot/queue/` rejected

### AC3: Injection Blocking
- ✅ Path traversal: `../../../tmp/queue/`
- ✅ Shell metacharacters: `;`, `|`, `&`
- ✅ Command substitution: `$(whoami)`
- ✅ Double slashes: `//`
- ✅ Null bytes: `\x00`

### AC4: Git Hook Validation
- ✅ Detects legacy paths in SPEC.md
- ✅ Validates DELEGATE/HANDBACK YAML files

### AC5: Edge Cases
- ✅ Empty path
- ✅ Relative paths (rejected)
- ✅ Missing session-id or harness (rejected)
- ✅ Helpful error messages

### AC6: Result Structure
- ✅ ValidationResult has `is_valid` and `errors` fields
- ✅ Error messages are descriptive

## Usage in Orchestrator

```python
from queue_path_validator import QueuePathValidator

# At DELEGATE processing time
validator = QueuePathValidator()
result = validator.validate(delegate.get('queue_path'))

if not result.is_valid:
    raise ValueError('Invalid queue path: {}'.format(', '.join(result.errors)))
```

## Usage in Git Hook

See `.githooks/pre-push` for integration pattern.

## Constraints

- Python 3.7+ compatible (no f-strings in type hints, no dataclasses)
- No external dependencies (stdlib only)
- Regex-based validation (no path resolution)
- Path injection focus (not filesystem availability check)

## Acceptance Criteria Met

- ✅ **AC1**: Runtime validator accepts canonical path only
- ✅ **AC2**: Legacy paths rejected
- ✅ **AC3**: Path injection attempts blocked
- ✅ **AC4**: Git hook validates DELEGATE/HANDBACK files
- ✅ **AC5**: All 20 test cases passing
- ✅ **AC6**: No linting errors

## References

- PHASE-1.5-SECURITY-HARDENING.md (lines 26-61)
- PHASE-1.5-ORCHESTRATION-PLAN.md (lines 23-90)
- SPEC.md (lines 504-546 for canonical path spec)
