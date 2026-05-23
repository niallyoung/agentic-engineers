"""
version-manager skill: semantic versioning workflow.

Provides:
- Semantic version calculation from commits
- CHANGELOG [Unreleased] section management
- Git hook integration
"""

from .version_calculator import (
    get_commits_since_tag,
    parse_commit_type,
    determine_version_bump,
    calculate_next_version,
    calculate_next_version_from_commits,
    get_current_version,
)

from .changelog_updater import (
    read_changelog,
    write_changelog,
    generate_unreleased_section,
    update_changelog_unreleased,
)

__all__ = [
    "get_commits_since_tag",
    "parse_commit_type",
    "determine_version_bump",
    "calculate_next_version",
    "calculate_next_version_from_commits",
    "get_current_version",
    "read_changelog",
    "write_changelog",
    "generate_unreleased_section",
    "update_changelog_unreleased",
]
