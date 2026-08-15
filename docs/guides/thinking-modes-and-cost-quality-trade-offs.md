# Thinking Modes & Cost-Quality Trade-offs

Extended thinking lets the model "think out loud" before answering — useful for judgment-heavy tasks, harmful overhead for deterministic ones. The framework enables thinking selectively to maximise quality where it matters and minimise cost where it doesn't.

> **Cost impact:** Extended thinking adds ~3–5× tokens and latency. Enabling it only for roles that genuinely require judgment reduces per-workflow cost by 40–60%.

## Decision Rule

```
Is the output determined by a fixed rule or checklist?
  YES → Thinking OFF  (Orchestrator, Engineer, QE)
  NO  → Is judgment, trade-off analysis, or structured exploration required?
          YES → Thinking ON  (Senior, Lead, Principal, Security, Model Engineers)
```

## Key Examples

| Role | Thinking | Reason |
|------|----------|--------|
| **Orchestrator** | ❌ OFF | Routing is deterministic pattern-matching. Thinking adds 3–5× cost with zero accuracy improvement. |
| **Engineer** | ❌ OFF | Execution work is pre-planned — numbered steps, file paths, success criteria. No extended reasoning needed. |
| **Senior Engineer** | ✅ ON | Receives unscoped, ambiguous problems. Must evaluate trade-offs and produce concrete plans. |
| **Lead Engineer** | ✅ ON | Code review requires detecting subtle logic errors and non-obvious security implications. |
| **Security Engineer** | ✅ ON | STRIDE threat modeling requires structured multi-step reasoning. Thinking is non-negotiable. |

## Reference

See [src/AGENTS.md](../../src/AGENTS.md) and [docs/decisions/](../decisions/) for the complete analysis.

---

## Related Reading

- **The Roster (8 roles):** See [README.md#the-roster](../../README.md#the-roster) for the full roles table
- **Model assignments per harness:** See [README.md](../../README.md) for an overview, or [docs/SPEC.md § Model Naming & Harness Compatibility](../SPEC.md) for the authoritative per-harness model mapping
