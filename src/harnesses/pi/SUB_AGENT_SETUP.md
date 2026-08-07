# Pi.dev Sub-Agent Setup Guide

## Overview

This guide documents the agentic-engineers configuration for the **pi.dev** coding agent harness.
The renderer copies files from `src/harnesses/pi/` to `~/.pi/agent/` verbatim.

**Last Updated:** 2026-05-16

---

## ⚠️ Known Limitations

Before proceeding, understand these important limitations:

### 1. Sub-Agent Support is SPECULATIVE

The `pi.yml` routing rules and `settings.json` extensions/packages/skills are based on
research into the pi.dev API and are **NOT verified against the actual pi.dev runtime**.
These features may have no effect.

**What this means:**
- The `routing:` section in `pi.yml` (conditions like `"security-scoped"`) may not be recognized
- The `extensions:` and `packages:` in `settings.json` may not be recognized
- The `skills:` list in `settings.json` may not be recognized

**What IS known to work:**
- `SYSTEM.md` — pi.dev reads this as the system prompt
- `AGENTS.md` — pi.dev reads this as agent role definitions
- `settings.json` — `defaultModel`, `defaultProvider`, `theme`, `compaction` are standard settings

### 2. No Content Transformation

Unlike the OpenCode and Claude Code harnesses, the π.dev renderer does **not** transform
`src/agents/` or `src/skills/`. It copies a manually-maintained set of files verbatim.
This means:
- Source files must be manually kept in sync with `src/AGENTS.md`
- Model IDs are set directly in `settings.json` and `pi.yml`

### 3. Hardcoded Paths in This Document

This document previously contained hardcoded user paths. It now uses generic paths.
Substitute your actual home directory where `~` appears.

---

## Available Agent Roles (8 Canonical)

| Agent | Model | Effort | Best For | Scope |
|-------|-------|--------|----------|-------|
| **Orchestrator** | claude-haiku-4.5 | low | Task routing, queue management | Routing only |
| **Engineer** | claude-haiku-4.5 | high | Feature implementation, bug fixes | Single file/module |
| **Senior Engineer** | claude-sonnet-5 | high | Complex design, debugging | Multi-service, logic |
| **Lead Engineer** | claude-sonnet-5 | high | Code review, quality gates | Validation, review |
| **Quality Engineer** | claude-sonnet-5 | medium | Post-impl quality gate | Quality verification |
| **Security Engineer** | claude-fable-5 (defensive-only) | medium | Vulnerability analysis, compliance | Security only; defensive analysis only |
| **Principal Engineer** | claude-opus-5 | high | Architecture, strategy | Organization-wide |
| **Model Engineer** | claude-sonnet-5 | high | Token optimization, cost analysis | Performance, budget |

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

## Task Routing Decision Tree

Route tasks using this priority order:

1. **Security-scoped?** → **Security Engineer** (block all other routes)
2. **Cross-service architecture (>2 repos)?** → **Principal Engineer**
3. **Complex coding WITHOUT pre-written plan?** → **Senior Engineer** (to plan first)
4. **Code review/validation?** → **Lead Engineer** or **Quality Engineer**
5. **Well-planned, low-medium complexity?** → **Engineer**
6. **Cost/optimization?** → **Model Engineer**
7. **Default** → **Engineer** (with complete context)

---

## Installed Files

After running `make install-pi`, these files are installed to `~/.pi/agent/`:

| File | Purpose | Verified? |
|------|---------|-----------|
| `SYSTEM.md` | System prompt for Orchestrator | ✅ Yes |
| `AGENTS.md` | Agent role definitions | ✅ Yes |
| `settings.json` | Core settings (model, theme, compaction) | ✅ Partial |
| `pi.yml` | Sub-agent configuration | ⚠️ Speculative |
| `SUB_AGENT_SETUP.md` | This file | ✅ Yes |

---

## Verification

To verify the installation:

```bash
# Check installed files
ls -la ~/.pi/agent/

# Check settings
cat ~/.pi/agent/settings.json

# Check system prompt
head -5 ~/.pi/agent/SYSTEM.md
```

Expected output for `settings.json`:
- `defaultModel`: `"claude-sonnet-4-6"`
- `defaultProvider`: `"anthropic"`
- `compaction.enabled`: `true`

---

## Troubleshooting

### Model not found errors

If pi.dev reports a model not found:
1. Check `settings.json` `defaultModel` value
2. Verify the model ID is supported by your pi.dev subscription
3. Update `settings.json` `defaultModel` to a supported model
4. Current model IDs: `claude-haiku-4-5`, `claude-sonnet-5`, `claude-opus-5`, `claude-fable-5` (defensive-only for Security Engineer)

**Harness limitation — fable-5 on pi:** pi.dev has a single `defaultModel` and no
per-agent model selection, so the framework cannot route an individual DELEGATE
to fable-5 here. fable-5 is usable on pi only by manually setting
`settings.json` `defaultModel` for a dedicated defensive-analysis session; the
Defensive-Only Model Constraint in AGENTS.md applies in full, and the
Orchestrator's C5 gate still validates the DELEGATE regardless of harness.

### Sub-agent routing not working

The routing rules in `pi.yml` are speculative. If they don't work:
1. Use the DELEGATE pattern manually (describe the task to the appropriate agent)
2. Reference the routing decision tree above
3. The system prompt in `SYSTEM.md` guides the Orchestrator's routing behavior

### Configuration sync issues

If you update `src/AGENTS.md` in the main repo:
1. Update `src/harnesses/pi/AGENTS.md` to match
2. Update `src/harnesses/pi/SYSTEM.md` with new model IDs
3. Update `src/harnesses/pi/pi.yml` with new model IDs
4. Update `src/harnesses/pi/settings.json` with new default model
5. Run `make install-pi` to deploy changes

### Re-installing

The π.dev renderer is idempotent:
```bash
make install-pi    # install or re-install
make uninstall-pi  # remove managed files
```

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
- **Haiku** (fast/cheap): Routing, simple tasks, routine work
- **Sonnet** (standard): Complex tasks, architecture, code review, quality gates
- **Opus** (premium): Security analysis, cross-service architecture

**Optimization Strategy**: Quality-first (maintain high quality, monitor costs)

---

## References

- **System Prompt**: `~/.pi/agent/SYSTEM.md`
- **Agent Roles**: `~/.pi/agent/AGENTS.md`
- **Configuration**: `~/.pi/agent/pi.yml`
- **Settings**: `~/.pi/agent/settings.json`
- **Canonical Roles**: `src/AGENTS.md` in the agentic-engineers repo
- **Install Guide**: `renderer/PI-DEV-RENDERER.md`
