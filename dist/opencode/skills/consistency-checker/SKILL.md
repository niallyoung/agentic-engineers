---
name: consistency-checker
description: Automated cross-validation of protocol queue integrity. Scans all DELEGATEs/HANDBACKs, validates schema compliance, detects cycles, checks rate limits, generates compliance report. Enables self-referential protocol improvements.
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.8+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: validation
  role: orchestrator
  model: claude-haiku-4.5
  effort: high
  thinking: false
  dependencies:
    - protocol-validator
    - queue-management
---

# consistency-checker

## Overview

Consistency-Checker skill provides automated cross-validation of the DELEGATE/HANDBACK queue.
It scans all tasks in all queue states, validates schema compliance, detects structural issues
(cycles, orphans), checks rate limits, and generates a detailed compliance report.

**What it does:**

1. **Queue Scanning** — Scan all DELEGATEs in queue (incoming/, assigned/, completed/)
2. **Schema Validation** — Run protocol-validator on each task (core + extensions)
3. **Structural Validation** — Detect parent/child chain issues (orphans, cycles, depth/width violations)
4. **Rate Limit Checking** — Verify per-session and per-parent rate limits not exceeded
5. **Report Generation** — Aggregate results: pass/fail counts, violations, warnings, stats
6. **Escalation** — Flag violations for Orchestrator or Model Engineer investigation

**Why it matters:**

- **Queue Health Monitoring** — Automated integrity checks prevent silent data corruption
- **Backward Compatibility** — Validate entire queue against new protocol versions
- **Cycle Detection** — Prevent infinite loops in task delegation chains
- **Performance Baseline** — Identify slow/expensive tasks for optimization
- **Self-Referential** — Validate protocol improvements before deployment (95%+ pass rate required)

---

## Invocation

### Programmatic Interface

```python
from skills.consistency_checker.scripts import ConsistencyChecker

# Initialize
checker = ConsistencyChecker(
    queue_path="~/.copilot/queue",
    session_id=None,  # None = check all sessions
)

# Run full check
report = checker.check_queue()

# Inspect results
print(f"Total tasks: {report.total_tasks}")
print(f"Valid: {report.valid_count}")
print(f"Invalid: {report.invalid_count}")
print(f"Pass rate: {report.pass_rate:.1%}")

if report.violations:
    print("Violations:")
    for violation in report.violations:
        print(f"  - {violation}")

if report.warnings:
    print("Warnings:")
    for warning in report.warnings:
        print(f"  - {warning}")
```

### CLI Interface

```bash
# Check all sessions in queue
python -m skills.consistency_checker

# Check specific session
python -m skills.consistency_checker --session my-session

# Check and save report
python -m skills.consistency_checker --report results/consistency-report.json

# Check against custom spec
python -m skills.consistency_checker --spec path/to/custom-spec.yaml

# Check with verbose output
python -m skills.consistency_checker --verbose

# Check only DELEGATEs (skip HANDBACKs)
python -m skills.consistency_checker --delegates-only
```

---

## Queue Scanning

### Queue Structure

The checker scans this directory structure:

```
~/.copilot/queue/
├── {session_id}/
│   ├── incoming/       # New tasks waiting to be processed
│   ├── assigned/       # Tasks currently being processed
│   ├── completed/      # Finished tasks (success/failure)
│   └── metadata/       # Rate limit tracking per parent
├── {other_session}/
└── ...
```

Each queue state contains YAML files named `{task_id}.yaml` or `{task_id}.json`.

### Scan Algorithm

1. **Discover Sessions** — Find all session directories
2. **Discover Tasks** — Find all task files in each session
3. **Load Tasks** — Read and parse each task YAML/JSON
4. **Validate Schema** — Run protocol-validator on each
5. **Check Structure** — Validate parent/child chains
6. **Check Limits** — Verify rate limits per parent and session
7. **Aggregate Report** — Collect all violations and stats

---

## Validation Rules

### Schema Compliance

Each DELEGATE is validated against `docs/specs/protocol-core-v1.0.yaml`:
- Core fields must be present and valid
- Extensions must be valid (loose validation)
- Unknown fields logged as warnings (don't fail)

### Structural Validation

**Parent/Child Chains:**
- All tasks with @parent_task_id must have parent in same session
- No cycles: A→B→C→A is forbidden (detected via DFS)
- Max depth: 5 levels (A→B→C→D→E→F fails)
- Max width: 10 children per parent (11+ children fails)

**Orphans:**
- Task references non-existent parent => violation
- Orphaned tasks are flagged but don't fail overall check

**Cycles:**
- DFS with visited set detects cycles in parent chains
- Cycle detected => violation with cycle path (A→B→C→A)

### Rate Limiting

**Per-Session:**
- Max 100 tasks per hour
- Sliding window: current_hour - 1 hour
- Violation: count > 100 in current hour

**Per-Parent:**
- Max 10 children per parent
- Violation: parent.children_count > 10

---

## Report Format

### ConsistencyReport Dataclass

```python
@dataclass
class ConsistencyReport:
    timestamp: str  # ISO 8601 when check ran
    duration_seconds: float  # Check execution time
    
    # Counts
    total_tasks: int
    valid_count: int
    invalid_count: int
    warning_count: int
    
    # Rates
    pass_rate: float  # valid_count / total_tasks
    
    # Details
    violations: List[str]  # Core validation failures
    warnings: List[str]  # Schema warnings, unknown fields
    stats: Dict[str, Any]  # Aggregated statistics
    
    # Breakdown by queue state
    by_state: Dict[str, StateStats]
    # by_state['incoming'] = StateStats(total=50, valid=49, invalid=1)
    # by_state['assigned'] = StateStats(total=10, valid=10, invalid=0)
    # by_state['completed'] = StateStats(total=2000, valid=1999, invalid=1)
```

### Example Report

```json
{
  "timestamp": "2025-01-15T14:23:45Z",
  "duration_seconds": 1.234,
  "total_tasks": 2060,
  "valid_count": 2045,
  "invalid_count": 15,
  "warning_count": 3,
  "pass_rate": 0.9927,
  "violations": [
    "Task 'orphan-task-001': parent 'parent-nonexistent' not found in session",
    "Task 'cycle-a': cycle detected: cycle-a → cycle-b → cycle-c → cycle-a",
    "Task 'deep-task-006': chain depth 7 exceeds max depth of 5"
  ],
  "warnings": [
    "Task 'task-001': unknown field 'future_field'",
    "Task 'task-002': deprecated extension field 'old_field'"
  ],
  "stats": {
    "schema_validation_ms": 234,
    "structural_validation_ms": 567,
    "rate_limit_check_ms": 89,
    "total_validation_ms": 890,
    "avg_task_ms": 0.43
  },
  "by_state": {
    "incoming": {"total": 50, "valid": 49, "invalid": 1},
    "assigned": {"total": 10, "valid": 10, "invalid": 0},
    "completed": {"total": 2000, "valid": 1986, "invalid": 14}
  }
}
```

---

## Self-Referential Protocol Improvement Workflow

Consistency-Checker enables protocol improvements via DELEGATE/HANDBACK:

### Workflow

1. **Propose** — Create DELEGATE with @scope='protocol-improvement'
   ```yaml
   task_id: protocol-add-retry-count
   scope: Add optional 'retry_count' field to HANDBACK extensions for retry tracking
   plan:
     - Define new field in spec
     - Update validation rules
     - Run consistency-checker on existing queue
     - Approve if pass rate >=95%
   ```

2. **Validate** — Consistency-checker loads proposed spec
   - Scan entire queue against new spec
   - Count pass/fail/warnings
   - Calculate pass rate

3. **Decide** — Approve or reject based on pass rate
   - If pass_rate ≥ 95%: Approve (new field deployed)
   - If pass_rate < 95%: Reject (old spec remains)
   - Report: which tasks would fail, impact analysis

4. **Deploy** — If approved, orchestrator deploys new spec
   - Update docs/specs/protocol-core-v1.0.yaml
   - Orchestrator restarts (loads new spec)
   - All future tasks use new schema

### Example: Adding a New Field

Original spec:
```yaml
handback:
  extensions:
    retry_count: {type: integer}  # ADD THIS FIELD
```

Run check:
```bash
python -m skills.consistency_checker \
  --spec docs/specs/protocol-core-v1.0-proposed.yaml \
  --report results/protocol-impact-report.json
```

Report:
```json
{
  "pass_rate": 0.9987,  # 1999/2000 tasks pass (1 has invalid retry_count)
  "violations": [
    "Task 'old-task-123': retry_count must be integer (got string '3')"
  ]
}
```

Decision: Pass rate = 99.87% ≥ 95% ✅ Approved → Deploy new spec

---

## Integration with Orchestrator

The Orchestrator should invoke consistency-checker:

1. **On Heartbeat** — Run every hour (configurable)
   ```python
   if orchestrator.heartbeat % 60 == 0:  # Every 60 heartbeats (1 hour)
       checker = ConsistencyChecker()
       report = checker.check_queue()
       if report.pass_rate < 0.95:
           alert(f"Queue integrity issue: {report.pass_rate:.1%}")
   ```

2. **On Protocol Change** — Run before deployment
   ```python
   # Validate protocol change
   old_report = check_with_spec("docs/specs/protocol-core-v1.0.yaml")
   new_report = check_with_spec("docs/specs/protocol-core-v1.0-proposed.yaml")
   
   if new_report.pass_rate >= 0.95:
       deploy_new_spec()
   else:
       reject_protocol_change(new_report)
   ```

3. **On Escalation** — If Model Engineer requests integrity audit
   ```python
   report = checker.check_queue()
   model_engineer.report_queue_health(report)
   ```

---

## Performance Characteristics

- **Queue Size: 2,000 tasks** → Check time: ~1-2 seconds
- **Per-task time** → <1ms (validation + structural check)
- **Report generation** → <100ms (aggregation)
- **Total** → <2 seconds for typical queue

### Optimization Tips

- Run consistency-checker in background (don't block queue processing)
- Cache results for 1 hour (queue doesn't change that fast)
- Check only "hot" sessions (active in last 24h)
- For large queues, parallelize by session

---

## Testing

### Unit Tests

```python
def test_check_queue_returns_report():
    """check_queue() returns ConsistencyReport"""

def test_detect_orphaned_parent():
    """Task with non-existent parent_task_id flagged as violation"""

def test_detect_cycle_in_chain():
    """Cycle A→B→C→A detected via DFS"""

def test_rate_limit_per_parent():
    """Parent with 11 children fails rate limit check"""

def test_schema_validation_per_task():
    """Each task validated against protocol spec"""

def test_backward_compatibility_phase3():
    """All Phase 1-3 tasks pass validation"""

def test_pass_rate_calculation():
    """pass_rate = valid_count / total_tasks"""

def test_aggregated_report_generation():
    """Report includes all violations, warnings, stats"""
```

### Coverage Target

- **Line Coverage** — ≥90%
- **Critical Paths** — 100% (cycle detection, schema validation)

---

## References

- `docs/specs/protocol-core-v1.0.yaml` — Protocol specification
- `skills/protocol-validator/` — Schema validation
- `skills/queue-management/` — Queue operations
- `docs/SELF-REFERENTIAL-WORKFLOW.md` — Protocol improvement workflow
- `docs/PROTOCOL.md` — Canonical protocol reference

---

## Version History

### v1.0 (Current)
- Initial release with Phase 4 implementation
- Full queue scanning and validation
- Cycle detection and rate limit checking
- Report generation for self-referential workflow
