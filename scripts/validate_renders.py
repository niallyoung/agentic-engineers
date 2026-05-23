#!/usr/bin/env python3
"""
validate_renders.py — verify that all src/skills/ entries have corresponding dist/ outputs.

Usage:
    python3 scripts/validate_renders.py [REPO_ROOT]

    REPO_ROOT defaults to the parent directory of this script's parent (i.e., repo root).

Exit codes:
    0 — all renders are in sync
    1 — one or more skills are missing from dist/, or dist/ itself is absent

Part of the agentic-engineers rendering pipeline:
    src/skills/  →  (render-*)  →  dist/<harness>/skills/  →  (install-*)  →  ~/.harness/skills/

This validator checks that every skill directory in src/skills/ that contains a SKILL.md
is present in ALL expected dist/<harness>/skills/ directories.  It also reports any stale
entries in dist/ that no longer have a source counterpart (warnings only, not errors).

Run automatically via:
    make validate-renders
    make quality-gate  (includes validate-renders)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


# Harnesses whose dist/<harness>/skills/ dirs must mirror src/skills/
HARNESSES = ["claude", "copilot", "opencode"]

# Skill directories in src/skills/ that are framework-internal and intentionally
# NOT rendered to dist/ (e.g., _meta contains implementation helpers, not user-facing skills)
_META_PREFIXES = ("_",)


def _is_renderable_skill(skill_dir: Path) -> bool:
    """Return True if this directory is a user-facing rendered skill."""
    name = skill_dir.name
    if any(name.startswith(p) for p in _META_PREFIXES):
        return False
    if not (skill_dir / "SKILL.md").exists():
        return False
    return True


def collect_source_skills(src_skills: Path) -> list[str]:
    """Return sorted list of renderable skill names from src/skills/."""
    return sorted(
        d.name
        for d in src_skills.iterdir()
        if d.is_dir() and _is_renderable_skill(d)
    )


def validate_renders(repo_root: Path) -> bool:
    """
    Validate that every source skill has a corresponding dist/<harness>/skills/ entry.

    Returns True if everything is in sync, False if any discrepancies found.
    """
    src_skills = repo_root / "src" / "skills"
    dist_root = repo_root / "dist"

    if not src_skills.exists():
        print(f"❌ src/skills/ not found at {src_skills}", file=sys.stderr)
        return False

    # ── dist/ presence check ────────────────────────────────────────────────
    if not dist_root.exists():
        print("❌ dist/ directory does not exist.")
        print("   Run 'make render-all' to generate rendered outputs.")
        return False

    source_skills = collect_source_skills(src_skills)
    if not source_skills:
        print("⚠️  No renderable skills found in src/skills/ — nothing to validate.")
        return True

    print(f"📋 Source skills ({len(source_skills)}): {', '.join(source_skills)}")
    print()

    all_ok = True
    harness_results: dict[str, dict[str, str]] = {}  # harness → {skill: status}

    for harness in HARNESSES:
        dist_skills_dir = dist_root / harness / "skills"
        harness_results[harness] = {}

        if not dist_skills_dir.exists():
            print(f"❌ dist/{harness}/skills/ not found.")
            print(f"   Run 'make render-{harness}' to regenerate.")
            for skill in source_skills:
                harness_results[harness][skill] = "missing_dir"
            all_ok = False
            continue

        for skill in source_skills:
            dist_skill = dist_skills_dir / skill
            if not dist_skill.exists():
                harness_results[harness][skill] = "missing"
                all_ok = False
            elif not (dist_skill / "SKILL.md").exists():
                harness_results[harness][skill] = "no_skill_md"
                all_ok = False
            else:
                harness_results[harness][skill] = "ok"

        # Stale check: dist skills without a source counterpart
        source_set = set(source_skills)
        for dist_skill in sorted(dist_skills_dir.iterdir()):
            if dist_skill.is_dir() and dist_skill.name not in source_set:
                print(
                    f"⚠️  dist/{harness}/skills/{dist_skill.name} has no source in src/skills/"
                    f" (stale — consider 'make render-{harness}' to refresh)"
                )

    # ── Report ───────────────────────────────────────────────────────────────
    print()
    header = f"{'Skill':<30}" + "  ".join(f"{h:<10}" for h in HARNESSES)
    print(header)
    print("─" * len(header))

    for skill in source_skills:
        row = f"{skill:<30}"
        for harness in HARNESSES:
            status = harness_results[harness].get(skill, "?")
            symbol = {
                "ok": "✅",
                "missing": "❌",
                "no_skill_md": "⚠️ ",
                "missing_dir": "❌",
                "?": "❓",
            }.get(status, "❓")
            row += f"{symbol:<12}"
        print(row)

    print()
    if all_ok:
        print(f"✅ All {len(source_skills)} skill(s) rendered correctly across {len(HARNESSES)} harness(es).")
    else:
        missing = sum(
            1
            for h in HARNESSES
            for s in source_skills
            if harness_results[h].get(s, "?") != "ok"
        )
        print(
            f"❌ {missing} render discrepancy(ies) found. Run 'make render-all' to regenerate dist/."
        )

    return all_ok


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if args:
        repo_root = Path(args[0]).resolve()
    else:
        # Default: parent of this script's parent directory
        repo_root = Path(__file__).resolve().parent.parent

    if not repo_root.exists():
        print(f"❌ REPO_ROOT not found: {repo_root}", file=sys.stderr)
        return 1

    ok = validate_renders(repo_root)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
