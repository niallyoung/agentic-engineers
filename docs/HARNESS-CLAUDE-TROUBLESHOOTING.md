# Claude Code Harness Troubleshooting Guide

This guide helps diagnose and fix Claude Code harness configuration issues and runtime problems.

## Quick Start

Run the harness validator to check the health of your Claude Code installation:

```bash
# Standard output
python3 -m src.harness.harness_checker --harness claude

# JSON output (for programmatic parsing)
python3 -m src.harness.harness_checker --harness claude --json

# With explicit repo root
python3 -m src.harness.harness_checker --harness claude --repo-root /path/to/agentic-engineers
```

## Common Issues and Fixes

### ❌ Agent Not Found

**Symptom:** `Error: Agent 'orchestrator' not found in configuration`

**Cause:** Agent definitions were not properly rendered during installation, or the session config is stale.

**Fix:**
```bash
# Regenerate agent configurations
make install-claude

# Verify agents directory exists
ls -la ~/.claude/config/agents/ | head -10

# Check file count (should show 8 agent files)
ls ~/.claude/config/agents/*.md | wc -l

# If agents missing, restore from repo
python3 renderer/scripts/render-claude.sh
```

**Expected agents:**
1. orchestrator.md
2. engineer.md
3. senior-engineer.md
4. lead-engineer.md
5. principal-engineer.md
6. security-engineer.md
7. quality-engineer.md
8. model-engineer.md

---

### ❌ Skill Not Rendering

**Symptom:** `Error: Skill 'task-routing' is not available` or skill does not appear in Claude Code UI

**Cause:** Skills directory was not populated during installation, or skill files are not readable.

**Fix:**
```bash
# Verify skills directory exists and is readable
ls -la ~/.claude/config/skills/ | head -20

# Check skill count (should be ≥14 core skills)
ls -d ~/.claude/config/skills/*/ | wc -l

# Verify file permissions
find ~/.claude/config/skills -type f -exec ls -lh {} \; | grep -v "^-rw"

# If skills missing, regenerate
make install-claude

# Or manually render
python3 renderer/scripts/render-claude.sh
```

**Core skills expected:**
- orchestrator
- spec-management
- skill-improvement-feedback
- codex-agent-cleanup
- protocol-validator
- queue-management
- queue-query
- spec-validator

---

### ❌ Session Not Detected

**Symptom:** `Error: No active session found` or `Error: Session ID format invalid`

**Cause:** Session directory not initialized or corrupted, or session ID format does not match expected pattern.

**Fix:**
```bash
# Create session directory manually
mkdir -p ~/.claude/sessions/{session-id}

# Verify directory structure
tree ~/.claude/sessions/ -L 2

# Check session ID format (should match: YYYY-MM-DD-HHMMSS)
# Example: 2026-06-15-143022

# Refresh sessions list
claude-code sessions refresh

# If session still missing, start new session
claude-code start
```

**Session directory structure expected:**
```
~/.claude/sessions/
├── {session-id}/
│   ├── config.jsonc            # Session-specific config
│   ├── context.json            # Session context
│   ├── history/                # Conversation history
│   └── cache/                  # Compiled references
```

---

### ❌ Model Not Recognized

**Symptom:** `Error: Model 'opus' not found` or `Error: Unknown model alias 'haiku'`

**Cause:** Model aliases are not properly configured, or claude.jsonc is missing/malformed.

**Fix:**
```bash
# Verify configuration file exists
ls -la ~/.claude/config/claude.jsonc

# Check model aliases are defined
cat ~/.claude/config/claude.jsonc | grep -A 10 "model.*:"

# Validate JSONC syntax
python3 << 'EOF'
import json
import re
with open(os.path.expanduser('~/.claude/config/claude.jsonc')) as f:
    content = f.read()
    # Remove comments for validation
    content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
    try:
        json.loads(content)
        print("✅ Config is valid JSON")
    except json.JSONDecodeError as e:
        print(f"❌ Config error: {e}")
EOF

# Expected model aliases in config
# haiku → claude-haiku-4.5
# sonnet → claude-sonnet-4
# opus → claude-opus-4

# If config invalid, regenerate
make install-claude
```

---

### ❌ HANDBACK Validation Failed

**Symptom:** `Error: HANDBACK schema validation failed` or `Error: Response does not match HANDBACK structure`

**Cause:** Agent response format does not conform to HANDBACK schema, or schema files are missing.

**Fix:**
```bash
# Verify schema files exist
ls -la ~/.claude/config/schemas/
ls ~/.claude/config/schemas/{delegate,handback}-schema.yaml

# Validate schema YAML syntax
python3 << 'EOF'
import yaml
for schema in ['~/.claude/config/schemas/delegate-schema.yaml', 
               '~/.claude/config/schemas/handback-schema.yaml']:
    try:
        with open(os.path.expanduser(schema)) as f:
            yaml.safe_load(f)
        print(f"✅ {schema} is valid")
    except yaml.YAMLError as e:
        print(f"❌ {schema} error: {e}")
EOF

# Check schema content (should have required_fields section)
grep -A 5 "required_fields:" ~/.claude/config/schemas/handback-schema.yaml

# If schemas missing or invalid, regenerate from repo
cp docs/specs/handback-schema.yaml ~/.claude/config/schemas/
cp docs/specs/delegate-schema.yaml ~/.claude/config/schemas/

# Then verify protocols
make install-claude
```

---

### ❌ Queue Draining Stuck

**Symptom:** Tasks remain in incoming/ state for >30s, or "Queue appears frozen" warning

**Cause:** Orchestrator is not polling, or incoming directory permissions are incorrect.

**Fix:**
```bash
# Check queue directory exists
ls -la ~/.claude/sessions/{session-id}/ | grep queue

# Verify queue subdirectories exist
mkdir -p ~/.claude/sessions/{session-id}/queue/{incoming,processing,done}

# Check permissions (should be 755)
ls -ld ~/.claude/sessions/{session-id}/queue/
ls -ld ~/.claude/sessions/{session-id}/queue/incoming/

# Fix permissions if needed
chmod 755 ~/.claude/sessions/{session-id}/queue/{incoming,processing,done}

# Check for stale files (older than 1 hour)
find ~/.claude/sessions/{session-id}/queue/incoming -type f -mmin +60 -ls

# If found, move to done/
mv ~/.claude/sessions/{session-id}/queue/incoming/*.yaml ~/.claude/sessions/{session-id}/queue/done/

# Restart orchestrator polling
claude-code sessions refresh
```

---

### ❌ Stale Cache Causing Issues

**Symptom:** Changes to agents/skills not visible, or "Configuration out of date" warning

**Cause:** Session cache is not invalidated after config changes.

**Fix:**
```bash
# Clear session cache
rm -rf ~/.claude/sessions/{session-id}/cache/

# Clear compiled references
rm -rf ~/.claude/config/cache/

# Verify caches cleared
ls -la ~/.claude/sessions/{session-id}/ | grep cache

# Restart Claude Code
claude-code sessions refresh

# Or start fresh session
claude-code start
```

---

### ❌ Wrong Model Used

**Symptom:** Task used Haiku when Sonnet was expected, or cost/quality mismatch in metrics

**Cause:** Model override configuration, or effort tier not properly configured.

**Fix:**
```bash
# Check model assignment for this session
cat ~/.claude/sessions/{session-id}/config.jsonc | grep -A 5 "model"

# Check global model config
cat ~/.claude/config/claude.jsonc | grep -A 5 "model"

# Verify effort tiers are defined
grep -A 10 "effort_tiers:" ~/.claude/config/claude.jsonc

# Expected effort mapping:
# low → haiku, medium → sonnet, high → opus

# If wrong model persists:
# 1. Check for per-project overrides
ls ~/.claude/projects/*/agents.jsonc 2>/dev/null

# 2. Check session override
cat ~/.claude/sessions/{session-id}/config.jsonc

# 3. Edit session config to correct model
# Then restart session: claude-code sessions refresh
```

---

### ❌ Protocol Violation Detected

**Symptom:** `Error: DELEGATE does not contain required field 'task_id'` or schema validation error

**Cause:** Task or response does not conform to DELEGATE/HANDBACK protocol.

**Fix:**
```bash
# Verify protocol schemas exist
ls -la ~/.claude/config/schemas/

# Check DELEGATE schema for required fields
python3 << 'EOF'
import yaml
with open(os.path.expanduser('~/.claude/config/schemas/delegate-schema.yaml')) as f:
    schema = yaml.safe_load(f)
    print("Required DELEGATE fields:")
    for field, spec in schema['required_fields'].items():
        print(f"  - {field}: {spec.get('type', 'unknown')}")
EOF

# Verify your DELEGATE blocks contain all required fields:
# - handoff_type: "DELEGATE"
# - task_id: format YYYY-MM-DD-kebab-case
# - agent: agent role (engineer, orchestrator, etc.)
# - scope: description (≥15 words)
# - plan: list of steps
# - success_criteria: list of acceptance criteria

# Check recent HANDBACKs for protocol compliance
cat ~/.claude/sessions/{session-id}/history/ | grep -A 20 "HANDBACK"

# If violations found, regenerate schemas
make install-claude
```

---

### ❌ Token Budget Exceeded

**Symptom:** `Error: Token budget exceeded for session` or `Error: Daily limit reached`

**Cause:** Session or daily token usage exceeded configured limits.

**Fix:**
```bash
# Check current token usage
python3 << 'EOF'
import json
import os
from datetime import datetime

session_dir = os.path.expanduser("~/.claude/sessions/{session-id}")
total_tokens = 0

# Sum tokens from all history files
for file in os.listdir(f"{session_dir}/history"):
    try:
        with open(f"{session_dir}/history/{file}") as f:
            data = json.load(f)
            total_tokens += data.get('tokens_used', 0)
    except:
        pass

print(f"Session tokens used: {total_tokens}")
EOF

# Check token budget configuration
cat ~/.claude/config/claude.jsonc | grep -A 5 "token_budget"

# Increase budget if needed (edit ~/.claude/config/claude.jsonc)
cat >> ~/.claude/config/claude.jsonc <<'EOF'
{
  "token_budget": {
    "session_limit": 2000000,      // Increase from default
    "daily_limit": 10000000,
    "hard_stop": false              // Warn but don't block
  }
}
EOF

# Or reduce scope of tasks to stay within budget
```

---

### ❌ Timeout Errors

**Symptom:** `Error: Operation timed out after 30s` or `Skill invocation timeout`

**Cause:** Operation exceeded configured timeout, or harness is hanging.

**Fix:**
```bash
# Check configured timeouts
cat ~/.claude/config/claude.jsonc | grep -A 10 "timeouts"

# Increase timeouts if needed
cat >> ~/.claude/config/claude.jsonc <<'EOF'
{
  "timeouts": {
    "skill_invocation": 60000,      // Increase to 60s
    "handback_validation": 20000,   // Increase to 20s
    "code_execution": 120000        // Increase to 2 min
  }
}
EOF

# Check if harness is hanging (process still running?)
ps aux | grep claude-code

# If hanging, kill and restart
pkill claude-code
sleep 2
claude-code start
```

---

## Full Validation Report Example

```
======================================================================
Claude Code Harness Validation Report
======================================================================

✅ check_agents_loaded: All 8 agents are defined in config/agents/

✅ check_skills_available: All 21 skills are available with documentation

✅ check_session_paths: Session structure properly initialized

❌ check_model_aliases: Model aliases mismatch (expected: haiku, sonnet, opus)
   → Remediation: Regenerate config with `make install-claude`

✅ check_schemas: Protocol schemas are valid and properly configured

✅ check_permissions: File permissions are correct (755 for dirs, 644 for files)

======================================================================
Result: WARNING (1 non-critical, 5 passed)
======================================================================
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed ✅ |
| 1 | One or more critical checks failed ❌ |
| 2 | Non-critical warnings (can proceed with caution) |

## Advanced Troubleshooting

### Check Repository Integrity

If multiple checks are failing, the repository may be corrupted:

```bash
# Verify repository structure
./scripts/verify-repo-integrity.sh

# Restore to known-good state
git status  # Check for uncommitted changes
git restore ~/.claude/  # Clear local customizations (⚠️ careful!)
make install-claude    # Reinstall from repo
```

### Manual Harness Initialization

If the harness checker can't fix issues automatically:

```bash
# 1. Remove stale configuration
rm -rf ~/.claude/config ~/.claude/sessions

# 2. Reinstall from scratch
make install-claude

# 3. Verify installation
ls -la ~/.claude/config/agents/ | wc -l  # Should show 8

# 4. Start fresh session
claude-code start
```

### Debug Mode

For detailed troubleshooting, enable debug logging:

```bash
# Set environment variable
export CLAUDE_DEBUG=1

# Start Claude Code with debug output
claude-code start

# Check logs
tail -f ~/.claude/sessions/{session-id}/logs/debug.log
```

## Performance

The harness validator is designed to run quickly:

- **Target:** <100ms for all checks
- **Typical time:** 10-50ms (depends on filesystem speed and cache size)
- **No blocking I/O:** All checks use local files only

## Integration with Claude Code

The HarnessChecker is designed to run at Claude Code startup to catch configuration errors early.

### Automatic Checks

Claude Code automatically runs validation checks:
- On startup (session initialization)
- After configuration changes (if enabled in settings)
- When rendering new agents or skills

### Manual Checks

Trigger validation manually:

```bash
# Check current session
claude-code verify

# Check specific harness
python3 -m src.harness.harness_checker --harness claude
```

## Further Reading

- [`~/.claude/config/AGENTS.md`](docs/guides/harness-setup/claude.md) — Claude Code agent setup
- [`docs/specs/delegate-schema.yaml`](docs/specs/delegate-schema.yaml) — DELEGATE block schema
- [`docs/specs/handback-schema.yaml`](docs/specs/handback-schema.yaml) — HANDBACK block schema
- [`docs/guides/harness-setup/README.md`](docs/guides/harness-setup/README.md) — Harness comparison
- [`docs/guides/claude-harness-extension.md`](docs/guides/claude-harness-extension.md) — Extension guide
