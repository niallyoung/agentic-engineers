"""
CHANGELOG.md management: maintains [Unreleased] section.

Maintains consistent [Unreleased] section with:
- Next projected version
- Commits grouped by type (feat, fix, docs, etc.)
- Proper markdown formatting
"""

import re
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from datetime import datetime
from collections import defaultdict

try:
    from .version_calculator import parse_commit_type
except ImportError:
    from version_calculator import parse_commit_type


def get_repo_root() -> str:
    """Get repository root directory."""
    return str(Path(__file__).parent.parent.parent)


def read_changelog(changelog_path: Optional[Path] = None) -> str:
    """
    Read CHANGELOG.md content.
    
    Args:
        changelog_path: Path to CHANGELOG.md (if None, uses repo default)
    
    Returns:
        CHANGELOG content as string
    """
    if changelog_path is None:
        changelog_path = Path(get_repo_root()) / "CHANGELOG.md"
    
    if not changelog_path.exists():
        return ""
    
    return changelog_path.read_text()


def write_changelog(content: str, changelog_path: Optional[Path] = None) -> None:
    """
    Write CHANGELOG.md content.
    
    Args:
        content: New CHANGELOG content
        changelog_path: Path to CHANGELOG.md (if None, uses repo default)
    """
    if changelog_path is None:
        changelog_path = Path(get_repo_root()) / "CHANGELOG.md"
    
    changelog_path.write_text(content)


def group_commits_by_type(commits: List[Tuple[str, str, str]]) -> Dict[str, List[str]]:
    """
    Group commits by semantic type.
    
    Args:
        commits: List of (hash, date, message) tuples
    
    Returns:
        Dict mapping type -> list of descriptions
    """
    groups = defaultdict(list)
    
    for commit_hash, author_date, message in commits:
        commit_type, is_breaking = parse_commit_type(message)
        
        # Extract description (remove type: prefix)
        description = message
        if ":" in message:
            parts = message.split(":", 1)
            if len(parts) > 1:
                # Remove type(scope): part
                description = parts[1].strip()
        
        # Clean up description
        description = description.strip()
        if description:
            groups[commit_type].append(description)
    
    return groups


def type_to_section(commit_type: str) -> str:
    """Map commit type to CHANGELOG section name."""
    mapping = {
        "feat": "Added",
        "fix": "Fixed",
        "refactor": "Changed",
        "chore": "Changed",
        "docs": "Documentation",
        "style": "Changed",
        "test": "Testing",
        "perf": "Performance",
        "other": "Miscellaneous"
    }
    return mapping.get(commit_type, "Miscellaneous")


def generate_unreleased_section(
    next_version: str,
    commits: List[Tuple[str, str, str]]
) -> str:
    """
    Generate [Unreleased] section for CHANGELOG.
    
    Args:
        next_version: Next projected version (e.g., "0.9.0")
        commits: List of (hash, date, message) tuples
    
    Returns:
        Formatted [Unreleased] section as markdown string
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Header
    lines = [
        f"## [Unreleased] - v{next_version}",
        ""
    ]
    
    if not commits:
        # No commits: indicate no unreleased changes
        lines.extend([
            "No unreleased changes.",
            "",
        ])
        return "\n".join(lines)
    
    # Group commits by type
    groups = group_commits_by_type(commits)
    
    # Map sections to entries
    sections = defaultdict(list)
    for commit_type, messages in groups.items():
        section_name = type_to_section(commit_type)
        sections[section_name].extend(messages)
    
    # Order sections logically
    section_order = [
        "Added",
        "Fixed",
        "Changed",
        "Performance",
        "Testing",
        "Documentation",
        "Miscellaneous"
    ]
    
    # Generate sections
    has_content = False
    for section_name in section_order:
        if section_name in sections and sections[section_name]:
            has_content = True
            lines.append(f"### {section_name}")
            
            # Remove duplicates and sort
            unique_messages = sorted(set(sections[section_name]))
            for msg in unique_messages:
                lines.append(f"- {msg}")
            
            lines.append("")
    
    if not has_content:
        lines.append("No notable changes.")
        lines.append("")
    
    return "\n".join(lines)


def insert_unreleased_section(
    changelog_content: str,
    unreleased_section: str
) -> str:
    """
    Insert [Unreleased] section into CHANGELOG.
    
    Replaces existing [Unreleased] section if present, or inserts after header.
    
    Args:
        changelog_content: Current CHANGELOG.md content
        unreleased_section: New [Unreleased] section to insert
    
    Returns:
        Updated CHANGELOG content
    """
    if not changelog_content:
        # Empty changelog: create from scratch
        return f"# Changelog\n\n{unreleased_section}\n"
    
    lines = changelog_content.split("\n")
    
    # Find header
    header_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("# Changelog"):
            header_idx = i
            break
    
    if header_idx == -1:
        # No header: prepend
        return f"# Changelog\n\n{unreleased_section}\n{changelog_content}"
    
    # Find existing [Unreleased] section (if any)
    unreleased_start = -1
    unreleased_end = -1
    
    for i in range(header_idx + 1, len(lines)):
        if lines[i].startswith("## [Unreleased]"):
            unreleased_start = i
        elif unreleased_start >= 0 and lines[i].startswith("## "):
            # Found next version section
            unreleased_end = i
            break
    
    # If [Unreleased] exists, replace it; otherwise insert after header
    if unreleased_start >= 0 and unreleased_end >= 0:
        # Replace existing [Unreleased]
        new_lines = (
            lines[:unreleased_start] +
            unreleased_section.split("\n") +
            lines[unreleased_end:]
        )
    elif unreleased_start >= 0:
        # [Unreleased] at end: replace
        new_lines = (
            lines[:unreleased_start] +
            unreleased_section.split("\n")
        )
    else:
        # No [Unreleased]: insert after header
        # Find position after header + blank lines
        insert_pos = header_idx + 1
        while insert_pos < len(lines) and lines[insert_pos].strip() == "":
            insert_pos += 1
        
        new_lines = (
            lines[:insert_pos] +
            [""] +
            unreleased_section.split("\n") +
            lines[insert_pos:]
        )
    
    return "\n".join(new_lines)


def update_changelog_unreleased(
    changelog_path: Optional[Path] = None,
    next_version: Optional[str] = None,
    commits: Optional[List[Tuple[str, str, str]]] = None
) -> None:
    """
    Update CHANGELOG.md [Unreleased] section.
    
    Args:
        changelog_path: Path to CHANGELOG.md (if None, uses repo default)
        next_version: Next version to use (if None, calculates from commits)
        commits: List of (hash, date, message) tuples (if None, gets from git)
    """
    if changelog_path is None:
        changelog_path = Path(get_repo_root()) / "CHANGELOG.md"
    
    if commits is None:
        # Import here to avoid circular imports
        try:
            from .version_calculator import get_commits_since_tag
        except ImportError:
            from version_calculator import get_commits_since_tag
        commits = get_commits_since_tag()
    
    if next_version is None:
        # Import here to avoid circular imports
        try:
            from .version_calculator import get_current_version, calculate_next_version
        except ImportError:
            from version_calculator import get_current_version, calculate_next_version
        current = get_current_version()
        next_version = calculate_next_version(current, commits)
    
    # Generate new [Unreleased] section
    unreleased_section = generate_unreleased_section(next_version, commits)
    
    # Read current CHANGELOG
    current_content = read_changelog(changelog_path)
    
    # Insert [Unreleased] section
    updated_content = insert_unreleased_section(current_content, unreleased_section)
    
    # Write back
    write_changelog(updated_content, changelog_path)


if __name__ == "__main__":
    # Usage example
    from .version_calculator import get_commits_since_tag, get_current_version, calculate_next_version
    
    commits = get_commits_since_tag()
    current = get_current_version()
    next_v = calculate_next_version(current, commits)
    
    print(f"Current version: {current}")
    print(f"Next version: {next_v}")
    print(f"Unreleased commits: {len(commits)}")
    print()
    print("Unreleased section:")
    print("=" * 70)
    print(generate_unreleased_section(next_v, commits))
