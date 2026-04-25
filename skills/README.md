# Skills — 38 Specialized Capabilities

**Domain-organized skills with role-as-container pattern. Skills exist once in domain directories; roles reference the skills they use.**

Total: 38 skills across 9 domain categories, referenced by 8 execution roles + 1 coordination role + shared utilities.

## Directory Structure

```
skills/
├── shared/               [4 skills: git, GitHub CLI, CDK, SigV4]
├── patterns/             [8 skills: TDD, Lambda, Makefile, CDK, API resilience, etc.]
├── orchestration/        [9 skills: task routing, metrics, model coordination, TODO management]
├── optimization/         [8 skills: cost analysis, model selection, A/B testing, automation]
├── review/               [3 skills: code review, quality analysis, quorum voting]
├── testing/              [1 skill: Playwright E2E testing (parts for Engineer + QE)]
├── monitoring/           [1 skill: local CI pipeline]
├── security/             [3 skills: threat modeling, vulnerability assessment, architecture review]
├── architecture/         [3 skills: design patterns, ADRs, tradeoff analysis]
└── roles/                [8 role container files: orchestrator.md, engineer.md, etc.]
```

## How to Use

### When assigned a task:

1. **Identify your role** from `../orchestration/AGENTS.md`
2. **Read your role container file** from `roles/{your-role}.md` (lists which skills you use)
3. **Load the domain-organized skills** referenced in your role file
4. **Reference during implementation**

### Example: Engineer working on lambda implementation

Your role file (`roles/engineer.md`) lists:
```
- patterns/implementation-coding.md      ← TDD workflow
- patterns/lambda-handler.md             ← Lambda scaffolding
- monitoring/local-ci-skill.md           ← Local testing
- patterns/makefile.md                   ← Build patterns
```

Load these files from their domain directories.

### Example: Quality Engineer reviewing code

Your role file (`roles/quality-engineer.md`) lists:
```
- review/code-quality-analysis.md        ← Analysis methodology
- review/quorum-qe.md                    ← Voting process
- testing/playwright-testing.md          ← E2E testing (Part 2: QE focus)
- review/overview.md                     ← Role context
```

Load these files from their domain directories.

## Role Container Files

Each role has a single container file in `roles/`:

| Role | File | Skills Count |
|------|------|--------------|
| **Orchestrator** | `roles/orchestrator.md` | 11 skills from orchestration/ + optimization/ + monitoring/ + shared/ |
| **Engineer** | `roles/engineer.md` | 5 skills from patterns/ + monitoring/ + testing/ + shared/ |
| **Senior Engineer** | `roles/senior-engineer.md` | 9 skills from patterns/ + architecture/ + shared/ |
| **Lead Engineer** | `roles/lead-engineer.md` | 7 skills from review/ + orchestration/ + shared/ |
| **Principal Engineer** | `roles/principal-engineer.md` | 6 skills from architecture/ + orchestration/ + shared/ |
| **Security Engineer** | `roles/security-engineer.md` | 6 skills from security/ + orchestration/ + architecture/ |
| **Quality Engineer** | `roles/quality-engineer.md` | 7 skills from review/ + testing/ + optimization/ + orchestration/ |
| **Model Engineer** | `roles/model-engineer.md` | 12 skills from optimization/ + orchestration/ + monitoring/ |

## Shared Skills (used by multiple roles)

| Skill | Location | Used By | Purpose |
|-------|----------|---------|---------|
| `git-workflow.md` | shared/ | All roles | Git best practices and workflow standards |
| `github-cli.md` | shared/ | Orchestrator, Engineer | GitHub CLI operations for automation |
| `cdk-stack.md` | shared/ | Engineer, Senior Engineer | CDK patterns for infrastructure |
| `sigv4-client.md` | shared/ | Senior Engineer, Engineer | IAM SigV4 signing for inter-service calls |

## Skill Template Structure

Each skill follows this structure:
- **What this covers:** Clear scope and capabilities
- **When to use:** Situations where this skill applies
- **Key patterns:** Patterns and best practices
- **Validation checklist:** How to verify you've applied it correctly
- **Common pitfalls:** What to avoid
- **Examples:** Real code examples from ERS platform

## Keeping Skills Updated

Skills are based on production code patterns from ERS platform. Update when:
- New architectural patterns prove successful
- Language/framework best practices change
- Cost optimization strategies improve
- Security patterns need strengthening

See `../guides/IMPLEMENTATION_COMPLETE.md` for versioning notes.

## See Also

- `../MANIFEST.md` — Complete file listing of entire system (discovery tool)
- `../guides/INDEX.md` — Complete file catalog and quick links
- `../orchestration/AGENTS.md` — Role definitions and skill assignments
- `../guides/CLAUDE.md` — Team context and integration
