# Documentation Structure

Welcome to the agentic-engineers documentation directory. This guide explains how documentation is organized and where to find what you need.

## Quick Start

- **Getting started?** → Start with [INSTALL.md](INSTALL.md)
- **Understanding the system?** → Read [ONBOARDING.md](ONBOARDING.md)
- **Looking for API reference?** → See [SPEC.md](SPEC.md)
- **Need to set up orchestration?** → Check [ORCHESTRATION-README.md](ORCHESTRATION-README.md)
- **Deployed or operational?** → See [SYSTEM.md](SYSTEM.md)

## Directory Organization

### Core Documentation (read first)
- **`SPEC.md`** — Complete specification for the agentic-engineers framework
- **`AGENTS.md`** — Routing decision tree and agent role definitions
- **`PROTOCOL.md`** — Queue protocol specification for all DELEGATE/HANDBACK interactions
- **`SYSTEM.md`** — Operational system architecture and deployment guide
- **`QUALITY.md`** — Quality assurance standards and validation rules

### Implementation Guides
- **`INSTALL.md`** — Installation and setup instructions
- **`ONBOARDING.md`** — New contributor onboarding guide
- **`ORCHESTRATION-README.md`** — How to use the Orchestrator
- **`SKILLS.md`** — Overview of available skills and how to create new ones
- **`MANIFEST.md`** — Complete file manifest and purpose of each directory

### Architecture & Design
- **`decisions/`** — Architecture Decision Records (ADRs) in Markdown
  - `ADR-structure-2025-05-09.md` — Repository structure optimization decision
- **`architecture-*.md`** — Detailed architectural explorations and design documents
- **`model-*.md`** — Model selection, configuration, and centralization guides
- **`queue-enforcement-*.md`** — Queue protocol implementation details
- **`quality-gate-*.md`** — Quality assurance gate implementation

### Standards & Compliance
- **`STANDARDS-*.md`** — Documentation of standards compliance and alignment

### Operational References
- **`LOGGING-QUEUE-ARCHITECTURE.md`** — Logging and queue architecture
- **`TOKEN-USAGE-TRACKING.md`** — Token usage monitoring
- **`MSMTP-SETUP.md`** — Email/notification setup

### Historical & Archived
- **`archive/`** — Archived documentation, session deliverables, and historical artifacts
  - `sessions/` — Session audit reports and deliverables
  - `legacy/` — Superseded guides and old architecture docs
  - See [archive/README.md](archive/README.md) for details

## Finding What You Need

### By Use Case

**I want to understand the system architecture**
1. Read: [SYSTEM.md](SYSTEM.md)
2. Then: [SPEC.md](SPEC.md) (core specification)
3. Deep dive: [decisions/ADR-structure-2025-05-09.md](decisions/ADR-structure-2025-05-09.md)

**I need to implement a new agent**
1. Start: [ONBOARDING.md](ONBOARDING.md)
2. Reference: [AGENTS.md](AGENTS.md) (routing tree)
3. Guide: [PROTOCOL.md](PROTOCOL.md) (DELEGATE/HANDBACK format)

**I'm setting up a development environment**
1. Read: [INSTALL.md](INSTALL.md)
2. Reference: [MANIFEST.md](MANIFEST.md) (what each directory contains)

**I need to create a new skill**
1. Reference: [SKILLS.md](SKILLS.md)
2. Spec: See `src/skills/skill-creator/SKILL.md` for skill template

**I'm troubleshooting an issue**
1. Check: [SYSTEM.md](SYSTEM.md) (operational issues)
2. Search: `grep -r "search_term" docs/` (find relevant documentation)
3. Archive: [archive/README.md](archive/README.md) if issue is old/historical

### By Topic

- **Agent orchestration:** SPEC.md, AGENTS.md, ORCHESTRATION-README.md
- **Queue protocol:** PROTOCOL.md, queue-enforcement-*.md
- **Quality gates:** QUALITY.md, quality-gate-*.md, DELEGATE-HANDBACK-QUALITY-GATES.md
- **Skills & automation:** SKILLS.md, TOKEN-USAGE-TRACKING.md
- **Deployment & operations:** SYSTEM.md, INSTALL.md, MSMTP-SETUP.md
- **Model selection:** [docs/architecture/model-optimization.md](architecture/model-optimization.md)
- **Testing & TDD:** TDD-ROADMAP.md, QUALITY-GATE-TEST-FRAMEWORK.md

## Documentation Standards

All documentation in this directory follows these standards:

1. **Clear structure:** Table of contents, clear headings, navigation links
2. **Purpose statement:** Every document begins with its purpose
3. **Up-to-date:** Documentation is maintained alongside code changes
4. **Linked:** Related documents link to each other
5. **Archival:** Outdated docs are archived, not deleted

## Contributing to Documentation

When adding or updating documentation:

1. **Determine scope:** Is this core documentation, architectural, or archived?
2. **Use clear naming:** Follow the naming convention (e.g., `SKILL-SPECS.md` moved to `docs/`)
3. **Update navigation:** Update this README.md if adding a top-level doc
4. **Preserve history:** Use `git mv` for significant moves, document the change
5. **Archive when ready:** Move completed/superseded docs to `docs/archive/`

## Important Notes

- **Root-level files:** Only `README.md` and `TODO.md` remain at root for immediate visibility
- **SPEC.md:** Canonical specification, controlled by Principal/Lead Engineer
- **AGENTS.md:** Routing reference (not in docs/ due to being in src/docs/ for tool access)
- **Do not modify:** Protected files include `src/agents/*-agent.md`, `src/skills/*/SKILL.md`

## Questions?

- Check [SYSTEM.md](SYSTEM.md) for operational questions
- See [ONBOARDING.md](ONBOARDING.md) for contribution questions
- Review relevant ADR in [decisions/](decisions/) for architectural decisions
