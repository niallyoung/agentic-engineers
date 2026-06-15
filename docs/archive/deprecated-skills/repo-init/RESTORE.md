# RESTORE: repo-init

This skill was archived on 2026-06-14 as part of Wave 3 skills consolidation (m3-skills-deprecation).

## Why archived

repo-init was explicitly disabled by user policy concern. It has 76 tests and 5660 LOC but
zero production utility in the current framework configuration.

## Restoration instructions

To restore this skill:

1. Move this directory back to `src/skills/repo-init/`
2. Re-add to CORE_SKILLS in `src/harnesses/claude_code/skill_renderer.py` if desired
3. Run `make render-claude` to re-register in dist/
4. Follow spec-management approval flow for un-deprecating (required per framework convention)

## Archive commit

Git history preserves all code: `git log -- src/skills/repo-init/`

## Original location

`src/skills/repo-init/`
