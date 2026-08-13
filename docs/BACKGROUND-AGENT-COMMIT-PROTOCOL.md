# Background Agent File Commitment Protocol

## Overview

When background agents (like `skill-creator` or `agent-creator`) create implementation files, they **MUST** explicitly commit those files to git. This protocol ensures:

1. ✅ All created files make it to git history (no orphaned files)
2. ✅ Tests are not lost due to bytecode caching
3. ✅ HANDBACK includes proof of commitment (commit SHA)
4. ✅ Orchestrator can validate that files actually reached git

## Why This Matters

**Problem**: A background skill-creator agent creates:
- `src/skills/new-skill/SKILL.md`
- `src/skills/new-skill/scripts/main.py`
- `src/skills/new-skill/scripts/test.py`

The agent runs tests locally (they pass), but never commits. Result: files exist in working tree but are **orphaned** — not tracked in git history.

**Solution**: Agent explicitly stages and commits all files, proving they reached git.

---

## Mandatory Finalization Steps

**All background agents creating files MUST perform these steps in order:**

### Step 1: Verify Files Exist

```bash
# After creating all files, verify they exist on disk
git status --short

# Expected output:
# ?? src/skills/new-skill/SKILL.md
# ?? src/skills/new-skill/scripts/main.py
# ?? src/skills/new-skill/scripts/test.py
# ?? src/skills/new-skill/scripts/__init__.py
```

**✅ Action**: If files don't show as `??` (untracked), fix and re-create.

---

### Step 2: Run Tests (If Applicable)

```bash
# For skills/agents with test files, run tests to verify they work
cd src/skills/new-skill/
pytest scripts/test.py -v

# Expected: All tests pass
```

**✅ Action**: If tests fail, fix implementation and re-run. Do NOT proceed until tests pass.

---

### Step 3: Stage All Created Files

```bash
# Stage all files in the skill/agent directory
git add src/skills/new-skill/

# Verify staging
git status --short

# Expected output:
# A  src/skills/new-skill/SKILL.md
# A  src/skills/new-skill/scripts/main.py
# A  src/skills/new-skill/scripts/test.py
# A  src/skills/new-skill/scripts/__init__.py
```

**✅ Action**: If any files show as `??` (untracked), they weren't staged. Run `git add` again.

---

### Step 4: Create Commit with Detailed Message

```bash
# Create commit listing all files created
git commit -m "Create: new-skill skill

Files:
- src/skills/new-skill/SKILL.md (frontmatter + documentation)
- src/skills/new-skill/scripts/main.py (implementation)
- src/skills/new-skill/scripts/test.py (unit tests)
- src/skills/new-skill/scripts/__init__.py (module marker)

All tests passing. Ready for review."
```

**✅ Action**: If commit fails (e.g., permission error), investigate error and retry.

---

### Step 5: Get Commit SHA

```bash
# Get the SHA of the commit just created
COMMIT_SHA=$(git rev-parse HEAD)
echo "✅ Committed with SHA: $COMMIT_SHA"
```

**✅ Action**: Save this SHA — you'll need it for the HANDBACK report.

---

### Step 6: Validate Commit Includes All Files

```bash
# Show all files in the commit
git show HEAD --stat

# Expected output includes all files:
# src/skills/new-skill/SKILL.md         | 50 ++
# src/skills/new-skill/scripts/main.py  | 120 ++
# src/skills/new-skill/scripts/test.py  | 80 ++
# src/skills/new-skill/scripts/__init__.py | 0
# 4 files changed, 250 insertions(+)
```

**❌ CRITICAL**: If a file is missing from the commit, something went wrong:
- Re-run `git add` for that file
- Run `git commit --amend` to add it to the commit
- Verify with `git show HEAD --stat` again

---

## HANDBACK Reporting

When returning HANDBACK for background agent tasks that create files, **MUST** include:

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-09-skill-creation
status: complete

# ✅ REQUIRED: List all files created
deliverables:
  - src/skills/new-skill/SKILL.md
  - src/skills/new-skill/scripts/main.py
  - src/skills/new-skill/scripts/test.py
  - src/skills/new-skill/scripts/__init__.py

# ✅ REQUIRED: Commit SHA (proves files reached git)
committed_files:
  - src/skills/new-skill/SKILL.md
  - src/skills/new-skill/scripts/main.py
  - src/skills/new-skill/scripts/test.py
  - src/skills/new-skill/scripts/__init__.py

commit_sha: "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"

# ✅ Test results (prove tests work)
tests:
  passed: 8
  failed: 0
  coverage: 92.5
  framework: pytest
metrics:
  quality: 0.94

notes: "Skill created with 4 files. All tests passing with 92.5% coverage. Committed to git with SHA a1b2c3d4. Ready for review."

---
```

---

## Orchestrator Validation (Will Perform)

After receiving HANDBACK, the orchestrator will:

1. **Verify commit SHA exists**:
   ```bash
   git cat-file -t <commit_sha>  # Should return 'commit'
   ```

2. **Verify all files in commit**:
   ```bash
   git show <commit_sha> --stat
   # Check that all 'committed_files' appear in output
   ```

3. **Reject if validation fails**:
   ```
   ❌ Commit validation failed: File X missing from commit
   ```

---

## Troubleshooting

### Issue: "❌ Staged .pyc file detected"

**Cause**: You accidentally staged `.pyc` bytecode (should never be committed).

**Fix**:
```bash
git reset HEAD src/skills/new-skill/__pycache__/
echo "**/__pycache__/" >> .gitignore
git add .gitignore
git commit --amend
```

---

### Issue: "⚠️ Bytecode newer than source (stale .py?)"

**Cause**: `.pyc` file is newer than `.py` source, indicates source wasn't regenerated.

**Fix**:
```bash
rm -rf src/skills/new-skill/__pycache__
python3 -m py_compile src/skills/new-skill/scripts/main.py
git add src/skills/new-skill/scripts/main.py
git commit --amend
```

---

### Issue: "❌ Test file not found on disk"

**Cause**: Test file was staged but doesn't exist (corruption or deletion mid-creation).

**Fix**: Recreate the test file and re-stage:
```bash
# Recreate test file
# Then:
git add src/skills/new-skill/scripts/test.py
git commit --amend
```

---

### Issue: "❌ Commit validation failed: File missing"

**Cause**: File was staged but didn't make it into the commit (permission error, interruption, etc).

**Fix**:
```bash
# Re-stage and re-commit
git add [file_that_was_missing]
git commit --amend
```

---

## Checklist Before Returning HANDBACK

- [ ] All files created (verified with `ls -la`)
- [ ] Tests pass (verified with `pytest`)
- [ ] All files staged (verified with `git status --short`)
- [ ] Commit created (verified with `git log -1`)
- [ ] Commit includes all files (verified with `git show HEAD --stat`)
- [ ] Commit SHA saved (e.g., `a1b2c3d4...`)
- [ ] HANDBACK includes `commit_sha` field
- [ ] HANDBACK includes `committed_files` list
- [ ] All HANDBACK fields complete and valid

---

## Example: Complete Workflow

```bash
# 1. Create skill files (done by agent)
mkdir -p src/skills/new-skill/scripts
cat > src/skills/new-skill/SKILL.md << 'EOF'
---
name: new-skill
version: 0.1.0
---
# New Skill
Description here.
EOF
cat > src/skills/new-skill/scripts/main.py << 'EOF'
def create_skill():
    return "Created!"
EOF
cat > src/skills/new-skill/scripts/test.py << 'EOF'
def test_create():
    from main import create_skill
    assert create_skill() == "Created!"
EOF

# 2. Test
cd src/skills/new-skill
pytest scripts/test.py -v
# ✅ PASSED

# 3. Stage
cd /repo
git add src/skills/new-skill/

# 4. Verify staging
git status --short
# A  src/skills/new-skill/SKILL.md
# A  src/skills/new-skill/scripts/main.py
# A  src/skills/new-skill/scripts/test.py

# 5. Commit
git commit -m "Create: new-skill skill

Files:
- src/skills/new-skill/SKILL.md
- src/skills/new-skill/scripts/main.py
- src/skills/new-skill/scripts/test.py

All tests passing."

# 6. Get SHA
COMMIT_SHA=$(git rev-parse HEAD)
echo "$COMMIT_SHA"  # a1b2c3d4...

# 7. Validate
git show HEAD --stat
# src/skills/new-skill/SKILL.md          | 10 +
# src/skills/new-skill/scripts/main.py   | 5 ++
# src/skills/new-skill/scripts/test.py   | 4 ++
# 3 files changed, 19 insertions(+)

# 8. Return HANDBACK with commit_sha and committed_files
echo "✅ Ready to report HANDBACK with commit_sha=$COMMIT_SHA"
```

---

## Key Policies

1. **Mandatory**: All background agents creating files MUST commit them before returning HANDBACK
2. **Immediate**: Commits must happen before HANDBACK is created (not deferred)
3. **Validation**: Orchestrator will verify commit SHA exists before accepting HANDBACK
4. **Bytecode**: `.pyc` files NEVER staged; `.py` source always committed
5. **Proof**: HANDBACK must include commit SHA as proof of commitment

---

## Related Documents

- `.githooks/pre-commit` — Pre-commit hook validates source integrity
- `docs/CONTRIBUTING.md` — General contribution guidelines
- `tests/conftest.py` — Pytest fixtures (includes test source audit)
- `.github/workflows/ci.yml` — CI/CD source integrity checks (orphaned bytecode
  gate; folded in from the former `validate-sources.yml` in the 2026-08-13
  infra consolidation)
