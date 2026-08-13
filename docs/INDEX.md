# Documentation Index

**Last Updated:** 2026-08-11 (post-slimdown, SPEC-2026-005)

---

## Start Here

| Document | Purpose |
|----------|---------|
| [README.md](../README.md) | Project overview, quick start |
| [ONBOARDING.md](ONBOARDING.md) | New developer onboarding |
| [AGENTS.md](AGENTS.md) | Pointer to the canonical roster/routing at [`src/AGENTS.md`](../src/AGENTS.md) |

---

## Core Protocol & Specification

| Document | Purpose |
|----------|---------|
| [SPEC.md](SPEC.md) | **Source of truth** — implementation specification |
| [PROTOCOL.md](PROTOCOL.md) | DELEGATE/HANDBACK validation, scoring, and escalation reference |
| [QUEUE-PROTOCOL.md](QUEUE-PROTOCOL.md) | Queue mechanics + state machine (durable inbox/audit substrate) |
| [CORE-PROTOCOL-QUICKSTART.md](CORE-PROTOCOL-QUICKSTART.md) | 30-minute protocol quick start |
| [ENTRYPOINT.md](ENTRYPOINT.md) | Standard execution model |
| [WORKFLOW.md](WORKFLOW.md) | SDLC lifecycle and enforcement gates |
| [RENDERING.md](RENDERING.md) | Framework render/install pipeline |
| [REGRESSION-GATE-POLICY.md](REGRESSION-GATE-POLICY.md) | Regression testing gate (interim permissive, WP-0/WP-5) |
| [BACKGROUND-AGENT-COMMIT-PROTOCOL.md](BACKGROUND-AGENT-COMMIT-PROTOCOL.md) | Background agent commit protocol |

---

## Design & Decisions

| Location | Contents |
|----------|----------|
| [design/](design/) | Active design notes (spawn-sub-agent pattern, HANDBACK-as-DELEGATE) |
| [decisions/](decisions/) | Architecture Decision Records (historical) |
| [specs/](specs/) | Machine-readable protocol schemas (delegate/handback/protocol-core) |
| [spec-proposals/](spec-proposals/) | SPEC change proposals (spec-management audit trail) |

---

## Guides

| Location | Contents |
|----------|----------|
| [guides/](guides/) | Agent/skill creation, harness extension, deployment, troubleshooting — see [guides/INDEX.md](guides/INDEX.md) |

---

## Governance

`docs/SPEC.md` is protected by the `spec-management` skill (proposal → analysis →
approval → changelog → audit). See its Update Log for the full change history.
