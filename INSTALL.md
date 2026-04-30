# Installation Guide — Agentic Engineers

Platform-specific installation to `~/.claude/` or `~/.copilot/`

## Quick Start

### Claude
```bash
cd /path/to/agentic-engineers
./scripts/install-claude.sh
```

### Copilot
```bash
cd /path/to/agentic-engineers
./scripts/install-copilot.sh
```

### Both
```bash
cd /path/to/agentic-engineers
make install-all
```

---

## Installation Targets

| Target | Action | Location |
|--------|--------|----------|
| `./scripts/install-claude.sh` | Install/update | `~/.claude/` |
| `./scripts/install-copilot.sh` | Install/update | `~/.copilot/` |
| `make install-claude` | Alias for above | `~/.claude/` |
| `make install-copilot` | Alias for above | `~/.copilot/` |
| `make install-all` | Install both | `~/.claude/` + `~/.copilot/` |

---

## Script Operations

Each install script supports three operations:

### 1. Install (default)
```bash
./scripts/install-claude.sh install
./scripts/install-claude.sh        # same thing
```

**Behavior:**
- Creates target directory (`~/.claude/` or `~/.copilot/`)
- Backs up existing installation with timestamp if it was previously managed
- Copies rendered agents and config from `dist/claude/` or `dist/copilot/`
- Writes installation marker (`.agentic-engine{service-name}`)
- Shows file count and next steps

**If directory exists but NOT managed:**
- Prompts: "Overwrite? (y/N)"
- Requires explicit confirmation to proceed

### 2. Uninstall
```bash
./scripts/install-claude.sh --uninstall
./scripts/install-copilot.sh --uninstall
```

**Behavior:**
- Removes installation only if marked as managed by agentic-engineers
- Leaves any non-managed installations untouched
- Shows count of files removed

### 3. Status
```bash
./scripts/install-claude.sh --status
./scripts/install-copilot.sh --status
```

**Behavior:**
- Shows installation location
- Shows installation date (from marker file)
- Shows number of roles installed
- Returns exit code 0 if installed, 1 if not

**Makefile alias:**
```bash
make status       # Shows both
make status-claude    # Claude only
make status-copilot   # Copilot only
```

---

## Render Targets

Generate provider-specific agent definitions in `dist/` from source:

```bash
make render-claude       # Generate dist/claude/
make render-copilot      # Generate dist/copilot/
make render-all          # Both
```

**Current behavior:**
- Copies all `orchestration/agents/*.md` files to `dist/{provider}/roles/`
- Creates provider-specific manifest (basic for now)

**Future enhancement:**
- Python render pipeline with model substitution
- Provider capability analysis (delta warnings for unsupported features)
- Optimized prompt lengths per provider

---

## Troubleshooting

### "dist/claude/ not found"
```bash
make render-claude
./scripts/install-claude.sh
```

### "~/.claude/ exists but not managed"
The directory exists from a previous installation, but doesn't have the agentic-engineers marker. You have two options:

1. **Overwrite (recommended if upgrading):**
   ```bash
   ./scripts/install-claude.sh  # Will prompt for confirmation
   ```

2. **Clean first:**
   ```bash
   rm -rf ~/.claude/
   ./scripts/install-claude.sh
   ```

3. **Use a different location:**
   - Edit the script and change `CLAUDE_DIR` (not recommended)

### "No agentic-engineers installation found"
This is normal if you haven't installed yet. Run:
```bash
./scripts/install-claude.sh
```

### Installation successful but files look wrong
1. Verify the source files exist:
   ```bash
   ls orchestration/agents/ | head -5
   ```

2. Verify rendering:
   ```bash
   make render-claude
   ```

3. Check the installation:
   ```bash
   ls -la ~/.claude/
   cat ~/.claude/.agentic-engine{service-name}
   ```

---

## Installation Flow

```
[User] make install-claude
           ↓
[Script] Check prerequisites (dist/claude/ exists?)
           ↓
[Script] Check if ~/.claude/ already exists
           ├─ YES: Is it managed? ─ YES → Backup existing
           │                      └─ NO  → Prompt user
           └─ NO: Create directory
           ↓
[Script] Copy files from dist/claude/ → ~/.claude/
           ↓
[Script] Write .agentic-engine{service-name} marker
           ↓
[Script] Report: installed, file count, next steps
           ↓
[User] ~/.claude/README.md for usage instructions
```

---

## Backup Management

When you run `install-claude.sh` or `install-copilot.sh` and an installation already exists:

1. **If managed by agentic-engineers:**
   - Backs up to `~/.claude.backup.TIMESTAMP/` or `~/.copilot.backup.TIMESTAMP/`
   - Backs up before overwriting
   - Shows backup location

2. **If NOT managed:**
   - Prompts user for confirmation
   - Does NOT create backup (user controls it)

**To restore a backup:**
```bash
rm ~/.claude
mv ~/.claude.backup.20260430_182101 ~/.claude
```

---

## Architecture

```
Repo: agentic-engineers/
├── orchestration/agents/*.md      ← Source definitions (14 agents)
├── dist/
│   ├── claude/roles/*.md          ← Rendered for Claude
│   └── copilot/roles/*.md         ← Rendered for Copilot
└── scripts/
    ├── install-claude.sh          ← Installs dist/claude/ → ~/.claude/
    └── install-copilot.sh         ← Installs dist/copilot/ → ~/.copilot/

Installation targets:
├── ~/.claude/                     ← Claude harness (managed)
│   ├── roles/
│   ├── config/
│   ├── README.md
│   └── .agentic-engine{service-name}
└── ~/.copilot/                    ← Copilot harness (managed)
    ├── roles/
    ├── config/
    ├── README.md
    └── .agentic-engine{service-name}

Old (abandoned):
    ~/.agents/agentic-engineers/  ← No longer used
```

---

## For CI/CD

Automated installation in GitHub Actions or other CI:

```bash
# Non-interactive install (assumes dist/claude/ exists)
./scripts/install-claude.sh install

# Check status
./scripts/install-claude.sh --status
```

The scripts are fully idempotent when dist/ files don't change.

---

## Verification

After installation, verify files are in place:

```bash
# Claude
ls ~/.claude/roles/ | wc -l         # Should show number of roles
cat ~/.claude/.agentic-engine{service-name}  # Installation timestamp

# Copilot  
ls ~/.copilot/roles/ | wc -l        # Should show number of roles
cat ~/.copilot/.agentic-engine{service-name} # Installation timestamp
```

---

**See also:**
- [README.md](README.md) — Project overview
- [WORKFLOW.md](WORKFLOW.md) — Agent communication diagrams
- [QUICK-REFERENCE.md](QUICK-REFERENCE.md) — One-page architecture guide
