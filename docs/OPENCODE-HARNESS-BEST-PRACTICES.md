# OpenCode Harness: Best Practices & Architecture Guide

**Status:** Phase 2C Analysis  
**Date:** 2026-05-16  
**Scope:** Architecture documentation, best practices, and improvement opportunities for the OpenCode harness (`render-opencode.sh`)

---

## Executive Summary

The OpenCode harness (`render-opencode.sh`) is the most sophisticated of the four agentic-engineers harnesses. It successfully implements:

- ✅ **Sentinel-based safety model** with JSONC comments and HTML markers for managed file detection
- ✅ **Hybrid metadata strategy** combining authoritative docs/AGENTS.md with fallback source frontmatter
- ✅ **Sidecar manifest tracking** for atomic agent lifecycle management
- ✅ **Foreign-file protection** preventing accidental overwrites of user-managed configurations
- ✅ **Compaction tuning** with 30,000-token headroom for skill-heavy workflows
- ✅ **OpenCode command integration** (sdlc-check, queue-status, hooks-install) for SDLC enforcement

This document captures what makes OpenCode successful, identifies current limitations, and proposes three tiers of improvements for Phase 3 and beyond.

---

## Part 1: Architecture & Design

### 1.1 High-Level Architecture

The OpenCode harness transforms canonical agentic-engineers specifications into an OpenCode-compatible installation at `~/.config/opencode/`:

```
┌─────────────────────────────────────────────────────────────┐
│ Canonical Source (agentic-engineers repo)                   │
├─────────────────────────────────────────────────────────────┤
│ docs/AGENTS.md                                              │
│   ├─ Role roster table (model, effort, description)         │
│   └─ Authoritative source for agent metadata                │
│                                                              │
│ src/agents/*-agent.md                                       │
│   ├─ Agent body content (responsibilities, integration)     │
│   └─ Fallback frontmatter (model, effort, description)      │
│                                                              │
│ src/skills/*/SKILL.md                                       │
│   └─ Skill definitions (workflow, scripts, references)      │
│                                                              │
│ .opencode/commands/*.md                                     │
│   └─ Custom OpenCode commands (sdlc-check, queue-status)    │
└─────────────────────────────────────────────────────────────┘
                            ↓
                  render-opencode.sh
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ OpenCode Installation (~/.config/opencode/)                 │
├─────────────────────────────────────────────────────────────┤
│ opencode.jsonc                                              │
│   ├─ Managed config (JSONC sentinel)                        │
│   ├─ Compaction: reserved=30000 (vs. default 20000)         │
│   ├─ Permissions: read, edit, bash, task, glob, grep, web   │
│   └─ Provider config: github-copilot models                 │
│                                                              │
│ AGENTS.md                                                   │
│   ├─ Global rules (HTML sentinel)                           │
│   ├─ Queue-based routing constraints                        │
│   ├─ Role-specific rules                                    │
│   └─ User override pattern (AGENTS.md.local)                │
│                                                              │
│ agents/                                                      │
│   ├─ orchestrator.md (mode: all)                            │
│   ├─ engineer.md (mode: subagent)                           │
│   ├─ senior-engineer.md                                     │
│   ├─ lead-engineer.md                                       │
│   ├─ quality-engineer.md                                    │
│   ├─ principal-engineer.md                                  │
│   ├─ security-engineer.md                                   │
│   ├─ model-engineer.md                                      │
│   └─ .agentic-engine{service-name} (manifest)               │
│                                                              │
│ skills/                                                      │
│   ├─ ab-testing/SKILL.md                                    │
│   ├─ agent-creator/SKILL.md                                 │
│   ├─ consistency-checker/SKILL.md                           │
│   ├─ metrics-etl/SKILL.md                                   │
│   ├─ model-engineer/SKILL.md                                │
│   ├─ protocol-validator/SKILL.md                            │
│   ├─ queue-management/SKILL.md                              │
│   ├─ repo-init/SKILL.md                                     │
│   ├─ skill-creator/SKILL.md                                 │
│   ├─ spec-management/SKILL.md                               │
│   ├─ spec-validator/SKILL.md                                │
│   ├─ tokenadvisor/SKILL.md                                  │
│   ├─ usage-tracking/SKILL.md                                │
│   ├─ voice-notify/SKILL.md                                  │
│   └─ [per-skill markers]                                    │
│                                                              │
│ commands/                                                    │
│   ├─ sdlc-check.md                                          │
│   ├─ queue-status.md                                        │
│   └─ hooks-install.md                                       │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Key Components

#### A. Sentinel-Based Safety Model

**Problem solved:** How to distinguish managed files from user-created files without a central registry?

**Solution:** Embed markers in files that are safe from schema validation:

1. **opencode.jsonc sentinel:**
   ```jsonc
   // _managed_by: agentic-engineers renderer/scripts/render-opencode.sh
   ```
   - Uses JSONC comment syntax (not a JSON field)
   - Avoids schema validation failures (`additionalProperties: false`)
   - Detectable with `grep` before overwriting

2. **AGENTS.md sentinel:**
   ```html
   <!-- managed by agentic-engineers render-opencode.sh; user edits to AGENTS.md.local will be loaded after this file -->
   ```
   - HTML comment on line 1
   - Checked with `head -n1 | grep`
   - Enables user override pattern (AGENTS.md.local)

3. **Per-skill marker files:**
   ```bash
   ~/.config/opencode/skills/{name}/.agentic-engine{service-name}
   ```
   - Timestamp file (created at render time)
   - Indicates skill is managed by renderer
   - Uninstall removes only marked skills

4. **Agent manifest (sidecar):**
   ```bash
   ~/.config/opencode/agents/.agentic-engine{service-name}
   ```
   - Newline-separated list of managed agent names
   - Atomic write with `.tmp` → `mv` pattern
   - Protects against partial-failure corruption

**Why this is effective:**
- No external registry needed (self-contained in files)
- Survives re-installs and user edits
- Minimal overhead (one comment, one file per skill, one manifest)
- Detectable with simple shell tools (`grep`, `head`, `test -f`)

#### B. Hybrid Metadata Strategy

**Problem solved:** How to keep agent metadata in sync across multiple sources (docs/AGENTS.md, src/agents/*-agent.md)?

**Solution:** Establish a clear precedence hierarchy:

```
docs/AGENTS.md (authoritative)
    ↓ (if empty)
src/agents/*-agent.md frontmatter
    ↓ (if empty)
src/agents/*-agent.md body (first non-empty line)
```

**Implementation:**

```bash
# 1. Lookup in docs/AGENTS.md (authoritative)
docs_row=$(docs_lookup_role "$name" || true)
docs_model=""; docs_effort=""; docs_desc=""
if [ -n "$docs_row" ]; then
    docs_model=$(printf '%s' "$docs_row" | awk -F'\t' '{print $1}')
    docs_effort=$(printf '%s' "$docs_row" | awk -F'\t' '{print $2}')
    docs_desc=$(printf '%s' "$docs_row" | awk -F'\t' '{print $3}')
fi

# 2. Fallback to source frontmatter
fm_desc=$(extract_fm "$src_file" "description" || true)
fm_model=$(extract_fm "$src_file" "model" || true)

# 3. Final fallback to body
body_model=$(extract_body_model "$src_file" || true)

# 4. Pick best available (prefer docs)
desc="$docs_desc"
[ -z "$desc" ] && desc="$fm_desc"
[ -z "$desc" ] && desc=$(strip_fm "$src_file" | awk 'NF{print; exit}')

model_raw="${docs_model:-${fm_model:-$body_model}}"
```

**Why this is effective:**
- Single source of truth (docs/AGENTS.md) for role assignments
- Fallback chain allows flexibility during development
- Clear precedence prevents ambiguity
- Supports both markdown table parsing and frontmatter extraction

#### C. Configuration Management

**opencode.jsonc structure:**

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["AGENTS.md"],
  "default_agent": "orchestrator",
  "model": "github-copilot/claude-haiku-4.5",
  "compaction": {
    "auto": true,
    "reserved": 30000  // ← Key tuning: 30K vs default 20K
  },
  "permission": {
    "read": "allow",
    "edit": "allow",
    "bash": "allow",
    "task": "allow",
    "glob": "allow",
    "grep": "allow",
    "webfetch": "allow"
  },
  "agent": {
    "orchestrator": {
      "model": "github-copilot/claude-haiku-4.5"
    }
  },
  "provider": {
    "github-copilot": {
      "models": {
        "claude-opus-4.6": {
          // Custom provider entry for claude-opus-4.6
          // (not available in default github-copilot provider)
        }
      }
    }
  }
}
```

**Key decisions:**

1. **Compaction reserve = 30,000 tokens**
   - Default is 20,000
   - Increased to reduce mid-task compaction surprises
   - Skill outputs are PRUNE_PROTECTED; tool outputs are not
   - Larger reserve provides more buffer for bash/task output

2. **Permissions: all allowed**
   - `read`, `edit`, `bash`, `task`, `glob`, `grep`, `webfetch`
   - Assumes trusted environment (user's own machine)
   - Could be tightened for shared/enterprise installs

3. **Custom provider entry**
   - `claude-opus-4.6` added to github-copilot provider
   - Allows model mapping without fallback to 4.7
   - Future enhancement: auto-detect from `opencode models`

#### D. Command Integration

**Three custom OpenCode commands:**

1. **sdlc-check** — Validate SDLC workflow compliance
   - Check queue health (stalled items, malformed YAML)
   - Validate DELEGATE/HANDBACK integrity
   - Verify git hooks are active
   - Quick SPEC compliance check

2. **queue-status** — Review pending work
   - List incoming DELEGATEs
   - List processing HANDBACKs
   - Show task counts and ages

3. **hooks-install** — Install git enforcement hooks
   - Set `core.hooksPath = .githooks`
   - Make hooks executable
   - Verify installation

**Why this matters:**
- Integrates SDLC enforcement into OpenCode workflow
- Enables in-harness queue monitoring (no external tools)
- Reduces friction for queue-based task management

### 1.3 Model Mapping Strategy

**Canonical IDs** (agentic-engineers):
```
claude-haiku-4-5
claude-sonnet-4-6
claude-opus-4-7
claude-opus-4-6
```

**OpenCode IDs** (github-copilot provider):
```
github-copilot/claude-haiku-4.5
github-copilot/claude-sonnet-4.6
github-copilot/claude-opus-4.7
github-copilot/claude-opus-4.6 (custom)
```

**Mapping function:**
```bash
map_model_opencode() {
    case "$1" in
        claude-haiku-4-5|claude-haiku-4.5)   echo "github-copilot/claude-haiku-4.5" ;;
        claude-sonnet-4-6|claude-sonnet-4.6) echo "github-copilot/claude-sonnet-4.6" ;;
        claude-sonnet-4-5|claude-sonnet-4.5) echo "github-copilot/claude-sonnet-4.5" ;;
        claude-opus-4-7|claude-opus-4.7)     echo "github-copilot/claude-opus-4.7" ;;
        claude-opus-4-6|claude-opus-4.6)     echo "github-copilot/claude-opus-4.6" ;;
        claude-opus-4-5|claude-opus-4.5)     echo "github-copilot/claude-opus-4.5" ;;
        *) echo "" ;;  # Unknown model
    esac
}
```

**Effort → Temperature mapping:**
```bash
effort_to_temperature() {
    case "$1" in
        low|medium)  echo "0.3" ;;  # Deterministic
        high|max)    echo "0.5" ;;  # Exploratory
        *)           echo "0.3" ;;  # Default
    esac
}
```

---

## Part 2: Best Practices

### 2.1 Sentinel-Based Safety

**Practice 1: Always check for sentinels before overwriting**

```bash
# Good: Check sentinel first
if [ -f "$DST_CONFIG" ] && ! grep -q "$CONFIG_SENTINEL" "$DST_CONFIG"; then
    echo "⚠️  skipping opencode.jsonc — foreign at $DST_CONFIG"
    return
fi
```

**Practice 2: Use file-safe marker formats**

- JSONC comments for JSON files (avoids schema validation)
- HTML comments for Markdown files
- Timestamp files for directories
- Manifest files for collections

**Practice 3: Implement atomic writes for critical files**

```bash
# Good: Atomic write with .tmp file
: > "$AGENT_MANIFEST.tmp"
# ... write to .tmp ...
mv "$AGENT_MANIFEST.tmp" "$AGENT_MANIFEST"
```

**Practice 4: Provide clear status reporting**

```bash
# Good: Distinguish between managed, foreign, and missing
if [ ! -f "$t" ]; then echo "  ❌ skill $name (not installed)"
elif [ ! -f "$t/$SKILL_MARKER" ]; then echo "  ⚠️  skill $name (foreign)"
elif diff -rq "$src" "$t" >/dev/null 2>&1; then echo "  ✅ skill $name"
else echo "  🔄 skill $name (drift)"; fi
```

### 2.2 Metadata Management

**Practice 1: Establish a single source of truth**

- docs/AGENTS.md is authoritative for role assignments
- src/agents/*-agent.md provides fallback and richer descriptions
- Clear precedence prevents ambiguity

**Practice 2: Document the metadata strategy**

Include comments in the renderer explaining:
- Why docs/AGENTS.md is authoritative
- What happens if metadata is missing
- How to add new agents or roles

**Practice 3: Validate metadata during rendering**

```bash
# Good: Warn if model lookup fails
if [ -z "$model_full" ]; then
    if [ -z "$model_raw" ]; then
        echo "  ⚠️  skipping agent $name — no model in docs/AGENTS.md"
    else
        echo "  ⚠️  skipping agent $name — model '$model_raw' not in registry"
    fi
    continue
fi
```

**Practice 4: Support fallback chains**

Allow metadata to come from multiple sources with clear precedence:
1. Authoritative source (docs/AGENTS.md)
2. Source frontmatter (src/agents/*-agent.md)
3. Body content (first non-empty line)

### 2.3 Configuration Management

**Practice 1: Separate configuration from content**

- opencode.jsonc: configuration (compaction, permissions, provider)
- AGENTS.md: content (rules, constraints, links)
- agents/*.md: agent definitions (frontmatter + body)
- skills/*/SKILL.md: skill definitions

**Practice 2: Use sensible defaults with clear tuning**

```jsonc
"compaction": {
  "auto": true,
  "reserved": 30000  // ← Documented: 30K vs default 20K
}
```

**Practice 3: Document why each setting exists**

Include comments explaining:
- Why compaction.reserved is 30,000 (vs. default 20,000)
- Why permissions are all allowed (vs. restricted)
- Why custom provider entries are needed

**Practice 4: Make configuration portable**

- Use XDG-standard paths (~/.config/opencode/)
- Support user overrides (AGENTS.md.local)
- Allow provider detection (future enhancement)

### 2.4 Command Integration

**Practice 1: Expose critical workflows as commands**

- sdlc-check: SDLC compliance validation
- queue-status: Queue monitoring
- hooks-install: Git hook setup

**Practice 2: Keep commands focused and composable**

Each command should do one thing well:
- sdlc-check: validate compliance
- queue-status: show status
- hooks-install: install hooks

**Practice 3: Provide clear status reporting**

Use consistent emoji/status indicators:
- ✅ Success
- ⚠️ Warning (non-blocking)
- ❌ Error (blocking)

**Practice 4: Document command usage**

Include in command definition:
- What the command does
- What it checks
- How to interpret results

### 2.5 Error Handling & Recovery

**Practice 1: Fail fast with clear errors**

```bash
# Good: Fail immediately with context
if [ -z "$model_full" ]; then
    echo "  ⚠️  skipping agent $name — model not found"
    continue
fi
```

**Practice 2: Support partial failure recovery**

- Agent manifest uses atomic writes
- Skills can be re-rendered individually
- Status mode shows what's missing/drifted

**Practice 3: Provide uninstall capability**

```bash
case "$MODE" in
    --uninstall)
        # Remove only managed files
        # Use sentinels and manifest to identify what's ours
        ;;
esac
```

**Practice 4: Document recovery procedures**

Include in OPENCODE-INSTALL.md:
- How to recover from partial failure
- How to clean up foreign files
- How to re-render from scratch

---

## Part 3: Current Limitations & Gaps

### 3.1 Known Limitations

#### 1. Provider-Specific Model IDs (Medium Priority)

**Issue:** Model IDs are hardcoded to `github-copilot/` provider.

**Impact:** Users with the `anthropic/` provider would need different IDs (e.g., `anthropic/claude-haiku-4-5`).

**Current workaround:** Comment in code suggests future enhancement to auto-detect providers.

**Recommendation:** Implement provider detection at install time.

#### 2. Fragile docs/AGENTS.md Table Parsing (Medium Priority)

**Issue:** The awk parser for the markdown table is sensitive to formatting changes.

```bash
awk -v role="$role" -F'|' '
    $0 ~ "\\| \\*\\*"role"\\*\\*" {
        # Parse fields from markdown table
        # Sensitive to: column order, bold markers, spacing
    }
' "$DOCS_AGENTS"
```

**Impact:** If table format changes (column reordering, bold markers), parser silently returns empty, causing agents to be skipped.

**Recommendation:** Add validation step that warns if `docs_lookup_role` returns empty for all agents.

#### 3. Fragile Frontmatter Parsing (Low Priority)

**Issue:** The awk-based frontmatter parser handles only simple `key: value` pairs.

**Impact:** Multi-line YAML values (e.g., `description: |\n  line1\n  line2`) will break extraction.

**Current status:** Not a bug in practice (current source files use single-line values), but fragile.

**Recommendation:** Document limitation or enhance parser to handle multi-line values.

#### 4. No Rollback on Partial Failure (Low Priority)

**Issue:** If render fails mid-way (e.g., rsync error on skill 7 of 14), already-rendered files remain.

**Impact:** Incomplete installation that may cause confusion.

**Current mitigation:** Agent manifest uses `.tmp` → `mv` strategy (atomic). Skills have no equivalent.

**Recommendation:** Add skill rollback on error, similar to agent manifest strategy.

#### 5. External Dependencies (Low Priority)

**Issue:** Script depends on `rsync` and `python3`.

**Impact:** May not be available on all systems (though common on macOS/Linux).

**Current fallback:** `json_escape` falls back to sed if Python 3 unavailable.

**Recommendation:** Document dependencies in OPENCODE-INSTALL.md.

#### 6. Schema Validation Uncertainty (Medium Priority)

**Issue:** `opencode.jsonc` includes `default_agent` and `agent` fields that may not be in the OpenCode JSON schema.

**Impact:** If OpenCode uses strict schema validation (`additionalProperties: false`), these fields could cause validation errors.

**Current status:** Appears to work in practice, but should be verified.

**Recommendation:** Verify against OpenCode schema documentation or test with strict validation.

---

## Part 4: Improvement Opportunities

### 4.1 Tier 1 Improvements (High Priority, Phase 3)

#### 1.1 Provider Auto-Detection

**Problem:** Model IDs are hardcoded to `github-copilot/` provider.

**Solution:** Detect available providers at install time and select appropriate model IDs dynamically.

**Implementation:**
```bash
detect_available_providers() {
    # Run: opencode models
    # Parse output to identify available providers
    # Return: list of providers (e.g., "github-copilot anthropic")
}

select_best_provider() {
    local providers="$1"
    # Prefer: anthropic > github-copilot > others
    # Return: selected provider
}

map_model_for_provider() {
    local model="$1"
    local provider="$2"
    # Map canonical ID to provider-specific ID
    # Example: claude-haiku-4-5 + anthropic → anthropic/claude-haiku-4-5
}
```

**Benefit:** Works with any provider (anthropic, github-copilot, etc.)

**Effort:** ~2 hours (shell scripting, testing with multiple providers)

#### 1.2 Validate docs/AGENTS.md Table Format

**Problem:** Parser silently fails if table format changes.

**Solution:** Add validation step that warns if `docs_lookup_role` returns empty for all agents.

**Implementation:**
```bash
validate_agents_md_table() {
    local agents_file="$1"
    local count=0
    for name in $(list_source_agents); do
        if docs_lookup_role "$name" >/dev/null; then
            count=$((count + 1))
        fi
    done
    if [ "$count" -eq 0 ]; then
        echo "⚠️  WARNING: docs/AGENTS.md table parsing failed for all agents"
        echo "   Check table format (columns, bold markers, spacing)"
        return 1
    fi
}
```

**Benefit:** Catches table format issues early

**Effort:** ~1 hour (awk validation, testing)

#### 1.3 Verify OpenCode Schema Compliance

**Problem:** Uncertain whether `default_agent` and `agent` fields are valid schema fields.

**Solution:** Verify against OpenCode schema documentation or test with strict validation.

**Implementation:**
```bash
validate_opencode_schema() {
    local config="$1"
    # Test with strict schema validation
    # Verify all fields are valid
    # Report any schema violations
}
```

**Benefit:** Ensures config is compatible with OpenCode

**Effort:** ~1 hour (schema verification, testing)

### 4.2 Tier 2 Improvements (Medium Priority, Phase 3+)

#### 2.1 Skill Rollback on Partial Failure

**Problem:** If render fails mid-way, already-rendered skills remain in inconsistent state.

**Solution:** Track rendered skills and roll back on error, similar to agent manifest strategy.

**Implementation:**
```bash
# Create skill manifest during render
: > "$SKILL_MANIFEST.tmp"
for name in $(list_source_skills); do
    # ... render skill ...
    echo "$name" >> "$SKILL_MANIFEST.tmp"
done

# On error, roll back rendered skills
on_error() {
    if [ -f "$SKILL_MANIFEST.tmp" ]; then
        while IFS= read -r name; do
            rm -rf "$DST_SKILLS/$name"
        done < "$SKILL_MANIFEST.tmp"
    fi
    rm -f "$SKILL_MANIFEST.tmp"
}
```

**Benefit:** Consistent state on failure

**Effort:** ~2 hours (manifest tracking, error handling, testing)

#### 2.2 Enhanced Frontmatter Parser

**Problem:** Parser fails on multi-line YAML values.

**Solution:** Enhance parser to handle multi-line values or document limitation clearly.

**Implementation:**
```bash
# Option 1: Use python3 yaml parser
extract_fm_yaml() {
    python3 -c "
import yaml, sys
with open('$1') as f:
    fm = yaml.safe_load(f)
    print(fm.get('$2', ''))
"
}

# Option 2: Document limitation and require single-line values
# (Simpler, current approach)
```

**Benefit:** Supports richer agent descriptions

**Effort:** ~2 hours (parser enhancement, testing) or ~30 min (documentation)

#### 2.3 Comprehensive Error Handling

**Problem:** Script has minimal error handling for edge cases.

**Solution:** Add comprehensive error handling with clear error messages.

**Implementation:**
```bash
# Trap errors and provide context
trap 'echo "❌ Error at line $LINENO"; exit 1' ERR

# Validate inputs
[ -d "$REPO_ROOT" ] || { echo "❌ REPO_ROOT not a directory: $REPO_ROOT"; exit 1; }
[ -d "$OPENCODE" ] || mkdir -p "$OPENCODE" || { echo "❌ Cannot create $OPENCODE"; exit 1; }

# Check dependencies
command -v rsync >/dev/null || { echo "❌ rsync not found"; exit 1; }
```

**Benefit:** Better error reporting and recovery

**Effort:** ~2 hours (error handling, testing)

### 4.3 Tier 3 Improvements (Nice-to-Have, Phase 4+)

#### 3.1 Incremental Rendering

**Problem:** Full render takes time; no way to re-render just one agent or skill.

**Solution:** Add `--agent <name>` and `--skill <name>` flags for incremental rendering.

**Implementation:**
```bash
case "$MODE" in
    --agent)
        # Render single agent: render-opencode.sh REPO_ROOT OPENCODE_DIR --agent orchestrator
        render_single_agent "$4"
        ;;
    --skill)
        # Render single skill: render-opencode.sh REPO_ROOT OPENCODE_DIR --skill ab-testing
        render_single_skill "$4"
        ;;
esac
```

**Benefit:** Faster iteration during development

**Effort:** ~3 hours (flag handling, single-item render, testing)

#### 3.2 Drift Repair

**Problem:** Status mode shows drift but doesn't fix it.

**Solution:** Add `--repair` flag to fix drifted files.

**Implementation:**
```bash
case "$MODE" in
    --repair)
        # Re-render all drifted files
        for name in $(list_source_skills); do
            src="$SRC_SKILLS/$name"; dst="$DST_SKILLS/$name"
            if ! diff -rq "$src" "$dst" >/dev/null 2>&1; then
                echo "  🔄 repairing skill $name..."
                rsync -a --delete "$src/" "$dst/"
            fi
        done
        ;;
esac
```

**Benefit:** One-command fix for drift

**Effort:** ~1 hour (repair logic, testing)

#### 3.3 Dry-Run Mode

**Problem:** No way to preview what will be rendered without actually rendering.

**Solution:** Add `--dry-run` flag to show what would be done.

**Implementation:**
```bash
case "$MODE" in
    --dry-run)
        # Show what would be rendered without actually doing it
        echo "Would render:"
        for name in $(list_source_skills); do
            echo "  - skill: $name"
        done
        for name in $(list_source_agents); do
            echo "  - agent: $name"
        done
        ;;
esac
```

**Benefit:** Safe preview before rendering

**Effort:** ~1 hour (dry-run logic, testing)

#### 3.4 Metrics Collection

**Problem:** No visibility into render performance or issues.

**Solution:** Collect metrics on render time, file counts, errors.

**Implementation:**
```bash
# Track render metrics
render_start=$(date +%s%N)
# ... render ...
render_end=$(date +%s%N)
render_duration_ms=$(( (render_end - render_start) / 1000000 ))

# Log metrics
cat > "$OPENCODE/.render-metrics" <<EOF
timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
duration_ms: $render_duration_ms
agents_rendered: $count_a
skills_rendered: $count_s
config_written: $config_written
rules_written: $rules_written
EOF
```

**Benefit:** Visibility into render performance

**Effort:** ~1 hour (metrics collection, logging)

#### 3.5 Configuration Validation

**Problem:** No way to validate opencode.jsonc before rendering.

**Solution:** Add JSON schema validation before writing config.

**Implementation:**
```bash
validate_config_schema() {
    local config="$1"
    # Validate against OpenCode schema
    # Report any violations
    # Return 0 if valid, 1 if invalid
}
```

**Benefit:** Catch config errors early

**Effort:** ~2 hours (schema validation, testing)

---

## Part 5: Recommendations for Phase 3

### 5.1 Priority Ranking

**Tier 1 (Must Have):**
1. ✅ Provider auto-detection (enables anthropic/ provider support)
2. ✅ Validate docs/AGENTS.md table format (prevents silent failures)
3. ✅ Verify OpenCode schema compliance (ensures compatibility)

**Tier 2 (Should Have):**
4. ✅ Skill rollback on partial failure (consistency)
5. ✅ Enhanced frontmatter parser (flexibility)
6. ✅ Comprehensive error handling (robustness)

**Tier 3 (Nice to Have):**
7. ✅ Incremental rendering (developer experience)
8. ✅ Drift repair (operational ease)
9. ✅ Dry-run mode (safety)
10. ✅ Metrics collection (visibility)
11. ✅ Configuration validation (robustness)

### 5.2 Implementation Plan

**Phase 3A (Weeks 1-2):** Tier 1 improvements
- Provider auto-detection
- docs/AGENTS.md validation
- Schema compliance verification

**Phase 3B (Weeks 3-4):** Tier 2 improvements
- Skill rollback
- Enhanced frontmatter parser
- Error handling

**Phase 3C (Weeks 5+):** Tier 3 improvements
- Incremental rendering
- Drift repair
- Dry-run mode
- Metrics collection
- Configuration validation

### 5.3 Testing Strategy

**Unit tests:**
- Model mapping (all canonical IDs → OpenCode IDs)
- Effort → temperature mapping
- Frontmatter extraction (single-line and edge cases)
- Sentinel detection (JSONC, HTML, files)

**Integration tests:**
- Full render cycle (source → ~/.config/opencode/)
- Uninstall cycle (removes only managed files)
- Status cycle (detects drift, missing, foreign)
- Provider detection (with mock providers)

**E2E tests:**
- Install → verify → uninstall → re-install
- Foreign file protection (doesn't overwrite user files)
- Manifest atomicity (no corruption on crash)

---

## Part 6: Comparison with Other Harnesses

### 6.1 OpenCode vs. Claude Code

| Feature | OpenCode | Claude Code |
|---------|----------|-------------|
| Config file | opencode.jsonc (managed) | CLAUDE.md (user-authored) |
| Global rules | AGENTS.md (managed) | CLAUDE.md (user-authored) |
| Agent format | OpenCode subagent (mode/model/temp) | Claude Code agent (model/temperature) |
| Skill format | SKILL.md (directory) | SKILL.md (directory) |
| Model IDs | provider/model (github-copilot/claude-haiku-4.5) | Short tier (haiku, sonnet, opus) |
| Sentinel strategy | JSONC comment + HTML comment | None (no managed files) |
| Foreign file protection | Yes (sentinel + manifest) | No |
| Uninstall capability | Yes (removes managed files) | No (user-managed) |
| Status reporting | Yes (drift detection) | No |

**Key difference:** OpenCode harness is fully managed (can be uninstalled cleanly), while Claude Code is user-authored (no uninstall).

### 6.2 OpenCode vs. Copilot

| Feature | OpenCode | Copilot |
|---------|----------|---------|
| Config file | opencode.jsonc | copilot.jsonc (custom) |
| Global rules | AGENTS.md | copilot.jsonc |
| Agent format | OpenCode subagent | Copilot agent |
| Sentinel strategy | JSONC comment | Custom marker |
| Uninstall capability | Yes | Yes |
| Status reporting | Yes | Yes |

**Key difference:** OpenCode uses XDG-standard paths (~/.config/opencode/), while Copilot uses custom paths (~/.copilot/).

### 6.3 OpenCode vs. π.dev

| Feature | OpenCode | π.dev |
|---------|----------|-------|
| Config file | opencode.jsonc | π.dev config (custom) |
| Global rules | AGENTS.md | π.dev rules |
| Agent format | OpenCode subagent | π.dev agent |
| Sentinel strategy | JSONC comment | Custom marker |
| Uninstall capability | Yes | Yes |
| Status reporting | Yes | Yes |

**Key difference:** π.dev is a specialized harness for π.dev platform, while OpenCode is a general-purpose harness.

---

## Part 7: Key Takeaways

### 7.1 What Makes OpenCode Successful

1. **Sentinel-based safety** — Elegant solution to the "managed vs. user files" problem without external registry
2. **Hybrid metadata strategy** — Clear precedence hierarchy (docs → source → body) prevents ambiguity
3. **Atomic writes** — Manifest with `.tmp` → `mv` pattern ensures consistency
4. **Foreign-file protection** — Refuses to overwrite files without markers
5. **Compaction tuning** — 30K token headroom reduces mid-task surprises
6. **Command integration** — Exposes critical workflows (sdlc-check, queue-status, hooks-install)
7. **Clear documentation** — OPENCODE-INSTALL.md explains architecture and usage

### 7.2 Lessons for Other Harnesses

1. **Use sentinels for managed file detection** — More robust than external registries
2. **Establish clear metadata precedence** — Prevents ambiguity and supports fallback chains
3. **Implement atomic writes** — Protects against partial-failure corruption
4. **Provide status reporting** — Helps users understand installation state
5. **Support uninstall** — Enables clean removal of managed files
6. **Expose critical workflows as commands** — Reduces friction for queue-based task management

### 7.3 Future Directions

1. **Provider auto-detection** — Support any provider (anthropic, github-copilot, etc.)
2. **Enhanced validation** — Catch table format changes and schema violations early
3. **Incremental rendering** — Faster iteration during development
4. **Drift repair** — One-command fix for drifted files
5. **Metrics collection** — Visibility into render performance

---

## Appendix A: File Structure Reference

### A.1 Canonical Source Layout

```
agentic-engineers/
├── docs/
│   ├── AGENTS.md                    ← Authoritative agent roster
│   ├── OPENCODE-INSTALL.md          ← Installation guide
│   └── OPENCODE-HARNESS-BEST-PRACTICES.md  ← This document
├── src/
│   ├── agents/
│   │   ├── orchestrator-agent.md
│   │   ├── engineer-agent.md
│   │   ├── senior-engineer-agent.md
│   │   ├── lead-engineer-agent.md
│   │   ├── quality-engineer-agent.md
│   │   ├── principal-engineer-agent.md
│   │   ├── security-engineer-agent.md
│   │   └── model-engineer-agent.md
│   └── skills/
│       ├── ab-testing/SKILL.md
│       ├── agent-creator/SKILL.md
│       ├── consistency-checker/SKILL.md
│       ├── metrics-etl/SKILL.md
│       ├── model-engineer/SKILL.md
│       ├── protocol-validator/SKILL.md
│       ├── queue-management/SKILL.md
│       ├── repo-init/SKILL.md
│       ├── skill-creator/SKILL.md
│       ├── spec-management/SKILL.md
│       ├── spec-validator/SKILL.md
│       ├── tokenadvisor/SKILL.md
│       ├── usage-tracking/SKILL.md
│       └── voice-notify/SKILL.md
├── .opencode/
│   └── commands/
│       ├── sdlc-check.md
│       ├── queue-status.md
│       └── hooks-install.md
└── renderer/
    └── scripts/
        ├── render-opencode.sh       ← Main renderer
        ├── render-claude.sh         ← Claude Code renderer
        ├── render-copilot.sh        ← Copilot renderer
        ├── render-pi.sh             ← π.dev renderer
        └── lib.sh                   ← Shared functions
```

### A.2 Installed Layout

```
~/.config/opencode/
├── opencode.jsonc                  ← Managed config (JSONC sentinel)
├── AGENTS.md                        ← Global rules (HTML sentinel)
├── AGENTS.md.local                  ← User overrides (optional)
├── agents/
│   ├── orchestrator.md              ← OpenCode subagent format
│   ├── engineer.md
│   ├── senior-engineer.md
│   ├── lead-engineer.md
│   ├── quality-engineer.md
│   ├── principal-engineer.md
│   ├── security-engineer.md
│   ├── model-engineer.md
│   └── .agentic-engine{service-name}  ← Agent manifest
├── skills/
│   ├── ab-testing/
│   │   ├── SKILL.md
│   │   └── .agentic-engine{service-name}
│   ├── agent-creator/
│   │   ├── SKILL.md
│   │   └── .agentic-engine{service-name}
│   ├── ... (12 more skills)
│   └── voice-notify/
│       ├── SKILL.md
│       └── .agentic-engine{service-name}
└── commands/
    ├── sdlc-check.md
    ├── queue-status.md
    └── hooks-install.md
```

---

## Appendix B: Sentinel Detection Patterns

### B.1 JSONC Comment Sentinel

**Pattern:** `// _managed_by: agentic-engineers renderer/scripts/render-opencode.sh`

**Detection:**
```bash
grep -q "$CONFIG_SENTINEL" "$DST_CONFIG"
```

**Why JSONC?** Avoids schema validation failures while remaining detectable.

### B.2 HTML Comment Sentinel

**Pattern:** `<!-- managed by agentic-engineers render-opencode.sh`

**Detection:**
```bash
head -n1 "$DST_RULES" | grep -q "$RULES_SENTINEL"
```

**Why HTML comment?** Markdown-compatible, visible to humans, detectable with `head`.

### B.3 Marker File Sentinel

**Pattern:** `.agentic-engine{service-name}` (timestamp file)

**Detection:**
```bash
[ -f "$dst/$SKILL_MARKER" ]
```

**Why timestamp file?** Indicates when skill was last rendered, survives re-installs.

### B.4 Manifest File Sentinel

**Pattern:** Newline-separated list of managed agent names

**Detection:**
```bash
grep -qx "$name" "$AGENT_MANIFEST"
```

**Why manifest?** Atomic write with `.tmp` → `mv` prevents corruption on crash.

---

## Appendix C: Error Handling Patterns

### C.1 Foreign File Protection

```bash
# Check if file exists and is NOT ours
if [ -f "$dst_file" ] && [ -f "$AGENT_MANIFEST" ] && ! grep -qx "$name" "$AGENT_MANIFEST"; then
    echo "  ⚠️  skipping agent $name — foreign at $dst_file"
    continue
fi

# Check if file exists but we don't have a manifest yet (first run)
if [ -f "$dst_file" ] && [ ! -f "$AGENT_MANIFEST" ]; then
    echo "  ⚠️  skipping agent $name — pre-existing file (no manifest yet)"
    continue
fi
```

### C.2 Atomic Writes

```bash
# Write to temporary file
: > "$AGENT_MANIFEST.tmp"
# ... write entries ...
# Atomically move to final location
mv "$AGENT_MANIFEST.tmp" "$AGENT_MANIFEST"
```

### C.3 Graceful Fallbacks

```bash
# Try primary method
model_full=$(map_model_opencode "$model_raw")

# If primary fails, check if model_raw is empty or unknown
if [ -z "$model_full" ]; then
    if [ -z "$model_raw" ]; then
        echo "  ⚠️  no model found (non-canonical role?)"
    else
        echo "  ⚠️  model '$model_raw' not in registry"
    fi
    continue
fi
```

---

## Appendix D: Testing Checklist

### D.1 Unit Tests

- [ ] Model mapping: all canonical IDs map correctly
- [ ] Effort → temperature: low/medium → 0.3, high/max → 0.5
- [ ] Sentinel detection: JSONC, HTML, files
- [ ] Frontmatter extraction: simple values, edge cases
- [ ] Manifest atomicity: no corruption on crash simulation

### D.2 Integration Tests

- [ ] Full install: source → ~/.config/opencode/
- [ ] Full uninstall: removes only managed files
- [ ] Status detection: identifies drift, missing, foreign
- [ ] Foreign file protection: doesn't overwrite user files
- [ ] Re-install: idempotent (same result)

### D.3 E2E Tests

- [ ] Install → verify → uninstall → re-install
- [ ] Provider detection: with mock providers
- [ ] Error handling: graceful failures with clear messages
- [ ] Compaction: 30K token reserve is respected
- [ ] Commands: sdlc-check, queue-status, hooks-install work

### D.4 Manual Tests

- [ ] Install on macOS (with rsync, python3)
- [ ] Install on Linux (with rsync, python3)
- [ ] Verify in OpenCode: agents and skills available
- [ ] Test commands: sdlc-check, queue-status, hooks-install
- [ ] Test uninstall: clean removal of managed files

---

## Appendix E: Documentation References

### E.1 Internal Documentation

- **docs/AGENTS.md** — Agent roster and routing rules
- **docs/OPENCODE-INSTALL.md** — Installation guide
- **docs/HANDOFF.md** — DELEGATE/HANDBACK protocol
- **docs/QUEUE-PROTOCOL.md** — Queue-based task management
- **docs/SKILLS.md** — Skill definitions and usage

### E.2 External Documentation

- **OpenCode docs:** https://opencode.ai/docs/config
- **XDG Base Directory:** https://specifications.freedesktop.org/basedir-spec/
- **JSONC spec:** https://github.com/microsoft/vscode/wiki/JSONC
- **YAML spec:** https://yaml.org/

---

## Appendix F: Glossary

| Term | Definition |
|------|-----------|
| **Sentinel** | A marker (comment, file) that identifies managed files |
| **Manifest** | A file listing managed items (agents, skills) |
| **Hybrid metadata** | Metadata from multiple sources with clear precedence |
| **Foreign file** | A file not managed by the renderer |
| **Drift** | When installed file differs from source |
| **Atomic write** | Write that either succeeds completely or fails completely |
| **Compaction** | Automatic pruning of old messages when token usage is high |
| **PRUNE_PROTECTED** | Skill outputs that survive compaction |
| **Provider** | Model provider (github-copilot, anthropic, etc.) |
| **Subagent** | Agent invoked via @-mention or task tool (not as primary agent) |

---

## Document History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-05-16 | 1.0 | Engineer | Initial analysis and best practices guide |

---

**End of Document**

This guide captures the architecture, best practices, and improvement opportunities for the OpenCode harness. It serves as a reference for Phase 3 development and future maintenance.
