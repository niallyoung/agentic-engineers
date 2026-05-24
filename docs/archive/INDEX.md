# Documentation Archive Index

**Last Updated:** 2025-05-24  
**Archive Created:** May 24, 2025  
**Purpose:** Preserve historical, design, and supplementary documentation with clear organization and categorization.

---

## Overview

This archive contains 46+ markdown files organized into the following categories:

| Category | Contents | Status |
|----------|----------|--------|
| Root-level | Implementation, design, roadmaps | Historical/Reference |
| Frameworks | AI framework analysis | Complete |
| Architecture | ADRs and explorations | Reference |
| Operations | Runbooks and procedures | Reference |
| Reference | Detailed specs | Reference |

---

## Root-Level Archived Files (18)

**Implementation & Design (8)**
- QUALITY-GATE-TEST-FRAMEWORK.md
- QUALITY-BASELINES.md
- SPEC-VALIDATION-FRAMEWORK.md
- PROTOCOL-MIGRATION-GUIDE.md
- OPENCODE-CONFIG-VALIDATION-GUIDE.md
- OPENCODE-HOOKS-INTEGRATION.md
- implementation-workflow.md
- AUTOMATIC-INVOCATION.md

**Configuration & Setup (3)**
- OPENCODE-CONFIG-COMMON-MISTAKES.md
- OPENCODE-TOKEN-VISIBILITY-SOLUTION.md
- cleanup.md

**Roadmaps & Analysis (2)**
- TESTING-ROADMAP-CONCURRENT-AGENTS.md
- model-implementation-roadmap.md

**Operational & Testing (5)**
- cicd-monitoring.md
- cloudwatch-queries.md
- test-business-logic.md
- test-e2e-orchestration.md
- test-integration-orchestration.md
- test-unit-orchestration.md
- security-dependency-scan.md
- security-secret-detection.md
- security-semantic-scan.md
- planning-standard.md

---

## Organized Subdirectories

- **FRAMEWORKS/** — AI framework research & analysis
- **architecture/** — Architecture decisions & exploration
- **decisions/** — Architecture Decision Records (ADRs)
- **operations/** — Operational runbooks & procedures
- **reference/** — Reference documentation & specs
- **runbooks/** — Incident response procedures
- **specs/** — Detailed specifications

---

## Categorization Rationale

### Why Archived

1. Historical/Completed initiatives
2. Implementation details better served by code
3. Design docs that have been implemented
4. Rarely-referenced supplementary materials
5. Reduce root-level cognitive load

### What Stays Active

**21 core documents** for:
- Protocol and architecture
- Agent routing and skills
- Quality standards
- Setup and onboarding
- Token tracking and operations

---

## Accessing Archived Docs

```bash
# Find by name
find docs/archive -name "*quality*"

# Search content
grep -r "PHASE" docs/archive/

# Browse by category
ls -la docs/archive/FRAMEWORKS/
```

---

## Maintenance

- Add new archives as docs become historical
- Remove if doc becomes active again
- Quarterly review of archive contents
- Annual consolidation/cleanup

---

**See Also:**
- [../INDEX.md](../INDEX.md) — Active documentation
- [../../DOCS_AUDIT_REPORT.md](../../DOCS_AUDIT_REPORT.md) — Audit report
