# $REPO_ROOT Variable Usage in Render Scripts

## Overview

The `$REPO_ROOT` variable is used in render scripts to reference the agentic-engineers repository root. This document explains why it's necessary and how it's used.

## Render Scripts Using $REPO_ROOT

1. **renderer/scripts/render-opencode.sh** - Renders config for OpenCode harness
2. **renderer/scripts/render-claude.sh** - Renders config for Claude Code harness
3. **renderer/scripts/render-copilot.sh** - Renders skills for Copilot harness
4. **renderer/scripts/render-pi.sh** - Renders config for π.dev harness

## Why $REPO_ROOT is Necessary

### 1. **Script Invocation from Any Directory**
The render scripts are invoked from the Makefile with absolute paths:

```bash
bash "$(REPO_ROOT)/renderer/scripts/render-opencode.sh" "$(REPO_ROOT)" "$(HOME)/.config/opencode"
```

The scripts are designed to be called with `$REPO_ROOT` as an **argument**, not sourced from a fixed location.

### 2. **Cross-Directory References**
Render scripts need to reference multiple source directories:
- `$REPO_ROOT/src/skills/` - Skill definitions
- `$REPO_ROOT/src/agents/` - Agent definitions
- `$REPO_ROOT/docs/AGENTS.md` - Framework documentation
- `$REPO_ROOT/renderer/scripts/lib.sh` - Shared functions

Using relative paths from the script location would require:
```bash
# Complex relative path logic
SRC_SKILLS="$(dirname "$0")/../../src/skills"
```

This is fragile and breaks if the script is symlinked or called from different contexts.

### 3. **Shared Library Sourcing**
Scripts source `lib.sh` using `$REPO_ROOT`:

```bash
source "$(dirname "$0")/lib.sh"
```

But `lib.sh` itself needs to reference the repo root for its operations.

### 4. **Git Operations**
Some scripts perform git operations that require the repo root:

```bash
url=$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)
```

## Design Pattern

The render scripts follow this pattern:

```bash
#!/usr/bin/env bash

# Accept REPO_ROOT as first argument
REPO_ROOT="${1:?usage: render-opencode.sh REPO_ROOT OPENCODE_DIR [--uninstall|--status]}"
OPENCODE="${2:?usage: render-opencode.sh REPO_ROOT OPENCODE_DIR [--uninstall|--status]}"

# Use $REPO_ROOT for all source references
SRC_SKILLS="$REPO_ROOT/src/skills"
SRC_AGENTS="$REPO_ROOT/src/agents"

# Source shared library (relative path works because we know script location)
source "$(dirname "$0")/lib.sh"

# Use $REPO_ROOT in git operations
git -C "$REPO_ROOT" ...
```

## Invocation Examples

### From Makefile (Recommended)
```bash
bash "$(REPO_ROOT)/renderer/scripts/render-opencode.sh" "$(REPO_ROOT)" "$(HOME)/.config/opencode"
```

### From Command Line
```bash
# Explicit repo root
bash /path/to/agentic-engineers/renderer/scripts/render-opencode.sh \
  /path/to/agentic-engineers \
  ~/.config/opencode

# Using git to find repo root
REPO_ROOT=$(git rev-parse --show-toplevel)
bash "$REPO_ROOT/renderer/scripts/render-opencode.sh" "$REPO_ROOT" ~/.config/opencode
```

## Conclusion

**$REPO_ROOT cannot be replaced with relative paths** because:

1. Scripts are invoked from arbitrary locations via Makefile
2. Multiple source directories need absolute references
3. Git operations require the repo root
4. The pattern is intentional and provides robustness

This is a deliberate design choice that ensures the render scripts work correctly regardless of where they're invoked from.

---
**Last Updated**: 2026-05-16
**Status**: Documented (no changes needed)
