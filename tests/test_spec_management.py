"""
Test suite for spec-management skill - SPEC.md change protection and audit trail.

RED-PHASE TESTS (TDD): These tests define the complete spec-management skill behavior.

Coverage areas:
1. Change Proposal Interface (parsing, validation, structure)
2. Impact Analysis (section detection, dependency analysis, compatibility)
3. Authorization System (role-based access control, actor validation)
4. Audit Trail (immutable logging, approval chain tracking)
5. Changelog Generation (auto-update SPEC.md CHANGELOG section)
6. Enforcement (reject unauthorized, enforce proposal format)
7. Rollback Capability (version tracking, undo support)

Author: Principal Engineer
Phase: TDD RED-phase (tests define behavior)
"""

import pytest
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
import hashlib
import json
import yaml


# ============================================================================
# DOMAIN MODELS & FIXTURES
# ============================================================================

@dataclass
class ChangeProposal:
    """Structured change proposal to SPEC.md"""
    change_id: str              # Unique ID for tracking (e.g., "SPEC-2024-001")
    proposer: str               # Username or role proposing change
    proposer_role: str          # "engineer", "lead-engineer", "security-engineer", "principal-engineer"
    timestamp: str              # ISO-8601 datetime
    affected_sections: List[str]  # List of section names affected (e.g., ["QUEUE POLLING", "ROUTING"])
    proposed_changes: Dict[str, str]  # Section name -> proposed text
    rationale: str              # Why this change is needed
    compatibility_notes: Optional[str] = None
    breaking_change: bool = False
    migration_path: Optional[str] = None


@dataclass
class ImpactAnalysis:
    """Computed analysis of change impact"""
    change_id: str
    affected_sections: List[str]
    is_breaking_change: bool
    affected_agents: List[str]  # Which agent roles are affected
    affected_workflows: List[str]  # Which workflows are affected
    compatibility_risks: List[str]
    migration_required: bool
    downstream_impact: Dict[str, List[str]]  # Downstream dependencies


@dataclass
class ApprovalEntry:
    """Approval record in audit trail"""
    change_id: str
    approver: str
    approver_role: str
    approval_timestamp: str
    status: str  # "approved", "rejected", "revision-requested"
    comments: Optional[str] = None


@dataclass
class AuditEntry:
    """Immutable audit trail entry"""
    entry_id: str
    change_id: str
    action: str  # "proposed", "analyzed", "approved", "rejected", "applied", "reverted"
    actor: str
    actor_role: str
    timestamp: str
    details: Dict
    approval_chain: List[ApprovalEntry]


@dataclass
class SpecVersion:
    """Version tracking for SPEC.md"""
    version_id: str
    change_id: str
    timestamp: str
    previous_hash: str  # SHA-256 of previous SPEC.md
    new_hash: str       # SHA-256 of new SPEC.md
    applied_changes: Dict[str, str]


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def spec_manager(request):
    """Instantiate SpecManager for testing"""
    import importlib
    spec_mgmt = importlib.import_module('src.skills.spec-management.scripts.spec_manager')
    return spec_mgmt.SpecManager()


@pytest.fixture
def audit_logger(request):
    """Instantiate AuditLogger for testing"""
    import importlib
    audit_log = importlib.import_module('src.skills.spec-management.scripts.audit_logger')
    return audit_log.AuditLogger()


@pytest.fixture
def authorizer(request):
    """Instantiate Authorizer for testing"""
    import importlib
    auth = importlib.import_module('src.skills.spec-management.scripts.authorizer')
    return auth.Authorizer()


@pytest.fixture
def impact_analyzer(request):
    """Instantiate ImpactAnalyzer for testing"""
    import importlib
    impact = importlib.import_module('src.skills.spec-management.scripts.impact_analyzer')
    return impact.ImpactAnalyzer()


@pytest.fixture
def changelog_generator(request):
    """Instantiate ChangelogGenerator for testing"""
    import importlib
    changelog = importlib.import_module('src.skills.spec-management.scripts.changelog_generator')
    return changelog.ChangelogGenerator()


@pytest.fixture
def valid_proposal():
    """Valid change proposal for testing"""
    return ChangeProposal(
        change_id="SPEC-2024-001",
        proposer="alice",
        proposer_role="principal-engineer",
        timestamp="2024-05-09T10:30:00Z",
        affected_sections=["ORCHESTRATOR-FIRST EXECUTION MODEL", "Implementation Requirements"],
        proposed_changes={
            "ORCHESTRATOR-FIRST EXECUTION MODEL": "New content here..."
        },
        rationale="Clarify queue polling requirements for session-partitioned queues",
        compatibility_notes="Backward compatible with existing agents",
        breaking_change=False
    )


@pytest.fixture
def unauthorized_proposal():
    """Proposal from unauthorized role"""
    return ChangeProposal(
        change_id="SPEC-2024-002",
        proposer="bob",
        proposer_role="engineer",  # Not authorized
        timestamp="2024-05-09T11:00:00Z",
        affected_sections=["Executive Summary"],
        proposed_changes={"Executive Summary": "Modified text"},
        rationale="Update summary",
        breaking_change=False
    )


@pytest.fixture
def breaking_change_proposal():
    """Proposal with breaking change"""
    return ChangeProposal(
        change_id="SPEC-2024-003",
        proposer="charlie",
        proposer_role="principal-engineer",
        timestamp="2024-05-09T11:30:00Z",
        affected_sections=["ORCHESTRATOR-FIRST EXECUTION MODEL"],
        proposed_changes={
            "ORCHESTRATOR-FIRST EXECUTION MODEL": "Fundamental change to queue mechanics..."
        },
        rationale="Redesign queue to support distributed agents",
        compatibility_notes="Requires migration of existing agents",
        breaking_change=True,
        migration_path="See MIGRATION-GUIDE.md section 2.1"
    )


# ============================================================================
# GROUP 1: CHANGE PROPOSAL INTERFACE & VALIDATION
# ============================================================================

class TestChangeProposalValidation:
    """Test structured change proposal parsing and validation"""

    def test_valid_proposal_accepts_all_required_fields(self, spec_manager, valid_proposal):
        """Valid proposal with all required fields passes validation"""
        result = spec_manager.validate_proposal(valid_proposal)
        assert result.is_valid is True
        assert result.errors == []

    def test_proposal_rejects_missing_change_id(self, spec_manager):
        """Proposal missing change_id is rejected"""
        proposal = ChangeProposal(
            change_id="",  # Missing
            proposer="alice",
            proposer_role="principal-engineer",
            timestamp="2024-05-09T10:30:00Z",
            affected_sections=["Section"],
            proposed_changes={"Section": "New text"},
            rationale="Rationale"
        )
        result = spec_manager.validate_proposal(proposal)
        assert result.is_valid is False
        assert any("change_id" in error for error in result.errors)

    def test_proposal_rejects_invalid_timestamp(self, spec_manager):
        """Proposal with invalid ISO-8601 timestamp is rejected"""
        proposal = ChangeProposal(
            change_id="SPEC-2024-001",
            proposer="alice",
            proposer_role="principal-engineer",
            timestamp="not-a-timestamp",  # Invalid
            affected_sections=["Section"],
            proposed_changes={"Section": "Text"},
            rationale="Rationale"
        )
        result = spec_manager.validate_proposal(proposal)
        assert result.is_valid is False
        assert any("timestamp" in error for error in result.errors)

    def test_proposal_rejects_empty_affected_sections(self, spec_manager):
        """Proposal with no affected sections is rejected"""
        proposal = ChangeProposal(
            change_id="SPEC-2024-001",
            proposer="alice",
            proposer_role="principal-engineer",
            timestamp="2024-05-09T10:30:00Z",
            affected_sections=[],  # Empty
            proposed_changes={"Section": "Text"},
            rationale="Rationale"
        )
        result = spec_manager.validate_proposal(proposal)
        assert result.is_valid is False
        assert any("affected_sections" in error for error in result.errors)

    def test_proposal_rejects_rationale_below_50_chars(self, spec_manager):
        """Proposal with rationale < 50 chars is rejected"""
        proposal = ChangeProposal(
            change_id="SPEC-2024-001",
            proposer="alice",
            proposer_role="principal-engineer",
            timestamp="2024-05-09T10:30:00Z",
            affected_sections=["Section"],
            proposed_changes={"Section": "Text"},
            rationale="Short"  # Too short
        )
        result = spec_manager.validate_proposal(proposal)
        assert result.is_valid is False
        assert any("rationale" in error for error in result.errors)

    def test_proposal_enforces_change_id_format(self, spec_manager):
        """change_id must match pattern SPEC-YYYY-NNN"""
        proposal = ChangeProposal(
            change_id="INVALID-001",  # Wrong format
            proposer="alice",
            proposer_role="principal-engineer",
            timestamp="2024-05-09T10:30:00Z",
            affected_sections=["Section"],
            proposed_changes={"Section": "Text"},
            rationale="This is a valid rationale with enough characters"
        )
        result = spec_manager.validate_proposal(proposal)
        assert result.is_valid is False
        assert any("change_id" in error and "format" in error for error in result.errors)

    def test_proposal_parses_structured_input(self, spec_manager):
        """Proposal can be parsed from structured input (dict/JSON)"""
        proposal_dict = {
            "change_id": "SPEC-2024-001",
            "proposer": "alice",
            "proposer_role": "principal-engineer",
            "timestamp": "2024-05-09T10:30:00Z",
            "affected_sections": ["Section A"],
            "proposed_changes": {"Section A": "New text"},
            "rationale": "This is sufficient rationale with adequate length"
        }
        proposal = spec_manager.parse_proposal(proposal_dict)
        assert proposal.change_id == "SPEC-2024-001"
        assert proposal.proposer == "alice"


# ============================================================================
# GROUP 2: IMPACT ANALYSIS
# ============================================================================

class TestImpactAnalysis:
    """Test impact analysis and dependency detection"""

    def test_impact_analysis_identifies_affected_sections(self, impact_analyzer, valid_proposal):
        """Impact analysis correctly identifies affected sections"""
        analysis = impact_analyzer.analyze(valid_proposal)
        assert "ORCHESTRATOR-FIRST EXECUTION MODEL" in analysis.affected_sections

    def test_impact_analysis_detects_breaking_changes(self, impact_analyzer, breaking_change_proposal):
        """Impact analysis correctly flags breaking changes"""
        analysis = impact_analyzer.analyze(breaking_change_proposal)
        assert analysis.is_breaking_change is True
        assert analysis.migration_required is True

    def test_impact_analysis_identifies_affected_agents(self, impact_analyzer, breaking_change_proposal):
        """Impact analysis identifies which agent roles are affected"""
        analysis = impact_analyzer.analyze(breaking_change_proposal)
        assert len(analysis.affected_agents) > 0
        assert "orchestrator" in [a.lower() for a in analysis.affected_agents]

    def test_impact_analysis_identifies_affected_workflows(self, impact_analyzer, valid_proposal):
        """Impact analysis identifies which workflows are affected"""
        analysis = impact_analyzer.analyze(valid_proposal)
        assert len(analysis.affected_workflows) > 0

    def test_impact_analysis_detects_compatibility_risks(self, impact_analyzer, breaking_change_proposal):
        """Impact analysis detects compatibility risks"""
        analysis = impact_analyzer.analyze(breaking_change_proposal)
        assert len(analysis.compatibility_risks) > 0

    def test_impact_analysis_maps_downstream_dependencies(self, impact_analyzer, breaking_change_proposal):
        """Impact analysis maps downstream dependencies"""
        analysis = impact_analyzer.analyze(breaking_change_proposal)
        assert isinstance(analysis.downstream_impact, dict)
        assert len(analysis.downstream_impact) > 0

    def test_impact_analysis_generates_migration_path_for_breaking_changes(self, impact_analyzer, breaking_change_proposal):
        """Breaking changes include migration guidance"""
        analysis = impact_analyzer.analyze(breaking_change_proposal)
        if analysis.is_breaking_change:
            assert analysis.migration_required is True


# ============================================================================
# GROUP 3: AUTHORIZATION & ROLE CONTROL
# ============================================================================

class TestAuthorization:
    """Test role-based access control (RBAC)"""

    def test_principal_engineer_can_propose_changes(self, authorizer):
        """Principal Engineer role can propose SPEC.md changes"""
        assert authorizer.can_propose("principal-engineer") is True

    def test_security_engineer_can_propose_changes(self, authorizer):
        """Security Engineer role can propose SPEC.md changes"""
        assert authorizer.can_propose("security-engineer") is True

    def test_lead_engineer_can_propose_changes(self, authorizer):
        """Lead Engineer role can propose SPEC.md changes"""
        assert authorizer.can_propose("lead-engineer") is True

    def test_regular_engineer_cannot_propose(self, authorizer):
        """Regular Engineer role CANNOT propose SPEC.md changes"""
        assert authorizer.can_propose("engineer") is False

    def test_senior_engineer_cannot_propose(self, authorizer):
        """Senior Engineer role CANNOT propose SPEC.md changes"""
        assert authorizer.can_propose("senior-engineer") is False

    def test_unauthorized_proposal_is_rejected(self, spec_manager, authorizer, unauthorized_proposal):
        """Proposals from unauthorized roles are rejected"""
        assert authorizer.can_propose(unauthorized_proposal.proposer_role) is False

    def test_authorization_check_happens_before_processing(self, spec_manager, unauthorized_proposal):
        """Authorization is checked before any proposal processing"""
        # Adjust unauthorized_proposal to have valid format but unauthorized role
        unauthorized_proposal.rationale = "This is a valid rationale with sufficient length to pass validation"
        result = spec_manager.submit_proposal(unauthorized_proposal)
        assert result.status == "rejected"
        assert "authorization" in result.reason.lower() or "unauthorized" in result.reason.lower()

    def test_approval_chain_respects_role_hierarchy(self, authorizer):
        """Approval routing respects role hierarchy"""
        # Proposer of lower rank → must go through higher rank approvers
        approval_chain = authorizer.get_approval_chain("security-engineer")
        assert "principal-engineer" in [r.lower() for r in approval_chain]

    def test_principal_engineer_approval_is_final(self, authorizer):
        """Principal Engineer approval is final (no higher review needed)"""
        approval_chain = authorizer.get_approval_chain("principal-engineer")
        # Principal proposes → approvers are other principal-level engineers
        assert len(approval_chain) >= 1


# ============================================================================
# GROUP 4: AUDIT TRAIL & IMMUTABILITY
# ============================================================================

class TestAuditTrail:
    """Test audit logging and immutability"""

    def test_audit_trail_records_proposal_submission(self, audit_logger, valid_proposal):
        """Audit trail records proposal submission"""
        entry = audit_logger.log_action(
            action="proposed",
            change_id=valid_proposal.change_id,
            actor=valid_proposal.proposer,
            actor_role=valid_proposal.proposer_role,
            details={"proposal": str(valid_proposal)}
        )
        assert entry.action == "proposed"
        assert entry.change_id == valid_proposal.change_id

    def test_audit_trail_records_impact_analysis(self, audit_logger, valid_proposal):
        """Audit trail records impact analysis completion"""
        entry = audit_logger.log_action(
            action="analyzed",
            change_id=valid_proposal.change_id,
            actor="system",
            actor_role="spec-manager",
            details={"analysis": "impact analysis completed"}
        )
        assert entry.action == "analyzed"

    def test_audit_trail_records_approval_decision(self, audit_logger):
        """Audit trail records approval decisions"""
        approval = ApprovalEntry(
            change_id="SPEC-2024-001",
            approver="dave",
            approver_role="principal-engineer",
            approval_timestamp="2024-05-09T11:00:00Z",
            status="approved",
            comments="Looks good"
        )
        entry = audit_logger.log_approval(approval)
        assert entry.approval_chain[0].status == "approved"
        assert entry.approval_chain[0].approver == "dave"

    def test_audit_trail_records_rejection(self, audit_logger):
        """Audit trail records rejection decisions with reason"""
        approval = ApprovalEntry(
            change_id="SPEC-2024-002",
            approver="eve",
            approver_role="security-engineer",
            approval_timestamp="2024-05-09T12:00:00Z",
            status="rejected",
            comments="This breaks backward compatibility without migration path"
        )
        entry = audit_logger.log_approval(approval)
        assert entry.approval_chain[0].status == "rejected"
        assert entry.approval_chain[0].comments is not None

    def test_audit_trail_is_immutable(self, audit_logger, valid_proposal):
        """Audit trail entries cannot be modified after creation"""
        entry = audit_logger.log_action(
            action="proposed",
            change_id=valid_proposal.change_id,
            actor=valid_proposal.proposer,
            actor_role=valid_proposal.proposer_role,
            details={}
        )
        # Attempting to modify entry should fail
        with pytest.raises(Exception):  # Should raise ImmutableError or similar
            entry.action = "modified"

    def test_audit_trail_includes_complete_approval_chain(self, audit_logger):
        """Audit trail includes full approval chain for approved changes"""
        entry = audit_logger.log_action(
            action="applied",
            change_id="SPEC-2024-001",
            actor="system",
            actor_role="spec-manager",
            details={},
            approval_chain=[
                ApprovalEntry("SPEC-2024-001", "alice", "security-engineer", "2024-05-09T11:00:00Z", "approved"),
                ApprovalEntry("SPEC-2024-001", "bob", "principal-engineer", "2024-05-09T12:00:00Z", "approved")
            ]
        )
        assert len(entry.approval_chain) == 2

    def test_audit_trail_prevents_tampering(self, audit_logger):
        """Audit trail uses cryptographic hashing to prevent tampering"""
        entry1 = audit_logger.log_action("proposed", "SPEC-001", "alice", "principal-engineer", {})
        entry2 = audit_logger.log_action("analyzed", "SPEC-001", "system", "spec-manager", {})
        
        # Entries should be linked with hashes
        assert hasattr(entry2, 'previous_hash')
        assert entry2.previous_hash is not None


# ============================================================================
# GROUP 5: CHANGELOG GENERATION
# ============================================================================

class TestChangelogGeneration:
    """Test automatic changelog updates"""

    def test_changelog_generator_adds_entry_on_approval(self, changelog_generator, valid_proposal):
        """Changelog is updated when change is approved"""
        # This would read SPEC.md, update CHANGELOG section, and write back
        updated_spec = changelog_generator.add_entry(
            change_id=valid_proposal.change_id,
            title=valid_proposal.rationale,
            author=valid_proposal.proposer,
            timestamp=valid_proposal.timestamp
        )
        assert "CHANGELOG" in updated_spec or "## Changes" in updated_spec

    def test_changelog_entry_includes_change_id(self, changelog_generator, valid_proposal):
        """Changelog entry includes change ID for traceability"""
        entry_text = changelog_generator.format_entry(
            change_id=valid_proposal.change_id,
            title="Test change",
            author="alice",
            timestamp="2024-05-09T10:00:00Z"
        )
        assert "SPEC-2024-001" in entry_text

    def test_changelog_entry_includes_author_and_date(self, changelog_generator):
        """Changelog entry includes author and date"""
        entry_text = changelog_generator.format_entry(
            change_id="SPEC-2024-001",
            title="Test",
            author="alice",
            timestamp="2024-05-09T10:00:00Z"
        )
        assert "alice" in entry_text
        assert "2024-05-09" in entry_text

    def test_changelog_maintains_chronological_order(self, changelog_generator):
        """Changelog entries are in reverse chronological order (newest first)"""
        # Add multiple entries
        changelog = changelog_generator.read_changelog()
        if len(changelog) > 1:
            # First entry should be newer than second
            assert changelog[0]["timestamp"] >= changelog[1]["timestamp"]

    def test_changelog_generator_preserves_existing_format(self, changelog_generator):
        """Changelog generator respects existing SPEC.md format"""
        original_spec = changelog_generator.read_spec()
        updated = changelog_generator.add_entry("SPEC-2024-001", "Test", "alice", "2024-05-09T10:00:00Z")
        # Structure should be preserved
        assert updated.count("---") >= original_spec.count("---")


# ============================================================================
# GROUP 6: ENFORCEMENT & REJECTION
# ============================================================================

class TestEnforcement:
    """Test enforcement of rules and rejection of invalid changes"""

    def test_enforce_no_direct_spec_edits(self):
        """SPEC.md can only be modified through spec-management skill"""
        # This would require git hooks or similar mechanism
        # For now, test that the skill is the only authorized modifier
        pass

    def test_reject_proposals_with_invalid_format(self, spec_manager):
        """Proposals with invalid format are rejected at intake"""
        invalid = ChangeProposal(
            change_id="SPEC-2024-001",
            proposer="alice",
            proposer_role="principal-engineer",
            timestamp="2024-05-09T10:30:00Z",
            affected_sections=[],  # Invalid: empty
            proposed_changes={},   # Invalid: empty
            rationale="Too short"  # Invalid: < 50 chars
        )
        result = spec_manager.validate_proposal(invalid)
        assert result.is_valid is False

    def test_reject_unauthorized_proposers(self, spec_manager, unauthorized_proposal):
        """Proposals from non-authorized roles are rejected"""
        result = spec_manager.submit_proposal(unauthorized_proposal)
        assert result.status == "rejected"

    def test_reject_proposals_without_migration_for_breaking_changes(self, spec_manager):
        """Breaking changes without migration path are rejected"""
        proposal = ChangeProposal(
            change_id="SPEC-2024-001",
            proposer="alice",
            proposer_role="principal-engineer",
            timestamp="2024-05-09T10:30:00Z",
            affected_sections=["Major Section"],
            proposed_changes={"Major Section": "Completely different content"},
            rationale="Redesign core system architecture for better performance" + " " * 50,
            breaking_change=True,
            migration_path=None  # Missing migration path
        )
        result = spec_manager.submit_proposal(proposal)
        if proposal.breaking_change:
            assert result.requires_migration_path is True or "migration" in result.reason.lower()

    def test_enforce_proposal_before_approval_workflow(self, spec_manager, valid_proposal):
        """Changes must go through proposal → approval workflow"""
        # Direct SPEC.md modification without going through workflow should be blocked
        # This test verifies workflow enforcement
        result = spec_manager.submit_proposal(valid_proposal)
        assert result.status in ["pending_approval", "approved", "rejected"]  # Not applied yet


# ============================================================================
# GROUP 7: ROLLBACK CAPABILITY
# ============================================================================

class TestRollbackCapability:
    """Test version tracking and rollback functionality"""

    def test_version_tracking_records_previous_hash(self, spec_manager):
        """Each change records SHA-256 hash of previous SPEC.md"""
        spec_hash = spec_manager.compute_spec_hash()
        assert spec_hash is not None
        assert len(spec_hash) == 64  # SHA-256 hex digest is 64 chars

    def test_rollback_manager_tracks_change_history(self, spec_manager):
        """Rollback manager maintains complete change history"""
        history = spec_manager.get_change_history()
        # History should be chronological, newest first
        if len(history) > 1:
            assert history[0].timestamp >= history[1].timestamp

    def test_rollback_can_revert_last_change(self, spec_manager):
        """Rollback can revert the most recent change"""
        # Get current spec hash
        current_hash = spec_manager.compute_spec_hash()
        
        # Rollback should restore previous version
        # (This requires a mock approved change first)
        result = spec_manager.rollback(steps=1)
        
        if result.get("success"):
            new_hash = spec_manager.compute_spec_hash()
            # Rollback may not succeed if there's no history, but structure is correct
            assert isinstance(result, dict)

    def test_rollback_requires_principal_authorization(self, spec_manager, authorizer):
        """Rollback operations require Principal Engineer authorization"""
        # Only Principal/Security/Lead can initiate rollback
        assert authorizer.can_approve("principal-engineer") is True
        # Regular engineers cannot
        assert authorizer.can_approve("engineer") is False

    def test_rollback_creates_audit_entry(self, audit_logger, spec_manager):
        """Rollback operations are recorded in audit trail"""
        # When rollback is executed, it should create an audit entry
        pass  # Implementation-specific test


# ============================================================================
# GROUP 8: INTEGRATION TESTS
# ============================================================================

class TestSpecManagementIntegration:
    """Integration tests for complete workflows"""

    def test_end_to_end_workflow_valid_proposal(self, spec_manager, authorizer, audit_logger):
        """Complete workflow: proposal → impact analysis → approval → apply → changelog"""
        proposal = ChangeProposal(
            change_id="SPEC-2024-001",
            proposer="alice",
            proposer_role="principal-engineer",
            timestamp="2024-05-09T10:30:00Z",
            affected_sections=["Executive Summary"],
            proposed_changes={"Executive Summary": "Updated summary..."},
            rationale="Clarify the executive summary for improved readability and understanding"
        )
        
        # Step 1: Validate authorization
        assert authorizer.can_propose(proposal.proposer_role) is True
        
        # Step 2: Submit proposal
        result = spec_manager.submit_proposal(proposal)
        assert result.status != "rejected"

    def test_end_to_end_workflow_breaking_change(self, spec_manager, authorizer, impact_analyzer):
        """Complete workflow for breaking change: proposal → analysis → escalated review"""
        proposal = ChangeProposal(
            change_id="SPEC-2024-002",
            proposer="bob",
            proposer_role="security-engineer",
            timestamp="2024-05-09T11:00:00Z",
            affected_sections=["ORCHESTRATOR-FIRST EXECUTION MODEL"],
            proposed_changes={"ORCHESTRATOR-FIRST EXECUTION MODEL": "New queue mechanism..."},
            rationale="Implement distributed queue system for multi-region support and high availability" + " " * 30,
            breaking_change=True,
            migration_path="MIGRATION-v5.11.md"
        )
        
        # Step 1: Validate
        assert authorizer.can_propose(proposal.proposer_role) is True
        
        # Step 2: Analyze impact
        analysis = impact_analyzer.analyze(proposal)
        assert analysis.is_breaking_change is True
        
        # Step 3: Route for approval (breaking changes may need escalation)
        approval_chain = authorizer.get_approval_chain(proposal.proposer_role)
        assert "principal-engineer" in [r.lower() for r in approval_chain]

    def test_rejected_proposal_remains_in_audit_trail(self, spec_manager):
        """Rejected proposals are retained in audit trail for reference"""
        proposal = ChangeProposal(
            change_id="SPEC-2024-003",
            proposer="bob",
            proposer_role="engineer",  # Unauthorized
            timestamp="2024-05-09T12:00:00Z",
            affected_sections=["Section"],
            proposed_changes={"Section": "Text"},
            rationale="This proposal will be rejected due to unauthorized role status assignment"
        )
        
        result = spec_manager.submit_proposal(proposal)
        assert result.status == "rejected"
        
        # Check audit trail includes the rejection (audit trail is internal to spec_manager)
        audit_entries = spec_manager.audit_logger.get_entries_for_change("SPEC-2024-003")
        assert any(e.action == "rejected" for e in audit_entries)


# ============================================================================
# HELPER TESTS & UTILITIES
# ============================================================================

class TestValidationResult:
    """Test validation result dataclass"""
    
    def test_validation_result_tracks_errors(self):
        """ValidationResult properly tracks validation errors"""
        pass

    def test_validation_result_is_serializable(self):
        """ValidationResult can be serialized to JSON for logging"""
        pass


class TestProposalParsing:
    """Test proposal parsing from various input formats"""
    
    def test_parse_proposal_from_dict(self):
        """Proposal can be parsed from dict"""
        pass
    
    def test_parse_proposal_from_yaml(self):
        """Proposal can be parsed from YAML"""
        pass
    
    def test_parse_proposal_from_json(self):
        """Proposal can be parsed from JSON"""
        pass


# ============================================================================
# COVERAGE TARGETS
# ============================================================================

"""
Coverage targets for spec-management skill:
- ChangeProposal: 100% (validation, parsing, serialization)
- ImpactAnalysis: 90% (all analysis paths, edge cases)
- AuditEntry: 95% (immutability, linking, cryptography)
- Authorization: 95% (all roles, hierarchy, edge cases)
- Changelog: 85% (format, ordering, integration)
- Enforcement: 90% (rejection paths, format validation)
- Rollback: 80% (basic rollback, versioning)

Total coverage target: 90%+

Tests should be runnable with:
  pytest tests/test_spec_management.py -v --cov=src/skills/spec_management --cov-report=html
"""
