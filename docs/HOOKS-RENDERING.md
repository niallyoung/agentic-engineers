# Hooks Rendering Integration — Harness-Specific Behavior

## Overview

Git hooks are installed consistently across all 4 harness renderers to enforce SDLC compliance at commit/push time. This document describes harness-specific behavior and integration patterns.

## Hooks Architecture

All harnesses use the same git hooks from `REPO_ROOT/.githooks/`:
- **pre-commit**: Enforces SPEC compliance, detects secrets, validates YAML/JSON
- **commit-msg**: Enforces commit message format and minimum length
- **pre-push**: Validates agent YAML, runs tests, warns on protected branches

## Harness-Specific Integration

### 1. OpenCode Renderer (`render-opencode.sh`)

**Hook Installation:**
- Installs hooks from `REPO_ROOT/.githooks/`
- Configures `core.hooksPath = .githooks` in the repository
- Makes all hooks executable with `chmod +x`

**When Hooks Are Installed:**
- During `render-opencode.sh install` (default mode)
- After skills and agents are rendered
- Before completion message

**Error Handling:**
- If `.githooks` directory doesn't exist, logs warning and continues
- Git configuration is applied to the repository itself (not harness-specific)
- Hooks are shared across all harnesses using the same repo

**Example Output:**
```
📦 Installing git hooks from /path/to/repo/.githooks/...
✅ Git hooks installed (core.hooksPath = .githooks)
```

### 2. Claude Code Renderer (`render-claude.sh`)

**Hook Installation:**
- Installs hooks from `REPO_ROOT/.githooks/`
- Configures `core.hooksPath = .githooks` in the repository
- Makes all hooks executable with `chmod +x`

**When Hooks Are Installed:**
- During `render-claude.sh install` (default mode)
- After skills and agents are rendered
- Before completion message

**Error Handling:**
- If `.githooks` directory doesn't exist, logs warning and continues
- Git configuration is applied to the repository itself (shared with OpenCode)
- Hooks are shared across all harnesses using the same repo

**Note:** Claude Code and OpenCode use the same git repository, so hooks are configured once and apply to both harnesses.

**Example Output:**
```
📦 Installing git hooks from /path/to/repo/.githooks/...
✅ Git hooks installed (core.hooksPath = .githooks)
```

### 3. GitHub Copilot Renderer (`render-copilot.sh`)

**Hook Installation:**
- Installs hooks from `REPO_ROOT/.githooks/`
- Configures `core.hooksPath = .githooks` in the repository
- Makes all hooks executable with `chmod +x`

**When Hooks Are Installed:**
- During `render-copilot.sh install` (default mode)
- After skills are rendered
- Before completion message

**Error Handling:**
- If `.githooks` directory doesn't exist, logs warning and continues
- Git configuration is applied to the repository itself (shared with OpenCode/Claude)
- Hooks are shared across all harnesses using the same repo

**Note:** Copilot uses the same git repository as OpenCode/Claude, so hooks are configured once and apply to all shell-based harnesses.

**Example Output:**
```
📦 Installing git hooks from /path/to/repo/.githooks/...
✅ Git hooks installed (core.hooksPath = .githooks)
```

### 4. Pi.dev Renderer (`render-pi-dev.py`)

**Hook Installation:**
- Discovers repository root by walking up directory tree looking for `.git/`
- Installs hooks from `REPO_ROOT/.githooks/`
- Configures `core.hooksPath = .githooks` using subprocess
- Makes all hooks executable with `chmod(0o755)`

**When Hooks Are Installed:**
- During `render_all()` method (default mode)
- After config files are validated
- Before completion message

**Error Handling:**
- If `.git` directory not found, logs warning and returns False
- If `.githooks` directory doesn't exist, logs warning and returns False
- Git configuration failures are caught and logged
- Returns boolean status indicating success/failure

**Repo Discovery Algorithm:**
```python
repo_root = self.src_dir
while repo_root != repo_root.parent:
    if (repo_root / ".git").exists():
        break
    repo_root = repo_root.parent
```

**Example Output:**
```
Installing git hooks...

✅ Git hooks installed (core.hooksPath = .githooks)
```

## Shared Hook Behavior

Since all harnesses use the same git repository, hooks are configured **once** and apply to **all harnesses**:

1. **First renderer to run** configures `core.hooksPath = .githooks`
2. **Subsequent renderers** re-apply the same configuration (idempotent)
3. **All harnesses** enforce the same SDLC rules at commit/push time

## Hook Execution Flow

```
Developer runs: git commit
    ↓
Git invokes: .githooks/pre-commit
    ├─ Check SPEC compliance (no external scripts)
    ├─ Detect secrets (API keys, AWS keys, etc.)
    ├─ Validate YAML/JSON syntax
    └─ Check for bypass markers
    ↓
If pre-commit passes:
    Git invokes: .githooks/commit-msg
    ├─ Validate message length (≥10 chars)
    ├─ Check message format
    └─ Verify SKIP_HOOKS documentation
    ↓
If commit-msg passes:
    Commit is created
    ↓
Developer runs: git push
    ↓
Git invokes: .githooks/pre-push
    ├─ Validate agent YAML frontmatter
    ├─ Run test suite (if available)
    └─ Warn on protected branches
    ↓
If pre-push passes:
    Push is allowed
```

## Bypass Mechanism

Emergency bypass is available via environment variable:

```bash
# Bypass pre-commit enforcement (pre-push still runs)
SKIP_HOOKS=1 git commit -m "emergency fix: reason here"

# Bypass pre-push enforcement
SKIP_HOOKS=1 git push
```

**Important:** When using `SKIP_HOOKS=1`, the commit message must document the reason:
- Include "SKIP_HOOKS: <reason>" in the message
- Or mention "emergency" or "bypass" in the message
- This is enforced by the commit-msg hook

## Testing Hook Installation

### Manual Testing

```bash
# Test OpenCode renderer
./renderer/scripts/render-opencode.sh /path/to/repo ~/.config/opencode

# Test Claude Code renderer
./renderer/scripts/render-claude.sh /path/to/repo ~/.claude

# Test Copilot renderer
./renderer/scripts/render-copilot.sh /path/to/repo ~/.copilot

# Test Pi.dev renderer
python3 ./renderer/scripts/render-pi-dev.py /path/to/repo ~/.pi
```

### Automated Testing

```bash
# Run hook installation tests
pytest tests/test_hooks_rendering_integration.py -v

# Run all hook tests
pytest tests/test_*_hook.py -v
```

### Verification

```bash
# Check if hooks are installed
git config core.hooksPath
# Expected output: .githooks

# Check hook executability
ls -la .githooks/
# Expected: all files should have x permission

# Test hook execution
git commit --allow-empty -m "test commit"
# Should see: ✅ pre-commit: all checks passed
# Should see: ✅ commit-msg: message format OK
```

## Harness-Specific Considerations

### OpenCode
- Runs in-harness via polling loop
- Hooks are enforced for all commits to the repository
- No special harness-specific hook behavior

### Claude Code
- Runs in VS Code extension
- Hooks are enforced for all commits to the repository
- No special harness-specific hook behavior

### GitHub Copilot
- Runs in VS Code extension (GitHub Copilot Chat)
- Hooks are enforced for all commits to the repository
- No special harness-specific hook behavior

### Pi.dev
- Runs in terminal with interactive agent
- Hooks are enforced for all commits to the repository
- Repo discovery algorithm handles non-standard directory structures

## Troubleshooting

### Hooks Not Running

**Problem:** Hooks are not being executed on commit/push

**Solution:**
1. Verify hooks are installed: `git config core.hooksPath`
2. Check hooks are executable: `ls -la .githooks/`
3. Re-run renderer: `./renderer/scripts/render-opencode.sh /path/to/repo ~/.config/opencode`

### Permission Denied on Hooks

**Problem:** `Permission denied: .githooks/pre-commit`

**Solution:**
1. Make hooks executable: `chmod +x .githooks/*`
2. Or re-run renderer (which does this automatically)

### Hooks Not Found

**Problem:** Git can't find hooks directory

**Solution:**
1. Verify `.githooks/` directory exists
2. Check `core.hooksPath` configuration: `git config core.hooksPath`
3. Should be `.githooks` (relative path from repo root)

### Pi.dev Repo Discovery Fails

**Problem:** Pi.dev renderer can't find git repository

**Solution:**
1. Ensure you're running from within a git repository
2. Check that `.git/` directory exists in repository root
3. Verify path is correct when calling renderer

## Implementation Details

### Hook Installation Code Patterns

**Bash Renderers (OpenCode, Claude, Copilot):**
```bash
if [ -d "$REPO_ROOT/.githooks" ]; then
    echo "📦 Installing git hooks from $REPO_ROOT/.githooks/..."
    git -C "$REPO_ROOT" config core.hooksPath .githooks
    for hook in "$REPO_ROOT"/.githooks/*; do
        [ -f "$hook" ] && chmod +x "$hook"
    done
    echo "✅ Git hooks installed (core.hooksPath = .githooks)"
else
    echo "⚠️  git hooks not found at $REPO_ROOT/.githooks — skipping"
fi
```

**Python Renderer (Pi.dev):**
```python
def _install_git_hooks(self) -> bool:
    """Install git hooks from source repo"""
    # Discover repo root
    repo_root = self.src_dir
    while repo_root != repo_root.parent:
        if (repo_root / ".git").exists():
            break
        repo_root = repo_root.parent
    
    hooks_dir = repo_root / ".githooks"
    if not hooks_dir.exists():
        return False
    
    # Configure git
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "core.hooksPath", ".githooks"],
        check=True
    )
    
    # Make executable
    for hook_file in hooks_dir.glob("*"):
        if hook_file.is_file():
            hook_file.chmod(0o755)
    
    return True
```

## Future Enhancements

1. **Hook Customization:** Allow harness-specific hook configurations
2. **Hook Versioning:** Track hook versions and auto-update
3. **Hook Metrics:** Collect statistics on hook execution
4. **Conditional Hooks:** Enable/disable hooks per harness
5. **Hook Chaining:** Support multiple hook implementations
