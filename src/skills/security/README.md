# Security — Security-Specific Analysis

**Skills for threat modeling, vulnerability assessment, and security architecture review.**

## Skills in This Directory

| Skill | Used By | Purpose |
|-------|---------|---------|
| **threat-modeling.md** | Security Engineer | STRIDE threat modeling methodology |
| **vulnerability-assessment.md** | Security Engineer | Vulnerability testing and CVE assessment |
| **security-architecture-review.md** | Security Engineer, QE | Design review checklist for security |

## When to Use

- **Designing new service** — Security Engineer uses threat-modeling.md
- **Testing for vulnerabilities** — Security Engineer uses vulnerability-assessment.md
- **Reviewing design for security** — Security Engineer uses security-architecture-review.md
- **Quality gate verification** — QE uses security-architecture-review.md for Tier 3

## Security Methodology

All three skills use consistent approach:
1. Identify threats (STRIDE)
2. Assess severity/likelihood
3. Design mitigations
4. Verify implementation
5. Document decisions (ADR)

## Tier 3 Quality Gates

Security review is a Tier 3 gate (Principal + Security roles):
- Auth correctness (STRIDE)
- Data flow security
- Access control patterns
- Cross-service contracts
- Vulnerability assessment

## See Also

- `../review/` — Quality gate verification
- `../architecture/` — Design decision documentation
- `../patterns/` — Secure coding patterns
