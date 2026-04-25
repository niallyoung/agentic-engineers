# Global Enforcement Infrastructure

Centralized Copilot CLI enforcement: hooks, scripts, and global instructions for all ERS repos.

**Location**: `~/git/ers/agentic-engineers/enforcement/`
**Installed to**: `~/.github/` (via symlinks)

## Structure

```
enforcement/
├── hooks/                    — Copilot CLI hook definitions
│   ├── guard.json           — preToolUse (blocks --no-verify, destructive ops, hook tampering)
│   └── session-init.json    — sessionStart (displays init messages)
│
├── scripts/                  — Enforcement logic and session init
│   ├── copilot-guard.sh     — Enforces CLI rules (preToolUse handler)
│   └── copilot-session-init.sh — Session start display
│
├── instructions/             — Global Copilot CLI instructions
│   └── copilot-instructions.md
│
├── workflows/                — Reusable GitHub Actions templates
│   └── ci.yml
│
├── shared.mk                 — Common Makefile targets (included by repo Makefiles)
├── Makefile                  — Install/uninstall logic
└── README.md                 — This file
```

## Installation

### First Time Setup

```bash
cd ~/git/ers/agentic-engineers/enforcement
make install
```

This creates symlinks:
- `hooks/` → `~/.github/hooks/`
- `scripts/` → `~/.github/scripts/`
- `copilot-instructions.md` → `~/.github/copilot-instructions.md`
- `shared.mk` → `~/.github/shared.mk`

### Verify Installation

```bash
make status
```

Shows all symlink targets and their health.

## Usage

All ERS repos inherit global enforcement automatically:
- Copilot CLI preToolUse hook validates all tool invocations
- Session start hook displays enforcement rules
- Git hooks (pre-commit, pre-push, commit-msg) delegate to Makefile targets
- `shared.mk` provides common targets for all repos

## Updating Enforcement Rules

Edit files in place:
- `hooks/*.json` — Change hook configuration
- `scripts/*.sh` — Change enforcement logic
- `instructions/copilot-instructions.md` — Update global instructions

Changes take effect immediately (symlinks reflect updates).

## Uninstall

```bash
make uninstall
```

Removes all symlinks from `~/.github/`. Repos will lose enforcement but continue functioning.

## History

**Previous location**: `~/git/ers/{service-name}/` (migrated Apr 2026)
- Consolidated all global enforcement into single agentic-engineers directory
- Symlink mechanism unchanged
- No functional changes to enforcement rules or scripts
