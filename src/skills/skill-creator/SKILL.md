---
name: skill-creator
description: Create new agentic-engineers skills following the agentskills.io specification. Use when designing new automation agents, task handlers, or operational tools for the agentic-engineers platform. Handles directory structure, SKILL.md frontmatter, script templates, and documentation scaffolding.
license: Proprietary
compatibility: Designed for agentic-engineers framework
metadata:
  author: agentic-engineers
  version: "1.0"
  category: orchestration
  role: orchestrator
---

## Overview

Create new agentic-engineers skills that comply with the [agentskills.io specification](https://agentskills.io/specification).

## Directory Structure

Each skill must follow this layout:

```
skill-name/
├── SKILL.md                 # Required: metadata + instructions
├── scripts/                 # Optional: executable code (isolated, modular)
│   ├── script-1.py
│   └── script-2.sh
├── references/              # Optional: detailed documentation
│   ├── REFERENCE.md
│   └── setup.md
└── assets/                  # Optional: templates, resources
    └── template.json
```

## Creating a New Skill

### 1. Directory Setup

```bash
mkdir -p agentic-engineers/skills/skill-name/{scripts,references,assets}
```

### 2. SKILL.md Frontmatter

Required fields:
- `name` (lowercase, hyphens only, 1-64 chars)
- `description` (1-1024 chars, include when/why to use)

Optional fields:
- `license` — License name or file reference
- `compatibility` — Environment/product requirements
- `metadata` — Key-value pairs (author, version, category, role)
- `allowed-tools` — Pre-approved tools (experimental)

**Template:**

```markdown
---
name: skill-name
description: Brief description of what this skill does and when to use it.
license: Proprietary
metadata:
  author: agentic-engineers
  version: "1.0"
  category: orchestration  # or: patterns, monitoring, optimization, etc.
  role: orchestrator       # or: engineer, senior-engineer, lead-engineer, etc.
---

## Overview
[Your skill instructions]
```

### 3. Script Organization

Each script in `scripts/`:
- Should be self-contained or document dependencies clearly
- Include helpful error messages
- Handle edge cases gracefully
- Be modular (one responsibility per script)

**Example:**
```bash
scripts/
├── analyze-metrics.py
├── generate-report.sh
└── validate-config.py
```

### 4. Documentation Structure

In `references/`:
- `REFERENCE.md` — Technical details, API docs
- Domain-specific files (`setup.md`, `config.md`, etc.)

Keep files focused and under 500 lines for progressive disclosure.

### 5. File References

Within `SKILL.md`, reference files with relative paths:

```markdown
See [detailed reference](references/REFERENCE.md) for setup.

Run: `scripts/analyze-metrics.py`
```

## Naming Conventions

**Skill names (directory + SKILL.md name field):**
- Lowercase alphanumeric + hyphens only
- No leading/trailing hyphens
- No consecutive hyphens
- Max 64 characters

**Valid examples:**
- `tokenadvisor`
- `ab-testing-monitor`

**Invalid examples:**
- `TokenAdvisor` (uppercase)
- `test--monitor` (consecutive hyphens)

## Categories

Organize skills by category in metadata:

- **orchestration** — Automation agents, scheduling, coordination
- **monitoring** — Metrics analysis, dashboards, alerting
- **optimization** — Cost-quality tradeoffs, A/B testing, routing
- **patterns** — Reusable code patterns (Lambda, CDK, API clients)
- **security** — Security reviews, threat modeling, vulnerability assessment
- **testing** — E2E testing, quality gates, test coverage
- **shared** — Cross-cutting libraries (git, CDK, SigV4)
- **architecture** — Design patterns, decision documentation
- **review** — Code review standards, quality checks
- **roles** — Role-specific guidance (Engineer, Senior, Lead, Principal)

## Compliance Checklist

- [ ] Directory name matches `SKILL.md` `name` field
- [ ] `SKILL.md` has valid YAML frontmatter
- [ ] `description` field is 1-1024 characters
- [ ] `name` field is lowercase alphanumeric + hyphens only
- [ ] Scripts in `scripts/` are modular and self-contained
- [ ] File references use relative paths (1 level deep)
- [ ] Body content under 500 lines (move details to references/)
- [ ] All referenced files exist and are accessible

## Validation

Validate your skill:

```bash
skills-ref validate ./agentic-engineers/skills/skill-name
```

This checks frontmatter format, naming conventions, and file references.

## Examples

See existing skills in `agentic-engineers/skills/`:
- `tokenadvisor/` — Daily metrics analysis agent
- `model-engineer/` — Cost-quality optimization agent
- `ab-testing/` — Experiment orchestration
