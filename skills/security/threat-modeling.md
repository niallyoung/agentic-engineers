# Security Engineer — Threat Modeling

**Role:** Security Engineer (Opus 4.7, max effort)  
**Purpose:** Identify security threats and design mitigations before implementation

---

## Overview

Threat modeling systematically identifies "what can go wrong" in a system so architects and engineers can defend against it.

**Input:** Architecture design, data flows, trust boundaries  
**Output:** STRIDE threat list, mitigation plan

**Goal:** Ship software that's hard to attack.

---

## Threat Categories (STRIDE)

| Category | Examples | Impact |
|----------|----------|--------|
| **Spoofing** | Attacker impersonates a user or service | Unauthorized access, fraud |
| **Tampering** | Attacker modifies data in transit or at rest | Data corruption, fraud |
| **Repudiation** | User denies an action (audit trail missing) | No accountability, insider threats |
| **Information Disclosure** | Sensitive data exposed (password, PII, API keys) | Privacy violation, further attacks |
| **Denial of Service** | Attacker makes system unavailable | Business disruption |
| **Elevation of Privilege** | Attacker gains higher permissions | Full system compromise |

---

## Methodology

### 1. Define Trust Boundaries

Who/what is inside the trust boundary, and who/what is outside?

```
Inside (trusted):
  - Internal services
  - Company infrastructure

Outside (untrusted):
  - User browsers
  - Third-party APIs
  - Network

Boundary crossing = validation point
```

### 2. Map Data Flows

For each flow, ask:

- **Where does data come from?** (user input, API, database, file)
- **Where does it go?** (database, external API, user response)
- **Who can access it?** (public, authenticated users, admins)
- **What could go wrong?**
  - Could it be spoofed at entry?
  - Could it be modified in transit?
  - Could it be leaked at rest?

### 3. Identify Threats (STRIDE)

For each data flow:

```
Flow: User submits password during login

Spoofing threat:
  - Attacker intercepts login form → replaces with fake → steals password
  - Mitigation: HTTPS only, validate server certificate

Tampering threat:
  - Attacker modifies password in transit → sets their own password
  - Mitigation: HTTPS (encryption), POST not GET (not in URL)

Information disclosure threat:
  - Password logged in plaintext in logs
  - Mitigation: Hash passwords before storage, never log passwords

Denial of service threat:
  - Attacker sends 1M login attempts → slows down service
  - Mitigation: Rate limiting, account lockout after N failures
```

### 4. Rate Severity & Likelihood

```
Severity:
  - High: Could compromise user accounts, steal data, take system down
  - Medium: Could leak minor data, degrade performance
  - Low: Limited impact, difficult to exploit

Likelihood:
  - High: Easy to exploit, no current defenses, known attack
  - Medium: Moderate effort, partially defended
  - Low: Difficult to exploit, well-defended, rare attack

Risk = Severity × Likelihood
```

### 5. Design Mitigations

For each threat, design a defense:

```
Threat: Attacker gets database dump, sees user passwords

Current state (vulnerability):
  - Passwords stored in plaintext OR weak hashing

Mitigation options:
  A) Use bcrypt with 12 rounds (password never visible, rehashing expensive)
  B) Encrypt passwords with AES + master key rotation
  C) Stop storing passwords (use OAuth with identity provider)

Recommend: Option A (bcrypt)
  - Passwords take 100ms to check (OK for login, defeats brute force)
  - If DB dumped, attacker needs 100ms per guess (defeats rainbow tables)
  - Industry standard, well-tested
```

### 6. Verify with Testing

Once implemented, verify mitigations work:

```
Threat: Attacker modifies JWT token → claims higher permissions

Mitigation: Sign JWT with RS256 (RSA)
  - Token is signed with private key
  - Attacker can modify token, but signature won't match
  - Server rejects modified token

Verification:
  - Test: Modify token, signature becomes invalid, server rejects ✅
  - Test: Attacker creates new token (can't, no private key) ✅
  - Test: Token expires after 1hr (even if valid, not usable) ✅
```

---

## Output Template

```
# Threat Model: [System/Feature]

## System Overview

[Architecture diagram or description]

## Trust Boundaries

Inside (trusted):
  - [component A]
  - [component B]

Outside (untrusted):
  - [user]
  - [third-party API]

## Data Flows

### Flow 1: [Name]
- Source: [user input]
- Destination: [database]
- Access: [who can see this data?]

[Repeat for other flows]

## Threats by Category

### Spoofing

| Threat | Likelihood | Severity | Mitigation | Status |
|--------|-----------|----------|------------|--------|
| Attacker forges JWT token | Medium | High | RS256 signature validation | Implemented |
| Attacker spoofs service A | Low | High | mTLS between services | Implemented |

### Tampering

| Threat | Likelihood | Severity | Mitigation | Status |
|--------|-----------|----------|------------|--------|
| API response modified in transit | Low | High | HTTPS + signature | Implemented |
| Database modified by attacker | Medium | Critical | IAM + encryption | In progress |

[Continue for other categories...]

## Risk Summary

| Risk Level | Count | Mitigated | Remaining |
|-----------|-------|-----------|-----------|
| Critical | 2 | 2 | 0 ✅ |
| High | 5 | 5 | 0 ✅ |
| Medium | 8 | 6 | 2 ⚠️ |
| Low | 12 | 10 | 2 |

## Open Threats (Not Mitigated Yet)

### [Threat A]
- Likelihood: Medium
- Severity: Medium
- Why not mitigated: Requires performance evaluation first
- Timeline: Planned for Q2

### [Threat B]
- Likelihood: Low
- Severity: Low
- Why acceptable: Requires mTLS, not justified for third-party integrations
- Acceptance: By [stakeholder]

## Defense in Depth

For critical threats, multiple layers:

```
Threat: Attacker dumps database, gets passwords

Layer 1: Encryption at rest (AES-256)
  → Attacker has ciphertext, not plaintext

Layer 2: Bcrypt password hashing
  → Even with encryption broken, passwords take 100ms each

Layer 3: Password audit logging
  → Unusual access patterns detected, incident triggered

Layer 4: Account lockout
  → After 5 failed attempts, account locked for 30min
```

## Testing & Verification

Threats validated by:
- [ ] Unit tests (input validation works)
- [ ] Integration tests (end-to-end flow secure)
- [ ] Penetration testing (attempted attack fails)
- [ ] Code review (no secrets in logs, error messages)
- [ ] Security scanning (static/dynamic analysis)

## Sign-off

- Security Engineer: [name]
- Architecture Owner: [name]
- Product Manager: [name] (accepts open risks)
```

---

## Common Vulnerabilities to Watch For

- **OWASP Top 10:** SQL injection, XSS, CSRF, insecure deserialization, broken auth
- **Credential exposure:** Secrets in logs, hardcoded, version control, error messages
- **Insufficient authorization:** Users can access others' data, escalate privileges
- **Missing encryption:** Passwords, PII, or API keys in plaintext
- **Rate limiting:** No protection against brute force or DoS
- **Dependency vulnerabilities:** Outdated libraries with known CVEs

---

## Integration with Architecture Design

**architecture-design.md** → "here's how we build it"  
**threat-modeling.md** → "here's what we're defending against"

Threat modeling should precede or parallel architecture design.

---

## Success Criteria

✅ All critical & high-risk threats have mitigations  
✅ Mitigations are designed before code is written  
✅ Open/accepted risks are documented with stakeholder approval  
✅ Threats can be verified with tests  
✅ Defense-in-depth (multiple layers for critical threats)
