# Architecture: spec-management Skill

## System Design

### Core Components

The spec-management skill consists of 7 core modules working together in a layered architecture:

```
┌─────────────────────────────────────────────────────────┐
│         EXTERNAL INTERFACE (DELEGATE/HANDBACK)          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│           SpecManager (Main Orchestrator)               │
│  - Proposal submission                                  │
│  - Approval workflow                                    │
│  - Change application                                   │
│  - Rollback coordination                                │
└────┬─────┬───────────┬──────────┬────────┬──────────────┘
     │     │           │          │        │
     ▼     ▼           ▼          ▼        ▼
┌─────────────────────────────────────────────────────────┐
│ Validator │ Authorizer │ ImpactAnalyzer │ Audit │ Changelog │
└─────────────────────────────────────────────────────────┘
     │                                          │
     ▼                                          ▼
┌─────────────────────────────────────────────────────────┐
│         RollbackManager (Version Tracking)              │
└─────────────────────────────────────────────────────────┘
```

### Data Flow Layers

**Layer 1: Intake & Validation**
- `ChangeValidator` — Validates proposal format and completeness
- Rejects invalid proposals before processing

**Layer 2: Authorization**
- `Authorizer` — Enforces role-based access control
- Routes proposals through approval chains based on role hierarchy

**Layer 3: Analysis**
- `ImpactAnalyzer` — Computes change impact and risks
- Identifies affected agents, workflows, and compatibility issues

**Layer 4: Audit & Logging**
- `AuditLogger` — Records immutable audit trail with cryptographic linking
- Tracks approval chain and decisions

**Layer 5: Change Application**
- `ChangelogGenerator` — Auto-updates SPEC.md CHANGELOG
- Applies approved changes to SPEC.md

**Layer 6: Durability**
- `RollbackManager` — Tracks versions and enables rollback
- Maintains change history with SHA-256 hashes

### Security Model

**Access Control (AuthorizationLayer)**
- Only 3 roles can propose: principal-engineer, security-engineer, lead-engineer
- All other roles are rejected at intake
- Approval chains enforce hierarchical review requirements

**Immutability (Audit Trail)**
- All entries are frozen (dataclass with frozen=True)
- Cryptographic linking prevents tampering
- Every action is recorded with actor, timestamp, and details
- Approval chain is part of each action record

**Change Protection**
- No direct SPEC.md edits allowed outside this skill
- All changes must go through: proposal → validation → authorization → analysis → approval → application
- Breaking changes require migration paths and additional approvals

### Data Structures

#### ChangeProposal
```python
@dataclass
class ChangeProposal:
    change_id: str                  # SPEC-YYYY-NNN format
    proposer: str                   # User ID
    proposer_role: str              # principal-engineer, security-engineer, lead-engineer
    timestamp: str                  # ISO-8601 datetime
    affected_sections: List[str]    # Sections being modified
    proposed_changes: Dict[str, str]  # section -> new_text
    rationale: str                  # Why this change (≥50 chars)
    compatibility_notes: Optional[str]
    breaking_change: bool
    migration_path: Optional[str]
```

#### AuditEntry (Immutable)
```python
@dataclass(frozen=True)
class AuditEntry:
    entry_id: str                   # Unique entry ID
    change_id: str                  # Reference to change
    action: str                     # proposed|analyzed|approved|rejected|applied|reverted
    actor: str                      # Who performed action
    actor_role: str                 # Role of actor
    timestamp: str                  # ISO-8601
    details: Dict                   # Action-specific data
    previous_hash: Optional[str]    # SHA-256 of previous entry (linking)
    approval_chain: List[ApprovalEntry]  # Approval decisions
```

#### ImpactAnalysis
```python
@dataclass
class ImpactAnalysis:
    change_id: str
    affected_sections: List[str]    # Sections being modified
    is_breaking_change: bool        # Requires compatibility review
    affected_agents: List[str]      # Agent roles that need updates
    affected_workflows: List[str]   # Workflows that are impacted
    compatibility_risks: List[str]  # Detected risks
    migration_required: bool        # Is migration guide needed?
    downstream_impact: Dict[str, List[str]]  # Dependency map
```

#### SpecVersion
```python
@dataclass
class SpecVersion:
    version_id: str                 # SPEC-v5.10.N
    change_id: str                  # Which change created this
    timestamp: str                  # When applied
    previous_hash: str              # SHA-256 before change
    new_hash: str                   # SHA-256 after change
    applied_changes: Dict[str, str] # Sections changed
```

## Proposal Lifecycle

### State Diagram

```
┌─────────────────┐
│   PROPOSAL      │
│   SUBMISSION    │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  VALIDATION FAILS?  │─── YES ──> [REJECTED] ──> audit trail
└────────┬────────────┘
         │ NO
         ▼
┌─────────────────────┐
│ AUTHORIZATION FAILS?│─── YES ──> [REJECTED] ──> audit trail
└────────┬────────────┘
         │ NO
         ▼
┌─────────────────────────┐
│  IMPACT ANALYSIS        │
│  - Detect breaking      │
│  - Find dependencies    │
│  - Assess risks         │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  ROUTE TO APPROVERS     │
│  - Approval chain       │
│  - Security review?     │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  AWAITING APPROVAL      │ ◄─── Approver reviews impact
│  - Logged in audit      │      and makes decision
└────────┬────────────────┘
         │
      YES│ / NO
         ▼
    [APPROVED]        [REVISION REQUESTED]
         │                    │
         │                    └──> Return to proposer
         │                         (audit recorded)
         ▼
┌─────────────────────────────────┐
│  APPLY CHANGE                   │
│  1. Update SPEC.md              │
│  2. Generate changelog entry    │
│  3. Record version              │
│  4. Log "applied" action        │
└─────────────────────────────────┘
         │
         ▼
    [APPLIED]
     Final state
```

### Approval Requirements by Role

| Proposer Role | Normal Change | Breaking Change | Security-Critical |
|---------------|---------------|-----------------|-------------------|
| principal-engineer | Peer review (principal-engineer) | Peer + Security | Peer + Security + all |
| security-engineer | Principal review | Principal + Security peer | Principal mandatory |
| lead-engineer | Principal review | Principal + Security | Principal + Security |

## Implementation Notes

### Validation Strategy

Validation is multi-layer:

1. **Format Validation** (ChangeValidator)
   - change_id format (SPEC-YYYY-NNN)
   - Timestamp ISO-8601
   - Required fields present
   - Field length constraints

2. **Semantic Validation** (ImpactAnalyzer)
   - Breaking change detected?
   - Migration path provided?
   - Affected sections valid?
   - Compatibility risks?

3. **Authorization Validation** (Authorizer)
   - Role in approved list?
   - Approval chain exists?

### Cryptographic Linking

Audit entries are linked using SHA-256 hashes:

```
Entry 1: 
  content = "entry-1|SPEC-001|proposed|alice|2024-05-09T10:00:00Z"
  hash = SHA256(content) = abc123...
  
Entry 2:
  content = "entry-2|SPEC-001|analyzed|system|2024-05-09T10:05:00Z"
  previous_hash = abc123... ◄── Links to Entry 1
  hash = SHA256(entry_2_content) = def456...
  
Entry 3:
  content = "entry-3|SPEC-001|approval_decision|bob|2024-05-09T11:00:00Z"
  previous_hash = def456... ◄── Links to Entry 2
  hash = SHA256(entry_3_content) = ghi789...
```

This chain ensures that if any entry is tampered with, the hashes will no longer match.

### Changelog Integration

The CHANGELOG section of SPEC.md is auto-generated and immutable. Format:

```markdown
## CHANGELOG

### [SPEC-2024-001] — 2024-05-09 — alice (principal-engineer)
Clarify queue polling requirements for session-partitioned queues.
Approved by: bob (security-engineer)

### [SPEC-2024-002] — 2024-05-08 — charlie (security-engineer)
Implement distributed queue system for multi-region support.
See docs/MIGRATION-v5.11.md for migration path.
Approved by: alice (principal-engineer), dave (principal-engineer)
```

Entries are immutable once created—they cannot be edited or removed, only new entries added.

## Testing Strategy

The skill uses TDD (Test-Driven Development) with 53 comprehensive tests:

- **Group 1: Proposal Validation** (7 tests)
  - Format validation, field constraints, change_id format

- **Group 2: Impact Analysis** (7 tests)
  - Breaking change detection, affected sections, agent impact

- **Group 3: Authorization** (9 tests)
  - Role checking, approval chains, role hierarchy

- **Group 4: Audit Trail** (7 tests)
  - Logging, immutability, cryptographic linking, chain integrity

- **Group 5: Changelog** (5 tests)
  - Entry generation, formatting, chronological order

- **Group 6: Enforcement** (5 tests)
  - Rejection rules, unauthorized proposals, format enforcement

- **Group 7: Rollback** (5 tests)
  - Version tracking, rollback capability, history management

- **Integration Tests** (3 tests)
  - End-to-end workflows, breaking change handling

**Coverage Target: 90%+**

Tests are runnable with:
```bash
pytest tests/test_spec_management.py -v
```

## Deployment Considerations

### Git Hook Integration

To prevent direct SPEC.md edits outside this skill, a git pre-commit hook can be installed:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Prevent direct edits to SPEC.md outside of spec-management skill
if git diff --cached --name-only | grep -q "docs/SPEC.md"; then
    echo "ERROR: Cannot edit SPEC.md directly."
    echo "Use: co delegate principal-engineer --skill spec-management"
    exit 1
fi
```

### Audit Trail Verification

Periodically verify audit chain integrity:

```python
from src.skills.spec_management.scripts.audit_logger import AuditLogger

logger = AuditLogger()
is_intact = logger.verify_chain_integrity()
if not is_intact:
    raise Exception("AUDIT TRAIL COMPROMISED: Tampering detected!")
```

### Monitoring & Alerting

Key events to monitor:

1. **Authorization Failures** — Multiple failed proposals from unauthorized roles
2. **Rollbacks** — Unexpected rollback requests (may indicate incident)
3. **Breaking Changes** — Breaking changes are high-risk and should be reviewed carefully
4. **Approval Delays** — Proposals stuck in approval (may need escalation)

## Future Enhancements

1. **Scheduled Reviews** — Automatic review of old proposals
2. **Change Bundles** — Group related proposals for review
3. **Approval SLA** — Track approval times and alert on delays
4. **Notification System** — Email/Slack notifications on approvals
5. **Diff Visualization** — Show before/after SPEC.md changes
6. **Risk Scoring** — Compute risk scores for proposals
7. **Comparison View** — Compare versions of SPEC.md
8. **Compliance Reports** — Generate governance compliance reports
