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

## Next Steps

1. Commit the workflow: `git add .github/workflows/ci.yml && git commit -m "ci: add GitHub Actions CI/CD workflow"`
2. Push to main: `git push origin main`
3. Workflow runs automatically
4. First tag will be `v0.8.0`
