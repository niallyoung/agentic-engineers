# Harness Implementations — Final Summary (2026-05-16)

**Date:** 2026-05-16  
**Last Updated:** 2026-05-16  
**Status:** Post-improvements (all 6 recommended improvements addressed)

---

## Executive Summary

The agentic-engineers framework provides four harness renderers that translate canonical agent and skill definitions into platform-specific configuration directories. As of 2026-05-16, all four harnesses are in good shape following a comprehensive review and improvement cycle.

**Key outcomes:**
- All 4 harnesses install correctly and are idempotent
- All 4 harnesses have uninstall support and foreign-file protection
- Documentation quality equalized across harnesses
- Copilot CLI limitation (skills only) clearly documented
- π.dev source files synced to canonical 8-role model
- Shared code extracted to `renderer/scripts/lib.sh`
- Repository root cleaned of historical documents

---

## Comparison Table (Post-Improvements)

| Feature | π.dev | OpenCode | Claude Code | Copilot CLI |
|---------|:-----:|:--------:|:-----------:|:-----------:|
| Agents rendered | ⚠️ Static | ✅ Dynamic | ✅ Dynamic | ❌ Not supported |
| Skills rendered | ❌ None | ✅ 14 skills | ✅ 14 skills | ✅ 14 skills |
| Config file managed | ⚠️ Static | ✅ Managed | ❌ N/A | ❌ N/A |
| Global rules file | ⚠️ Static | ✅ Managed | ❌ N/A | ❌ N/A |
| Model mapping | ✅ Current IDs | ✅ Full qualified | ✅ Tier names | ❌ N/A |
| Canonical 8 roles | ✅ Yes | ✅ Yes | ✅ Yes | ❌ N/A |
| Marker/sentinel safety | ⚠️ Partial | ✅ Full | ✅ Full | ✅ Skills only |
| Uninstall support | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Skills only |
| Status/drift detection | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Foreign file protection | ⚠️ Partial | ✅ Full | ✅ Full | ✅ Skills only |
| docs/AGENTS.md lookup | ❌ Manual | ✅ Yes | ❌ Frontmatter | ❌ N/A |
| Dedicated install guide | ✅ PI-DEV-RENDERER.md | ✅ OPENCODE-INSTALL.md | ✅ CLAUDE-INSTALL.md | ⚠️ Inline only |
| Speculative features marked | ✅ Yes | N/A | N/A | N/A |
| Shared lib.sh functions | ✅ N/A | ✅ Yes | ✅ Yes | ✅ Yes |

---

## Detailed Status: Each Harness

### π.dev Harness

**Architecture:** Python renderer (`render-pi-dev.py`) + Bash wrapper (`render-pi.sh`) copies manually-maintained files from `renderer/pi-dev-src/` to `~/.pi/agent/`.

**Current Status (post-improvements):**
- ✅ Source files updated to canonical 8-role model
- ✅ Model IDs updated to current versions (`claude-haiku-4-5`, `claude-sonnet-4-6`, etc.)
- ✅ Speculative features clearly marked in `pi.yml` and `settings.json`
- ✅ `SUB_AGENT_SETUP.md` updated with known limitations and troubleshooting
- ✅ Hardcoded user paths removed from documentation

**Remaining Limitations:**
- No content transformation — files are copied verbatim (not generated from `src/agents/`)
- Sub-agent routing in `pi.yml` is unverified against actual pi.dev runtime
- `settings.json` extensions/packages/skills are speculative
- Python renderer argument parsing heuristic is fragile (known bug, low priority)
- `agent_dir` created in `__init__` before mode is known (known bug, low priority)

**Compliance:** ✅ Medium (correct for what it does; limitations clearly documented)

---

### OpenCode Harness

**Architecture:** Bash script (`render-opencode.sh`) transforms `src/agents/` and `src/skills/` into OpenCode-format files with hybrid metadata from `docs/AGENTS.md`.

**Current Status:**
- ✅ Most complete and production-ready harness
- ✅ Managed `opencode.jsonc` with JSONC sentinel
- ✅ Managed `AGENTS.md` with HTML comment sentinel
- ✅ 8 agents with fully-qualified `github-copilot/` model IDs
- ✅ 14 skills with per-skill marker files
- ✅ Hybrid metadata strategy (docs/AGENTS.md + src frontmatter)
- ✅ Atomic agent manifest with `.tmp` + `mv`
- ✅ Comprehensive `OPENCODE-INSTALL.md` documentation
- ✅ Now sources shared `lib.sh` (eliminates duplication)

**Remaining Limitations:**
- Provider hardcoded to `github-copilot/` (users with `anthropic/` provider need different IDs)
- `docs/AGENTS.md` table parser is fragile to format changes
- No rollback on partial failure for skills

**Compliance:** ✅ High

---

### Claude Code Harness

**Architecture:** Bash script (`render-claude.sh`) transforms `src/agents/` and `src/skills/` into Claude Code-format files using tier-name model mapping.

**Current Status (post-improvements):**
- ✅ 8 agents with tier-name model IDs (`haiku`, `sonnet`, `opus`)
- ✅ 14 skills with per-skill marker files
- ✅ Agent manifest with `.tmp` + `mv` atomicity
- ✅ Foreign file protection identical to OpenCode harness
- ✅ New `docs/CLAUDE-INSTALL.md` documentation (mirrors OPENCODE-INSTALL.md quality)
- ✅ Now sources shared `lib.sh` (eliminates ~50 lines of duplication)

**Remaining Limitations:**
- Simplified model mapping (tier names only; no version distinction)
- No `docs/AGENTS.md` lookup (reads from source frontmatter only)
- No config file or global rules file (Claude Code uses `CLAUDE.md` pattern)

**Compliance:** ✅ High

---

### Copilot CLI Harness

**Architecture:** Bash script (`render-copilot.sh`) syncs skills from `src/skills/` to `~/.copilot/skills/`. Skills only — Copilot CLI does not support custom agents.

**Current Status (post-improvements):**
- ✅ 14 skills installed with per-skill marker files
- ✅ Makefile inconsistency resolved — both root and renderer Makefile now install skills only
- ✅ Clear documentation that agents are not supported
- ✅ `render-copilot-agents.py` legacy renderer NOT invoked (skills only)

**Remaining Limitations:**
- No agents (intentional — Copilot CLI platform limitation)
- No dedicated install guide (inline documentation only)
- `render-copilot-agents.py` still exists as legacy/experimental code

**Compliance:** ✅ Medium-High (correct for platform capabilities)

---

## Recommendations for Users

### Which Harness to Use

| Scenario | Recommended Harness |
|----------|---------------------|
| Full agent orchestration with all 8 roles | **OpenCode** |
| Claude Code users | **Claude Code** |
| GitHub Copilot CLI users (skills only) | **Copilot CLI** |
| pi.dev users | **π.dev** (with awareness of limitations) |
| All platforms | Run `make install` to install all 4 |

### Installation

```bash
# Install all 4 harnesses
make install

# Install specific harness
make install-opencode    # OpenCode → ~/.config/opencode/
make install-claude      # Claude Code → ~/.claude/
make install-copilot     # Copilot CLI → ~/.copilot/ (skills only)
make install-pi          # π.dev → ~/.pi/agent/

# Check status
make status

# Uninstall
make uninstall-all
```

### Known Limitations (Remaining)

1. **π.dev sub-agent routing is speculative** — The `pi.yml` routing rules may have no effect in the actual pi.dev runtime. Use the DELEGATE pattern manually.

2. **OpenCode provider hardcoded to `github-copilot/`** — Users with the `anthropic/` provider need to edit `render-opencode.sh` or wait for auto-detection feature.

3. **Claude Code uses tier names** — `haiku`, `sonnet`, `opus` resolve to latest version of each tier; no version-specific control.

4. **Copilot CLI agents not supported** — Only skills are installed. Use OpenCode or Claude Code for full agent support.

---

## Compliance Status

| Requirement | π.dev | OpenCode | Claude Code | Copilot CLI |
|-------------|:-----:|:--------:|:-----------:|:-----------:|
| Canonical 8 roles | ✅ | ✅ | ✅ | N/A |
| Current model IDs | ✅ | ✅ | ✅ (tiers) | N/A |
| SPEC.md layout | ⚠️ | ✅ | ✅ | ✅ |
| Idempotent installs | ✅ | ✅ | ✅ | ✅ |
| Foreign file protection | ⚠️ Partial | ✅ | ✅ | ✅ |
| Uninstall support | ✅ | ✅ | ✅ | ✅ |
| Dedicated documentation | ✅ | ✅ | ✅ | ⚠️ |

---

## Files Changed in This Improvement Cycle

### Created
- `docs/CLAUDE-INSTALL.md` — Claude Code installation guide
- `renderer/scripts/lib.sh` — Shared Bash functions
- `docs/archive/README.md` — Archive index
- `HARNESS-FINAL-SUMMARY.md` — This document

### Updated
- `renderer/pi-dev-src/SYSTEM.md` — 8 canonical roles, current model IDs
- `renderer/pi-dev-src/AGENTS.md` — 8 canonical roles (removed Spec/Healing Engineer)
- `renderer/pi-dev-src/settings.json` — Current model ID, speculative features marked
- `renderer/pi-dev-src/pi.yml` — 8 canonical roles, speculative features clearly marked
- `renderer/pi-dev-src/SUB_AGENT_SETUP.md` — Known limitations, troubleshooting, generic paths
- `Makefile` — Copilot CLI limitation documented in install-copilot target
- `renderer/Makefile` — install-copilot now skills only (removed agent renderer invocation)
- `renderer/scripts/render-claude.sh` — Sources lib.sh, removed duplicated functions
- `renderer/scripts/render-opencode.sh` — Sources lib.sh, removed duplicated functions
- `HARNESS-REVIEW.md` — Added "Improvements Made" section, updated compliance status

### Moved to docs/archive/
- `ANALYSIS_PI_INTEGRATION.md`
- `PI_INTEGRATION_FILES.md`
- `PI_INTEGRATION_SUMMARY.md`
- `PI-DEV-INTEGRATION.md`
- `PROTOCOL-ANALYSIS.md`
- `RESTRUCTURE-DESIGN.md`
- `RESTRUCTURE-FINAL-REPORT.md`
- `PHASE-4-HANDBACK.md`

### Moved to src/skills/_archive/
- `engineer-agent.md`, `lead-engineer-agent.md`, `model-engineer-agent.md`
- `principal-engineer-agent.md`, `security-agent.md`, `senior-engineer-agent.md`
- `spec-engineer-agent.md`, `healing-agent.md`

### Deleted
- `src/skills/.SDLC-ORCHESTRATOR-DIAGRAMS.md.swp` (vim swap file)

---

## See Also

- [HARNESS-REVIEW.md](./HARNESS-REVIEW.md) — Detailed per-harness analysis
- [docs/OPENCODE-INSTALL.md](./OPENCODE-INSTALL.md) — OpenCode installation guide
- [docs/CLAUDE-INSTALL.md](./CLAUDE-INSTALL.md) — Claude Code installation guide
- [renderer/PI-DEV-RENDERER.md](../renderer/PI-DEV-RENDERER.md) — π.dev renderer documentation
- [README.md](../README.md) — Repository overview
