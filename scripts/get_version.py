#!/usr/bin/env python3
"""
Semantic versioning utility for agentic-engineers.

Reads git tags and manages version information.
Usage:
  get_version.py            — Get current version from git tags
  get_version.py next-patch — Get next patch version
  get_version.py next-minor — Get next minor version
"""

import sys
import subprocess
from packaging import version as pkg_version

def run_git(cmd):
    """Run git command and return output."""
    result = subprocess.run(
        ["git"] + cmd,
        capture_output=True,
        text=True,
        cwd="/Users/niall/git/agentic-engineers"
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
    except:
        pass
    return None

def get_current_version():
    """Get current version from VERSION file or git tags."""
    try:
        with open("/Users/niall/git/agentic-engineers/VERSION") as f:
            return f.read().strip()
    except:
        tag = get_latest_tag()
        if tag:
            return tag.lstrip("v")
        return "0.8.0"

def get_next_version(bump_type="patch"):
    """Get next version."""
    current = get_current_version()
    v = pkg_version.parse(current)
    
    if bump_type == "patch":
        return f"{v.major}.{v.minor}.{v.micro + 1}"
    elif bump_type == "minor":
        return f"{v.major}.{v.minor + 1}.0"
    elif bump_type == "major":
        return f"{v.major + 1}.0.0"
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
