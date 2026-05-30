# Roles — Team Member Container Definitions

**Each role is defined by which skills it uses, not by a nested file structure.**

This is the new role-as-container approach: minimal files, maximum reuse.

---

## Role Definitions (8 total)

| Role | Model | Effort | Cost | Primary Use |
|------|-------|--------|------|-------------|
| **orchestrator.md** | Haiku 4.5 | low | 1x | Task routing, metrics, automation |
| **engineer.md** | Haiku 4.5 | high | 1x | Well-scoped implementation (2-4 hrs) |
| **senior-engineer.md** | Sonnet 4.5 | high + thinking | 3x | Complex coding, cross-service |
| **lead-engineer.md** | Sonnet 4.6 | high + thinking | 3x | Quality verification, code review |
| **principal-engineer.md** | Opus 4.6 | high + thinking | 7.5x | Cross-service architecture |
| **security-engineer.md** | Opus 4.8 | max + thinking | 7.5x | Threat modeling, security review |
| **quality-engineer.md** | Sonnet 4.5 | medium | 3x | QA gates, E2E validation |
| **model-engineer.md** | Sonnet 4.5 | high + thinking | 3x | Cost optimization, recommendations |

---

## How to Read a Role File

Each role file contains:

1. **What This Role Does** — Clear summary
2. **Primary Skills** — Role-specific capabilities
3. **Shared Skills** — Used across multiple roles
4. **When Escalated To** — What triggers this role
5. **Escalation To** — Where this role escalates
6. **Workflow or Involvement** — How it participates
7. **Key Decisions** — What authority it has
8. **See Also** — Related skills and files

---

## Role Composition Map

```
orchestrator.md uses:
  ├─ orchestration/task-routing.md
  ├─ monitoring/metrics-collection.md
  ├─ orchestration/model-engineer-coordination.md
  ├─ shared/github-cli.md
  ├─ monitoring/cicd-watch.md
  ├─ shared/git-workflow.md
  └─ [5 more optimization/monitoring skills]

engineer.md uses:
  ├─ shared/core-engineering-baseline.md
  ├─ shared/quality-assessment-baseline.md
  ├─ shared/engineer-specifics.md
  ├─ patterns/implementation-coding.md
  ├─ patterns/local-ci.md
  ├─ testing/playwright-testing.md (Part 1)
  ├─ patterns/lambda-handler.md
  ├─ patterns/makefile.md
  ├─ shared/git-workflow.md
  ├─ shared/cdk-stack.md
  └─ [more shared skills]

senior-engineer.md uses:
  ├─ shared/core-engineering-baseline.md
  ├─ shared/quality-assessment-baseline.md
  ├─ patterns/api-resilience.md (owned)
  ├─ patterns/event-consumer.md (owned)
  ├─ review/code-review.md
  ├─ patterns/lambda-handler.md
  ├─ patterns/makefile.md
  ├─ testing/playwright-testing.md (both parts)
  └─ [more shared skills]

lead-engineer.md uses:
  ├─ shared/quality-assessment-baseline.md
  ├─ shared/core-engineering-baseline.md
  ├─ review/code-review.md
  ├─ review/code-quality-analysis.md
  ├─ patterns/lambda-handler.md
  ├─ orchestration/todo-management.md
  └─ [more monitoring/review skills]

quality-engineer.md uses:
  ├─ shared/quality-assessment-baseline.md
  ├─ shared/core-engineering-baseline.md
  ├─ review/code-quality-analysis.md
  ├─ review/quorum-qe.md
  ├─ monitoring/cicd-watch.md
  ├─ orchestration/todo-management.md
  ├─ testing/playwright-testing.md (E2E focus)
  └─ [more review/security skills]

[etc for principal-engineer, security-engineer, model-engineer]
```

---

## How to Change a Role

Instead of restructuring directories:

1. **Rename role:** Rename orchestrator.md → task-router.md
2. **Add skill:** Add line to role file linking to skill
3. **Remove skill:** Remove line from role file
4. **Create new role:** Create new .md file listing skills
5. **Merge roles:** Copy skills from 2 roles into 1

All changes are **one file edits** — no directory moving.

---

## Future: YAML-Based Roles

This text-based structure can evolve to YAML:

```yaml
roles:
  orchestrator:
    model: haiku-4-5
    effort: low
    skills:
      - orchestration/task-routing
      - monitoring/metrics-collection
      - shared/github-cli
      - monitoring/cicd-watch
```

With this, role composition becomes:
- Data-driven (not file-based)
- Versioned (git history of changes)
- A/B testable (easy to try new compositions)
- Dynamic (load at runtime)

---

## Understanding Role Relationships

```
User Task
  ↓
Orchestrator (routes)
  ├─ → Engineer (well-scoped, <4 hrs)
  ├─ → Senior Engineer (complex, unclear)
  ├─ → Principal Engineer (architecture)
  └─ → Security Engineer (threat modeling)
       ↓
     Lead Engineer (code review)
       ↓
     Quality Engineer (QA gates)
       ↓
     Model Engineer (feedback analysis)
       ↓
   (recommendation) → Orchestrator
```

---

## Key Benefits of This Structure

1. **Skill-Centric** — "What skills does this need?" not "Which role?"
2. **Reusable** — Same skill used by multiple roles (shared/)
3. **Composable** — Mix and match skills easily
4. **Maintainable** — One skill file, changed once
5. **Flexible** — Rename or reorganize roles without file moving
6. **Testable** — Easy A/B test different role compositions

---

## When to Use Each Role

| Situation | Route To |
|-----------|----------|
| Well-scoped task, <4 hours | Engineer |
| Unclear requirements, complex | Senior Engineer |
| Code review needed | Lead Engineer |
| Design/architecture decision | Principal Engineer |
| Threat/vulnerability concern | Security Engineer |
| QA/gate verification | Quality Engineer |
| Cost optimization needed | Model Engineer |
| Task needs routing | Orchestrator |

---

## See Also

- `../shared/` — Cross-role skills
- `../patterns/` — Implementation skills
- `../review/` — Quality verification skills
- `orchestration/AGENTS.md` — Routing decision tree (root dir)
