#!/usr/bin/env python3
"""
Validate SPEC architectural constraints across the codebase.

This script enforces rules defined in docs/SPEC.md by scanning source code for
violations. Constraints are defined declaratively, making it easy to add new
rules without modifying this script.

Usage:
  python3 scripts/validate-spec-constraints.py                    # Check all constraints
  python3 scripts/validate-spec-constraints.py --constraint NAME  # Check specific constraint

Invoked by .githooks/pre-push (see that hook's SPEC constraint section).
"""

import re
import sys
import argparse
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class Constraint:
    """Defines a SPEC architectural constraint to validate."""
    name: str
    description: str
    spec_section: str  # e.g., "ORCHESTRATOR-FIRST EXECUTION MODEL"
    forbidden_patterns: List[str]  # Regex patterns that must not appear in code (non-comments)
    search_paths: List[str]  # Directories to search (relative to repo root)
    search_extensions: List[str]  # File extensions to check (e.g., ['.sh', '.py', '.md'])
    skip_patterns: List[str]  # Regex patterns in comments/strings that are OK (legacy, SPEC example, etc.)


# Define all SPEC constraints here — add new ones as the framework evolves
CONSTRAINTS = [
    # orchestration/ no longer exists (removed in the framework slimdown). These
    # patterns are retained as a *re-introduction* guard: nothing may add an
    # external script-runner tree back under orchestration/.
    Constraint(
        name="no-external-scripts-in-orchestration",
        description="All automation must flow through DELEGATE/HANDBACK; external scripts forbidden in orchestration/",
        spec_section="ORCHESTRATOR-FIRST EXECUTION MODEL",
        forbidden_patterns=[
            r"orchestration/scripts",
            r"orchestration/config/.*\.cron",
        ],
        search_paths=["src/skills", "renderer"],  # Only check skills and renderer, not helper scripts
        search_extensions=[".sh", ".py"],
        skip_patterns=["LEGACY", "fallback", "historic", "example", "TODO"],
    ),
    # Future constraints can be added here.
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
            except OSError as e:
                print(f"warning: could not read {file_path}: {e}", file=sys.stderr)

    return violations


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
    args = parser.parse_args()

    # Derive the repo root from this file, not the cwd: running the script from a
    # subdirectory used to silently scan nothing and report success.
    repo_root = Path(__file__).resolve().parent.parent
    constraints_to_check = (
        [c for c in CONSTRAINTS if c.name == args.constraint]
        if args.constraint
        else CONSTRAINTS
    )

    all_valid = True
    total_violations = 0

    for constraint in constraints_to_check:
        violations = find_violations(constraint, repo_root)
        total_violations += len(violations)

        if violations:
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
