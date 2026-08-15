"""
Pointer-doc contract validation for AGENTS.md.

SPEC-2026-005 established a new contract: docs/AGENTS.md is a short pointer document
(status: Pointer) that references src/AGENTS.md as the canonical roster. This test
validates that:
1. docs/AGENTS.md exists and is a pointer stub (short, explicit pointer)
2. src/AGENTS.md exists as the canonical source
3. The pointer actually points to src/AGENTS.md
4. src/docs/AGENTS.md does not exist (stale copy)
"""

import pytest
from pathlib import Path


class TestAgentsMdLocation:
    """Tests for AGENTS.md pointer-doc contract."""

    def test_agents_md_pointer_exists_in_docs(self):
        """PASS: docs/AGENTS.md exists as a pointer document."""
        pointer_path = Path(__file__).parent.parent / "docs" / "AGENTS.md"
        assert pointer_path.exists(), (
            f"Pointer AGENTS.md not found at {pointer_path}. "
            "docs/AGENTS.md should be a short pointer to src/AGENTS.md."
        )

    def test_canonical_agents_md_exists_in_src(self):
        """PASS: src/AGENTS.md exists as canonical source."""
        canonical_path = Path(__file__).parent.parent / "src" / "AGENTS.md"
        assert canonical_path.exists(), (
            f"Canonical AGENTS.md not found at {canonical_path}. "
            "src/AGENTS.md is the canonical roster and routing source."
        )

    def test_agents_md_does_not_exist_in_stale_location(self):
        """FAIL: src/docs/AGENTS.md should not exist (stale copy)."""
        stale_path = Path(__file__).parent.parent / "src" / "docs" / "AGENTS.md"
        assert not stale_path.exists(), (
            f"Stale AGENTS.md found at {stale_path}. "
            "Remove this stale copy with: git rm src/docs/AGENTS.md"
        )

    def test_pointer_document_references_canonical_source(self):
        """PASS: docs/AGENTS.md pointer actually points to src/AGENTS.md."""
        pointer_path = Path(__file__).parent.parent / "docs" / "AGENTS.md"
        assert pointer_path.exists(), "Pointer AGENTS.md not found"
        content = pointer_path.read_text()

        # The pointer should explicitly mention src/AGENTS.md
        assert "src/AGENTS.md" in content, (
            "Pointer docs/AGENTS.md should reference src/AGENTS.md as canonical source"
        )

        # Pointer should be brief (status: Pointer indicates it's a stub)
        assert len(content) < 1000, (
            f"docs/AGENTS.md pointer is too long ({len(content)} chars); "
            "pointer stubs should be brief, not long documentation"
        )
