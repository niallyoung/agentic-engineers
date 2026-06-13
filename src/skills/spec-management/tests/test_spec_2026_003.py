"""End-to-end test for SPEC-2026-003 proposal workflow.

This test simulates the complete flow for fixing the AutomationController reference
in docs/SPEC.md using the spec-management skill.
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
    """Create temporary data directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_spec_file(temp_data_dir):
    """Create a temporary SPEC.md file similar to the real one."""
    spec_file = Path(temp_data_dir) / "SPEC.md"
    spec_content = """# SPEC.md Test Document

## Polling Architecture

The Orchestrator uses AutomationController to poll the queue periodically.
This component is responsible for checking for new tasks.

### Full Reference

See the integration guide for more details.

## Summary

This is the end of the document.
"""
    spec_file.write_text(spec_content)
    return str(spec_file)


@pytest.fixture
def monkeypatch_home(monkeypatch, temp_data_dir):
    """Monkeypatch home directory."""
    monkeypatch.setenv("HOME", temp_data_dir)
    return temp_data_dir


class TestSPEC2026003:
    """Test SPEC-2026-003 proposal workflow."""

    def test_full_workflow_proposal_to_approval(self, monkeypatch_home, temp_spec_file):
        """Test complete workflow from proposal submission to approval."""
        manager = SpecManager(spec_path=temp_spec_file)

        # Step 1: Create and submit proposal
        proposal_dict = {
            "change_id": "SPEC-2026-003",
            "proposer": "principal-engineer",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Integration & Polling Architecture"],
            "proposed_changes": {
                "Integration & Polling Architecture": """### Integration & Polling Architecture

The Orchestrator operates via harness-initiated polling:
- Each harness (OpenCode, Copilot, Claude, PI) owns its idle-loop via OrchestratorSkill.run_idle_loop()
- Harness wakes up on schedule and calls orchestrator to check queue
- No long-running daemon processes
"""
            },
            "rationale": "Fix stale AutomationController reference. AutomationController was removed in the 2026-05-17 daemon-removal refactor. The harness now owns polling via OrchestratorSkill.run_idle_loop. This proposal updates SPEC.md to document the actual polling mechanism.",
            "insertion_point": "before:### Full Reference",
        }

        proposal = manager.parse_proposal(proposal_dict)
        submission = manager.submit_proposal(proposal)

        # Verify submission
        assert submission.status == "pending_approval"
        assert submission.change_id == "SPEC-2026-003"
        assert "principal-engineer" in submission.approval_chain

        # Step 2: Security engineer approves
        approval1 = manager.approve_change(
            change_id="SPEC-2026-003",
            approver="security-engineer",
            approver_role="security-engineer",
            comments="Security review passed. No breaking changes."
        )

        assert approval1.status == "pending_approval"

        # Step 3: Principal engineer approves (final)
        approval2 = manager.approve_change(
            change_id="SPEC-2026-003",
            approver="principal-engineer",
            approver_role="principal-engineer",
            comments="Approved. Applying change to SPEC.md."
        )

        assert approval2.status == "approved"

        # Step 4: Verify change was applied to SPEC.md
        with open(temp_spec_file, 'r') as f:
            spec_content = f.read()

        # Should contain the new section
        assert "OrchestratorSkill.run_idle_loop" in spec_content
        # Should not contain AutomationController mention in new section
        lines = spec_content.split("\n")
        # Find the new section and verify it's before "### Full Reference"
        new_section_idx = None
        full_ref_idx = None

        for i, line in enumerate(lines):
            if "OrchestratorSkill.run_idle_loop" in line:
                new_section_idx = i
            if "### Full Reference" in line:
                full_ref_idx = i

        assert new_section_idx is not None
        assert full_ref_idx is not None
        assert new_section_idx < full_ref_idx

    def test_proposal_persistence_across_instances(self, monkeypatch_home, temp_spec_file):
        """Test that proposals and audit trail persist across SpecManager instances."""
        manager1 = SpecManager(spec_path=temp_spec_file)

        # Create and submit proposal
        proposal_dict = {
            "change_id": "SPEC-2026-003",
            "proposer": "principal-engineer",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Integration & Polling Architecture"],
            "proposed_changes": {"Integration & Polling Architecture": "New content"},
            "rationale": "Fix stale AutomationController reference and update polling architecture documentation",
            "insertion_point": "before:### Full Reference",
        }

        proposal = manager1.parse_proposal(proposal_dict)
        result = manager1.submit_proposal(proposal)

        assert result.status == "pending_approval"

        # Create a new manager instance - should load persisted proposal
        manager2 = SpecManager(spec_path=temp_spec_file)

        assert "SPEC-2026-003" in manager2._proposals
        assert manager2._proposals["SPEC-2026-003"].insertion_point == "before:### Full Reference"

        # Load audit trail in new instance
        audit_data = manager2._load_persisted_audit_trail("SPEC-2026-003")
        assert len(audit_data) > 0
        assert any(e["action"] == "proposed" for e in audit_data)

    def test_insertion_point_before_full_reference(self, monkeypatch_home, temp_spec_file):
        """Test that new section is inserted before 'Full Reference'."""
        manager = SpecManager(spec_path=temp_spec_file)

        proposal_dict = {
            "change_id": "SPEC-2026-003",
            "proposer": "principal-engineer",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Integration & Polling Architecture"],
            "proposed_changes": {
                "Integration & Polling Architecture": "MARKER_NEW_SECTION"
            },
            "rationale": "Fix stale AutomationController reference and update polling architecture documentation",
            "insertion_point": "before:### Full Reference",
        }

        proposal = manager.parse_proposal(proposal_dict)
        manager._proposals[proposal.change_id] = proposal

        with open(temp_spec_file, 'r') as f:
            original = f.read()

        result = manager._apply_positional_insertion(original, proposal)

        # Verify insertion order
        marker_idx = result.find("MARKER_NEW_SECTION")
        full_ref_idx = result.find("### Full Reference")

        assert marker_idx != -1, "New section not found"
        assert full_ref_idx != -1, "Full Reference section not found"
        assert marker_idx < full_ref_idx, "New section should be before Full Reference"
