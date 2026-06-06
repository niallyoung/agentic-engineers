# Creating a New Skill in 5 Steps

> **Quick-start guide for Phase 5.1+ skill authoring.**  
> Prerequisites: `make install` complete, working in a feature branch.

---

## Overview

A **skill** is a reusable, testable capability packaged under `src/skills/<skill-name>/`.
Every skill must:

1. Have a `SKILL.md` with complete frontmatter
2. Expose a Python API via `__init__.py`
3. Contain implementation logic in `scripts/<skill_name>.py`
4. Have tests in `tests/test_<skill_name>.py`
5. Be registered in `config/FRAMEWORK-MANIFEST.yaml`

---

## Step 1 — Copy the Template

```bash
# From the repository root
SKILL=my-new-skill

cp -r src/skills/_meta/skill-template src/skills/$SKILL

# Rename the placeholder script and test files
mv src/skills/$SKILL/scripts/skill_name.py  src/skills/$SKILL/scripts/${SKILL//-/_}.py
mv src/skills/$SKILL/tests/test_skill_name.py src/skills/$SKILL/tests/test_${SKILL//-/_}.py
```

You should now have:

```
src/skills/my-new-skill/
├── SKILL.md
├── __init__.py
├── scripts/
│   ├── __init__.py
│   └── my_new_skill.py
└── tests/
    ├── __init__.py
    └── test_my_new_skill.py
```

---

## Step 2 — Fill in SKILL.md Frontmatter

Open `SKILL.md` and replace every `<PLACEHOLDER>` value.

### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `name` | Skill name (kebab-case, matches directory) | `my-new-skill` |
| `description` | ≤200 char summary shown in harness listings | `"Detects drift in config files."` |
| `license` | Always `Proprietary` | `Proprietary` |
| `compatibility` | Framework version + Python requirement | `agentic-engineers framework v5.10+. Requires Python 3.11+` |
| `metadata.author` | Always `agentic-engineers` | `agentic-engineers` |
| `metadata.version` | Semantic version string | `"1.0"` |
| `metadata.category` | Skill category | `validation` |
| `metadata.role` | Which agent role invokes this skill | `engineer` |
| `metadata.model` | Default model for this skill | `claude-haiku-4.5` |
| `metadata.effort` | Complexity level | `low` |

### Optional Fields

| Field | Default | Notes |
|-------|---------|-------|
| `metadata.thinking` | `false` | Set `true` for reasoning-heavy skills |
| `metadata.dependencies` | `[]` | Other skill names this skill needs |
| `metadata.trigger` | `on-demand` | `on-demand \| scheduled \| pre-merge \| real-time` |
| `metadata.tdd_phase` | `RED` | Update to `GREEN` once tests pass |

### Allowed Values

**Categories:** `orchestration` · `validation` · `monitoring` · `optimization` ·
`observability` · `scaffolding` · `integration` · `queue` · `metrics` ·
`maintenance` · `hygiene` · `management` · `security`

**Roles:** `engineer` · `senior-engineer` · `lead-engineer` · `principal-engineer` ·
`security-engineer` · `quality-engineer` · `orchestrator`

**Models:**

| Tier | Models |
|------|--------|
| Haiku (fast/cheap) | `claude-haiku-4.5` |
| Sonnet (balanced) | `claude-sonnet-4.5`, `claude-sonnet-4.6` |
| Opus (powerful) | `claude-opus-4.7`, `claude-opus-4.8` |

---

## Step 3 — Write Tests First (TDD RED Phase)

Open `tests/test_my_new_skill.py` and un-comment the `pytest.skip` lines as you define
the expected behaviour. At this stage the tests should **fail** — that's correct.

```bash
# Confirm tests fail (RED phase)
python -m pytest src/skills/my-new-skill/tests/ -v
# Expected: FAILED / ERROR for all tests — tests are not yet skipped but implementation is missing
```

---

## Step 4 — Implement the Skill

Open `scripts/my_new_skill.py` and replace the `<SkillClass>`, `<SkillConfig>`, and
`<SkillResult>` placeholders with your real class names.  Implement `run()`.

```bash
# Run tests until they pass (GREEN phase)
python -m pytest src/skills/my-new-skill/tests/ -v --tb=short

# Check coverage
python -m pytest src/skills/my-new-skill/tests/ --cov=src/skills/my-new-skill --cov-report=term-missing
# Target: ≥90% coverage
```

Once all tests pass, update `metadata.tdd_phase: GREEN` in `SKILL.md`.

---

## Step 5 — Register and Ship

### 5a. Register in FRAMEWORK-MANIFEST.yaml

Add an entry under the `skills:` key in `config/FRAMEWORK-MANIFEST.yaml`:

```yaml
skills:
  my-new-skill:
    name: my-new-skill
    description: "Detects drift in config files."
    category: validation
    status: active
    model: claude-haiku-4.5
    role: engineer
    effort: low
    version: "1.0"
    created: "YYYY-MM-DD"
    last_updated: "YYYY-MM-DD"
```

### 5b. Add to SKILLS-AVAILABLE.md

Add a row to the appropriate section in `docs/SKILLS-AVAILABLE.md`:

```markdown
| my-new-skill | Detects drift in config files | validation | claude-haiku-4.5 |
```

### 5c. Run Full Validation

```bash
make lint         # must pass
make test         # all tests must pass
make verify       # manifest + rendering checks must pass
```

### 5d. Commit

```bash
git add src/skills/my-new-skill/ config/FRAMEWORK-MANIFEST.yaml docs/SKILLS-AVAILABLE.md
git commit -m "feat(skills): add my-new-skill — <brief description>"
```

---

## Validation Checklist

Before opening a PR, confirm:

- [ ] `SKILL.md` has all required frontmatter fields (no `<PLACEHOLDER>` values remain)
- [ ] `metadata.tdd_phase` is `GREEN` (all tests pass)
- [ ] `__init__.py` exports the public API
- [ ] `scripts/<skill_name>.py` implements `run()` returning a result dataclass
- [ ] Test coverage ≥90%
- [ ] Registered in `config/FRAMEWORK-MANIFEST.yaml`
- [ ] Listed in `docs/SKILLS-AVAILABLE.md`
- [ ] `make lint && make test && make verify` all pass

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ImportError` on skill import | Check `__init__.py` import path matches script filename |
| Tests fail with `ModuleNotFoundError` | Run `pip install -e .` from repo root |
| CI fails on "SKILL.md missing required fields" | Run `python scripts/validate_skills.py` locally |
| Harness listings don't show new skill | Run `make render-copilot render-claude render-opencode` |

---

## Related Documents

- [`src/skills/_meta/skill-template/SKILL.md`](../skill-template/SKILL.md) — Canonical template
- [`docs/SKILLS-AVAILABLE.md`](../../docs/SKILLS-AVAILABLE.md) — Active skill registry
- [`config/FRAMEWORK-MANIFEST.yaml`](../../config/FRAMEWORK-MANIFEST.yaml) — Manifest
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md) — General contribution guide
- [`docs/guides/HARNESS-SYNC-CHECKLIST.md`](HARNESS-SYNC-CHECKLIST.md) — Harness sync process
