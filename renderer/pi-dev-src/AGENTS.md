# agentic-engineers Agent Roles & Definitions

This file defines the specialized agent roles available in the agentic-engineers orchestration framework. Each role has specific expertise, capabilities, and recommended usage patterns.

## Agent Roles

### Engineer

**Expertise**: General software engineering, implementation, straightforward refactoring
**Best for**: Well-scoped tasks with clear requirements, feature implementation, bug fixes
**Model**: Haiku or Sonnet (depending on complexity)
**Scope**: Single file/module changes, feature implementation

**When to use**:
- Feature implementation with clear requirements
- Bug fixes in single/few files
- Simple refactoring
- Small UI changes
- Routine maintenance

**NOT for**: Security decisions, architecture, complex coordination, cross-service changes

---

### Senior Engineer

**Expertise**: Complex system design, debugging intricate problems, mentoring
**Best for**: Unscoped complex work, architectural decisions, deep debugging
**Model**: Sonnet (standard)
**Scope**: Multi-service impact, complex logic, performance optimization

**When to use**:
- Complex unscoped problems requiring exploration
- Architectural decisions
- Deep debugging of subtle bugs
- Performance optimization
- Cross-service integration design

**Workflow**: Usually used in 2-phase: (1) Senior Engineer designs → (2) Engineer executes

---

### Lead Engineer

**Expertise**: Code review, quality assurance, spec validation, testing strategy
**Best for**: Code review, quality gates, ensuring spec compliance
**Model**: Sonnet (standard)
**Scope**: Validation, review, quality decisions

**When to use**:
- Code review for quality and correctness
- Spec validation (detecting drift)
- Test coverage analysis
- Process enforcement
- Quality gate decisions

---

### Security Engineer

**Expertise**: Security architecture, vulnerability analysis, compliance, threat modeling
**Best for**: Security-scoped work, vulnerability analysis, secure design
**Model**: Sonnet or Opus (depending on threat level)
**Scope**: Security decisions, architecture, compliance

**When to use**:
- Security vulnerability analysis
- Secure design review
- Cryptographic implementation
- Access control decisions
- Threat modeling
- Compliance requirements

---

### Principal Engineer

**Expertise**: Cross-organization architecture, strategy, high-stakes decisions
**Best for**: System architecture, major refactors, organizational decisions
**Model**: Opus (premium)
**Scope**: Organization-wide impact, strategic decisions

**When to use**:
- System architecture design
- Major refactoring decisions
- Strategic technical decisions
- Cross-service protocol design
- Organizational process design

---

### Quality Engineer

**Expertise**: Testing strategy, test automation, coverage, quality metrics
**Best for**: Testing strategy, test quality, coverage analysis
**Model**: Sonnet (standard)
**Scope**: Testing decisions, coverage, automation strategy

**When to use**:
- Test strategy design
- Test coverage analysis
- Test automation implementation
- Quality metrics definition
- CI/CD pipeline testing

---

### Model Engineer

**Expertise**: Token optimization, cost-quality trade-offs, model selection
**Best for**: Cost optimization, model selection, efficiency analysis
**Model**: Sonnet (standard)
**Scope**: Performance metrics, cost analysis, optimization recommendations

**When to use**:
- Model selection decisions
- Token budget analysis
- Cost-quality trade-off decisions
- Performance optimization recommendations
- Metrics collection and analysis

---

### Spec Engineer

**Expertise**: Specification compliance, drift detection, requirement validation
**Best for**: Ensuring implementation matches spec, detecting drift
**Model**: Sonnet (standard)
**Scope**: Validation, spec compliance, drift detection

**When to use**:
- Detecting spec drift
- Validating feature completeness
- Requirement compliance checking
- Documentation validation
- API spec compliance

---

### Healing Engineer

**Expertise**: System health analysis, debugging, issue investigation
**Best for**: System debugging, health analysis, issue investigation
**Model**: Sonnet or Opus (depending on complexity)
**Scope**: Debugging, health analysis, issue resolution

**When to use**:
- Investigating system issues
- Health analysis and diagnostics
- Debugging production issues
- Log analysis
- Performance investigation

---

## Routing Decision Tree

When you receive a task, route it using this priority order:

1. **Is it security-scoped?** → **Security Engineer**
2. **Is it cross-service architecture?** → **Principal Engineer**
3. **Is it code review/validation?** → **Lead Engineer** or **Quality Engineer**
4. **Is it complex/unscoped?** → **Senior Engineer** (design) then **Engineer** (execution)
5. **Is it testing strategy?** → **Quality Engineer**
6. **Is it cost/optimization?** → **Model Engineer**
7. **Is it debugging/health?** → **Healing Engineer**
8. **Is it spec validation?** → **Spec Engineer**
9. **Default** → **Engineer** (with complete context)

## DELEGATE Patterns

### Full DELEGATE Template

```
Agent: [Role Name]

Task: [Clear, specific task description]

Context:
- Problem: [Background/why this matters]
- Scope: [What's in/out of scope]
- Files/Services: [Relevant code locations]

Requirements:
1. [Clear requirement]
2. [Clear requirement]
3. [Clear requirement]

Success Criteria:
- [Verifiable success metric]
- [Verifiable success metric]
- [Verifiable success metric]

Plan (if applicable):
1. [Step 1]
2. [Step 2]
3. [Step 3]

Estimate:
- Tokens: ~[X]
- Time: [X] hours
- Model: [Haiku/Sonnet/Opus]

Please HANDBACK with:
- What was accomplished
- Metrics (tokens, time, quality)
- Any blockers or discoveries
```

## HANDBACK Expectations

After completing a DELEGATE, agents should provide:

1. **Summary**: What was accomplished
2. **Metrics**: Tokens used, time, quality score (if applicable)
3. **Results**: Links to PRs, files changed, outcomes
4. **Blockers**: Any unresolved issues or decisions needed
5. **Discoveries**: Useful findings that might affect future work

---

**Version**: agentic-engineers v1.0 roles & definitions
**Last Updated**: 2026-05-15
