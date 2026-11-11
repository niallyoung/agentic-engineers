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
  model: claude-haiku-5.5
  effort: high
  thinking: false
  dependencies:
    - PyYAML (for spec loading)
---

# protocol-validator

Validates DELEGATE and HANDBACK blocks against the canonical schema in
`docs/specs/protocol-core-v1.0.yaml`. Core fields are checked strictly;
extension fields loosely; unknown fields produce warnings, not errors
(forward-compatible). Implementation: `scripts/protocol_validator.py`.

## Usage

```python
from skills.protocol_validator.scripts import ProtocolValidator

validator = ProtocolValidator(spec_path="docs/specs/protocol-core-v1.0.yaml")
result = validator.validate_delegate(delegate)   # or validate_handback(handback)
if not result.valid:
    raise ValueError(result.errors)              # warnings are informational only
```

`ValidationResult` carries `valid`, `errors`, `warnings`, `duration_ms` and
`field_types`. The spec is loaded once and cached; a validation takes under 5ms.

## Rules at a glance

DELEGATE core fields: `handoff_type: DELEGATE`, `task_id` (kebab-case, 3-50
chars), `agent` (a roster role, hyphenated), `scope` (>=15 words),
`success_criteria` (>=1 item), `plan` (>=2 steps of >=3 words) and `context`
(string of >=20 words, or non-empty array). `skill` and `spec_version` are
optional extensions; when `skill` is present it must exist under `src/skills/`.

HANDBACK core fields: `handoff_type: HANDBACK`, `task_id`, `status` (success |
failure | partial | blocked | escalate), `output` and `metrics` (`quality`
0.0-1.0; `tokens`, `cost`, `duration_seconds` all >= 0).

The YAML spec is authoritative. If this page and the spec disagree, the spec wins.

## Tests

```bash
python3 -m pytest src/skills/protocol-validator/tests -q
```

## References

- `docs/specs/protocol-core-v1.0.yaml` - canonical protocol specification
- `docs/PROTOCOL.md` - protocol overview
