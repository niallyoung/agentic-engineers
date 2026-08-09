"""Tests for true section-body replacement in the SPEC amendment apply-mechanism.

Bug fixed: the "simple replacement" branch of SpecManager._apply_change used
to INSERT new text directly after a `## {section}` heading while leaving the
entire original section body in place, duplicating content (old and new
contradictory text both present). It also used unbounded str.replace (could
hit occurrences inside fenced code blocks or repeated headings) and silently
no-op'd on a typo'd section name while still reporting success.

These tests cover the fixed `_replace_section_body` helper (used directly)
and the `_apply_change` "simple replacement" branch end-to-end (via
approve_change, which triggers apply on final approval), proving:

1. Replacing a mid-document section replaces the body and does not
   duplicate the old text.
2. The next section and all other sections survive untouched.
3. Replacing the LAST section in the file works (no following heading).
4. A section name that does not exist fails loudly rather than silently
   succeeding.
5. A `## Foo` occurring inside a fenced code block is not treated as a
   heading.
6. Existing positional-insertion behaviour is not regressed.
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from importlib import import_module

spec_management = import_module("src.skills.spec-management.scripts.spec_manager")
SpecManager = spec_management.SpecManager
ChangeProposal = spec_management.ChangeProposal


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for persistence testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def monkeypatch_home(monkeypatch, temp_data_dir):
    """Monkeypatch home directory so SpecManager persistence stays isolated."""
    monkeypatch.setenv("HOME", temp_data_dir)
    return temp_data_dir


@pytest.fixture
def temp_spec_file(temp_data_dir):
    """Create a temporary multi-section SPEC.md file."""
    spec_file = Path(temp_data_dir) / "SPEC.md"
    spec_file.write_text(
        "# SPEC.md Test Document\n"
        "\n"
        "## Section 1\n"
        "Original body for section 1.\n"
        "\n"
        "## Section 2\n"
        "Original body for section 2.\n"
        "More original section 2 content.\n"
        "\n"
        "## Section 3\n"
        "Original body for section 3 (the last section).\n"
    )
    return str(spec_file)


@pytest.fixture
def spec_manager(monkeypatch_home, temp_spec_file):
    """SpecManager wired to the temp SPEC.md file, with isolated persistence."""
    return SpecManager(spec_path=temp_spec_file)


class TestReplaceSectionBodyDirect:
    """Direct unit tests against SpecManager._replace_section_body."""

    def test_mid_document_replacement_does_not_duplicate_old_text(self, spec_manager, temp_spec_file):
        """Replacing a mid-document section replaces the body; old body is gone."""
        original_content = Path(temp_spec_file).read_text()

        result = spec_manager._replace_section_body(
            original_content, "Section 2", "Brand new body for section 2."
        )

        assert "Original body for section 2." not in result
        assert "More original section 2 content." not in result
        assert "Brand new body for section 2." in result
        # Heading itself must be preserved.
        assert "## Section 2" in result

    def test_other_sections_survive_untouched(self, spec_manager, temp_spec_file):
        """Sections before/after the replaced one are byte-for-byte unaffected."""
        original_content = Path(temp_spec_file).read_text()

        result = spec_manager._replace_section_body(
            original_content, "Section 2", "Brand new body for section 2."
        )

        assert "## Section 1" in result
        assert "Original body for section 1." in result
        assert "## Section 3" in result
        assert "Original body for section 3 (the last section)." in result

    def test_replacing_last_section_with_no_following_heading(self, spec_manager, temp_spec_file):
        """Replacing the final section in the file (no next heading) works."""
        original_content = Path(temp_spec_file).read_text()

        result = spec_manager._replace_section_body(
            original_content, "Section 3", "New final section body."
        )

        assert "Original body for section 3 (the last section)." not in result
        assert "New final section body." in result
        assert "## Section 3" in result
        # Preceding sections untouched.
        assert "## Section 1" in result
        assert "## Section 2" in result
        assert "Original body for section 2." in result

    def test_nonexistent_section_raises_value_error(self, spec_manager, temp_spec_file):
        """A typo'd/nonexistent section name fails loudly, not a silent no-op."""
        original_content = Path(temp_spec_file).read_text()

        with pytest.raises(ValueError, match="Section not found"):
            spec_manager._replace_section_body(
                original_content, "Nonexistent Section", "Whatever."
            )

    def test_fenced_fake_heading_not_mistaken_for_real_target(self, spec_manager):
        """A `## Section 2`-looking line inside a fenced code block (within
        Section 1's body) must not be picked as the heading when the real
        `## Section 2` heading appears later, outside any fence."""
        content = (
            "# Doc\n"
            "\n"
            "## Section 1\n"
            "Body of section 1 before fence.\n"
            "\n"
            "```\n"
            "## Section 2\n"
            "fake heading text inside a fenced code block\n"
            "```\n"
            "\n"
            "Body of section 1 after fence.\n"
            "\n"
            "## Section 2\n"
            "Real body of section 2.\n"
        )

        result = spec_manager._replace_section_body(content, "Section 2", "Replaced section 2 body.")

        # Section 1's body, including the fenced block, is untouched.
        assert "Body of section 1 before fence." in result
        assert "fake heading text inside a fenced code block" in result
        assert "Body of section 1 after fence." in result
        # The REAL Section 2 body was replaced.
        assert "Real body of section 2." not in result
        assert "Replaced section 2 body." in result
        assert result.count("## Section 2") == 2  # one fake (in fence) + one real heading

    def test_fenced_fake_heading_does_not_terminate_section_early(self, spec_manager):
        """A fake `## Section 2` heading inside a fenced code block within
        Section 1's own body must not be treated as the end of Section 1 —
        the boundary scan must skip past the fence to the real next heading."""
        content = (
            "# Doc\n"
            "\n"
            "## Section 1\n"
            "Body of section 1 before fence.\n"
            "\n"
            "```\n"
            "## Section 2\n"
            "fake heading text inside a fenced code block\n"
            "```\n"
            "\n"
            "Body of section 1 after fence.\n"
            "\n"
            "## Section 2\n"
            "Real body of section 2.\n"
        )

        result = spec_manager._replace_section_body(content, "Section 1", "Replaced section 1 body.")

        # All of section 1's original body (including the fenced fake
        # heading) is gone, replaced by the new body in full.
        assert "Body of section 1 before fence." not in result
        assert "fake heading text inside a fenced code block" not in result
        assert "Body of section 1 after fence." not in result
        assert "Replaced section 1 body." in result
        # The REAL Section 2 heading and body survive untouched.
        assert "## Section 2" in result
        assert "Real body of section 2." in result

    def test_single_occurrence_only_first_true_heading(self, spec_manager):
        """Only the first true (non-fenced) heading match is replaced."""
        content = (
            "# Doc\n"
            "## Target\n"
            "First body.\n"
            "## Other\n"
            "Other body.\n"
        )
        result = spec_manager._replace_section_body(content, "Target", "Replaced.")
        assert result.count("## Target") == 1
        assert "First body." not in result
        assert "Replaced." in result
        assert "## Other" in result
        assert "Other body." in result


class TestApplyChangeSimpleReplacementEndToEnd:
    """End-to-end tests through approve_change -> _apply_change (no insertion_point)."""

    def _submit_and_approve(self, manager, proposal_dict):
        proposal = manager.parse_proposal(proposal_dict)
        result = manager.submit_proposal(proposal)
        assert result.status == "pending_approval"
        # Approval by principal-engineer triggers final apply.
        return manager.approve_change(
            change_id=proposal.change_id,
            approver="alice",
            approver_role="principal-engineer",
        )

    def test_apply_change_replaces_body_without_duplication(self, spec_manager, temp_spec_file):
        proposal_dict = {
            "change_id": "SPEC-2026-101",
            "proposer": "alice",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Section 2"],
            "proposed_changes": {"Section 2": "Superseding new rules for section 2."},
            "rationale": "Redesign section 2 to correct contradictory guidance found during audit review",
        }

        result = self._submit_and_approve(spec_manager, proposal_dict)

        assert result.status == "approved"

        final_content = Path(temp_spec_file).read_text()
        assert "Original body for section 2." not in final_content
        assert "More original section 2 content." not in final_content
        assert "Superseding new rules for section 2." in final_content
        # Other sections untouched.
        assert "## Section 1" in final_content
        assert "Original body for section 1." in final_content
        assert "## Section 3" in final_content
        assert "Original body for section 3 (the last section)." in final_content

    def test_apply_change_nonexistent_section_fails_loudly(self, spec_manager, temp_spec_file):
        proposal_dict = {
            "change_id": "SPEC-2026-102",
            "proposer": "alice",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["Section Typo"],
            "proposed_changes": {"Section Typo": "This section does not exist."},
            "rationale": "Attempt to amend a section name that was typo'd and does not exist",
        }

        original_content = Path(temp_spec_file).read_text()

        result = self._submit_and_approve(spec_manager, proposal_dict)

        # Must NOT silently report success.
        assert result.status == "rejected"
        assert "Section Typo" in result.reason or "not found" in result.reason.lower()

        # SPEC.md must be left unmodified.
        assert Path(temp_spec_file).read_text() == original_content


class TestPositionalInsertionNotRegressed:
    """Confirm _apply_positional_insertion behaviour is unaffected by the fix."""

    def test_positional_insertion_still_inserts_before_anchor(self, spec_manager, temp_spec_file):
        proposal_dict = {
            "change_id": "SPEC-2026-103",
            "proposer": "alice",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["New Section"],
            "proposed_changes": {"New Section": "## New Section\nBrand new inserted content."},
            "rationale": "Insert a brand new section before Section 3 for structural clarity",
            "insertion_point": "before:## Section 3",
        }
        proposal = spec_manager.parse_proposal(proposal_dict)

        original_content = Path(temp_spec_file).read_text()
        result = spec_manager._apply_positional_insertion(original_content, proposal)

        assert "## New Section" in result
        assert result.index("## New Section") < result.index("## Section 3")
        # Original sections and their bodies remain intact (insertion doesn't
        # replace anything).
        assert "Original body for section 1." in result
        assert "Original body for section 2." in result
        assert "Original body for section 3 (the last section)." in result

    def test_positional_insertion_anchor_not_found_still_raises(self, spec_manager, temp_spec_file):
        proposal_dict = {
            "change_id": "SPEC-2026-104",
            "proposer": "alice",
            "proposer_role": "principal-engineer",
            "timestamp": "2026-06-13T10:00:00Z",
            "affected_sections": ["New Section"],
            "proposed_changes": {"New Section": "content"},
            "rationale": "Insert a brand new section using an anchor that does not exist in doc",
            "insertion_point": "before:## Does Not Exist",
        }
        proposal = spec_manager.parse_proposal(proposal_dict)
        original_content = Path(temp_spec_file).read_text()

        with pytest.raises(ValueError, match="Anchor line not found"):
            spec_manager._apply_positional_insertion(original_content, proposal)
