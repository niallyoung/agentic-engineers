# OpenCode Installation Guide

Install agentic-engineers agents and skills into OpenCode for seamless AI agent orchestration.

This guide covers the **managed install** via `make install-opencode`, which renders a lockdown configuration (`opencode.json`), global rules (`AGENTS.md`), 8 specialized agents, and 14 reusable skills into `~/.config/opencode/` (the XDG-canonical OpenCode config directory).

## Quick Start

```bash
# Install agents & skills to ~/.config/opencode/
make install-opencode

# Verify installation
make status-opencode

# Full validation (status + JSON schema check)
make validate-opencode

# Uninstall (removes agentic-engineers configs only)
make uninstall-opencode
```

If you have a legacy install from the old Python renderer, see [Migrating from a Legacy Install](#migrating-from-a-legacy-install) below.

## What Gets Installed

### 1. opencode.json — Managed Lockdown Config

A minimal, locked-down OpenCode configuration that:
- **Enables compaction** with `reserved: 30000` tokens (vs. default 20000) to reduce mid-task surprises
- **Sets global permissions** (read, edit, bash, task, glob, grep, webfetch all allowed)
- **References AGENTS.md** as the instructions entry-point
- **Includes a sentinel field** (`_managed_by`) to detect foreign edits; renderer refuses to overwrite non-managed files

**Actual file (installed at `~/.config/opencode/opencode.json`):**

```json
{
  "_managed_by": "agentic-engineers renderer/scripts/render-opencode.sh — do not edit; will be overwritten on re-install",
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["AGENTS.md"],
  "compaction": {
    "auto": true,
    "reserved": 30000
  },
  "permission": {
    "read": "allow",
    "edit": "allow",
    "bash": "allow",
    "task": "allow",
    "glob": "allow",
    "grep": "allow",
    "webfetch": "allow"
  }
}
```

**Compaction behavior:** When total tokens used ≥ (context limit - 30000), OpenCode automatically prunes older messages. The TUI signals when compaction occurs. Skill tool outputs are `PRUNE_PROTECTED` (survive compaction), so you can call skills aggressively without fear of losing their results.

### 2. AGENTS.md — Global Rules Entry-Point

A concise, user-friendly guide to the framework's mandatory constraints and queue-based routing model. Installed at `~/.config/opencode/AGENTS.md`.

**Key features:**
- **HTML-comment sentinel** on line 1 (`<!-- managed by agentic-engineers render-opencode.sh`) enables safe re-render detection
- **User override pattern:** If you want to customize rules, create `~/.config/opencode/AGENTS.md.local` (NOT created by renderer; survives re-installs). OpenCode loads it after AGENTS.md automatically.
- **Content:** Queue-based routing rules, mandatory constraints, role-specific rules, and links to full docs (HANDOFF.md, SKILLS.md, etc.)

### 3. agents/ — 8 Specialized Agents

All agents are configured as **subagents** with full permissions. Model IDs use the `github-copilot/` provider (verified against your OpenCode registry via `opencode models`).

| Agent | Model | Effort | Temperature | Use Case |
|-------|-------|--------|-------------|----------|
| **orchestrator** | `github-copilot/claude-haiku-4.5` | low | 0.3 | Central coordinator; task routing and queue management |
| **engineer** | `github-copilot/claude-haiku-4.5` | high | 0.5 | Execute well-scoped tasks with pre-written plans |
| **senior-engineer** | `github-copilot/claude-sonnet-4.6` | high | 0.5 | Complex coding & root-cause diagnosis |
| **lead-engineer** | `github-copilot/claude-sonnet-4.6` | high | 0.5 | Code review & quality gate verification |
| **quality-engineer** | `github-copilot/claude-sonnet-4.6` | medium | 0.3 | Post-implementation quality checks |
| **principal-engineer** | `github-copilot/claude-opus-4.7` | high | 0.5 | Cross-service architecture & design |
| **security-engineer** | `github-copilot/claude-opus-4.7` | max | 0.5 | Security analysis & threat modeling |
| **model-engineer** | `github-copilot/claude-sonnet-4.6` | high | 0.5 | Cost optimization via feedback analysis |

**Agent manifest:** A sidecar file `.agentic-engine{service-name}` in `~/.config/opencode/agents/` tracks which agent files are managed by the renderer. Uninstall removes only marked files.

**Agent config format (example: orchestrator.md):**

```yaml
---
description: "All entry points; routing decisions; task management; metrics collection; model recommendations"
mode: subagent
model: github-copilot/claude-haiku-4.5
temperature: 0.3
permission:
  read: allow
  edit: allow
  bash: allow
  task: allow
  glob: allow
  grep: allow
  webfetch: allow
---

# Orchestrator Agent

[Agent body with responsibilities, integration notes, and usage guidance...]
```

### 4. skills/ — 14 Reusable Skills

Skills are flat (no domain grouping in the new install). Each skill is a directory with a `SKILL.md` file.

**Installed skills (14 total):**

1. **ab-testing** — Experiment orchestration with traffic allocation and Welch's t-test
2. **agent-creator** — Scaffold new SPEC-compliant agents
3. **consistency-checker** — Validate protocol queue integrity
4. **metrics-etl** — Aggregate metrics to Prometheus format
5. **model-engineer** — Cost-quality optimization analysis
6. **protocol-validator** — Runtime DELEGATE/HANDBACK validation
7. **queue-management** — Atomic queue operations with cycle detection
8. **repo-init** — Initialize repos with agentic-engineers framework
9. **skill-creator** — Create new skills per agentskills.io spec
10. **spec-management** — SPEC.md change protection with audit trail
11. **spec-validator** — Compliance validation against SPEC.md
12. **tokenadvisor** — Daily metrics analysis and cost optimization
13. **usage-tracking** — Real-time token usage capture and forecasting
14. **voice-notify** — Voice alerts for lifecycle events

**Skill marker files:** Each skill directory has a `.agentic-engine{service-name}` marker file. Uninstall removes only marked skills.

**Skill discovery:** Skills are automatically available via the `skill` tool in OpenCode. Use the `/skills` command to see all available skills.

## How the Renderer Works

The `renderer/scripts/render-opencode.sh` script:

1. **Parses source files:**
   - `src/agents/*-agent.md` — Agent definitions with frontmatter (model, effort, description) and body
   - `src/skills/*/SKILL.md` — Skill definitions
   - `docs/AGENTS.md` — Primary roster table (model, effort, description per role)

2. **Hybrid frontmatter merge:**
   - Frontmatter from `docs/AGENTS.md` (model, effort, description) drives the OpenCode config
   - Body from `src/agents/*-agent.md` is preserved as-is
   - Temperature is derived from effort level (low/medium → 0.3, high/max → 0.5)

3. **Renders to OpenCode format:**
   - Agent configs → `~/.config/opencode/agents/{name}.md` (OpenCode subagent format)
   - Skills → `~/.config/opencode/skills/{name}/SKILL.md` (flat structure, no domain grouping)
   - Config → `~/.config/opencode/opencode.json` (lockdown settings)
   - Rules → `~/.config/opencode/AGENTS.md` (global entry-point)

4. **Safety markers:**
   - Sentinel field `_managed_by` in opencode.json
   - HTML-comment sentinel on line 1 of AGENTS.md
   - `.agentic-engine{service-name}` marker files in agents/ and skills/
   - Renderer refuses to overwrite files without our markers (foreign-file detection)

**Sibling renderers:** This script mirrors the style and safety model of `render-claude.sh`, `render-copilot.sh`, and `render-pi.sh` — all share the marker-based safety pattern.

## Model Mapping

The renderer maps agentic-engineers canonical model IDs (e.g., `claude-haiku-4-5`) to OpenCode provider/model IDs (e.g., `github-copilot/claude-haiku-4.5`).

**Mapping logic (from render-opencode.sh):**

```bash
map_model_opencode() {
	case "$1" in
		claude-haiku-4-5|claude-haiku-4.5)   echo "github-copilot/claude-haiku-4.5" ;;
		claude-sonnet-4-6|claude-sonnet-4.6) echo "github-copilot/claude-sonnet-4.6" ;;
		claude-opus-4-7|claude-opus-4.7)     echo "github-copilot/claude-opus-4.7" ;;
		claude-opus-4-6|claude-opus-4.6)     echo "github-copilot/claude-opus-4.7" ;;  # closest available
		*) echo "" ;;
	esac
}
```

**Why `github-copilot/`?** This install uses the GitHub Copilot provider (the only Claude provider currently in this user's registry per `opencode models`). Users with the `anthropic/` provider configured would want different IDs (e.g., `anthropic/claude-haiku-4-5` with dashed versions).

**Future enhancement:** Auto-detect available providers from `opencode models` output at install time and pick the best match. For now, the provider is hardcoded to `github-copilot/`.

## Compaction Behavior

OpenCode's compaction system automatically prunes older messages when token usage approaches the context limit.

**Settings (in opencode.json):**
- `compaction.auto: true` — Enable automatic pruning
- `compaction.reserved: 30000` — Reserve 30,000 tokens as headroom (vs. upstream default of 20,000)

**Why 30,000?** Tool outputs (bash, task, etc.) are not `PRUNE_PROTECTED` by default, so they can be pruned mid-task. Skill outputs ARE `PRUNE_PROTECTED`, so they survive. The larger reserve reduces surprises when compaction triggers during heavy tool use.

**Visibility:** The OpenCode TUI signals when compaction occurs, so you retain visibility into the process.

**Best practice:** Call skills aggressively (their outputs are protected). For long-running tasks, monitor the TUI for compaction signals.

## Foreign-File Safety

The renderer uses a marker-based system to detect and protect against foreign (non-managed) files.

**Markers:**

1. **opencode.json:** Sentinel field `_managed_by` with value starting with `"agentic-engineers renderer/scripts/render-opencode.sh"`
2. **AGENTS.md:** HTML-comment sentinel on line 1: `<!-- managed by agentic-engineers render-opencode.sh`
3. **agents/:** Sidecar manifest file `.agentic-engine{service-name}` listing managed agent names
4. **skills/:** Marker file `.agentic-engine{service-name}` in each skill directory

**Behavior:**
- If a file exists WITHOUT our marker, the renderer skips it and warns: `⚠️  skipping {file} — foreign at {path}`
- If a file exists WITH our marker, the renderer overwrites it (safe re-render)
- Uninstall removes only marker-tagged files; foreign files are left alone

**Example:** If you manually create `~/.config/opencode/agents/my-custom-agent.md` (no marker), it survives both install and uninstall. If you later want to remove it, delete it manually.

## Verification

### Status Check

```bash
make status-opencode
```

**Sample output:**

```
  ✅ opencode.json
  ✅ AGENTS.md
  ✅ skill ab-testing
  ✅ skill agent-creator
  ... (12 more skills)
  skills: 14 ok / 0 drift / 0 missing / 0 foreign
  ✅ agent engineer
  ✅ agent lead-engineer
  ... (6 more agents)
  agents: 8 ok / 0 missing / 0 foreign
```

### Full Validation

```bash
make validate-opencode
```

Runs status check plus JSON schema validation on opencode.json. Success looks like:

```
🔍 Validating OpenCode install at ~/.config/opencode/...
  ✅ opencode.json
  ✅ AGENTS.md
  ... (all files ok)
  ✅ opencode.json is valid JSON
  ✅ OpenCode validation complete
```

## Migrating from a Legacy Install

If you have an old install from the Python renderer or a hand-edited install, follow this pattern:

1. **Backup the old install:**
   ```bash
   mv ~/.config/opencode/ ~/.config/opencode.backup-$(date +%Y%m%d-%H%M%S)/
   ```

2. **Install the new managed version:**
   ```bash
   make install-opencode
   ```

3. **Verify:**
   ```bash
   make status-opencode
   ```

4. **If you had custom agents or skills**, restore them from backup:
   ```bash
   cp ~/.config/opencode.backup-*/agents/my-custom-agent.md ~/.config/opencode/agents/
   cp -r ~/.config/opencode.backup-*/skills/my-domain/ ~/.config/opencode/skills/
   ```

**Why not just uninstall the old one?** The old install may not have marker files, so `uninstall-opencode` won't recognize it as managed. Use `uninstall-opencode-legacy` as a fallback if needed:

```bash
make uninstall-opencode-legacy
```

This removes files matching the old renderer's patterns, but use with caution — it may remove foreign files if naming overlaps.

## Troubleshooting

### ProviderModelNotFoundError when invoking agents

**Symptom:** OpenCode error: `ProviderModelNotFoundError: Model 'github-copilot/claude-haiku-4.5' not found`

**Cause:** Model ID doesn't match your OpenCode registry.

**Fix:**
1. Check available models: `opencode models`
2. If you see `anthropic/claude-*` models instead of `github-copilot/claude-*`, you have the Anthropic provider configured
3. Reinstall with a custom provider mapping (requires editing render-opencode.sh or waiting for auto-detection feature)

### Foreign file warnings during install

**Symptom:** Install output shows `⚠️  skipping {file} — foreign at {path}`

**Cause:** A file exists at the target path without our marker.

**Fix:**
- If it's your custom file, leave it alone (it will survive install and uninstall)
- If you want the managed version instead, move or delete the custom file, then reinstall:
  ```bash
  rm ~/.config/opencode/agents/my-custom-agent.md
  make install-opencode
  ```

### Skills don't appear in OpenCode

**Symptom:** `/skills` command doesn't list agentic-engineers skills

**Cause:** Installation incomplete or OpenCode needs restart

**Fix:**
1. Verify installation: `make status-opencode`
2. Check skill files exist: `ls ~/.config/opencode/skills/`
3. Restart OpenCode to refresh discovery
4. If still missing, validate: `make validate-opencode`

### Re-render needed after source changes

**Symptom:** You edited `src/agents/*-agent.md` or `docs/AGENTS.md` but changes don't appear in OpenCode

**Cause:** Renderer only runs on `make install-opencode`

**Fix:** Reinstall (idempotent):
```bash
make install-opencode
```

## Update Log

- **2026-05-16:** Rewrote docs/OPENCODE-INSTALL.md to reflect new managed install. Replaced Python renderer with bash render-opencode.sh; added managed opencode.json + AGENTS.md; fixed model ID provider (github-copilot vs anthropic); 14 skills (was 10); marker-based safe install/uninstall; sibling-style with render-claude/copilot/pi. Compaction reserved bumped to 30000 (was default 20000).

## See Also

- [AGENTS.md](./AGENTS.md) — Complete agent orchestration documentation
- [SKILLS.md](./SKILLS.md) — Full skill definitions and workflows
- [HANDOFF.md](./HANDOFF.md) — DELEGATE/HANDBACK protocol specification
- [OpenCode Agents Documentation](https://opencode.ai/docs/agents/)
- [OpenCode Skills Documentation](https://opencode.ai/docs/skills/)
- [OpenCode Config Documentation](https://opencode.ai/docs/config/)
