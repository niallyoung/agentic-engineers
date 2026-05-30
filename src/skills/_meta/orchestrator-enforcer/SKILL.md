---
# Skill metadata (follows agentskills.io spec)
name: orchestrator-enforcer
title: Orchestrator Enforcement Decorator
version: 1.0.0
author: Principal Engineer
created: 2026-05-30
updated: 2026-05-30

description: |
  Runtime enforcement of DELEGATE field requirements via decorators.
  Prevents DELEGATEs from bypassing critical field validation and orchestrator
  from processing non-compliant work before execution.

role: principal-engineer
effort: high
priority: normal

purpose: |
  Provide runtime enforcement of DELEGATE field requirements via decorators.
  Prevents DELEGATEs from bypassing critical field validation and enables
  orchestrator to reject non-compliant work before execution.

scope: |
  Implements @enforce_delegate_requirement decorator for pre-function validation.
  
  Features:
  - Validates required fields in DELEGATE dicts
  - Enforces allowed values for specific fields
  - Supports stacking multiple decorators
  - Provides clear, actionable error messages
  - Stores delegate metadata for debugging
  
  Primary use case: Security-scoped DELEGATE enforcement
  @enforce_delegate_requirement('security_scope', allowed_values=['auth','crypto'])
  @enforce_delegate_requirement('approval_gate', required=True)
  def route_to_security_engineer(delegate):
      # Won't execute if requirements not met
      ...

dependencies: []

---

## Overview

The Orchestrator needs runtime enforcement mechanisms to ensure DELEGATEs meet
field requirements before functions execute. Without this, a malformed DELEGATE
can pass through to a handler function, causing unexpected behavior or security
issues.

The **Orchestrator Enforcement Decorator** provides a declarative way to specify
field constraints via Python decorators. Multiple decorators can be stacked to
enforce independent constraints.

## Core Components

### 1. DelegateRequirementViolation Exception

Custom exception that captures validation failures with full DELEGATE metadata.

```python
class DelegateRequirementViolation(Exception):
    """Exception raised when DELEGATE fails requirement validation."""
    
    def __init__(self, message, field_name, delegate, 
                 current_value=None, allowed_values=None):
        # Stores field name, delegate dict, current value, allowed values
        # Enables detailed error reporting and debugging
```

**Attributes:**
- `message`: Human-readable error message
- `field_name`: Name of the field that failed validation
- `delegate`: Complete DELEGATE dict (full context for debugging)
- `current_value`: Actual value of the field (for value-based failures)
- `allowed_values`: List of allowed values (if validation is value-based)

### 2. enforce_delegate_requirement Decorator Factory

Creates decorators for field-level validation. Designed for stacking.

```python
@enforce_delegate_requirement(field_name, allowed_values=None, required=True)
def my_handler(delegate):
    # Function body
```

**Parameters:**
- `field_name` (str, required): Name of the field to validate
- `allowed_values` (list, optional): List of acceptable values. If provided,
  field value must be in this list.
- `required` (bool, optional, default=True): If True, field must exist in delegate.
  If False, field is optional but must match allowed_values if present.

**Behavior:**
1. Validates that first argument is a dict (assumed to be DELEGATE)
2. Checks if required field exists (if required=True)
3. Checks if field value is in allowed_values (if allowed_values specified)
4. If validation passes, calls wrapped function unchanged
5. If validation fails, raises DelegateRequirementViolation with context

**Error Messages Include:**
- Field name
- Current value (if applicable)
- Allowed values (if applicable)
- task_id from DELEGATE (for traceability)

## Usage Examples

### Example 1: Single Decorator (Required Field)

```python
@enforce_delegate_requirement('role', required=True)
def assign_work(delegate):
    return f"Assigning to {delegate['role']}"

# Valid:
assign_work({'task_id': 'TASK-001', 'role': 'engineer'})
# Returns: "Assigning to engineer"

# Invalid:
assign_work({'task_id': 'TASK-002'})
# Raises: DelegateRequirementViolation
#   message: "Required field 'role' missing from DELEGATE TASK-002"
```

### Example 2: Single Decorator (Allowed Values)

```python
@enforce_delegate_requirement(
    'security_scope', 
    allowed_values=['auth', 'crypto', 'pii']
)
def route_to_security(delegate):
    return f"Routing to security ({delegate['security_scope']})"

# Valid:
route_to_security({'task_id': 'TASK-003', 'security_scope': 'auth'})
# Returns: "Routing to security (auth)"

# Invalid:
route_to_security({'task_id': 'TASK-004', 'security_scope': 'network'})
# Raises: DelegateRequirementViolation
#   message: "Field 'security_scope' has invalid value 'network' in DELEGATE TASK-004. 
#            Allowed values: ['auth', 'crypto', 'pii']"
```

### Example 3: Stacked Decorators (from Spec)

```python
@enforce_delegate_requirement('security_scope', allowed_values=['auth', 'crypto'])
@enforce_delegate_requirement('approval_gate', required=True)
def route_to_security_engineer(delegate):
    return f"Approved: {delegate['approval_gate']}, Scope: {delegate['security_scope']}"

# Valid:
route_to_security_engineer({
    'task_id': 'TASK-005',
    'security_scope': 'auth',
    'approval_gate': 'approved'
})
# Returns: "Approved: approved, Scope: auth"

# Invalid (fails inner decorator):
route_to_security_engineer({
    'task_id': 'TASK-006',
    'security_scope': 'invalid',
    'approval_gate': 'approved'
})
# Raises: DelegateRequirementViolation (from security_scope check)

# Invalid (fails outer decorator):
route_to_security_engineer({
    'task_id': 'TASK-007',
    'security_scope': 'auth'
    # approval_gate missing
})
# Raises: DelegateRequirementViolation (from approval_gate check)
```

### Example 4: Optional Field with Allowed Values

```python
@enforce_delegate_requirement(
    'priority',
    allowed_values=['low', 'medium', 'high'],
    required=False  # Field is optional
)
def schedule_task(delegate):
    priority = delegate.get('priority', 'medium')
    return f"Scheduled with priority: {priority}"

# Valid (field present):
schedule_task({'task_id': 'TASK-008', 'priority': 'high'})
# Returns: "Scheduled with priority: high"

# Valid (field absent):
schedule_task({'task_id': 'TASK-009'})
# Returns: "Scheduled with priority: medium"

# Invalid (present but invalid):
schedule_task({'task_id': 'TASK-010', 'priority': 'critical'})
# Raises: DelegateRequirementViolation
```

## Decorator Stacking Semantics

Decorators are applied from bottom to top (standard Python behavior). Validation
occurs in reverse order of decorator application.

```python
@enforce_1  # Applied 3rd, validated 1st
@enforce_2  # Applied 2nd, validated 2nd
@enforce_3  # Applied 1st, validated 3rd
def my_function(delegate):
    pass
```

When `my_function` is called:
1. enforce_3 validates
2. If valid, enforce_2 validates
3. If valid, enforce_1 validates
4. If all valid, my_function executes

**Important:** If any decorator fails, the entire call stack stops and raises
`DelegateRequirementViolation`. No further decorators are evaluated.

## Error Message Format

Error messages are designed to be actionable. Key information included:

```
Required field '{field_name}' missing from DELEGATE {task_id}
```

or

```
Field '{field_name}' has invalid value '{current_value}' in DELEGATE {task_id}.
Allowed values: {allowed_values}
```

All three pieces of information (field name, current value, allowed values) are
included in the exception message to support debugging and logging.

## Implementation Details

### Type Safety
- First argument must be a dict (assumed to be DELEGATE)
- If not a dict, raises DelegateRequirementViolation immediately
- Supports Python 3.7+ (uses functools.wraps for proper decorator composition)

### Preserved Function Behavior
- Decorated function return value is unchanged
- Function arguments beyond the delegate are passed through correctly
- Function is wrapped with functools.wraps to preserve metadata

### Exception Metadata
- Full DELEGATE dict stored in exception for debugging
- Field name accessible via `exception.field_name`
- Current value accessible via `exception.current_value`
- Allowed values accessible via `exception.allowed_values`

## Testing

Test suite includes 33 tests covering:

1. **Exception Behavior (3 tests)**
   - Creation with metadata
   - Field name accessibility
   - task_id preservation

2. **Required Field Validation (5 tests)**
   - Valid delegates pass through unchanged
   - Missing required fields rejected
   - Error includes task_id
   - Falsy values (False, 0, "", []) pass if field exists

3. **Allowed Values Validation (7 tests)**
   - Valid values pass
   - Invalid values rejected
   - Error includes: field name, current value, allowed values
   - Multiple allowed values work
   - Missing field rejected even with allowed_values

4. **Stacked Decorators (5 tests)**
   - Multiple decorators all enforce constraints
   - Failure at first decorator
   - Failure at second decorator
   - Three decorators stacked
   - Failure in middle of stack

5. **Exception Metadata (3 tests)**
   - Exception has delegate metadata
   - Full structure preserved
   - Field name accessible

6. **Real-World Examples (3 tests)**
   - Security engineer routing (from spec)
   - Routing fails on invalid scope
   - Routing fails on missing approval

7. **Edge Cases (7 tests)**
   - Return values preserved
   - Multiple function arguments work
   - None values handled
   - Case-sensitive field names
   - Zero values pass
   - Empty lists pass
   - Single allowed value works

**Run tests:**
```bash
cd src/skills/_meta/orchestrator-enforcer
python3 -m pytest tests/test_orchestrator_enforcer.py -v
```

## Performance

Decorator execution is O(n) where n = number of fields validated (typically 1-3).
Each validation is a simple dict lookup or list membership check.

- Required field check: O(1) dict lookup
- Allowed values check: O(n) list membership (typically n=1-5)
- Stacked decorators: O(d) where d = number of decorators

No regex, no complex data structures. Minimal overhead suitable for production
routing code.

## Security Implications

This decorator is part of the security hardening phase (PHASE-1.5). It enables:

1. **Runtime enforcement** of DELEGATE schema requirements
2. **Rejection at the gate** of non-compliant work before function execution
3. **Audit trail** via exception metadata (task_id, field values stored)
4. **Clear error reporting** for operational debugging

**Not a replacement for:**
- Input validation (only checks DELEGATE dict structure)
- Type validation (only checks presence/membership, not types)
- Cryptographic verification (no signing/verification)

## Integration Points

### Orchestrator
Use to pre-validate DELEGATEs before routing to handlers.

```python
@enforce_delegate_requirement('type', allowed_values=['DELEGATE', 'ESCALATION'])
def route_task(delegate):
    # Route to appropriate handler
```

### Security Handlers
Use to ensure security-scoped work is properly approved.

```python
@enforce_delegate_requirement('security_scope', allowed_values=['auth', 'crypto'])
@enforce_delegate_requirement('approval_gate', required=True)
def handle_security_work(delegate):
    # Process security work
```

### Quality Engineering
Use to pre-validate QA DELEGATEs have required fields.

```python
@enforce_delegate_requirement('status', required=True)
@enforce_delegate_requirement('quality_score', required=True)
def validate_handback(delegate):
    # Validate HANDBACK completeness
```

## Future Extensions

Possible enhancements (outside current scope):

1. **Type validation**: `enforce_type('field', str)` → check field is string
2. **Range validation**: `enforce_range('priority', 1, 10)` → numeric ranges
3. **Regex validation**: `enforce_pattern('task_id', r'^TASK-\d+$')`
4. **Custom validators**: `enforce_custom('field', validator_func)`
5. **Conditional requirements**: `enforce_if('field1', required_if='field2')`

---

## Files

- `scripts/orchestrator_enforcer.py`: Core implementation
- `tests/test_orchestrator_enforcer.py`: 33-test suite
- `SKILL.md`: This file

## References

- PHASE-1.5-ORCHESTRATION-PLAN.md (lines 310-378) — Full spec
- PHASE-1.5-SECURITY-HARDENING.md (lines 230-260) — Security context
- src/skills/roles/principal-engineer.md — Role definition
