"""
changelog_generator.py — Auto-updates SPEC.md CHANGELOG section.

Responsibilities:
- Maintain CHANGELOG section in SPEC.md
- Add entries on change approval
- Format entries with change_id, author, timestamp, approval chain
- Ensure reverse chronological order (newest first)

Author: Principal Engineer
"""

from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path


class ChangelogGenerator:
    """Auto-updates SPEC.md CHANGELOG section."""
    
    CHANGELOG_SECTION_MARKER = "## CHANGELOG"
    
    def __init__(self, spec_path: str = "docs/SPEC.md"):
        self.spec_path = Path(spec_path)
    
    def add_entry(self, change_id: str, title: str, author: str, 
                  timestamp: str, approval_chain: Optional[List[str]] = None) -> str:
        """Add entry to CHANGELOG and return updated SPEC.md content.
        
        Args:
            change_id: Change ID (e.g., "SPEC-2024-001")
            title: Change title (usually from rationale)
            author: Proposer name
            timestamp: ISO-8601 timestamp
            approval_chain: Optional list of approver names
            
        Returns:
            Updated SPEC.md content
        """
        if not self.spec_path.exists():
            # If SPEC.md doesn't exist yet, create minimal structure
            spec_content = self._create_minimal_spec()
        else:
            spec_content = self.spec_path.read_text()
        
        # Format the new entry
        entry = self._format_entry(change_id, title, author, timestamp, approval_chain)
        
        # Find CHANGELOG section
        if self.CHANGELOG_SECTION_MARKER not in spec_content:
            # Add CHANGELOG section if it doesn't exist
            spec_content += f"\n\n{self.CHANGELOG_SECTION_MARKER}\n\n"
        
        # Insert entry at top of CHANGELOG (after section marker)
        marker_pos = spec_content.find(self.CHANGELOG_SECTION_MARKER)
        if marker_pos != -1:
            # Find position after the marker and any blank lines
            insert_pos = marker_pos + len(self.CHANGELOG_SECTION_MARKER)
            # Skip to end of line
            insert_pos = spec_content.find('\n', insert_pos)
            if insert_pos != -1:
                insert_pos += 1
            else:
                insert_pos = len(spec_content)
            
            # Insert entry
            spec_content = spec_content[:insert_pos] + entry + "\n" + spec_content[insert_pos:]
        
        return spec_content
    
    def read_changelog(self) -> List[Dict]:
        """Read existing CHANGELOG entries.
        
        Returns:
            List of changelog entries as dicts
        """
        if not self.spec_path.exists():
            return []
        
        spec_content = self.spec_path.read_text()
        
        if self.CHANGELOG_SECTION_MARKER not in spec_content:
            return []
        
        # Extract CHANGELOG section
        marker_pos = spec_content.find(self.CHANGELOG_SECTION_MARKER)
        changelog_start = marker_pos + len(self.CHANGELOG_SECTION_MARKER)
        
        # Find next section or end of file
        next_section_pos = spec_content.find("\n## ", changelog_start + 1)
        if next_section_pos == -1:
            changelog_text = spec_content[changelog_start:]
        else:
            changelog_text = spec_content[changelog_start:next_section_pos]
        
        # Parse entries (very simple parsing)
        entries = []
        lines = changelog_text.strip().split('\n')
        
        for line in lines:
            if line.startswith("### [SPEC-"):
                # Parse entry header
                # Format: ### [SPEC-2024-001] — 2024-05-09 — author
                parts = line.replace("###", "").replace("[", "").replace("]", "").split(" — ")
                if len(parts) >= 3:
                    entries.append({
                        "change_id": parts[0].strip(),
                        "timestamp": parts[1].strip(),
                        "author": parts[2].strip()
                    })
        
        return entries
    
    def read_spec(self) -> str:
        """Read current SPEC.md."""
        if not self.spec_path.exists():
            return ""
        return self.spec_path.read_text()
    
    def format_entry(self, change_id: str, title: str, author: str, 
                     timestamp: str, approval_chain: Optional[List[str]] = None) -> str:
        """Format a changelog entry (public method for testing).
        
        Format:
        ### [SPEC-2024-001] — 2024-05-09 — alice (principal-engineer)
        Change title here.
        Approved by: bob, charlie
        """
        return self._format_entry(change_id, title, author, timestamp, approval_chain)
    
    def _format_entry(self, change_id: str, title: str, author: str, 
                      timestamp: str, approval_chain: Optional[List[str]] = None) -> str:
        """Format a changelog entry.
        
        Format:
        ### [SPEC-2024-001] — 2024-05-09 — alice (principal-engineer)
        Change title here.
        Approved by: bob, charlie
        """
        # Extract date from timestamp (format: 2024-05-09)
        date_part = timestamp[:10] if timestamp else "unknown-date"
        
        # Format header
        header = f"### [{change_id}] — {date_part} — {author}"
        
        # Format body
        lines = [header, title]
        
        if approval_chain:
            approvers_text = ", ".join(approval_chain)
            lines.append(f"Approved by: {approvers_text}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _create_minimal_spec() -> str:
        """Create minimal SPEC.md structure."""
        return """---
name: Agentic Engineers Implementation Specification
description: Current state of the agent orchestration system
version: 1.0
updated: 2024-05-09
---

# Agentic Engineers Implementation Specification

## CHANGELOG
"""
