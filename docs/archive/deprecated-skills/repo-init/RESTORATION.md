# repo-init Restoration Guide

## Status

**Deprecated:** 2026-05-30  
**Reason:** Disabled due to user concerns about installing into other repos without explicit approval. Heavy dependencies and complex integration requirements make it a maintenance burden.

## Deprecation Rationale

- **Already disabled** with explicit user concern documented in SKILL.md
- **No test coverage** — complex integration with high risk of failure
- **Heavy dependencies** — depends on both agent-creator and spec-management
- **Scope creep** — 8-phase initialization process too broad for reliable automation
- **Risk profile** — repo modification without clear user consent is problematic

## Historical Context

`repo-init` was designed to bootstrap new repositories with the agentic-engineers framework in a single invocation. It performs:

1. Repository analysis (language, package manager, CI/CD structure)
2. SPEC.md generation with project-specific configuration
3. Framework structure initialization (agents/, skills/, tests/, docs/)
4. Package manager housekeeping (.gitignore, README sections)
5. Framework bootstrap (symlink/copy core agents and essential skills)
6. Compatibility validation (harness, tools, API keys)
7. TODO.md initialization with priority-ordered first delegations
8. Documentation generation (ONBOARDING.md, QUICK-START.md, repo-specific AGENTS.md)

However, concerns about modifying user repositories without explicit approval led to this skill being marked as DISABLED.

## Alternatives & Migration Paths

**For bootstrapping new repos, use one of these alternatives:**

1. **Manual bootstrap** (RECOMMENDED)
   - Copy `SPEC.md` template from docs/
   - Run `make setup` to install hooks and dependencies
   - Manually create `src/agents/`, `docs/` structure as needed
   - This gives full control and clarity about what's being modified

2. **Use agent-creator directly** (FOR SKILLED USERS)
   - Use the `agent-creator` skill to scaffold individual agents
   - Use the `skill-creator` skill to scaffold individual skills
   - Combine manually for full framework setup

3. **Reference existing repos**
   - Study the agentic-engineers repo structure in `docs/ONBOARDING.md`
   - Copy patterns manually rather than running automated bootstrap
   - Safer and more transparent

## When to Restore

**Do NOT restore this skill unless:**
1. User explicitly approves automated repo modification
2. Comprehensive test suite is added (≥20 tests covering all 8 phases)
3. Safety confirmations are added (explicit DELEGATE confirmation required before modifying)
4. Clear documentation exists about exactly what files will be modified

**Restore if:** Your team frequently bootstraps new repos and wants to automate the process with explicit per-repo approval.

## Git Commands to Restore

**Option A: Restore from archive (this repository)**
```bash
# Copy the archived skill back to active skills
cp -r docs/archive/deprecated-skills/repo-init ~/.claude/skills/repo-init

# Update __init__.py to re-enable
# Edit .opencode/agent-router.yaml to include repo-init in routing

# Re-run tests
pytest tests/test_repo_init.py -v

# Commit and push
git add -A
git commit -m "restore: re-enable repo-init skill with safety improvements"
git push
```

**Option B: Restore from git history**
```bash
# Find the commit where repo-init was active
git log --oneline --all -- .claude/skills/repo-init | head -5

# Check out the skill directory from that commit
git show <commit_hash>:.claude/skills/repo-init > /tmp/repo-init-backup.tar
tar -xf /tmp/repo-init-backup.tar ~/.claude/skills/

# Re-enable in __init__.py and routing
# Re-run tests
# Commit with safety improvements documented
```

**Option C: Restore from upstream (if available)**
```bash
# If the framework is imported from upstream
git remote add upstream https://github.com/anomalyco/agentic-engineers.git
git fetch upstream main

# Cherry-pick the repo-init commits
git cherry-pick <commit_hash>

# Re-run tests and commit
```

## How to Re-Enable

**BEFORE re-enabling, address all deprecation concerns:**

1. **Add comprehensive test suite:**
   ```bash
   tests/test_repo_init.py (minimum 20 tests)
   - test_bootstrap_python_repo
   - test_bootstrap_node_repo
   - test_bootstrap_go_repo
   - test_spec_generation_with_project_specifics
   - test_framework_structure_creation
   - test_safety_confirmation_required (critical)
   - test_dry_run_mode (non-destructive)
   - test_rollback_on_error
   + 12 more
   ```

2. **Add safety mechanism:**
   - Require explicit DELEGATE confirmation with `--approve-repo-modification` flag
   - Add dry-run mode (`--dry-run`) to show what will be modified
   - Generate summary report of changes before applying
   - Enable rollback to pre-modification state

3. **Update SKILL.md:**
   - Remove disabled status
   - Add safety section documenting confirmation process
   - Add dry-run usage examples
   - Document rollback procedure

4. **Re-register in __init__.py:**
   ```python
   # In skills/__init__.py
   from .repo_init import RepoInit  # Uncomment
   AVAILABLE_SKILLS['repo-init'] = RepoInit
   ```

5. **Update routing rules:**
   ```yaml
   # In .opencode/agent-router.yaml
   - skill: repo-init
     condition: "task_type == 'bootstrap' AND user_approval == true"
     role: senior-engineer
     tier: standard
   ```

6. **Re-enable in docs/SKILLS-AVAILABLE.md:**
   - Move from "Deprecated" section back to "Operations Skills"

7. **Commit and test:**
   ```bash
   git add tests/ skills/ .opencode/ docs/
   git commit -m "restore: re-enable repo-init with safety improvements

   - Added comprehensive test suite (20+ tests)
   - Added explicit approval requirement (--approve-repo-modification)
   - Added dry-run mode (--dry-run)
   - Added rollback capability
   - Updated documentation with safety procedures"
   
   make verify  # Ensure all tests pass
   git push
   ```

## Archive Location

```
docs/archive/deprecated-skills/repo-init/
├── SKILL.md (original skill definition)
├── scripts/ (original implementation)
├── RESTORATION.md (this file)
└── tests/ (original tests, if any)
```

## Last Known State

- **Deprecation Commit:** d84e255e (2026-05-30)
- **Last Active Commit:** (check git history)
- **Test Coverage:** 0% (no tests in original)
- **Dependencies:** agent-creator, spec-management
- **Scripts:** 9 implementation files in scripts/

## Questions?

Refer to:
- `docs/DEPRECATED-SKILLS.md` — Master index of all deprecated skills
- `docs/ONBOARDING.md` — Manual bootstrap procedure
- `.opencode/agent-router.yaml` — Skill routing configuration
