# Harness Setup Guides

Agentic Engineers supports multiple AI coding harnesses. Choose the one that fits your workflow.

## Supported Harnesses

| Harness | Description | Best For | Status |
|---------|-------------|----------|--------|
| [OpenCode](opencode.md) | Primary harness for autonomous coordination | Production use | ✅ Recommended |
| GitHub Copilot | GitHub's official CLI with CI/CD integration | GitHub workflows, team collaboration | ✅ Stable |
| Claude Code | Claude's native CLI harness | Interactive development, prototyping | ✅ Stable (see [opencode.md](opencode.md) or [codex.md](codex.md) for a template-quality per-harness setup guide) |
| [Codex](codex.md) | Codex custom agents, skills, and permission profiles | Local development, workspace-managed runs | ✅ Supported, opt-in install |

## Quick Start

### Install Default Harnesses (Recommended)

```bash
make install
```

This installs all default harnesses: OpenCode, Copilot, Claude, and Codex.

Each installer writes only to its own harness config root: `~/.config/opencode/`, `~/.copilot/`, `~/.claude/`, or `~/.codex/`.

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
| Source Agents | `claude-<family>-<major>.<minor>` (dots) | — | Canonical format in source |
| OpenCode | dotted source ID | hyphenated ID (`claude-<family>-<major>-<minor>`) | CLI requirement |
| Copilot CLI | dotted source ID | dotted source ID (pass-through) | Anthropic API format |
| Claude Code | dotted source ID | registry-pinned full ID (hyphenated minor) | Exact pin; short alias only via `AGENTIC_CLAUDE_MODEL_RENDER=alias` |
| Codex | registry family | family-based tier mapping | Codex model tiers derived from role registry family: haiku→mini (gpt-5.4-mini), sonnet→standard (gpt-5.5), opus/fable→top (gpt-5.5) |

Claude Code renders the registry-pinned full ID, not a short alias. To fall back to the
floating alias (`haiku`/`sonnet`/`opus`/`fable`) run the renderer or installer with
`AGENTIC_CLAUDE_MODEL_RENDER=alias`. OpenCode records any fallback it had to use in
`dist/opencode/model-resolution.json`. Current pins: [docs/MODELS.md](../../MODELS.md).

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

All harnesses pass through the same DELEGATE Validation and HANDBACK Validation gates
(Gates 3 and 5) before work is considered done. There is no automated multi-layer
composite-scoring formula or fixed numeric acceptance threshold — quality is assessed
by convention (self-reported `metrics.quality`, optional Quality Engineer verification,
routing by `status`). See [docs/PROTOCOL.md](../../PROTOCOL.md) and
[docs/WORKFLOW.md](../../WORKFLOW.md) § Gate 5 for the authoritative description.


## Next Steps

Choose your harness and follow the detailed setup guide:
- [OpenCode Setup](opencode.md)
- [Codex Setup](codex.md)
- GitHub Copilot and Claude Code are summarized in the top-level [README](../../../README.md).
