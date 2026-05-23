# repo-init: Detailed Workflow Reference

**Skill:** `repo-init` v1.0  
**Author:** Senior Engineer  
**Purpose:** Full decision tree and phase-level logic for repository initialization

---

## Pre-flight Guard Clauses

Before any phase begins, repo-init runs these checks in order. Any HARD FAIL aborts
with a clear error message and non-zero exit code.

```
Is repo_root a valid directory?         → HARD FAIL if not
Is repo_root a git repo?                → HARD FAIL if not (run git init first)
Is Python ≥ 3.8 available?             → HARD FAIL if not
Is .agentic-engineers/INIT-COMPLETE.yaml present? → WARN + abort unless --force-reinit
Is SPEC.md already at docs/SPEC.md?    → WARN, skip Phase 2 unless --force-reinit
```

---

## Phase 1: Repository Analysis — Decision Tree

```
scan repo_root/
│
├── Count file extensions
│   ├── .py files > threshold?   → primary_language = "python"
│   ├── .ts/.tsx > threshold?    → primary_language = "typescript"
│   ├── .go > threshold?         → primary_language = "go"
│   ├── .rs > threshold?         → primary_language = "rust"
│   ├── .java > threshold?       → primary_language = "java"
│   └── none dominant?           → primary_language = "polyglot"
│
├── Package manager detection (first match wins)
│   ├── pyproject.toml → "pip/poetry"
│   ├── requirements.txt → "pip"
│   ├── package.json → "npm" (or "yarn"/"pnpm" from packageManager field)
│   ├── go.mod → "go"
│   ├── Cargo.toml → "cargo"
│   ├── pom.xml → "maven"
│   ├── build.gradle → "gradle"
│   ├── Gemfile → "bundler"
│   └── none found → "unknown"
│
├── Test framework detection
│   ├── pytest.ini or pyproject.toml [tool.pytest] → "pytest"
│   ├── jest.config.* → "jest"
│   ├── vitest.config.* → "vitest"
│   ├── go.mod present → "go-test"
│   ├── Cargo.toml present → "cargo-test"
│   └── none → "unknown"
│
├── CI/CD detection
│   ├── .github/workflows/*.yml → "github-actions"
│   ├── .gitlab-ci.yml → "gitlab-ci"
│   ├── Jenkinsfile → "jenkins"
│   ├── .circleci/ → "circleci"
│   ├── .buildkite/ → "buildkite"
│   └── none → "none"
│
├── Monorepo detection
│   ├── packages/ directory exists → True
│   ├── apps/ + shared/ directories → True
│   ├── services/ with ≥3 subdirs → True
│   ├── workspaces in package.json → True
│   └── else → False
│
└── Size classification
    ├── total_files < 100 → "small"
    ├── total_files < 1000 → "medium"
    └── total_files ≥ 1000 → "large"
```

**Size-based adjustments to conservative defaults:**

| Size | Engineer Model | Coverage Threshold | Effort Default |
|------|---------------|-------------------|----------------|
| small | claude-haiku-4.5 | 85% | low |
| medium | claude-haiku-4.5 | 85% | low |
| large | claude-sonnet-4.6 | 70% | medium |

---

## Phase 2: SPEC.md Generation — Template Variables

The SPEC.md template (`assets/spec-template.md`) uses these placeholders:

| Variable | Source | Example |
|----------|--------|---------|
| `{project_name}` | config or inferred | `my-api` |
| `{project_description}` | config or `""` | `REST API for widgets` |
| `{primary_language}` | Phase 1 | `python` |
| `{package_manager}` | Phase 1 | `pip` |
| `{test_framework}` | Phase 1 | `pytest` |
| `{ci_provider}` | Phase 1 | `github-actions` |
| `{framework_version}` | config | `5.10` |
| `{model_harness}` | config | `claude` |
| `{date}` | runtime | `2025-05-09` |
| `{engineer_model}` | compat result | `claude-haiku-4.5` |
| `{senior_model}` | compat result | `claude-sonnet-4.6` |
| `{lead_model}` | compat result | `claude-sonnet-4.6` |
| `{principal_model}` | compat result | `claude-opus-4.7` |
| `{quality_threshold}` | size-based | `85` |
| `{git_remote}` | Phase 1 | `github.com/org/repo` |
| `{license}` | Phase 1 | `MIT` |

---

## Phase 3: Directory Structure — Idempotency Rules

All directory/file creation follows these rules:

```python
def safe_mkdir(path: Path) -> bool:
    """Create directory only if it does not exist. Return True if created."""
    if path.exists():
        return False  # idempotent — no-op
    path.mkdir(parents=True, exist_ok=True)
    return True

def safe_write(path: Path, content: str, force: bool = False) -> bool:
    """Write file only if it does not exist (or force=True). Return True if written."""
    if path.exists() and not force:
        return False  # idempotent — skip
    path.write_text(content)
    return True
```

---

## Phase 5: Framework Detection — Resolution Order

```
1. AGENTIC_ENGINEERS_HOME env var set?
   └─→ YES: use that path (validate it contains src/agents/, src/skills/)
       NO: continue

2. ~/.agentic-engineers/ directory exists?
   └─→ YES: check for version marker (framework_version.txt)
       version matches? → use it
       version mismatch → WARN, use anyway
       NO: continue

3. ../agentic-engineers/ directory adjacent to repo_root?
   └─→ YES: validate structure, use it
       NO: continue

4. pip package agentic_engineers importable?
   └─→ YES: use pkg_resources to find path
       NO: continue

5. No framework found → WARN and skip Phase 5
   (repo-init continues; user must manually copy agents later)
```

---

## Phase 6: Compatibility Validation — Detailed Checks

### Tool Check Implementation

```bash
# Each check runs in a subprocess with timeout=5s
git --version 2>/dev/null | grep -q "git version"
python3 -c "import sys; assert sys.version_info >= (3, 8)" 2>/dev/null
bash --version 2>/dev/null | grep -q "bash"
jq --version 2>/dev/null | grep -q "jq"
curl --version 2>/dev/null | grep -q "curl"
```

### API Key Masking

API keys are NEVER logged. Only a boolean is stored:

```python
def _check_api_key(env_var: str) -> bool:
    """Returns True if key is present and non-empty. NEVER logs the key value."""
    val = os.environ.get(env_var, "")
    return bool(val.strip())
```

### Local Model Detection

```python
def _detect_local_model() -> Optional[str]:
    """Detect running local LLM server."""
    # 1. Ollama: check OLLAMA_HOST or default http://localhost:11434
    try:
        r = requests.get(
            os.environ.get("OLLAMA_HOST", "http://localhost:11434") + "/api/tags",
            timeout=2
        )
        if r.status_code == 200:
            return "ollama"
    except Exception:
        pass

    # 2. LM Studio: check default port 1234
    try:
        r = requests.get("http://localhost:1234/v1/models", timeout=2)
        if r.status_code == 200:
            return "lm-studio"
    except Exception:
        pass

    return None
```

---

## Phase 7: TODO.md — Conditional Item Logic

```python
def build_conditional_todos(analysis: AnalysisResult) -> List[TodoItem]:
    items = []

    if analysis.test_framework == "unknown":
        items.append(TodoItem(
            id="INIT-T01",
            priority="standard",
            title="Create test suite foundation",
            description=f"No test framework detected. Add {_suggest_test_fw(analysis.primary_language)}.",
            owner="Engineer",
        ))

    if analysis.ci_provider == "none":
        items.append(TodoItem(
            id="INIT-C01",
            priority="standard",
            title="Add CI/CD workflow",
            description="No CI/CD detected. Add GitHub Actions or equivalent.",
            owner="Engineer",
        ))

    if analysis.is_monorepo:
        items.append(TodoItem(
            id="INIT-M01",
            priority="standard",
            title="Configure per-package agent scoping",
            description="Monorepo detected. Configure agents per package boundary.",
            owner="Senior Engineer",
        ))

    if not analysis.has_readme:
        items.append(TodoItem(
            id="INIT-R01",
            priority="priority",
            title="Review and extend generated README.md",
            description="No README.md detected; generated a stub. Customize for project.",
            owner="Engineer",
        ))

    if analysis.total_files >= 1000:
        items.append(TodoItem(
            id="INIT-L01",
            priority="priority",
            title="Run architecture audit before agent delegation",
            description=f"Large codebase ({analysis.total_files} files). Run audit before queuing work.",
            owner="Principal Engineer",
        ))

    if analysis.contributor_count > 5:
        items.append(TodoItem(
            id="INIT-X01",
            priority="standard",
            title="Share ONBOARDING.md with team",
            description=f"{analysis.contributor_count} contributors detected. Share docs/ONBOARDING.md.",
            owner="Lead Engineer",
        ))

    return items
```

---

## Phase 8: Documentation — Section Map

### `docs/ONBOARDING.md` Structure

```
1. Welcome — What is the agentic-engineers framework?
2. Prerequisites — Python, git, model harness setup
3. Your First Task — How to submit via DELEGATE block
4. Agent Team — Who does what (from docs/AGENTS.md)
5. DELEGATE/HANDBACK Protocol — Quick reference
6. Quality Gates — What quality checks run automatically
7. TODO.md — How to read and add work items
8. Troubleshooting — Common issues and fixes
9. Further Reading — Links to docs/
```

### `docs/QUICK-START.md` Structure

```
1. In 5 minutes — Minimal working example
2. DELEGATE block template — Copy-paste starter
3. HANDBACK format — What to expect back
4. Queue commands — Check status, view done/pending
5. TDD workflow — RED → GREEN → REFACTOR cheatsheet
6. Common mistakes — Top 5 pitfalls
```

### `docs/AGENTS.md` Structure

```
1. Agent roster — Enabled agents for this repo
2. Routing table — Task type → Agent mapping
3. Model assignments — Which model per role
4. Effort guide — When to use low/medium/high
5. Escalation paths — When to escalate and to whom
```

---

## Error Handling

All errors follow this pattern:

```python
class RepoInitError(Exception):
    def __init__(self, phase: str, message: str, recoverable: bool = False):
        self.phase = phase
        self.message = message
        self.recoverable = recoverable
        super().__init__(f"[{phase}] {message}")
```

- `recoverable=True` → log warning, skip phase, continue
- `recoverable=False` → log error, abort, write partial `INIT-FAILED.yaml`

The `INIT-FAILED.yaml` marker records which phases completed so a re-run can
skip them with `--resume`.

---

## Resume Logic

```bash
# Resume from where a failed init left off
python src/skills/repo-init/scripts/repo_init.py \
  --repo-root /path/to/repo \
  --resume
```

Resume reads `.agentic-engineers/INIT-FAILED.yaml`:
```yaml
status: FAILED
failed_at: housekeeping
completed_phases:
  - analyze
  - generate-spec
  - bootstrap-structure
timestamp: 2025-05-09T14:23:00Z
```

And skips already-completed phases.
