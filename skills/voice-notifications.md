---
name: Voice Notifications with Context-Specific Phrases
description: Dynamic voice alerts at 70% and 85% token thresholds with context-aware messages
type: skill
applies_to: [agentic-engineers framework]
---

# Voice Notifications — Context-Specific Phrases

**Settings Location**: `~/.claude/settings.json` (do NOT hardcode commands here)

## Phrase Selection

Voice notifications should use **context-specific phrases** instead of static "yo":

| Context | Phrase | When to Use |
|---------|--------|------------|
| CICD monitoring | `watching cicd` | While monitoring GitHub Actions builds |
| General waiting | `waiting` | Other background waits (deploys, API calls) |
| Uncertainty | `hmm` | When investigating or thinking through options |
| Confirmation | `yes` | Confirming user requests before action |

**Volume**: 70% (Daniel voice)

## Configuration (Correct Way)

❌ **WRONG** — Hardcoding in settings.json:
```json
{
  "hooks": {
    "Notification": [
      {
        "command": "say -v Daniel YO"  // ← Hardcoded, can't change
      }
    ]
  }
}
```

✅ **RIGHT** — Use Claude Code voice command directly when needed:

```bash
# In scripts or bash tools
osascript -e 'beep 1'  # Fallback if say command not available

# Or use Claude's native notification system
# (handled by the Notification hook, but phrase selection by context)
```

## Implementation Pattern

When you need to send a notification:

```bash
# Example: While monitoring builds
# Send to user's notification system with context phrase

# Via system notification (preferred):
# User will hear context phrase based on what they set

# OR via bash if needed:
say -v Daniel "watching cicd" 2>/dev/null &
```

## For Orchestrator

When delegating work or waiting:

1. **Determine context**: What are we waiting for?
2. **Choose phrase**: Select from table above
3. **Send notification**: Let system handle it
4. **Don't hardcode**: Never put phrases in settings.json

## Removing Hardcoded "YO"

If you see `"say -v Daniel YO"` in settings.json:

1. Open `~/.claude/settings.json`
2. Find the Notification hook
3. Remove or comment out the hardcoded command
4. Let context-specific phrases be chosen at runtime based on what's actually happening

**After removing hardcoded command**:
```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "*"
        // Command removed — phrases chosen by context at runtime
      }
    ]
  }
}
```

## Voice Notification Thresholds

Claude Code sends notifications at token usage milestones:
- **70% usage**: Warning (first notification)
- **85% usage**: Critical (final warning)

Phrase should reflect the current context when notification fires, not a generic hardcoded phrase.

