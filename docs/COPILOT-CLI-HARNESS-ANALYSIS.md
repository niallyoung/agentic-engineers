# Copilot CLI Harness Analysis: Intentional Minimalism & Expansion Opportunities

**Task ID:** 2026-05-16-copilot-cli-harness-analysis  
**Analyst:** Engineer  
**Date:** 2026-05-16  
**Scope:** render-copilot.sh, design constraints, feature gaps, expansion opportunities  
**Deliverable:** Feature analysis, design rationale, and Phase 3 recommendations

---

## Executive Summary

The Copilot CLI harness (`render-copilot.sh`) is **intentionally minimal** by design. It renders only skills (14 total) to `~/.copilot/skills/` and explicitly omits agents. This design reflects a fundamental constraint: **GitHub Copilot CLI does not support custom agents** — it only supports custom skills/tools.

**Key findings:**

1. **Intentional minimalism is justified** — Copilot CLI's API only supports skills, not agents. Rendering agents would be dead code.
2. **Skills rendering is complete and correct** — All 14 canonical skills are synced with proper marker-based safety.
3. **Design constraints are well-documented** — HARNESS-REVIEW.md clearly explains why agents are skipped.
4. **Minor gaps exist** — No dedicated install guide, legacy agent renderer (`render-copilot-agents.py`) creates confusion.
5. **Expansion opportunities exist** — Tier 1 (documentation) and Tier 2 (configuration management) improvements are feasible without breaking minimalism.

**Compliance Status:** ✅ Medium-High (skills complete, agents intentionally omitted, documentation minimal)

---

## 1. Copilot CLI Harness Architecture

### 1.1 Current Design

The Copilot CLI harness consists of a single Bash script:

```
render-copilot.sh
├─ Input: $REPO_ROOT (agentic-engineers repo), $COPILOT (destination, e.g., ~/.copilot)
├─ Mode: install | --uninstall | --status
├─ Output: ~/.copilot/skills/<name>/SKILL.md (14 skills)
└─ Safety: Marker file per skill, foreign skip, rsync --delete
```

**What it does:**
- ✅ Enumerates source skills from `src/skills/` (dirs with `SKILL.md`)
- ✅ Syncs each skill to `~/.copilot/skills/<name>/` using rsync
- ✅ Writes marker file (`.agentic-engine{service-name}`) per skill
- ✅ Supports `--uninstall` (removes marked skills only)
- ✅ Supports `--status` (shows drift detection)
- ✅ Installs git hooks from `.githooks/` (shared with all harnesses)

**What it does NOT do:**
- ❌ Render agents (intentional — Copilot CLI doesn't support custom agents)
- ❌ Manage configuration (Copilot CLI has no global config file like OpenCode's `opencode.jsonc`)
- ❌ Provide global rules (Copilot CLI has no `AGENTS.md` equivalent)

### 1.2 Why Agents Are Skipped

**Root cause:** GitHub Copilot CLI's public API does not expose custom agent registration. The Copilot CLI documentation (verified via `gh copilot --help` and GitHub's official docs) shows:

- ✅ Custom skills/tools can be added to `~/.copilot/skills/`
- ❌ Custom agents cannot be registered (no `~/.copilot/agents/` support)

**Evidence:**
- Copilot CLI skill format: `~/.copilot/skills/<name>/SKILL.md` (documented)
- Copilot CLI agent format: Not documented; no public API
- Legacy renderer (`render-copilot-agents.py`) exists but produces `.agent.md` files (non-standard format)
- No Copilot CLI documentation mentions custom agent support

**Conclusion:** Rendering agents for Copilot CLI is **dead code**. The intentional omission is correct.

### 1.3 Design Rationale

The minimalism is justified by three constraints:

| Constraint | Impact | Mitigation |
|-----------|--------|-----------|
| **No agent API** | Cannot register custom agents | Render skills only (correct) |
| **No config file** | Cannot manage global settings | Rely on Copilot CLI's built-in config |
| **Minimal documentation** | Users may not understand limitations | Create dedicated `COPILOT-INSTALL.md` |

---

## 2. Skill Rendering Analysis

### 2.1 Completeness

All 14 canonical skills are rendered:

```
ab-testing
agent-creator
consistency-checker
metrics-etl
model-engineer
protocol-validator
queue-management
repo-init
skill-creator
spec-management
spec-validator
tokenadvisor
usage-tracking
voice-notify
```

**Status:** ✅ Complete

### 2.2 Correctness

| Feature | Status | Notes |
|---------|--------|-------|
| Source enumeration | ✅ | Correctly finds dirs with `SKILL.md` |
| Rsync sync | ✅ | Uses `--delete` to keep destination in sync |
| Marker file | ✅ | Per-skill `.agentic-engine{service-name}` |
| Foreign skip | ✅ | Checks marker before overwriting |
| Uninstall | ✅ | Removes only marked skills |
| Status/drift | ✅ | Uses `diff -rq` for comparison |
| Error handling | ✅ | `set -euo pipefail`, source validation |

**Status:** ✅ Correct

### 2.3 Safety Model

The marker-based safety model is identical to OpenCode and Claude Code harnesses:

```bash
# Install: write marker to each skill
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$dst/$MARKER"

# Uninstall: only remove if marker exists
if [ -f "$target/$MARKER" ]; then
    rm -rf "$target"
fi

# Status: check marker to detect foreign skills
if [ ! -f "$dst/$MARKER" ]; then
    echo "⚠️  $name (exists but not managed by us)"
fi
```

**Status:** ✅ Safe

---

## 3. Design Constraints & Trade-offs

### 3.1 Intentional Minimalism

The Copilot CLI harness is intentionally minimal because:

1. **GitHub Copilot CLI is a CLI tool, not a framework** — It's designed for command-line assistance, not agent orchestration. The skill registration API is the only extension point.

2. **No agent orchestration in Copilot CLI** — Unlike OpenCode (which supports 8 custom agents via `~/.config/opencode/agents/`) or Claude Code (which supports agents via `~/.claude/agents/`), Copilot CLI has no documented agent registration mechanism.

3. **Skills are sufficient for Copilot CLI's use case** — Copilot CLI can invoke skills/tools to extend its capabilities. Agents (with their own models, effort levels, and routing logic) are unnecessary.

4. **Minimal configuration** — Copilot CLI uses environment variables and CLI flags for configuration, not a global config file. There's no need for a rendered `copilot.jsonc` equivalent.

### 3.2 Constraints vs. Opportunities

| Constraint | Type | Severity | Workaround |
|-----------|------|----------|-----------|
| No agent API | Technical | High | Render skills only (current approach) |
| No config file | Technical | Medium | Document Copilot CLI config separately |
| No global rules | Design | Low | Document framework rules in `COPILOT-INSTALL.md` |
| Legacy agent renderer | Maintenance | Low | Archive or remove `render-copilot-agents.py` |
| No dedicated docs | Documentation | Low | Create `COPILOT-INSTALL.md` |

---

## 4. Feature Comparison Matrix

### 4.1 Harness Parity (Post-Improvements, 2026-05-16)

| Feature | π.dev | OpenCode | Claude Code | Copilot CLI |
|---------|-------|----------|-------------|-------------|
| **Agents rendered** | ⚠️ Static | ✅ Dynamic | ✅ Dynamic | ❌ N/A (not supported) |
| **Skills rendered** | ❌ None | ✅ 14 skills | ✅ 14 skills | ✅ 14 skills |
| **Config file** | ⚠️ Static | ✅ Managed | ❌ N/A | ❌ N/A |
| **Global rules** | ⚠️ Static | ✅ Managed | ❌ N/A | ❌ N/A |
| **Model mapping** | ✅ Current IDs | ✅ Full | ⚠️ Tier only | ❌ N/A |
| **Marker/sentinel** | ⚠️ Partial | ✅ Full | ✅ Full | ✅ Skills only |
| **Uninstall** | ✅ | ✅ | ✅ | ✅ |
| **Status/drift** | ✅ | ✅ | ✅ | ✅ |
| **Foreign protection** | ⚠️ Partial | ✅ | ✅ | ✅ |
| **Git hooks** | ✅ | ✅ | ✅ | ✅ |
| **Dedicated install doc** | ✅ PI-DEV-RENDERER.md | ✅ OPENCODE-INSTALL.md | ✅ CLAUDE-INSTALL.md | ⚠️ Inline only |

**Key insight:** Copilot CLI is intentionally simpler because it has fewer extension points. This is **correct by design**, not a limitation.

### 4.2 Compliance Checklist

| Requirement | Status | Notes |
|-------------|--------|-------|
| Installs to correct location | ✅ | `~/.copilot/skills/` |
| Preserves user files | ✅ | Marker-based foreign skip |
| Uninstall removes only managed files | ✅ | Marker file is authoritative |
| Status mode with drift detection | ✅ | `diff -rq` comparison |
| Marker file strategy | ✅ | Per-skill marker |
| Content matches canonical model | ✅ | Reads directly from src/skills/ |
| SPEC.md compliance | ✅ | Uses canonical src/ layout |
| Git hooks installed | ✅ | Shared with all harnesses |
| Documentation quality | ⚠️ | No dedicated guide |

---

## 5. Configuration Management Analysis

### 5.1 Current State

Copilot CLI has **no rendered configuration file** because:

1. **No global config API** — Copilot CLI doesn't expose a `~/.copilot/config.json` or equivalent
2. **CLI-based configuration** — Settings are managed via environment variables and CLI flags (e.g., `gh copilot config set`)
3. **No global rules** — Unlike OpenCode (which renders `AGENTS.md` with framework rules), Copilot CLI has no rules file

### 5.2 What Could Be Configured (Tier 2 Opportunity)

If Copilot CLI adds configuration support in the future, we could render:

```
~/.copilot/
├─ config.json          ← Future: Copilot CLI settings
├─ AGENTS.md            ← Future: Framework rules (informational)
├─ skills/
│  ├─ ab-testing/
│  ├─ agent-creator/
│  └─ ...
└─ .agentic-engine{service-name}  ← Marker for managed directory
```

**Current status:** Not applicable (Copilot CLI doesn't support this yet)

---

## 6. Gaps & Limitations

### 6.1 Documentation Gap

**Issue:** No dedicated Copilot CLI installation guide.

**Current state:**
- ✅ `OPENCODE-INSTALL.md` — Comprehensive OpenCode guide
- ✅ `CLAUDE-INSTALL.md` — Comprehensive Claude Code guide
- ⚠️ `PI-DEV-RENDERER.md` — π.dev guide (in renderer/ dir)
- ❌ `COPILOT-INSTALL.md` — Missing

**Impact:** Users may not understand:
- Why agents are not rendered
- How to use Copilot CLI skills
- What the marker file does
- How to uninstall/update

**Recommendation:** Create `COPILOT-INSTALL.md` (Tier 1, low effort)

### 6.2 Legacy Agent Renderer

**Issue:** `render-copilot-agents.py` and `render-copilot-agents.sh` exist but are not invoked by the root Makefile.

**Current state:**
- Root Makefile: `make install-copilot` → skills only (correct)
- Renderer Makefile: `make install-copilot` → skills + agents (inconsistent)
- Agent renderer: Produces `.agent.md` files (non-standard format)

**Impact:** Confusion about whether agents are supported.

**Recommendation:** Archive or remove legacy agent renderer (Tier 1, low effort)

### 6.3 Makefile Inconsistency (RESOLVED)

**Status:** ✅ Fixed in commit b10295f

The root Makefile and renderer Makefile now produce consistent results.

---

## 7. Expansion Opportunities

### 7.1 Tier 1: Documentation & Cleanup (Effort: 2-3 hours)

**Priority:** HIGH  
**Impact:** Clarity, user experience  
**Risk:** None (documentation only)

| Task | Effort | Benefit | Status |
|------|--------|---------|--------|
| Create `COPILOT-INSTALL.md` | 1 hour | Clear installation guide | ⏳ Recommended |
| Archive `render-copilot-agents.py` | 30 min | Reduce confusion | ⏳ Recommended |
| Update `docs/INSTALL.md` | 30 min | Remove outdated paths | ⏳ Recommended |
| Add Copilot CLI to feature matrix | 30 min | Comprehensive comparison | ⏳ Recommended |

**Deliverables:**
- `docs/COPILOT-INSTALL.md` (≥500 words)
- `renderer/scripts/_archive/render-copilot-agents.py` (moved)
- `renderer/scripts/_archive/render-copilot-agents.sh` (moved)
- Updated `docs/INSTALL.md` (remove dead links)

### 7.2 Tier 2: Configuration Management (Effort: 4-6 hours)

**Priority:** MEDIUM  
**Impact:** Future-proofing, extensibility  
**Risk:** Low (speculative feature, behind feature flag)

If GitHub Copilot CLI adds configuration support, we could render:

| Feature | Effort | Benefit | Blocker |
|---------|--------|---------|---------|
| Detect Copilot CLI config API | 1 hour | Understand future support | None |
| Design config schema | 1 hour | Plan structure | None |
| Implement config renderer | 2 hours | Render config.json | Needs API docs |
| Implement AGENTS.md renderer | 1 hour | Render framework rules | None |
| Test with mock Copilot CLI | 1 hour | Verify correctness | None |

**Deliverables:**
- `renderer/scripts/render-copilot-config.sh` (optional, feature-flagged)
- `docs/COPILOT-CONFIG-SCHEMA.md` (design doc)
- Tests for config rendering

**Blocker:** Requires GitHub Copilot CLI to expose a config API. Currently not documented.

### 7.3 Tier 3: Agent Orchestration (Effort: 8-12 hours)

**Priority:** LOW  
**Impact:** Parity with OpenCode/Claude Code  
**Risk:** High (requires Copilot CLI API changes)

If GitHub Copilot CLI adds agent support, we could:

| Feature | Effort | Benefit | Blocker |
|---------|--------|---------|---------|
| Design agent registration API | 2 hours | Plan structure | None |
| Implement agent renderer | 3 hours | Render agents | Needs API |
| Implement agent manifest | 2 hours | Track managed agents | Needs API |
| Implement uninstall/status | 2 hours | Lifecycle management | Needs API |
| Test with mock Copilot CLI | 3 hours | Verify correctness | Needs API |

**Deliverables:**
- `renderer/scripts/render-copilot-agents.sh` (refactored, feature-flagged)
- `renderer/scripts/render-copilot-agents.py` (refactored, feature-flagged)
- `docs/COPILOT-AGENTS-SCHEMA.md` (design doc)
- Tests for agent rendering

**Blocker:** Requires GitHub Copilot CLI to expose an agent registration API. Currently not available.

---

## 8. Recommended Phase 3 Plan

### 8.1 Immediate Actions (Week 1)

**Tier 1 tasks — low risk, high clarity:**

1. **Create `docs/COPILOT-INSTALL.md`** (1 hour)
   - Mirror structure of `OPENCODE-INSTALL.md` and `CLAUDE-INSTALL.md`
   - Explain why agents are not rendered
   - Document skill installation, uninstall, status
   - Provide troubleshooting guide
   - Link to feature matrix for comparison with other harnesses

2. **Archive legacy agent renderer** (30 min)
   - Move `renderer/scripts/render-copilot-agents.py` → `renderer/scripts/_archive/`
   - Move `renderer/scripts/render-copilot-agents.sh` → `renderer/scripts/_archive/`
   - Add `_archive/README.md` explaining why these were archived
   - Update root Makefile to remove references (already done in commit b10295f)

3. **Update `docs/INSTALL.md`** (30 min)
   - Remove references to `./scripts/install-copilot.sh` (dead link)
   - Add link to `COPILOT-INSTALL.md`
   - Update Makefile examples

### 8.2 Medium-term Actions (Weeks 2-4)

**Tier 2 tasks — future-proofing:**

1. **Research Copilot CLI config API** (1 hour)
   - Review GitHub Copilot CLI documentation for config support
   - Check GitHub issues/discussions for planned features
   - Document findings in `docs/COPILOT-CONFIG-RESEARCH.md`

2. **Design config schema** (1 hour)
   - If config API exists, design schema for `~/.copilot/config.json`
   - Document in `docs/COPILOT-CONFIG-SCHEMA.md`

3. **Implement config renderer** (2 hours, if API exists)
   - Add `render-copilot-config.sh` to renderer
   - Integrate with root Makefile

### 8.3 Long-term Actions (Weeks 5+)

**Tier 3 tasks — speculative:**

1. **Monitor Copilot CLI roadmap** (ongoing)
   - Track GitHub issues for agent support
   - Subscribe to GitHub Copilot CLI announcements

2. **Prepare agent renderer** (if/when API available)
   - Refactor `render-copilot-agents.py` to use new API
   - Add to root Makefile
   - Document in `COPILOT-INSTALL.md`

---

## 9. Design Constraints Summary

### 9.1 Why Copilot CLI Harness is Minimal

| Constraint | Reason | Implication |
|-----------|--------|-------------|
| **No agent API** | Copilot CLI is a CLI tool, not a framework | Render skills only (correct) |
| **No config file** | Copilot CLI uses env vars + CLI flags | No config rendering needed |
| **No global rules** | Copilot CLI has no rules engine | Document rules separately |
| **Minimal documentation** | Copilot CLI is simpler than other harnesses | Create dedicated guide |

### 9.2 Minimalism is a Feature, Not a Bug

The Copilot CLI harness is intentionally minimal because:

1. **Correct abstraction** — It matches Copilot CLI's actual capabilities (skills only)
2. **Low maintenance** — Fewer features = fewer bugs
3. **Clear scope** — Users understand what's supported and what's not
4. **Future-proof** — Easy to extend if Copilot CLI adds new APIs

**Conclusion:** The minimalism is justified and should be preserved.

---

## 10. Recommendations Summary

### 10.1 Immediate (Tier 1)

- ✅ **Create `COPILOT-INSTALL.md`** — Comprehensive installation guide
- ✅ **Archive legacy agent renderer** — Reduce confusion
- ✅ **Update `docs/INSTALL.md`** — Remove dead links

**Effort:** 2-3 hours  
**Impact:** High (clarity, user experience)  
**Risk:** None (documentation only)

### 10.2 Medium-term (Tier 2)

- ⏳ **Research Copilot CLI config API** — Understand future support
- ⏳ **Design config schema** — Plan for future expansion
- ⏳ **Implement config renderer** — If API becomes available

**Effort:** 4-6 hours (if API exists)  
**Impact:** Medium (future-proofing)  
**Risk:** Low (behind feature flag)

### 10.3 Long-term (Tier 3)

- ⏳ **Monitor Copilot CLI roadmap** — Track agent support
- ⏳ **Prepare agent renderer** — If/when API available

**Effort:** 8-12 hours (if API available)  
**Impact:** Low (parity with other harnesses)  
**Risk:** High (requires API changes)

---

## 11. Conclusion

The Copilot CLI harness is **intentionally minimal and correctly designed**. It renders 14 canonical skills to `~/.copilot/skills/` and omits agents because GitHub Copilot CLI doesn't support custom agent registration.

**Key takeaways:**

1. ✅ **Minimalism is justified** — Matches Copilot CLI's actual capabilities
2. ✅ **Skills rendering is complete and correct** — All 14 skills synced with proper safety
3. ⚠️ **Documentation gap exists** — No dedicated `COPILOT-INSTALL.md`
4. ⚠️ **Legacy code creates confusion** — Archive `render-copilot-agents.py`
5. ⏳ **Future expansion is possible** — Tier 2/3 opportunities if Copilot CLI adds APIs

**Recommended next steps:**
1. Create `COPILOT-INSTALL.md` (Tier 1, 1 hour)
2. Archive legacy agent renderer (Tier 1, 30 min)
3. Research Copilot CLI config API (Tier 2, 1 hour)
4. Monitor Copilot CLI roadmap for agent support (Tier 3, ongoing)

**Compliance status:** ✅ Medium-High (skills complete, agents intentionally omitted, documentation minimal)

---

## Appendix A: File Inventory

### Harness Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `renderer/scripts/render-copilot.sh` | Skills renderer | ✅ Complete |
| `renderer/scripts/render-copilot-agents.sh` | Agent wrapper (legacy) | ⏳ Archive recommended |
| `renderer/scripts/render-copilot-agents.py` | Agent renderer (legacy) | ⏳ Archive recommended |

### Source Files

| Directory | Contents | Count |
|-----------|----------|-------|
| `src/skills/` | Skill dirs with `SKILL.md` | 14 |
| `src/agents/` | Agent definitions | 8 (not rendered for Copilot CLI) |

### Documentation

| File | Status |
|------|--------|
| `docs/HARNESS-REVIEW.md` | ✅ Comprehensive (section 4) |
| `docs/COPILOT-INSTALL.md` | ❌ Missing (Tier 1 recommendation) |
| `docs/INSTALL.md` | ⚠️ Outdated (needs update) |

---

## Appendix B: Feature Comparison Matrix (Detailed)

### Skills Rendering

| Feature | Copilot CLI | OpenCode | Claude Code | π.dev |
|---------|-------------|----------|-------------|-------|
| Skills count | 14 | 14 | 14 | 0 |
| Rsync sync | ✅ | ✅ | ✅ | N/A |
| Marker file | ✅ | ✅ | ✅ | ⚠️ |
| Foreign skip | ✅ | ✅ | ✅ | ⚠️ |
| Uninstall | ✅ | ✅ | ✅ | ✅ |
| Status/drift | ✅ | ✅ | ✅ | ✅ |

### Agent Rendering

| Feature | Copilot CLI | OpenCode | Claude Code | π.dev |
|---------|-------------|----------|-------------|-------|
| Agents count | 0 (N/A) | 8 | 8 | ⚠️ 9 (stale) |
| Dynamic transform | N/A | ✅ | ✅ | ⚠️ Static |
| Model mapping | N/A | ✅ | ⚠️ Tier only | ⚠️ Stale |
| Marker file | N/A | ✅ | ✅ | ⚠️ Partial |
| Uninstall | N/A | ✅ | ✅ | ✅ |
| Status/drift | N/A | ✅ | ✅ | ✅ |

### Configuration Management

| Feature | Copilot CLI | OpenCode | Claude Code | π.dev |
|---------|-------------|----------|-------------|-------|
| Config file | ❌ N/A | ✅ opencode.jsonc | ❌ N/A | ⚠️ settings.json |
| Global rules | ❌ N/A | ✅ AGENTS.md | ❌ N/A | ⚠️ SYSTEM.md |
| Managed config | ❌ N/A | ✅ Sentinel | ❌ N/A | ⚠️ Static |

---

## Appendix C: Design Decision Log

### Why Skills Only?

**Decision:** Render skills but not agents for Copilot CLI.

**Rationale:**
- GitHub Copilot CLI API only supports skills/tools registration
- No documented agent registration mechanism
- Rendering agents would be dead code
- Minimalism reduces maintenance burden

**Evidence:**
- `gh copilot --help` shows no agent registration
- GitHub Copilot CLI docs (https://github.com/github/gh-copilot) don't mention agents
- Legacy `render-copilot-agents.py` produces non-standard `.agent.md` format

**Decision:** ✅ Correct

### Why No Config File?

**Decision:** Don't render `~/.copilot/config.json` or equivalent.

**Rationale:**
- Copilot CLI uses environment variables + CLI flags for config
- No documented global config file API
- Rendering config would be speculative

**Evidence:**
- `gh copilot config` command exists (CLI-based)
- No `~/.copilot/config.json` documented
- Copilot CLI source code (GitHub) doesn't reference config file

**Decision:** ✅ Correct

### Why Archive Agent Renderer?

**Decision:** Move `render-copilot-agents.py` and `render-copilot-agents.sh` to `_archive/`.

**Rationale:**
- Dead code (agents not supported by Copilot CLI)
- Creates confusion (users wonder if agents are supported)
- Not invoked by root Makefile (already inconsistent)
- Reduces maintenance burden

**Evidence:**
- Root Makefile: `make install-copilot` → skills only
- Renderer Makefile: `make install-copilot` → skills + agents (inconsistent)
- Agent renderer produces `.agent.md` (non-standard format)

**Decision:** ✅ Recommended (Tier 1)

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-16  
**Status:** Complete & Ready for Review
