# API Reference: spec-management Skill

## SpecManager API

The main orchestrator for SPEC.md change management.

### Class: SpecManager

```python
class SpecManager:
    def __init__(self, spec_path: str = "docs/SPEC.md")
```

#### Methods

##### parse_proposal(proposal_dict: Dict) → ChangeProposal

Parse a proposal from dict/JSON input.

**Parameters:**
- `proposal_dict` (Dict): Dictionary with proposal fields

**Returns:** ChangeProposal object

**Example:**
```python
proposal_dict = {
    "change_id": "SPEC-2024-001",
    "proposer": "alice",
    "proposer_role": "principal-engineer",
    "timestamp": "2024-05-09T10:30:00Z",
    "affected_sections": ["Executive Summary"],
    "proposed_changes": {"Executive Summary": "Updated text"},
    "rationale": "Clarify the executive summary for better understanding and clarity"
}
proposal = spec_manager.parse_proposal(proposal_dict)
```

##### validate_proposal(proposal: ChangeProposal) → ValidationResult

Validate proposal format and completeness.

**Parameters:**
- `proposal` (ChangeProposal): Proposal to validate

**Returns:** ValidationResult with `is_valid` (bool) and `errors` (List[str])

**Validation checks:**
- change_id format (SPEC-YYYY-NNN)
- All required fields present
- Timestamp is valid ISO-8601
- Affected sections non-empty
- Rationale ≥ 50 characters
- Breaking change has migration path

**Example:**
```python
result = spec_manager.validate_proposal(proposal)
if not result.is_valid:
    print(f"Validation failed: {result.errors}")
```

##### submit_proposal(proposal: ChangeProposal) → SubmissionResult

Submit a change proposal for processing.

Performs:
1. Validation
2. Authorization check
3. Impact analysis
4. Approval routing
5. Audit trail logging

**Parameters:**
- `proposal` (ChangeProposal): Proposal to submit

**Returns:** SubmissionResult with:
- `status` (str): "pending_approval", "approved", "rejected"
- `change_id` (str): ID of change
- `reason` (Optional[str]): Error/reason if rejected
- `approval_chain` (List[str]): Required approvers

**Example:**
```python
result = spec_manager.submit_proposal(proposal)
if result.status == "rejected":
    print(f"Rejected: {result.reason}")
elif result.status == "pending_approval":
    print(f"Awaiting approval from: {', '.join(result.approval_chain)}")
```

##### approve_change(change_id: str, approver: str, approver_role: str, comments: Optional[str]) → SubmissionResult

Approve a pending change.

**Parameters:**
- `change_id` (str): ID of change to approve
- `approver` (str): Name/ID of approver
- `approver_role` (str): Role of approver
- `comments` (Optional[str]): Approval comments

**Returns:** SubmissionResult with approval status

**Example:**
```python
result = spec_manager.approve_change(
    change_id="SPEC-2024-001",
    approver="bob",
    approver_role="security-engineer",
    comments="Looks good, security impact is acceptable"
)
```

##### reject_change(change_id: str, rejector: str, rejector_role: str, comments: str) → SubmissionResult

Reject a pending change.

**Parameters:**
- `change_id` (str): ID of change to reject
- `rejector` (str): Name/ID of rejector
- `rejector_role` (str): Role of rejector
- `comments` (str): Required reason for rejection

**Returns:** SubmissionResult with rejection status

**Example:**
```python
result = spec_manager.reject_change(
    change_id="SPEC-2024-002",
    rejector="alice",
    rejector_role="principal-engineer",
    comments="Breaks backward compatibility without clear migration path"
)
```

##### compute_spec_hash() → str

Compute SHA-256 hash of current SPEC.md.

**Returns:** 64-character hex string (SHA-256 digest)

**Example:**
```python
current_hash = spec_manager.compute_spec_hash()
print(f"Current SPEC.md hash: {current_hash}")
```

##### get_change_history() → List[SpecVersion]

Get complete change history.

**Returns:** List of SpecVersion objects, ordered chronologically

**Example:**
```python
history = spec_manager.get_change_history()
for version in history:
    print(f"{version.version_id}: {version.change_id} ({version.timestamp})")
```

##### rollback(steps: int = 1, initiated_by: str = "system") → Dict

Rollback one or more changes.

**Parameters:**
- `steps` (int): Number of changes to revert
- `initiated_by` (str): User initiating rollback

**Returns:** Dict with:
- `success` (bool): Whether rollback succeeded
- `previous_version` (str): Version reverted to
- `reverted_versions` (List[str]): Versions removed
- `details` (str): Human-readable summary

**Example:**
```python
result = spec_manager.rollback(steps=1, initiated_by="alice")
if result["success"]:
    print(f"Rolled back to {result['previous_version']}")
```

##### rollback_to_version(version_id: str, initiated_by: str = "system") → Dict

Rollback to a specific version.

**Parameters:**
- `version_id` (str): Version to rollback to (e.g., "SPEC-v5.10.1")
- `initiated_by` (str): User initiating rollback

**Returns:** Dict with rollback status and details

**Example:**
```python
result = spec_manager.rollback_to_version("SPEC-v5.9.2", initiated_by="alice")
```

---

## Authorizer API

Controls role-based access to SPEC.md changes.

### Class: Authorizer

```python
class Authorizer:
    PROPOSER_ROLES = {"principal-engineer", "security-engineer", "lead-engineer"}
    APPROVER_ROLES = {"principal-engineer", "security-engineer", "lead-engineer"}
```

#### Methods

##### can_propose(role: str) → bool

Check if role is authorized to propose changes.

**Parameters:**
- `role` (str): Role to check

**Returns:** True if role can propose, False otherwise

**Example:**
```python
authorizer = Authorizer()
if authorizer.can_propose("principal-engineer"):
    print("Authorized to propose")
else:
    print("NOT authorized to propose")
```

##### can_approve(role: str) → bool

Check if role is authorized to approve changes.

**Parameters:**
- `role` (str): Role to check

**Returns:** True if role can approve, False otherwise

##### get_approval_chain(proposer_role: str) → List[str]

Get approval chain for a proposer role.

**Parameters:**
- `proposer_role` (str): Role of proposal author

**Returns:** List of approver roles in order

**Example:**
```python
chain = authorizer.get_approval_chain("security-engineer")
print(f"Required approvers: {', '.join(chain)}")
# Output: Required approvers: principal-engineer, security-engineer
```

##### requires_security_review(proposal: ChangeProposal) → bool

Check if proposal requires security review.

**Parameters:**
- `proposal` (ChangeProposal): Proposal to check

**Returns:** True if security review required

**Logic:**
- Breaking changes always require review
- Sections with "security", "authorization", "audit" keywords require review

##### is_final_approval(approver_role: str) → bool

Check if approval from this role is final.

**Parameters:**
- `approver_role` (str): Role of approver

**Returns:** True if approval is final (only principal-engineer)

---

## ImpactAnalyzer API

Analyzes impact of proposed SPEC.md changes.

### Class: ImpactAnalyzer

```python
class ImpactAnalyzer:
    def analyze(self, proposal: ChangeProposal) -> ImpactAnalysis
```

#### Methods

##### analyze(proposal: ChangeProposal) → ImpactAnalysis

Analyze impact of proposed change.

**Parameters:**
- `proposal` (ChangeProposal): Proposal to analyze

**Returns:** ImpactAnalysis with impact details

**Analysis includes:**
- Affected sections and dependencies
- Breaking change detection
- Affected agent roles
- Affected workflows
- Compatibility risks
- Migration requirements
- Downstream dependencies

**Example:**
```python
analyzer = ImpactAnalyzer()
impact = analyzer.analyze(proposal)

if impact.is_breaking_change:
    print(f"⚠️  BREAKING CHANGE")
    print(f"Affected agents: {', '.join(impact.affected_agents)}")
    print(f"Risks: {', '.join(impact.compatibility_risks)}")
else:
    print(f"✓ Non-breaking change")
```

---

## AuditLogger API

Records immutable audit trail for SPEC.md changes.

### Class: AuditLogger

```python
class AuditLogger:
    def log_action(self, action: str, change_id: str, actor: str, actor_role: str,
                   details: Optional[Dict] = None,
                   approval_chain: Optional[List[ApprovalEntry]] = None) -> AuditEntry
```

#### Methods

##### log_action(...) → AuditEntry

Log an action to the audit trail.

**Parameters:**
- `action` (str): Action type (proposed, analyzed, approved, rejected, applied, reverted)
- `change_id` (str): ID of change being acted upon
- `actor` (str): Name of actor
- `actor_role` (str): Role of actor
- `details` (Optional[Dict]): Action-specific details
- `approval_chain` (Optional[List[ApprovalEntry]]): Approval decisions

**Returns:** Immutable AuditEntry

##### log_approval(approval: ApprovalEntry) → AuditEntry

Log an approval decision.

**Parameters:**
- `approval` (ApprovalEntry): Approval to log

**Returns:** AuditEntry recording the approval

##### get_entries_for_change(change_id: str) → List[AuditEntry]

Get all audit entries for a specific change.

**Parameters:**
- `change_id` (str): Change ID to query

**Returns:** List of AuditEntry objects

##### get_entries_by_action(action: str) → List[AuditEntry]

Get all entries for a specific action type.

**Parameters:**
- `action` (str): Action type to query

**Returns:** List of AuditEntry objects

##### get_entries_since(timestamp: str) → List[AuditEntry]

Get all entries since a timestamp.

**Parameters:**
- `timestamp` (str): ISO-8601 timestamp

**Returns:** List of AuditEntry objects

##### verify_chain_integrity() → bool

Verify cryptographic integrity of audit chain.

**Returns:** True if chain is intact, False if tampering detected

**Example:**
```python
logger = AuditLogger()
if not logger.verify_chain_integrity():
    raise Exception("AUDIT TRAIL COMPROMISED!")
```

---

## ChangeValidator API

Validates change proposals for format and completeness.

### Class: ChangeValidator

```python
class ChangeValidator:
    CHANGE_ID_PATTERN = re.compile(r'^SPEC-\d{4}-\d{3}$')
    TIMESTAMP_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
    MIN_RATIONALE_LENGTH = 50
```

#### Methods

##### validate(proposal: ChangeProposal) → ValidationResult

Validate a change proposal.

**Parameters:**
- `proposal` (ChangeProposal): Proposal to validate

**Returns:** ValidationResult with `is_valid` (bool) and `errors` (List[str])

---

## ChangelogGenerator API

Auto-updates SPEC.md CHANGELOG section.

### Class: ChangelogGenerator

```python
class ChangelogGenerator:
    def add_entry(self, change_id: str, title: str, author: str, 
                  timestamp: str, approval_chain: Optional[List[str]] = None) -> str
```

#### Methods

##### add_entry(...) → str

Add entry to CHANGELOG and return updated SPEC.md content.

**Parameters:**
- `change_id` (str): Change ID
- `title` (str): Change title
- `author` (str): Proposer name
- `timestamp` (str): ISO-8601 timestamp
- `approval_chain` (Optional[List[str]]): Approver names

**Returns:** Updated SPEC.md content

##### format_entry(...) → str

Format a changelog entry (for testing).

**Parameters:** Same as `add_entry`

**Returns:** Formatted entry text

##### read_changelog() → List[Dict]

Read existing CHANGELOG entries.

**Returns:** List of changelog entries as dicts

##### read_spec() → str

Read current SPEC.md.

**Returns:** SPEC.md content as string

---

## RollbackManager API

Tracks SPEC.md versions and enables rollback.

### Class: RollbackManager

```python
class RollbackManager:
    def create_version(self, change_id: str, previous_hash: str, new_hash: str,
                      changes: Dict[str, str]) -> SpecVersion
```

#### Methods

##### create_version(...) → SpecVersion

Create a version record for a change.

**Parameters:**
- `change_id` (str): ID of change being applied
- `previous_hash` (str): SHA-256 of SPEC.md before change
- `new_hash` (str): SHA-256 of SPEC.md after change
- `changes` (Dict[str, str]): Changed sections

**Returns:** SpecVersion record

##### get_history() → List[SpecVersion]

Get complete change history.

**Returns:** List of SpecVersion in chronological order

##### rollback(steps: int = 1) → Dict

Rollback one or more changes.

**Parameters:**
- `steps` (int): Number of changes to revert

**Returns:** Dict with success status and details

##### rollback_to_version(version_id: str) → Dict

Rollback to a specific version.

**Parameters:**
- `version_id` (str): Version to rollback to

**Returns:** Dict with success status and details

---

## Data Classes

### ChangeProposal

```python
@dataclass
class ChangeProposal:
    change_id: str
    proposer: str
    proposer_role: str
    timestamp: str
    affected_sections: List[str]
    proposed_changes: Dict[str, str]
    rationale: str
    compatibility_notes: Optional[str] = None
    breaking_change: bool = False
    migration_path: Optional[str] = None
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
```

### SubmissionResult

```python
@dataclass
class SubmissionResult:
    status: str
    change_id: str
    reason: Optional[str] = None
    requires_migration_path: bool = False
    next_steps: Optional[str] = None
    approval_chain: List[str] = field(default_factory=list)
```

### ImpactAnalysis

```python
@dataclass
class ImpactAnalysis:
    change_id: str
    affected_sections: List[str]
    is_breaking_change: bool
    affected_agents: List[str]
    affected_workflows: List[str]
    compatibility_risks: List[str]
    migration_required: bool
    downstream_impact: Dict[str, List[str]]
```

### AuditEntry

```python
@dataclass(frozen=True)
class AuditEntry:
    entry_id: str
    change_id: str
    action: str
    actor: str
    actor_role: str
    timestamp: str
    details: Dict
    previous_hash: Optional[str] = None
    approval_chain: List[ApprovalEntry] = field(default_factory=list)
```

### ApprovalEntry

```python
@dataclass
class ApprovalEntry:
    change_id: str
    approver: str
    approver_role: str
    approval_timestamp: str
    status: str
    comments: Optional[str] = None
```

### SpecVersion

```python
@dataclass
class SpecVersion:
    version_id: str
    change_id: str
    timestamp: str
    previous_hash: str
    new_hash: str
    applied_changes: Dict[str, str]
```

---

## Error Handling

### ImmutableError

Raised when attempting to modify an immutable audit entry.

```python
try:
    entry.action = "modified"  # This will fail
except ImmutableError:
    print("Cannot modify audit entries after creation")
```

### ValidationError

Returned in ValidationResult.errors when proposal is invalid.

### AuthorizationError

Returned in SubmissionResult when role is not authorized.

---

## Examples

### Complete Workflow Example

```python
from src.skills.spec_management.scripts import (
    SpecManager, ChangeProposal, ChangeValidator, Authorizer
)

# Initialize components
spec_manager = SpecManager()
authorizer = Authorizer()

# 1. Create proposal
proposal = ChangeProposal(
    change_id="SPEC-2024-001",
    proposer="alice",
    proposer_role="principal-engineer",
    timestamp="2024-05-09T10:30:00Z",
    affected_sections=["Executive Summary"],
    proposed_changes={"Executive Summary": "Updated summary..."},
    rationale="Clarify the executive summary for improved understanding"
)

# 2. Validate
result = spec_manager.validate_proposal(proposal)
if not result.is_valid:
    print(f"Validation failed: {result.errors}")
    exit(1)

# 3. Check authorization
if not authorizer.can_propose(proposal.proposer_role):
    print("NOT authorized to propose")
    exit(1)

# 4. Submit
submission = spec_manager.submit_proposal(proposal)
if submission.status == "rejected":
    print(f"Rejected: {submission.reason}")
    exit(1)

print(f"Proposal submitted: {submission.change_id}")
print(f"Awaiting approval from: {', '.join(submission.approval_chain)}")

# 5. Approve (as principal engineer)
approval_result = spec_manager.approve_change(
    change_id="SPEC-2024-001",
    approver="bob",
    approver_role="security-engineer",
    comments="Looks good"
)

print(f"Approval status: {approval_result.status}")
```

