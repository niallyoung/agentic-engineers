# ADD-FEATURE-TO-FRAMEWORK

## Metadata

```yaml
name: add-feature-to-framework
type: meta
role: senior-engineer
category: integration-checklist
version: 1.0
maturity: draft
applies_to: every new feature, SKILL, agent, decorator, validation gate
effort_estimate: 2-4h additional for full framework integration (on top of implementation)
```

## Purpose

Provide a comprehensive checklist ensuring every new feature/SKILL/agent:
- Aligns with SPEC.md requirements and intent
- Includes complete test coverage (unit + integration)
- Has complete documentation (code, README, AGENTS.md, inline comments)
- Is fully integrated into framework (hooks, decorators, validators)
- Passes framework compliance checks
- No partial implementations that work in isolation but break integration

## When to Use This Skill

Use this checklist **EVERY TIME** you add:
- New SKILL or agent
- New validation gate, decorator, or framework mechanism
- New API endpoint or core function
- New command-line interface feature
- Changes to SPEC.md or core framework behavior
- New security hardening measure

## The Checklist (Expandable Template)

### Phase 1: Design & Planning (Before Implementation)

- [ ] **Task is clearly defined**
  - [ ] Problem statement documented
  - [ ] Success criteria explicit (acceptance criteria)
  - [ ] Scope boundaries defined (what's in/out)
  - [ ] Estimated effort realistic (not guessed)

- [ ] **Framework alignment verified**
  - [ ] Doesn't contradict existing SPEC.md
  - [ ] Fits with existing architecture patterns
  - [ ] No circular dependencies with other SKILLs
  - [ ] Identified which roles will use this feature
  - [ ] Identified integration points (hooks, validators, decorators)

- [ ] **Design reviewed by appropriate role**
  - [ ] Security features: reviewed by Security Engineer
  - [ ] Core framework: reviewed by Principal/Lead Engineer
  - [ ] Integration points: reviewed by framework maintainer

### Phase 2: Implementation

- [ ] **Code written with quality standards**
  - [ ] Type hints on all function signatures
  - [ ] Docstrings on all public functions
  - [ ] Error handling for all edge cases
  - [ ] No hardcoded values (use constants/config)
  - [ ] Follows existing code patterns in codebase

- [ ] **Unit tests written FIRST (TDD)**
  - [ ] Test-driven development: RED → GREEN → REFACTOR
  - [ ] Test every public function
  - [ ] Test both happy path and error cases
  - [ ] Test edge cases (empty input, None, invalid types)
  - [ ] Mocks external dependencies (don't hit real APIs)
  - [ ] Tests are fast (< 1 second per test)
  - [ ] Tests are independent (can run in any order)

- [ ] **Integration tests verify framework connections**
  - [ ] Feature works with existing hooks/decorators
  - [ ] Feature works with validation gates
  - [ ] Feature works with queue management
  - [ ] Feature works with other related SKILLs
  - [ ] No test fragility (doesn't fail intermittently)

- [ ] **Local environment testing**
  - [ ] `make test` passes (all unit + integration tests)
  - [ ] `make validate-spec` passes (compliance with SPEC.md)
  - [ ] Container simulation test passes: `docker run ... make test`
  - [ ] No new linting warnings: `black`, `pylint`, `mypy --strict`
  - [ ] No security issues: `bandit`, `detect-secrets`

### Phase 3: Documentation

- [ ] **Code documentation complete**
  - [ ] Inline comments for non-obvious logic
  - [ ] Docstrings follow Google/NumPy style
  - [ ] Type hints explain parameter types
  - [ ] Examples provided for complex APIs

- [ ] **User-facing documentation updated**
  - [ ] README.md updated (if user-visible)
  - [ ] AGENTS.md updated (if affects roles/responsibilities)
  - [ ] New section in SKILL.md (if new SKILL)
  - [ ] Links added to related documentation
  - [ ] Examples provided for common use cases

- [ ] **SPEC.md updated (if behavior changed)**
  - [ ] New requirements documented
  - [ ] New constraints documented
  - [ ] Breaking changes listed
  - [ ] Migration path provided (if applicable)
  - [ ] Security implications noted (if applicable)

- [ ] **Framework documentation updated**
  - [ ] `src/AGENTS.md`: Role definitions (if role-specific)
  - [ ] `src/SKILLS.md`: SKILL documentation (if new SKILL)
  - [ ] `.githooks/README.md`: Hook documentation (if new hook)
  - [ ] `Makefile`: New targets documented
  - [ ] GitHub Actions workflows: Updated CI config (if new CI stage)

### Phase 4: Framework Integration

- [ ] **Hooks integrated (if applicable)**
  - [ ] Pre-commit hook updated: `.githooks/pre-commit`
  - [ ] Pre-push hook updated: `.githooks/pre-push`
  - [ ] Post-merge validation added: `.githooks/post-merge`
  - [ ] Hook installed in `make setup`

- [ ] **Decorators/Validators applied (if applicable)**
  - [ ] Feature uses framework decorators (e.g., `@enforce_delegate_requirement`)
  - [ ] Feature validates using framework validators (e.g., `validate_queue_path()`)
  - [ ] No bypassing framework constraints
  - [ ] Decorators have tests verifying they work

- [ ] **SPEC.md compliance verified**
  - [ ] Framework compliance check passes: `make validate-spec`
  - [ ] No SPEC.md drift detected
  - [ ] New feature respects all SPEC.md constraints
  - [ ] Enforcement mechanisms (decorators, validators) active

- [ ] **Protocol compliance verified (if DELEGATE/HANDBACK involved)**
  - [ ] DELEGATE tasks follow protocol: `spec-core-v1.0.yaml`
  - [ ] HANDBACK responses follow protocol
  - [ ] Protocol validation tool confirms compliance
  - [ ] No unknown/undefined protocol fields

### Phase 5: Testing & Verification

- [ ] **All tests pass**
  - [ ] `make test` passes (full suite)
  - [ ] `make test-integration` passes
  - [ ] `make validate-spec` passes
  - [ ] Zero new warnings/errors in linting

- [ ] **CI pipeline passes**
  - [ ] GitHub Actions workflow passes (all jobs)
  - [ ] No flaky tests (run 3 times to confirm)
  - [ ] Container environment test passes
  - [ ] Security scan passes (no new vulnerabilities)

- [ ] **Regression testing**
  - [ ] Existing tests still pass (didn't break anything)
  - [ ] Existing functionality still works
  - [ ] No unexpected side effects

- [ ] **Manual testing completed (for UI/API changes)**
  - [ ] Feature works as documented
  - [ ] Error messages are clear and actionable
  - [ ] Performance acceptable (no major slowdowns)

### Phase 6: Review & Merge

- [ ] **Code review checklist**
  - [ ] Another engineer reviewed the code
  - [ ] All review comments addressed
  - [ ] Code follows existing patterns
  - [ ] No security issues identified
  - [ ] Architecture decisions documented

- [ ] **PR preparation**
  - [ ] PR title clear: `[AREA] TASK-ID: Feature description`
  - [ ] PR description includes:
    - [ ] What changed and why
    - [ ] How to test the changes
    - [ ] Any breaking changes
    - [ ] Links to related tasks/issues
  - [ ] Related issues linked with `Closes #123` format
  - [ ] Draft PR reviewed before moving to "Ready for Review"

- [ ] **Post-merge process**
  - [ ] Watch GitHub Actions for any failures
  - [ ] If CI passes: proceed to rebase (see code-hygiene skill)
  - [ ] If CI fails: investigate immediately, root-cause, fix
  - [ ] Rebase all active feature branches on main
  - [ ] Verify no new conflicts/breakage in rebased branches

## Integration Verification Checklist

Before claiming "done", verify these framework connections:

### If Feature Uses Decorators

```python
# ✅ Correct: Feature respects @enforce_delegate_requirement
@enforce_delegate_requirement
def route_task(task: Dict) -> Result:
    # Implementation uses feature
    pass

# ❌ Wrong: Feature implemented but decorator not applied
def route_task(task: Dict) -> Result:
    # Implementation uses feature, but no decorator = can be bypassed
    pass
```

Test:
```bash
pytest tests/test_decorator_enforcement.py -v -k "enforce_delegate"
```

### If Feature Uses Validation

```python
# ✅ Correct: Feature validates inputs before use
def validate_feature_input(path: Path) -> bool:
    assert isinstance(path, Path), f"Expected Path, got {type(path)}"
    assert path.exists(), f"Path does not exist: {path}"
    return True

# ❌ Wrong: No validation, silent failure on wrong input
def use_feature(path):
    # Might fail mysteriously if path is wrong type
    pass
```

Test:
```bash
pytest tests/test_feature_validation.py -v
```

### If Feature Affects SPEC.md

```yaml
# ✅ Correct: New constraint added to SPEC.md
constraints:
  - All queue paths must be validated with validate_queue_path()
  - All DELEGATEs must use decorator @enforce_delegate_requirement

# ❌ Wrong: Feature implemented but SPEC not updated
# (Later, someone implements similar feature differently = inconsistency)
```

Test:
```bash
make validate-spec
```

### If Feature Adds New Role/Responsibility

```markdown
# ✅ Correct: AGENTS.md updated with new role
## Quality Engineer (New Role)
- Responsibility: Run enhanced test environment simulation
- Tools: Docker, pytest, container environment
- Authority: Can trigger pre-push gate validations

# ❌ Wrong: Feature implemented but AGENTS.md not updated
# (Team doesn't know about new role = bottleneck)
```

Test: Grep for role in AGENTS.md
```bash
grep "Quality Engineer" src/AGENTS.md
```

## Common Integration Gaps (Red Flags)

🚩 **Red Flag 1**: "Tests pass locally but fail in CI"
- **Root cause**: Feature not tested in container environment
- **Fix**: Add container simulation to pre-push hook
- **Prevention**: This checklist, Phase 5 (CI pipeline passes)

🚩 **Red Flag 2**: "Feature works but breaks existing tests"
- **Root cause**: Integration test coverage incomplete
- **Fix**: Add integration tests with existing features
- **Prevention**: This checklist, Phase 2 (Integration tests)

🚩 **Red Flag 3**: "Feature implemented but SPEC.md not updated"
- **Root cause**: Framework requirements unclear
- **Fix**: Update SPEC.md + re-run compliance checks
- **Prevention**: This checklist, Phase 3 (SPEC.md updated)

🚩 **Red Flag 4**: "Feature has no tests"
- **Root cause**: TDD not followed
- **Fix**: Implement tests retroactively (if possible)
- **Prevention**: This checklist, Phase 2 (Unit tests written FIRST)

🚩 **Red Flag 5**: "Feature uses wrong decorator or validator"
- **Root cause**: Framework integration not understood
- **Fix**: Review framework docs, apply correct decorators
- **Prevention**: This checklist, Phase 4 (Hooks/Decorators integrated)

## Quick Integration Checklist (Abbreviated)

For quick reference, these are the **must-haves**:

- [ ] Tests written first (TDD)
- [ ] All tests pass locally + in container
- [ ] SPEC.md updated (if behavior changed)
- [ ] Framework validators/decorators applied
- [ ] Documentation complete (code + SPEC + README)
- [ ] No framework compliance drift
- [ ] CI passes, no regressions
- [ ] PR reviewed and merged
- [ ] All active branches rebased and verified

## Related Skills

- `code-hygiene-git-workflow`: Pre-commit/pre-push workflow
- `spec-validator`: SPEC.md compliance verification
- `protocol-validator`: DELEGATE/HANDBACK protocol validation
- `spec-management`: Managing SPEC.md changes

## Examples

### Example 1: Adding a New Validation Gate

**Follows**: add-feature-to-framework + code-hygiene-git-workflow

1. Design phase: What should this validation check? When should it run?
2. Implement: Add validation function with type hints + docstrings
3. Tests: Unit tests for validation logic, integration tests with hooks
4. Docs: Update SPEC.md with new constraint, AGENTS.md with responsible role
5. Integration: Add to pre-commit hook, run in CI pipeline
6. Verification: Run compliance checks, container tests
7. Review: PR, merge, watch CI, rebase branches

### Example 2: Adding a New SKILL

**Follows**: add-feature-to-framework + skill-creator + code-hygiene-git-workflow

1. Design: Use `skill-creator` to scaffold SKILL structure
2. Implement: Fill in workflow logic, add tests
3. Docs: Complete SKILL.md, link from README and AGENTS.md
4. Integration: Add to `src/AGENTS.md`, update related decorators
5. Tests: Unit + integration tests, verify with existing workflows
6. Verification: Compliance checks pass, no drift
7. Review: PR, merge, watch CI

## Implementation Notes

This checklist is **aspirational and comprehensive**. In practice:
- Start with **Quick Integration Checklist** (the must-haves)
- For security/core features, go full checklist
- For docs/examples, abbreviated checklist is fine
- Use as PR review guide (check off items as you review)
- Update checklist based on team feedback

The goal is **consistency + completeness**, not perfection.
