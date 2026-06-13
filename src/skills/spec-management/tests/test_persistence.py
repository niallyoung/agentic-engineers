"""Tests for persistence layer in spec-management skill.

Tests cover:
- Proposal serialization to YAML
- Proposal deserialization from YAML
- Audit trail serialization
- Audit trail deserialization
- Persistence on proposal submission
- Persistence on approval
- Round-trip integrity
"""
import pytest
from pathlib import Path
import tempfile
import os
import shutil
import yaml
from importlib import import_module

# Import the spec-management skill modules
spec_management = import_module("src.skills.spec-management.scripts.spec_manager")
SpecManager = spec_management.SpecManager
ChangeProposal = spec_management.ChangeProposal

audit_logger_module = import_module("src.skills.spec-management.scripts.audit_logger")
AuditLogger = audit_logger_module.AuditLogger
ApprovalEntry = audit_logger_module.ApprovalEntry


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for persistence testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_spec_file(temp_data_dir):
    """Create a temporary SPEC.md file."""
    spec_file = Path(temp_data_dir) / "SPEC.md"
    spec_file.write_text("# SPEC.md\n\n## Section 1\nContent here.\n")
    return str(spec_file)


@pytest.fixture
def monkeypatch_home(monkeypatch, temp_data_dir):
    """Monkeypatch home directory to use temp directory."""
    monkeypatch.setenv("HOME", temp_data_dir)
    return temp_data_dir


class TestProposalPersistence:
    """Test proposal persistence."""

    def test_save_proposal(self, monkeypatch_home, temp_spec_file):
        """Test saving proposal to disk."""
        manager = SpecManager(spec_path=temp_spec_file)

        proposal_dict = {
            "change_id": "SPEC-2026-003",
            "proposer": "principal-engineer",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Queue Architecture"],
            "proposed_changes": {"Queue Architecture": "New content"},
            "rationale": "Add Queue SLA section to improve queue management and monitoring capabilities",
            "insertion_point": "before:## Section 2",
        }

        proposal = manager.parse_proposal(proposal_dict)
        manager._save_proposal(proposal)

        # Verify file exists
        proposal_file = manager.proposals_dir / "SPEC-2026-003.yaml"
        assert proposal_file.exists()

        # Verify content
        with open(proposal_file, 'r') as f:
            saved_data = yaml.safe_load(f)

        assert saved_data["change_id"] == "SPEC-2026-003"
        assert saved_data["insertion_point"] == "before:## Section 2"

    def test_load_persisted_proposals(self, monkeypatch_home, temp_spec_file):
        """Test loading proposals from disk."""
        manager = SpecManager(spec_path=temp_spec_file)

        # Save a proposal
        proposal_dict = {
            "change_id": "SPEC-2026-003",
            "proposer": "principal-engineer",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Queue Architecture"],
            "proposed_changes": {"Queue Architecture": "New content"},
            "rationale": "Add Queue SLA section to improve queue management and monitoring capabilities",
            "insertion_point": "before:## Section 2",
        }

        proposal = manager.parse_proposal(proposal_dict)
        manager._save_proposal(proposal)

        # Create new manager to load proposals
        manager2 = SpecManager(spec_path=temp_spec_file)

        # Should load persisted proposal
        assert "SPEC-2026-003" in manager2._proposals
        assert manager2._proposals["SPEC-2026-003"].insertion_point == "before:## Section 2"

    def test_proposal_roundtrip(self, monkeypatch_home, temp_spec_file):
        """Test proposal save/load roundtrip."""
        manager = SpecManager(spec_path=temp_spec_file)

        proposal_dict = {
            "change_id": "SPEC-2026-004",
            "proposer": "lead-engineer",
            "proposer_role": "lead-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Approval", "Impact"],
            "proposed_changes": {"Approval": "New approval rules", "Impact": "New impact rules"},
            "rationale": "Update approval and impact sections",
            "compatibility_notes": "Backward compatible",
            "breaking_change": False,
            "migration_path": None,
            "insertion_point": "after:## Validation",
        }

        original_proposal = manager.parse_proposal(proposal_dict)
        manager._save_proposal(original_proposal)

        # Create new manager and load
        manager2 = SpecManager(spec_path=temp_spec_file)
        loaded_proposal = manager2._proposals["SPEC-2026-004"]

        # Verify all fields match
        assert loaded_proposal.change_id == original_proposal.change_id
        assert loaded_proposal.proposer == original_proposal.proposer
        assert loaded_proposal.proposer_role == original_proposal.proposer_role
        assert loaded_proposal.timestamp == original_proposal.timestamp
        assert loaded_proposal.affected_sections == original_proposal.affected_sections
        assert loaded_proposal.proposed_changes == original_proposal.proposed_changes
        assert loaded_proposal.rationale == original_proposal.rationale
        assert loaded_proposal.insertion_point == original_proposal.insertion_point


class TestAuditPersistence:
    """Test audit trail persistence."""

    def test_persist_audit_trail(self, monkeypatch_home, temp_spec_file):
        """Test persisting audit trail to disk."""
        manager = SpecManager(spec_path=temp_spec_file)

        # Create some audit entries
        manager.audit_logger.log_action(
            action="proposed",
            change_id="SPEC-2026-003",
            actor="principal-engineer",
            actor_role="principal-engineer",
            details={"test": "data"}
        )

        manager.audit_logger.log_action(
            action="analyzed",
            change_id="SPEC-2026-003",
            actor="system",
            actor_role="spec-manager",
            details={"analysis": "complete"}
        )

        # Persist audit trail
        manager._persist_audit_trail("SPEC-2026-003")

        # Verify file exists
        audit_file = manager.audit_dir / "SPEC-2026-003.yaml"
        assert audit_file.exists()

        # Verify content
        with open(audit_file, 'r') as f:
            audit_data = yaml.safe_load(f)

        assert len(audit_data) == 2
        assert audit_data[0]["action"] == "proposed"
        assert audit_data[1]["action"] == "analyzed"

    def test_load_persisted_audit_trail(self, monkeypatch_home, temp_spec_file):
        """Test loading persisted audit trail."""
        manager = SpecManager(spec_path=temp_spec_file)

        # Create and persist audit entries
        manager.audit_logger.log_action(
            action="proposed",
            change_id="SPEC-2026-003",
            actor="principal-engineer",
            actor_role="principal-engineer",
            details={"proposal": "data"}
        )

        manager._persist_audit_trail("SPEC-2026-003")

        # Load persisted audit trail
        audit_data = manager._load_persisted_audit_trail("SPEC-2026-003")

        assert len(audit_data) == 1
        assert audit_data[0]["action"] == "proposed"
        assert audit_data[0]["change_id"] == "SPEC-2026-003"

    def test_load_nonexistent_audit_trail(self, monkeypatch_home, temp_spec_file):
        """Test loading nonexistent audit trail returns empty list."""
        manager = SpecManager(spec_path=temp_spec_file)

        audit_data = manager._load_persisted_audit_trail("NONEXISTENT")

        assert audit_data == []

    def test_audit_persistence_with_approvals(self, monkeypatch_home, temp_spec_file):
        """Test persisting audit trail with approval entries."""
        manager = SpecManager(spec_path=temp_spec_file)

        change_id = "SPEC-2026-003"

        # Log proposal
        manager.audit_logger.log_action(
            action="proposed",
            change_id=change_id,
            actor="principal-engineer",
            actor_role="principal-engineer",
            details={"proposal": "data"}
        )

        # Log approval
        approval = ApprovalEntry(
            change_id=change_id,
            approver="security-engineer",
            approver_role="security-engineer",
            approval_timestamp="2026-06-13T11:00:00Z",
            status="approved",
            comments="Looks good"
        )
        manager.audit_logger.log_approval(approval)

        # Persist
        manager._persist_audit_trail(change_id)

        # Load and verify
        audit_data = manager._load_persisted_audit_trail(change_id)

        assert len(audit_data) >= 2
        assert any(e["action"] == "proposed" for e in audit_data)
        assert any(e["action"] == "approval_decision" for e in audit_data)


class TestProposalSubmissionPersistence:
    """Test proposal submission with persistence."""

    def test_submit_proposal_persists_to_disk(self, monkeypatch_home, temp_spec_file):
        """Test that submitting a proposal persists it to disk."""
        manager = SpecManager(spec_path=temp_spec_file)

        proposal_dict = {
            "change_id": "SPEC-2026-003",
            "proposer": "principal-engineer",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Queue Architecture"],
            "proposed_changes": {"Queue Architecture": "New content"},
            "rationale": "Add Queue SLA section to improve queue management and monitoring capabilities",
            "insertion_point": "before:## Section 2",
        }

        proposal = manager.parse_proposal(proposal_dict)
        result = manager.submit_proposal(proposal)

        # Verify submission was successful
        assert result.status == "pending_approval"

        # Verify proposal file was created
        proposal_file = manager.proposals_dir / "SPEC-2026-003.yaml"
        assert proposal_file.exists()

        # Verify audit file was created
        audit_file = manager.audit_dir / "SPEC-2026-003.yaml"
        assert audit_file.exists()
