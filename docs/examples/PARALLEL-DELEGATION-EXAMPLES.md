# Parallel Delegation Examples

**Detailed, real-world examples of parallel delegation in action.**

---

## Table of Contents

1. [Example 1: Security Audit (4 Services)](#example-1-security-audit-4-services)
2. [Example 2: Database Migration (10 Databases)](#example-2-database-migration-10-databases)
3. [Example 3: Code Review (5 Repositories)](#example-3-code-review-5-repositories)
4. [Example 4: Feature Implementation (3 Services)](#example-4-feature-implementation-3-services)
5. [Example 5: Handling Partial Failures](#example-5-handling-partial-failures)

---

## Example 1: Security Audit (4 Services)

### Scenario

Audit security in 4 payment services (Stripe, PayPal, Crypto, Square) for vulnerabilities, dependency issues, and compliance gaps.

**Requirements:**
- All 4 services must be audited
- Results must be aggregated into consolidated report
- Wall-clock time critical (deadline: 4 hours)
- Token cost not critical

**Sequential approach (old):**
- 1 Security Engineer audits all 4 services sequentially
- 1 hour per service × 4 = 4 hours wall-clock
- Cost: $0.30

**Parallel approach (new):**
- 1 Senior Engineer creates 4 sub-tasks
- 4 Security Engineers audit in parallel
- 1 hour wall-clock (vs. 4 hours)
- Cost: $0.30 (same)
- **Benefit: 3 hours saved (75% faster)**

### Implementation

#### Step 1: Orchestrator Creates Parent Task

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-16-security-audit-payments-001
role: senior_engineer
model: claude-sonnet-4-6
effort: high
scope: >
  Coordinate security audit of all 4 payment services (Stripe, PayPal, Crypto, Square).
  Ensure all services are audited for vulnerabilities, dependency issues, and compliance gaps.
  Produce consolidated security report with prioritized remediation plan.
context:
  - Deadline: 4 hours
  - Services: Stripe, PayPal, Crypto, Square
  - Focus: Vulnerabilities, dependencies, compliance
  - Related: docs/security-audit-checklist.md
plan:
  1. Create sub-task for each of 4 services
  2. Wait for all audits to complete (60-minute timeout)
  3. Aggregate findings into consolidated report
  4. Prioritize remediation by severity
  5. Document recommendations
success_criteria:
  - All 4 services audited
  - Consolidated report completed
  - Remediation plan prioritized
  - No critical findings left undocumented
---
```

#### Step 2: Senior Engineer Creates 4 Child Tasks

```python
from skills.queue_management.scripts.queue_ops import QueueOperations

ops = QueueOperations(queue_dir="/path/to/queue", session_id="security-audit-001")

services = [
    {
        "name": "stripe",
        "repo": "stripe-integration/",
        "focus": "Payment processing, webhook handling, key management"
    },
    {
        "name": "paypal",
        "repo": "paypal-integration/",
        "focus": "OAuth flow, API security, error handling"
    },
    {
        "name": "crypto",
        "repo": "crypto-integration/",
        "focus": "Key rotation, entropy, rate limiting"
    },
    {
        "name": "square",
        "repo": "square-integration/",
        "focus": "Card handling, PCI compliance, data encryption"
    }
]

for service in services:
    ops.create_delegate(
        task_id=f"2026-05-16-security-audit-{service['name']}-001",
        role="security_engineer",
        model="claude-opus-4-7",
        effort="max",
        scope=f"Conduct comprehensive security audit of {service['name']} payment service. "
              f"Identify vulnerabilities, dependency issues, and compliance gaps. "
              f"Focus on: {service['focus']}",
        context=[
            f"Parent task: 2026-05-16-security-audit-payments-001",
            f"Repository: {service['repo']}",
            f"Focus areas: {service['focus']}",
            f"Related: docs/security-audit-checklist.md",
            f"Deadline: 1 hour from now"
        ],
        plan=[
            f"Review {service['name']} integration code for security issues",
            "Check all dependencies against CVE database",
            "Analyze authentication and authorization flows",
            "Review error handling and logging",
            "Check compliance requirements (PCI, GDPR, etc.)",
            "Document findings with severity levels",
            "Provide remediation recommendations"
        ],
        success_criteria=[
            f"Security audit of {service['name']} completed",
            "All vulnerabilities documented with severity",
            "All CVEs identified and documented",
            "Compliance gaps identified",
            "Remediation recommendations provided"
        ],
        parent_task_id="2026-05-16-security-audit-payments-001",
    )
```

#### Step 3: Orchestrator Routes 4 Children to 4 Security Engineers

```
Time  Parent Task         Stripe Audit    PayPal Audit    Crypto Audit    Square Audit
────  ─────────────────   ─────────────   ─────────────   ─────────────   ─────────────
 0:00 ├─ Receives DELEGATE
 0:05 ├─ Creates 4 children
 0:10 ├─ Returns HANDBACK
      │  (children_created=[...])
      │
 0:10 │                   ├─ Assigned      ├─ Assigned      ├─ Assigned      ├─ Assigned
 0:15 │                   ├─ Starts audit  ├─ Starts audit  ├─ Starts audit  ├─ Starts audit
      │
 0:30 │ ├─ Detects 4 children
 0:30 │ ├─ Starts waiting...
      │
 1:00 │                   ├─ Completes    ├─ Completes    ├─ Completes    ├─ Completes
 1:05 │ ├─ All children done
 1:05 │ ├─ Aggregates results
 1:10 │ ├─ Writes parent HANDBACK
 1:10 │ └─ Moves to done/

Wall-clock: 1 hour 10 minutes (vs. 4+ hours if sequential)
```

#### Step 4: Each Security Engineer Returns HANDBACK

**Stripe Audit HANDBACK:**
```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-16-security-audit-stripe-001
status: complete
deliverables:
  - Report: stripe-security-audit.md
  - Findings: 2 critical, 3 high, 1 medium
tests:
  - Manual code review: COMPLETE
  - Dependency scan: COMPLETE (using OWASP DependencyCheck)
  - Compliance check: COMPLETE
tokens_in: 2400
tokens_out: 1800
model: claude-opus-4-7
effort: max
duration_minutes: 55
escalations: 0
notes: "Stripe integration has 2 critical issues: webhook validation missing in error path, rate limiting insufficient. Recommend immediate remediation."
---
```

**PayPal Audit HANDBACK:**
```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-16-security-audit-paypal-001
status: complete
deliverables:
  - Report: paypal-security-audit.md
  - Findings: 0 critical, 1 high, 2 medium
tests:
  - Manual code review: COMPLETE
  - Dependency scan: COMPLETE
  - Compliance check: COMPLETE
tokens_in: 2200
tokens_out: 1600
model: claude-opus-4-7
effort: max
duration_minutes: 58
escalations: 0
notes: "PayPal integration is well-secured. One high-severity issue: dependency paypal-sdk@2.1.0 has CVE-2025-1234. Recommend upgrade to 2.2.0."
---
```

**Crypto Audit HANDBACK:**
```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-16-security-audit-crypto-001
status: complete
deliverables:
  - Report: crypto-security-audit.md
  - Findings: 1 critical, 2 high, 3 medium
tests:
  - Manual code review: COMPLETE
  - Dependency scan: COMPLETE
  - Compliance check: COMPLETE
tokens_in: 2500
tokens_out: 1900
model: claude-opus-4-7
effort: max
duration_minutes: 60
escalations: 0
notes: "Crypto integration has critical issue: key rotation not implemented. Also: weak entropy source (Math.random), no rate limiting. Recommend immediate action."
---
```

**Square Audit HANDBACK:**
```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-16-security-audit-square-001
status: complete
deliverables:
  - Report: square-security-audit.md
  - Findings: 0 critical, 0 high, 1 medium
tests:
  - Manual code review: COMPLETE
  - Dependency scan: COMPLETE
  - Compliance check: COMPLETE
tokens_in: 2100
tokens_out: 1500
model: claude-opus-4-7
effort: max
duration_minutes: 52
escalations: 0
notes: "Square integration is well-secured. Only minor issue: logging could be more detailed for audit trails. Otherwise excellent security posture."
---
```

#### Step 5: Orchestrator Aggregates Results

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-16-security-audit-payments-001
status: complete
deliverables:
  - Consolidated report: payment-security-audit-consolidated.md
  - Summary: 3 critical, 6 high, 7 medium findings across 4 services
  - Remediation plan: prioritized by severity and impact
children_created:
  - 2026-05-16-security-audit-stripe-001
  - 2026-05-16-security-audit-paypal-001
  - 2026-05-16-security-audit-crypto-001
  - 2026-05-16-security-audit-square-001
children_results:
  2026-05-16-security-audit-stripe-001:
    status: complete
    output:
      critical: 2
      high: 3
      medium: 1
      findings:
        - "Webhook validation missing in error path"
        - "Rate limiting insufficient for DDoS protection"
    quality: 92
  2026-05-16-security-audit-paypal-001:
    status: complete
    output:
      critical: 0
      high: 1
      medium: 2
      findings:
        - "Dependency paypal-sdk@2.1.0 has CVE-2025-1234"
    quality: 88
  2026-05-16-security-audit-crypto-001:
    status: complete
    output:
      critical: 1
      high: 2
      medium: 3
      findings:
        - "Key rotation not implemented"
        - "Entropy source weak (Math.random)"
        - "No rate limiting on API calls"
    quality: 85
  2026-05-16-security-audit-square-001:
    status: complete
    output:
      critical: 0
      high: 0
      medium: 1
      findings:
        - "Logging could be more detailed for audit trails"
    quality: 95
children_failed: []
result_aggregation_status: all_complete
tokens_in: 9200
tokens_out: 6800
model: claude-sonnet-4-6
effort: high
duration_minutes: 70
escalations: 0
notes: >
  All 4 services audited in parallel. Stripe and Crypto require immediate attention (3 critical findings total).
  PayPal has 1 high-severity dependency issue (easy fix). Square is well-secured.
  Recommend prioritized remediation plan: (1) Stripe webhook validation, (2) Crypto key rotation,
  (3) Crypto entropy source, (4) PayPal dependency upgrade.
---
```

**Quality aggregation:**
```
Children: [92, 88, 85, 95] with efforts [max, max, max, max]
Weights: [3, 3, 3, 3]
Numerator: (92×3) + (88×3) + (85×3) + (95×3) = 276 + 264 + 255 + 285 = 1080
Denominator: 3 + 3 + 3 + 3 = 12
Result: 1080 / 12 = 90.0
```

---

## Example 2: Database Migration (10 Databases)

### Scenario

Migrate 10 databases from PostgreSQL 12 to PostgreSQL 15 with schema updates.

**Requirements:**
- All 10 databases must be migrated
- Zero downtime migration
- Wall-clock time critical (maintenance window: 2 hours)
- Token cost not critical

**Sequential approach:**
- 1 Engineer migrates all 10 databases sequentially
- 1 hour per database × 10 = 10 hours
- Exceeds maintenance window (FAIL)

**Parallel approach:**
- 1 Senior Engineer creates 10 sub-tasks
- 10 Engineers migrate in parallel
- 1 hour wall-clock
- Fits in maintenance window (SUCCESS)
- **Benefit: 9 hours saved, meets deadline**

### Implementation

#### Step 1: Orchestrator Creates Parent Task

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-16-db-migration-postgres-001
role: senior_engineer
model: claude-sonnet-4-6
effort: high
scope: >
  Coordinate migration of all 10 production databases from PostgreSQL 12 to PostgreSQL 15.
  Ensure zero-downtime migration, data integrity, and rollback capability.
  All migrations must complete within 2-hour maintenance window.
context:
  - Maintenance window: 2026-05-16 22:00-00:00 UTC
  - Databases: 10 production databases
  - Source: PostgreSQL 12
  - Target: PostgreSQL 15
  - Schema changes: docs/postgres-15-migration-guide.md
plan:
  1. Create sub-task for each of 10 databases
  2. Wait for all migrations to complete (60-minute timeout)
  3. Verify all databases migrated successfully
  4. Run smoke tests on all databases
  5. Document migration results
success_criteria:
  - All 10 databases migrated to PostgreSQL 15
  - Zero downtime (no service interruption)
  - Data integrity verified
  - Smoke tests passing on all databases
  - Rollback plan documented
---
```

#### Step 2: Senior Engineer Creates 10 Child Tasks

```python
from skills.queue_management.scripts.queue_ops import QueueOperations

ops = QueueOperations(queue_dir="/path/to/queue", session_id="db-migration-001")

databases = [
    {"name": "users_db", "size": "50GB", "tables": 45},
    {"name": "orders_db", "size": "120GB", "tables": 62},
    {"name": "products_db", "size": "30GB", "tables": 28},
    {"name": "payments_db", "size": "80GB", "tables": 35},
    {"name": "analytics_db", "size": "200GB", "tables": 89},
    {"name": "notifications_db", "size": "20GB", "tables": 12},
    {"name": "inventory_db", "size": "60GB", "tables": 41},
    {"name": "shipping_db", "size": "40GB", "tables": 33},
    {"name": "reviews_db", "size": "25GB", "tables": 18},
    {"name": "recommendations_db", "size": "150GB", "tables": 71},
]

for db in databases:
    ops.create_delegate(
        task_id=f"2026-05-16-db-migration-{db['name']}-001",
        role="engineer",
        model="claude-haiku-4-5",
        effort="high",
        scope=f"Migrate {db['name']} from PostgreSQL 12 to PostgreSQL 15. "
              f"Database size: {db['size']}, tables: {db['tables']}. "
              f"Ensure zero-downtime migration and data integrity.",
        context=[
            f"Parent task: 2026-05-16-db-migration-postgres-001",
            f"Database: {db['name']}",
            f"Size: {db['size']}",
            f"Tables: {db['tables']}",
            f"Maintenance window: 2026-05-16 22:00-00:00 UTC",
            f"Related: docs/postgres-15-migration-guide.md"
        ],
        plan=[
            f"Create backup of {db['name']}",
            "Set up PostgreSQL 15 replica",
            "Run schema migration scripts",
            "Verify data integrity",
            "Switch traffic to PostgreSQL 15",
            "Monitor for errors (15 minutes)",
            "Document migration results"
        ],
        success_criteria=[
            f"{db['name']} migrated to PostgreSQL 15",
            "Zero downtime (no service interruption)",
            "Data integrity verified (row counts match)",
            "Smoke tests passing",
            "Rollback tested and documented"
        ],
        parent_task_id="2026-05-16-db-migration-postgres-001",
    )
```

#### Step 3: Orchestrator Routes 10 Children to 10 Engineers

All 10 migrations run in parallel, each taking ~1 hour.

#### Step 4: Each Engineer Returns HANDBACK

**Example HANDBACK (users_db):**
```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-16-db-migration-users-db-001
status: complete
deliverables:
  - Backup: users_db_pg12_backup.sql.gz (50GB)
  - Migration log: users_db_migration.log
  - Verification report: users_db_verification.txt
tests:
  - Backup verification: PASS
  - Schema migration: PASS (45 tables)
  - Data integrity: PASS (row counts match)
  - Smoke tests: PASS (all queries < 100ms)
  - Rollback test: PASS (verified rollback capability)
tokens_in: 1200
tokens_out: 800
model: claude-haiku-4-5
effort: high
duration_minutes: 58
escalations: 0
notes: "users_db migrated successfully. No data loss. All indexes rebuilt. Performance improved (queries 15% faster on average)."
---
```

#### Step 5: Orchestrator Aggregates Results

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-16-db-migration-postgres-001
status: complete
deliverables:
  - Migration summary: all-databases-migration-summary.md
  - Results: 10/10 databases migrated successfully
  - Verification: all smoke tests passing
children_created:
  - 2026-05-16-db-migration-users-db-001
  - 2026-05-16-db-migration-orders-db-001
  - 2026-05-16-db-migration-products-db-001
  - 2026-05-16-db-migration-payments-db-001
  - 2026-05-16-db-migration-analytics-db-001
  - 2026-05-16-db-migration-notifications-db-001
  - 2026-05-16-db-migration-inventory-db-001
  - 2026-05-16-db-migration-shipping-db-001
  - 2026-05-16-db-migration-reviews-db-001
  - 2026-05-16-db-migration-recommendations-db-001
children_results:
  2026-05-16-db-migration-users-db-001:
    status: complete
    quality: 95
  2026-05-16-db-migration-orders-db-001:
    status: complete
    quality: 92
  2026-05-16-db-migration-products-db-001:
    status: complete
    quality: 94
  2026-05-16-db-migration-payments-db-001:
    status: complete
    quality: 93
  2026-05-16-db-migration-analytics-db-001:
    status: complete
    quality: 90
  2026-05-16-db-migration-notifications-db-001:
    status: complete
    quality: 96
  2026-05-16-db-migration-inventory-db-001:
    status: complete
    quality: 91
  2026-05-16-db-migration-shipping-db-001:
    status: complete
    quality: 92
  2026-05-16-db-migration-reviews-db-001:
    status: complete
    quality: 94
  2026-05-16-db-migration-recommendations-db-001:
    status: complete
    quality: 88
children_failed: []
result_aggregation_status: all_complete
tokens_in: 12000
tokens_out: 8000
model: claude-sonnet-4-6
effort: high
duration_minutes: 65
escalations: 0
notes: >
  All 10 databases migrated successfully within maintenance window (65 minutes total).
  Zero downtime achieved. All smoke tests passing. Data integrity verified.
  Performance improved on average (queries 12% faster). Ready for production.
---
```

---

## Example 3: Code Review (5 Repositories)

### Scenario

Review code changes in 5 repositories before merging to main branch.

**Requirements:**
- All 5 repos must be reviewed
- Results aggregated into consolidated review
- Wall-clock time critical (release deadline: 4 hours)
- Quality critical (no regressions)

**Sequential approach:**
- 1 Lead Engineer reviews all 5 repos sequentially
- 2 hours per repo × 5 = 10 hours
- Exceeds deadline (FAIL)

**Parallel approach:**
- 1 Principal Engineer creates 5 sub-tasks
- 5 Lead Engineers review in parallel
- 2 hours wall-clock
- Meets deadline (SUCCESS)
- **Benefit: 8 hours saved, meets deadline**

### Implementation

#### Step 1: Orchestrator Creates Parent Task

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-16-code-review-release-001
role: principal_engineer
model: claude-opus-4-6
effort: high
scope: >
  Coordinate code review of all 5 repositories for release 2.0.
  Ensure code quality, test coverage, no regressions, and architectural alignment.
  Produce consolidated review with merge/no-merge recommendation.
context:
  - Release: 2.0
  - Repositories: auth, billing, notifications, api, worker
  - Deadline: 4 hours
  - Focus: Quality, test coverage, regressions, architecture
plan:
  1. Create sub-task for each of 5 repositories
  2. Wait for all reviews to complete (120-minute timeout)
  3. Aggregate findings and recommendations
  4. Produce consolidated review
  5. Make final merge/no-merge recommendation
success_criteria:
  - All 5 repos reviewed
  - Consolidated review completed
  - Merge recommendation provided
  - No critical issues left undocumented
---
```

#### Step 2: Principal Engineer Creates 5 Child Tasks

```python
from skills.queue_management.scripts.queue_ops import QueueOperations

ops = QueueOperations(queue_dir="/path/to/queue", session_id="code-review-001")

repos = [
    {"name": "auth", "changes": "OAuth2 flow refactor", "files": 12, "tests": 45},
    {"name": "billing", "changes": "Payment processing improvements", "files": 18, "tests": 62},
    {"name": "notifications", "changes": "Email template updates", "files": 8, "tests": 28},
    {"name": "api", "changes": "API versioning implementation", "files": 25, "tests": 89},
    {"name": "worker", "changes": "Job queue optimization", "files": 15, "tests": 41},
]

for repo in repos:
    ops.create_delegate(
        task_id=f"2026-05-16-code-review-{repo['name']}-001",
        role="lead_engineer",
        model="claude-sonnet-4-6",
        effort="high",
        scope=f"Review code changes in {repo['name']} repository for release 2.0. "
              f"Changes: {repo['changes']}. {repo['files']} files changed, {repo['tests']} tests. "
              f"Ensure code quality, test coverage, no regressions, architectural alignment.",
        context=[
            f"Parent task: 2026-05-16-code-review-release-001",
            f"Repository: {repo['name']}",
            f"Changes: {repo['changes']}",
            f"Files: {repo['files']}",
            f"Tests: {repo['tests']}",
            f"Related: PR #{repo['name']}-release-2.0"
        ],
        plan=[
            f"Review all {repo['files']} changed files in {repo['name']}",
            "Check test coverage (must be ≥85%)",
            "Verify no regressions in existing functionality",
            "Check architectural alignment with design docs",
            "Review error handling and edge cases",
            "Check performance implications",
            "Document findings and recommendations"
        ],
        success_criteria=[
            f"{repo['name']} code review completed",
            "Test coverage ≥85%",
            "No regressions identified",
            "Architectural alignment verified",
            "Merge/no-merge recommendation provided"
        ],
        parent_task_id="2026-05-16-code-review-release-001",
    )
```

#### Step 3: Orchestrator Routes 5 Children to 5 Lead Engineers

All 5 reviews run in parallel, each taking ~2 hours.

#### Step 4: Each Lead Engineer Returns HANDBACK

**Example HANDBACK (auth repo):**
```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-16-code-review-auth-001
status: complete
deliverables:
  - Review: auth-code-review.md
  - Findings: 2 issues (1 critical, 1 minor)
  - Recommendation: CONDITIONAL MERGE (fix critical issue first)
tests:
  - Code review: COMPLETE (12 files)
  - Test coverage: 87% (meets requirement)
  - Regression test: PASS (all existing tests pass)
  - Architecture check: PASS (aligns with design)
tokens_in: 2800
tokens_out: 2100
model: claude-sonnet-4-6
effort: high
duration_minutes: 118
escalations: 0
notes: >
  Auth OAuth2 refactor is well-implemented. Test coverage excellent (87%).
  One critical issue: token refresh logic has race condition in concurrent scenarios.
  One minor issue: error message could be more descriptive.
  Recommend: fix race condition, then merge.
---
```

#### Step 5: Orchestrator Aggregates Results

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-16-code-review-release-001
status: complete
deliverables:
  - Consolidated review: release-2.0-consolidated-review.md
  - Summary: 5 repos reviewed, 3 critical issues, 7 minor issues
  - Recommendation: CONDITIONAL MERGE (fix 3 critical issues first)
children_created:
  - 2026-05-16-code-review-auth-001
  - 2026-05-16-code-review-billing-001
  - 2026-05-16-code-review-notifications-001
  - 2026-05-16-code-review-api-001
  - 2026-05-16-code-review-worker-001
children_results:
  2026-05-16-code-review-auth-001:
    status: complete
    quality: 92
  2026-05-16-code-review-billing-001:
    status: complete
    quality: 88
  2026-05-16-code-review-notifications-001:
    status: complete
    quality: 95
  2026-05-16-code-review-api-001:
    status: complete
    quality: 85
  2026-05-16-code-review-worker-001:
    status: complete
    quality: 90
children_failed: []
result_aggregation_status: all_complete
tokens_in: 14000
tokens_out: 10500
model: claude-opus-4-6
effort: high
duration_minutes: 125
escalations: 0
notes: >
  All 5 repos reviewed. Overall quality good (average 90%).
  3 critical issues identified: (1) auth token race condition, (2) billing payment race condition,
  (3) api versioning backward compatibility issue.
  7 minor issues (mostly documentation and error messages).
  Recommendation: fix 3 critical issues, then merge. Estimated fix time: 2 hours.
---
```

---

## Example 4: Feature Implementation (3 Services)

### Scenario

Implement new feature (user preferences) across 3 backend services (auth, users, api).

**Requirements:**
- All 3 services must implement feature
- Services must be compatible
- Wall-clock time critical (sprint deadline: 8 hours)
- Quality critical (no bugs)

**Sequential approach:**
- 1 Engineer implements feature in all 3 services sequentially
- 3 hours per service × 3 = 9 hours
- Exceeds deadline (FAIL)

**Parallel approach:**
- 1 Senior Engineer creates 3 sub-tasks
- 3 Engineers implement in parallel
- 3 hours wall-clock
- Meets deadline (SUCCESS)
- **Benefit: 6 hours saved, meets deadline**

### Implementation

#### Step 1: Orchestrator Creates Parent Task

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-16-feature-user-preferences-001
role: senior_engineer
model: claude-sonnet-4-6
effort: high
scope: >
  Implement user preferences feature across 3 backend services (auth, users, api).
  Services must be compatible and integrated. Feature includes: theme selection,
  notification settings, language preference, timezone setting.
context:
  - Feature: User Preferences
  - Services: auth, users, api
  - Deadline: 8 hours
  - Design: docs/user-preferences-design.md
plan:
  1. Create sub-task for each of 3 services
  2. Wait for all implementations to complete (180-minute timeout)
  3. Integration testing across services
  4. Verify feature works end-to-end
  5. Document implementation
success_criteria:
  - All 3 services implement feature
  - Services are compatible
  - Integration tests passing
  - Feature works end-to-end
  - Documentation complete
---
```

#### Step 2: Senior Engineer Creates 3 Child Tasks

```python
from skills.queue_management.scripts.queue_ops import QueueOperations

ops = QueueOperations(queue_dir="/path/to/queue", session_id="feature-impl-001")

services = [
    {
        "name": "auth",
        "scope": "Implement user preferences in authentication service",
        "tasks": ["Add preferences table", "Add preferences API", "Add preferences validation"]
    },
    {
        "name": "users",
        "scope": "Implement user preferences in user service",
        "tasks": ["Add preferences storage", "Add preferences retrieval", "Add preferences update"]
    },
    {
        "name": "api",
        "scope": "Implement user preferences in API gateway",
        "tasks": ["Add preferences endpoints", "Add preferences caching", "Add preferences validation"]
    }
]

for service in services:
    ops.create_delegate(
        task_id=f"2026-05-16-feature-user-preferences-{service['name']}-001",
        role="engineer",
        model="claude-haiku-4-5",
        effort="high",
        scope=service['scope'],
        context=[
            f"Parent task: 2026-05-16-feature-user-preferences-001",
            f"Service: {service['name']}",
            f"Feature: User Preferences",
            f"Related: docs/user-preferences-design.md"
        ],
        plan=service['tasks'],
        success_criteria=[
            f"User preferences implemented in {service['name']}",
            "All tests passing",
            "Code review approved",
            "Documentation complete"
        ],
        parent_task_id="2026-05-16-feature-user-preferences-001",
    )
```

---

## Example 5: Handling Partial Failures

### Scenario

Analyze 5 microservices for performance bottlenecks. 1 service analysis fails; 4 succeed.

### Implementation

#### Parent Task Creates 5 Children

```python
for service in ["auth", "billing", "notifications", "api", "worker"]:
    ops.create_delegate(
        task_id=f"2026-05-16-perf-analysis-{service}-001",
        role="engineer",
        parent_task_id="2026-05-16-perf-analysis-001",
    )
```

#### 4 Children Succeed, 1 Fails

**Successful HANDBACK (auth):**
```yaml
status: complete
quality: 92
```

**Failed HANDBACK (billing):**
```yaml
status: failed
quality: 0
notes: "Unable to access billing service database. Rate limiting prevented analysis."
```

**Successful HANDBACK (notifications):**
```yaml
status: complete
quality: 88
```

**Successful HANDBACK (api):**
```yaml
status: complete
quality: 90
```

**Successful HANDBACK (worker):**
```yaml
status: complete
quality: 85
```

#### Orchestrator Aggregates with Partial Failure

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-16-perf-analysis-001
status: complete
children_results:
  2026-05-16-perf-analysis-auth-001:
    status: complete
    quality: 92
  2026-05-16-perf-analysis-billing-001:
    status: failed
    quality: 0
  2026-05-16-perf-analysis-notifications-001:
    status: complete
    quality: 88
  2026-05-16-perf-analysis-api-001:
    status: complete
    quality: 90
  2026-05-16-perf-analysis-worker-001:
    status: complete
    quality: 85
children_failed: [2026-05-16-perf-analysis-billing-001]
result_aggregation_status: partial
notes: "4 of 5 services analyzed successfully. Billing analysis failed (database access issue). Recommend retry after rate limiting window."
---
```

**Quality calculation (only successful children):**
```
Children: [92, 88, 90, 85] (billing excluded)
Numerator: (92×3) + (88×3) + (90×3) + (85×3) = 276 + 264 + 270 + 255 = 1065
Denominator: 3 + 3 + 3 + 3 = 12
Result: 1065 / 12 = 88.75
```

---

## Summary

These examples demonstrate parallel delegation in action:

✅ **Security Audit** — 4 services, 75% time savings
✅ **Database Migration** — 10 databases, 90% time savings
✅ **Code Review** — 5 repos, 80% time savings
✅ **Feature Implementation** — 3 services, 67% time savings
✅ **Partial Failures** — 5 services, 1 fails, 4 succeed

Use parallel delegation for naturally decomposable work where wall-clock time matters more than token cost.

---

**See also:**
- [PARALLEL-DELEGATION-GUIDE.md](PARALLEL-DELEGATION-GUIDE.md)
- [AGENTS.md — Parallel Delegation](AGENTS.md#parallel-delegation-phase-2-feature)
- [HANDOFF.md — Parallel Protocol](HANDOFF.md#parallel-delegation-protocol-phase-2)
