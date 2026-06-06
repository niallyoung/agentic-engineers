# Architecture Guide — Skills Consolidation

**Status:** Current (post Phase 3, 2026-06-06)
**Audience:** Contributors and maintainers
**Scope:** High-level overview of *why* and *how* the skills layer is
organized after consolidation. For component-level detail, follow the links in
each section rather than duplicating it here.

---

## 1. Why Consolidation Happened

Before Phase 3, 37 skills had accreted organically. Three problems emerged:

1. **Inconsistent naming.** Related skills were hard to discover because they
   lacked a shared prefix (`todo-maintenance` vs. `queue-management`), and
   harness-specific skills were not marked as such (`opencode-feature-sync`).
2. **Duplicate logic.** Two protocol validators (`protocol-validation` and
   `protocol-validator`) overlapped, creating a maintenance hazard and a latent
   import cycle.
3. **Dead weight.** Unused skills (e.g. `voice-notify`) added cross-platform
   complexity and cognitive overhead with no demonstrated adoption.

### Benefit analysis

| Goal | Mechanism | Outcome |
|------|-----------|---------|
| Discoverability | Consistent prefixes (`queue-*`, `harness-*`, `spec-*`, `protocol-*`, `model-*`, `cost-*`, `agent-*`, `skill-*`) | Skills group by purpose |
| Maintainability | Merge duplicate validators into one canonical skill | Single source of truth, no import cycle |
| Simplicity | Remove unused skills | Fewer files, lower surface area |
| Clarity | Isolate framework-internal "meta" skills | User-facing vs. internal separation |

Measured result of the consolidation: 4 skills renamed/removed, ~60 files
modified, 17 files deleted, zero regressions, 98/100 specification-compliance
score. See [README → Phase 3](../../README.md#phase-3-skills-consolidation-complete---2026-06-06)
for the headline numbers and [MIGRATION-2026-06-06.md](../MIGRATION-2026-06-06.md)
for consumer-facing changes.

---

## 2. Folder Structure (Post-Consolidation)

```
src/skills/
├── <user-facing skill>/        # e.g. queue-todo-sync, protocol-validator,
│   ├── SKILL.md                #   harness-opencode-feature-sync, model-engineer
│   ├── scripts/                # Implementation (one responsibility per script)
│   ├── references/             # Optional supporting data (YAML, docs)
│   └── tests/                  # Skill-local tests
│
└── _meta/                      # Framework-INTERNAL skills (not user-facing)
    ├── evaluation_framework/   #   e.g. harness_invoker, eval harness
    ├── queue-isolation/
    ├── orchestrator-enforcer/
    ├── git-operations/
    └── ...                     #   internals that wire the framework together
```

**The distinction that matters:** anything directly under `src/skills/` is a
**user-facing skill** an agent can be asked to invoke. Anything under
`src/skills/_meta/` is **framework plumbing** — it implements the rules,
validation, and orchestration that make the other skills work, and is not part
of the public skill catalog.

### Naming prefixes (canonical groups)

| Prefix | Members | Purpose |
|--------|---------|---------|
| `queue-*` | queue-management, queue-query, queue-todo-sync | DELEGATE/HANDBACK queue lifecycle |
| `harness-*` | harness-integration-tracker, harness-opencode-feature-sync | Harness-specific integration |
| `spec-*` | spec-validator, spec-management, spec-extract | SPEC.md governance |
| `protocol-*` | protocol-validator *(canonical)* | DELEGATE/HANDBACK schema validation |
| `model-*` | model-engineer, model-selection | Model routing / cost-quality |
| `cost-*` | cost-aggregation, cost-budgeting | Token/cost tracking |
| `agent-*` / `skill-*` | agent-creator / skill-creator | Scaffolding |

---

## 3. Harness Rendering Pipeline

Skills are authored **once** in `src/skills/` and rendered into
harness-specific output. The source tree is authoritative; rendered output is a
build artifact and must never be hand-edited.

```
  AUTHOR ONCE                 RENDER                    INSTALL
  ───────────                 ──────                    ───────
                       ┌──> dist/claude/   ──┐
  src/skills/  ──────► ├──> dist/copilot/  ──┤──► ~/.claude/skills/
  src/agents/          ├──> dist/opencode/ ──┤    ~/.copilot/skills/
  SPEC.md              └──> dist/pi/        ──┘    ~/.config/opencode/skills/
                                                   (+ π.dev)
        make render-all              make install
```

| Stage | Command | Output |
|-------|---------|--------|
| Render one harness | `make render-claude` (also `-copilot`, `-opencode`, `-pi`) | `dist/<harness>/` |
| Render all + specs | `make render-all` | all `dist/*` + `dist/specs/` |
| Install everywhere | `make install` | the four user config dirs |

Each harness applies provider-specific transformations during render (model
naming, permissions, frontmatter shape). That is why the **same** skill name
must appear identically across `dist/claude/`, `dist/copilot/`, and
`dist/opencode/` — and why a rename like `todo-maintenance → queue-todo-sync`
is only "done" once it re-renders cleanly to all four harnesses. See
[docs/RENDERING.md](../RENDERING.md) for transformation details.

---

## 4. Testing Strategy

The governing rule: **test against rendered output, not your dev install.**

- A developer's `~/.claude/` may be empty or stale in CI, so tests that read a
  developer's home directory are fragile. Tests instead read from `dist/`
  (the deterministic render) so they pass identically locally and in CI.
- Skill-local tests live in `src/skills/<skill>/tests/`; cross-skill behavior
  (e.g. interop, protocol compliance) lives in the top-level `tests/`.
- After any rename or merge, the **test-fixture counts** must match the actual
  skill count — a renamed skill that still lists its old name in a fixture is a
  drift bug caught by the suite.

```bash
make verify                       # structure + agents + skills + queue checks
python3 -m pytest tests/ -q       # full suite (run before every push)
```

See [CONTRIBUTING → Skill Lifecycle](../CONTRIBUTING/README.md#skill-lifecycle)
for how testing fits into the create→render→deploy flow, and
[CONTRIBUTING → Test Fixture Synchronization](../CONTRIBUTING/README.md#test-fixture-synchronization).

---

## 5. Single Source of Truth (Protocol Validation)

The clearest example of consolidation's payoff is protocol validation:

```
BEFORE                                    AFTER
──────                                    ─────
protocol-validator ─┐                     protocol-validator  ◄── canonical
                    ├─ overlap            (validate_delegate / validate_handback,
protocol-validation ┘  + latent cycle      ProtocolValidator class)
                                          ▲   ▲   ▲
core_protocol_validator ─► validation     │   │   └ renderer/validate_agents.py
   (cycle risk)                           │   └ _meta/evaluation_framework/harness_invoker
                                          └ queue-management/core_protocol_validator
```

All callers now import from `src/skills/protocol-validator/scripts`. The old
`protocol-validation` skill is deleted, and the previous import cycle is gone.
Consumer migration steps are in
[MIGRATION-2026-06-06.md → §3](../MIGRATION-2026-06-06.md#3-protocol-validation-merged-into-protocol-validator).

---

## See Also

- [docs/MIGRATION-2026-06-06.md](../MIGRATION-2026-06-06.md) — consumer migration steps
- [docs/SKILLS.md](../SKILLS.md) — current skill registry
- [docs/RENDERING.md](../RENDERING.md) — render pipeline & transformations
- [docs/CONTRIBUTING/README.md](../CONTRIBUTING/README.md) — skill lifecycle & testing
- `SKILLS-CONSOLIDATION-PLAN-2026-06-06.md` (repo root) — original execution plan
