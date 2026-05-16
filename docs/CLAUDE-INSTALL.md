# Claude Code Installation Guide

Install agentic-engineers agents and skills into Claude Code for seamless AI agent orchestration.

This guide covers the **managed install** via `make install-claude`, which renders 8 specialized agents and 14 reusable skills into `~/.claude/` (the Claude Code global config directory).

**Last Updated:** 2026-05-16

## Quick Start

```bash
# 1. Install agents & skills to ~/.claude/
make install-claude

# 2. Verify installation
make status

# 3. Uninstall (removes agentic-engineers configs only)
make uninstall-claude
```

> **Note:** There is no dedicated `make status-claude` — use `make status` which checks all 4 harnesses (copilot, claude, pi, opencode) and includes the `~/.claude/` section.

If you have a legacy install without marker files, see [Migrating from a Legacy Install](#migrating-from-a-legacy-install) below.

## What Gets Installed

### 1. agents/ — 8 Specialized Agents

All agents are installed as Claude Code subagents in `~/.claude/agents/`. Model IDs use short tier names (`haiku`, `sonnet`, `opus`) which Claude Code resolves to the latest available version of each tier automatically.

| Agent | Model Tier | Effort | Use Case |
|-------|-----------|--------|----------|
| **orchestrator** | `haiku` | low | Central coordinator; task routing and queue management |
| **engineer** | `haiku` | high | Execute well-scoped tasks with pre-written plans |
| **senior-engineer** | `sonnet` | high | Complex coding & root-cause diagnosis |
| **lead-engineer** | `sonnet` | high | Code review & quality gate verification |
| **quality-engineer** | `sonnet` | medium | Post-implementation quality checks |
| **principal-engineer** | `opus` | high | Cross-service architecture & design |
| **security-engineer** | `opus` | max | Security analysis & threat modeling |
| **model-engineer** | `sonnet` | high | Cost optimization via feedback analysis |

**Agent manifest:** A sidecar file `.agentic-engine{service-name}` in `~/.claude/agents/` tracks which agent files are managed by the renderer. Uninstall removes only marked files.

**Agent config format (example: orchestrator.md):**

```yaml
---
name: orchestrator
description: "All entry points; routing decisions; task management; metrics collection; model recommendations"
model: haiku
---

# Orchestrator Agent

[Agent body with responsibilities, integration notes, and usage guidance...]
```

### 2. skills/ — 14 Reusable Skills

Skills are installed in `~/.claude/skills/`. Each skill is a directory with a `SKILL.md` file.

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

## How the Renderer Works

The `renderer/scripts/render-claude.sh` script:

1. **Parses source files:**
   - `src/agents/*-agent.md` — Agent definitions with frontmatter (model, description) and body
   - `src/skills/*/SKILL.md` — Skill definitions

2. **Hybrid frontmatter merge:**
   - Description extracted from source frontmatter (falls back to first non-empty body line)
   - Model extracted from frontmatter or body `Model:` line, then mapped to tier name
   - Writes Claude Code agent format with `name`, `description`, `model` fields

3. **Renders to Claude Code format:**
   - Agent configs → `~/.claude/agents/{name}.md`
   - Skills → `~/.claude/skills/{name}/SKILL.md`

4. **Safety markers:**
   - `.agentic-engine{service-name}` marker files in agents/ and skills/
   - Renderer refuses to overwrite files without our markers (foreign-file detection)

**Sibling renderers:** This script mirrors the safety model of `render-opencode.sh`, `render-copilot.sh`, and `render-pi.sh` — all share the marker-based safety pattern.

## Model ID Mapping Strategy

Claude Code accepts short tier names rather than fully-qualified provider/model IDs. This is the key difference from the OpenCode harness.

**Mapping logic (from render-claude.sh):**

```bash
map_model() {
    case "$1" in
        *haiku*)  echo "haiku" ;;
        *sonnet*) echo "sonnet" ;;
        *opus*)   echo "opus" ;;
        *)        echo "" ;;
    esac
}
```

**Why tier names instead of version-specific IDs?**

Claude Code resolves `haiku`, `sonnet`, and `opus` to the latest available version of each tier automatically. This approach has deliberate tradeoffs:

| Aspect | Tier Names (`haiku`, `sonnet`, `opus`) | Version-Specific (`claude-sonnet-4-6`) |
|--------|----------------------------------------|----------------------------------------|
| **Maintenance** | Zero — Claude Code auto-updates | Manual update needed per release |
| **Precision** | Low — Anthropic controls exact version | High — pinned to specific version |
| **Stability** | Lower — behavior can change on Anthropic's release schedule | Higher — deterministic behavior |
| **Future-proof** | Yes — survives model version bumps | No — IDs become stale |

**Practical implications:**
- All `claude-sonnet-*` variants (4-5, 4-6, 4-7) map to `sonnet` — no version distinction
- Claude Code controls which exact model version runs per tier
- If Anthropic releases `claude-haiku-5`, the `haiku` tier name picks it up automatically
- If Claude Code requires fully-qualified IDs in a future version, the `map_model()` function will need updating

**Contrast with OpenCode:** The OpenCode harness uses fully-qualified `github-copilot/claude-haiku-4.5` style IDs for precise version control. Claude Code's tier-name approach is simpler but less precise. See [OPENCODE-INSTALL.md](./OPENCODE-INSTALL.md) for the OpenCode model mapping.

## Usage Examples

### Invoking Agents

Once installed, reference agents using `@agent-name` syntax in Claude Code:

```
# Route a task through the orchestrator (recommended entry point)
@orchestrator Route this task to the appropriate specialist

# Delegate directly to a specialist
@engineer Implement the feature described in DELEGATE.yaml
@senior-engineer Debug this complex issue: [description]
@lead-engineer Review this PR for correctness and safety
@security-engineer Review this authentication code for vulnerabilities
@principal-engineer Design the cross-service architecture for [feature]
```

Or use the `/agents` command in Claude Code to see all available agents.

### DELEGATE/HANDBACK Workflow

The recommended pattern is to route all work through the orchestrator, which creates structured DELEGATE blocks and routes to specialists:

```
@orchestrator I need to fix a bug in lambda/api/main.go where token expiry
isn't handling clock skew. Please route this to the appropriate specialist.
```

The orchestrator will:
1. Assess the task (complexity, type, security scope)
2. Create a DELEGATE block with plan, scope, and success criteria
3. Route to the appropriate agent (Senior Engineer for diagnosis, Engineer for implementation)
4. Collect the HANDBACK and verify quality

### Loading Skills

Skills are available via the skill tool in Claude Code. Reference them by name:

```
Load the queue-management skill to handle this DELEGATE lifecycle operation.
Load the spec-validator skill to check this implementation against SPEC.md.
```

### Direct Script Invocation

```bash
# Install
renderer/scripts/render-claude.sh REPO_ROOT ~/.claude

# Status check
renderer/scripts/render-claude.sh REPO_ROOT ~/.claude --status

# Uninstall
renderer/scripts/render-claude.sh REPO_ROOT ~/.claude --uninstall
```

## Foreign-File Safety

The renderer uses a marker-based system to detect and protect against foreign (non-managed) files.

**Markers:**
1. **agents/:** Sidecar manifest file `.agentic-engine{service-name}` listing managed agent names
2. **skills/:** Marker file `.agentic-engine{service-name}` in each skill directory

**Behavior:**
- If a file exists WITHOUT our marker, the renderer skips it and warns: `⚠️  skipping {file} — foreign at {path}`
- If a file exists WITH our marker, the renderer overwrites it (safe re-render)
- Uninstall removes only marker-tagged files; foreign files are left alone

**Example:** If you manually create `~/.claude/agents/my-custom-agent.md` (no marker), it survives both install and uninstall. If you later want to remove it, delete it manually.

## Verification

### Status Check

```bash
make status
```

**Sample output (Claude Code section):**

```
📋 Installation status for ~/.claude/:
  ✅ skill ab-testing
  ✅ skill agent-creator
  ... (12 more skills)
  skills: 14 ok / 0 drift / 0 missing / 0 foreign
  ✅ agent engineer
  ✅ agent lead-engineer
  ... (6 more agents)
  agents: 8 ok / 0 missing / 0 foreign
```

### Manual Verification

```bash
# List installed agents
ls ~/.claude/agents/

# List installed skills
ls ~/.claude/skills/

# Check a specific agent
cat ~/.claude/agents/orchestrator.md
```

## Migrating from a Legacy Install

If you have an old install without marker files:

1. **Backup the old install:**
   ```bash
   mv ~/.claude/ ~/.claude.backup-$(date +%Y%m%d-%H%M%S)/
   ```

2. **Install the new managed version:**
   ```bash
   make install-claude
   ```

3. **Verify:**
   ```bash
   make status
   ```

4. **If you had custom agents or skills**, restore them from backup:
   ```bash
   cp ~/.claude.backup-*/agents/my-custom-agent.md ~/.claude/agents/
   cp -r ~/.claude.backup-*/skills/my-domain/ ~/.claude/skills/
   ```

**Why not just uninstall the old one?** The old install may not have marker files, so `uninstall-claude` won't recognize it as managed. In that case, back it up and remove it manually:

```bash
mv ~/.claude ~/.claude.backup-$(date -u +%Y%m%dT%H%M%SZ)
make install-claude
```

This preserves your old install for inspection while letting the renderer write a clean managed tree.

## Known Limitations

1. **Simplified model mapping** — Tier names only (`haiku`, `sonnet`, `opus`); version-specific model IDs not preserved. All `claude-sonnet-*` variants map to `sonnet`. See [Model ID Mapping Strategy](#model-id-mapping-strategy) for rationale.

2. **No config file** — Claude Code uses `CLAUDE.md` for instructions (not a JSON config like OpenCode's `opencode.json`). The renderer does not write a `CLAUDE.md` — use the standard Claude Code pattern for project-level instructions.

3. **No global rules file** — Unlike the OpenCode harness which writes a managed `AGENTS.md`, the Claude Code harness does not write a global rules file. Use `CLAUDE.md` in your project root for project-specific rules.

4. **No docs/AGENTS.md lookup** — Model and description come from source frontmatter only (`src/agents/*-agent.md`). If `docs/AGENTS.md` is updated with new model assignments, the source frontmatter must also be updated, then re-render with `make install-claude`.

5. **`rsync` dependency** — Requires `rsync` to be installed (standard on macOS/Linux).

6. **No `make status-claude`** — Unlike `make status-opencode`, there is no harness-specific status command for Claude Code. Use `make status` (multi-harness) instead.

7. **No JSON schema validation** — Unlike `make validate-opencode`, there is no equivalent `make validate-claude` since Claude Code has no JSON config to validate.

## Troubleshooting

### Agent not found when using @agent-name

**Symptom:** Claude Code doesn't recognize `@orchestrator` or other agents

**Cause:** Agents not installed or Claude Code needs restart

**Fix:**
1. Verify installation: `make status`
2. Check agent files exist: `ls ~/.claude/agents/`
3. Restart Claude Code to refresh agent discovery

### Foreign file warnings during install

**Symptom:** Install output shows `⚠️  skipping {file} — foreign at {path}`

**Cause:** A file exists at the target path without our marker.

**Fix:**
- If it's your custom file, leave it alone (it will survive install and uninstall)
- If you want the managed version instead, move or delete the custom file, then reinstall:
  ```bash
  rm ~/.claude/agents/my-agent.md
  make install-claude
  ```

### Skills don't appear in Claude Code

**Symptom:** Skills not available or not loading

**Cause:** Installation incomplete or Claude Code needs restart

**Fix:**
1. Verify installation: `make status`
2. Check skill files exist: `ls ~/.claude/skills/`
3. Restart Claude Code to refresh discovery
4. If still missing, check for foreign-file warnings during install

### Re-render after source changes

**Symptom:** You edited `src/agents/*-agent.md` but changes don't appear in Claude Code

**Cause:** Renderer only runs on `make install-claude`

**Fix:** Reinstall (idempotent):
```bash
make install-claude
```

### Pre-existing file blocks install (no manifest)

**Symptom:** Install output shows `⚠️  skipping agent {name} — pre-existing file (no manifest yet); move it aside and re-run`

**Cause:** An agent file exists at `~/.claude/agents/{name}.md` but there is no manifest file (first-time install on a system with pre-existing Claude Code agents).

**Fix:**
```bash
# Option A: Back up and move aside
mv ~/.claude/agents/orchestrator.md ~/.claude/agents/orchestrator.md.bak
make install-claude

# Option B: Back up the entire agents directory
mv ~/.claude/agents ~/.claude/agents.bak
make install-claude
```

## CLI Reference

```bash
# Install
make install-claude          # Install agents + skills to ~/.claude/

# Status (multi-harness — includes ~/.claude/ section)
make status                  # Check all 4 harnesses

# Uninstall
make uninstall-claude        # Remove agentic-engineers files from ~/.claude/

# Direct script invocation
renderer/scripts/render-claude.sh REPO_ROOT ~/.claude            # install
renderer/scripts/render-claude.sh REPO_ROOT ~/.claude --status   # status
renderer/scripts/render-claude.sh REPO_ROOT ~/.claude --uninstall # uninstall
```

## Maintenance

### Updating After Source Changes

When agent definitions or skills are updated in the source tree, re-render to pick up changes:

```bash
# Re-render and reinstall (idempotent — safe to run at any time)
make install-claude

# Verify the update took effect
make status
```

### Keeping Custom Agents Alongside Managed Agents

You can add custom agents to `~/.claude/agents/` alongside the managed agents. The renderer will skip any file that lacks its marker, so custom agents survive re-installs and uninstalls:

```bash
# Add a custom agent (no marker = not managed = survives install/uninstall)
cat > ~/.claude/agents/my-custom-agent.md << 'EOF'
---
name: my-custom-agent
description: "My custom agent for project X"
model: sonnet
---

# My Custom Agent
...
EOF

# Managed agents are updated; custom agent is untouched
make install-claude
```

### Checking for Drift

If you suspect installed agents have drifted from source (e.g., manual edits to `~/.claude/agents/`):

```bash
# Status shows drift for skills (diff-based); agents show ok/missing/foreign
make status

# To reset a drifted agent back to source, reinstall
make install-claude
```

> **Note:** The `--status` mode detects drift for skills (via `diff -rq`) but not for individual agent files (agents are tracked by manifest presence only, not content diff). To reset agent content, run `make install-claude`.

### Uninstalling and Reinstalling

```bash
# Clean uninstall (managed files only)
make uninstall-claude

# Reinstall from scratch
make install-claude
make status
```

## Update Log

- **2026-05-16:** Rewrote `docs/CLAUDE-INSTALL.md` to mirror `docs/OPENCODE-INSTALL.md` quality. Added Maintenance section, expanded Usage Examples with DELEGATE/HANDBACK workflow, expanded Model ID Mapping Strategy with tier-vs-version tradeoff table, added pre-existing file troubleshooting entry, added Known Limitations items 6 and 7, corrected `make status` note (no dedicated `make status-claude`).

## See Also

- [OPENCODE-INSTALL.md](./OPENCODE-INSTALL.md) — OpenCode installation guide (managed config, fully-qualified model IDs, JSON schema validation)
- [AGENTS.md](./AGENTS.md) — Complete agent orchestration documentation
- [SKILLS.md](./SKILLS.md) — Full skill definitions and workflows
- [HANDOFF.md](./HANDOFF.md) — DELEGATE/HANDBACK protocol specification
- [Claude Code Agents Documentation](https://docs.anthropic.com/en/docs/claude-code/agents)
