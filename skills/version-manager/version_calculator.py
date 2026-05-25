"""
Semantic version calculation from git commits.

Parses conventional commits and calculates semantic version bumps:
- feat: → minor bump
- fix: → patch bump
- BREAKING CHANGE: → major bump
"""

import subprocess
import re
from pathlib import Path
from typing import List, Tuple, Optional
from packaging import version as pkg_version


def get_repo_root() -> str:
    """Get repository root directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    # Fallback: assume this is in repo/skills/version_manager/
    return str(Path(__file__).parent.parent.parent)


def run_git(cmd: List[str], cwd: Optional[str] = None) -> str:
    """Run git command and return output."""
    if cwd is None:
        cwd = get_repo_root()
    
    result = subprocess.run(
        ["git"] + cmd,
        capture_output=True,
        text=True,
        cwd=cwd
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{result.stderr}")
    
    return result.stdout.strip()


def get_latest_tag(fetch_remote: bool = False) -> Optional[str]:
    """
    Get latest semantic version tag.
    
    Args:
        fetch_remote: If True, fetch tags from remote before reading. Useful when
                     CI creates remote tags that haven't been pulled locally yet.
    
    Returns:
        Latest semantic version tag (e.g., 'v0.9.1') or None if no tags exist.
    """
    try:
        if fetch_remote:
            # Sync remote CI-created tags before reading
            run_git(["fetch", "--tags", "--quiet"])
        
        tags_output = run_git(["tag", "-l", "v*", "--sort=-version:refname"])
        if not tags_output:
            return None
        
        tags = tags_output.split("\n")
        if tags and tags[0]:
            return tags[0]
    except:
        pass
    
    return None


def get_commits_since_tag(tag: Optional[str] = None) -> List[Tuple[str, str, str]]:
    """
    Get all commits since a given tag.
    
    Args:
        tag: Git tag to use as reference. If None, uses latest tag.
    
    Returns:
        List of (commit_hash, author_date, commit_message) tuples
        Newest commits first.
    """
    if tag is None:
        tag = get_latest_tag()
    
    try:
        if tag:
            # Get commits since tag (newest first)
            git_range = f"{tag}..HEAD"
            output = run_git(["log", git_range, "--format=%H%n%ai%n%s%n---"])
        else:
            # No tag: get all commits (newest first)
            output = run_git(["log", "--all", "--format=%H%n%ai%n%s%n---"])
        
        if not output:
            return []
        
        commits = []
        entries = output.split("---\n")
        
        for entry in entries:
            lines = entry.strip().split("\n")
            if len(lines) >= 3:
                commit_hash = lines[0].strip()
                author_date = lines[1].strip().split()[0]  # Extract just the date
                message = lines[2].strip()
                
                if commit_hash and author_date and message:
                    commits.append((commit_hash, author_date, message))
        
        return commits
    
    except Exception as e:
        print(f"Warning: Could not get commits: {e}")
        return []


def parse_commit_type(message: str) -> Tuple[str, bool]:
    """
    Parse semantic type from commit message.
    
    Supports conventional commits format:
    - feat: new feature
    - fix: bug fix
    - feat!: breaking feature
    - fix(scope): scoped fix
    - BREAKING CHANGE: keyword
    
    Args:
        message: Commit message to parse
    
    Returns:
        (type, is_breaking)
        type: "feat", "fix", "refactor", "chore", "docs", "style", "test", "perf", or "other"
        is_breaking: True if BREAKING CHANGE or ! suffix
    """
    message = message.strip()
    if not message:
        return ("other", False)
    
    # Check for breaking change marker (!: or BREAKING CHANGE:)
    is_breaking = "BREAKING CHANGE" in message or "!" in message.split(":")[0]
    
    # Parse type from conventional commit format
    parts = message.split(":", 1)
    if len(parts) >= 2:
        prefix = parts[0].strip().lower()
        
        # Extract type, removing scope (type(scope) → type)
        type_part = prefix.split("(")[0].strip()
        # Remove ! for breaking changes
        type_part = type_part.rstrip("!")
        
        valid_types = ["feat", "fix", "refactor", "chore", "docs", "style", "test", "perf"]
        
        if type_part in valid_types:
            return (type_part, is_breaking)
    
    return ("other", False)


def determine_version_bump(commits: List[Tuple[str, str, str]]) -> str:
    """
    Determine semantic version bump type based on commits.
    
    Returns:
        "major", "minor", "patch", or "none"
    
    Logic:
        - If any BREAKING CHANGE: major
        - Else if any feat: minor
        - Else if any fix: patch
        - Else: none
    """
    has_breaking = False
    has_feature = False
    has_fix = False
    
    for commit_hash, author_date, message in commits:
        commit_type, is_breaking = parse_commit_type(message)
        
        if is_breaking:
            has_breaking = True
        
        if commit_type == "feat":
            has_feature = True
        elif commit_type == "fix":
            has_fix = True
    
    if has_breaking:
        return "major"
    elif has_feature:
        return "minor"
    elif has_fix:
        return "patch"
    else:
        return "none"


def get_current_version() -> str:
    """
    Get current version from git tags or fallback.
    
    This calls scripts/get_version.py for consistency.
    
    Returns:
        Version string (e.g., "0.8.1")
    """
    try:
        repo_root = get_repo_root()
        result = subprocess.run(
            ["python3", "scripts/get_version.py"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    # Fallback
    return "0.8.0"


def calculate_next_version(current_version: str, commits: List[Tuple[str, str, str]]) -> str:
    """
    Calculate next semantic version based on commits.
    
    Args:
        current_version: Current version (e.g., "0.8.0")
        commits: List of (hash, date, message) tuples since last tag
    
    Returns:
        Next version (e.g., "0.9.0" for minor bump)
    """
    if not commits:
        return current_version
    
    bump_type = determine_version_bump(commits)
    
    if bump_type == "none":
        return current_version
    
    try:
        v = pkg_version.parse(current_version)
        
        if bump_type == "major":
            return f"{v.major + 1}.0.0"
        elif bump_type == "minor":
            return f"{v.major}.{v.minor + 1}.0"
        elif bump_type == "patch":
            return f"{v.major}.{v.minor}.{v.micro + 1}"
    except:
        pass
    
    return current_version


def calculate_next_version_from_commits(tag: Optional[str] = None, current_version: Optional[str] = None) -> str:
    """
    High-level function: get commits since tag and calculate next version.
    
    Args:
        tag: Git tag reference (if None, uses latest tag)
        current_version: Current version (if None, derives from tag)
    
    Returns:
        Next semantic version
    """
    commits = get_commits_since_tag(tag)
    
    if current_version is None:
        current_version = get_current_version()
    
    return calculate_next_version(current_version, commits)


if __name__ == "__main__":
    # Usage example
    commits = get_commits_since_tag()
    current = get_current_version()
    next_v = calculate_next_version(current, commits)
    print(f"Current: {current}")
    print(f"Commits since tag: {len(commits)}")
    print(f"Next version: {next_v}")
