#!/usr/bin/env python3
"""
Validate SPEC architectural constraints across the codebase.

This script enforces rules defined in docs/SPEC.md by scanning source code for
violations. Constraints are defined declaratively, making it easy to add new
rules without modifying this script.

Usage:
  python3 scripts/validate-spec-constraints.py                    # Check all constraints
  python3 scripts/validate-spec-constraints.py --constraint NAME  # Check specific constraint
  python3 scripts/validate-spec-constraints.py --fix              # (future) Auto-fix violations
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass


@dataclass
class Constraint:
    """Defines a SPEC architectural constraint to validate."""
    name: str
    description: str
    spec_section: str  # e.g., "Queue Architecture & Paths"
    forbidden_patterns: List[str]  # Regex patterns that must not appear in code (non-comments)
    search_paths: List[str]  # Directories to search (relative to repo root)
    search_extensions: List[str]  # File extensions to check (e.g., ['.sh', '.py', '.md'])
    skip_patterns: List[str]  # Regex patterns in comments/strings that are OK (legacy, SPEC example, etc.)


# Define all SPEC constraints here — add new ones as the framework evolves
CONSTRAINTS = [
    Constraint(
        name="no-external-scripts-in-orchestration",
        description="All automation must flow through DELEGATE/HANDBACK; external scripts forbidden in orchestration/",
        spec_section="Queue Architecture & Paths (LOCKED)",
        forbidden_patterns=[
            r"orchestration/scripts",
            r"orchestration/config/.*\.cron",
        ],
        search_paths=["src/skills", "renderer"],  # Only check skills and renderer, not helper scripts
        search_extensions=[".sh", ".py"],
        skip_patterns=["LEGACY", "fallback", "historic", "example", "TODO"],
    ),
    # Future constraints can be added here:
    # Constraint(
    #     name="queue-paths-canonical",
    #     description="All queue paths must use ~/.agentic-engineers/ canonical path",
    #     spec_section="Queue Architecture & Paths",
    #     forbidden_patterns=[r"~/.copilot/queue", r"~/\.claude/queue"],
    #     search_paths=["src", "docs"],
    #     search_extensions=[".py", ".sh", ".md"],
    #     skip_patterns=["LEGACY", "deprecated", "historic"],
    # ),
]


def is_comment_line(line: str) -> bool:
    """Check if line is a comment (bash, python, etc)."""
    stripped = line.lstrip()
    return stripped.startswith("#") or stripped.startswith("//")


def should_skip_violation(line: str, skip_patterns: List[str]) -> bool:
    """Check if line contains skip pattern (marked as legacy/example/etc)."""
    return any(pattern.lower() in line.lower() for pattern in skip_patterns)


def find_violations(constraint: Constraint, repo_root: Path) -> List[Tuple[str, int, str]]:
    """
    Find violations of a constraint in the codebase.

    Returns: List of (file_path, line_number, line_content) tuples
    """
    violations = []

    for search_path in constraint.search_paths:
        full_path = repo_root / search_path
        if not full_path.exists():
            continue

        for file_path in full_path.rglob("*"):
            if not file_path.is_file():
                continue

            # Check file extension
            if file_path.suffix not in constraint.search_extensions:
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        # Skip comment-only lines
                        if is_comment_line(line):
                            continue

                        # Skip lines marked with skip patterns
                        if should_skip_violation(line, constraint.skip_patterns):
                            continue

                        # Check for forbidden patterns
                        for pattern in constraint.forbidden_patterns:
                            if re.search(pattern, line):
                                rel_path = file_path.relative_to(repo_root)
                                violations.append((str(rel_path), line_num, line.rstrip()))
                                break  # One violation per line
            except Exception as e:
                # Skip files that can't be read
                pass

    return violations


def validate_constraint(constraint: Constraint, repo_root: Path) -> Tuple[bool, List[Tuple[str, int, str]]]:
    """
    Validate a single constraint.

    Returns: (is_valid, violations)
    """
    violations = find_violations(constraint, repo_root)
    return len(violations) == 0, violations


def format_violation(file_path: str, line_num: int, line_content: str) -> str:
    """Format a violation for human-readable output."""
    return f"  {file_path}:{line_num}: {line_content}"


def main():
    parser = argparse.ArgumentParser(
        description="Validate SPEC architectural constraints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--constraint",
        help="Validate only this constraint (by name)",
        choices=[c.name for c in CONSTRAINTS],
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    constraints_to_check = (
        [c for c in CONSTRAINTS if c.name == args.constraint]
        if args.constraint
        else CONSTRAINTS
    )

    all_valid = True
    total_violations = 0

    for constraint in constraints_to_check:
        is_valid, violations = validate_constraint(constraint, repo_root)
        total_violations += len(violations)

        if not is_valid:
            all_valid = False
            print(f"❌ {constraint.name}")
            print(f"   {constraint.description}")
            print(f"   SPEC: {constraint.spec_section}")
            print()
            for violation in violations:
                print(format_violation(*violation))
            print()
        else:
            print(f"✅ {constraint.name}")

    if all_valid:
        print(f"\n✅ All {len(constraints_to_check)} SPEC constraint(s) valid")
        return 0
    else:
        print(f"\n❌ {total_violations} violation(s) found across {len(constraints_to_check)} constraint(s)")
        print("\nFix: Remove hardcoded paths and use SPEC-canonical patterns (see docs/SPEC.md)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
