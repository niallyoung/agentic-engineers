# Self-Referential Protocol Workflow

## Overview

The self-referential protocol workflow enables the DELEGATE/HANDBACK protocol to improve itself via the same DELEGATE/HANDBACK system it governs. Protocol improvements are proposed, validated, and approved through the queue system itself.

**Key principle:** The protocol can evolve without external intervention. Any protocol change is validated against the existing queue before deployment.

---

## Workflow Phases

### Phase 1: Propose

A human or agent proposes a protocol improvement:

```yaml
@task_id: protocol-add-retry-count
@skill: protocol-validator
@agent: principal-engineer
@scope: Add optional 'retry_count' field to HANDBACK extensions for improved retry tracking and diagnostics
@success_criteria:
  - New field added to protocol spec
  - All existing HANDBACKs validate against new spec
  - No breaking changes to Phase 1-3 tasks
  - Test coverage >=95%
@plan:
  - Define new field in specs/protocol-core-v1.0-proposed.yaml
  - Add validation rules to extension validator
  - Run consistency-checker against existing queue
  - If pass rate >=95%, approve for deployment
  - Update specs/protocol-core-v1.0.yaml with new field
  - Update protocol-validator to load new spec
@context: |
  Retry tracking is needed for improved diagnostics of task failures and recovery patterns.
  Current protocol lacks explicit retry_count field, making it hard to track retry behavior.
  Proposed addition is optional (extension field), maintaining backward compatibility.
  See RETRY-TRACKING-SPEC.md for detailed requirements.
@effort: medium
@parent_task_id: null  # Top-level protocol improvement
```

### Phase 2: Validate

The Orchestrator routes this to Principal Engineer or Quality Engineer. Validator:

1. **Loads Proposed Spec** — Read `specs/protocol-core-v1.0-proposed.yaml`
2. **Validates Consistency** — Run consistency-checker against existing queue with new spec
3. **Calculates Impact** — Report pass rate, violations, affected tasks
4. **Generates Report** — Create HANDBACK with validation results

Example validation:

```bash
# Step 1: Create proposed spec (with new retry_count field)
cp specs/protocol-core-v1.0.yaml specs/protocol-core-v1.0-proposed.yaml
# ... edit to add field ...

# Step 2: Run consistency-checker
python -m skills.consistency_checker \
  --spec specs/protocol-core-v1.0-proposed.yaml \
  --report results/protocol-impact-report.json

# Step 3: Check pass rate
jq '.pass_rate' results/protocol-impact-report.json
# 0.9987  => 1999/2000 tasks pass, 1 fails
```

### Phase 3: Decide & Approve

Based on pass rate, approve or reject:

**If pass_rate ≥ 95% (≤5% of tasks fail):**
- ✅ **Approve** — Protocol change is safe
- Deploy new spec to production
- All future tasks use new schema
- Old tasks still validate (backward-compatible)

**If pass_rate < 95% (>5% of tasks fail):**
- ❌ **Reject** — Protocol change requires migration
- Identify which tasks fail and why
- Create migration plan (data cleanup, field updates, etc.)
- Propose revised change or post-migration cleanup task

### Phase 4: Deploy

Once approved, orchestrator deploys:

```python
# Orchestrator startup sequence
if new_spec_approved():
    # 1. Back up old spec
    shutil.copy('specs/protocol-core-v1.0.yaml', 
                'specs/protocol-core-v1.0-backup.yaml')
    
    # 2. Deploy new spec
    shutil.move('specs/protocol-core-v1.0-proposed.yaml',
                'specs/protocol-core-v1.0.yaml')
    
    # 3. Reinitialize validators
    validator = ProtocolValidator(spec_path='specs/protocol-core-v1.0.yaml')
    
    # 4. Log deployment
    logger.info("Protocol spec upgraded to v1.0 with new field: retry_count")
```

---

## Decision Criteria

### Approval Threshold: 95% Pass Rate

- **Pass rate ≥ 95%** → Safe to deploy (backward-compatible, no migration needed)
- **Pass rate < 95%** → Requires migration or redesign

### Rationale for 95%

1. **Real-World Reliability** — 95% pass rate allows for occasional edge cases
2. **Operational Feasibility** — Teams can handle <5% broken tasks post-deployment
3. **Balance** — Strict enough to prevent breaking changes, loose enough to allow evolution
4. **Industry Standard** — Similar to SRE error budgets (99.9% uptime → 0.1% errors)

### Special Cases

**Critical Security Fix:**
- Override 95% threshold if security issue requires immediate deployment
- Document rationale in HANDBACK with `@flags: ['security-override']`

**Deprecation:**
- Removing a field requires 100% pass rate (all tasks use new schema) OR migration task
- Deprecations should be communicated 2-3 phases in advance

---

## Examples

### Example 1: Adding Optional Field (Low Risk)

**Proposal:** Add `@retry_count` field to HANDBACK extensions

**Validation Result:**
```json
{
  "pass_rate": 0.9987,
  "total_tasks": 2000,
  "valid_count": 1999,
  "invalid_count": 1,
  "violations": [
    "Task 'old-task-with-bad-retry': retry_count must be integer (got string '3')"
  ]
}
```

**Decision:** ✅ **Approve** (99.87% > 95%)

**Action:** Deploy new spec immediately. Old task is a data quality issue (unrelated to protocol).

---

### Example 2: Changing Required Field (High Risk)

**Proposal:** Make `@parent_task_id` required in DELEGATE

**Validation Result:**
```json
{
  "pass_rate": 0.75,
  "total_tasks": 2000,
  "valid_count": 1500,
  "invalid_count": 500,
  "violations": [
    "Task 'standalone-task-001': parent_task_id is required but missing",
    "Task 'standalone-task-002': parent_task_id is required but missing",
    "... (498 more)"
  ]
}
```

**Decision:** ❌ **Reject** (75% < 95%)

**Action:** 
- Analyze 500 standalone tasks
- Create migration task: "Audit standalone tasks and add parent_task_id or redesign"
- Propose change again after migration

---

### Example 3: Field Validation Improvement (Medium Risk)

**Proposal:** Tighten `@scope` word count from 15 to 20 words

**Validation Result:**
```json
{
  "pass_rate": 0.92,
  "total_tasks": 2000,
  "valid_count": 1840,
  "invalid_count": 160,
  "violations": [
    "Task 'quick-task-001': scope must be >=20 words (13 provided)",
    "... (159 more)"
  ]
}
```

**Decision:** ❌ **Reject** (92% < 95%, but close)

**Options:**
1. Keep threshold at 15 (current standard)
2. Compromise: 17 words (affects 80 tasks, ~96% pass rate)
3. Create cleanup task: "Audit and improve short scopes"

---

## Implementation in Orchestrator

### Integration Points

**1. Startup** — Load spec and initialize validator:
```python
# orchestrator/__init__.py
self.validator = ProtocolValidator(spec_path='specs/protocol-core-v1.0.yaml')
self.consistency_checker = ConsistencyChecker()
```

**2. On DELEGATE Creation** — Validate before queueing:
```python
# orchestrator/queue_ops.py
def create_delegate(self, delegate_dict):
    result = self.validator.validate_delegate(delegate_dict)
    if not result.valid:
        raise ValidationError(f"Invalid DELEGATE: {result.errors}")
    self.queue.create_delegate(delegate_dict)
```

**3. On HANDBACK Acceptance** — Validate before processing:
```python
# orchestrator/handback_handler.py
def accept_handback(self, handback_dict):
    result = self.validator.validate_handback(handback_dict)
    if not result.valid:
        raise ValidationError(f"Invalid HANDBACK: {result.errors}")
    self.queue.accept_handback(handback_dict)
```

**4. On Heartbeat** — Run consistency check hourly:
```python
# orchestrator/heartbeat.py
if self.heartbeat_count % 60 == 0:  # Every 60 heartbeats = 1 hour
    report = self.consistency_checker.check_queue()
    if report.pass_rate < 0.95:
        logger.warning(f"Queue integrity: {report.pass_rate:.1%}")
        self.model_engineer.alert(report)
```

**5. On Protocol Change Proposal** — Validate impact:
```python
# orchestrator/protocol_handler.py
def handle_protocol_improvement_delegate(self, delegate):
    # Extract proposed spec from delegate
    proposed_spec = delegate['context']  # or load from file
    
    # Run consistency check with proposed spec
    checker = ConsistencyChecker(spec_path=proposed_spec)
    report = checker.check_queue()
    
    # Create HANDBACK with results
    return {
        'task_id': delegate['task_id'],
        'status': 'success' if report.pass_rate >= 0.95 else 'partial',
        'output': asdict(report),
        'metrics': {...},
    }
```

---

## Protocol Versioning

### Semantic Versioning

- **Major (1.0 → 2.0)** — Breaking changes (required field removed, core structure changed)
- **Minor (1.0 → 1.1)** — New optional fields, new enums
- **Patch (1.0 → 1.0.1)** — Validation rule tightening, docs

### Version Tracking

```yaml
# specs/protocol-core-v1.0.yaml
version: "1.0"
released_date: "2025-01-15"
next_proposed_version: "1.1"  # What's being worked on

delegate:
  ...

handback:
  ...
```

### Migration Guide

For major version bumps, create migration guide:
- What changed
- How to update existing tasks
- Timeline (e.g., "v1.x supported for 90 days")
- Automated migration tools (if applicable)

---

## Audit Trail

All protocol changes are recorded:

```python
# logs/protocol-changes.log
2025-01-15T14:23:45Z | PROPOSED | protocol-add-retry-count | v1.0 → v1.1
2025-01-15T14:30:12Z | VALIDATED | pass_rate=99.87% | violations=1
2025-01-15T14:31:00Z | APPROVED | deploying v1.1
2025-01-15T14:31:15Z | DEPLOYED | v1.1 active | tasks using new spec: all future
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Deploy breaking change | 95% pass rate threshold prevents this |
| Inconsistent validation | Test validators against same queue twice — must get same results |
| Performance regression | Benchmark validation time before/after |
| Dependency loop | Validators don't depend on orchestrator, only on queue |
| Spec corruption | Back up old spec before deploying new one |

---

## Governance

### Who Can Propose?

- Principal Engineer (architectural changes)
- Lead Engineer (field additions, rule tightening)
- Security Engineer (security-related changes)
- Model Engineer (performance-related changes)

### Approval Authority

- **Minor Changes** (new optional fields): Lead Engineer
- **Validation Rules**: Quality Engineer
- **Major Changes** (breaking, removal): Principal Engineer + Orchestrator team

### Escalation Path

If pass rate 85-94% (borderline):
1. Analyze failures (which tasks fail and why?)
2. Decide: reject, compromise, or create migration task
3. Document reasoning in ADR (Architecture Decision Record)

---

## Future Enhancements

1. **Gradual Rollout** — Deploy new spec to 10% of tasks first, monitor, then 100%
2. **Automatic Migration** — AI-generated migration tasks for common failures
3. **A/B Testing** — Compare metrics under old vs. new spec
4. **Version Negotiation** — Agents can request old spec if new one breaks them
5. **Spec Branching** — Maintain multiple spec versions for different use cases

---

## See Also

- `specs/protocol-core-v1.0.yaml` — Protocol specification
- `skills/protocol-validator/SKILL.md` — Validation rules
- `skills/consistency-checker/SKILL.md` — Queue integrity checking
- `docs/PROTOCOL.md` — Protocol reference
- `docs/PROTOCOL-MIGRATION-GUIDE.md` — Migration guide for major versions
