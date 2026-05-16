# SDLC Hooks — Enforcement Reference

**Last Updated:** 2026-05-16  
**Scope:** agentic-engineers SDLC enforcement via git hooks and OpenCode commands

---

## Overview

The agentic-engineers framework enforces the DELEGATE → Agent Work → HANDBACK → QE Review SDLC workflow through two complementary mechanisms:

1. **Git hooks** (`.githooks/`) — commit-time enforcement for the repo itself
2. **OpenCode commands** (`.opencode/commands/`) — workflow shortcuts and status checks

---

## Git Hooks

All hooks live in `.githooks/` and are activated via:
```bash
git config core.hooksPath .githooks
```

This is automatically configured by `make install` / `renderer/scripts/render-opencode.sh`.

### Emergency Bypass

```bash
SKIP_HOOKS=1 git commit -m "emergency: <reason>"
```

Document the reason in the commit message. `commit-msg` hook still runs.

---

### `pre-commit`

**Trigger:** Before every `git commit`

| Check | Rule | Severity |
|-------|------|----------|
| SPEC constraint | No `.py`/`.sh` in `orchestration/scripts/` | ❌ BLOCK |
| SPEC constraint | No `.cron` in `orchestration/config/` | ❌ BLOCK |
| Secret detection | No API keys, AWS keys, passwords in staged files | ❌ BLOCK |
| YAML validity | Staged `.yaml`/`.yml` files must be valid YAML | ❌ BLOCK |
| JSON validity | Staged `.json`/`.jsonc` files must be valid JSON | ⚠️ WARN |
| Bypass markers | `--no-verify` or `SKIP_HOOKS=1` in committed code | ⚠️ WARN |

---

### `commit-msg`

**Trigger:** After commit message is written

| Check | Rule | Severity |
|-------|------|----------|
| Non-empty | Message must not be empty | ❌ BLOCK |
| Minimum length | First line ≥ 10 characters | ❌ BLOCK |
| Bypass documentation | If `SKIP_HOOKS` mentioned, reason must be documented | ❌ BLOCK |

---

### `pre-push`

**Trigger:** Before `git push`

| Check | Rule | Severity |
|-------|------|----------|
| Protected branch | Warn when pushing to `main`/`master` | ⚠️ WARN |
| Agent YAML | Frontmatter in `src/agents/*.md` must be valid YAML | ❌ BLOCK |
| Test suite | `pytest tests/` (if pytest and tests/ exist) | ⚠️ WARN |

---

## OpenCode Commands

Available in the TUI via `/command-name`:

| Command | Description | Agent |
|---------|-------------|-------|
| `/sdlc-check` | Full SDLC compliance check (queue, DELEGATEs, hooks) | orchestrator |
| `/hooks-install` | Install/verify git enforcement hooks | — |
| `/queue-status` | Review pending DELEGATEs and HANDBACKs | orchestrator |

---

## Cross-Harness Support Matrix

| Enforcement Point | OpenCode | Claude Code | Copilot CLI | π.dev |
|-------------------|----------|-------------|-------------|-------|
| Git pre-commit | ✅ `.githooks/pre-commit` | ✅ same repo hooks | ✅ same repo hooks | ✅ same repo hooks |
| Git commit-msg | ✅ `.githooks/commit-msg` | ✅ same | ✅ same | ✅ same |
| Git pre-push | ✅ `.githooks/pre-push` | ✅ same | ✅ same | ✅ same |
| Session guard (preToolUse) | ❌ no native hook | ❌ no native hook | ✅ `copilot-guard.sh` | ❌ no native hook |
| Session init | ❌ AGENTS.md rules | ❌ CLAUDE.md rules | ✅ `copilot-session-init.sh` | ❌ SYSTEM.md rules |
| SDLC commands | ✅ `.opencode/commands/` | ❌ not supported | ❌ not supported | ❌ not supported |
| Auto hook install | ✅ `render-opencode.sh` | ❌ manual | ❌ manual | ❌ manual |

**Notes:**
- Git hooks apply to all harnesses equally (they're repo-level, not tool-level)
- Copilot CLI has the strongest runtime enforcement via `preToolUse` hooks
- OpenCode has the richest workflow commands via `.opencode/commands/`
- Claude Code and π.dev rely on instruction-level rules (CLAUDE.md / SYSTEM.md)

---

## Workflow Enforcement Points

```
User Request
     │
     ▼
[OpenCode /sdlc-check]  ← manual compliance check
     │
     ▼
Orchestrator (queue routing)
     │
     ▼
DELEGATE → Agent Work
     │
     ▼
HANDBACK → QE Review
     │
     ▼
git commit ──► [pre-commit hook]  ← SPEC compliance, secrets, YAML
     │              │
     │         [commit-msg hook]  ← message format
     │
     ▼
git push ───► [pre-push hook]    ← agent YAML, tests
```

---

## Installation

### Automatic (recommended)

```bash
make install          # renders all harnesses + configures git hooks
```

### Manual

```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/commit-msg .githooks/pre-push
```

### Verify

```bash
git config core.hooksPath   # should return: .githooks
ls -la .githooks/            # should show all 3 hooks as executable
```

Or use the OpenCode command:
```
/sdlc-check
```

---

## Troubleshooting

**Hook not running:**
```bash
git config core.hooksPath   # check if set
git config core.hooksPath .githooks  # fix
```

**YAML validation failing:**
- Ensure `python3` and `pyyaml` are installed: `pip3 install pyyaml`

**Tests failing on pre-push:**
- Pre-push test failures are warnings (non-blocking) — push proceeds
- Fix tests before merging to main

**Emergency bypass:**
```bash
SKIP_HOOKS=1 git commit -m "emergency: <reason for bypass>"
```
