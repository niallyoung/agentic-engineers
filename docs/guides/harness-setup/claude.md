# Claude Code Harness Setup

**Description:** Native IDE and code editor harness for interactive development. Recommended for single-developer workflows and rapid prototyping.

**Latest Tested:** v1.3.0 (2026-06-15)  
**Minimum Required:** v1.1.0  
**Repository:** [github.com/anthropic-ai/claude-code](https://github.com/anthropic-ai/claude-code)

## Features

- ✅ Full DELEGATE/HANDBACK protocol support
- ✅ Interactive web-based IDE with real-time code editing
- ✅ Integrated terminal and console output
- ✅ Local file system access with granular permissions
- ✅ Model selection via UI (opus, sonnet, haiku aliases)
- ✅ Session-based context preservation (24-hour retention)

## Installation

```bash
make install-claude
```

This will:
1. Create configuration at `~/.claude/` with agent definitions and skills
2. Initialize session state directory at `~/.claude/sessions/`
3. Render agent configurations with Claude Code-specific model aliases
4. Install protocol documents and skill documentation
5. Set up the harness integration layer

## Configuration

### Session Directory

Claude Code uses session-based storage for context and state:

```bash
~/.claude/
├── CLAUDE.md                    # Codebase documentation (auto-generated)
├── config/                      # Agent and skill configuration
│   ├── AGENTS.md                # Agent definitions (rendered)
│   ├── claude.jsonc             # Harness config (model aliases, timeouts)
│   ├── agents/                  # Agent profiles
│   └── skills/                  # Skill documentation
├── sessions/                    # Active session storage
│   ├── {session-id}/
│   │   ├── context.json         # Session context and state
│   │   ├── history/             # Conversation history
│   │   └── cache/               # Compiled agent/skill references
└── projects/                    # Per-project overrides (optional)
```

These directories are created automatically by `make install-claude`.

### Model Aliases

Claude Code uses short model aliases in the UI (opus, sonnet, haiku) which are mapped internally to full Anthropic model names:

- `haiku` → `claude-haiku-4.5`
- `sonnet` → `claude-sonnet-4`
- `opus` → `claude-opus-4`

The renderer automatically handles these aliases during configuration rendering.

## Usage

### Starting Claude Code

Claude Code is typically invoked from the CLI or as a VS Code extension:

```bash
# Start Claude Code web interface (localhost:3000)
claude-code start

# Start with custom port
claude-code start --port 3001

# Start with specific codebase context
claude-code start --project /path/to/project
```

### Interactive Development Workflow

```bash
# 1. Open Claude Code IDE
claude-code start

# 2. Load your agentic-engineers repository context
# (via "Load project" UI or --project flag)

# 3. Ask Claude a question or request a task
"Fix the token validation timeout in lambda/api/main.go"

# 4. Claude returns HANDBACK-format response with:
# - Code changes (inline in editor)
# - Test results
# - Metrics (tokens used, quality estimate)

# 5. Review changes and accept/modify
```

### Session Management

Claude Code preserves session context across browser refreshes:

```bash
# List active sessions
claude-code sessions list

# Resume previous session
claude-code sessions open {session-id}

# Clear session cache (if needed)
claude-code sessions clear {session-id}
```

## Known Limitations

- Session context limited to 24 hours (context expires and is archived)
- File permissions checked per operation (interactive prompts for new paths)
- Model selection persists per session (not global)
- Terminal access is sandboxed (cannot execute arbitrary system commands outside project)

## Compatibility Notes

- ✅ Works with Anthropic API keys (default, via ~/.claude/config/)
- ✅ Integrates with GitHub (clone, commit, PR operations)
- ✅ Supports local projects (monorepos, microservices)
- ✅ Compatible with all Anthropic models (haiku, sonnet, opus)

## Troubleshooting

### Session not detected

**Symptom:** `Error: No active session found`

**Cause:** Claude Code session directory does not exist or was cleared.

**Fix:**
```bash
mkdir -p ~/.claude/sessions/{session-id}

# Or restart Claude Code
claude-code sessions refresh
```

### Model not recognized

**Symptom:** `Error: Model 'opus' not found in configuration`

**Cause:** Model aliases are not properly configured.

**Fix:** Verify configuration was rendered:
```bash
# Check config file
cat ~/.claude/config/claude.jsonc | grep -i "model"

# If missing, re-run installer
make install-claude
```

### File permissions denied

**Symptom:** `Error: Permission denied for /path/to/file`

**Cause:** Claude Code requires explicit permission to access file paths outside the initial project context.

**Fix:**
1. In the Claude Code UI, a permission prompt should appear automatically
2. Click "Allow" to grant access
3. To allow all paths: edit `~/.claude/config/claude.jsonc` and set `permissive_mode: true` (not recommended for security)

### Context not loading

**Symptom:** `Error: CLAUDE.md not found or invalid`

**Cause:** Codebase documentation was not properly rendered during installation.

**Fix:**
```bash
# Regenerate CLAUDE.md
make install-claude

# Or manually run renderer
python3 renderer/scripts/render-claude.sh
```

## Advanced Configuration

### Custom Model Pins (Per-Session)

Override model assignments for a specific session by editing the session config:

```jsonc
// ~/.claude/sessions/{session-id}/config.jsonc
{
  "model_overrides": {
    "orchestrator": "opus",       // Always use Opus for orchestration
    "engineer": "sonnet",          // Always use Sonnet for engineers
    "quality-engineer": "haiku"    // Use Haiku for QE (cost optimization)
  }
}
```

After editing, restart the session for changes to take effect.

### Effort Tier Customization

Customize effort-based model selection:

```jsonc
// ~/.claude/config/claude.jsonc
{
  "effort_tiers": {
    "low": "haiku",        // < 30 min, straightforward
    "medium": "sonnet",    // 1-2 hours, some complexity
    "high": "opus"         // 2+ hours, high complexity
  }
}
```

### Per-Project Agent Overrides

Create project-specific agent profiles to override global settings:

```bash
# Create .claude/agents.jsonc in your project root
cat > ~/git/agentic-engineers/.claude/agents.jsonc <<'EOF'
{
  "agents": {
    "orchestrator": {
      "model": "opus",
      "temperature": 0.3
    }
  }
}
EOF
```

When you load the project in Claude Code, these overrides take precedence.

## Advanced Configuration

### Token Budget Tuning

Set per-session token budgets to control costs:

```jsonc
// ~/.claude/config/claude.jsonc
{
  "token_budget": {
    "session_limit": 1000000,    // Max tokens per session
    "daily_limit": 5000000,       // Max tokens per day
    "hard_stop": true             // Block when limit reached
  }
}
```

### Custom Timeout Policies

Configure timeouts for different operation types:

```jsonc
// ~/.claude/config/claude.jsonc
{
  "timeouts": {
    "skill_invocation": 30000,    // 30s for skills
    "handback_validation": 10000, // 10s for schema validation
    "code_execution": 60000       // 60s for linting/testing
  }
}
```

## Testing Your Changes

### Verify Configuration

After editing `claude.jsonc`, verify the syntax is valid:

```bash
python3 << 'EOF'
import json
import sys

try:
    with open(os.path.expanduser("~/.claude/config/claude.jsonc")) as f:
        # Note: JSONC allows comments; use standard json for validation
        content = f.read()
        # Remove comments for validation
        import re
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        json.loads(content)
    print("✅ Configuration is valid")
except json.JSONDecodeError as e:
    print(f"❌ Invalid configuration: {e}")
    sys.exit(1)
EOF
```

### Test Agent Loading

Verify agents load correctly with your customizations:

```bash
# Start Claude Code and check console for load errors
claude-code start

# In another terminal, check logs
tail -f ~/.claude/sessions/{session-id}/logs/agent-load.log
```

### Test Skill Availability

Verify your skills are accessible:

```bash
# List available skills in Claude Code UI (Help → Skills)
# Or check programmatically:
python3 -c "
import json
with open(os.path.expanduser('~/.claude/config/claude.jsonc')) as f:
    config = json.load(f)
    print(f\"Available skills: {len(config.get('skills', []))}\")"
```

## Next Steps

- [Harness Setup Overview](README.md)
- [Claude Code Extension Guide](../claude-harness-extension.md)
- [Claude Code Troubleshooting](../../HARNESS-CLAUDE-TROUBLESHOOTING.md)
