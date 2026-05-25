#!/usr/bin/env python3
"""
CLI wrapper for version-manager skill (DEPRECATED/DISABLED).

STATUS: This script is DISABLED in favor of CI/CD-driven versioning.
CHANGELOG now uses direct versioned entries only, not unreleased sections.

Git tags are the source of truth, created automatically by CI/CD.

Historical usage (no longer recommended):
    python3 update-changelog.py --dry-run    # Show next version (read-only)
    
Note: Update functionality is disabled. Use for version calculation only if needed.
"""

import sys
import argparse
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from version_calculator import (
        get_commits_since_tag,
        get_current_version,
        calculate_next_version,
    )
    from changelog_updater import (
        read_changelog,
        write_changelog,
        generate_unreleased_section,
    )
except ImportError:
    # Try absolute imports as fallback
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from skills.version_manager.version_calculator import (
        get_commits_since_tag,
        get_current_version,
        calculate_next_version,
    )
    from skills.version_manager.changelog_updater import (
        read_changelog,
        write_changelog,
        generate_unreleased_section,
    )


def get_repo_root() -> Path:
    """Get repository root directory."""
    return Path(__file__).parent.parent.parent.parent


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="[DEPRECATED] Calculate next version (CHANGELOG updates disabled)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without writing"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force update even if CHANGELOG is current"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatic mode (used by git hook, non-blocking)"
    )
    
    args = parser.parse_args()
    
    try:
        repo_root = get_repo_root()
        changelog_path = repo_root / "CHANGELOG.md"
        
        if args.verbose:
            print(f"📁 Repository: {repo_root}")
            print(f"📄 CHANGELOG: {changelog_path}")
        
        # Get current state
        current_version = get_current_version()
        commits = get_commits_since_tag()
        
        if args.verbose:
            print(f"📌 Current version: {current_version}")
            print(f"📊 Unreleased commits: {len(commits)}")
        
        # Calculate next version
        next_version = calculate_next_version(current_version, commits)
        
        if args.verbose:
            print(f"🔢 Next version: {next_version}")
        
        # Generate unreleased section
        unreleased_section = generate_unreleased_section(next_version, commits)
        
        # Read current CHANGELOG
        current_content = read_changelog(changelog_path)
        
        # Check if already up-to-date
        if "[Unreleased] - v" + next_version in current_content and not args.force:
            if args.verbose:
                print("✅ CHANGELOG already has [Unreleased] section with correct version")
            return 0
        
        # Prepare new content (simple insertion for now)
        from changelog_updater import insert_unreleased_section
        new_content = insert_unreleased_section(current_content, unreleased_section)
        
        if args.dry_run:
            print("=" * 70)
            print("PROPOSED CHANGELOG UPDATE:")
            print("=" * 70)
            print(new_content[:1000])
            print("...")
            return 0
        
        # Write updated CHANGELOG
        write_changelog(new_content, changelog_path)
        
        if args.verbose or not args.auto:
            print(f"✅ Updated {changelog_path}")
            print(f"📌 Version: {next_version}")
            print(f"📊 Unreleased commits: {len(commits)}")
        
        return 0
    
    except Exception as e:
        if args.verbose:
            print(f"❌ Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        
        # In auto mode, don't fail (it's a git hook)
        if args.auto:
            return 0
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
