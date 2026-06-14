"""Tests for positional insertion logic in spec-management skill.

Tests cover:
- Parsing insertion_point from proposal YAML
- Finding anchor lines in SPEC.md
- Inserting new section before/after anchor
- Edge cases (anchor not found, invalid format)
"""
import pytest
from pathlib import Path
import tempfile
import os
from importlib import import_module

# Import the spec-management skill module
spec_management = import_module("src.skills.spec-management.scripts.spec_manager")
SpecManager = spec_management.SpecManager
ChangeProposal = spec_management.ChangeProposal


@pytest.fixture
def temp_spec_file():
    """Create a temporary SPEC.md file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""# SPEC.md Test Document

## Section 1
Content for section 1.

## Section 2
Content for section 2.

## Queue Architecture
This is the queue architecture section.
Detailed docs here.

## Section 3
Content for section 3.
""")
        temp_path = f.name

    yield temp_path

    # Cleanup
    try:
        os.unlink(temp_path)
    except:
        pass


@pytest.fixture
def spec_manager(temp_spec_file):
    """Create SpecManager with temporary SPEC file."""
    return SpecManager(spec_path=temp_spec_file)


class TestPositionalInsertion:
    """Test positional insertion logic."""

    def test_parse_insertion_point_before(self):
        """Test parsing 'before' insertion point."""
        proposal_dict = {
            "change_id": "SPEC-2026-003",
            "proposer": "principal-engineer",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Queue Architecture"],
            "proposed_changes": {"Queue Architecture": "New SLA content"},
            "rationale": "Add Queue SLA section to improve queue management and monitoring capabilities",
            "insertion_point": "before:## Section 3",
        }

        manager = SpecManager()
        proposal = manager.parse_proposal(proposal_dict)

        assert proposal.insertion_point == "before:## Section 3"
        assert proposal.change_id == "SPEC-2026-003"

    def test_parse_insertion_point_after(self):
        """Test parsing 'after' insertion point."""
        proposal_dict = {
            "change_id": "SPEC-2026-004",
            "proposer": "principal-engineer",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Queue Architecture"],
            "proposed_changes": {"Queue Architecture": "New content"},
            "rationale": "Add Queue SLA section to improve queue management and monitoring capabilities",
            "insertion_point": "after:## Queue Architecture",
        }

        manager = SpecManager()
        proposal = manager.parse_proposal(proposal_dict)

        assert proposal.insertion_point == "after:## Queue Architecture"

    def test_insertion_before_anchor(self, spec_manager, temp_spec_file):
        """Test inserting new section before anchor line."""
        proposal_dict = {
            "change_id": "SPEC-2026-003",
            "proposer": "principal-engineer",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Queue SLA"],
            "proposed_changes": {"Queue SLA": "## Queue SLA\nNew SLA requirements here."},
            "rationale": "Add Queue SLA section to improve queue management and monitoring capabilities",
            "insertion_point": "before:## Section 3",
        }

        proposal = spec_manager.parse_proposal(proposal_dict)
        spec_manager._proposals[proposal.change_id] = proposal

        # Read original content
        with open(temp_spec_file, 'r') as f:
            original_content = f.read()

        # Apply insertion
        result = spec_manager._apply_positional_insertion(original_content, proposal)

        # Verify Section 3 came after Queue SLA
        assert "## Queue SLA" in result
        assert result.index("## Queue SLA") < result.index("## Section 3")

    def test_insertion_after_anchor(self, spec_manager, temp_spec_file):
        """Test inserting new section after anchor line."""
        proposal_dict = {
            "change_id": "SPEC-2026-003",
            "proposer": "principal-engineer",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Queue SLA"],
            "proposed_changes": {"Queue SLA": "## Queue SLA\nNew SLA requirements here."},
            "rationale": "Add Queue SLA section to improve queue management and monitoring capabilities",
            "insertion_point": "after:## Queue Architecture",
        }

        proposal = spec_manager.parse_proposal(proposal_dict)

        # Read original content
        with open(temp_spec_file, 'r') as f:
            original_content = f.read()

        # Apply insertion
        result = spec_manager._apply_positional_insertion(original_content, proposal)

        # Verify Queue SLA came after Queue Architecture
        assert "## Queue SLA" in result
        assert result.index("## Queue Architecture") < result.index("## Queue SLA")

    def test_insertion_point_anchor_not_found(self, spec_manager, temp_spec_file):
        """Test error when anchor line not found."""
        proposal_dict = {
            "change_id": "SPEC-2026-003",
            "proposer": "principal-engineer",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Queue SLA"],
            "proposed_changes": {"Queue SLA": "New content"},
            "rationale": "Add Queue SLA section to improve queue management and monitoring capabilities",
            "insertion_point": "before:## Nonexistent Section",
        }

        proposal = spec_manager.parse_proposal(proposal_dict)

        with open(temp_spec_file, 'r') as f:
            original_content = f.read()

        # Should raise ValueError
        with pytest.raises(ValueError, match="Anchor line not found"):
            spec_manager._apply_positional_insertion(original_content, proposal)

    def test_insertion_point_ambiguous_anchor_raises(self, spec_manager):
        """Test error when anchor matches more than one line (ambiguous).

        Silently picking the first match risks inserting content at the wrong
        position, so an anchor that resolves to multiple lines must be rejected.
        """
        content = (
            "# Doc\n"
            "## Repeated Heading\n"
            "Body A.\n"
            "## Repeated Heading\n"
            "Body B.\n"
        )

        proposal_dict = {
            "change_id": "SPEC-2026-003",
            "proposer": "principal-engineer",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Queue SLA"],
            "proposed_changes": {"Queue SLA": "## Queue SLA\nNew content"},
            "rationale": "Add Queue SLA section to improve queue management and monitoring capabilities",
            "insertion_point": "before:## Repeated Heading",
        }

        proposal = spec_manager.parse_proposal(proposal_dict)

        with pytest.raises(ValueError, match="Ambiguous anchor"):
            spec_manager._apply_positional_insertion(content, proposal)


    def test_insertion_point_invalid_format(self, spec_manager):
        """Test error with invalid insertion_point format."""
        proposal_dict = {
            "change_id": "SPEC-2026-003",
            "proposer": "principal-engineer",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Queue SLA"],
            "proposed_changes": {"Queue SLA": "New content"},
            "rationale": "Add Queue SLA section to improve queue management and monitoring capabilities",
            "insertion_point": "invalid_format_no_colon",
        }

        proposal = spec_manager.parse_proposal(proposal_dict)

        with pytest.raises(ValueError, match="Invalid insertion_point format"):
            spec_manager._apply_positional_insertion("some content", proposal)

    def test_insertion_point_invalid_position(self, spec_manager):
        """Test error with invalid position (not before/after)."""
        proposal_dict = {
            "change_id": "SPEC-2026-003",
            "proposer": "principal-engineer",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Queue SLA"],
            "proposed_changes": {"Queue SLA": "New content"},
            "rationale": "Add Queue SLA section to improve queue management and monitoring capabilities",
            "insertion_point": "middle:## Section 3",
        }

        proposal = spec_manager.parse_proposal(proposal_dict)

        with pytest.raises(ValueError, match="Invalid position: middle"):
            spec_manager._apply_positional_insertion("some content", proposal)

    def test_insertion_none_insertion_point(self, spec_manager, temp_spec_file):
        """Test that None insertion_point returns content unchanged."""
        proposal_dict = {
            "change_id": "SPEC-2026-003",
            "proposer": "principal-engineer",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Queue SLA"],
            "proposed_changes": {"Queue SLA": "New content"},
            "rationale": "Add Queue SLA section to improve queue management and monitoring capabilities",
            "insertion_point": None,
        }

        proposal = spec_manager.parse_proposal(proposal_dict)

        with open(temp_spec_file, 'r') as f:
            original_content = f.read()

        # Should return content unchanged
        result = spec_manager._apply_positional_insertion(original_content, proposal)
        assert result == original_content
