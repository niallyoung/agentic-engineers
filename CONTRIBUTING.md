# Contributing to agentic-engineers

> **Architecture:** Queue-based DELEGATE/HANDBACK multi-agent framework.  
> **8 roles:** Orchestrator, Engineer, Model Engineer, Quality Engineer, Lead Engineer, Senior Engineer, Principal Engineer, Security Engineer.

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/niallyoung/agentic-engineers.git
cd agentic-engineers

# 2. Install to all harnesses
make install

# 3. Verify the installation
make verify

# 4. Run the test suite
python3 -m pytest tests/ -q
```

---

## Development Workflow

### Standard Change Flow

```
1. Create a feature branch
   git checkout -b feature/your-change

2. Make your changes (agents, skills, or framework code)

3. Run local quality gate
   make lint && python3 -m pytest tests/ -q && make verify

4. Validate agents and skills
   python3 renderer/validate_agents.py
   python3 renderer/validate_skills.py

5. Render and install (if you changed agent/skill definitions)
   make render-all
   make install

6. Commit with conventional commits
   git commit -m "feat(skills): add new skill for X"
   git commit -m "fix(agents): correct routing rule in orchestrator"
   git commit -m "docs(src): update SKILLS.md with new skill"

7. Push and open a PR
   git push origin feature/your-change
   gh pr create --draft --title "feat: ..." --body "..."

8. CI passes → request review → merge
```

### Conventional Commit Prefixes

| Prefix | When to use |
|--------|-------------|
| `feat` | New skill, agent, or feature |
| `fix` | Bug fix in agent logic, rendering, or framework |
| `docs` | Documentation changes only (no logic changes) |
| `refactor` | Code change that doesn't add features or fix bugs |
| `test` | Adding or updating tests |
| `chore` | Dependency updates, build config, CI config |
| `perf` | Performance improvement |

### Commit Scope (optional but encouraged)

| Scope | Meaning |
|-------|---------|
| `agents` | Changes to `src/agents/` |
| `skills` | Changes to `src/skills/` |
| `renderer` | Changes to `renderer/` |
| `src` | Changes to `src/*.md` protocol documents |
| `tests` | Changes to `tests/` |
| `ci` | Changes to CI/CD pipeline |
| `deps` | Dependency updates |

Example: `feat(skills): add spec-validator skill for QE role`

---

## Adding a New Agent

Agents live in `src/agents/<name>-agent.md`.

### Step 1: Create the agent file

```bash
cp src/agents/engineer-agent.md src/agents/new-role-agent.md
```

### Step 2: Edit the YAML frontmatter

```yaml
---
name: new-role           # lowercase-hyphenated; must be unique
description: One sentence — what this agent does and when to use it
model: claude-sonnet-4-6 # choose from: claude-haiku-4-5 | claude-sonnet-4-6 | claude-opus-4-6 | claude-opus-4-7
---
```

### Step 3: Write the agent body

Required sections:
- **Purpose** — what this role does and does not do
- **Routing Rules** — when the Orchestrator should route here
- **Responsibilities** — bullet list of what this agent handles
- **Escalation** — when to escalate and to whom
- **HANDBACK Format** — what the agent returns on completion

### Step 4: Register the agent

Add a row to `src/AGENTS.md` Agent Roster table.  
Add a row to `src/SKILLS.md` Role Skill Definitions table.

### Step 5: Validate and test

```bash
python3 renderer/validate_agents.py
python3 -m pytest tests/ -k "test_agent" -q
```

---

## Adding a New Skill

Skills live in `src/skills/<category>/`.

### Skill Types

| Type | Location | When to use |
|------|----------|-------------|
| Single-file skill | `src/skills/<skill-name>.md` | Simple, self-contained skill |
| Directory skill | `src/skills/<skill-name>/SKILL.md` | Skill with supporting references |
| Category skill | `src/skills/<category>/<skill-name>.md` | Skill that belongs to a logical group |

### Step 1: Create the skill file

For a new skill in an existing category:
```bash
# e.g., a new monitoring skill:
touch src/skills/monitoring/new-skill.md
```

For a new standalone skill:
```bash
mkdir -p src/skills/new-skill
touch src/skills/new-skill/SKILL.md
```

### Step 2: Add YAML frontmatter

```yaml
---
name: new-skill-name
description: One sentence — what this skill enables the agent to do
version: 1.0.0
roles:
  - engineer
  - senior-engineer
tags:
  - implementation
  - patterns
---
```

### Step 3: Write the skill content

Required sections:
- **Purpose** — what capability this skill gives the agent
- **When to Use** — concrete trigger conditions
- **Instructions** — step-by-step guidance
- **Examples** — at least one concrete example
- **Acceptance Criteria** — how to verify the skill was applied correctly

### Step 4: Register the skill

Add a row to the appropriate category table in `src/SKILLS.md`.  
Update the role's "Skills by Role" section if this skill is primary for a role.

### Step 5: Validate

```bash
python3 renderer/validate_skills.py
```

---

## Adding a New Harness

Harness configurations live in `renderer/`.

| Harness | Config location | Install target |
|---------|----------------|----------------|
| Claude | `renderer/scripts/render-claude.sh` | `make install-claude` |
| Copilot CLI | `renderer/scripts/render-copilot.sh` | `make install-copilot` |
| OpenCode | `renderer/scripts/render-opencode.sh` | `make install-opencode` |
| π.dev | `renderer/scripts/render-pi-dev.py` | `make install-pi` |

To add a new harness:
1. Create `renderer/scripts/render-<harness>.sh` (or `.py`)
2. Add `install-<harness>`, `render-<harness>`, `uninstall-<harness>`, and `status-<harness>` targets to the Makefile
3. Add it to the `install` and `uninstall-all` aggregate targets
4. Add a row to the `status` target output
5. Write tests in `tests/test_renderer_<harness>.py`

---

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make help` | Show all targets |
| `make install` | Install to all 4 harnesses |
| `make install-<harness>` | Install to a specific harness |
| `make render-all` | Generate dist/ from source |
| `make render-<harness>` | Render for a specific harness |
| `make verify` | Full framework verification + tests |
| `make validate-opencode` | Validate OpenCode config |
| `make status` | Show installation status |
| `make clean` | Remove build artifacts |

---

## Validation

### Agent Validator

```bash
python3 renderer/validate_agents.py [--strict] [--agents-dir src/agents]
```

Checks:
- YAML frontmatter present and valid on all agent files
- Required fields: `name`, `description`, `model`
- Model value is one of the known models
- Agent name matches filename convention
- Agent referenced in `src/AGENTS.md`

### Skill Validator

```bash
python3 renderer/validate_skills.py [--strict] [--skills-dir src/skills]
```

Checks:
- All skill files have YAML frontmatter
- Required fields: `name`, `description`
- All skills referenced in `src/SKILLS.md` exist on disk
- All skills on disk are registered in `src/SKILLS.md`
- Roles referenced in skill frontmatter exist in agent roster

---

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -q

# Run with coverage
python3 -m pytest tests/ --cov=src --cov-report=term-missing -q

# Run a specific test file
python3 -m pytest tests/test_renderer.py -v

# Run tests matching a keyword
python3 -m pytest tests/ -k "agent" -q
```

Test files mirror the source structure:
```
tests/
  test_agents.py          ← agent definition tests
  test_skills.py          ← skill completeness tests  
  test_renderer.py        ← renderer pipeline tests
  test_orchestration/     ← queue + orchestration tests
```

---

## Code Style

### Python
- Follow PEP 8 (enforced by `make lint`)
- Type hints on all function signatures
- Docstrings on all public functions
- Use `pathlib.Path` instead of `os.path`

### Markdown
- ATX-style headings (`##`, not underlines)
- Tables for structured data
- Code blocks for any shell commands or YAML
- No trailing whitespace

### YAML
- 2-space indent
- Quoted strings for values with special characters
- Keys in `snake_case`

---

## Pull Request Guidelines

1. **Title:** Use conventional commit format (`feat(scope): description`)
2. **Body:** Include what changed, why, and how to verify
3. **Size:** Keep PRs focused — one logical change per PR
4. **Tests:** All new code must have tests
5. **Docs:** Update `src/SKILLS.md` or `src/AGENTS.md` if adding/changing a skill or agent
6. **CI:** All checks must pass before requesting review

### PR Template

```markdown
## What
[Brief description of the change]

## Why
[Why this change is needed / what problem it solves]

## How to Verify
1. [Step 1]
2. [Step 2]

## Checklist
- [ ] Tests added / updated
- [ ] `make verify` passes
- [ ] `src/SKILLS.md` updated (if skill added/changed)
- [ ] `src/AGENTS.md` updated (if agent added/changed)
- [ ] Conventional commit message
```

---

## Project Structure

```
agentic-engineers/
├── src/
│   ├── AGENTS.md           ← Agent roster + handover packet spec
│   ├── DECISION-MAKING.md  ← Decision rules + escalation tree
│   ├── SKILLS.md           ← Complete skill matrix
│   ├── CLI-PERMISSIONS.md  ← Tool access control by role
│   ├── TOKEN_METRICS.md    ← Cost tracking specification
│   ├── TODO.md.template    ← Task tracking format
│   ├── agents/             ← Agent definition files
│   │   ├── orchestrator-agent.md
│   │   ├── engineer-agent.md
│   │   └── ...
│   └── skills/             ← Skill definitions (40+ skills)
│       ├── orchestration/
│       ├── monitoring/
│       ├── optimization/
│       └── ...
├── renderer/               ← Rendering pipeline
│   ├── validate_agents.py  ← Agent validator
│   ├── validate_skills.py  ← Skill validator
│   └── scripts/            ← Harness-specific render scripts
├── tests/                  ← Test suite
├── CONTRIBUTING.md         ← This file
├── Makefile                ← Build and install targets
├── README.md               ← Project overview
└── TODO.md                 ← Current task list (gitignored)
```
