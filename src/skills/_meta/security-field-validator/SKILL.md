---
# Skill metadata (follows agentskills.io spec)
name: security-field-validator
title: Security-Critical DELEGATE Field Validator
version: 1.0.0
author: Principal Engineer
created: 2026-05-30
updated: 2026-05-30

role: principal-engineer
effort: high
priority: normal

purpose: |
  Validate security-critical DELEGATE fields and enforce routing rules.
  Prevents security work from being mis-routed to general engineers.

scope: |
  Validates three new fields added to the DELEGATE schema:
  - security_scope: enum [none|auth|crypto|pii|secrets|injection|supply_chain]
  - approval_gate: enum [none|lead_engineer|principal_engineer|security_engineer|cto]
  - audit_required: boolean
  
  Enforces validation rules:
  1. If security_scope != none, approval_gate MUST be set (not "none")
  2. If approval_gate is set, audit_required MUST be true
  3. Security scopes route to Security Engineer minimum
  
  Provides routing logic to determine required role based on security_scope.

dependencies: []

---

## Overview

Security-critical work often gets routed to the wrong agent because DELEGATE blocks lack
security-specific metadata. This validator enforces a three-field scheme to ensure:

- **Visibility**: All security work is explicitly flagged with a security_scope
- **Routing**: Security-scoped tasks are routed to Security Engineer (minimum)
- **Approvals**: Security work requires explicit approval gates
- **Auditing**: Approved work is auditable via the audit_required flag

## Architecture

```
SecurityFieldValidator
├── validate()              # Main entry point
├── _determine_required_role()
└── apply_defaults()        # Fill in missing fields with defaults
```

### Validation Flow

1. **Enum validation** — security_scope and approval_gate must be valid enum values
2. **Dependent field validation** — enforce constraints between fields
3. **Role determination** — compute required_role based on security_scope

### Validation Rules

| Rule | Condition | Consequence |
|------|-----------|-------------|
| R1 | `security_scope != "none"` ⟹ `approval_gate != "none"` | REJECT if violated |
| R2 | `approval_gate != "none"` ⟹ `audit_required == true` | REJECT if violated |
| R3 | `security_scope ∈ {auth, crypto, pii, secrets, injection, supply_chain}` | Route to Security Engineer |

## Usage

### Basic Validation

```python
from security_field_validator import SecurityFieldValidator

validator = SecurityFieldValidator()

# Validate a DELEGATE block
delegate = {
    "security_scope": "auth",
    "approval_gate": "principal_engineer",
    "audit_required": True,
}

result = validator.validate(delegate)

if result["valid"]:
    print(f"✅ VALID — route to {result['required_role']}")
else:
    for error in result["errors"]:
        print(f"❌ {error}")
```

### Apply Defaults

```python
delegate = {}
validator.apply_defaults(delegate)
# Now: security_scope="none", approval_gate="none", audit_required=false
```

### Convenience Function

```python
from security_field_validator import validate_security_fields

result = validate_security_fields(delegate)
```

## Validation Result Format

```python
{
    "valid": bool,                    # True if all checks pass
    "errors": list,                   # Error messages (empty if valid)
    "warnings": list,                 # Warning messages (can coexist with valid=true)
    "security_scope": str,            # Resolved value (with default if not set)
    "approval_gate": str,             # Resolved value (with default if not set)
    "audit_required": bool,           # Resolved value (with default if not set)
    "required_role": str or None,     # "security_engineer" if security-scoped, else None
}
```

## Integration Points

### DELEGATE Schema (delegate-schema.yaml)

Add these fields to `optional_fields`:

```yaml
security_fields:
  security_scope:
    type: string
    enum:
      - none
      - auth
      - crypto
      - pii
      - secrets
      - injection
      - supply_chain
    default: none
    description: "Security classification for task (triggers routing to Security Engineer)"
    example: "auth"
  
  approval_gate:
    type: string
    enum:
      - none
      - lead_engineer
      - principal_engineer
      - security_engineer
      - cto
    default: none
    description: "Required approval authority before task execution"
    example: "principal_engineer"
  
  audit_required:
    type: boolean
    default: false
    description: "Whether task execution must be audited (required if approval_gate set)"
    example: true
```

### Orchestrator Routing

After validation, the orchestrator should:

```python
result = validator.validate(delegate)

if not result["valid"]:
    # Reject DELEGATE with validation errors
    return reject_delegate(delegate, result["errors"])

if result["required_role"] == "security_engineer":
    # Force role to security_engineer if not already set
    delegate["role"] = "security_engineer"

if result["approval_gate"] != "none":
    # Apply approval gate checks before execution
    apply_approval_gate(delegate, result["approval_gate"])
```

## Testing

All test cases verify acceptance criteria from FIX #4:

- **AC1**: Non-security tasks default correctly
- **AC2**: Security scopes route to Security Engineer
- **AC3**: Approval gates are enforced
- **AC4**: Invalid combinations are rejected
- **AC5**: Validation rules work
- **AC6**: 16 test cases all passing

Run tests:

```bash
cd src/skills/_meta/security-field-validator
python3 -m pytest tests/test_security_field_validator.py -v
```

Expected: **16 passed**

## Constraints

- Python 3.7+ compatible
- No external dependencies (pure stdlib)
- Validation response time: <5ms (suitable for orchestrator gates)
- Extensible: New security_scope values can be added without code changes

## Future Extensions

1. **Rate limiting per approval_gate** — different approval authorities have different throughput
2. **Audit trail integration** — track which tasks required which approval gates
3. **Escalation detection** — automatic escalation to CTO if certain scope + gate combos detected
4. **Metrics collection** — track security task volume by scope and approval gate

## Related Skills

- `src/skills/roles/security-engineer.md` — Security Engineer role definition
- `src/skills/roles/principal-engineer.md` — Principal Engineer role definition
- `src/orchestration/delegate-schema.yaml` — Master DELEGATE schema
