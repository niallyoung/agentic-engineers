# Harness Setup Guides

Agentic Engineers supports multiple AI coding harnesses. Choose the one that fits your workflow.

## Supported Harnesses

| Harness | Description | Best For | Status |
|---------|-------------|----------|--------|
| [OpenCode](opencode.md) | Primary harness for autonomous coordination | Production use, dark factory mode | ✅ Recommended |
| GitHub Copilot | GitHub's official CLI with CI/CD integration | GitHub workflows, team collaboration | ✅ Stable |
| [Claude Code](claude.md) | Claude's native IDE and code editor | Interactive development, prototyping | ✅ Stable |
| [Codex](codex.md) | Codex custom agents, skills, and permission profiles | Local development, workspace-managed runs | ✅ Supported, opt-in install |

## Quick Start

### Install Default Harnesses (Recommended)

```bash
make install
```

This runs the default harness renderers (OpenCode, Copilot, and Claude). Use `make install-codex` separately for Codex.

Each installer writes only to its own harness config root: `~/.config/opencode/`, `~/.copilot/`, `~/.claude/`, or `~/.codex/` via `make install-codex`.

### Install Claude Code (Interactive Development)

For interactive development and rapid prototyping with Claude Code IDE:

```bash
make install-claude
```

This configures Claude Code with agent definitions, skills, and the DELEGATE/HANDBACK protocol. Configuration is installed to `~/.claude/`.

### Install Specific Harness

```bash
# OpenCode (recommended for production)
make install-opencode

# GitHub Copilot
make install-copilot

# Claude Code
make install-claude

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
| Codex | `claude-opus-4.8` role tier | `gpt-5.5` / `gpt-5.4-mini` | Codex custom-agent model mapping |

### Renderer Scripts

Each harness uses a dedicated renderer script to handle these transformations:
- `renderer/scripts/render-opencode.sh` — OpenCode configuration
- `renderer/scripts/render-copilot.sh` — Copilot CLI configuration
- `renderer/scripts/render-claude.sh` — Claude Code configuration
- `renderer/scripts/render-codex.py` — Codex custom agents, config, and skills

Run `make install` for the default harness set, or use individual `make install-{harness}` targets when you need a specific harness, including `make install-codex`.

## Troubleshooting

### Common Issues by Harness

| Issue | Harness | Fix |
|-------|---------|-----|
| Model not recognized | Copilot CLI | Verify `copilot --version` is ≥2.0.0 |
| Agent not found | Claude Code | Run `make install-claude` |

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

**Status:** EVALS-001 framework in active development.

## Next Steps

Choose your harness and follow the detailed setup guide:
- [OpenCode Setup](opencode.md)
- [Codex Setup](codex.md)
- GitHub Copilot and Claude Code are summarized in the top-level [README](../../../README.md).
