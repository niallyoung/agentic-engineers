# Agentic Engineers — Quick Reference

**One-page cheat sheet for the 7-role agent system. Print or bookmark.**

---

## 7-Role Model

| Role | Model | Cost | Use For |
|------|-------|------|---------|
| **Orchestrator** | Haiku | 1x | Task routing, metrics, automation |
| **Engineer** | Haiku | 1x | Well-scoped coding (<2hr), TDD |
| **Senior Engineer** | Sonnet | 3x | Complex code, architecture questions |
| **Lead Engineer** | Sonnet | 3x | Code review, quality verification |
| **Principal Engineer** | Opus | 7.5x | Cross-service design, strategy |
| **Security Engineer** | Opus | 7.5x | Threat modeling, security analysis |
| **Quality Engineer** | Haiku | 1x | QA gates, quorum voting |

**Routing:** Complexity + scope → role. See AGENTS.md lines 28-50 for decision tree.

---

## DELEGATE/HANDBACK Protocol

**Orchestrator → Engineer:**
```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-24-redis-caching
role: Engineer
model: claude-haiku-4-5
effort: high
scope: Add Redis caching to {example-service}
context:
  - File: lambda/query/main.go:45
  - Problem: Cache misses on every query
plan:
  1. Add Redis client
  2. Implement cache getter (1hr TTL)
  3. Write hit/miss tests
success_criteria:
  - make verify passes
  - Cache hit ratio >80%
---
```

**Engineer → Orchestrator:**
```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-24-redis-caching
status: complete
deliverables:
  - Modified: lambda/query/main.go:45-80
  - Added: lambda/query/cache_test.go (tests)
tests:
  - "make verify": PASS (87% coverage)
tokens_in: 18500
tokens_out: 2100
quality_score: 90
---
```

**See HANDOFF.md for full spec.**

---

## Quality Gate Checklist (Tier 1 — All Tasks)

- ✓ Lint passes (`make lint`)
- ✓ Tests pass (`make test`)
- ✓ No new errors or warnings
- ✓ In-scope changes only
- ✓ Tests added/updated for new code
- ✓ No production hazards (panic, secrets, commented code)

**Rule:** HANDBACK invalid until all items ✓

See QUALITY.md for Tier 2 (Senior+) and Tier 3 (Principal/Security).

---

## Routing Decision Tree (Short Form)

```
Task arrives
  ↓
Is scope clear + plan included?
  → Yes: → Complexity analysis
         → Estimate tokens + duration
  → No: → Escalate to Lead Engineer (unclear scope)
         ↓
  ↓
Task complexity + repo type?
  → Low + Go → Haiku Engineer
  → Low + React → Haiku Engineer
  → Medium + familiar → Haiku Engineer (if <2hr)
  → Medium + unfamiliar → Sonnet Senior Engineer
  → High + cross-service → Sonnet Lead Engineer
  → Architecture/design → Opus Principal Engineer
  → Security analysis → Opus Security Engineer
```

See AGENTS.md for full routing rules.

---

## Escalation Checklist

**Engineer → Senior Engineer:**
- Root cause unclear
- Task complexity > 2 hours
- Architectural question ("how should we...")
- Cross-service coordination

**Senior Engineer → Lead Engineer:**
- Code review blocker
- Quality gate failure (Tier 2)
- Design decision needed (not architecture)

**Any role → Principal Engineer:**
- Multi-team impact
- Long-term strategy decision
- Cost/quality tradeoff analysis

**Any role → Security Engineer:**
- Threat model concern
- Compliance question
- Auth/encryption decision

---

## Key Files

| Task | File |
|------|------|
| Understanding roles & routing | AGENTS.md |
| DELEGATE/HANDBACK markup | HANDOFF.md |
| Quality standards | QUALITY.md |
| All 22 skills | skills/ directory |
| Metrics schema | operations/METRICS.md |
| Cost optimization | operations/TOKENADVISOR.md |

---

## Common Tasks (2-minute reference)

**"I have a task for the team"**
→ Route with AGENTS.md decision tree → Create DELEGATE markup → Send to agent

**"I'm an Engineer receiving a task"**
→ Read DELEGATE markup → TDD (RED-GREEN-REFACTOR) → Return HANDBACK → metrics

**"I'm Quality Engineer reviewing code"**
→ Check QUALITY.md Tier 1 checklist → PASS/CONDITIONAL/NEEDS_WORK → Return verdict

**"I'm Orchestrator analyzing cost"**
→ Read METRICS.md per-task records → Run TokenAdvisor analysis → Generate recommendations

---

## Cost Targets (Year 1)

- **Daily cost:** $2.10 → $1.50 (28% reduction)
- **Cost per quality point:** $0.00220 → $0.00160
- **Model split:** Haiku 60%, Sonnet 35%, Opus 5%

---

**Load agentic-engineers/ as a complete unit. Everything you need is here.**
