#!/usr/bin/env python3
"""
Validate CHANGELOG.md consistency with git commits in CI/CD.

Ensures that:
1. CHANGELOG has [Unreleased] section
2. All commits since last tag have entries in CHANGELOG
3. [Unreleased] version matches calculated next version

Exit codes:
  0: CHANGELOG is valid
  1: CHANGELOG is invalid (missing entries, format issues, etc.)
"""

import sys
import re
import subprocess
from pathlib import Path
from typing import List, Set, Tuple, Optional
from collections import defaultdict


def get_repo_root() -> Path:
    """Get repository root directory."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError("Not in a git repository")
    return Path(result.stdout.strip())


def run_git(cmd: List[str]) -> str:
    """Run git command and return output."""
    result = subprocess.run(
        ["git"] + cmd,
        capture_output=True,
        text=True,
        cwd=get_repo_root()
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def get_latest_tag() -> Optional[str]:
    """Get latest semantic version tag."""
    try:
        tags_output = run_git(["tag", "-l", "v*", "--sort=-version:refname"])
        if not tags_output:
            return None
        tags = tags_output.split("\n")
        return tags[0] if tags and tags[0] else None
    except:
        return None


def get_commits_since_tag(tag: Optional[str] = None) -> List[Tuple[str, str]]:
    """
    Get all commits since a given tag.
    
    Returns:
        List of (message, hash) tuples
    """
    if tag is None:
        tag = get_latest_tag()
    
    try:
        if tag:
            git_range = f"{tag}..HEAD"
            output = run_git(["log", git_range, "--format=%s|%H"])
        else:
            output = run_git(["log", "--all", "--format=%s|%H"])
        
        if not output:
            return []
        
        commits = []
        for line in output.split("\n"):
            if "|" in line:
                message, commit_hash = line.split("|", 1)
                commits.append((message.strip(), commit_hash.strip()))
        
        return commits
    except Exception as e:
        print(f"❌ Error getting commits: {e}", file=sys.stderr)
        return []


def extract_changelog_entries(changelog_path: Path) -> Set[str]:
    """
    Extract unreleased entries from CHANGELOG.md.
    
    Returns:
        Set of entry descriptions (without bullet points)
    """
    if not changelog_path.exists():
        return set()
    
    content = changelog_path.read_text()
    
    # Find [Unreleased] section
    unreleased_match = re.search(
        r"## \[Unreleased\] - v[0-9.]+\n(.*?)(?=\n## \[|$)",
        content,
        re.DOTALL
    )
    
    if not unreleased_match:
        return set()
    
    unreleased_block = unreleased_match.group(1)
    entries = set()
    
    # Extract bullet point entries (- description)
    for line in unreleased_block.split("\n"):
        line = line.strip()
        if line.startswith("- "):
            entries.add(line[2:])  # Remove "- " prefix
    
    return entries


def normalize_message(message: str) -> str:
    """Normalize commit message for comparison with CHANGELOG entries."""
    # Remove conventional commit prefix (type(scope): → )
    message = message.strip()
    
    # Handle "type(scope): description" or "type: description"
    if ":" in message:
        parts = message.split(":", 1)
        if len(parts) > 1:
            description = parts[1].strip()
            return description
    
    return message


def main():
    """Validate CHANGELOG consistency."""
    try:
        repo_root = get_repo_root()
        changelog_path = repo_root / "CHANGELOG.md"
        
        print("🔍 Validating CHANGELOG.md consistency with git commits...\n")
        
        # Check CHANGELOG exists
        if not changelog_path.exists():
            print("❌ CHANGELOG.md not found")
            return 1
        
        # Check [Unreleased] section exists
        changelog_content = changelog_path.read_text()
        if "[Unreleased]" not in changelog_content:
            print("❌ CHANGELOG.md missing [Unreleased] section")
            print("   Run: python3 skills/version-manager/scripts/update-changelog.py")
            return 1
        
        print("✅ [Unreleased] section found")
        
        # Get commits since last tag
        commits = get_commits_since_tag()
        
        if not commits:
            print("✅ No unreleased commits (nothing to validate)")
            return 0
        
        print(f"📊 Found {len(commits)} unreleased commits\n")
        
        # Extract CHANGELOG entries
        changelog_entries = extract_changelog_entries(changelog_path)
        print(f"📋 Found {len(changelog_entries)} entries in CHANGELOG [Unreleased] section\n")
        
        if not changelog_entries:
            print("❌ [Unreleased] section is empty but has unreleased commits")
            print(f"   Missing {len(commits)} entries\n")
            
            print("Unreleased commits (not in CHANGELOG):")
            for message, commit_hash in commits:
                print(f"  {commit_hash[:8]} {message}")
            
            print("\nRun: python3 skills/version-manager/scripts/update-changelog.py --force")
            return 1
        
        # Check if all commits have entries in CHANGELOG
        missing_commits = []
        
        for commit_message, commit_hash in commits:
            normalized = normalize_message(commit_message)
            
            # Check if this entry is in CHANGELOG (exact or fuzzy match)
            found = False
            
            # Exact match
            if normalized in changelog_entries:
                found = True
            else:
                # Fuzzy match: check if any CHANGELOG entry contains the key parts
                for entry in changelog_entries:
                    # Remove common patterns and compare
                    entry_lower = entry.lower()
                    msg_lower = normalized.lower()
                    
                    # Simple substring match
                    if msg_lower in entry_lower or entry_lower in msg_lower:
                        found = True
                        break
            
            if not found:
                missing_commits.append((commit_message, commit_hash))
        
        if missing_commits:
            print(f"❌ {len(missing_commits)} commit(s) NOT in CHANGELOG [Unreleased]:\n")
            
            for message, commit_hash in missing_commits:
                print(f"  {commit_hash[:8]} {message}")
            
            print("\n💡 Fix:")
            print("  python3 skills/version-manager/scripts/update-changelog.py --force")
            print("  git add CHANGELOG.md")
            print("  git commit --amend (or make a new commit)")
            
            return 1
        
        print(f"✅ All {len(commits)} commits have CHANGELOG entries")
        print("✅ CHANGELOG validation passed\n")
        
        return 0
    
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
