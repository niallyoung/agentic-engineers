"""
tests/evals/conftest.py — Fixtures for DELEGATE/HANDBACK quality evaluation tests.

Provides canonical samples of valid DELEGATEs and HANDBACKs to serve as the basis
for quality evaluation tests. All samples conform to QUEUE-PROTOCOL.md canonical schema.
"""

import pytest
from typing import Dict, List


# ============================================================================
# CANONICAL DELEGATE SAMPLES (valid, conforming to QUEUE-PROTOCOL.md)
# ============================================================================

@pytest.fixture
def canonical_delegate_basic() -> Dict:
    """
    Minimal valid DELEGATE with all required fields.

    Required fields per QUEUE-PROTOCOL.md:
    - handoff_type: "DELEGATE"
    - task_id: kebab-case format (YYYY-MM-DD-...)
    - agent: hyphenated lowercase
    - scope: >= 15 words
    - plan: list of imperative steps
    - success_criteria: list of measurable criteria
    - context: string or list with >= 20 words
    """
    return {
        "handoff_type": "DELEGATE",
        "task_id": "2026-06-09-implement-token-grace-period",
        "agent": "engineer",
        "model": "claude-haiku-4.5",
        "effort": "medium",
        "scope": "Add 30-second grace period to token expiry validation in auth-service to account for clock skew on mobile devices",
        "plan": [
            "Read lambda/api/main.go to understand current token validation logic",
            "Locate expiry check at line 92 and identify the exp claim validation",
            "Add 30-second grace period constant and update validation logic",
            "Add test TestTokenExpiryGracePeriod to cover edge cases",
            "Run make verify to ensure all tests pass",
        ],
        "context": [
            "Service: auth-service (Go/Lambda)",
            "Problem: Mobile devices with clock skew (20-30 seconds behind) fail token validation",
            "File: lambda/api/main.go line 92 (token expiry check)",
            "Reference: docs/DESIGN.md line 156 (token lifecycle)",
        ],
        "success_criteria": [
            "Token validation logic accepts tokens within 30-second grace period",
            "Tokens expired more than 30 seconds ago are rejected",
            "All existing tests pass without regressions",
            "New test TestTokenExpiryGracePeriod provides coverage for grace period edge cases",
        ],
    }


@pytest.fixture
def canonical_delegate_senior() -> Dict:
    """Valid DELEGATE for senior-engineer (complex, unscoped)."""
    return {
        "handoff_type": "DELEGATE",
        "task_id": "2026-06-09-design-cross-service-auth",
        "agent": "senior-engineer",
        "model": "claude-sonnet-4.5",
        "effort": "high",
        "scope": "Design cross-service authentication architecture that handles token sharing across microservices in a distributed system with proper isolation and revocation semantics",
        "context": "Current system has service-to-service auth via shared secrets; needs replacement with JWT-based system supporting fine-grained permissions and revocation chains",
        "success_criteria": [
            "Architecture document with threat model and isolation guarantees",
            "Implementation plan for migration from existing system",
            "Design handles token revocation without database queries for every request",
        ],
    }


@pytest.fixture
def canonical_delegate_security() -> Dict:
    """Valid DELEGATE for security-engineer (security-scoped)."""
    return {
        "handoff_type": "DELEGATE",
        "task_id": "2026-06-09-audit-secret-exposure-risk",
        "agent": "security-engineer",
        "model": "claude-opus-4.8",
        "effort": "high",
        "scope": "Conduct security audit of secret management practices in all deployed services to identify exposure risks and recommend hardening measures",
        "context": "Recent vulnerability disclosure in upstream library; need to assess attack surface and compliance gaps",
        "success_criteria": [
            "Complete inventory of secrets across all services (DB credentials, API keys, certs)",
            "Threat model identifying exposure vectors and current mitigations",
            "Actionable recommendations ranked by risk severity",
        ],
    }


@pytest.fixture
def canonical_delegate_quality() -> Dict:
    """Valid DELEGATE for quality-engineer (verification task)."""
    return {
        "handoff_type": "DELEGATE",
        "task_id": "2026-06-09-verify-token-cache-handback",
        "agent": "quality-engineer",
        "model": "claude-sonnet-4.6",
        "effort": "medium",
        "scope": "Review and verify engineer HANDBACK for token-cache feature to ensure quality gates are met and no regressions exist",
        "context": "Engineer completed token cache feature; need QE sign-off before merging to main",
        "success_criteria": [
            "All automated tests pass with no regressions",
            "Code coverage maintained above 87%",
            "Manual E2E test confirms cache hit rates improve by at least 15%",
            "Security review confirms no credential leakage in cache",
        ],
    }


@pytest.fixture
def canonical_delegate_escalated() -> Dict:
    """Valid DELEGATE for escalated work (from engineer to senior-engineer)."""
    return {
        "handoff_type": "DELEGATE",
        "task_id": "2026-06-09-fix-race-condition-escalated-to-senior-engineer",
        "agent": "senior-engineer",
        "model": "claude-sonnet-4.5",
        "effort": "high",
        "scope": "Resolve critical race condition in token validation logic that causes intermittent 401 errors under high concurrency",
        "context": [
            "Original task: fix token validation timeout",
            "Engineer escalation reason: Race condition in concurrent validation path requires architectural review",
            "Escalation chain: [engineer, senior-engineer]",
            "Blocker: Concurrent access to shared Redis TTL cache without proper locking",
        ],
        "success_criteria": [
            "Race condition eliminated with proper synchronization strategy",
            "Load test with 200+ concurrent requests shows no 401 errors",
            "Solution explains architectural tradeoff between performance and correctness",
        ],
    }


# ============================================================================
# CANONICAL HANDBACK SAMPLES (success, failure, escalation)
# ============================================================================

@pytest.fixture
def canonical_handback_success() -> Dict:
    """
    Valid HANDBACK with status=success and complete metrics.

    Required fields per QUEUE-PROTOCOL.md:
    - handoff_type: "HANDBACK"
    - task_id: matches DELEGATE task_id
    - agent: agent that completed the work
    - status: one of [success, failure, partial, blocked, escalate]
    - output: any value (result of work)
    - metrics: dict with [quality, tokens, cost, duration_seconds] all numeric
    """
    return {
        "handoff_type": "HANDBACK",
        "task_id": "2026-06-09-implement-token-grace-period",
        "agent": "engineer",
        "status": "success",
        "output": {
            "summary": "Modified lambda/api/main.go to add 30-second grace period to exp claim validation",
            "changes": [
                "lambda/api/main.go: Added GRACE_PERIOD_SECONDS = 30 constant (line 85)",
                "lambda/api/main.go: Updated exp validation to check (now_unix <= exp + GRACE_PERIOD_SECONDS) (line 93-96)",
                "lambda/api/main.go: Added explanatory comment about clock skew tolerance",
                "tests/auth/test_token_validation.py: Added TestTokenExpiryGracePeriod with 5 test cases",
            ],
            "files_modified": ["lambda/api/main.go", "tests/auth/test_token_validation.py"],
            "commit_hash": "a1b2c3d4e5f6",
        },
        "metrics": {
            "quality": 0.95,
            "tokens": 1200,
            "cost": 0.048,
            "duration_seconds": 180.5,
        },
        "model_used": "claude-haiku-4.5",
        "effort_actual": "medium",
        "tests": {
            "passed": 47,
            "failed": 0,
            "coverage": 87.3,
        },
        "confidence": 0.95,
    }


@pytest.fixture
def canonical_handback_failure() -> Dict:
    """Valid HANDBACK with status=failure (work could not be completed)."""
    return {
        "handoff_type": "HANDBACK",
        "task_id": "2026-06-09-migrate-database-schema",
        "agent": "engineer",
        "status": "failure",
        "output": {
            "error": "Backward compatibility constraint violated: existing column name conflicts with new schema",
            "details": "Attempted to rename 'status' column to 'status_code' but 15 dependent views exist with no documented migration path",
            "blocker": "Requires coordination with 3 downstream services; cannot proceed without DESIGN review",
        },
        "metrics": {
            "quality": 0.15,
            "tokens": 800,
            "cost": 0.032,
            "duration_seconds": 120.0,
        },
        "model_used": "claude-haiku-4.5",
        "error": "Dependency analysis revealed unmapped downstream impact",
        "confidence": 0.85,
    }


@pytest.fixture
def canonical_handback_partial() -> Dict:
    """Valid HANDBACK with status=partial (some work completed, some remains)."""
    return {
        "handoff_type": "HANDBACK",
        "task_id": "2026-06-09-refactor-auth-module",
        "agent": "engineer",
        "status": "partial",
        "output": {
            "summary": "Refactored auth module core; dependency injection layer incomplete",
            "completed": [
                "Extracted TokenValidator into standalone class with pure functions",
                "Added 42 unit tests with 91% code coverage",
                "Integrated with existing service instantiation",
            ],
            "remaining": [
                "Implement optional dependency injection container for test mocks",
                "Add integration tests with live Redis instance",
            ],
        },
        "metrics": {
            "quality": 0.72,
            "tokens": 1500,
            "cost": 0.060,
            "duration_seconds": 240.0,
        },
        "model_used": "claude-haiku-4.5",
        "effort_actual": "high",
        "tests": {
            "passed": 42,
            "failed": 0,
            "coverage": 91.0,
        },
        "confidence": 0.70,
    }


@pytest.fixture
def canonical_handback_blocked() -> Dict:
    """Valid HANDBACK with status=blocked (awaiting external input)."""
    return {
        "handoff_type": "HANDBACK",
        "task_id": "2026-06-09-integrate-payment-processor",
        "agent": "engineer",
        "status": "blocked",
        "output": {
            "blocker": "API credentials for Stripe test environment not available in CI",
            "context": "Integration requires live Stripe API key; currently hardcoded mock only",
            "next_steps": "Await Infrastructure team to provision secure secret storage in CI/CD pipeline",
        },
        "metrics": {
            "quality": 0.40,
            "tokens": 450,
            "cost": 0.018,
            "duration_seconds": 60.0,
        },
        "model_used": "claude-haiku-4.5",
        "error": "External dependency unavailable",
        "confidence": 0.80,
    }


@pytest.fixture
def canonical_handback_escalate() -> Dict:
    """Valid HANDBACK with status=escalate (escalating to next agent)."""
    return {
        "handoff_type": "HANDBACK",
        "task_id": "2026-06-09-fix-race-condition",
        "agent": "engineer",
        "status": "escalate",
        "output": {
            "escalate_to": "senior-engineer",
            "reason": "Race condition in concurrent token validation requires architectural review beyond engineer scope",
            "analysis": "Found concurrent access to shared Redis TTL cache without proper locking in token_validator.py:42-67",
            "why_escalate": "Fix requires selecting between 3 architectural approaches (mutex vs atomic ops vs queue-based); needs design guidance",
        },
        "escalation_chain": ["engineer"],
        "metrics": {
            "quality": 0.50,
            "tokens": 950,
            "cost": 0.038,
            "duration_seconds": 150.0,
        },
        "model_used": "claude-haiku-4.5",
        "confidence": 0.75,
    }


@pytest.fixture
def canonical_handback_low_quality() -> Dict:
    """Valid HANDBACK with status=success but quality=0.45 (QE would reject)."""
    return {
        "handoff_type": "HANDBACK",
        "task_id": "2026-06-09-implement-feature-low-quality",
        "agent": "engineer",
        "status": "success",
        "output": {
            "summary": "Feature implemented but with significant shortcuts",
        },
        "metrics": {
            "quality": 0.45,
            "tokens": 1100,
            "cost": 0.044,
            "duration_seconds": 170.0,
        },
        "model_used": "claude-haiku-4.5",
        "tests": {
            "passed": 20,
            "failed": 5,
            "coverage": 63.0,
        },
        "confidence": 0.55,
    }


@pytest.fixture
def canonical_handback_high_quality() -> Dict:
    """Valid HANDBACK with status=success and quality=0.98 (exemplary)."""
    return {
        "handoff_type": "HANDBACK",
        "task_id": "2026-06-09-implement-feature-exemplary",
        "agent": "engineer",
        "status": "success",
        "output": {
            "summary": "Feature implemented with comprehensive tests and documentation",
            "deliverables": [
                "Implementation with proper error handling",
                "90+ automated tests with edge case coverage",
                "User documentation with examples",
                "Inline code comments explaining complex logic",
            ],
        },
        "metrics": {
            "quality": 0.98,
            "tokens": 2100,
            "cost": 0.084,
            "duration_seconds": 320.0,
        },
        "model_used": "claude-haiku-4.5",
        "tests": {
            "passed": 94,
            "failed": 0,
            "coverage": 98.5,
        },
        "confidence": 0.98,
    }


# ============================================================================
# CORPUS FIXTURES: Collections of samples for batch testing
# ============================================================================

@pytest.fixture
def delegate_corpus() -> List[Dict]:
    """Corpus of 5 valid DELEGATEs for testing routing and quality evals."""
    return [
        {
            "handoff_type": "DELEGATE",
            "task_id": "2026-06-09-fix-auth-timeout-race-condition",
            "agent": "engineer",
            "scope": "Fix token validation timeout that causes intermittent 401 errors when processing requests under load with concurrent token access patterns",
            "plan": [
                "Read auth/token.py to understand current timeout logic and token validation",
                "Identify race condition in concurrent validation path causing 401s under load",
                "Apply fix with proper locking mechanism to serialize access to token cache",
                "Write comprehensive test coverage for concurrent token validation scenarios",
                "Run full test suite to verify no regressions in authentication behavior",
            ],
            "context": [
                "Service: auth-service (Go implementation)",
                "Problem: 401 errors spike during periods of 100+ concurrent requests",
                "Root cause: Concurrent access to shared token cache without synchronization",
                "Frequency: Intermittent failures observed in production (P1 severity)",
            ],
            "success_criteria": [
                "No 401 errors under sustained 200+ concurrent requests in load test",
                "All existing authentication tests pass without regression",
                "New concurrent test cases validate locking behavior",
                "Performance impact of locking is < 5% latency increase",
            ],
        },
        {
            "handoff_type": "DELEGATE",
            "task_id": "2026-06-09-audit-vulnerability-exposure",
            "agent": "security-engineer",
            "scope": "Conduct comprehensive security audit of secret management practices in all deployed services to identify credential exposure risks and recommend hardening measures",
            "plan": [
                "Scan all service repositories for hardcoded secrets using automated tools",
                "Document inventory of secrets by service, environment, and rotation status",
                "Assess current secret storage mechanisms and identify exposure vectors",
                "Evaluate compliance gaps against industry standards and internal security policy",
                "Create threat model documenting attack scenarios and mitigations",
                "Provide prioritized recommendations for hardening secret management",
            ],
            "context": [
                "Recent vulnerability disclosure in upstream dependency exposed secret patterns",
                "Need to assess attack surface and compliance gap across 12 microservices",
                "Current practice has secrets scattered across environment files and ConfigMaps",
                "Must complete within 14 days per security steering committee mandate",
            ],
            "success_criteria": [
                "Complete inventory of all secrets across all deployed services documented",
                "Threat model with identified attack scenarios and likelihood assessment",
                "Prioritized recommendations ranked by risk severity and implementation effort",
                "Gap analysis against industry standards (e.g., NIST, AWS Secrets best practices)",
                "Remediation roadmap with estimated timeline and resource requirements",
            ],
        },
        {
            "handoff_type": "DELEGATE",
            "task_id": "2026-06-09-design-cross-service-auth",
            "agent": "senior-engineer",
            "scope": "Design cross-service authentication architecture that handles JWT token sharing across microservices with fine-grained permissions, proper service isolation, and efficient token revocation semantics",
            "plan": [
                "Review current service-to-service authentication model and identify gaps",
                "Research JWT-based authentication approaches suitable for distributed systems",
                "Design token format, claims structure, and issuer/verifier patterns",
                "Develop isolation strategy ensuring services cannot exceed their permission boundaries",
                "Design revocation mechanism supporting both immediate and eventual consistency models",
                "Create architecture document with threat model and deployment strategy",
                "Plan incremental migration path from current secret-based system",
            ],
            "context": [
                "Current system uses shared secrets between services; security team requires JWT migration",
                "Must support fine-grained permissions per service pair (not all-or-nothing)",
                "Must enable fast revocation without requiring database queries for every request",
                "12 microservices in total; migration must be phased across 6 months",
            ],
            "success_criteria": [
                "Comprehensive architecture document with design rationale and threat model",
                "Detailed design of JWT claims structure and permission model",
                "Specification of revocation mechanism with performance analysis",
                "Incremental migration plan with minimal disruption to production services",
                "Security review from infrastructure/security engineers confirming threat mitigations",
            ],
        },
        {
            "handoff_type": "DELEGATE",
            "task_id": "2026-06-09-verify-token-cache-implementation",
            "agent": "quality-engineer",
            "scope": "Review and verify engineer HANDBACK for token-cache feature implementation to ensure all quality gates are met and no regressions exist in production behavior",
            "plan": [
                "Review code changes against style guide and architecture patterns",
                "Verify all unit tests pass and new test coverage meets minimum threshold",
                "Run manual end-to-end tests simulating production token cache scenarios",
                "Verify performance improvements meet acceptance criteria (cache hit rate >= 15%)",
                "Conduct security review confirming no credential leakage in cache layer",
                "Verify backward compatibility with existing token validation clients",
            ],
            "context": [
                "Engineer completed token cache feature; code review passed",
                "Need QE sign-off before merge to main branch and deployment",
                "Feature improves auth latency by caching validated tokens for 60 seconds",
                "Production load test results show promising preliminary performance gains",
            ],
            "success_criteria": [
                "All automated test suite passes with no regressions (47 tests)",
                "Code coverage maintained above 87% minimum threshold",
                "Manual E2E test confirms cache hit rates improve by at least 15%",
                "Security review confirms no credential leakage in cache implementation",
                "Performance benchmark shows average latency reduction of 50-200ms per request",
            ],
        },
        {
            "handoff_type": "DELEGATE",
            "task_id": "2026-06-09-evaluate-database-migration-strategy",
            "agent": "principal-engineer",
            "scope": "Evaluate and design database migration strategy for moving from MongoDB to PostgreSQL across three interdependent microservices while maintaining data consistency and availability",
            "plan": [
                "Audit current MongoDB usage patterns across all three affected services",
                "Analyze data models and schema for relational normalization opportunities",
                "Design dual-write strategy supporting gradual cutover from MongoDB to PostgreSQL",
                "Develop zero-downtime migration approach with read-your-own-writes consistency",
                "Create comprehensive testing strategy for consistency validation during migration",
                "Document rollback procedures and failure recovery mechanisms",
                "Estimate timeline, resource requirements, and risk mitigation strategies",
            ],
            "context": [
                "MongoDB license change makes continued use financially unsustainable",
                "Three services are tightly coupled via shared data collections (migration complex)",
                "Must maintain high availability (SLA requires <= 30 minutes downtime window)",
                "Organization has limited PostgreSQL expertise; training required",
            ],
            "success_criteria": [
                "Comprehensive migration architecture with zero-downtime cutover plan",
                "Risk assessment identifying potential failure modes and mitigations",
                "Detailed rollback procedures ensuring data recovery capability",
                "Timeline estimate with critical path analysis and dependency mapping",
                "Resource and skill requirements assessment with training recommendations",
                "Post-migration validation strategy confirming data integrity",
            ],
        },
    ]


@pytest.fixture
def handback_corpus() -> List[Dict]:
    """Corpus of 5 valid HANDBACKs with mixed statuses for testing."""
    return [
        {
            "handoff_type": "HANDBACK",
            "task_id": "2026-06-09-fix-auth-timeout-race-condition",
            "agent": "engineer",
            "status": "success",
            "output": {
                "summary": "Fixed race condition in token validation with proper mutex-based locking",
                "changes": [
                    "Added RWMutex to TokenValidator struct to synchronize cache access",
                    "Implemented read lock for token lookup and write lock for cache updates",
                    "Added 47 new test cases covering concurrent access patterns",
                ],
                "test_results": "47 passed, 0 failed; coverage 91.2%",
                "performance": "Added ~2ms latency per token validation; no measurable impact under load",
            },
            "metrics": {
                "quality": 0.92,
                "tokens": 1200,
                "cost": 0.048,
                "duration_seconds": 180.0,
            },
            "confidence": 0.92,
        },
        {
            "handoff_type": "HANDBACK",
            "task_id": "2026-06-09-audit-vulnerability-exposure",
            "agent": "security-engineer",
            "status": "success",
            "output": {
                "summary": "Security audit completed identifying 12 critical findings and 8 medium-risk exposures",
                "findings": [
                    "3 services have plaintext credentials in environment files (CRITICAL)",
                    "6 services lack secret rotation strategy (MEDIUM)",
                    "Database credentials stored in git history for 2 services (CRITICAL)",
                ],
                "inventory": "Documented 47 secrets across 12 services with rotation status",
                "recommendations": "Migrating to HashiCorp Vault with quarterly credential rotation policy",
            },
            "metrics": {
                "quality": 0.88,
                "tokens": 3500,
                "cost": 0.140,
                "duration_seconds": 420.0,
            },
            "confidence": 0.88,
        },
        {
            "handoff_type": "HANDBACK",
            "task_id": "2026-06-09-design-cross-service-auth",
            "agent": "senior-engineer",
            "status": "success",
            "output": {
                "summary": "Designed JWT-based cross-service authentication with fine-grained permissions and efficient revocation",
                "deliverables": [
                    "Architecture document (12 pages) with threat model analysis",
                    "JWT claims structure supporting role-based access control (RBAC)",
                    "Revocation mechanism using Redis-backed bloom filters for fast TTL checks",
                ],
                "design_options_evaluated": "Considered 3 approaches; selected decentralized verification with async revocation",
                "migration_timeline": "6-month phased rollout across 12 microservices with rollback strategy",
            },
            "metrics": {
                "quality": 0.85,
                "tokens": 2800,
                "cost": 0.112,
                "duration_seconds": 480.0,
            },
            "confidence": 0.85,
        },
        {
            "handoff_type": "HANDBACK",
            "task_id": "2026-06-09-verify-token-cache-implementation",
            "agent": "quality-engineer",
            "status": "partial",
            "output": {
                "summary": "Code and functional testing complete; performance validation in progress",
                "completed": [
                    "Code review passed: 14 files changed, 320 lines added with no style issues",
                    "Unit test suite: 47 tests pass, 100% coverage of cache logic",
                    "Security review: No credential leakage in cache layer confirmed",
                ],
                "in_progress": [
                    "Production load testing to validate 15% cache hit rate improvement",
                    "Integration test with downstream auth clients (2 services)",
                ],
                "timeline": "Expect QE sign-off within 2 days pending load test results",
            },
            "metrics": {
                "quality": 0.68,
                "tokens": 1500,
                "cost": 0.060,
                "duration_seconds": 240.0,
            },
            "confidence": 0.70,
        },
        {
            "handoff_type": "HANDBACK",
            "task_id": "2026-06-09-integrate-payment-processor",
            "agent": "engineer",
            "status": "blocked",
            "output": {
                "blocker": "Stripe test API credentials not provisioned in CI/CD environment",
                "attempted": [
                    "Implemented Stripe payment integration with proper error handling",
                    "Created unit tests using Stripe mock library",
                ],
                "blocking_factor": "CI/CD pipeline cannot authenticate with Stripe API; secrets management not yet deployed",
                "next_steps": "Await Infrastructure team to provision secure secret storage (estimated 3-5 days)",
                "impact": "Feature cannot merge to main until integration tests pass against live Stripe API",
            },
            "metrics": {
                "quality": 0.40,
                "tokens": 450,
                "cost": 0.018,
                "duration_seconds": 60.0,
            },
            "confidence": 0.80,
        },
    ]
