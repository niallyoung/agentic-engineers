"""
RED phase tests for AGENTS.md location validation.

Per LF standard, canonical documentation location is docs/ not src/docs/.
This test validates that:
1. docs/AGENTS.md exists as the canonical location
2. src/docs/AGENTS.md does not exist (stale copy)
"""

import pytest
from pathlib import Path


class TestAgentsMdLocation:
    """Tests for AGENTS.md canonical location."""

    def test_agents_md_exists_in_canonical_location(self):
        """PASS: docs/AGENTS.md exists as canonical location."""
        canonical_path = Path(__file__).parent.parent / "docs" / "AGENTS.md"
        assert canonical_path.exists(), (
            f"Canonical AGENTS.md not found at {canonical_path}. "
            "Per LF standard, docs/ is canonical location."
        )

    def test_agents_md_does_not_exist_in_stale_location(self):
        """FAIL: src/docs/AGENTS.md should not exist (stale copy)."""
        stale_path = Path(__file__).parent.parent / "src" / "docs" / "AGENTS.md"
        assert not stale_path.exists(), (
            f"Stale AGENTS.md found at {stale_path}. "
            "Per LF standard, only docs/AGENTS.md should be canonical. "
            "Remove stale copy with: git rm src/docs/AGENTS.md"
        )

    def test_canonical_agents_md_has_content(self):
        """PASS: Canonical docs/AGENTS.md contains documentation."""
        canonical_path = Path(__file__).parent.parent / "docs" / "AGENTS.md"
        assert canonical_path.exists(), "Canonical AGENTS.md not found"
        content = canonical_path.read_text()
        assert len(content) > 100, "AGENTS.md should contain meaningful documentation"
        assert "agent" in content.lower(), "AGENTS.md should document agents"
