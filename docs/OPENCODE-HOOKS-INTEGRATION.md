# OpenCode Git Hooks Integration

This document describes the integration of git enforcement hooks with OpenCode configuration for the agentic-engineers framework.

## Overview

The integration provides:

1. **Git hooks configuration** via `core.hooksPath = .githooks`
2. **OpenCode commands** for hook management and SDLC workflow validation
3. **Unified SDLC enforcement** across git and OpenCode

## Configuration

### opencode.jsonc

The project-level OpenCode configuration is stored in `opencode.jsonc` with:

- **Schema**: Validates against `https://opencode.ai/config.json`
- **Commands**: Three OpenCode commands for SDLC workflow
- **Permissions**: Tool access control for agents
- **Providers**: GitHub Copilot model configuration

Key sections:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  
  // Commands for SDLC workflow
  "command": {
    "sdlc-check": { ... },      // Validate workflow compliance
    "hooks-install": { ... },   // Install/verify hooks
    "queue-status": { ... }     // Review work queue
  },
  
  // Git hooks path configuration (reference)
  // Actual configuration: git config core.hooksPath = .githooks
}
```

### Git Hooks Configuration

Hooks are configured via:

```bash
git config core.hooksPath .githooks
```

This points git to the `.githooks/` directory instead of the default `.git/hooks/`.

## Hooks

Three enforcement hooks are installed:

### 1. `.githooks/pre-commit`

**Purpose**: Enforce SPEC compliance and security before staging

**Checks**:
- SPEC constraint: No external scripts in `orchestration/scripts/`
- SPEC constraint: No cron files in `orchestration/config/`
- Secret detection (API keys, AWS keys, passwords)
- YAML/JSON well-formedness
- No bypass markers in committed code

**Bypass**: `SKIP_HOOKS=1 git commit` (emergency only)

### 2. `.githooks/commit-msg`

**Purpose**: Validate commit message format and protocol compliance

**Checks**:
- Message length (10-72 chars for subject line)
- Conventional commit format (optional but encouraged)
- Task ID tracking (YYYY-MM-DD-kebab-case)
- DELEGATE/HANDBACK protocol validation
- No secrets in commit message

**Bypass**: `SKIP_COMMIT_MSG_HOOK=true git commit` (not recommended)

### 3. `.githooks/pre-push`

**Purpose**: Quality gate before pushing to shared branches

**Checks**:
- Agent YAML validation
- Test suite execution (pytest)
- Documentation consistency
- DELEGATE/HANDBACK protocol compliance
- SPEC compliance
- Warning for main/master branch pushes

**Bypass**: `SKIP_HOOKS=1 git push` (emergency only)

## OpenCode Commands

### `/sdlc-check`

Validates SDLC workflow compliance:

```
/sdlc-check
```

Checks:
1. **Queue health**: Stalled items in `artifacts/queue/`
2. **DELEGATE/HANDBACK integrity**: Missing matches, malformed YAML
3. **Git hooks status**: Verify enforcement hooks are active
4. **SPEC compliance**: No violations in protected paths

### `/hooks-install`

Installs and verifies git enforcement hooks:

```
/hooks-install
```

Executes:
```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/commit-msg .githooks/pre-push
```

Verifies:
- `git config core.hooksPath` returns `.githooks`
- All hook files exist and are executable

### `/queue-status`

Reviews pending work in the queue:

```
/queue-status
```

Summarizes:
1. **Incoming queue**: Pending tasks waiting for routing
2. **Processing queue**: Tasks in-flight with status
3. **Done queue**: Completed tasks from today
4. **Recent DELEGATEs**: DELEGATEs from last 24 hours

## Integration Workflow

### Initial Setup

1. Clone the repository
2. Run `/hooks-install` command to configure hooks
3. Verify with `git config core.hooksPath`

### Daily Workflow

1. **Pre-commit**: Hooks validate changes before staging
2. **Commit message**: Hooks validate message format
3. **Pre-push**: Hooks run quality gates before pushing
4. **SDLC check**: Run `/sdlc-check` to validate workflow

### Emergency Bypass

If a hook blocks legitimate work:

```bash
# Pre-commit bypass
SKIP_HOOKS=1 git commit -m "fix: urgent issue"

# Pre-push bypass
SKIP_HOOKS=1 git push

# Commit message bypass (not recommended)
SKIP_COMMIT_MSG_HOOK=true git commit
```

**Important**: Document the reason in the commit message when using bypass.

## Testing

Run integration tests:

```bash
python3 -m pytest tests/test_opencode_hooks_integration.py -v
```

Test coverage:
- OpenCode configuration validity
- Git hooks configuration
- Hook file existence and permissions
- Command file structure
- Integration between hooks and commands
- Bypass mechanisms

## Troubleshooting

### Hooks not running

Check configuration:
```bash
git config core.hooksPath
# Should output: .githooks

ls -la .githooks/
# All hooks should be executable (-rwx)
```

### Reinstall hooks

```bash
/hooks-install
```

Or manually:
```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/commit-msg .githooks/pre-push
```

### Bypass a specific hook

```bash
# Skip all hooks
SKIP_HOOKS=1 git commit

# Skip commit message validation only
SKIP_COMMIT_MSG_HOOK=true git commit

# Skip pre-push validation
SKIP_HOOKS=1 git push
```

## References

- **SPEC.md**: Framework specification and constraints
- **AGENTS.md**: Agent definitions and roles
- **docs/QUEUE-PROTOCOL.md**: DELEGATE/HANDBACK protocol
- **docs/SECURITY-HOOKS.md**: Security bypass procedures

## Files

- `opencode.jsonc` - OpenCode configuration with commands
- `.githooks/pre-commit` - SPEC compliance enforcement
- `.githooks/commit-msg` - Message format validation
- `.githooks/pre-push` - Quality gate enforcement
- `.opencode/commands/hooks-install.md` - Hook installation command
- `.opencode/commands/sdlc-check.md` - Workflow validation command
- `.opencode/commands/queue-status.md` - Queue status command
- `tests/test_opencode_hooks_integration.py` - Integration tests
