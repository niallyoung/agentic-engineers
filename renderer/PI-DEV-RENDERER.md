# π.dev Harness Renderer

Renders **agentic-engineers** configuration into **π.dev** integration harness.

## Prerequisites

- **Python 3.8+** — required
- **PyYAML** — optional but recommended (enables YAML validation of `pi.yml`)
  ```bash
  pip install pyyaml
  # or: pip3 install pyyaml
  ```
  Without PyYAML, the renderer will skip YAML validation and print a warning.
  All other functionality (file rendering, JSON validation, status, uninstall) works without it.

## What It Does

The renderer generates three critical files in `~/.pi/agent/`:

| File | Purpose | Bootstrap Impact |
|------|---------|------------------|
| **SYSTEM.md** | Complete system prompt | **Replaces pi's default prompt** at bootstrap |
| **AGENTS.md** | Agent role definitions | Appended as project context |
| **settings.json** | Model & UI defaults | Loaded on pi startup |

## Key Design Points

### 100% System Prompt Control from Bootstrap

Per pi.dev research, when `~/.pi/agent/SYSTEM.md` exists, pi reads it **first** and uses it as the complete system prompt, **replacing** the built-in pi default.

**This means**:
- ✅ agentic-engineers identity is guaranteed from turn 1
- ✅ No pi defaults leak through
- ✅ No forking or custom pi binary required
- ✅ Works with standard `pi` binary (v0.74.0+)

### Config Hierarchy

```
~/.pi/agent/SYSTEM.md          ← Global system prompt (REPLACES pi default)
~/.pi/agent/AGENTS.md          ← Global context (appended as "Project Context")
~/.pi/agent/settings.json      ← Model defaults, UI theme, compaction
~/.pi/agent/extensions/        ← Optional: TypeScript event handlers
```

Project-level `.pi/` (in your repo) overrides global `~/.pi/agent/` for SYSTEM.md, AGENTS.md, and settings.json.

## Quick Start

### 1. Install pi.dev

```bash
npm install -g @earendil-works/pi-coding-agent
# or check official docs: https://github.com/earendil-works/pi
```

### 2. Render agentic-engineers Config

```bash
cd /path/to/agentic-engineers
python3 renderer/scripts/render-pi-dev.py
```

Output:
```
π.dev Harness Renderer (agentic-engineers)
======================================================================
Source: /path/to/agentic-engineers/renderer/pi-dev-src
Destination: /Users/you/.pi/agent

✅ Rendered: SYSTEM.md → ~/.pi/agent/SYSTEM.md
✅ Rendered: AGENTS.md → ~/.pi/agent/AGENTS.md
✅ Rendered: settings.json → ~/.pi/agent/settings.json
```

### 3. Start Using pi

```bash
cd /any/project
pi

# Your system prompt will be agentic-engineers (from SYSTEM.md)
# Your available agent roles will be loaded from AGENTS.md
```

### 4. Verify It Worked

Check that pi loads your system prompt:

```bash
# The pi TUI should show "agentic-engineers" behavior
# System prompt has your custom Orchestrator identity
```

## Renderer Usage

### Default Behavior

```bash
python3 renderer/scripts/render-pi-dev.py
```

Renders from `renderer/pi-dev-src/` → `~/.pi/agent/`

### Custom Source/Destination

```bash
python3 renderer/scripts/render-pi-dev.py /custom/src /custom/dest
```

Renders from `/custom/src/` → `/custom/dest/agent/`

## File Structure

```
renderer/
├── pi-dev-src/                ← Source files (committed)
│   ├── SYSTEM.md              ← agentic-engineers system prompt
│   ├── AGENTS.md              ← Agent role definitions
│   └── settings.json          ← Model/UI defaults
│
└── scripts/
    ├── render-pi-dev.py       ← The renderer (executable)
    └── render-copilot-agents.py
```

## Source Files

### SYSTEM.md

Master system prompt for agentic-engineers. Covers:
- Core identity (Orchestrator)
- Task routing decision tree
- DELEGATE creation patterns
- Metrics collection
- CI/CD monitoring
- Token optimization strategies

When rendered to `~/.pi/agent/SYSTEM.md`, this **completely replaces** pi's built-in prompt at bootstrap.

### AGENTS.md

Global agent role context. Covers:
- 9 specialized roles (Engineer, Senior Engineer, Security Engineer, etc.)
- Role expertise and best uses
- DELEGATE patterns
- HANDBACK expectations
- Routing decision tree

Appended to SYSTEM.md as "Project Context" in every pi turn.

### settings.json

pi.dev model and UI configuration:
- Default LLM provider (Anthropic)
- Default model (claude-sonnet-4-20250514)
- Thinking level (medium)
- Theme (dark)
- Token compaction settings
- Extensions and skills

## Advanced: Project-Level Overrides

Create `.pi/` in your repo to override global settings for specific projects:

```bash
# In your project root:
mkdir -p .pi

# Override system prompt:
cp ~/.pi/agent/SYSTEM.md .pi/SYSTEM.md
# Edit .pi/SYSTEM.md with project-specific instructions

# pi will now use .pi/SYSTEM.md for this project
pi
```

Priority: `.pi/SYSTEM.md` (project) > `~/.pi/agent/SYSTEM.md` (global)

## Advanced: TypeScript Extensions

For dynamic per-turn prompt modifications, create `~/.pi/agent/extensions/agentic-engineers.ts`:

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function(pi: ExtensionAPI) {
  pi.on("before_agent_start", async (event) => {
    // event.systemPrompt — current prompt (includes SYSTEM.md)
    // Modify or replace it here if needed
    return {
      systemPrompt: event.systemPrompt + "\n\n[Additional instructions]"
    };
  });
}
```

Add to `settings.json`:
```json
{
  "extensions": ["~/.pi/agent/extensions/agentic-engineers.ts"]
}
```

## Troubleshooting

### SYSTEM.md Not Loading

**Symptom**: pi still shows its default prompt ("You are an expert coding assistant...")

**Fix**:
1. Verify `~/.pi/agent/SYSTEM.md` exists: `ls ~/.pi/agent/SYSTEM.md`
2. Verify it has content: `head ~/.pi/agent/SYSTEM.md`
3. Try re-rendering: `python3 renderer/scripts/render-pi-dev.py`
4. Check pi version: `pi --version` (should be 0.74.0+)

### Settings Not Applied

**Symptom**: pi uses different model/theme than settings.json

**Fix**:
1. Verify `~/.pi/agent/settings.json` exists and is valid JSON
2. Check for project-level `.pi/settings.json` override (takes priority)
3. Try: `rm ~/.pi/sessions/*` (clear cached sessions)

### Extensions Not Loading

**Symptom**: Extension TypeScript not executing

**Fix**:
1. Ensure path in `settings.json` is absolute or starts with `~`
2. Verify `.ts` file is valid TypeScript
3. Check pi logs: `pi --debug` (if available)

## Integration with agentic-engineers Workflow

### When to Render

- **First setup**: Initial pi.dev installation
- **After SYSTEM.md changes**: When updating system prompt
- **After AGENTS.md changes**: When adding roles or changing routing
- **After settings.json changes**: When adjusting model defaults

### Typical Workflow

```bash
# 1. Modify agentic-engineers prompts in renderer/pi-dev-src/
vim renderer/pi-dev-src/SYSTEM.md

# 2. Render to ~/.pi/agent/
python3 renderer/scripts/render-pi-dev.py

# 3. Test with pi
cd /your/project
pi "What can you do?"

# 4. Commit changes if happy
git add renderer/pi-dev-src/
git commit -m "Update agentic-engineers system prompt"
```

## CLI Reference

### Render Command

```bash
python3 renderer/scripts/render-pi-dev.py [source] [dest]

Options:
  source  Source directory with .md/.json files (default: renderer/pi-dev-src/)
  dest    Destination base (default: ~/.pi)
          Creates dest/agent/ directory automatically

Exit Codes:
  0       Success
  1       Error (missing files, write permission, etc.)
```

### pi Commands

```bash
pi                           # Interactive mode with agentic-engineers prompt
pi --no-session              # Ephemeral mode (no session saved)
pi --system-prompt "..."     # Override system prompt for this session
pi --append-system-prompt "..."  # Append to system prompt
pi --no-context-files        # Don't load AGENTS.md
```

## Maintenance

### Update Frequency

- **SYSTEM.md**: As agentic-engineers evolves (quarterly+ or as needed)
- **AGENTS.md**: When adding new agent roles or changing routing
- **settings.json**: When changing model defaults or UI preferences

### Version Tracking

Source files are committed to git:
```bash
git log renderer/pi-dev-src/
git show HEAD:renderer/pi-dev-src/SYSTEM.md  # View history
```

Rendered files in `~/.pi/` are **local only** (not committed).

---

**Documentation Version**: 1.0
**π.dev Version Tested**: 0.74.0+
**agentic-engineers Version**: 1.0
**Last Updated**: 2026-05-15
