# Agentic Engineers

A **multi-agent orchestration framework** for coordinating specialized AI agents
through structured handoffs, quality gates, and cost-aware model selection.
Designed for integration with coding CLIs: **OpenCode**, **Copilot**, **Claude**,
**Codex**.

## What It Is

Agentic Engineers solves the multi-agent coordination problem: how do you route
work to the right specialist, enforce quality consistently, and keep cost
proportional to task complexity — without spaghetti code or a polling daemon?

**The answer:** an ORCHESTRATOR-FIRST architecture built on **direct sub-agent
spawning**, not queue polling:

1. Work is expressed as a DELEGATE task (structured YAML: scope, context, plan, success criteria)
2. The Orchestrator spawns the right specialist directly (Agent/Task tool) and reads the HANDBACK back as that spawn call's result — no polling loop, no timer, no daemon, no filesystem queue
3. The specialist executes and returns a HANDBACK with results + metrics
4. The harness session transcript itself — every DELEGATE as a spawn prompt, every HANDBACK as that spawn's result — is the durable audit record
5. Metrics feed back into model selection and routing for future tasks

## Goals

The framework is built to be **minimal, portable, and self-reducing**:

- **Small AGENTS + SKILLS mechanisms** — a portable orchestration layer that works across harnesses (Claude, Copilot, OpenCode, Codex) without proprietary integrations
- **Framework self-reduction** — as base and frontier models improve, LOC and complexity are meant to decrease, not grow
- **Eventual redundancy** — when harnesses compose and delegate work well by default, this coordination layer should fade into standard practice
- **Harness comparative analysis** — the `src/ → make render → dist/ → make install → ~/.<harness>` pipeline lets the same agent/skill roster be compared across harnesses for feature parity and quality trade-offs

## The Roster

Eight roles: **Orchestrator** (routing, `claude-sonnet-5`), **Engineer** (well-scoped
implementation, `claude-haiku-4.5`), **Senior Engineer**, **Lead Engineer**,
**Quality Engineer**, **Model Engineer** (all `claude-sonnet-5`), **Principal
Engineer** (`claude-opus-5`), and **Security Engineer** (`claude-fable-5`). Full
definitions, routing rules, and escalation paths live in
[src/AGENTS.md](src/AGENTS.md). Skills are cataloged in
[src/SKILLS.md](src/SKILLS.md).

## Quick Start

```bash
# Install the default harness set (OpenCode, Copilot, Claude)
make install

# Or a single harness:
make install-claude
make install-opencode
make install-codex

# Preview without touching your home dir — renders to dist/<harness>/ instead:
make render-claude
make render-copilot
make render-opencode
make render-codex
make render-all      # every harness + dist/specs/
```

`make install` backs up your existing harness config to a date-stamped copy
before writing the new one (see `make install-<harness>` output for details).
To install into an alternate root instead of `$HOME` (e.g. for testing):

```bash
DESTDIR=/tmp/test-install make install-opencode
```

**Using the Orchestrator:**

```bash
claude --permission-mode auto --dangerously-skip-permissions --agent orchestrator
opencode --agent orchestrator
copilot --agent orchestrator
```

Then delegate work in plain language:

```bash
delegate: Fix the CI/CD timeout in .github/workflows/ci.yml
```

The Orchestrator parses the task, spawns the right specialist(s) directly (one
DELEGATE per spawn), reads each HANDBACK back as the spawn result, and reports
back to you.

## Quality Gates

`make quality-gate` (lint + test + verify + render validation) is the standard
pre-push check; CI re-runs the same gate. Git hooks under `.githooks/` enforce
protocol compliance at commit time — DELEGATE/HANDBACK structure, secret-leak
checks, and SPEC.md drift (`scripts/validate-spec-constraints.py`). CI's
security-gate workflow additionally runs `scripts/entropy_detector.py` for
credential/secret entropy scanning, and `scripts/check_protocol_compliance.py`
validates DELEGATE/HANDBACK protocol conformance. Run the full local suite with `make test`.

## Documentation

| Topic | Document |
|-------|----------|
| Full agent roster & routing | [src/AGENTS.md](src/AGENTS.md) |
| Skills catalog | [src/SKILLS.md](src/SKILLS.md) |
| Specification | [docs/SPEC.md](docs/SPEC.md) |
| Protocol (DELEGATE/HANDBACK) | [docs/PROTOCOL.md](docs/PROTOCOL.md) |
| Onboarding | [docs/ONBOARDING.md](docs/ONBOARDING.md) |
| Docs index | [docs/INDEX.md](docs/INDEX.md) |
| Guides (agent/skill creation, harness setup, troubleshooting) | [docs/guides/](docs/guides/) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |

## Supported Harnesses

| Harness | Status |
|---------|--------|
| [OpenCode](docs/guides/harness-setup/opencode.md) | Recommended |
| [Claude Code](docs/guides/harness-setup/claude.md) | Stable |
| GitHub Copilot | Stable |
| [Codex](docs/guides/harness-setup/codex.md) | Supported, opt-in install |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Areas of interest: harness integrations,
new agent roles, new skills, test coverage, documentation.

## License

MIT License — see [LICENSE](LICENSE) for details.
