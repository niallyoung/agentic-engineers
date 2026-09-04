#!/usr/bin/env python3
"""
Semantic versioning utility for agentic-engineers.

Reads git tags and manages version information.
Usage:
  get_version.py            — Get current version from git tags
  get_version.py next-patch — Get next patch version
  get_version.py next-minor — Get next minor version
  get_version.py next-major — Get next major version

Version Source Priority:
  1. Git tags (primary source of truth)
  2. FALLBACK_VERSION (for offline/no-git scenarios)
"""

import sys
import subprocess
from pathlib import Path

# Single source of truth for the offline/no-git fallback version.
# setup.py imports this rather than duplicating the literal.
FALLBACK_VERSION = "0.8.0"


def get_repo_root():
    """Get repository root directory for git operations."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass

    # Fallback: assume script is in repo_root/scripts/
    script_dir = Path(__file__).parent
    return str(script_dir.parent)


def run_git(cmd):
    """Run git command and return output."""
    repo_root = get_repo_root()
    result = subprocess.run(
        ["git"] + cmd,
        capture_output=True,
        text=True,
        cwd=repo_root
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def get_latest_tag():
    """Get latest semantic version tag."""
    try:
        tags = run_git(["tag", "-l", "v*", "--sort=-version:refname"]).split("\n")
        if tags and tags[0]:
            return tags[0]
    except (OSError, subprocess.SubprocessError, RuntimeError):
        pass
    return None


def get_current_version():
    """Get current version from git tags (primary) or hardcoded fallback.

    Priority:
      1. Latest git tag (primary, always authoritative)
      2. FALLBACK_VERSION (for offline/no-git scenarios)
    """
    # Primary source: git tags (always accurate, no sync issues)
    try:
        tag = get_latest_tag()
        if tag:
            return tag.lstrip("v")
    except (OSError, subprocess.SubprocessError, RuntimeError):
        pass

    # Last resort: hardcoded default (first release version)
    return FALLBACK_VERSION


def _parse_version(text):
    """Parse a dotted version string into a (major, minor, patch) int tuple.

    Trailing pre-release/build suffixes on the patch component (e.g. "1.2.3-rc1")
    are dropped. Missing components default to 0, so "1.2" parses as (1, 2, 0).
    """
    parts = text.strip().split(".")
    numbers = []
    for part in parts[:3]:
        digits = ""
        for char in part:
            if not char.isdigit():
                break
            digits += char
        numbers.append(int(digits) if digits else 0)
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)


def get_next_version(bump_type="patch"):
    """Get next version."""
    current = get_current_version()
    major, minor, patch = _parse_version(current)

    if bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "major":
        return f"{major + 1}.0.0"
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "next-patch":
            print(get_next_version("patch"))
        elif cmd == "next-minor":
            print(get_next_version("minor"))
        elif cmd == "next-major":
            print(get_next_version("major"))
        else:
            print(f"Unknown command: {cmd}", file=sys.stderr)
            sys.exit(1)
    else:
        print(get_current_version())
