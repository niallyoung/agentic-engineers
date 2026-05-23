# CI/CD Workflow

This repository uses GitHub Actions for automated quality checks and semantic versioning.

## Workflow: `ci.yml`

Triggered on:
- **Push to `main` branch** (automatic)
- **Manual dispatch** (via `workflow_dispatch` in GitHub UI)

### Jobs

#### 1. Quality Gate
Runs linting, testing, and verification using the Makefile:
- `make lint` — Syntax checks (Python, Shell, YAML)
- `make test` — Pytest suite with coverage
- `make verify` — Framework structure validation (agents, skills, protocols)

Only proceeds to tagging if **all checks pass**.

#### 2. Tag Release
**Only runs if:**
1. Quality gate job succeeds
2. Branch is `main`

**Actions:**
- Reads conventional commit messages (e.g., `feat:`, `fix:`, `BREAKING CHANGE:`)
- Automatically determines semantic version bump (patch/minor/major)
- Creates annotated git tag (format: `v0.8.0`, `v0.8.1`, etc.)
- Generates release summary in GitHub's workflow run UI
- **Initial version:** `v0.8.0` (for current HEAD)

### Semantic Versioning

The workflow uses conventional commits to determine version bumps:

| Commit Type | Bump | Example |
|---|---|---|
| `fix:` | Patch | `v0.8.0` → `v0.8.1` |
| `feat:` | Minor | `v0.8.0` → `v0.9.0` |
| `BREAKING CHANGE:` | Major | `v0.8.0` → `v1.0.0` |

Example commit messages:
```
fix: correct auth token validation
feat: add new agent routing system
feat!: refactor protocol queue structure
```

### Manual Trigger

To manually run the workflow:
1. Go to **Actions** → **CI**
2. Click **Run workflow** → **Run workflow**
3. Workflow runs immediately

### Version Tags

Tags are created automatically and visible in:
- GitHub Releases (`/releases`)
- Git log: `git log --oneline --decorate`
- Git tags: `git tag -l`

### Viewing Workflow Runs

- GitHub: **Actions** → **CI** tab shows all runs
- Each run shows pass/fail status and detailed logs
- Release summaries appear in the job summary

## Configuration

See `.github/workflows/ci.yml` for full configuration. Key settings:
- `python-version`: 3.11
- `default_bump`: patch (if no conventional commit detected)
- `tag_prefix`: `v` (creates tags like `v0.8.0`)
- `release_branches`: main (only tags main branch)

## Current Status

✅ **Workflow deployed and active** at `.github/workflows/ci.yml`

**Test Execution Status:** The quality gate successfully exercises all Makefile targets (lint, test, verify) on every main push. However, the test suite currently has pre-existing failures in test modules:
- `test_agent_creator.py` - Missing skill module imports
- `test_queue_management.py` - Missing skill module imports  
- `test_git_hooks.py` - Missing .git/hooks directory in CI
- `test_spec_management.py` - Missing skill module imports

These failures exist locally as well and are unrelated to the CI workflow itself. They need to be fixed in the codebase to enable automatic tagging.

## Next Steps

**To enable automatic tagging on main pushes:**
1. Fix failing test modules to eliminate ModuleNotFoundError and FileNotFoundError
2. Once all tests pass, the next push to main will:
   - Run quality gate (lint + test + verify)
   - If all pass, automatically create tag `v0.8.0`
   - Subsequent commits will increment: `v0.8.1`, `v0.9.0`, etc. (semantic versioning)

## Configuration Notes

- **PYTHONPATH handling:** Set dynamically in Makefile (`test` target) using `REPO_ROOT` variable, not hardcoded
- **pytest configuration:** `pytest.ini` configured with `pythonpath = .` for test discovery
- **Makefile:** Uses `git rev-parse --show-toplevel` for dynamic repo root detection
