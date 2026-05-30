# Cross-Reference Map: Session Task Dependencies & Relationships

## Session: test-session-mgr-001

### Task Dependency Graph

```
TASK-LINTING-GATES-001 (FOUNDATION)
├── Enables: TASK-TEST-ENVIRONMENT-SIMULATION-001
├── Enables: TASK-CI-PATH-SYMLINK-IMPL-001
├── Supports: SKILL-code-hygiene-git-workflow
└── Used by: All subsequent tasks

TASK-TEST-ENVIRONMENT-SIMULATION-001
├── Depends on: TASK-LINTING-GATES-001
├── Tests: TASK-CI-PATH-SYMLINK-IMPL-001
└── Validates: Container environment compatibility

TASK-CI-PATH-SYMLINK-IMPL-001 (CRITICAL PATH)
├── Depends on: TASK-LINTING-GATES-001
├── Fixes: 22 CI failures from run #26669403874
├── Enables: TASK-SECURITY-ANALYSIS-GAPS-001
└── Required by: TASK-QUEUE-PROTOCOL-INTEGRATION-001

TASK-SECURITY-ANALYSIS-GAPS-001
├── Investigates: Queue/protocol architecture
├── Identifies: 5 critical gaps + remediation roadmap
└── Feeds into: Phase 2 planning

TASK-QUEUE-PROTOCOL-INTEGRATION-001 (INVESTIGATION)
├── Depends on: All previous tasks (for context)
├── Documents: 5 gaps, Phase 2 roadmap
└── Recommends: 5 Phase 2 implementation tasks

SKILL-code-hygiene-git-workflow
├── Motivated by: TASK-LINTING-GATES-001
└── Used by: All future TASK implementations

SKILL-add-feature-to-framework
├── Motivated by: TASK-QUEUE-PROTOCOL-INTEGRATION-001
└── Used by: All future feature work
```

### Task Relationships

| Source | Target | Relationship | Type |
|--------|--------|--------------|------|
| TASK-LINTING-GATES-001 | TASK-TEST-ENVIRONMENT-SIMULATION-001 | Sequential | Enabler→Extender |
| TASK-TEST-ENVIRONMENT-SIMULATION-001 | TASK-CI-PATH-SYMLINK-IMPL-001 | Sequential | Enabler→Implementation |
| TASK-CI-PATH-SYMLINK-IMPL-001 | TASK-SECURITY-ANALYSIS-GAPS-001 | Parallel | Context |
| TASK-SECURITY-ANALYSIS-GAPS-001 | TASK-QUEUE-PROTOCOL-INTEGRATION-001 | Parallel | Related Investigation |
| TASK-LINTING-GATES-001 | SKILL-code-hygiene-git-workflow | Codification | Process Documentation |
| TASK-QUEUE-PROTOCOL-INTEGRATION-001 | SKILL-add-feature-to-framework | Motivation | Process Documentation |

### HANDBACK Artifact Locations

All HANDBACKs: `.agentic-engineers/queue/done/`

- HANDBACK-TASK-LINTING-GATES-001-20260530T121500Z.yaml
- HANDBACK-TASK-TEST-ENVIRONMENT-SIMULATION-001-20260530T121500Z.yaml
- HANDBACK-TASK-SECURITY-ANALYSIS-GAPS-001-20260530T121500Z.yaml
- HANDBACK-TASK-CI-PATH-SYMLINK-IMPL-001-20260530T121500Z.yaml
- HANDBACK-TASK-QUEUE-PROTOCOL-INTEGRATION-001-20260530T121500Z.yaml
- HANDBACK-SKILL-code-hygiene-git-workflow-20260530T121500Z.yaml
- HANDBACK-SKILL-add-feature-to-framework-20260530T121500Z.yaml

### Session Files

- index.json (searchable task metadata)
- DECISIONS.md (decision log)
- CROSS-REFERENCES.md (this file)

---

## For Future Sessions

To query this session's artifacts:

```bash
# Find all tasks
jq '.tasks | keys' .agentic-engineers/session-001/index.json

# Find HANDBACK artifacts
ls .agentic-engineers/queue/done/HANDBACK-*

# Review decisions
cat .agentic-engineers/session-001/DECISIONS.md

# View task metadata
cat .agentic-engineers/session-001/index.json | jq '.metrics'
```

**Created:** 2026-05-30T12:30:00Z
