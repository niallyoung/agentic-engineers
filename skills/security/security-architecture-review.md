# Security Engineer — Security Architecture Review

**Role:** Security Engineer (Opus 4.7, max effort)  
**Purpose:** Review system design for auth, data flows, access control, and cross-service security contracts

---

## Overview

Security Architecture Review examines design decisions (before code is written) to catch security flaws at architectural level. This prevents expensive rework and ensures compliance, resilience, and defense-in-depth.

**Input:** Architecture design (from Principal Engineer), data flow diagrams, threat model  
**Output:** Security audit report with remediation requirements, sign-off

**Goal:** Ship architectures that are secure by design, not secured by patches.

---

## Review Checklist

### 1. Authentication & Authorization

**Questions to ask:**

```
□ How are users identified? (passwords, OAuth, MFA, certificates)
□ Is MFA required? (REQUIRED for high-risk operations)
□ What is the token lifetime? (short-lived access, long-lived refresh OK)
□ How are tokens transported? (HTTPS only, secure cookie flags)
□ How are tokens validated? (signature verification, issuer check, expiry check)
□ Is there a logout mechanism? (token revocation, blacklist, or expiry)
□ Are scopes defined? (granular permissions, not binary)
□ How are scopes enforced? (checked at every boundary)
□ Is there role-based access control (RBAC)? (user → role → permissions)
□ Is there attribute-based access control (ABAC)? (context-dependent access)
□ Can users escalate privileges? (no lateral moves without re-auth)
□ Are admin accounts separate from user accounts? (dedicated admin interfaces)
□ Is there audit logging for access control decisions? (who accessed what, when)
```

**Checklist:**
- [ ] All user-facing APIs require authentication
- [ ] All internal APIs require authentication (IAM, OAuth, mTLS)
- [ ] Token validation includes issuer, audience, signature, expiry
- [ ] Logout invalidates the token (blacklist or short TTL)
- [ ] MFA required for admin operations and sensitive data access
- [ ] Scope enforcement is present at every boundary
- [ ] No hardcoded credentials or default passwords
- [ ] Session/token lifetime is configurable per environment

**Example (BAD):**
```
API Gateway validates JWT signature
  ↓
Backend Lambda trusts API Gateway, doesn't re-validate
  ↓
Problem: If API Gateway config compromised, backend is exposed
```

**Example (GOOD):**
```
API Gateway validates JWT signature + audience
  ↓
Backend Lambda re-validates JWT signature + issuer + expiry
  ↓
Cross-service call uses IAM SigV4 (not JWT)
  ↓
Result: Defense-in-depth — multiple verification layers
```

### 2. Data Protection (Confidentiality, Integrity)

**Questions:**

```
□ What data is sensitive? (PII, API keys, credentials, financial, health)
□ Where is sensitive data stored? (database, logs, caches, backups, CDN)
□ Is sensitive data encrypted at rest? (AES-256, encrypted DB, encrypted backups)
□ Is the encryption key rotated? (when, how often)
□ Is sensitive data encrypted in transit? (TLS 1.2+, no HTTP)
□ Are integrity checks present? (signatures, MACs, hashing)
□ Is sensitive data logged? (NO — never log passwords, API keys, credit cards, PII)
□ Are logs encrypted? (LOG_ENCRYPTION=true, retention policies)
□ Is sensitive data visible in error messages? (NO stack traces with secrets)
□ How are backups protected? (encrypted, off-site, access-controlled)
□ Are CDNs caching sensitive data? (CloudFront NOT caching /api/auth, /user/profile)
□ Is PII anonymized in analytics? (hashed IDs, not real user names)
```

**Checklist:**
- [ ] No plaintext passwords in any storage (use bcrypt/scrypt/Argon2)
- [ ] No API keys in code, logs, or version control (use Secrets Manager)
- [ ] All data at rest encrypted (database, S3, backups, CDN)
- [ ] All data in transit encrypted (TLS 1.2+)
- [ ] Sensitive data NOT logged (or heavily redacted)
- [ ] Key rotation strategy defined (when, how, who owns)
- [ ] Backups encrypted and access-controlled
- [ ] Error messages don't leak sensitive data
- [ ] CDN cache headers prevent caching of sensitive responses

**Example (BAD):**
```
POST /login
Response: {success: true, accessToken: "eyJ...", refreshToken: "eyJ..."}
App logs: "Login response: {success: true, accessToken: "eyJ...", refreshToken: "eyJ..."}"
Problem: Tokens in logs, logs can be accessed by anyone with log access
```

**Example (GOOD):**
```
POST /login
Response: {success: true, accessToken_masked: "eyJ...***"}
App logs: "Login response: {success: true, accessToken: [REDACTED]}"
Database: accessToken stored as bcrypt hash
Problem: Solved — tokens only in memory, never persisted
```

### 3. Access Control at Boundaries

**Questions:**

```
□ Is there a boundary between trusted/untrusted networks? (internal vs. external APIs)
□ Are internal APIs protected from external access? (VPC, security groups, API Gateway auth)
□ Do API Gateway validators run BEFORE Lambda? (catch bad requests early)
□ Is input validation present on all endpoints? (types, lengths, formats)
□ Can a user access other users' data? (authorization checks before responding)
□ Can a user modify other users' data? (authorization checks before mutation)
□ Can a user delete other users' data? (authorization checks before deletion)
□ Are there resource quotas? (rate limiting, size limits)
□ Is there audit logging at the boundary? (who, what, when, result)
□ Are there network controls? (security groups, NACLs, WAF rules)
```

**Checklist:**
- [ ] All user IDs are never trusted from client (extracted from JWT)
- [ ] Authorization checks performed BEFORE accessing data (not after)
- [ ] Resource ownership verified (user can only access their own resources)
- [ ] Rate limiting prevents brute force (login, password reset, API calls)
- [ ] Request size limits prevent memory exhaustion
- [ ] API Gateway validators enforce schema before backend
- [ ] All boundaries have audit logging

**Example (BAD):**
```
GET /users/{userID}/profile
No Authorization check
User A can request /users/bob-id/profile → gets Bob's data
Problem: User A can access any user by guessing IDs
```

**Example (GOOD):**
```
GET /users/{userID}/profile
Authorization check: token.userID must == userID parameter
User A requests /users/bob-id/profile → 403 Forbidden
User A requests /users/alice-id/profile (their own) → 200 OK with data
Problem: Solved — verified ownership before responding
```

### 4. Cross-Service Data Contracts

**Questions:**

```
□ How do services communicate? (REST, gRPC, events, batch)
□ Are cross-service calls authenticated? (IAM SigV4, mTLS, service tokens)
□ Are data formats versioned? (event schema version, API versioning)
□ What data is shared between services? (who owns what)
□ Can a service trust data from another service? (is it already validated)
□ Are there circular dependencies? (A calls B calls A → deadlock risk)
□ Is there a circuit breaker? (timeout, retry, fallback)
□ Are services resilient to failures? (downstream service down → graceful degradation)
□ Is there a contract for data consistency? (strong consistency or eventual)
□ Are there sequence numbers or timestamps for ordering? (event replay order)
```

**Checklist:**
- [ ] All cross-service calls authenticated (IAM SigV4 or mTLS)
- [ ] Data schemas are versioned
- [ ] Data ownership is clear (which service owns which data)
- [ ] No circular service dependencies
- [ ] Circuit breakers on all external calls
- [ ] Retry logic with exponential backoff
- [ ] Fallback behavior defined (degrade gracefully)
- [ ] Event ordering ensured (sequence numbers or FIFO)

**Example (BAD):**
```
{example-service} calls {service-name} (sync) → {service-name} calls {example-service} → {example-service} calls {example-service}
Circular dependency → deadlock risk
```

**Example (GOOD):**
```
{example-service} → {service-name} (IAM SigV4 signed, 3-second timeout, fallback: cache)
{service-name} → {example-service} (IAM SigV4 signed, async with circuit breaker)
{example-service} → SNS (async, fire-and-forget)
Problem: Solved — clear direction, resilience, no circles
```

### 5. Compliance & Regulatory

**Questions:**

```
□ Is there a compliance requirement? (GDPR, HIPAA, PCI-DSS, SOC2, CCPA)
□ Is data residency required? (EU data in EU, no cross-border)
□ Is there a data retention policy? (how long to keep, when to delete)
□ Is there a right to be forgotten? (GDPR — can users request deletion)
□ Is there encryption key management? (KMS, key rotation, access logs)
□ Are there audit logs? (immutable, tamper-evident, long retention)
□ Is there a data processing agreement (DPA)? (if using third-party services)
□ Is there incident response plan? (breach detection, notification, legal)
□ Are there vulnerability scanning requirements? (penetration testing, SAST/DAST)
□ Is there a security training requirement? (developers, ops, admins)
```

**Checklist:**
- [ ] Compliance requirements documented
- [ ] Data residency constraints enforced (multi-region strategy)
- [ ] Data retention policy automated (TTL, deletion jobs)
- [ ] Encryption key management via KMS (not DIY)
- [ ] Audit logs immutable (S3, CloudTrail)
- [ ] Incident response plan tested
- [ ] Penetration testing scheduled
- [ ] Third-party vendors have security certification

### 6. Operational Security

**Questions:**

```
□ How are AWS credentials managed? (IAM roles, cross-account, temporary tokens)
□ Are there separate dev/staging/prod accounts? (isolation)
□ Are there permission boundaries? (developers can't delete prod databases)
□ Is there a change control process? (approvals before production changes)
□ Is there infrastructure-as-code versioning? (CDK, Terraform, git history)
□ Are there secrets management? (Secrets Manager, not hardcoded)
□ Are there monitoring & alerting? (suspicious activity, anomalies)
□ Is there an on-call rotation? (incident response coverage)
□ Is there a disaster recovery plan? (RTO, RPO, testing)
□ Is there a decommissioning process? (data deletion, account cleanup)
```

**Checklist:**
- [ ] AWS IAM follows least privilege (fine-grained permissions)
- [ ] Separate AWS accounts per environment
- [ ] Permission boundaries prevent privilege escalation
- [ ] All secrets in Secrets Manager (not in code or logs)
- [ ] Infrastructure-as-code in version control (CDK tracked)
- [ ] All changes logged (CloudTrail, VCS audit)
- [ ] Security monitoring enabled (CloudWatch, GuardDuty, Config)
- [ ] Incident response runbook exists and is tested
- [ ] Disaster recovery tested (restore from backup)

---

## Output Template

```
# Security Architecture Review: [System/Feature]

## Executive Summary
[1 paragraph: overall security posture, critical findings, risk level]

## Scope
- Architecture document reviewed: [reference]
- Threat model basis: [reference to threat-modeling.md]
- Services affected: [list]
- Critical data: [PII, secrets, financial, etc.]

## Authentication & Authorization

### Assessment
- [ ] All APIs require authentication
- [ ] Token validation includes signature + issuer + audience
- [ ] Logout invalidates tokens
- [ ] MFA required for sensitive ops
- [ ] Scope enforcement present
- [ ] No hardcoded credentials

**Findings:**
- ✅ GOOD: JWT signature validation in API Gateway
- ⚠️  MEDIUM: MFA not enforced for admin operations
- ❌ CRITICAL: Default password in IAM role trust policy

**Remediation:**
1. Add MFA requirement for admin API endpoints
2. Remove default password, use temporary STS tokens only

## Data Protection

### Assessment
- [ ] Sensitive data identified
- [ ] Encryption at rest (AES-256)
- [ ] Encryption in transit (TLS 1.2+)
- [ ] No sensitive data in logs
- [ ] Key rotation strategy defined
- [ ] Backups encrypted

**Findings:**
- ✅ GOOD: DynamoDB encryption enabled
- ✅ GOOD: Logs redacted (tokens not logged)
- ⚠️  MEDIUM: Key rotation not automated
- ❌ CRITICAL: S3 bucket public, PII exposed

**Remediation:**
1. Implement automated key rotation via KMS
2. Restrict S3 bucket to private, enable versioning + MFA delete

## Access Control at Boundaries

### Assessment
- [ ] Internal/external boundary clear
- [ ] User IDs from JWT (not client)
- [ ] Authorization checks before data access
- [ ] Rate limiting on sensitive endpoints
- [ ] Request size limits
- [ ] Audit logging

**Findings:**
- ✅ GOOD: Authorization checks on all /user/* endpoints
- ⚠️  MEDIUM: Rate limiting missing on /login endpoint
- ❌ CRITICAL: Users can access other users' orders by guessing order IDs

**Remediation:**
1. Add rate limiting to /login (5 attempts/minute)
2. Add authorization check to verify order.userID == token.userID

## Cross-Service Data Contracts

### Assessment
- [ ] Cross-service calls authenticated
- [ ] Data schemas versioned
- [ ] Data ownership clear
- [ ] No circular dependencies
- [ ] Circuit breakers present
- [ ] Event ordering ensured

**Findings:**
- ✅ GOOD: All inter-service calls IAM SigV4 signed
- ✅ GOOD: Event schema includes version field
- ⚠️  MEDIUM: No circuit breaker on external API calls
- ❌ CRITICAL: Event stream unordered, replay fails

**Remediation:**
1. Add circuit breaker pattern (timeout + retry + fallback)
2. Enforce FIFO queue for event ordering

## Compliance & Regulatory

### Assessment
- [ ] Requirements documented
- [ ] Data residency enforced
- [ ] Retention policy automated
- [ ] KMS key management
- [ ] Audit logs immutable
- [ ] Incident response plan

**Findings:**
- ✅ GOOD: GDPR data residency enforced (EU only)
- ⚠️  MEDIUM: No automated data retention
- ❌ CRITICAL: Logs stored in S3 without versioning (tamper risk)

**Remediation:**
1. Implement DynamoDB TTL for automatic data deletion
2. Enable S3 Object Lock for audit logs (immutability)

## Operational Security

### Assessment
- [ ] IAM least privilege
- [ ] Separate dev/staging/prod accounts
- [ ] Permission boundaries
- [ ] Secrets in Secrets Manager
- [ ] Infrastructure-as-code versioned
- [ ] Monitoring & alerting enabled

**Findings:**
- ✅ GOOD: Separate AWS accounts per environment
- ✅ GOOD: All secrets in Secrets Manager
- ⚠️  MEDIUM: No monitoring for suspicious IP access patterns
- ❌ CRITICAL: Production permissions too permissive (developers can delete tables)

**Remediation:**
1. Add CloudWatch alarms for suspicious activity
2. Implement permission boundaries (developers limited to non-prod resources)

## Risk Summary

| Issue | Severity | Impact | Timeline |
|-------|----------|--------|----------|
| Public S3 bucket | CRITICAL | Data breach, PII exposed | Fix immediately |
| Order ID access bypass | CRITICAL | User data leakage | Fix before launch |
| MFA missing | HIGH | Account takeover | Fix before launch |
| Rate limiting missing | HIGH | Brute force | Fix within sprint |
| No circuit breaker | MEDIUM | Cascading failures | Fix within sprint |
| Event ordering | MEDIUM | Replay failures | Fix before launch |

## Sign-off

- Security Engineer: [name]
- Architecture Owner: [name]
- Product Manager: [name] (accepts remaining risks)
- Launch approval: [APPROVED | CONDITIONAL | BLOCKED]

**Conditions for launch:**
- [ ] Critical issues resolved
- [ ] Penetration testing completed
- [ ] Incident response plan reviewed and tested
```

---

## Integration with Threat Modeling & Vulnerability Assessment

**threat-modeling.md** → "What can go wrong?" (identifies threats)  
**vulnerability-assessment.md** → "Where are the weaknesses?" (finds CVEs, bugs)  
**security-architecture-review.md** → "Is the design sound?" (validates architecture)

These three work together:
1. Design phase: Security Architect reviews (this skill)
2. Threat analysis: Threat Modeling identifies attacks (threat-modeling.md)
3. Code phase: Vulnerability Assessment finds weaknesses (vulnerability-assessment.md)

---

## Success Criteria

✅ Architecture review completed before implementation starts  
✅ All critical and high-risk findings documented with remediation  
✅ Authentication and authorization strategy clear and justified  
✅ Data protection strategy aligns with compliance requirements  
✅ Cross-service contracts are secure and versioned  
✅ Operational security controls are feasible (not just theoretical)  
✅ Security sign-off obtained before design approval  
✅ Launch is not blocked by unresolved critical findings
