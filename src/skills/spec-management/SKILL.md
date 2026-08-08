---
name: spec-management
description: Exclusive SPEC.md change protection with structured proposal interface, impact analysis, multi-level authorization, immutable audit trail, and rollback capability. Only Principal/Security/Lead Engineers can invoke. Enforces all SPEC.md modifications through proposal→analysis→approval→changelog workflow with tamper-evident audit trail.
license: Proprietary
compatibility: Agentic-Engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: management
  role: principal-engineer
  authority: principal-engineer, security-engineer, lead-engineer
  model: claude-opus-4.8
  effort: medium
  thinking: true
---

# spec-management Skill

## Overview

**CRITICAL SECURITY SKILL**: This skill is the **exclusive gateway** for all SPEC.md modifications. Our goal is to ensure that all SPEC.md changes follow a clear proposal → analysis → approval → audit → changelog workflow. Only Principal Engineer, Security Engineer, and Lead Engineer roles can invoke it.

### What It Does

1. **Change Proposal Interface** — Parses and validates structured change proposals with required fields (change_id, sections, rationale, impact assessment)
2. **Impact Analysis** — Computes affected sections, identifies breaking changes, maps downstream dependencies, flags compatibility risks
3. **Multi-Level Authorization** — Routes proposals through role-based approval chains for Principal/Security/Lead review
4. **Immutable Audit Trail** — Records every action (proposed, analyzed, approved, rejected, applied, reverted) with cryptographic linking to prevent tampering
5. **Changelog Generation** — Auto-updates SPEC.md CHANGELOG section on approval; includes change_id, author, timestamp
6. **Governance** — Enforces structured proposal format and requires approval before changes take effect
7. **Rollback Capability** — Tracks SPEC.md versions with SHA-256 hashes, enables reverting changes with full audit trail

## Architecture

### Core Components

```
spec-management/
├── SKILL.md                              # This file
├── scripts/
│   ├── spec_manager.py                   # Main orchestrator
│   ├── change_validator.py               # Proposal validation
│   ├── impact_analyzer.py                # Impact analysis engine
│   ├── authorizer.py                     # Role-based authorization
│   ├── audit_logger.py                   # Immutable audit trail
│   ├── changelog_generator.py            # Auto-update CHANGELOG
│   └── rollback_manager.py               # Version tracking & rollback
├── references/
│   ├── ARCHITECTURE.md                   # Detailed system design
│   ├── API.md                            # Public API specification
│   ├── AUTHORIZATION.md                  # Role hierarchy & approval rules
│   ├── AUDIT-TRAIL.md                    # Audit format & immutability
│   └── EXAMPLES.md                       # Usage examples
└── assets/
    ├── proposal-template.yaml            # Proposal format template
    └── approval-rules.yaml               # Authorization rules
```

### Data Flow

```
1. PROPOSAL SUBMISSION
   User (Principal/Security/Lead) → ChangeProposal → SpecManager

2. VALIDATION & AUTHORIZATION
   SpecManager → ChangeValidator.validate() → Authorizer.can_propose()
   If invalid or unauthorized → REJECT (audit logged)

3. IMPACT ANALYSIS
   ImpactAnalyzer.analyze() → identify sections, agents, workflows, risks
   Audit: log "analyzed" action

4. APPROVAL ROUTING
   Authorizer.get_approval_chain() → route to appropriate approvers
   Audit: log "approval_requested" action

5. APPROVAL PROCESS
   Approver reviews impact → submits ApprovalEntry (approved/rejected/revision)
   Audit: log "approval_decision" action with full approval chain

6. APPLICATION (ON APPROVAL)
   SpecManager.apply_change() →
     a) Update SPEC.md with proposed changes
     b) Compute new SPEC hash
     c) ChangelogGenerator.add_entry() → Update CHANGELOG section
     d) AuditLogger.log_action() → Record "applied" with hashes
     e) Write version metadata to artifacts/

7. ROLLBACK (IF NEEDED)
   Authorizer.can_approve() → RollbackManager.rollback(steps=N) →
     a) Retrieve previous SPEC version from artifacts/
     b) Restore SPEC.md
     c) AuditLogger.log_action() → Record "reverted"
```

## Usage Examples

### Proposing a Change

```yaml
# docs/spec-proposals/SPEC-2024-001.yaml
change_id: SPEC-2024-001
proposer: alice
proposer_role: principal-engineer
timestamp: 2024-05-09T10:30:00Z
affected_sections:
  - ORCHESTRATOR-FIRST EXECUTION MODEL
  - Implementation Requirements
proposed_changes:
  ORCHESTRATOR-FIRST EXECUTION MODEL: |
    New text for this section...
  Implementation Requirements: |
    Updated requirements...
rationale: |
  Clarify queue polling requirements for session-partitioned queues.
  Agents have asked for explicit documentation on how to detect session IDs
  and poll only their assigned queue partition. This change includes examples.
compatibility_notes: Backward compatible with v5.9 and earlier.
breaking_change: false
```

### Breaking Change Proposal

```yaml
change_id: SPEC-2024-002
proposer: bob
proposer_role: security-engineer
timestamp: 2024-05-09T11:00:00Z
affected_sections:
  - ORCHESTRATOR-FIRST EXECUTION MODEL
proposed_changes:
  ORCHESTRATOR-FIRST EXECUTION MODEL: |
    Queue format changes to use distributed ledger...
rationale: |
  Implement distributed queue system for multi-region support.
  Requires agent update to handle new queue format.
compatibility_notes: |
  Breaking change. Agents must update to new queue format.
  See MIGRATION-v5.11.md for upgrade path.
breaking_change: true
migration_path: docs/MIGRATION-v5.11.md
```

## Authorization Model

### Authorized Roles

Only these roles can invoke spec-management:
- **Principal Engineer** — Can propose any changes; approvals from peers or Security/Lead
- **Security Engineer** — Can propose security-related changes; Principal or other Security Engineers approve
- **Lead Engineer** — Can propose operational changes; Principal or Security Engineers approve

### Rejected Roles

These roles **cannot** invoke spec-management:
- Engineer
- Senior Engineer
- Orchestrator
- Quality Engineer
- Model Engineer
- Any other role

### Approval Chain

Changes are routed to approvers based on proposer role and change severity:

| Proposer | Normal Change | Breaking Change | Security-Critical |
|----------|---------------|-----------------|------------------|
| Principal Engineer | Peer review | Peer + Lead | Peer + Security |
| Security Engineer | Security principal | Principal + Security peer | Principal |
| Lead Engineer | Principal or Security | Principal | Principal + Security |

## Validation Rules

### Change Proposal Format

All proposals must include:

1. **change_id** (required)
   - Format: `SPEC-YYYY-NNN` (e.g., `SPEC-2024-001`)
   - Must be unique; system rejects duplicates

2. **proposer** (required)
   - Username or identifier of proposal author
   - Must match authenticated user

3. **proposer_role** (required)
   - One of: `principal-engineer`, `security-engineer`, `lead-engineer`
   - Unauthorized roles are rejected at intake

4. **timestamp** (required)
   - ISO-8601 format (e.g., `2024-05-09T10:30:00Z`)
   - Must be valid; invalid timestamps rejected

5. **affected_sections** (required)
   - List of section names from SPEC.md
   - Must be non-empty; empty list rejected
   - Sections are matched against actual SPEC.md structure

6. **proposed_changes** (required)
   - Dict mapping section name → new text
   - At least one change must be included
   - Changes must not be empty strings

7. **rationale** (required)
   - Explanation of why change is needed
   - Must be ≥50 characters
   - Short rationales are rejected

8. **compatibility_notes** (optional)
   - Impact on existing systems/agents
   - Required if `breaking_change: true`

9. **breaking_change** (optional, default: false)
   - Boolean flag: is this a breaking change?
   - If true, `migration_path` is required

10. **migration_path** (conditional)
    - Path to migration guide (e.g., `docs/MIGRATION-v5.11.md`)
    - Required if `breaking_change: true`
    - File must exist and be readable

### Rejection Criteria

Proposals are rejected if they:
- Contain invalid change_id format
- Contain invalid timestamp
- Have empty affected_sections
- Have missing rationale or rationale < 50 chars
- Are from unauthorized roles
- Include breaking_change without migration_path
- Have security issues flagged by impact analysis

## Audit Trail

Every action is recorded in an immutable audit trail stored at `artifacts/audit/spec-management/`:

### Audit Entry Structure

```yaml
entry_id: audit-{timestamp}-{random}
change_id: SPEC-2024-001
action: proposed|analyzed|approval_requested|approval_decision|applied|reverted
actor: alice
actor_role: principal-engineer
timestamp: 2024-05-09T10:30:00Z
previous_hash: a1b2c3d4...  # SHA-256 of previous audit entry (cryptographic linking)
details:
  # Action-specific details
approval_chain:
  - change_id: SPEC-2024-001
    approver: bob
    approver_role: security-engineer
    approval_timestamp: 2024-05-09T11:00:00Z
    status: approved
    comments: Looks good, security impact is acceptable
  - change_id: SPEC-2024-001
    approver: charlie
    approver_role: principal-engineer
    approval_timestamp: 2024-05-09T12:00:00Z
    status: approved
    comments: Approved. Can merge.
```

### Audit Properties

- **Immutable** — Entries cannot be modified after creation; attempting to edit raises ImmutableError
- **Cryptographically Linked** — Each entry includes SHA-256 hash of previous entry, preventing tampering
- **Complete** — Every action is logged; no changes occur outside audit trail
- **Queryable** — Can search audit trail by change_id, actor, timestamp, action type

### Querying Audit Trail

```python
# Get all entries for a specific change
entries = audit_logger.get_entries_for_change("SPEC-2024-001")

# Get entries by action
rejections = audit_logger.get_entries_by_action("rejected")

# Get entries in date range
recent = audit_logger.get_entries_since("2024-05-01")

# Verify audit chain integrity (check cryptographic linking)
is_valid = audit_logger.verify_chain_integrity()
```

## Changelog Management

### Changelog Format in SPEC.md

SPEC.md includes a CHANGELOG section (near the end) in this format:

```markdown
## CHANGELOG

### [SPEC-2024-002] — 2024-05-09 — bob (security-engineer)
Implement distributed queue system for multi-region support.
See docs/MIGRATION-v5.11.md for upgrade details.
Approved by: alice (principal-engineer), charlie (principal-engineer)

### [SPEC-2024-001] — 2024-05-09 — alice (principal-engineer)
Clarify queue polling requirements for session-partitioned queues.
Backward compatible.
Approved by: bob (security-engineer)

... (earlier entries)
```

### Automatic Changelog Generation

When a change is approved:

1. **Entry Created** — System generates changelog entry with:
   - change_id (formatted as link to proposal)
   - timestamp of approval
   - proposer name and role
   - rationale (from proposal)
   - approval chain (list of approvers)

2. **Added to SPEC.md** — Entry is inserted at the top of CHANGELOG section (most recent first)

3. **Immutable** — Changelog entries match audit trail; cannot be removed or modified (only new entries added)

## Rollback & Version Tracking

### Version Tracking

When a change is applied, a version record is created:

```yaml
# artifacts/spec-versions/SPEC-v{number}.yaml
version_id: SPEC-v5.10.1
change_id: SPEC-2024-001
timestamp: 2024-05-09T10:30:00Z
applied_by: system
applied_timestamp: 2024-05-09T13:00:00Z
previous_hash: "a1b2c3d4e5f6......"  # SHA-256 of SPEC.md before change
new_hash: "z9y8x7w6v5u4......"       # SHA-256 of SPEC.md after change
changes:
  ORCHESTRATOR-FIRST EXECUTION MODEL: "New text..."
  Implementation Requirements: "Updated text..."
```

### Rollback Capability

Only Principal/Security/Lead Engineers can initiate rollback:

```python
# Rollback one change
result = spec_manager.rollback(steps=1, initiated_by="alice")

# Rollback to specific version
result = spec_manager.rollback_to_version("SPEC-v5.9.2", initiated_by="alice")

# Rollback result includes:
# - success: bool
# - previous_version: str
# - new_version: str
# - audit_entry: AuditEntry (recorded as "reverted" action)
```

### Rollback Audit Trail

Every rollback is recorded:
```yaml
action: reverted
change_id: SPEC-2024-001  # The change being reverted
details:
  reverted_from_version: SPEC-v5.10.1
  reverted_to_version: SPEC-v5.10.0
  reason: Security issue found in change, needs revision
```

## Implementation Status

This skill is in **DESIGN** phase and follows these implementation stages:

### Phase 1: Architecture & TDD (Current)
- ✅ Architecture design (this document)
- ✅ TDD test suite (tests/test_spec_management.py) — 40+ tests defined
- 🔄 Core implementation (scripts/)

### Phase 2: Core Modules
- Change Validator
- Impact Analyzer
- Authorizer
- Audit Logger
- Changelog Generator
- Rollback Manager

### Phase 3: Integration
- End-to-end workflows
- Error handling & edge cases
- Performance testing
- Security audit

### Phase 4: Deployment
- Git hook for SPEC.md protection
- Monitoring & alerting
- Documentation & training

## Calling This Skill

Only authorized users can invoke spec-management:

```bash
# Invalid: Regular engineer tries to propose change
co delegate principal-engineer \
  --skill spec-management \
  --proposal docs/spec-proposals/SPEC-2024-001.yaml
# ERROR: Unauthorized role (engineer)

# Valid: Principal Engineer proposes change
co delegate principal-engineer \
  --skill spec-management \
  --proposal docs/spec-proposals/SPEC-2024-001.yaml
# SUCCESS: Proposal SPEC-2024-001 submitted for analysis
```

## Related Documentation

- `references/ARCHITECTURE.md` — Detailed system design and data structures
- `references/API.md` — Complete API specification and method signatures
- `references/AUTHORIZATION.md` — Role hierarchy, approval rules, escalation paths
- `references/AUDIT-TRAIL.md` — Audit format, cryptographic linking, verification
- `references/EXAMPLES.md` — Working examples of proposals, approvals, rollbacks
- `docs/SPEC.md` — The SPEC.md file being protected

## Success Criteria

- ✅ Skill fully functional and tested (90%+ coverage)
- ✅ Authorization properly enforced (only Principal/Security/Lead can invoke)
- ✅ Change proposals validated structurally and semantically
- ✅ Impact analysis generated for each proposal
- ✅ Audit trail complete with approval chain and cryptographic linking
- ✅ Changelog auto-updated on approval with change history
- ✅ Rollback capability with version tracking
- ✅ All tests passing, zero regressions
- ✅ SPAN file generated with skill metrics

## Constraints & Non-Goals

### Constraints
- **TDD discipline**: All implementation must be driven by tests
- **Model**: Claude Fable 5 (highest capability for security scrutiny)
- **Authority**: Principal/Security/Lead exclusive
- **No direct edits**: SPEC.md can only be modified through this skill
- **Audit immutability**: Audit trail is permanent and tamper-evident
- **Impact analysis required**: Changes must go through full analysis before approval

### Non-Goals
- This skill does not modify files other than SPEC.md
- This skill does not bypass approval requirements
- This skill does not support untracked rollbacks
- This skill does not allow downgrading authorization requirements

## Maintenance & Evolution

This skill will be maintained by:
- **Principal Engineer** — Architecture oversight, breaking change approval
- **Security Engineer** — Authorization & audit trail validation
- **Lead Engineer** — Operational impact assessment

Updates to this skill require approval through the same proposal workflow, ensuring consistency and trustworthiness.

## Self-Improvement

We aim for **spec-management** to feel like a knowledgeable colleague rather than a rulebook. If any section felt prescriptive rather than guiding, a `tone_note` in your feedback helps us improve it.

This skill participates in the framework's continuous improvement cycle
(see [`skill-improvement-feedback`](../skill-improvement-feedback/SKILL.md)).

When you use **spec-management** during a task, include a `skill_feedback` entry
in your HANDBACK to help improve it over time:

```yaml
skill_feedback:
  - skill_name: spec-management
    effectiveness_score: 0.85        # required: 0.0–1.0
    clarity_score: 0.90              # optional
    coverage_gaps:
      - "Specific scenario the skill did not address"
    improvement_suggestions:
      - "Concrete change that would have helped"
    usage_context: "One sentence on how you used this skill"
```

Positive feedback is as valuable as critical feedback. Three or more
feedback items for this skill automatically trigger an improvement task.
