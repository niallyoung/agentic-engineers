# Harness Sync Checklist

> **Purpose**: Prevent drift between `src/skills/` (source of truth) and rendered
> harness directories (`dist/copilot/`, `dist/opencode/`, `dist/claude/`).  
> **Phase**: 5.1 — initial audit + sync checklist  
> **Last audited**: 2026-06-06 (Phase 5.1 framework standardization)

---

## Background

agentic-engineers maintains **four harness render targets**:

| Harness | Dist Path | Renderer | Trigger |
|---------|-----------|----------|---------|
| Copilot CLI | `dist/copilot/` | `make render-copilot` | CI + on-demand |
| OpenCode | `dist/opencode/` | `make render-opencode` | CI + on-demand |
| Claude | `dist/claude/` | `make render-claude` | CI + on-demand |
| PI (Prompt Injection) | `dist/pi/` | `make render-pi` | CI + on-demand |

**Source of truth**: `src/skills/<skill-name>/SKILL.md`  
**Rendered output**: `dist/<harness>/skills/<skill-name>/`

Drift occurs when:
1. A skill is renamed/added/removed in `src/` but render is not re-run
2. A harness render template changes but existing renders are not regenerated
3. Deprecated skills remain in `dist/` after removal from `src/`

---

## Phase 5.1 Audit Findings (2026-06-06)

### Copilot Harness Drift

**Stale entries (in `dist/copilot/` but not in `src/skills/`):**

| Skill | Reason | Action |
|-------|--------|--------|
| `ab-testing` | Deprecated in Phase 4 | Remove from dist/copilot/ |
| `consistency-checker` | Missing `__init__.py` in src; present in dist | Fix src or keep in dist |
| `model-selection` | Not in active source dir listing | Verify source location |
| `opencode-feature-sync` | Renamed → `harness-opencode-feature-sync` in Phase 2B | Remove stale; dist/opencode/ already has new name |
| `protocol-validation` | Merged → `protocol-validator` in Phase 1 | Remove stale |
| `spec-management` | In source but missing from source scan (has SKILL.md) | Recheck source listing |
| `testing` | Internal meta-skill; should not be in dist | Remove from dist |
| `todo-maintenance` | Renamed → `queue-todo-sync` in Phase 2A | Remove stale |
| `usage-tracking` | In source (has SKILL.md); present in copilot dist | Re-run render |
| `voice-notify` | Deleted in Phase 3 | Remove from dist/copilot/ |
| `workflow-review` | Present in src; should be in dist | Re-run render |

**Missing entries (in `src/skills/` but not in `dist/copilot/`):**

| Skill | Action |
|-------|--------|
| `harness-opencode-feature-sync` | Run `make render-copilot` |
| `queue-todo-sync` | Run `make render-copilot` |

### OpenCode Harness Drift

**Stale entries (in `dist/opencode/` but not active source):**

| Skill | Reason | Action |
|-------|--------|--------|
| `ab-testing` | Deprecated in Phase 4 | Remove from dist/opencode/ |
| `consistency-checker` | Missing `__init__.py` in src | Fix or remove |
| `model-selection` | Not in active source | Verify |
| `spec-management` | Missing from source scan | Recheck |
| `testing` | Internal meta-skill | Remove from dist |
| `usage-tracking` | Has SKILL.md in src but not rendered consistently | Re-run render |
| `workflow-review` | Has source but inconsistent | Re-run render |

**Correctly synced (appear in both opencode dist and source):**

`agent-creator`, `cost-aggregation`, `doc-quality-monitor`, `file-sync`,
`harness-integration-tracker`, `harness-opencode-feature-sync`, `local-model-runtime`,
`metrics-etl`, `model-engineer`, `protocol-validator`, `queue-management`,
`queue-query`, `queue-todo-sync`, `repo-init`, `skill-creator`, `spec-validator`,
`tokenadvisor`

### Claude Harness

Claude dist only has `agents/` and `skills/` dirs — the skills listing appears empty.
Requires investigation: run `make render-claude` and verify output.

---

## Sync Process (Standard Operating Procedure)

### When to Run Sync

- ✅ After adding a new skill to `src/skills/`
- ✅ After renaming a skill directory
- ✅ After deleting/deprecating a skill
- ✅ Before any release tag
- ✅ After modifying a harness render template

### How to Sync

```bash
# 1. Sync all harnesses (run after any skill change)
make render-copilot render-claude render-opencode render-pi render-specs

# 2. Verify no unexpected drift remains
python scripts/validate_skills.py          # Check source conformance
git diff --stat dist/                      # See what changed in rendered output

# 3. Remove stale rendered skills (manual step — check each before deleting)
#    Example: removing deprecated voice-notify from copilot dist
rm -rf dist/copilot/skills/voice-notify/

# 4. Commit the render outputs
git add dist/
git commit -m "chore(dist): re-render all harnesses after skill changes"
```

### Automated Check (CI)

Gate 4 in `ci.yml` ("Skill template conformance report") generates a per-commit
summary. The render steps in CI re-render all harnesses on every push to `main`.

---

## Checklist Before Merging Skill Changes

```
Pre-merge harness sync checklist:

Skill source changes:
[ ] SKILL.md frontmatter is complete (run: python scripts/validate_skills.py)
[ ] Skill registered in config/FRAMEWORK-MANIFEST.yaml
[ ] Skill listed in docs/SKILLS-AVAILABLE.md

Harness render:
[ ] make render-copilot   — completed without errors
[ ] make render-claude    — completed without errors  
[ ] make render-opencode  — completed without errors
[ ] make render-pi        — completed without errors
[ ] make render-specs     — completed without errors

Drift check:
[ ] dist/copilot/skills/<skill-name>/ exists (if skill is copilot-compatible)
[ ] dist/opencode/skills/<skill-name>/ exists (if skill is opencode-compatible)
[ ] No stale dist/ entries from renamed/deleted skills

Tests:
[ ] make test             — all tests pass
[ ] make verify           — manifest checks pass
[ ] make lint             — no lint errors
```

---

## Adding a New Harness

When a new harness target is added (e.g., a new AI assistant integration):

1. Create `dist/<harness-name>/` directory structure
2. Add `make render-<harness-name>` target to `Makefile`
3. Add render step to `.github/workflows/ci.yml` (alongside existing render steps)
4. Add harness to the table at the top of this document
5. Add `dist/<harness-name>/skills/<skill-name>/` to this checklist

---

## Related Documents

- [`src/skills/_meta/skill-template/QUICKSTART.md`](../../../src/skills/_meta/skill-template/QUICKSTART.md) — Skill authoring guide
- [`docs/SKILLS-AVAILABLE.md`](../SKILLS-AVAILABLE.md) — Active skill registry
- [`config/FRAMEWORK-MANIFEST.yaml`](../../config/FRAMEWORK-MANIFEST.yaml) — Manifest
- [`docs/RENDERING.md`](../RENDERING.md) — Harness rendering documentation
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md) — Contribution guide (CI section)
