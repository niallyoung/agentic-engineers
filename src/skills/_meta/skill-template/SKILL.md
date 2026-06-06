---
# ============================================================
# SKILL.md — Canonical Template for agentic-engineers Skills
# Copy this file into src/skills/<skill-name>/SKILL.md and
# replace all <PLACEHOLDER> values before shipping.
# See docs/guides/SKILL-QUICKSTART.md for the 5-step guide.
# ============================================================
name: <skill-name>           # REQUIRED — kebab-case, matches directory name
description: >               # REQUIRED — one-line description shown in harness listings
  <Brief description of what this skill does and when to invoke it.
  Should be ≤200 characters for clean harness rendering.>
license: Proprietary         # REQUIRED — do not change
compatibility: agentic-engineers framework v5.10+. Requires Python 3.11+  # REQUIRED
metadata:
  author: agentic-engineers   # REQUIRED — do not change
  version: "1.0"              # REQUIRED — increment on breaking changes
  category: <category>        # REQUIRED — see Allowed Categories below
  role: <role>                # REQUIRED — see Allowed Roles below
  model: <model>              # REQUIRED — see Allowed Models below
  effort: <effort>            # REQUIRED — low | medium | high
  thinking: false             # OPTIONAL — default false; set true for reasoning-heavy tasks
  dependencies: []            # OPTIONAL — list of other skill names this skill requires
  trigger: on-demand          # OPTIONAL — on-demand | scheduled | pre-merge | real-time
  tdd_phase: RED              # OPTIONAL — RED | GREEN | REFACTOR; tracks TDD progress
---

# <skill-name>

<!-- ============================================================
     REQUIRED SECTIONS (must appear in every SKILL.md):
     Overview, Invocation, Integration, Configuration, Tests
     OPTIONAL SECTIONS (include when applicable):
     Scripts, Examples, Metrics, Delegate/Handback Protocol
     ============================================================ -->

## Overview

<!-- REQUIRED: 2–5 sentences explaining what this skill does, why it exists,
     and the key problem it solves. -->

**<skill-name>** <brief explanation of purpose and value>.

**What it does:**

1. **<Step 1 name>** — <description>
2. **<Step 2 name>** — <description>
3. **<Step 3 name>** — <description>

**Why it matters:**

- **<Benefit 1>** — <explanation>
- **<Benefit 2>** — <explanation>

---

## Invocation

<!-- REQUIRED: How to run this skill. Include at minimum one of:
     Python API, CLI, or automated trigger. -->

### Python API (preferred)

```python
from src.skills.<skill_name> import <SkillClass>

# Initialize and run
skill = <SkillClass>()
result = skill.run(<args>)
print(result)
```

### CLI

```bash
python src/skills/<skill-name>/scripts/<skill_name>.py \
  --<arg1> <value1> \
  --<arg2> <value2>
```

### Automated Trigger

<!-- If the skill runs on a schedule or as a CI gate, describe it here. -->

```yaml
# In .github/workflows/ci.yml:
- name: <Skill Name>
  run: python src/skills/<skill-name>/scripts/<skill_name>.py
```

---

## Integration

<!-- REQUIRED: How does this skill fit into the broader framework?
     What does it consume? What does it produce? Who calls it? -->

**Input:** <What the skill consumes — file paths, environment vars, CLI args>
**Output:** <What the skill produces — report, JSON, exit code, side-effects>
**Used by:** <Which agents or skills call this skill>
**Calls:** <Which skills or tools this skill depends on>

---

## Configuration

<!-- REQUIRED: Document all parameters/settings. Use this table format. -->

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `<param1>` | str | ✅ | — | <description> |
| `<param2>` | int | ❌ | `10` | <description> |
| `<param3>` | bool | ❌ | `false` | <description> |

### Allowed Categories

`orchestration` · `validation` · `monitoring` · `optimization` · `observability` ·
`scaffolding` · `integration` · `queue` · `metrics` · `maintenance` · `hygiene` · `management` · `security`

### Allowed Roles

`engineer` · `senior-engineer` · `lead-engineer` · `principal-engineer` ·
`security-engineer` · `quality-engineer` · `orchestrator`

### Allowed Models

| Tier | Model | Recommended for |
|------|-------|-----------------|
| Haiku (fast/cheap) | `claude-haiku-4.5` | engineer, orchestrator |
| Sonnet (balanced) | `claude-sonnet-4.5`, `claude-sonnet-4.6` | senior, lead, quality |
| Opus (powerful) | `claude-opus-4.7`, `claude-opus-4.8` | principal, security |
| OpenAI | `gpt-4o-mini`, `gpt-4o`, `gpt-5-mini` | special cases |
| Gemini | `gemini-3.5-flash`, `gemini-3.1-pro-preview` | special cases |

---

## Tests

<!-- REQUIRED: How to run the test suite for this skill. -->

```bash
python -m pytest src/skills/<skill-name>/tests/ -v
# Expected: N tests, M% coverage
```

---

## Scripts

<!-- OPTIONAL: List the scripts in scripts/ with one-line purpose descriptions. -->

- `scripts/<skill_name>.py` — Core implementation entry point

---

## DELEGATE / HANDBACK Protocol

<!-- OPTIONAL: Include if this skill can be delegated via the protocol. -->

### Example DELEGATE

```yaml
---
handoff_type: DELEGATE
task_id: <YYYY-MM-DD-skill-name-task>
timestamp: <ISO8601>
role: <role>
model: <model>
effort: <effort>
scope: >
  <What needs to be done — 1–3 sentences>
context:
  - <key context item 1>
  - <key context item 2>
---
```

### Example HANDBACK

```yaml
---
handoff_type: HANDBACK
task_id: <YYYY-MM-DD-skill-name-task>
timestamp: <ISO8601>
status: success
deliverables:
  - <file or artifact produced>
quality_score: 95
confidence: 0.95
tokens:
  used: <N>
  efficiency: 0.9
notes: "<What was done and any notable findings>"
---
```
