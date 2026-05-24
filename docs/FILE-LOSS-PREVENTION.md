# File Loss Prevention: Comprehensive Guide

## Quick Answer: "How do I prevent files from being lost?"

Background agents (skill-creator, agent-creator, etc.) **must explicitly commit files to git**. This guide explains why and how.

---

## Table of Contents

1. [The Problem](#the-problem)
2. [Root Causes](#root-causes)
3. [Prevention Mechanisms](#prevention-mechanisms)
4. [For Background Agents](#for-background-agents)
5. [For Orchestrators](#for-orchestrators)
6. [Troubleshooting](#troubleshooting)

---

## The Problem

### Scenario

A background agent (e.g., skill-creator) is invoked to create a new skill:

1. **Agent creates files**: `SKILL.md`, `main.py`, `test.py`
2. **Agent runs tests**: All tests pass ✅
3. **Agent returns HANDBACK**: Status = "complete" ✅
4. **Session ends** ⏱️
5. **Files are lost** ❌ (not in git, not in any persistent storage)

### Impact

- **Developer discovers files missing** when trying to use the skill
- **No way to recover** (files only existed in agent's ephemeral working directory)
- **Time wasted** recreating files or debugging why creation "failed"

---

## Root Causes

### 1. Ephemeral Working Directories

Background agents run in isolated, temporary working directories that are deleted when the agent session ends. **Files created in these directories must be explicitly committed to git to persist.**

### 2. Bytecode Cache Masking

Python caches compiled `.pyc` files in `__pycache__/`. If:
- Agent creates `test.py` and runs tests (creates `test.pyc`)
- Agent **forgets** to commit `test.py`
- Pytest loads the cached `.pyc` (tests appear to work!)
- Session ends, `test.py` is lost, `.pyc` cache is cleared

**Result**: Tests pass locally, but fail on CI when `test.pyc` doesn't exist.

### 3. No Explicit Commitment Protocol

Without a mandatory protocol, agents might:
- Assume files will be committed automatically (they won't)
- Forget to stage files before returning HANDBACK
- Return HANDBACK without verifying commit succeeded

---

## Prevention Mechanisms

The framework implements **8 layered prevention mechanisms**:

### Mechanism 1: Agent Commit Protocol (CRITICAL)
**What**: Agents explicitly `git add` and `git commit` files before returning HANDBACK

**Where**: All background agents, particularly:
- `skills/skill-creator/`
- `skills/agent-creator/`
- Any agent that creates files in `src/` or `skills/`

**Validation**: HANDBACK schema requires `commit_sha` field (proves files reached git)

---

### Mechanism 2: Pre-Commit Hook Bytecode Check
**What**: `.githooks/pre-commit` rejects any `.pyc` files from being staged

**When**: Before any commit (catches mistakes immediately)

**Output**:
```
❌ ERROR: Staged .pyc file detected: skills/my-skill/__pycache__/main.cpython-37.pyc
   Fix: git reset HEAD skills/my-skill/__pycache__/
        echo '**/__pycache__/' >> .gitignore
```

---

### Mechanism 3: Test Source Audit (pytest plugin)
**What**: Pytest plugin validates all tests come from `.py` source (not `.pyc` cache)

**When**: Before running tests (when tests are collected)

**Output**:
```
🔍 Audit: Test Source Integrity
✅ Test source audit passed: 42 tests from valid .py sources
```

**Failure**:
```
❌ TEST SOURCE AUDIT FAILED
Some tests are from bytecode cache without .py source:
   - tests/test_module.py
FIX: rm -rf .pytest_cache __pycache__; pytest --cache-clear
```

---

### Mechanism 4: CI/CD Validation
**What**: GitHub Actions workflow validates:
- No `.pyc` files in committed history
- All test sources exist on disk
- Skill/agent test-implementation pairs are complete

**When**: On every push and PR

**Jobs**:
1. `check-orphaned-bytecode` — Find stray `.pyc` files
2. `verify-test-sources` — Collect tests, verify sources exist
3. `check-skill-integrity` — Verify test/impl pairs

---

### Mechanism 5: HANDBACK Schema Validation
**What**: HANDBACK schema includes fields for commit tracking:
- `commit_sha` — Git SHA of commit (required if `status: complete`)
- `committed_files` — List of files in the commit

**Validation**:
```yaml
commit_sha: "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
# Must be:
# - Valid SHA-1 (40 hex chars)
# - Exist in git history (git cat-file -t <sha> == 'commit')
# - Include all files from committed_files list
```

---

### Mechanism 6: Orchestrator Commit Validation
**What**: Orchestrator verifies commit before accepting HANDBACK

**Process**:
1. Receive HANDBACK with `commit_sha`
2. Run: `git cat-file -t <sha>` → verify it's a commit
3. Run: `git show <sha> --stat` → verify files are in commit
4. Reject HANDBACK if validation fails

---

### Mechanism 7: Bytecode Timestamp Check
**What**: Pre-commit hook warns if `.pyc` is newer than `.py` (stale source)

**Indicator**: Means source `.py` wasn't regenerated after `.pyc` was created

**Action**: Clear `__pycache__/` and regenerate

---

### Mechanism 8: Documentation & Troubleshooting
**What**: Clear protocols and guides for:
- Agents: How to properly commit files
- Orchestrators: How to validate commits
- Developers: How to troubleshoot missing files

**Where**:
- `docs/BACKGROUND-AGENT-COMMIT-PROTOCOL.md` — Agent protocol
- `docs/FILE-LOSS-PREVENTION.md` — This document
- `CONTRIBUTING.md` — Links to protocols

---

## For Background Agents

### If You Create Files

You **MUST** do all of these before returning HANDBACK:

#### 1. Verify Files Exist
```bash
git status --short
# Shows all created files as "?? filename"
```

#### 2. Run Tests (if applicable)
```bash
pytest [test_file] -v
# All tests must pass
```

#### 3. Stage Files
```bash
git add [directory_with_files]
git status --short
# Shows all files as "A  filename" (staged)
```

#### 4. Create Commit
```bash
git commit -m "Create: [description]

Files:
- [file1]
- [file2]
...

All tests passing."
```

#### 5. Get Commit SHA
```bash
COMMIT_SHA=$(git rev-parse HEAD)
echo "Committed: $COMMIT_SHA"
```

#### 6. Validate Commit
```bash
git show HEAD --stat
# Verify all files appear in output
```

#### 7. Report in HANDBACK
```yaml
status: complete
committed_files:
  - [file1]
  - [file2]
  ...
commit_sha: "a1b2c3d4e5f6..."
```

### Example Implementation

```python
# In skill-creator/scripts/main.py or similar

def create_skill(skill_name):
    # 1. Create files
    files_created = scaffold_skill(skill_name)
    print(f"✅ Created {len(files_created)} files")
    
    # 2. Run tests
    test_result = run_tests()
    assert test_result.passed == test_result.total, "Tests failed!"
    print("✅ All tests passed")
    
    # 3. Stage files
    for f in files_created:
        run_cmd(f"git add {f}")
    print(f"✅ Staged {len(files_created)} files")
    
    # 4. Verify staging
    status = run_cmd("git status --short").output
    assert all(f"A  {f}" in status for f in files_created)
    print("✅ All files staged correctly")
    
    # 5. Commit
    commit_msg = f"Create: {skill_name}\n\nFiles:\n" + \
                 "\n".join(f"- {f}" for f in files_created)
    run_cmd(f"git commit -m '{commit_msg}'")
    print("✅ Committed")
    
    # 6. Get SHA
    commit_sha = run_cmd("git rev-parse HEAD").output.strip()
    print(f"✅ Commit SHA: {commit_sha}")
    
    # 7. Validate
    stat = run_cmd(f"git show {commit_sha} --stat").output
    assert all(f in stat for f in files_created)
    print("✅ Commit validated")
    
    # 8. Return HANDBACK
    return {
        "status": "complete",
        "committed_files": files_created,
        "commit_sha": commit_sha,
        "tests": {"passed": test_result.total, "failed": 0},
    }
```

---

## For Orchestrators

### When Receiving HANDBACK

If HANDBACK includes `commit_sha`:

```python
def validate_handback(handback):
    if handback.get("status") == "complete" and handback.get("committed_files"):
        commit_sha = handback.get("commit_sha")
        
        # 1. Verify commit exists
        result = run_cmd(f"git cat-file -t {commit_sha}")
        if result.returncode != 0:
            raise ValidationError(f"Commit not found: {commit_sha}")
        
        # 2. Verify files in commit
        stat = run_cmd(f"git show {commit_sha} --stat").output
        for file in handback["committed_files"]:
            if file not in stat:
                raise ValidationError(f"File missing from commit: {file}")
        
        # 3. Store validation result
        handback["commit_validation"] = {
            "validated_at": now(),
            "valid": True,
            "files_in_commit": [...]
        }
    
    return handback
```

---

## Troubleshooting

### Problem: "Files were created but aren't in git"

**Diagnosis**:
```bash
# Agent's working directory still exists?
ls -la /tmp/agent-session-xyz/src/skills/new-skill/
# Files exist but aren't committed

git log --oneline --all | head -10
# Commit not in history
```

**Cause**: Agent didn't commit files before session ended

**Fix**:
1. Recreate files if possible (agent's session might still exist)
2. Re-run agent with explicit instruction to commit
3. Or manually recreate files and commit them

---

### Problem: "Pytest says tests don't exist"

**Error**:
```
ERROR: file not found: tests/test_module.py
```

**Diagnosis**:
```bash
# Check if .py exists
ls -la tests/test_module.py
# File not found

# Check if .pyc exists
find . -name "test_module*.pyc"
# Found: __pycache__/test_module.cpython-37.pyc
```

**Cause**: Source `.py` is missing, only `.pyc` cache remains

**Fix**:
```bash
# Clear cache
rm -rf .pytest_cache __pycache__

# Recreate source or restore from git
git checkout tests/test_module.py

# Re-run tests
pytest --cache-clear
```

---

### Problem: "Pre-commit hook rejects my commit with bytecode error"

**Error**:
```
❌ ERROR: Staged .pyc file detected: skills/my-skill/__pycache__/main.cpython-37.pyc
```

**Cause**: You accidentally staged `.pyc` bytecode

**Fix**:
```bash
# Unstage the bytecode
git reset HEAD skills/my-skill/__pycache__/

# Ensure .gitignore has bytecode entries
echo "**/__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore

# Re-stage (without bytecode)
git add skills/my-skill/
git add .gitignore

# Commit
git commit -m "Create: my-skill"
```

---

### Problem: "Orchestrator says commit validation failed"

**Error**:
```
❌ Commit validation failed: File 'src/skills/new-skill/main.py' missing from commit
```

**Diagnosis**:
```bash
# Check what's in the commit
git show a1b2c3d4 --stat
# main.py not listed

# Check git log
git log --oneline | grep "Create: new-skill"
# Commit exists
```

**Cause**: File was staged but didn't make it into the commit (permission error, interruption, etc.)

**Fix**:
```bash
# Re-stage the file
git add src/skills/new-skill/main.py

# Amend the commit
git commit --amend

# Verify
git show HEAD --stat
# main.py should now appear

# Get new SHA and update HANDBACK
```

---

### Problem: "CI/CD validation fails with 'orphaned bytecode'"

**Error**:
```
❌ Found 1 orphaned bytecode issue(s)
   ❌ ERROR: Orphaned bytecode without source
      Bytecode: ./skills/my-skill/__pycache__/module.cpython-37.pyc
      Expected source: ./skills/my-skill/module.py
```

**Cause**: Someone committed `.pyc` without `.py` source (or `.py` was deleted)

**Fix**:
```bash
# 1. Find and delete orphaned .pyc
find . -path "*/__pycache__/*" -name "*.pyc" -delete

# 2. Recreate missing .py sources (or restore from previous commit)
git checkout HEAD^ -- skills/my-skill/module.py

# 3. Commit the fix
git add skills/my-skill/
git commit -m "Fix: restore missing module.py source"

# 4. Push and re-run CI/CD
git push
```

---

## Best Practices

1. **Always stage before committing**: `git add [files]` before `git commit`

2. **Never commit `.pyc` files**: Add `**/__pycache__/` and `*.pyc` to `.gitignore`

3. **Clear cache when suspicious**: `rm -rf .pytest_cache __pycache__` before running tests

4. **Validate before returning HANDBACK**: Run `git show HEAD --stat` to verify

5. **Test locally first**: Run `pytest --cache-clear` locally to catch missing sources

6. **Document what you create**: Include file list in commit message

---

## Related Documentation

- `docs/BACKGROUND-AGENT-COMMIT-PROTOCOL.md` — Detailed agent protocol
- `.githooks/pre-commit` — Pre-commit validation
- `.github/workflows/validate-sources.yml` — CI/CD validation
- `tests/conftest.py` — Pytest plugin (test source audit)
- `src/orchestration/handback-schema.yaml` — HANDBACK schema with commit fields

---

## Questions?

- **For agents**: See `BACKGROUND-AGENT-COMMIT-PROTOCOL.md`
- **For debugging**: See [Troubleshooting](#troubleshooting)
- **For validation**: See `src/orchestration/handback-schema.yaml`

