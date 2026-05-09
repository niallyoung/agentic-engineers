# Architecture — High-Level Design & Decisions

**Skills for designing cross-service architectures and documenting design decisions.**

## Skills in This Directory

| Skill | Used By | Purpose |
|-------|---------|---------|
| **architecture-design.md** | Principal Engineer | Methodology for cross-service architecture design |
| **design-decision-documentation.md** | Principal Engineer | ADR (Architecture Decision Record) format |
| **system-tradeoff-analysis.md** | Principal Engineer | Systematic tradeoff analysis framework |

## When to Use

- **Before major architecture change** — Principal Engineer uses architecture-design.md
- **Documenting a significant decision** — Principal Engineer uses design-decision-documentation.md
- **Evaluating competing approaches** — Principal Engineer uses system-tradeoff-analysis.md

## Architecture Workflow

```
Problem identified
  ↓
architecture-design.md: Problem mapping + Option generation
  ↓
system-tradeoff-analysis.md: Evaluate competing options
  ↓
Choose winning approach
  ↓
design-decision-documentation.md: Record ADR with rationale
  ↓
Share decision with team
  ↓
Plan rollout
```

## Key Decisions

These are cross-service decisions requiring Principal Engineer:
- Splitting monolith into services
- Adding new service (Handler vs. Event Consumer)
- Changing event schema
- Changing auth/security model
- Changing storage layer
- Performance optimization strategy

## See Also

- `../patterns/` — Implementation patterns that follow from architecture
- `../security/` — Threat modeling for architectural decisions
- `../optimization/` — Cost analysis for architectural tradeoffs
