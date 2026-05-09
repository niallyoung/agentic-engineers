# Review — Code Review & Quality Assessment

**Skills for verifying code quality, conducting reviews, and making quality decisions.**

Used by roles that verify code before acceptance or publication.

## Skills in This Directory

| Skill | Used By | Purpose |
|-------|---------|---------|
| **code-review.md** | Lead Engineer, Senior Engineer | Code review standards and verification checklist |
| **code-quality-analysis.md** | Quality Engineer | Structured code quality assessment methodology |
| **quorum-qe.md** | Quality Engineer | Quorum voting process (1/3/5 QE verification) |
| **security-architecture-review.md** | Security Engineer, QE | Security design review checklist |

## When to Use

- **Reviewing code** — Lead Engineer uses code-review.md
- **Assessing quality** — Quality Engineer uses code-quality-analysis.md
- **Voting on acceptance** — Quality Engineer uses quorum-qe.md for multi-reviewer process
- **Security review** — Security Engineer uses security-architecture-review.md

## Quality Gates

These skills directly support orchestration/QUALITY.md:
- Tier 1: code-quality-analysis.md checklist
- Tier 2: code-review.md and security-architecture-review.md
- Tier 3: quorum-qe.md for critical decisions

## See Also

- `../orchestration/` — Task routing and handoff
- `../roles/` — Role definitions and review responsibilities
