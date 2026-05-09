# Reference — Architecture & Coding Standards

**Production code patterns and architectural guidance extracted from the ERS platform.**

These documents provide reference material for implementation decisions, coding standards, and architectural patterns.

## Files

| File | Audience | When to Read |
|------|----------|--------------|
| **CODING_STANDARDS.md** | All engineers | Before writing code in Go/TypeScript/CDK |
| **DESIGN_PATTERNS.md** | Senior Engineers | Before architecture decisions (handlers, idempotency, caching) |
| **CQRS_AND_EVENT_SOURCING.md** | System Architects | Before event system changes (domain events, projection rebuild) |
| **MULTI_AGENT_OPTIMIZATION.md** | Principal Engineer | Strategic research on RLAF, model selection, and cost optimization |
| **OPERATIONAL_DASHBOARDS.md** | Orchestrator | Week 3+ (metrics visualization and monitoring setup) |
| **TODO.md** | Project Managers | Phase tracking, deliverables checklist, milestone planning |

## How to Use This Directory

**For implementation guidance:**
- Check `CODING_STANDARDS.md` for Go/TypeScript/CDK conventions before writing code
- Check `DESIGN_PATTERNS.md` for architectural patterns and proven solutions

**For understanding architecture:**
- Read `CQRS_AND_EVENT_SOURCING.md` to understand the event-driven architecture
- Read `MULTI_AGENT_OPTIMIZATION.md` for research on model selection and cost optimization

**For project tracking:**
- Check `TODO.md` for phase status, deliverables, and milestones
- Use `OPERATIONAL_DASHBOARDS.md` as a guide for setting up metrics dashboards

## Key Concepts

### Coding Standards
- Language-specific conventions (Go, TypeScript, CDK)
- Error handling patterns
- Testing strategies
- Code organization principles

### Design Patterns
- Handler patterns (HTTP API, event consumer)
- Idempotency implementations
- Caching strategies
- Cross-service communication patterns

### Event Architecture
- CQRS (Command Query Responsibility Segregation)
- Event Sourcing principles
- Domain events vs. commands
- Replay and projection rebuild procedures

### Cost Optimization Research
- Model selection algorithms
- Token burn analysis
- Quality-cost tradeoff evaluation
- A/B testing frameworks

## See Also

- `../MANIFEST.md` — Complete file listing of entire system (discovery tool)
- `../guides/INDEX.md` — Complete file catalog
- `../guides/CLAUDE.md` — Team context and integration
- `../orchestration/AGENTS.md` — Role definitions
