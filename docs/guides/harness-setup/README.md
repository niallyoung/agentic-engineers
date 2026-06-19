# Harness Setup Guides

Agentic Engineers supports multiple AI coding harnesses. Choose the one that fits your workflow.

## Supported Harnesses

| Harness | Description | Best For | Status |
|---------|-------------|----------|--------|
| [Codex](codex.md) | Codex custom agents, skills, and permission profiles | Local development, workspace-managed runs | ✅ Supported, opt-in install |
| [OpenCode](opencode.md) | Primary harness for autonomous coordination | Production use, dark factory mode | ✅ Recommended |
| [GitHub Copilot](copilot.md) | GitHub's official CLI with CI/CD integration | GitHub workflows, team collaboration | ✅ Stable |
| [Claude Code](claude.md) | Claude's native IDE and code editor | Interactive development, prototyping | ✅ Stable |
| [π.dev](pi-dev.md) | Experimental harness with emerging features | Early adopters, experimentation | ⚠️ Beta |

## Quick Start

### Install Default Harnesses (Recommended)

```bash
make install
```

This runs the default harness renderers (Claude, Copilot, OpenCode, and π.dev). Use `make install-codex` separately for Codex.

### Install Specific Harness

```bash
# OpenCode (recommended for production)
make install-opencode

# GitHub Copilot
make install-copilot

# Claude Code
make install-claude

# π.dev
make install-pi

# Codex
make install-codex
```

## Version Compatibility

### Model Naming Across Harnesses

Agentic Engineers uses a canonical model naming format internally (with dots), which is automatically transformed per-harness:

| Harness | Internal Format | Transformed Format | Reason |
|---------|-----------------|-------------------|--------|
| Source Agents | `claude-opus-4.8` (dots) | — | Canonical format in source |
| OpenCode | `claude-opus-4.8` | `claude-opus-4-8` (hyphens) | CLI requirement |
| Copilot CLI | `claude-opus-4.8` | `claude-opus-4.8` (pass-through) | Anthropic API format |
| Claude Code | `claude-opus-4.8` | `opus` (short alias) | Web UI simplification |
| π.dev | `claude-opus-4.8` | `claude-opus-4-8` (hyphens) | Anthropic API format |
| Codex | `claude-opus-4.8` role tier | `gpt-5.5` / `gpt-5.4-mini` | Codex custom-agent model mapping |

### Renderer Scripts

Each harness uses a dedicated renderer script to handle these transformations:
- `renderer/scripts/render-opencode.sh` — OpenCode configuration
- `renderer/scripts/render-copilot.sh` — Copilot CLI configuration
- `renderer/scripts/render-claude.sh` — Claude Code configuration
- `renderer/scripts/render-pi-dev.py` — π.dev configuration
- `renderer/scripts/render-codex.py` — Codex custom agents, config, and skills

Run `make install` for the default harness set, or use individual `make install-{harness}` targets when you need a specific harness, including `make install-codex`.

## Troubleshooting

See the [Troubleshooting Guide](../troubleshooting.md) for common issues and fixes.

### Common Issues by Harness

| Issue | Harness | Fix |
|-------|---------|-----|
| Queue directories not found | OpenCode | `mkdir -p ~/.agentic-engineers/queue/{incoming,processing,done}` |
| Model not recognized | Copilot CLI | Verify `copilot --version` is ≥2.0.0 |
| System prompt not loaded | Claude Code | Run `make install-claude` |
| Events not firing | π.dev | Check `~/.pi/agent/extensions/` for handler files |

## Quality Gates

All harnesses pass through three quality gates before deployment:

1. **DELEGATE Structure Validation** (40% weight)
   - Task ID format validation (`YYYY-MM-DD-kebab-case`)
   - Required field presence (scope, plan, success_criteria)
   - Scope clarity and completeness

2. **Task Routing Quality** (35% weight)
   - Correct agent selection via decision tree
   - Confidence scoring (≥75% required)
   - Model suitability assessment

3. **HANDBACK Validation** (25% weight)
   - Success criteria met
   - Quality score ≥ threshold
   - Metrics presence and accuracy

**Routing by Quality Score:**
- 90–100: Move to done immediately
- 80–89: Move to done with notes
- 70–79: Route to Lead Engineer for review
- 60–69: Issue rework DELEGATE (max 2 retries)
- <60: Escalate to Principal Engineer

## Continuous Evaluation Framework (EVALS-001)

Harness and model compatibility is continuously tested via the **EVALS-001 framework** (currently in development). This ensures:

- ✅ **Automated regression testing** — Nightly CI/CD job detects breaking changes
- ✅ **Model compatibility matrix** — Track which models work with which harnesses
- ✅ **Skill interoperability tests** — Validate each skill works across all harnesses
- ✅ **End-to-end delegation workflows** — Test complex scenarios (escalation, parallel work, error handling)

**Success Criteria:**
- All harness × model × skill combinations tested automatically
- Compatibility reports showing pass/fail status
- Model regressions detected immediately
- ≥95% pass rate required before production deployment

**Status:** EVALS-001 framework in active development (target completion: June 2026).  
**Reference:** See [TODO.md § Harness Compatibility & Evaluation Testing](../../../TODO.md#harness-compatibility--evaluation-testing)

## Next Steps

Choose your harness and follow its detailed setup guide:
- [OpenCode Setup](opencode.md)
- [Codex Setup](codex.md)
- [GitHub Copilot Setup](copilot.md)
- [Claude Code Setup](claude.md)
- [π.dev Setup](pi-dev.md)
