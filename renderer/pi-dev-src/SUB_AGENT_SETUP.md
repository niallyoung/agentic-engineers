# Pi Sub-Agent Support Setup Guide

## ✅ Configuration Complete

Your Pi installation at `~/.pi/agent/` is now configured for sub-agent orchestration with **9 specialized agent roles**.

### Files Created/Modified

1. **`/Users/niall/.pi/agent/pi.yml`** - Full sub-agent configuration
2. **`/Users/niall/.pi/agent/settings.json`** - Updated with extensions, packages, skills

---

## Available Sub-Agents

| Agent | Model | Best For | Scope |
|-------|-------|----------|-------|
| **Engineer** | Haiku | Feature implementation, bug fixes | Single file/module |
| **Senior Engineer** | Sonnet | Complex design, debugging | Multi-service, logic |
| **Lead Engineer** | Sonnet | Code review, quality gates | Validation, review |
| **Security Engineer** | Sonnet | Vulnerability analysis, compliance | Security decisions |
| **Principal Engineer** | Opus | Architecture, strategy | Organization-wide |
| **Quality Engineer** | Sonnet | Testing strategy, coverage | Test decisions |
| **Model Engineer** | Sonnet | Token optimization, cost analysis | Performance, budget |
| **Spec Engineer** | Sonnet | Spec compliance, drift detection | Validation |
| **Healing Engineer** | Sonnet | System debugging, health | Issue investigation |

---

## How to Delegate Tasks

### Pattern: Full Delegation

```
Agent: [Engineer Role]

Task: [Clear task description]

Context:
- Problem: [Background]
- Scope: [In/out of scope]
- Files: [Relevant locations]

Requirements:
1. [Requirement 1]
2. [Requirement 2]

Success Criteria:
- [Verifiable metric]
- [Verifiable metric]

Plan:
1. [Step 1]
2. [Step 2]

Please HANDBACK with:
- What was accomplished
- Metrics (tokens, time, quality)
- Any blockers
```

### Example: Engineer Delegation

```
Agent: Engineer

Task: Fix null pointer exception in auth service

Context:
- Problem: Users getting 500 error when logging in
- Files: src/auth/login.ts, src/auth/session.ts
- Tests: tests/auth/login.test.ts

Requirements:
1. Fix the NullPointerException
2. Add null check before line 45 in login.ts
3. Test passes

Success Criteria:
- No more 500 errors on login
- All tests pass
- No regressions

Please HANDBACK with:
- What was fixed
- Tests passed?
- Any observations
```

---

## Automatic Task Routing

The system automatically routes tasks based on priority:

1. **Security-scoped?** → **Security Engineer**
2. **Cross-service architecture?** → **Principal Engineer**
3. **Code review/validation?** → **Lead Engineer**
4. **Complex/unscoped?** → **Senior Engineer** (design) → **Engineer** (execution)
5. **Testing strategy?** → **Quality Engineer**
6. **Cost/optimization?** → **Model Engineer**
7. **Debugging/health?** → **Healing Engineer**
8. **Spec validation?** → **Spec Engineer**
9. **Default** → **Engineer** (with context)

---

## Collecting Metrics

After each HANDBACK, metrics are automatically collected:

- ✅ **Tokens used** (for cost analysis)
- ✅ **Time spent** (for efficiency tracking)
- ✅ **Quality score** (for output validation)
- ✅ **Completion status** (pass/fail/blockers)

These feed into cost-quality optimization decisions.

---

## Quality Gates

Before marking tasks complete, verify:

- ✅ Tests pass (run linters, builds, tests)
- ✅ Changes verified (fix actually works)
- ✅ No regressions (existing behavior unchanged)
- ✅ Documentation updated (if applicable)

---

## Token Budget & Cost Optimization

**Total Budget**: 200,000 tokens

**Model Allocation**:
- **Haiku** (fast/cheap): Simple tasks, routine work
- **Sonnet** (standard): Complex tasks, architecture, code review
- **Opus** (premium): Critical decisions, expert analysis

**Optimization Strategy**: Quality-first (maintain high quality, monitor costs)

---

## Verification

To verify configuration is working:

```bash
cat /Users/niall/.pi/agent/settings.json
cat /Users/niall/.pi/agent/pi.yml
```

Expected output:
- `extensions`: `["agent-orchestrator", "specialized-agents"]`
- `packages`: `["orchestration-framework"]`
- `skills`: All 5 skills listed
- `pi.yml`: Full agent definitions

---

## Next Steps

1. **Start delegating tasks** using the DELEGATE pattern above
2. **Monitor token usage** via metrics collection
3. **Optimize agent selection** based on task type
4. **Collect learnings** from each HANDBACK
5. **Run A/B tests** on agent configurations as needed

---

## References

- **System Prompt**: `/Users/niall/.pi/agent/SYSTEM.md`
- **Agent Roles**: `/Users/niall/.pi/agent/AGENTS.md`
- **Configuration**: `/Users/niall/.pi/agent/pi.yml`
- **Settings**: `/Users/niall/.pi/agent/settings.json`
