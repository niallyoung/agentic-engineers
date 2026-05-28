---
role: security-engineer
model: claude-opus-4.7
effort: high
priority: normal
version: 1.0
---

# Agent Definition Verification (FIX #3)

**Skill:** Tri-level verification of AGENTS.md against SPEC.md  
**Purpose:** Block model downgrade attacks (e.g., Security Engineer Opus-4.7 → Sonnet-4.6)  
**Protocol:** DELEGATE/HANDBACK with model_verification_sha field

---

## Overview

Implements FIX #3: Agent Definition Verification (Tri-Level)

**Problem:** No mechanism verifies AGENTS.md matches SPEC.md definitions. Security work silently underfunded if a role's model is downgraded.

**Attack Scenario:**
- SPEC.md says: Security Engineer = `claude-opus-4.7`
- Attacker modifies AGENTS.md: Security Engineer = `claude-sonnet-4.6`
- Cost drops from $0.15 to $0.09 per task
- Quality drops; security work is underfunded without awareness

**Solution:** Tri-level verification
1. **Git hook** — Verify `model_verification_sha` in all DELEGATE/HANDBACK files before push
2. **Schema field** — Add `model_verification_sha` to delegate-schema.yaml
3. **Runtime** — Orchestrator verifies model exists in AGENTS.md before invoking

---

## Component Files

```
src/skills/_meta/agent-definition-verifier/
├── SKILL.md                                 # This file
├── scripts/
│   └── agent_definition_verifier.py         # SHA generation & validation
└── tests/
    └── test_agent_definition_verifier.py    # 17 test cases (TDD)

src/orchestration/
├── agent-verification.py                    # SHA generation wrapper
└── delegate-schema.yaml                     # Updated with model_verification_sha field

.githooks/
└── pre-push                                 # Updated with agent verification checks

.agents_verification_sha                      # Current SHA256 of AGENTS.md
```

---

## Core Functions

### generate_agents_sha256(agents_file: str) → str

Generate SHA256 hash of AGENTS.md file.

```python
from agent_definition_verifier import generate_agents_sha256

sha = generate_agents_sha256("src/AGENTS.md")
# Returns: "a1b2c3d4e5f6..." (64-char hex string)
```

**Returns:** 64-character hex string (SHA256 hash)  
**Raises:** FileNotFoundError if file does not exist

---

### verify_sha_matches(delegate: Dict, current_agents_sha: str) → bool

Verify DELEGATE has matching `model_verification_sha`.

```python
from agent_definition_verifier import verify_sha_matches

delegate = {
    "task_id": "TASK-2026-05-30-fix-3",
    "role": "security-engineer",
    "model": "claude-opus-4.7",
    "model_verification_sha": "a1b2c3d4..."  # Must match current AGENTS.md
}

if verify_sha_matches(delegate, current_sha):
    print("✅ DELEGATE accepted")
else:
    print("❌ DELEGATE rejected — SHA mismatch")
```

---

### validate_agent_in_roster(role: str, model: str, agents_file: str) → bool

Validate role→model pair exists in current AGENTS.md.

```python
from agent_definition_verifier import validate_agent_in_roster

# Valid: Security Engineer with Opus-4.7
assert validate_agent_in_roster("security-engineer", "claude-opus-4.7", "src/AGENTS.md")

# Invalid: Security Engineer with Sonnet-4.6 (downgrade attempt)
assert not validate_agent_in_roster("security-engineer", "claude-sonnet-4.6", "src/AGENTS.md")
```

---

### load_agents_manifest(agents_file: str) → Dict[str, str]

Parse AGENTS.md roster and extract role→model mapping.

```python
from agent_definition_verifier import load_agents_manifest

roster = load_agents_manifest("src/AGENTS.md")
# Returns:
# {
#     "orchestrator": "claude-haiku-4.5",
#     "engineer": "claude-haiku-4.5",
#     "security_engineer": "claude-opus-4.7",
#     "principal_engineer": "claude-opus-4-6",
#     ...
# }
```

---

## Test Coverage

All tests (17 total) pass. Coverage includes:

### AC1: SHA Generated Correctly (64-char hex SHA256)
- ✅ test_ac1_sha_generated_correctly_format
- ✅ test_ac1_sha_is_sha256_hash
- ✅ test_ac1_sha_deterministic

### AC2: SHA Matches for Unmodified; Changes When Modified
- ✅ test_ac2_sha_matches_unmodified
- ✅ test_ac2_sha_changes_on_model_modification
- ✅ test_ac2_sha_changes_on_any_modification

### AC3: DELEGATE with Matching SHA Accepted; Mismatched Rejected
- ✅ test_ac3_matching_sha_accepted
- ✅ test_ac3_mismatched_sha_rejected
- ✅ test_ac3_missing_sha_rejected

### AC4: Model Downgrade Attacks Blocked
- ✅ test_ac4_model_downgrade_blocked_security_engineer
- ✅ test_ac4_model_not_in_roster_blocked
- ✅ test_ac4_valid_model_accepted

### AC5: Git Hook Validates model_verification_sha
- ✅ test_ac5_load_agents_manifest_success
- ✅ test_ac5_manifest_contains_all_required_roles

### Edge Cases
- ✅ test_empty_agents_file
- ✅ test_nonexistent_file_error
- ✅ test_whitespace_changes_affect_sha

**Run tests:**
```bash
cd src/skills/_meta/agent-definition-verifier
python3 -m pytest tests/test_agent_definition_verifier.py -v
```

**Expected output:** 17 passed in ~0.06s

---

## Integration Points

### 1. Git Hook (.githooks/pre-push)

Added checks:
```bash
# Verify all DELEGATE/HANDBACK files have model_verification_sha
python3 src/orchestration/agent-verification.py \
  validate-queue \
  src/AGENTS.md \
  ~/.copilot/queue/incoming \
  ~/.copilot/queue/done
```

### 2. DELEGATE Schema (src/orchestration/delegate-schema.yaml)

Added field:
```yaml
model_verification_sha:
  type: string
  required: true
  pattern: "^[0-9a-f]{64}$"
  description: "SHA256 of AGENTS.md at time of task creation (prevents model downgrades)"
```

### 3. Runtime Verification (Orchestrator)

Before invoking agent:
```python
# Verify model exists in current AGENTS.md
if not validate_agent_in_roster(role, model, "src/AGENTS.md"):
    raise SecurityException(f"Model {model} not valid for role {role}")
```

---

## Deployment Checklist

- [x] Tests pass (17/17)
- [x] Verifier functions implemented
- [x] SKILL.md created
- [x] SHA generation working
- [x] Schema updated
- [x] Git hook updated
- [x] .agents_verification_sha generated
- [ ] Orchestrator integration (delegated to Principal Engineer)

---

## FAQ

**Q: Why SHA256 specifically?**  
A: Standard cryptographic hash; 64-char hex representation; collision-resistant; widely supported.

**Q: What if AGENTS.md changes legitimately?**  
A: Update .agents_verification_sha and regenerate all in-flight DELEGATEs with new SHA.

**Q: Can an attacker forge the SHA?**  
A: No — SHA256 is cryptographically secure. Attacker would need to modify AGENTS.md *and* forge the hash, which is infeasible.

**Q: What if .agents_verification_sha is missing?**  
A: Pre-push hook rejects all DELEGATEs. Developer must regenerate via agent-verification.py.

---

## References

- PHASE-1.5-ORCHESTRATION-PLAN.md (lines 165-237)
- PHASE-1.5-SECURITY-HARDENING.md (lines 112-154)
- src/AGENTS.md (Agent Roster table)
- src/orchestration/delegate-schema.yaml
