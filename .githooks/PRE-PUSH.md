# Pre-Push Hook Implementation

## Overview

The `.githooks/pre-push` script is a comprehensive quality gate that runs before every `git push` operation. It validates the codebase against multiple criteria to ensure code quality, protocol compliance, and documentation consistency.

## Installation

The hook is automatically installed when you run:

```bash
git config core.hooksPath .githooks
```

Or during the initial setup:

```bash
make install
```

## Features

### 1. **Agent YAML Validation**
- Validates YAML frontmatter in `src/agents/*.md` files
- Checks for required fields: `name`, `model`
- Ensures valid YAML syntax
- Skips README files automatically

### 2. **Workflow File Validation**
- Validates GitHub Actions workflow files (`.github/workflows/*.yml`)
- Checks for required fields: `name`, `on` (trigger)
- Ensures valid YAML syntax

### 3. **Documentation Consistency**
- Verifies presence of required documentation files:
  - `docs/SPEC.md` (with `version:` field)
  - `docs/AGENTS.md`
  - `README.md`
- Checks for top-level headings in documentation

### 4. **DELEGATE/HANDBACK Protocol Validation**
- Validates DELEGATE files in `artifacts/delegates/`
- Checks for required fields:
  - DELEGATE: `handoff_type`, `task_id`, `role`, `model`
- Ensures valid YAML syntax

### 5. **SPEC Compliance**
- Verifies no external scripts in `orchestration/scripts/`
- Verifies no cron files in `orchestration/config/`
- Checks Makefile for proper script invocation patterns
- Allows `renderer/scripts/` as an exception for build-time operations

### 6. **Test Suite Execution**
- Runs pytest on the `tests/` directory
- Skips `test_git_hooks.py` to prevent timeout
- Warns if tests fail (non-blocking)
- Times out after 30 seconds to prevent hanging

### 7. **Protected Branch Warnings**
- Warns when pushing to `main` or `master` branches
- Reminds developers to ensure Quality Engineer review

## Validation Output

The hook provides color-coded output with clear status indicators:

```
📋 Pre-push validation starting...

🤖 Validating agent definitions...
✅ Agent YAML frontmatter valid

🔄 Validating workflow files...
✅ Workflow files valid

📚 Validating documentation consistency...
✅ Documentation files present and valid

📦 Validating DELEGATE/HANDBACK protocol...
✅ DELEGATE/HANDBACK protocol valid

🧪 Running test suite...
✅ All tests passed

🔐 Validating SPEC compliance...
✅ SPEC compliance verified

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Pre-push validation summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Checks passed: 7
  Checks failed: 0
  Errors:       0
  Warnings:     0

✅ pre-push: quality gate passed
```

## Error Handling

### Blocking Errors

The following issues will block the push:

1. **Invalid YAML**: Agent files, workflows, or protocol files with invalid YAML
2. **Missing Required Fields**: SPEC.md, AGENTS.md, or protocol files missing required fields
3. **SPEC Violations**: External scripts in orchestration/ or cron files
4. **Missing Documentation**: Required documentation files not found

### Non-Blocking Warnings

The following issues will warn but allow the push:

1. **Test Failures**: Some tests failed (review before pushing to shared branches)
2. **Protected Branch**: Pushing to main/master (ensure QE review)
3. **Test Timeout**: Test suite timed out (>30s)

## Bypass

For emergency situations, you can bypass the hook:

```bash
SKIP_HOOKS=1 git push
```

**Important**: This should only be used in genuine emergencies and should be documented in your commit message.

## Testing

The hook includes a comprehensive test suite in `tests/test_pre_push_hook.py`:

```bash
python3 tests/test_pre_push_hook.py
```

Tests verify:

1. Hook file exists and is executable
2. Hook has correct shebang
3. SKIP_HOOKS bypass works
4. Agent YAML validation
5. Documentation files exist
6. SPEC.md and AGENTS.md structure
7. Workflow YAML validation
8. DELEGATE/HANDBACK protocol compliance
9. SPEC compliance (no external scripts)
10. Test directory exists
11. Hook output format

## Implementation Details

### Hook Location
- **File**: `.githooks/pre-push`
- **Permissions**: Executable (`755`)
- **Shebang**: `#!/usr/bin/env bash`

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `SKIP_HOOKS` | Bypass all validations | `0` |
| `SKIP_PYTEST` | Skip pytest execution | `0` |

### Color Codes

- 🟢 **Green (✅)**: Check passed
- 🔴 **Red (❌)**: Error (blocking)
- 🟡 **Yellow (⚠️)**: Warning (non-blocking)
- 🔵 **Blue (ℹ️)**: Information

### Timeout Values

- **Test Suite**: 30 seconds
- **Hook Overall**: No timeout (but individual checks are fast)

## Integration with CI/CD

The pre-push hook runs locally before pushing. It complements CI/CD checks by:

1. **Early Feedback**: Developers get immediate feedback before pushing
2. **Reduced CI Load**: Prevents invalid commits from reaching CI
3. **Protocol Compliance**: Ensures DELEGATE/HANDBACK files committed to the repo are schema-valid
4. **Documentation Sync**: Keeps documentation in sync with code changes

## Troubleshooting

### Hook Not Running

1. Verify git hooks are configured:
   ```bash
   git config core.hooksPath
   ```
   Should output: `.githooks`

2. Verify hook is executable:
   ```bash
   ls -la .githooks/pre-push
   ```
   Should show `rwxr-xr-x` permissions

3. Reinstall hooks:
   ```bash
   git config core.hooksPath .githooks
   ```

### Hook Timeout

If the hook times out:

1. Check for hanging pytest tests:
   ```bash
   pytest tests/ --timeout=5
   ```

2. Run tests individually:
   ```bash
   pytest tests/test_specific.py -v
   ```

3. Bypass temporarily:
   ```bash
   SKIP_HOOKS=1 git push
   ```

### YAML Validation Errors

If YAML validation fails:

1. Check file syntax:
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('file.yaml'))"
   ```

2. Use a YAML linter:
   ```bash
   yamllint file.yaml
   ```

## Future Enhancements

Potential improvements to the pre-push hook:

1. **Incremental Validation**: Only validate changed files
2. **Parallel Checks**: Run validations in parallel for speed
3. **Custom Rules**: Allow project-specific validation rules
4. **Performance Metrics**: Track validation time per check
5. **Caching**: Cache validation results for unchanged files

## Related Documentation

- [.githooks/pre-commit](../pre-commit) - Pre-commit hook
- [.githooks/commit-msg](../commit-msg) - Commit message validation
- [docs/SPEC.md](../../docs/SPEC.md) - Framework specification
- [docs/AGENTS.md](../../docs/AGENTS.md) - Agent documentation

## CI Environment Simulation (test-ci)

For developers who want to test in an environment matching GitHub Actions before pushing:

```bash
# First run (simulates CI environment locally)
make test-ci

# Strict mode (must pass, useful before force push)
make test-ci-force

# Interactive debugging in container
make test-ci-shell
```

See [Makefile](../../Makefile) for details on `test-ci` targets.
