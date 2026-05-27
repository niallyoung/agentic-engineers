---
name: repo-init
description: "[DISABLED] Initializes new repositories with the agentic-engineers framework. Currently disabled pending further discussion about repo modification policies."
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.8+, git, bash.
metadata:
  author: agentic-engineers
  version: "1.0"
  category: orchestration
  role: senior-engineer
  model: claude-sonnet-4.6
  effort: medium
  thinking: false
  disabled: true
  disabled_reason: "User concern about installing into other repos without explicit approval"
  dependencies:
    - agent-creator
    - spec-management
---

# repo-init [DISABLED]

## Status

**This skill is currently DISABLED.** It was designed to bootstrap new repositories with the agentic-engineers framework, but has been disabled pending further discussion about repo modification policies and user concerns regarding installing into external repositories without explicit approval.

## Overview (Archived)

~~`repo-init` bootstraps any repository to be immediately job-ready for agentic-engineers
workflow — agents, delegation queues, SPEC-driven quality gates, and documentation —
with a single invocation. It is the on-ramp skill for every new project.~~

**What it does (8 phases):**

1. **Analyze** — Scan the repository: language, package manager, existing structure,
   CI/CD config, licence, contributors.
2. **Generate SPEC.md** — Produce a project-specific framework specification with
   conservative, extensible defaults.
3. **Bootstrap Structure** — Create `agents/`, `skills/`, `tests/`, `docs/` layouts
   with role-appropriate templates.
4. **Housekeeping** — Update `.gitignore`, scaffold `README.md` sections, create
   `docs/` index files.
5. **Framework Bootstrap** — Copy or symlink core agent definitions and essential
   skills into the target repo.
6. **Compatibility Validation** — Check model harness (Claude, GPT-5, local),
   tool availability (git, python, bash, jq), API key presence (masked).
7. **TODO.md Initialization** — Bootstrap `TODO.md` with priority-ordered first
   delegations ready to queue.
8. **Documentation Generation** — Create `ONBOARDING.md`, `QUICK-START.md`,
   repo-specific `AGENTS.md`.

---

## When to Invoke

| Trigger | Who | Condition |
|---------|-----|-----------|
| New repository created | Orchestrator | No `.agentic-engineers/` marker file present |
| `/init` command | Any agent | User explicitly requests framework init |
| Onboarding ticket | Senior Engineer | DELEGATE references `repo-init` |
| CI bootstrap step | Automation | `make init` target in new repo Makefile |

---

## Usage

### Python API (preferred)

```python
from src.skills.repo_init.scripts.repo_init import RepoInitConfig, RepoInitializer
from pathlib import Path

cfg = RepoInitConfig(
    repo_root=Path("/path/to/target/repo"),
    project_name="my-api",
    project_description="REST API for widget management.",
    model_harness="claude",          # "claude" | "gpt5" | "local"
    framework_version="5.10",
    dry_run=False,
)

initializer = RepoInitializer()
result = initializer.run(cfg)
print(result)
# [SUCCESS] repo-init: my-api
#   phases completed: 8/8
#   files created: 34
#   warnings: 0
#   duration_ms: 1240
```

### Dry-run (validate only, no file writes)

```python
result = initializer.run(cfg, dry_run=True)
# Returns SUCCESS with planned deliverables, writes nothing to disk.
```

### CLI

```bash
python src/skills/repo-init/scripts/repo_init.py \
  --repo-root /path/to/target/repo \
  --project-name my-api \
  --model-harness claude

# Dry-run:
python src/skills/repo-init/scripts/repo_init.py \
  --repo-root /path/to/target/repo \
  --dry-run

# Skip specific phases (comma-separated):
python src/skills/repo-init/scripts/repo_init.py \
  --repo-root /path/to/target/repo \
  --skip-phases housekeeping,framework-bootstrap
```

---

## Configuration

| Parameter | Type | Required | Default | Notes |
|-----------|------|----------|---------|-------|
| `repo_root` | Path | ✅ | — | Absolute path to target repository |
| `project_name` | str | ❌ | inferred from `dirname` | Lowercase, hyphens OK |
| `project_description` | str | ❌ | `""` | Used in generated SPEC.md |
| `model_harness` | str | ❌ | `"claude"` | `"claude"` \| `"gpt5"` \| `"local"` |
| `framework_version` | str | ❌ | `"5.10"` | Pinned framework version |
| `dry_run` | bool | ❌ | `False` | Validate only, no writes |
| `skip_phases` | list[str] | ❌ | `[]` | Phase names to skip |
| `conservative_defaults` | bool | ❌ | `True` | Use low-effort, haiku defaults |
| `force_reinit` | bool | ❌ | `False` | Overwrite existing init marker |

---

## Initialization Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                      repo-init WORKFLOW                         │
└─────────────────────────────────────────────────────────────────┘

  START
    │
    ▼
┌───────────────────┐
│  Pre-flight check │  ← Is repo git-initialized? Is Python ≥ 3.8?
│  (guard clauses)  │    Is .agentic-engineers/ already present?
└───────┬───────────┘
        │ PASS
        ▼
┌───────────────────┐
│ Phase 1: ANALYZE  │  ← scan_languages(), detect_package_manager(),
│                   │    scan_ci_config(), read_existing_docs()
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│ Phase 2: SPEC.md  │  ← build_spec_context(analysis_result),
│  GENERATION       │    render_spec_template(), write SPEC.md
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│ Phase 3: BOOTSTRAP│  ← create agents/, skills/, tests/, docs/
│  STRUCTURE        │    write role-template stubs
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│ Phase 4:          │  ← patch .gitignore, scaffold README sections,
│  HOUSEKEEPING     │    create docs/index.md
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│ Phase 5: FRAMEWORK│  ← copy_core_agents(), copy_essential_skills(),
│  BOOTSTRAP        │    write .agentic-engineers/config.yaml
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│ Phase 6: COMPAT   │  ← check_model_harness(), check_tools(),
│  VALIDATION       │    check_api_keys() (masked), emit warnings
└───────┬───────────┘
        │  (warnings only — never blocks)
        ▼
┌───────────────────┐
│ Phase 7: TODO.md  │  ← build_initial_todos(analysis_result),
│  INITIALIZATION   │    write TODO.md with priority-ordered items
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│ Phase 8: DOCS     │  ← generate ONBOARDING.md, QUICK-START.md,
│  GENERATION       │    AGENTS.md (repo-specific)
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│  Write init       │  ← .agentic-engineers/INIT-COMPLETE.yaml
│  marker + summary │    (timestamp, phases, files_created, warnings)
└───────┬───────────┘
        │
        ▼
  RETURN InitResult
```

---

## Phase Details

### Phase 1: Repository Analysis

**Script:** `scripts/analyze_repo.py`

```
Inputs:  repo_root (Path)
Outputs: AnalysisResult dataclass
```

Detection logic:

| Signal | File(s) Checked | Output Field |
|--------|-----------------|--------------|
| Primary language | `*.py`, `*.ts`, `*.go`, `*.rs`, `*.java` (file count) | `primary_language` |
| Package manager | `package.json`, `requirements.txt`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`, `pyproject.toml`, `Gemfile` | `package_manager` |
| Test framework | `pytest.ini`, `jest.config.*`, `go test`, `cargo test` | `test_framework` |
| CI/CD | `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/` | `ci_provider` |
| Existing docs | `README.md`, `docs/`, `CHANGELOG.md` | `has_readme`, `has_docs` |
| License | `LICENSE`, `LICENSE.md`, `COPYING` | `license` |
| Framework | `django`, `flask`, `fastapi`, `express`, `nextjs`, `gin` | `framework` |
| Monorepo | `packages/`, `apps/`, `services/`, `workspaces` in package.json | `is_monorepo` |

```python
@dataclass
class AnalysisResult:
    repo_root: Path
    project_name: str
    primary_language: str           # "python" | "typescript" | "go" | ...
    secondary_languages: List[str]
    package_manager: str            # "pip" | "npm" | "cargo" | "maven" | ...
    test_framework: str             # "pytest" | "jest" | "go-test" | "unknown"
    ci_provider: str                # "github-actions" | "gitlab-ci" | "jenkins" | "none"
    framework: str                  # "django" | "fastapi" | "express" | "unknown"
    is_monorepo: bool
    has_readme: bool
    has_docs: bool
    license: str                    # "MIT" | "Apache-2.0" | "proprietary" | "unknown"
    git_remote: str                 # First origin remote URL
    contributor_count: int          # From git log --format='%ae' | sort -u | wc -l
    total_files: int
    existing_spec: bool             # SPEC.md already present
    existing_agents: bool           # agents/ already present
```

### Phase 2: SPEC.md Generation

**Script:** `scripts/generate_spec.py`  
**Template:** `assets/spec-template.md`

Generates a project-specific SPEC.md with:
- Project identity (name, description, language, framework)
- Agent team configuration (which agents are enabled, model assignments)
- Effort defaults (conservative: `low` for engineer, `medium` for senior)
- Tool availability matrix (pre-filled from Phase 1 analysis)
- Quality gate thresholds (85% test coverage default)
- Delegation protocol headers

**Conservative defaults applied:**
```yaml
# Generated .agentic-engineers/config.yaml
framework_version: "5.10"
model_harness: claude          # or gpt5 / local
default_engineer_model: claude-haiku-4.5
default_senior_model: claude-sonnet-4.6
default_lead_model: claude-sonnet-4.6
default_principal_model: claude-opus-4.7
default_effort: low
quality_gate:
  min_coverage: 85
  require_handback: true
  require_spec_compliance: true
```

### Phase 3: Directory Structure Bootstrap

**Script:** `scripts/bootstrap_structure.py`

Creates this layout in the target repo:

```
{repo_root}/
├── .agentic-engineers/
│   ├── config.yaml              # Framework config
│   ├── INIT-COMPLETE.yaml       # Written last (init marker)
│   └── model-assignments.yaml   # Per-role model config
├── agents/
│   ├── README.md                # Agent catalog
│   ├── engineer.md              # Engineer role definition
│   ├── senior-engineer.md       # Senior role definition
│   ├── lead-engineer.md         # Lead role definition
│   └── orchestrator.md          # Orchestrator definition
├── skills/
│   ├── README.md                # Skills index
│   └── usage-tracking/          # Symlink or copy from framework
│       └── SKILL.md
├── tests/
│   ├── conftest.py              # Pytest configuration
│   ├── README.md                # Testing guide
│   └── test_framework_init.py  # Smoke tests for this init
├── docs/
│   ├── SPEC.md                  # Generated project spec
│   ├── AGENTS.md                # Repo-specific agent config
│   ├── ONBOARDING.md            # New contributor guide
│   ├── QUICK-START.md           # Quick reference
│   └── index.md                 # Docs index
├── artifacts/
│   └── queue/                   # Delegation queue (gitignored)
│       ├── incoming/
│       └── done/
├── TODO.md                      # Bootstrapped with initial delegations
└── Makefile                     # (if not exists) or patch existing
```

### Phase 4: Housekeeping

**Script:** `scripts/housekeeping.py`

**`.gitignore` additions:**
```
# agentic-engineers framework
.agentic-engineers/session-*.log
~/.agentic-engineers/
artifacts/spans/
data/metrics/*.jsonl
__pycache__/
*.pyc
.pytest_cache/
```

**`README.md` scaffold:**
If no README.md exists → create from template.
If README.md exists → append `## Agentic Engineers` section at end.

**Section appended:**
```markdown
## Agentic Engineers

This repo uses the [agentic-engineers](https://github.com/{your-org}/agentic-engineers)
framework for AI-assisted development.

- See [docs/ONBOARDING.md](docs/ONBOARDING.md) to get started.
- See [docs/AGENTS.md](docs/AGENTS.md) for agent team configuration.
- See [TODO.md](TODO.md) for current task queue.
```

### Phase 5: Framework Bootstrap

**Script:** `scripts/framework_bootstrap.py`

Copies (or symlinks with `--symlink` flag) core artifacts from the installed
framework into the target repo:

| Source | Destination | Method |
|--------|-------------|--------|
| `src/agents/engineer.md` | `agents/engineer.md` | copy |
| `src/agents/senior-engineer.md` | `agents/senior-engineer.md` | copy |
| `src/agents/lead-engineer.md` | `agents/lead-engineer.md` | copy |
| `src/agents/orchestrator.md` | `agents/orchestrator.md` | copy |
| `src/skills/usage-tracking/` | `skills/usage-tracking/` | copy |
| `src/config/models.yaml` | `.agentic-engineers/models.yaml` | copy |

**Framework location detection order:**
1. `AGENTIC_ENGINEERS_HOME` environment variable
2. `~/.agentic-engineers/` (global install)
3. Adjacent directory `../agentic-engineers/` (monorepo co-location)
4. PyPI package `agentic_engineers` (future)

### Phase 6: Compatibility Validation

**Script:** `scripts/validate_compatibility.py`

**Tool availability checks (hard requirements):**

| Tool | Check | Failure Action |
|------|-------|----------------|
| `git` | `git --version` | ERROR — abort |
| `python3` | `python3 --version ≥ 3.8` | ERROR — abort |
| `bash` | `bash --version` | WARNING — downgrade |
| `jq` | `jq --version` | WARNING — skip JSON features |
| `curl` / `wget` | either present | WARNING |

**Model harness checks:**

| Harness | Check | How |
|---------|-------|-----|
| Claude | `ANTHROPIC_API_KEY` set | `os.environ` (key masked in output) |
| GPT-5 | `OPENAI_API_KEY` set | `os.environ` (key masked) |
| Local | `OLLAMA_HOST` or `lm-studio` process | env + process scan |
| GitHub Copilot | `.copilot/` dir OR `GH_TOKEN` | filesystem + env |

**Output: CompatibilityResult**
```python
@dataclass
class CompatibilityResult:
    harness: str
    hard_failures: List[str]    # Abort init if non-empty
    warnings: List[str]         # Emit but continue
    tool_matrix: Dict[str, bool]
    api_key_present: bool       # NOT the key value — just bool
    recommended_adjustments: List[str]
```

**Compatibility matrix (by harness):**

| Feature | Claude | GPT-5 | Local (Ollama/LM-Studio) |
|---------|--------|-------|--------------------------|
| Tool use | ✅ Full | ✅ Full | ⚠️ Model-dependent |
| Long context | ✅ 200k | ✅ 128k | ⚠️ Varies |
| Structured output | ✅ | ✅ | ⚠️ |
| Function calling | ✅ | ✅ | ⚠️ |
| Streaming | ✅ | ✅ | ✅ |
| Cost | 💰 | 💰 | 🆓 |
| Privacy | Cloud | Cloud | ✅ Local |

**Adjustments applied for local models:**
- `default_engineer_model` → `ollama/llama3.2` (configurable)
- `default_effort` → `medium` (local models often slower)
- Quality gate coverage → `70%` (conservative for local)
- Disable `require_spec_compliance` (may exceed context)

### Phase 7: TODO.md Initialization

**Script:** `scripts/init_todo.py`

Bootstraps `TODO.md` with an initial task queue derived from the analysis:

```markdown
# TODO: {project_name}

**Last Updated:** {date}
**Initialized by:** repo-init skill v1.0
**Framework Version:** {framework_version}

---

## 🔴 Priority (Must Do First)

- [ ] **INIT-001:** Review and customize generated SPEC.md
  - Path: `docs/SPEC.md`
  - Action: Verify agent assignments, model tiers, quality gate thresholds
  - Owner: Principal Engineer
  - Added: {date}

- [ ] **INIT-002:** Run initial compatibility validation
  - Command: `python skills/repo-init/scripts/validate_compatibility.py --report`
  - Owner: Senior Engineer
  - Added: {date}

## 🟡 Standard (Active Backlog)

- [ ] **INIT-003:** Write first failing tests (TDD RED-phase)
  - Reference: `docs/QUICK-START.md#tdd-workflow`
  - Owner: Engineer
  - Added: {date}

- [ ] **INIT-004:** Configure CI/CD integration
  - Reference: `docs/ONBOARDING.md#cicd`
  - Owner: Engineer
  - Added: {date}

## 🔮 Future (Not Yet Scheduled)

- [ ] **INIT-005:** Add project-specific agent customizations
  - Reference: `agents/README.md`
  - Added: {date}
```

**Conditional items added by analysis:**

| Analysis Finding | Additional TODO Item |
|------------------|----------------------|
| No existing tests | `INIT-T01`: Create test suite foundation |
| No CI/CD | `INIT-C01`: Add GitHub Actions / GitLab CI workflow |
| Monorepo detected | `INIT-M01`: Configure per-package agent scoping |
| No .gitignore | `INIT-G01`: Review and extend generated .gitignore |
| Legacy codebase (>1000 files) | `INIT-L01`: Run architecture audit before agent work |
| Multiple contributors | `INIT-X01`: Share ONBOARDING.md with team |

### Phase 8: Documentation Generation

**Script:** `scripts/generate_docs.py`

**`docs/ONBOARDING.md`** — New contributor guide:
- Framework overview and philosophy
- How to submit a task via delegation queue
- DELEGATE/HANDBACK protocol quickref
- Agent team roster (from SPEC.md)
- Links to key docs

**`docs/QUICK-START.md`** — 5-minute reference:
- First delegation example
- TDD workflow (RED → GREEN → REFACTOR)
- Common DELEGATE block templates
- Queue commands

**`docs/AGENTS.md`** — Repo-specific agent config:
- Which agents are enabled for this repo
- Model assignments per role
- Effort defaults
- Escalation paths

---

## Output: InitResult

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

@dataclass
class InitResult:
    status: str                     # "SUCCESS" | "FAILED" | "PARTIAL" | "DRY_RUN"
    project_name: str
    phases_completed: List[str]     # Phase names that completed
    phases_skipped: List[str]       # Phase names skipped by --skip-phases
    phases_failed: List[str]        # Phase names that failed
    files_created: List[Path]       # All files written to disk
    files_modified: List[Path]      # Existing files that were patched
    warnings: List[str]
    errors: List[str]
    compatibility: "CompatibilityResult"
    span: Dict                      # {"duration_ms": N, "files_created": N}
```

---

## Integration Points

### With agent-creator

`repo-init` does **not** duplicate agent-creator's scaffolding logic.
Instead, for each agent stub in `agents/`, repo-init calls:

```python
from src.skills.agent_creator import AgentConfig, AgentCreator

creator = AgentCreator(output_root=target_repo / "skills")
for role in enabled_roles:
    cfg = AgentConfig(name=f"{project_name}-{role}", role=role, ...)
    creator.create(cfg, dry_run=dry_run)
```

### With spec-management

repo-init generates the **initial** SPEC.md. All subsequent changes to SPEC.md
MUST go through the `spec-management` skill (not repo-init).
repo-init writes a header comment to the generated SPEC.md:

```markdown
<!-- MANAGED BY spec-management SKILL — do not edit directly -->
<!-- Initial version generated by repo-init v1.0 on {date} -->
```

### With usage-tracking

After Phase 5, repo-init configures the `usage-tracking` skill by writing
`skills/usage-tracking/config.yaml` with project-specific thresholds.

### With the Orchestrator

repo-init is invoked by the Orchestrator in response to a DELEGATE block like:

```yaml
DELEGATE:
  task: repo-init
  skill: repo-init
  target: /path/to/new/repo
  config:
    project_name: my-api
    model_harness: claude
    dry_run: false
  effort: medium
  model: claude-sonnet-4.6
```

---

## File Templates

See:
- [`assets/spec-template.md`](assets/spec-template.md) — SPEC.md generation template
- [`assets/agents-md-template.md`](assets/agents-md-template.md) — AGENTS.md template
- [`assets/todo-template.md`](assets/todo-template.md) — TODO.md template
- [`assets/gitignore-additions.txt`](assets/gitignore-additions.txt) — .gitignore lines

---

## Reference Documentation

- [`references/WORKFLOW.md`](references/WORKFLOW.md) — Detailed workflow diagram
- [`references/SPEC-TEMPLATE.md`](references/SPEC-TEMPLATE.md) — SPEC.md authoring guide
- [`references/DIRECTORY-STRUCTURE.md`](references/DIRECTORY-STRUCTURE.md) — Directory spec
- [`references/COMPATIBILITY-MATRIX.md`](references/COMPATIBILITY-MATRIX.md) — Compat checklist

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/repo_init.py` | Main orchestrator — runs all 8 phases in order |
| `scripts/analyze_repo.py` | Phase 1: Repository analysis |
| `scripts/generate_spec.py` | Phase 2: SPEC.md generation |
| `scripts/bootstrap_structure.py` | Phase 3: Directory structure creation |
| `scripts/housekeeping.py` | Phase 4: .gitignore, README.md patching |
| `scripts/framework_bootstrap.py` | Phase 5: Core agents + skills copy |
| `scripts/validate_compatibility.py` | Phase 6: Harness + tool checks |
| `scripts/init_todo.py` | Phase 7: TODO.md initialization |
| `scripts/generate_docs.py` | Phase 8: ONBOARDING, QUICK-START, AGENTS.md |

---

## Tests

```bash
python3 -m pytest tests/test_repo_init.py -v
# Expected: 80+ tests, 90%+ coverage
```

Test categories:
- `test_analyze_*` — Repository analysis detection logic
- `test_generate_spec_*` — SPEC.md template rendering
- `test_bootstrap_*` — Directory structure creation
- `test_housekeeping_*` — .gitignore and README.md patching
- `test_framework_bootstrap_*` — Core artifact copying
- `test_validate_compat_*` — Compatibility checks
- `test_init_todo_*` — TODO.md bootstrap
- `test_generate_docs_*` — Documentation generation
- `test_dry_run_*` — No writes in dry-run mode
- `test_idempotent_*` — Safe to run twice (no duplicates)

---

## Idempotency

repo-init is **idempotent by default**:

- Existing files are **not overwritten** unless `--force-reinit` is passed.
- The init marker `.agentic-engineers/INIT-COMPLETE.yaml` prevents double-init.
- All file writes are checked with `Path.exists()` before writing.
- `.gitignore` additions are deduplicated (no duplicate lines).

---

## Compliance Checklist

- [ ] `SKILL.md` has valid YAML frontmatter
- [ ] `name` field matches directory name (`repo-init`)
- [ ] All scripts in `scripts/` are modular (one responsibility per script)
- [ ] `assets/` templates exist and are referenced by relative paths
- [ ] `references/` docs exist and are under 500 lines each
- [ ] dry-run mode returns SUCCESS without any file writes
- [ ] init marker written only on full SUCCESS
- [ ] Integration with agent-creator (no duplicate scaffolding)
- [ ] Integration with spec-management (SPEC.md header comment)
- [ ] Tests exist with 90%+ coverage target
