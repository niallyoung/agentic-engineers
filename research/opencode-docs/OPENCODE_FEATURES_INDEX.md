# OpenCode Features Index & Design Principles

## Core Architecture

OpenCode is an AI coding agent that operates as a terminal-based interface, desktop app, or IDE extension. It's designed around a **plugin architecture** with role-based agent routing, comprehensive permission management, and extensibility via MCP (Model Context Protocol).

### Design Intent
- **Modularity**: Agents as specialized assistants for different tasks
- **Safety**: Permission system prevents unintended actions
- **Extensibility**: MCP servers and custom tools add capabilities
- **Context Efficiency**: Automatic compaction, token preservation, and pruning
- **Workflow Integration**: Git hooks, rules (AGENTS.md), and SDLC alignment

---

## 5 Most Important OpenCode Features

### 1. **Agent Routing & Role-Based Access Control**
**What it does**: Routes work to specialized agents with different capabilities and permissions.

**Key concepts**:
- **Primary agents** (Build, Plan, Compaction, Title, Summary) — main assistants you interact with
- **Subagents** (General, Explore, Scout) — called automatically or via `@mention` for specialized tasks
- **Custom agents** — define unlimited specialized agents with custom prompts, models, and permissions

**Why it matters for agentic-engineers**:
- Enables the 8-agent DELEGATE/HANDBACK workflow
- Per-role model routing (Haiku for Engineer, Sonnet for Senior, Opus for Principal)
- Permissions enforcement at agent level (read-only agents prevent accidental changes)

**Documentation**: `/docs/agents/`

---

### 2. **Granular Permission System**
**What it does**: Controls which tools an agent can use with three levels of access (allow/ask/deny).

**Key permissions**:
- `read` — file reading (default: allow, except .env files)
- `edit` — file modifications (write, edit, patch)
- `bash` — shell commands (with pattern matching for granular control)
- `task` — subagent invocation
- `skill` — skill loading
- `external_directory` — file access outside working directory
- `doom_loop` — protection against repeated failed operations
- `webfetch`, `websearch`, `glob`, `grep`, `lsp`, `question`

**Pattern matching**:
- Wildcards: `*` (zero or more), `?` (exactly one)
- Examples: `"git *"` → allow git commands, `"rm -rf *"` → deny dangerous patterns
- Precedence: last matching rule wins

**Why it matters for agentic-engineers**:
- Enforces protocol constraints (Engineer can't push code, Security Engineer alone can approve)
- Enables role-specific capabilities
- Prevents accidental damage via pattern blocking

**Documentation**: `/docs/permissions/`

---

### 3. **MCP (Model Context Protocol) Integration**
**What it does**: Extends OpenCode with external tools via local or remote servers.

**Server types**:
- **Local**: Command-based (e.g., `npx -y my-mcp-command`)
- **Remote**: HTTP endpoints with OAuth support
- Examples: Sentry (error tracking), GitHub (PRs/issues), Jira, Context7 (doc search), Grep.app

**Why it matters for agentic-engineers**:
- Can integrate DELEGATE/HANDBACK queue as MCP server
- External tool access without modifying core OpenCode
- OAuth authentication for enterprise integration

**Documentation**: `/docs/mcp-servers/`

---

### 4. **Context Compaction & Token Efficiency**
**What it does**: Automatically compacts long conversations to preserve token budget.

**Configuration**:
- `auto` — automatically compress when context full
- `prune` — remove old tool outputs to save tokens
- `reserved` — token buffer to prevent overflow
- **Skill tool outputs are PRUNE_PROTECTED** — survive compaction

**Why it matters for agentic-engineers**:
- Long-running orchestrator sessions don't bloat token usage
- Skills (DELEGATE/HANDBACK templates, protocols) are preserved
- Enables cost-effective multi-session workflows

**Documentation**: `/docs/config#compaction`

---

### 5. **Rules System (AGENTS.md) for Project Guidance**
**What it does**: Provides custom instructions to agents via `AGENTS.md` file (like Cursor's `.cursor/rules.md`).

**Scope**:
- **Project**: `AGENTS.md` in project root (overrides global)
- **Global**: `~/.config/opencode/AGENTS.md` (applies to all sessions)
- **Claude Code compatibility**: Falls back to `CLAUDE.md` / `~/.claude/CLAUDE.md`

**Content**:
- Build, lint, test commands
- Architecture & structure
- Code standards & conventions
- Operational gotchas
- External file references (via `instructions` field in config)

**Why it matters for agentic-engineers**:
- Encodes SPEC.md constraints and protocol rules
- Shares workflow with all agents across harnesses
- Can reference external instruction files (e.g., CONTRIBUTING.md)

**Documentation**: `/docs/rules/`

---

## Feature Ecosystem

### Configuration System
**Files & Precedence** (later overrides earlier):
1. Remote config (`.well-known/opencode` endpoint)
2. Global config (`~/.config/opencode/opencode.json`)
3. Custom config (env var `OPENCODE_CONFIG`)
4. Project config (`opencode.json` in project root)
5. `.opencode/` directories (agents/, commands/, modes/, plugins/, skills/, tools/, themes/)
6. Inline config (env var `OPENCODE_CONFIG_CONTENT`)
7. Managed config (admin-enforced, `/Library/Application Support/opencode/`)
8. macOS MDM preferences (highest priority, cannot override)

**Schema validation**: `opencode.ai/config.json` and `opencode.ai/tui.json`

---

### Built-in Tools (13 types)

| Tool | Purpose | Permission | Use Case |
|------|---------|-----------|----------|
| `bash` | Shell commands | "allow" | Git, npm, system operations |
| `read` | File reading | "allow" | Code analysis, understanding |
| `edit` | File modifications (strings) | "allow" | Precise code changes |
| `write` | File creation | "allow" | New files |
| `apply_patch` | Patch application | "allow" | Diff-based changes |
| `glob` | File pattern matching | "allow" | File discovery |
| `grep` | Content search (regex) | "allow" | Code search |
| `lsp` (experimental) | Code intelligence | "allow" | Go-to-def, references, hover |
| `skill` | Skill loading | "allow" | Custom workflows |
| `todowrite` | Task management | "allow" | Multi-step tracking |
| `webfetch` | URL content fetching | "allow" | Documentation, research |
| `websearch` | Web search (requires OpenCode provider or `OPENCODE_ENABLE_EXA=1`) | "allow" | Research beyond training cutoff |
| `question` | User prompts | "allow" | Clarification, choices |

All tools respect `.gitignore` by default; use `.ignore` to whitelist paths.

---

### Commands & Custom Automation
**Define in `opencode.jsonc`**:
```jsonc
{
  "command": {
    "test": {
      "description": "Run tests with coverage",
      "agent": "build",
      "model": "anthropic/claude-haiku-4-5",
      "template": "Run the full test suite with coverage..."
    }
  }
}
```

**Or via markdown files** in `~/.config/opencode/commands/` or `.opencode/commands/`

---

### Model Configuration & Variants
**Provider routing**:
- `model: "provider/model-id"` format (e.g., `"anthropic/claude-sonnet-4-5"`)
- `small_model` for lightweight tasks (title generation, compaction)
- Per-agent model override (e.g., faster model for Plan agent)

**Variants** for same model with different configs:
- Built-in variants: Anthropic (`high`, `max`), OpenAI (`low`, `medium`, `high`), Google (`low`, `high`)
- Custom variants: Create per-model configuration sets
- Switch via keybind `variant_cycle`

**Provider options**:
- Timeout, chunk timeout, cache settings
- Provider-specific: AWS Bedrock region/profile, reasoning effort (OpenAI)

---

### Permissions Deep Dive
**Three-level access model**:
- `"allow"` — no prompt required
- `"ask"` — user approves before action (can save pattern for future)
- `"deny"` — tool blocked entirely

**Granular control**:
```jsonc
{
  "permission": {
    "bash": {
      "*": "ask",  // Catch-all: ask first
      "git *": "allow",  // Allow git commands
      "rm -rf *": "deny",  // Block destructive commands
      "grep *": "allow"
    },
    "edit": {
      "*": "deny",  // Block most edits
      "packages/web/src/**": "allow"  // Allow only web package
    },
    "external_directory": {
      "~/projects/personal/**": "allow"  // Allow access to external dirs
    }
  }
}
```

---

### Skills System
**What it does**: Reusable workflow modules loaded on-demand via the skill tool.

**Structure** (agentskills.io spec):
- `SKILL.md` — frontmatter + instructions
- `scripts/` — executable implementations
- `__init__.py` — Python module interface
- Versioning & dependencies

**PRUNE_PROTECTED**: Skill outputs survive context compaction (critical for agentic-engineers)

---

### TUI-Specific Features
**Separate config** (`tui.json`):
- Theme selection (tokyonight, etc.)
- Keybinds customization
- Scroll speed/acceleration
- Desktop notifications & sounds
- Attention feature (visual/audio alerts)

**Session features**:
- Session hierarchies (parent → child via subagent work)
- Navigation: `session_child_first`, `session_child_cycle`, `session_parent`
- Tab key: switch between primary agents
- Plan mode (Tab): disable changes, suggestions only

---

### Sharing & Collaboration
**Built-in sharing** (`share` option):
- `"manual"` — explicit `/share` command (default)
- `"auto"` — auto-share new conversations
- `"disabled"` — no sharing

**Generates shareable links** (opencode.ai/s/...)

---

### Hooks & Validation
**Tool hooks** (for plugins):
- `tool.execute.before` — pre-execution validation
- `tool.execute.after` — post-execution handling

**LSP integration** (experimental):
- Code intelligence from LSP servers
- Operations: goToDefinition, findReferences, hover, documentSymbol, callHierarchy

---

### Server & Remote Features
**OpenCode Server** (`opencode serve`):
- mDNS service discovery
- CORS configuration
- Custom hostname/port
- REST API for programmatic access

---

## Design Principles (From OpenCode Docs)

1. **Safety First**: Permission system prevents unintended damage
2. **Role-Based**: Different agents for different tasks (Planning ≠ Building)
3. **Extensible**: MCP servers, custom tools, plugins
4. **Context-Aware**: AGENTS.md rules, project-specific guidance
5. **Cost-Conscious**: Compaction, small_model for light tasks, reserved token buffer
6. **Integrated**: Hooks into git, LSP, IDE, web
7. **Transparent**: Explicit tool calls, ask permissions, undo/redo
8. **Composable**: Tasks → subagents → organized workflows

---

## Configuration Priority & Merging

**Key insight**: Configs are **merged**, not replaced.

Example:
- Global: `{ autoupdate: true }`
- Project: `{ model: "anthropic/claude-sonnet-4-5" }`
- **Result**: Both settings apply

This enables:
- Org-wide defaults (remote config)
- User preferences (global config)
- Project overrides (project config)

---

## OpenCode vs. Other Tools Comparison

| Feature | OpenCode | Cursor | GitHub Copilot |
|---------|----------|--------|-----------------|
| Agent routing | Yes (8+ custom) | No | No |
| Permission system | Granular (regex) | Rules only | No |
| MCP integration | Yes (remote/local) | No | GitHub MCP only |
| AGENTS.md rules | Yes | .cursor/rules | No |
| Compaction | Yes (PRUNE_PROTECTED) | Limited | No |
| Session hierarchy | Yes (subagents) | No | No |
| Local + remote config | Yes | Yes | No |
| Sharing | Yes | No | GitHub-only |
| macOS MDM | Yes | No | No |
| Custom models | Via variants | Via config | No |

---

## Integration Points for agentic-engineers

1. **Agent configuration** → Role-based agent setup (Orchestrator, Engineer, Senior, etc.)
2. **Permission system** → Enforce SPEC.md constraints (Security Engineer only for security tasks)
3. **Rules system** → Encode DELEGATE/HANDBACK protocol in AGENTS.md
4. **MCP integration** → Could expose queue as MCP server for external tooling
5. **Skills system** → Package DELEGATE templates, protocol validators as skills
6. **Compaction** → Long-running orchestrator sessions stay cost-effective
7. **Hooks** → Intercept tool calls for SDLC enforcement
8. **Subagents** → Model the 8-agent collaboration pattern

---

## External References

- [OpenCode Documentation](https://opencode.ai/docs/)
- [Config Schema](https://opencode.ai/config.json)
- [TUI Schema](https://opencode.ai/tui.json)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [agentskills.io Specification](https://agentskills.io/)
- [AI SDK (Vercel)](https://ai-sdk.dev/)
- [Models.dev](https://models.dev/)
