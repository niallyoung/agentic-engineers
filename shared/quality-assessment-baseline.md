# Quality Assessment Baseline

**Purpose:** Unified quality evaluation criteria used by Lead Engineer (blocking authority) and Quality Engineer (post-approval assessment)

**Audience:** Lead Engineer, Quality Engineer, Quality Checks Orchestrator

**Last Updated:** 2026-05-09

**Owned By:**
- Lead Engineer — blocking criteria (Section 4)
- Quality Engineer — assessment dimensions (Section 2) and scoring (Section 3)

---

## Overview

This baseline eliminates ambiguity between roles by providing a single source of truth for how code quality is measured and acted upon.

- **Lead Engineer** uses this to decide: _APPROVE or REWORK?_
- **Quality Engineer** uses this to measure: _How good is this code, and is quality trending up?_
- **Both roles** use the same scoring table (Section 3), so a score of 75 means the same thing to both.

---

## Section 1: Assessment Dimensions

Eight dimensions are evaluated on every submission. Each dimension contributes to the overall quality score.

---

### Dimension 1 — Test Coverage

**Description:** Percentage of lines, branches, and functions exercised by automated tests.

**Why It Matters:** Low coverage leaves regressions undetected. Coverage is the first-order signal that untested failure modes exist in the code.

**Target:** ≥ 80% across all metrics (lines, branches, functions)

**Key Indicators:**
- pytest coverage report (`--cov` output)
- jest / vitest `--coverage` output
- GitHub Actions CI coverage summary

**Good Signals:**
- Lines, branches, and functions all ≥ 80%
- Edge cases (empty input, error paths, boundary values) explicitly covered
- New code matches or exceeds existing module coverage

**Bad Signals:**
- Any single metric < 70%
- New code added with no accompanying tests
- Coverage drops compared to the base branch

---

### Dimension 2 — Test Quality (Not Just Quantity)

**Description:** Tests must be specific, isolated, and trustworthy — not merely present to inflate numbers.

**Why It Matters:** Flaky or poorly written tests create false confidence. A test suite full of trivial assertions can report 90% coverage while missing the real failure modes.

**Target:** Tests describe exact scenarios, use fixtures properly, and fail for the right reason.

**Key Indicators:**
- Test names are readable descriptions of behavior (`test_login_rejects_expired_token`)
- No `time.sleep()` or arbitrary waits
- No shared mutable state between tests
- Mocking is explicit and purposeful

**Good Signals:**
- Test name = exact scenario being tested, readable by non-author
- Table-driven tests for multiple input variations
- Each test has a single clear assertion
- Fixtures used to share setup, not global variables

**Bad Signals:**
- Generic test names (`test_1`, `test_function_works`)
- `time.sleep()` or polling loops inside tests
- Tests that pass in isolation but fail in sequence (shared state)
- Mocking everything — tests no real behavior

---

### Dimension 3 — Code Readability & Maintainability

**Description:** Code is understandable by someone unfamiliar with the change, without requiring the author to explain it.

**Why It Matters:** Future maintainers (including the original author six months later) introduce bugs when code is hard to follow. High complexity is a defect magnet.

**Target:** Functions < 30 lines, cyclomatic complexity < 10, names convey intent.

**Key Indicators:**
- Function length (count lines)
- Cyclomatic complexity (linter or manual review)
- Variable and function names
- Nesting depth (avoid > 3 levels)

**Good Signals:**
- Self-documenting code — minimal inline comments needed to understand logic
- Variable names describe what they hold, not how they are used (`user_email`, not `val`)
- Functions do one thing and their name says what
- Conditionals read like English (`if user.is_authenticated()`)

**Bad Signals:**
- Cryptic abbreviations (`tpe`, `mgr2`, `x`)
- Functions > 40 lines doing multiple distinct things
- Deeply nested `if/else` trees (≥ 4 levels deep)
- Comments explain *what* the code does instead of *why* a decision was made

---

### Dimension 4 — Error Handling & Resilience

**Description:** All failure modes are handled explicitly. No silent errors.

**Why It Matters:** Unhandled exceptions or swallowed errors cause unpredictable production failures that are hard to diagnose. Explicit error handling is a reliability contract.

**Target:** Specific exception types caught, errors logged with context, graceful fallback or clear propagation.

**Key Indicators:**
- Exception specificity (`ValueError`, not bare `except`)
- Logging present at error site with enough context to debug
- No `pass` in except blocks
- Go: all returned errors checked
- Structured operational logs at key state transitions (connection established, request received, processing complete) — not just error paths
- Successful operations logged at INFO level for observability

**Good Signals:**
- Specific exception types: `except ValueError as e:` with log + re-raise or return
- Error messages include context: `"Failed to load user {user_id}: {e}"`
- Functions return typed errors or raise well-named exceptions
- Fallback behavior documented (retry, default value, circuit break)

**Bad Signals:**
- Bare `except:` or `except Exception:` with no logging
- Errors silently discarded with `pass`
- Go: `_ = someFunc()` ignoring a returned error
- Missing error handling for I/O, network, and database calls
- No log output on success paths — production behavior is invisible post-deployment
- Errors logged but without enough context to reproduce (missing request ID, user context, state at failure)

---

### Dimension 5 — Documentation & API Clarity

**Description:** Public interfaces and non-obvious logic are documented. Assumptions about inputs and outputs are explicit.

**Why It Matters:** Undocumented APIs force callers to read source code. Undocumented assumptions become silent bugs when callers make different assumptions.

**Target:** All public functions have docstrings, complex logic has inline comments explaining *why*, edge cases and preconditions documented.

**Key Indicators:**
- Docstrings on public functions and classes
- Raises/throws documented (`Raises: ValueError if price < 0`)
- Non-obvious algorithms have a comment explaining the approach
- README or API docs updated if public interface changes

**Good Signals:**
- `"""Fetch the user record. Raises ValueError if user_id is None."""`
- Complex business logic has a comment linking to the relevant ticket or spec
- Parameter types and return types annotated
- API contract (inputs, outputs, errors) documented before implementation

**Bad Signals:**
- Public functions with no docstring
- Silent assumptions about inputs (no validation, no documentation)
- Comments that restate the code: `# increment counter` above `counter += 1`
- Changed API with no documentation update

---

### Dimension 6 — Security & Privacy

**Description:** No credential leaks, appropriate data handling, authenticated endpoints, no injection vectors.

**Why It Matters:** Security vulnerabilities do not degrade gracefully. A single exposed credential or unprotected endpoint can cause a breach affecting all users.

**Target:** Zero known vulnerabilities. Secrets in environment variables. Private data classified. Auth enforced.

**Key Indicators:**
- No hardcoded secrets, tokens, or API keys in source code or commit messages
- Input validated and sanitised before use in queries or shell commands
- Auth checks present on all non-public endpoints
- Data classification present (PII marked, not logged)

**Good Signals:**
- Secrets loaded from environment: `os.environ["API_KEY"]` or AWS Secrets Manager
- Private data redacted from logs: `log.info("User login", user_id=uid)` not email
- IAM roles used for service-to-service calls, not static credentials
- SQL parameters use placeholders, not string interpolation

**Bad Signals:**
- API key or password hardcoded in source: `api_key = "sk-abc123"`
- User-supplied input used directly in SQL/shell without sanitisation
- Endpoint accessible without auth check
- PII (email, SSN, payment data) written to logs or metrics

---

### Dimension 7 — Performance (No Obvious Regressions)

**Description:** No N+1 query patterns, no unindexed scans on large tables, no unnecessary recomputation inside loops.

**Why It Matters:** Performance regressions are often invisible until production load exposes them. O(n²) code that works fine at 100 records silently degrades at 10,000.

**Target:** No new N+1 query patterns, algorithmic complexity justified for data size, caching used where appropriate.

**Key Indicators:**
- Query count per request (ORM query logging in dev)
- Algorithm choice noted for any loop > O(n)
- Load test result or estimate for expected data volume
- Cache invalidation strategy documented

**Good Signals:**
- Batch queries used instead of per-item fetches
- Database indexes exist on columns used in `WHERE` and `JOIN` clauses
- Repeated expensive computation extracted and cached
- Complexity noted in comment where non-trivial: `# O(n log n) sort, acceptable for ≤10k items`

**Bad Signals:**
- Query inside a loop (N+1 pattern)
- `SELECT *` on unbounded tables
- Sorting or filtering large datasets in application memory instead of database
- No consideration of scale for new feature with expected growth

---

### Dimension 8: Architectural & Design Consistency

**Description:** Code follows established platform patterns and architectural decisions. No new abstractions or coupling introduced without design review.

**Target:** All service boundaries, data ownership models, and event contracts respected. New patterns approved by Lead/Principal before implementation.

**Why it matters:**
- Inconsistent patterns create technical debt and distributed correctness issues
- One "shortcut" triggers copy-paste across the codebase
- Platform stability depends on consistent abstractions
- Cross-service dependencies must be intentional

**Key indicators:**
- CQRS separation respected (command handlers don't read from query projections)
- Events use canonical schema; no ad-hoc message types
- Service calls go through defined interfaces (event bus, API gateway, RPC layer)
- New abstractions documented and approved before use
- No bypass patterns introduced

**Good Signals:**
- Event follows published schema with versioning
- Service X calls Service Y via RPC layer, not direct DB access
- New pattern discussed in design review before implementation
- Architectural decision documented in ADR or design doc
- Consistent with similar components elsewhere

**Bad Signals:**
- Direct cross-service database access
- New stateful singletons bypassing pub-sub
- Event bus bypassed for "efficiency"
- Undiscussed new abstractions added to shared modules (creates surprise coupling)
- Pattern violates established CQRS or service boundary model
- Change introduces tight temporal coupling where loose coupling exists elsewhere

---

## Section 2: Scoring System

Both Lead Engineer and Quality Engineer use the same scoring table. Scores are not computed mechanically — they are a judgment integrating all eight dimensions with weight given to severity.

| Score | Label | Merge Decision | What It Means |
|-------|-------|----------------|---------------|
| **90–100** | Excellent | **APPROVE** | All dimensions ≥ 85%. No security or performance concerns. Ready to ship. |
| **80–89** | Good | **APPROVE WITH MINOR NOTES** | Most dimensions ≥ 80%. Minor improvements suggested but not blocking. Safe to merge; note improvements for future work. |
| **70–79** | Fair | **REWORK** | One or more dimensions below threshold. Specific changes required before merge. Should not merge without addressing.

**Conditional Approval (Lead discretion):**
  Lead Engineer may approve a 70–79 score if ALL of the following hold:
  - **Single dimension below threshold**: Only one assessment dimension is marginal (<80%); others are ≥80%
  - **Documented upward trajectory**: That dimension has measurably improved over recent PRs (trend is positive)
  - **Low change risk**: Change scope is low-risk (internal refactor, optimization, non-breaking enhancement; NOT new public API, schema change, or cross-service boundary change)
  
  Example: PR has 75% test coverage (below 80%) but coverage has risen from 60% → 68% → 75% over recent commits, and change is an internal optimization with no API changes. Lead may approve with note: "Approve conditional on continued coverage trend; next PR in this area should target ≥80%." |
| **< 70** | Poor | **REWORK + ESCALATE** | Multiple dimensions significantly weak. Architecture concerns or systemic issues. Escalate to Senior Engineer for design review. Significant rework required. |

### Scoring Notes

- A single **critical failure** (security vulnerability, data loss risk) overrides the numeric score and forces **REWORK + ESCALATE** regardless of other dimensions.
- Test coverage below 80% blocks merge (the target must be met). Coverage below 70% triggers REWORK + ESCALATE as a systemic coverage concern.
- Scores are signals, not verdicts on the engineer. A 72 means "this PR needs more work", not "this engineer is poor."
- Score trends matter: a team improving from 72 → 78 → 83 over three PRs is healthier than one stuck at 81.

---

### Weighting Guidance (Informational)

While dimensions are evaluated individually, Lead Engineer may use the following tier system for consistency when comparing across PRs or sprints:

| Tier | Dimensions | Example Weighting | When to Use |
|------|------------|-------------------|------------|
| **A (Critical)** | Security, Error Handling, Test Coverage | 30% | Comparative scoring across multiple PRs in same module |
| **B (High)** | Architectural Consistency, Performance | 20% | Risk assessment for deployment to production |
| **C (Standard)** | Test Quality, Readability, Documentation | 15% | Post-approval QE trend analysis |

**Note:** This is guidance for consistency only, not a binding formula. Lead Engineer may weight dimensions differently based on change scope (e.g., documentation more important for public API changes, performance more important for data path changes). QE may choose to report weighted vs. unweighted scores depending on context.

Example: A PR with 90+ on all C-tier dimensions, 75 on B-tier (one architectural pattern marginal), and 85 on A-tier would be scored as overall 82 (favorable on critical tier) for purposes of consistency check.

---

## Section 3: Blocking Criteria (Lead Engineer Authority)

These conditions trigger a **REWORK** decision. Lead Engineer has sole authority to block merges. A PR meeting any of these criteria must not merge until the condition is resolved.

| Condition | Threshold | Rationale |
|-----------|-----------|-----------|
| **Test coverage** | <80% blocks merge; <70% triggers REWORK + ESCALATE | Test coverage below 80% blocks merge (target not met). Coverage 70–79% is REWORK, may be conditionally approved by Lead judgment (see Section 2 Conditional Approval). Coverage <70% is REWORK + ESCALATE (systemic issue). |
| **Security vulnerability present** | Any known issue | Does not degrade gracefully; block immediately |
| **No error handling for failure modes** | I/O, network, or DB calls without error handling | Silent failures cause unpredictable production behavior |
| **Performance regression** | Measurable degradation vs baseline, or new N+1 pattern | May not manifest until production load |
| **Breaking change without migration path** | API or schema change without versioning or migration | Breaks callers silently |
| **Secrets committed** | Any credential, token, or API key in source | Committed secrets constitute an already-occurred breach event. REWORK + ESCALATE + immediate credential rotation required. Do not merge until credentials are rotated and scanned from git history. |
| **Architectural pattern violation** | Violation without Lead or Principal Engineer sign-off | Direct violation of CQRS separation, event schema contracts, or service boundary isolation. Introduces systemic coupling or distributed correctness issues. |

### Lead Engineer Does Not Block For

- Style preferences where linting is silent
- Minor documentation gaps on internal (non-public) functions
- Suggestions that are improvements but not correctness issues
- Test coverage 70–79% when Conditional Approval criteria are met (see Section 2 Conditional Approval)

---

## Section 4: Post-Approval Assessment (Quality Engineer)

After Lead Engineer approves a PR, Quality Engineer performs a structured assessment. This is not a blocking gate — it feeds metrics, trend analysis, and model optimization recommendations.

### What Quality Engineer Measures

1. **Dimensional score** — Score each of the 8 dimensions and produce an overall quality score.
2. **Trend analysis** — Is quality improving, stable, or degrading across recent PRs from this engineer or this module?
3. **Pattern adherence** — Are platform conventions (CQRS, event schema, error handling patterns) being followed?
4. **Model performance signal** — Did the assigned model handle the complexity appropriately? Feed this to Model Engineer.
5. **Improvement adoption** — Are notes from previous REWORK cycles being applied?

### Quality Engineer Does Not

- Block merges (Lead Engineer has that authority)
- Re-review items Lead Engineer already addressed
- Request changes in post-approval assessment — notes go to metrics and trend tracking only
- Penalise engineers — use assessment to help, not score

### Security Critical Findings Exception

QE has escalation authority (not remediation authority) for critical security findings discovered during post-approval assessment:

**Security Critical includes:**
- Secrets committed or hardcoded credentials
- SQL injection or code injection vectors
- Cross-site scripting (XSS) vectors in user input handling
- Missing authentication or authorization checks on sensitive operations
- PII (personally identifiable information) logged or exposed in error messages

**QE Action:** Escalate immediately to Lead Engineer and Security Engineer. Do not merge or deploy until credential rotation (if secrets) and security fix are confirmed.

This exception exists because security findings have time-critical impact (credential compromise, data breach risk) that overrides standard post-approval workflow.

### Disagreement Resolution: QE vs Lead Engineer

If QE's post-approval assessment conflicts with Lead Engineer's APPROVE decision:

**Default (90% of cases):** QE documents the disagreement in the assessment record and feeds trend data to Model Engineer. Lead's merge decision stands; QE tracks whether quality improves in the next PR from same author/module.

**Escalation (10% of cases — systemic disagreements):** If QE assesses that the disagreement reflects a systemic quality issue (not a one-off judgment call), escalate to Principal Engineer with:
- Lead's approval rationale
- QE's assessment and scoring
- Pattern across recent PRs (e.g., "three PRs from this team in 70-79 band; trend is not improving")

Principal Engineer mediates and may recommend process adjustments for future.

Example of escalation trigger: "Lead conditionally approved 72% coverage due to upward trend (60% → 68% → 72%), but the trend stopped here and latest PR still at 72%. This suggests the upward trajectory justification no longer holds. Escalate to clarify expectation for next PR."

Example of non-escalation: "Lead approved 79% with the note 'approve conditional on next PR targeting 80%.' QE documents this and monitors next PR. No escalation unless next PR regresses."

### Assessment Output Format

```yaml
pr_number: 147
assessment_date: 2026-05-10
overall_score: 85
status: approved_tracking
dimensions:
  test_coverage:              { score: 82, notes: "Lines 82%, branches 81%, functions 85%" }
  test_quality:               { score: 90, notes: "Table-driven, descriptive names, no waits" }
  readability:                { score: 88, notes: "Clear naming, functions < 25 lines" }
  error_handling:             { score: 85, notes: "Specific exceptions, all I/O paths handled, structured logs on state transitions" }
  documentation:              { score: 92, notes: "Docstrings on all public functions" }
  security:                   { score: 95, notes: "No hardcoded secrets, auth present" }
  performance:                { score: 88, notes: "No N+1, indexes present on query columns" }
  architectural_consistency:  { score: 90, notes: "CQRS respected, event schema versioned, no bypass patterns" }
trend_tracking:
  prior_scores: [76, 80, 85]           # Previous assessments in this PR series
  module_baseline_avg: 82              # Historical average for this code module
  trajectory: upward                   # or: stable, downward, unknown
model_engineer_input: ready            # Feed to cost-quality analysis
notes: "Trend is positive. Recommend continued focus on coverage in next cycle."
```

---

## Section 5: Worked Examples

### Example 1: REWORK — Lead Engineer Blocking Review

```
PR #147: User authentication service (initial submission)

Dimensions Assessed:
  Test coverage:    72%  ⚠️  (below 80% target, above 70% floor)
  Test quality:     75   ⚠️  (generic test names, two hardcoded sleeps found)
  Readability:      85   ✅
  Error handling:   88   ✅  (specific exceptions, logged with context)
  Documentation:    60   ⚠️  (no docstrings on /login or /logout endpoints)
  Security:         90   ✅
  Performance:      85   ✅

Overall Score: 79  →  REWORK

Lead Engineer Decision:
  Status: CHANGES REQUESTED
  Blocking issues:
    1. Coverage at 72% — must reach ≥80% before merge
    2. Document /login and /logout public API (parameters, errors, auth requirements)
    3. Remove hardcoded sleeps in test_login_timeout and test_session_expiry

  Non-blocking suggestions:
    - Rename test cases to describe behavior (e.g., test_login_rejects_expired_token)
    - Consider extracting token validation logic to auth_utils.py

  Not merging until blocking issues resolved.
```

---

### Example 2: APPROVE — Lead Engineer After Rework

```
PR #147 (revision 2): User authentication service

Dimensions Assessed:
  Test coverage:    83%  ✅
  Test quality:     84   ✅  (descriptive names, no waits, fixtures used properly)
  Readability:      85   ✅
  Error handling:   88   ✅
  Documentation:    82   ✅  (docstrings added to all public endpoints)
  Security:         90   ✅
  Performance:      85   ✅

Overall Score: 85  →  APPROVE WITH MINOR NOTES

Lead Engineer Decision:
  Status: APPROVED
  Notes (non-blocking, for future work):
    - Token validation logic is a good candidate to extract to a helper in a follow-up
    - Consider adding a load test for /refresh at scale

  Merged.
```

---

### Example 3: Post-Approval Assessment — Quality Engineer

```
PR #147: Data aggregation service (post-approval QE assessment)
Date: May 10, 2026
Assessed by: Quality Engineer

Assessment:
- Coverage: 82% ✅ (target 80%)
- Test quality: Excellent fixtures, table-driven ✅
- Readability: Clear variable names, functions <30 lines ✅
- Error handling: Handles timeouts and parsing errors, structured logging on state transitions ✅
- Documentation: Public API fully documented ✅
- Security: No hardcoded credentials ✅
- Performance: No N+1 queries ✅
- Architectural Consistency: CQRS separation respected, event schema versioned ✅

Overall Score: 85
Decision: APPROVED, high quality
Trend: Upward (76 → 80 → 85 over last 3 PRs)
Module Baseline: 82 (this PR slightly above)

QE Note: "Coverage and architectural consistency continue to improve. Recommend maintaining this trajectory in next cycle."
```

```yaml
pr_number: 147
assessment_date: 2026-05-10
overall_score: 85
status: approved_tracking
dimensions:
  test_coverage:              { score: 82, notes: "Lines 82%, branches 81%, functions 85%" }
  test_quality:               { score: 90, notes: "Table-driven, descriptive names, no waits" }
  readability:                { score: 88, notes: "Clear naming, functions < 25 lines" }
  error_handling:             { score: 85, notes: "Specific exceptions, all I/O paths handled, structured logs on state transitions" }
  documentation:              { score: 92, notes: "Docstrings on all public functions" }
  security:                   { score: 95, notes: "No hardcoded secrets, auth present" }
  performance:                { score: 88, notes: "No N+1, indexes present on query columns" }
  architectural_consistency:  { score: 90, notes: "CQRS respected, event schema versioned, no bypass patterns" }
trend_tracking:
  prior_scores: [76, 80, 85]
  module_baseline_avg: 82
  trajectory: upward
model_engineer_input: ready
notes: "Trend is positive. Recommend continued focus on coverage in next cycle."
```

---

### Example 4: REWORK + ESCALATE — Systemic Issues

```
PR #152: Background job processor (initial submission)

Dimensions Assessed:
  Test coverage:    58%  ❌  (below 70% floor — hard blocker)
  Test quality:     55   ❌  (tests mock all real behavior, test nothing)
  Readability:      62   ⚠️
  Error handling:   45   ❌  (bare except clauses throughout, errors silently swallowed)
  Documentation:    70   ⚠️
  Security:         88   ✅
  Performance:      50   ❌  (N+1 query pattern in job dispatch loop)

Overall Score: 61  →  REWORK + ESCALATE

Lead Engineer Decision:
  Status: CHANGES REQUESTED — Escalate to Senior Engineer for design review

  Blocking issues:
    1. Test coverage 58% — hard floor violation (must reach ≥70% before re-review)
    2. Bare except clauses in job_processor.py lines 34, 67, 89, 112 — silently hide failures
    3. N+1 query in dispatch_jobs(): fetches job config inside loop — must batch
    4. Test suite mocks all dependencies — tests cover structure, not behavior

  Escalation reason:
    Error handling and performance issues are not isolated — they reflect a structural
    approach to this module. Senior Engineer should review design before rework.

  Do not re-submit without Senior Engineer sign-off on design.
```

---

## Section 6: Coordination Between Roles

### How Lead Engineer Uses This Baseline

Lead Engineer applies this baseline during PR review:

1. Evaluate each dimension against the indicators in **Section 1**
2. Check all **blocking criteria in Section 3** — any hit is an automatic REWORK
3. Assign an **overall score using Section 2**
4. Deliver structured feedback: blocking issues labelled as blocking, suggestions labelled as non-blocking
5. On re-review, verify each blocking issue was addressed before approving

**Primary skill reference:** `skills/review/code-review.md` (8-point checklist and blocking authority)

---

### How Quality Engineer Uses This Baseline

Quality Engineer applies this baseline after Lead Engineer approval:

1. Score each of the 8 dimensions in **Section 1**
2. Compute overall score using **Section 2**
3. Note trend vs prior PRs from same engineer/module
4. Complete model assessment for Model Engineer routing feedback
5. Log structured output per **Section 4 format**
6. No blocking decisions — assessment feeds metrics and trend tracking only

### Out of Scope: Post-Deployment Performance Regressions

Quality Engineer is not the decision-maker for production performance regressions detected after deployment. These are deployment/rollback decisions, not PR quality decisions.

**QE's role:** Detect regression signals in trend data (e.g., latency +50%, error rate +10%), notify Lead Engineer and Operations, and track whether the regression is corrected in a follow-up deployment.

**Lead/Operations role:** Decide whether to rollback, hot-fix, or accept the regression based on business impact.

QE feeds the signal; Lead + Operations + Product decide the action.

### Architectural Consistency Exception (Dimension 8 Post-Approval)

If QE scores Dimension 8 (Architectural & Design Consistency) below 60 during post-approval assessment (indicating a direct pattern violation, not marginal misalignment), QE should escalate to Lead Engineer and Principal Engineer for awareness.

This is not a re-gating action (QE does not block already-approved PRs). This is a "awareness escalation" — ensure the pattern violation is tracked and that a follow-up task is created before the pattern spreads (copy-paste antipattern).

**Examples of escalation trigger (<60 score):**
- Direct cross-service database access where event bus exists
- Service X calls Service Y's private DB instead of public API
- New stateful singleton introduced in shared module without design review
- Event bypasses canonical schema (ad-hoc message format)

**Example of non-escalation (≥60 score):**
- Minor API design inconsistency with existing patterns (60-70 range) — document and track for next cycle
- Marginal issue in new abstraction (70-80 range) — acceptable with refinement in follow-up

**Primary skill reference:** `skills/review/code-quality-analysis.md` (structured feedback format for Model Engineer)

---

### Shared Reference Points

| Question | Answer | Source |
|----------|--------|--------|
| What is the minimum acceptable test coverage? | 80% (merge block), 70% (REWORK + ESCALATE floor) | Section 3 + Dimension 1 |
| What score triggers a REWORK? | < 80 | Section 2 |
| What score triggers REWORK + ESCALATE? | < 70 | Section 2 |
| Who has authority to block a merge? | Lead Engineer only | Section 3 |
| Who measures quality after approval? | Quality Engineer | Section 4 |
| Does QE post-approval assessment block merge? | No | Section 4 |
| What is a security finding's effect on score? | Overrides score → REWORK + ESCALATE | Section 2 (scoring notes) |

---

## Section 7: Evolving This Baseline

This document is a living standard. Update it when:

- A new pattern becomes convention (add to Dimension 3 — readability indicators)
- A blocking threshold proves too tight or too loose (update Section 3 with rationale)
- A new risk category is identified (add a dimension or blocking criterion)
- Score thresholds are recalibrated based on observed quality trends

**To update:** Submit a PR with the proposed change, reviewed and approved by Lead Engineer before taking effect. Quality Engineer must confirm assessment dimensions remain accurate.

**Version history:** Record significant threshold changes with date and rationale in a `CHANGELOG` comment below this section if needed.
