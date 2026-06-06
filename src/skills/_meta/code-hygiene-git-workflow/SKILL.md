---
name: code-hygiene-git-workflow
description: "Disciplined queue-to-branch-to-PR-to-merge workflow for code quality and CI stability"
type: meta
role: team-discipline
category: workflow-standards
version: 1.0
maturity: draft
effort_estimate: 15-20h for full team adoption
---

# CODE-HYGIENE-GIT-WORKFLOW

## Metadata

```yaml
name: code-hygiene-git-workflow
type: meta
role: team-discipline
category: workflow-standards
version: 1.0
maturity: draft
effort_estimate: 15-20h for full team adoption
```

## Purpose

Establish disciplined queue→branch→PR→merge→rebase workflow to maximize code quality, minimize CI failures, and maintain polished production state. This skill defines standards for:

- Queue management (TODO.md, incoming tasks, DELEGATE tracking)
- Branch discipline (feature branches, atomic commits, clear naming)
- Pre-commit/pre-push validation gates (catch obvious failures locally)
- PR consolidation & review (grouped by feature area)
- Merge discipline (watch CI, fix failures ASAP)
- Post-merge rebase & verification (keep all branches up-to-date)

## Core Principles

1. **Local Validation First**: All obvious failures caught locally BEFORE CI runs
   - Linting (syntax, style, naming conventions)
   - Basic tests (unit tests, type checking)
   - Contract validation (function signatures, parameter types)
   - No commits that break test suite locally

2. **CI as Release Gate**: CI pipeline validates release-readiness, not development correctness
   - Runs full test suite in container environment (catches environment mismatches)
   - Validates against real infrastructure constraints (permissions, symlinks, paths)
   - Acts as final sanity check before merge
   - Quick re-run to confirm stability

3. **Queue→Branch→PR Flow**:
   ```
   TODO.md / incoming/
      ↓ (DELEGATE task created)
   Feature branch created
      ↓ (code + tests + docs)
   Atomic commits (one logical change per commit)
      ↓ (pass all pre-commit/pre-push checks)
   Pre-push: Full test suite passes locally
      ↓ (push to origin)
   PR created (grouped by feature area)
      ↓ (CI runs, user review)
   Merge to main (watch for CI failures)
      ↓ (PRIORITY: investigate + fix any CI failures)
   Post-merge: Rebase all active branches
      ↓ (Verify no new conflicts/breakage)
   Return to Step 2 for next task
   ```

4. **Atomic PRs**: Each PR covers one logical feature/fix area
   - Group related commits (e.g., all linting improvements, all test additions)
   - Keep PRs focused and reviewable (< 500 LOC per PR is ideal)
   - One PR per branch (avoid mixing unrelated work)
   - Clear PR title/description linking to task IDs

5. **Merge Discipline**: 
   - Watch for CI failures immediately after merge
   - Treat CI failures as PRIORITY (block new work until fixed)
   - Root-cause analysis required (don't just re-run)
   - Fix committed to same branch, squashed into atomic commit if needed
   - Re-merge after fix verified

6. **Rebase Discipline**:
   - After successful merge, rebase all active feature branches
   - Verify no new conflicts or breakage introduced
   - Test locally after rebase (ensure merged code compatible with branch)
   - Mark branches as "rebase-verified" before resuming work

## Validation Gates

### Pre-Commit (Auto-Run, Developer Workstation)

Catches issues before they're even committed:

```yaml
checks:
  - name: syntax-validation
    tools: [python -m py_compile, shellcheck]
    description: "No syntax errors in Python/shell files"
    fail_fast: true
    
  - name: linting-basic
    tools: [black, pylint --disable=convention]
    description: "Code style and obvious bugs (not design/convention)"
    fail_fast: false
    categories: [pep8, naming, obvious-bugs]
    
  - name: type-checking
    tools: [mypy --strict]
    description: "Type annotations match function signatures"
    fail_fast: true
    
  - name: import-validation
    tools: [isort --check-only]
    description: "Imports properly sorted and organized"
    fail_fast: true
    
  - name: file-permissions
    tools: [custom: check_file_permissions.py]
    description: "No executable bits on .md, .yaml, .txt files"
    fail_fast: true
    
  - name: secrets-detection
    tools: [detect-secrets]
    description: "No API keys, passwords, tokens in committed code"
    fail_fast: true
    
  - name: contract-validation
    tools: [custom: validate_function_contracts.py]
    description: "Function signatures match decorator expectations"
    fail_fast: true
```

**Implementation**: `.githooks/pre-commit` (auto-installed by `make setup`)

### Pre-Push (Auto-Run, Developer Workstation)

Catches failures before they reach origin:

```yaml
checks:
  - name: unit-tests-pass
    command: "make test"
    description: "All unit tests pass locally (full suite, ~5min)"
    fail_fast: true
    
  - name: integration-tests-pass
    command: "make test-integration"
    description: "All integration tests pass locally (~3min)"
    fail_fast: true
    
  - name: spec-compliance
    command: "make validate-spec"
    description: "Code complies with SPEC.md requirements"
    fail_fast: true
    
  - name: env-simulation
    command: "docker run --rm -v $(pwd):/workspace -w /workspace python:3.11 make test"
    description: "Tests pass in container environment (simulates CI)"
    fail_fast: false
    optional: true
    note: "Optional on first push, mandatory on second attempt if CI later fails"
```

**Implementation**: `.githooks/pre-push` (auto-installed by `make setup`)

### CI Pipeline (GitHub Actions)

Final gate before merge:

```yaml
stages:
  - name: lint
    checks: [black --check, pylint, mypy]
    timeout: 5min
    
  - name: test
    checks: [make test, make test-integration]
    timeout: 10min
    matrix: [python-3.9, python-3.10, python-3.11]
    
  - name: container-validation
    checks: ["docker run ... make test"]
    timeout: 15min
    description: "Verify tests pass in clean container (CI environment)"
    
  - name: security-scan
    checks: [bandit, safety, secrets-detection]
    timeout: 5min
    
  - name: build-artifacts
    checks: ["make build", verify-artifact-integrity]
    timeout: 10min
```

## Workflow Checklist

### Starting a New Task (from TODO/queue)

- [ ] Create feature branch: `git checkout -b feature/TASK-ID-short-description`
- [ ] Update TODO.md: mark task as `in_progress`
- [ ] Make changes, write tests, update docs
- [ ] Commit atomically: `git commit -m "TASK-ID: one logical change"`
- [ ] Pre-commit checks run automatically (fix any failures)

### Before Pushing

- [ ] Run `make test` locally (all tests pass)
- [ ] Run `make validate-spec` (code complies with SPEC.md)
- [ ] Review commits: `git log origin/main..HEAD` (each commit is one logical unit)
- [ ] Update SPEC.md if behavior changed (required for all non-trivial changes)
- [ ] Pre-push checks run automatically (fix any failures)

### Creating PR

- [ ] Title format: `[AREA] TASK-ID: Brief description` (e.g., `[Security] TASK-CI-001: Fix path validation`)
- [ ] Link to task ID in PR description
- [ ] Group related commits (same feature area)
- [ ] Keep PR < 500 LOC if possible (break into multiple PRs if needed)
- [ ] Add summary of changes, testing approach, and any breaking changes
- [ ] Request review from appropriate role (Security Engineer, Senior Engineer, etc.)

### After Merge (PRIORITY WORKFLOW)

**CRITICAL**: Watch for CI failures immediately after merge!

- [ ] Monitor GitHub Actions CI run (don't close terminal/browser)
- [ ] If CI passes: proceed to Post-Merge rebase (below)
- [ ] If CI fails:
  - [ ] Check logs immediately (don't let it sit)
  - [ ] Root-cause analysis (not just re-run)
  - [ ] Create fix commit to same branch (still available for checkout)
  - [ ] Push fix to origin
  - [ ] Create new PR for fix (or force-push to same PR if not yet merged)
  - [ ] After fix merges, re-merge main to feature branches (see Post-Merge below)

### Post-Merge (Rebase All Active Branches)

After successful merge, prepare all active branches:

- [ ] List active branches: `git branch -a | grep feature/`
- [ ] For each active branch:
  - [ ] `git fetch origin`
  - [ ] `git checkout feature/X`
  - [ ] `git rebase origin/main` (handle any conflicts)
  - [ ] `make test` (verify no new breakage from merged code)
  - [ ] Mark branch as "rebase-verified" in TODO.md
- [ ] Update TODO.md: mark all rebase-verified branches
- [ ] Proceed to next task only after all rebases verified

## Git Commit Message Format

```
TASK-ID: One-line summary (imperative, < 50 chars)

Optional detailed explanation (wrapped at 72 chars):
- What changed and why
- Any non-obvious implementation details
- Links to related tasks/issues

Relates-to: TASK-ID-RELATED
Fixes: #issue-number (if applicable)
```

## Branch Naming Convention

```
feature/TASK-ID-short-slug        # New features, enhancements
fix/TASK-ID-short-slug            # Bug fixes
refactor/TASK-ID-short-slug       # Code refactoring (no behavior change)
docs/TASK-ID-short-slug           # Documentation only
security/TASK-ID-short-slug       # Security hardening
test/TASK-ID-short-slug           # Test additions/improvements
```

Example: `feature/EVALS-001-sanitization-pipeline`

## Queue Management

### TODO.md Structure

```markdown
## In Queue (Ready to Start)
- [ ] TASK-CI-001: Implement linting gates (estimate: 4h)
- [ ] TASK-EVALS-001: Build sanitization pipeline (estimate: 6h)

## In Progress
- [x] TASK-SECURITY-001: Phase 1.5 FIXes (branch: feature/TASK-SECURITY-001)
  - Rebase-verified: ✓
  - Pre-push: ✓
  - PR: #24 (merged)

## Blocked (Waiting For)
- [ ] TASK-OPENCODE-001: Depends on TASK-SECURITY-001 (PR merged 2026-05-30)

## Completed This Week
- [x] TASK-SECURITY-001 → PR #24 merged
```

### Incoming Queue (Parallel Delegation)

Store as YAML files in `~/.agentic-engineers/queue/incoming/`:

```yaml
---
task_id: TASK-FEATURE-001
type: DELEGATE
role: senior-engineer
model: claude-opus-4.8  # temporary 48h window
effort: high
priority: urgent

context:
  description: |
    Clear, actionable description
  repo: github.com/niallyoung/agentic-engineers
  branch: feature/TASK-FEATURE-001
  files: [list of relevant files]

requirements:
  - Req 1
  - Req 2
  
acceptance_criteria:
  - "AC1: Testable outcome"
  - "AC2: Framework integrated"
```

## Prevention Patterns

### Catch Environment Mismatch Bugs

**Pattern**: Test locally in container environment before push

```bash
# Before git push:
docker run --rm -v $(pwd):/workspace -w /workspace python:3.11 make test
```

**Why**: Catches filesystem differences (symlinks, permissions, paths)

### Catch Contract Violations

**Pattern**: Add type hints + assert parameters at function entry

```python
def validate_queue_path(path: Path | str) -> bool:
    """Validate queue path (must be directory, not file)."""
    p = Path(path)
    assert p.is_dir(), f"Expected directory, got file: {p}"  # Catch misuse immediately
    # ... rest of validation
```

**Why**: Catches wrong types at runtime with clear error messages

### Catch Incomplete Feature Integration

**Pattern**: Use add-feature-to-framework SKILL checklist

- [ ] Tests written (unit + integration)
- [ ] Docs updated (README, AGENTS.md, inline comments)
- [ ] SPEC.md updated (new requirements/constraints)
- [ ] Framework integration verified (hooks, decorators, validators)
- [ ] No framework drift (compliance check passes)

**Why**: Prevents partial features that work in isolation but break integration

## Implementation Roadmap

### Phase 1 (This 48h Window)
- Create `.githooks/pre-commit` (linting, type checking, secrets detection)
- Create `.githooks/pre-push` (run full test suite)
- Add to `make setup` (auto-install hooks)
- Document workflow in AGENTS.md

### Phase 2 (Post-48h)
- Add container simulation to pre-push (optional on first run)
- Build comprehensive test environment validation
- Create automated compliance dashboard (SPEC.md drift detection)

### Phase 3 (Ongoing)
- Apply to all team members (training, code review)
- Measure impact (reduce CI failures by X%)
- Iterate based on feedback

## Related Skills

- `add-feature-to-framework`: Checklist for fully integrating new features
- `spec-validator`: Validates compliance with SPEC.md requirements
- `protocol-validator`: Validates DELEGATE/HANDBACK protocol compliance
- `spec-management`: Manages SPEC.md changes with approval workflow

## References

- `.githooks/`: Hook implementation
- `Makefile`: `make setup`, `make test`, `make validate-spec`
- `SPEC.md`: Framework requirements
- `AGENTS.md`: Role definitions
- `TODO.md`: Task tracking
