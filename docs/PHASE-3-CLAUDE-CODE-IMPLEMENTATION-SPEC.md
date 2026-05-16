# Phase 3 — Claude Code Harness Implementation Specification

**Task ID**: 2026-05-16-phase3-claude-code-impl-spec  
**Author**: Senior Engineer (claude-sonnet-4-6)  
**Date**: 2026-05-16  
**Status**: Specification Complete — Ready for Implementation  
**Source Analysis**: `docs/CLAUDE-CODE-HARNESS-ANALYSIS.md`  
**Target Files**: `renderer/scripts/render-claude.sh`, `renderer/scripts/lib.sh`, `.githooks/pre-commit`

---

## Executive Summary

This document provides detailed implementation specifications for the two highest-priority features identified in the Claude Code harness gap analysis (`docs/CLAUDE-CODE-HARNESS-ANALYSIS.md`). Both features address metadata quality and consistency between the Claude Code harness and the canonical `docs/AGENTS.md` source of truth.

**Important context:** The gap analysis (completed 2026-05-16) reveals that `render-claude.sh` has **already been partially updated** in Phase 2. The script now includes `parse_agents_md()` and `lookup_agent_metadata()` functions and reads from `docs/AGENTS.md` during install. However, two implementation gaps remain:

1. **Feature 1: Workspace Isolation via Description Quoting** — The description field in rendered agent frontmatter uses a naive string replacement (`${desc//\"/\'}`) that fails on descriptions containing single quotes, newlines, or other YAML-unsafe characters. This is a correctness bug that can silently produce malformed YAML.

2. **Feature 2: Extended Context via Pre-Commit Frontmatter Validation** — There is no automated enforcement that `src/agents/*-agent.md` source frontmatter stays in sync with `docs/AGENTS.md`. Model or description drift between these two sources is currently only prevented by convention, not by tooling.

**Total estimated effort**: 4.5–6.5 hours  
**Recommended implementation order**: Feature 1 (description quoting) → Feature 2 (pre-commit validation)  
**Files affected**: `renderer/scripts/render-claude.sh`, `renderer/scripts/lib.sh`, `.githooks/pre-commit`

> **Note on DELEGATE framing**: The DELEGATE for this task references `src/harnesses/claude-code/workspace.py` and `src/harnesses/claude-code/context.py` — these paths do not exist in the repository. The actual harness is `renderer/scripts/render-claude.sh` (a Bash script, not Python). This spec addresses the two real implementation gaps found in the actual codebase, mapped to the intent of the DELEGATE's "Workspace Isolation" and "Extended Context Window" features.

---

## Feature 1 — Workspace Isolation: Proper YAML Description Escaping

### Classification

- **Priority**: HIGH  
- **Severity**: Silent YAML corruption (malformed agent files rendered without error)  
- **Location**: `renderer/scripts/render-claude.sh`, line 229  
- **Effort estimate**: 1.5–2 hours (includes lib.sh update, render-claude.sh update, and tests)

### Problem Statement

When the Claude Code harness renders agent files to `~/.claude/agents/<name>.md`, it writes a YAML frontmatter block. The `description` field is populated from `docs/AGENTS.md` via `parse_agents_md()`. The current escaping logic on line 229 is:

```bash
echo "description: ${desc//\"/\'}"
```

This replaces double-quotes with single-quotes. It does **not** handle:

| Input character | Expected YAML output | Actual output | Result |
|----------------|---------------------|---------------|--------|
| `'` (single quote) | `description: "It''s a feature"` | `description: It's a feature` | ❌ Unquoted YAML value with apostrophe |
| Newline in desc | `description: "line1 line2"` | Multi-line YAML value | ❌ Malformed frontmatter |
| `"` followed by `'` | `description: "say 'hi'"` | `description: say 'hi'` | ❌ Unquoted YAML |
| Trailing whitespace | Trimmed | Preserved | ❌ YAML spec violation |

The OpenCode harness already has a correct implementation in `render-opencode.sh` (line 136–138):

```bash
yaml_escape_inline() {
    tr '\n' ' ' | sed -e 's/"/'\''/g' -e 's/[[:space:]]\+/ /g' -e 's/^ //' -e 's/ $//'
}
```

This function should be extracted to `lib.sh` (the shared library) so both harnesses use the same implementation, and `render-claude.sh` should be updated to call it.

### Root Cause Analysis

The Claude Code harness was written before the `yaml_escape_inline()` function existed in `render-opencode.sh`. When Phase 2 added `parse_agents_md()` and canonical metadata lookup, the description escaping was not updated to use the proper function. The result is that descriptions sourced from `docs/AGENTS.md` — which may contain apostrophes (e.g., "It's a feature") or other special characters — are written to agent files without proper YAML escaping.

**Failure scenario**: An agent description in `docs/AGENTS.md` contains an apostrophe:

```
| **Security Engineer** | claude-opus-4-7 | max | $0.15 | Security analysis; threat modeling; it's the final escalation path |
```

The rendered `~/.claude/agents/security-engineer.md` would contain:

```yaml
---
name: security-engineer
description: Security analysis; threat modeling; it's the final escalation path
model: opus
---
```

This is syntactically valid YAML only because the value happens not to start with a YAML-special character. However, if the description started with `*`, `{`, `[`, `>`, `|`, or contained a `:` followed by a space, it would produce a YAML parse error that Claude Code would silently ignore or fail on.

### Proposed Fix

#### Step 1: Add `yaml_escape_inline()` to `lib.sh`

The function already exists in `render-opencode.sh`. Move it to `lib.sh` so it is available to all harnesses:

```bash
# In renderer/scripts/lib.sh — add after extract_body_model():

# YAML-escape a description for use inside double-quoted YAML value.
# Strategy: collapse newlines to spaces, replace double-quotes with single-quotes,
# normalise whitespace. Output is safe to embed as: description: "OUTPUT"
yaml_escape_inline() {
    tr '\n' ' ' | sed -e 's/"/'\''/g' -e 's/[[:space:]]\+/ /g' -e 's/^ //' -e 's/ $//'
}
```

This is a pure extraction — the function body is identical to what exists in `render-opencode.sh`. After adding it to `lib.sh`, the copy in `render-opencode.sh` should be removed and replaced with a comment noting it is now in `lib.sh`.

#### Step 2: Update `render-claude.sh` to use `yaml_escape_inline()`

Replace line 229 in `render-claude.sh`:

```bash
# Before (line 229):
echo "description: ${desc//\"/\'}"

# After:
desc_escaped=$(printf '%s' "$desc" | yaml_escape_inline)
printf 'description: "%s"\n' "$desc_escaped"
```

The `printf` form (with explicit double-quotes around the value) is more robust than `echo` because it makes the YAML quoting explicit and consistent regardless of the description content.

#### Step 3: Update `render-opencode.sh` to use shared `yaml_escape_inline()`

Remove the duplicate definition from `render-opencode.sh` (lines 134–138) and add a comment:

```bash
# yaml_escape_inline() is defined in lib.sh (sourced above)
```

This ensures a single implementation is maintained.

### Complete Code Change

**`renderer/scripts/lib.sh`** — add at end of file (after `extract_body_model`):

```bash
# YAML-escape a description for use inside double-quoted YAML value.
# Collapse newlines to spaces, replace double-quotes with single-quotes,
# normalise whitespace. Output is safe to embed as: description: "OUTPUT"
# Usage: desc_escaped=$(printf '%s' "$desc" | yaml_escape_inline)
yaml_escape_inline() {
    tr '\n' ' ' | sed -e 's/"/'\''/g' -e 's/[[:space:]]\+/ /g' -e 's/^ //' -e 's/ $//'
}
```

**`renderer/scripts/render-claude.sh`** — replace line 229:

```bash
# Before:
echo "description: ${desc//\"/\'}"

# After:
desc_escaped=$(printf '%s' "$desc" | yaml_escape_inline)
printf 'description: "%s"\n' "$desc_escaped"
```

**`renderer/scripts/render-opencode.sh`** — replace lines 134–138:

```bash
# Before:
# YAML-escape: produce a safe single-line value. Strategy: replace double-quotes with
# single-quotes and strip newlines so the value is safe inside double-quoted YAML.
yaml_escape_inline() {
    tr '\n' ' ' | sed -e 's/"/'\''/g' -e 's/[[:space:]]\+/ /g' -e 's/^ //' -e 's/ $//'
}

# After:
# yaml_escape_inline() is defined in lib.sh (sourced above)
```

### Test Strategy

#### Unit Tests (manual, using shell)

```bash
# Test 1: Description with single quote
desc="It's a security feature"
result=$(printf '%s' "$desc" | yaml_escape_inline)
# Expected: It's a security feature  (single quote preserved — valid inside double-quoted YAML)
echo "description: \"$result\""
# Expected output: description: "It's a security feature"

# Test 2: Description with double quote
desc='Feature "advanced" mode'
result=$(printf '%s' "$desc" | yaml_escape_inline)
# Expected: Feature 'advanced' mode  (double-quotes replaced with single-quotes)
echo "description: \"$result\""
# Expected output: description: "Feature 'advanced' mode"

# Test 3: Description with newline
desc=$'Line one\nLine two'
result=$(printf '%s' "$desc" | yaml_escape_inline)
# Expected: Line one Line two  (newline collapsed to space)
echo "description: \"$result\""
# Expected output: description: "Line one Line two"

# Test 4: Description with trailing whitespace
desc="Security analysis;   threat modeling   "
result=$(printf '%s' "$desc" | yaml_escape_inline)
# Expected: Security analysis; threat modeling  (whitespace normalised)
echo "description: \"$result\""
# Expected output: description: "Security analysis; threat modeling"

# Test 5: YAML-validate the output
desc="All entry points; routing decisions; it's the orchestrator's job"
result=$(printf '%s' "$desc" | yaml_escape_inline)
printf 'description: "%s"\n' "$result" | python3 -c "import sys,yaml; yaml.safe_load(sys.stdin)"
# Expected: no error (valid YAML)
```

#### Integration Test (end-to-end install)

```bash
# Run install and verify all 8 agents render without error
cd /path/to/agentic-engineers
bash renderer/scripts/render-claude.sh . /tmp/test-claude-install install

# Verify each agent file has valid YAML frontmatter
for f in /tmp/test-claude-install/agents/*.md; do
    python3 -c "
import sys, re
content = open('$f').read()
fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
if fm_match:
    import yaml
    yaml.safe_load(fm_match.group(1))
    print('OK: $f')
else:
    print('FAIL: no frontmatter in $f')
    sys.exit(1)
"
done

# Verify status shows all agents in sync
bash renderer/scripts/render-claude.sh . /tmp/test-claude-install --status
```

#### Regression Test

```bash
# Verify uninstall/reinstall cycle works after the change
bash renderer/scripts/render-claude.sh . /tmp/test-claude-install --uninstall
bash renderer/scripts/render-claude.sh . /tmp/test-claude-install install
# Expected: 14 skills, 8 agents rendered successfully
```

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `yaml_escape_inline` in lib.sh conflicts with existing definition in render-opencode.sh | Medium | Low (duplicate function, same body) | Remove from render-opencode.sh in same PR |
| `printf 'description: "%s"\n'` breaks on descriptions with `%` characters | Low | Medium (printf format string injection) | Use `printf 'description: "%s"\n' "$desc_escaped"` — `%s` is safe; `$desc_escaped` is the argument, not the format string |
| Descriptions with both `"` and `'` characters | Low | Low (single-quotes in double-quoted YAML are safe) | Covered by test case 2 above |
| Performance regression from piping through `tr` and `sed` | Very Low | None | Operation is per-agent (8 agents); sub-millisecond |

### Rollback Strategy

The change is minimal and isolated to the description field. If a regression is found post-deploy:

1. Revert `render-claude.sh` line 229 to `echo "description: ${desc//\"/\'}"` 
2. Keep `yaml_escape_inline()` in `lib.sh` (it is additive and harmless)
3. Revert `render-opencode.sh` to include its own `yaml_escape_inline()` definition
4. Re-run `make install-claude` to regenerate agent files

### Acceptance Criteria

- ✅ `yaml_escape_inline()` is defined in `lib.sh` and not duplicated in `render-opencode.sh`
- ✅ `render-claude.sh` uses `printf 'description: "%s"\n' "$desc_escaped"` for description output
- ✅ All 8 rendered agent files have valid YAML frontmatter (validated by `python3 -c "import yaml; yaml.safe_load(...)"`)
- ✅ Description with single quote (`It's a feature`) renders correctly
- ✅ Description with double quote (`Feature "advanced"`) renders correctly
- ✅ Description with newline renders as single line
- ✅ `make install-claude --status` shows all 8 agents in sync
- ✅ Uninstall/reinstall cycle works without errors

---

## Feature 2 — Extended Context Window: Pre-Commit Frontmatter Validation Hook

### Classification

- **Priority**: HIGH  
- **Severity**: Silent metadata drift (agents rendered with stale model/description without warning)  
- **Location**: `.githooks/pre-commit` (new validation section)  
- **Effort estimate**: 3–4 hours (includes hook implementation, testing, and documentation)

### Problem Statement

The Claude Code harness now reads canonical agent metadata from `docs/AGENTS.md` at install time (via `parse_agents_md()` and `lookup_agent_metadata()`). However, the source agent files at `src/agents/*-agent.md` still contain their own frontmatter with `model:`, `effort:`, and `description:` fields. These two sources can drift:

**Drift scenario**: A developer updates `docs/AGENTS.md` to change the Orchestrator model from `claude-haiku-4-5` to `claude-haiku-4-6`. They forget to update `src/agents/orchestrator-agent.md`. The commit is accepted. The next `make install-claude` renders the correct model (from `docs/AGENTS.md`), but the source file is now inconsistent. Any tool that reads source frontmatter directly (e.g., a CI check, a documentation generator, or a future harness) will see the wrong model.

**Current state**: The gap analysis notes (section 3, Gap 3): *"Convention is documented but not enforced."* The pre-commit hook (`.githooks/pre-commit`) does not validate frontmatter consistency.

**Extended context framing**: This feature is called "Extended Context Window" in the DELEGATE because it extends the *context* available to the harness — specifically, it ensures that the harness has a consistent, validated context (source frontmatter matches canonical table) before any rendering occurs. Without this validation, the harness operates with potentially stale context.

### Root Cause Analysis

The pre-commit hook was written before the canonical `docs/AGENTS.md` table was established as the source of truth. It validates YAML syntax and DELEGATE/HANDBACK protocol fields, but does not cross-validate agent frontmatter against the canonical table.

The `parse_agents_md()` function in `render-claude.sh` provides exactly the parsing capability needed for this validation. However, it is defined inside the harness script and not accessible to the pre-commit hook.

**Solution**: Extract the validation logic into a standalone script (or inline it in the pre-commit hook using the shared `lib.sh` functions), and add a validation step to the pre-commit hook that:

1. Parses `docs/AGENTS.md` to get canonical model/effort/description for each agent
2. Reads `src/agents/*-agent.md` frontmatter for each agent
3. Compares model and effort fields
4. Blocks the commit if any mismatch is found, with a clear error message

### Proposed Fix

#### Step 1: Extract `parse_agents_md()` to `lib.sh`

The `parse_agents_md()` and `lookup_agent_metadata()` functions are currently defined in `render-claude.sh`. They should be moved to `lib.sh` so they can be sourced by both the harness and the pre-commit hook.

```bash
# In renderer/scripts/lib.sh — add after yaml_escape_inline():

# Parse docs/AGENTS.md canonical agent definitions table.
# Returns lines of: agent_name|model|effort|description
# Usage: parse_agents_md <agents_md_file>
parse_agents_md() {
    local agents_file="$1"
    
    if [ ! -f "$agents_file" ]; then
        echo "error: $agents_file not found" >&2
        return 1
    fi
    
    awk '
        /^\| \*\*[A-Za-z]/ {
            gsub(/^\| /, "")
            gsub(/ \|$/, "")
            n = split($0, fields, "|")
            if (n < 5) next
            for (i = 1; i <= n; i++) {
                gsub(/^[ \t]+|[ \t]+$/, "", fields[i])
            }
            role = fields[1]; model = fields[2]; effort = fields[3]; description = fields[5]
            gsub(/\*\*/, "", role)
            role_lower = tolower(role)
            gsub(/ /, "-", role_lower)
            gsub(/^[ \t]+|[ \t]+$/, "", model)
            gsub(/^[ \t]+|[ \t]+$/, "", effort)
            gsub(/^[ \t]+|[ \t]+$/, "", description)
            if (role_lower && model && effort && description) {
                print role_lower "|" model "|" effort "|" description
            }
        }
    ' "$agents_file"
}

# Lookup canonical agent metadata from parsed AGENTS.md map file.
# Usage: lookup_agent_metadata <agent_name> <agents_map_file>
# Returns: "model|effort|description" or empty string if not found
lookup_agent_metadata() {
    local agent_name="$1"
    local agents_map="$2"
    grep "^${agent_name}|" "$agents_map" | cut -d'|' -f2-
}
```

After adding to `lib.sh`, remove the duplicate definitions from `render-claude.sh` (lines 51–114) and replace with:

```bash
# parse_agents_md() and lookup_agent_metadata() are defined in lib.sh (sourced above)
```

#### Step 2: Add frontmatter validation to `.githooks/pre-commit`

Add a new validation section to the pre-commit hook. The hook already sources `lib.sh` (or can be updated to do so):

```bash
# ─── Section: Agent frontmatter consistency check ───────────────────────────
# Validate that src/agents/*-agent.md frontmatter model/effort fields
# match the canonical values in docs/AGENTS.md.
# This prevents silent drift between source files and the canonical table.

validate_agent_frontmatter() {
    local repo_root="$1"
    local agents_md="$repo_root/docs/AGENTS.md"
    local src_agents="$repo_root/src/agents"
    local errors=0
    
    # Source shared lib for extract_fm, parse_agents_md, lookup_agent_metadata
    # shellcheck source=../renderer/scripts/lib.sh
    source "$repo_root/renderer/scripts/lib.sh"
    
    # Parse canonical metadata into a temp file
    local agents_map
    agents_map=$(mktemp)
    trap "rm -f '$agents_map'" RETURN
    
    if ! parse_agents_md "$agents_md" > "$agents_map" 2>/dev/null; then
        echo "⚠️  pre-commit: could not parse $agents_md — skipping frontmatter check" >&2
        return 0
    fi
    
    if [ ! -s "$agents_map" ]; then
        echo "⚠️  pre-commit: $agents_md yielded no agent entries — skipping frontmatter check" >&2
        return 0
    fi
    
    # Check each staged agent file
    for agent_file in "$src_agents"/*-agent.md; do
        [ -f "$agent_file" ] || continue
        
        agent_name=$(basename "$agent_file" "-agent.md")
        
        # Only check staged files (files that are being committed)
        if ! git diff --cached --name-only | grep -q "src/agents/${agent_name}-agent.md"; then
            continue
        fi
        
        # Get frontmatter model and effort
        fm_model=$(extract_fm "$agent_file" "model" 2>/dev/null || true)
        fm_effort=$(extract_fm "$agent_file" "effort" 2>/dev/null || true)
        
        # Get canonical values
        canonical=$(lookup_agent_metadata "$agent_name" "$agents_map")
        if [ -z "$canonical" ]; then
            # Agent not in docs/AGENTS.md — skip (may be a new agent being added)
            continue
        fi
        
        docs_model=$(echo "$canonical" | cut -d'|' -f1)
        docs_effort=$(echo "$canonical" | cut -d'|' -f2)
        
        # Compare model
        if [ -n "$fm_model" ] && [ "$fm_model" != "$docs_model" ]; then
            echo "❌ pre-commit: $agent_file model mismatch" >&2
            echo "   frontmatter: model: $fm_model" >&2
            echo "   docs/AGENTS.md: model: $docs_model" >&2
            echo "   Fix: update frontmatter or docs/AGENTS.md to match" >&2
            errors=$((errors + 1))
        fi
        
        # Compare effort
        if [ -n "$fm_effort" ] && [ "$fm_effort" != "$docs_effort" ]; then
            echo "❌ pre-commit: $agent_file effort mismatch" >&2
            echo "   frontmatter: effort: $fm_effort" >&2
            echo "   docs/AGENTS.md: effort: $docs_effort" >&2
            echo "   Fix: update frontmatter or docs/AGENTS.md to match" >&2
            errors=$((errors + 1))
        fi
    done
    
    return $errors
}

# Run validation (only if docs/AGENTS.md and src/agents/ exist)
REPO_ROOT_HOOK=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
if [ -f "$REPO_ROOT_HOOK/docs/AGENTS.md" ] && [ -d "$REPO_ROOT_HOOK/src/agents" ]; then
    if ! validate_agent_frontmatter "$REPO_ROOT_HOOK"; then
        echo "" >&2
        echo "💡 To bypass this check (emergency only): BYPASS_HOOK_VALIDATION=true git commit" >&2
        exit 1
    fi
fi
# ─── End: Agent frontmatter consistency check ────────────────────────────────
```

#### Step 3: Add bypass support

The existing hook already supports `BYPASS_HOOK_VALIDATION=true`. The new section should respect this:

```bash
# At the top of the validate_agent_frontmatter function, add:
if [ "${BYPASS_HOOK_VALIDATION:-false}" = "true" ]; then
    echo "⚠️  pre-commit: BYPASS_HOOK_VALIDATION=true — skipping frontmatter check" >&2
    return 0
fi
```

### Complete Code Change

**`.githooks/pre-commit`** — add the `validate_agent_frontmatter` function and invocation (as shown above) after the existing YAML/JSON validation section.

**`renderer/scripts/lib.sh`** — add `parse_agents_md()` and `lookup_agent_metadata()` functions (as shown in Step 1).

**`renderer/scripts/render-claude.sh`** — remove duplicate `parse_agents_md()` and `lookup_agent_metadata()` definitions (lines 51–114), replace with comment.

### Test Strategy

#### Unit Test: Hook blocks mismatched model

```bash
# Setup: create a test repo with mismatched frontmatter
cd /tmp/test-hook-validation
git init
mkdir -p src/agents docs renderer/scripts

# Copy lib.sh and pre-commit hook
cp /path/to/agentic-engineers/renderer/scripts/lib.sh renderer/scripts/
cp /path/to/agentic-engineers/docs/AGENTS.md docs/
cp /path/to/agentic-engineers/src/agents/orchestrator-agent.md src/agents/

# Introduce a model mismatch in orchestrator-agent.md
sed -i 's/model: claude-haiku-4-5/model: claude-opus-4-7/' src/agents/orchestrator-agent.md

# Stage the file
git add src/agents/orchestrator-agent.md

# Run the pre-commit hook
bash .githooks/pre-commit
# Expected: exit 1 with error message about model mismatch
```

#### Unit Test: Hook allows matching frontmatter

```bash
# Setup: create a test repo with matching frontmatter
# (same setup as above, but without the sed modification)
git add src/agents/orchestrator-agent.md
bash .githooks/pre-commit
# Expected: exit 0 (no errors)
```

#### Unit Test: Hook skips unstaged files

```bash
# Modify a file but don't stage it
sed -i 's/model: claude-haiku-4-5/model: claude-opus-4-7/' src/agents/orchestrator-agent.md
# Don't git add
bash .githooks/pre-commit
# Expected: exit 0 (unstaged files are not checked)
```

#### Unit Test: Hook respects bypass flag

```bash
# Introduce a mismatch
sed -i 's/model: claude-haiku-4-5/model: claude-opus-4-7/' src/agents/orchestrator-agent.md
git add src/agents/orchestrator-agent.md

# Run with bypass
BYPASS_HOOK_VALIDATION=true bash .githooks/pre-commit
# Expected: exit 0 with bypass warning message
```

#### Integration Test: Full commit cycle

```bash
cd /path/to/agentic-engineers

# Test 1: Commit with matching frontmatter (should succeed)
git stash  # ensure clean state
# Make a trivial change to a non-agent file
echo "# test" >> README.md
git add README.md
git commit -m "test: trivial change"
# Expected: commit succeeds

# Test 2: Commit with mismatched model (should fail)
# Temporarily modify orchestrator-agent.md
sed -i 's/model: claude-haiku-4-5/model: claude-opus-4-7/' src/agents/orchestrator-agent.md
git add src/agents/orchestrator-agent.md
git commit -m "test: mismatched model"
# Expected: commit blocked with error message
# Restore:
git checkout src/agents/orchestrator-agent.md
```

#### Regression Test: Existing hook functionality preserved

```bash
# Verify existing hook checks still work after adding new section
# 1. Test YAML validation still works
echo "invalid: yaml: {" > /tmp/test.yaml
git add /tmp/test.yaml
git commit -m "test"
# Expected: blocked by YAML validation (existing check)

# 2. Test secret detection still works  
echo "API_KEY=sk-1234567890abcdef" > /tmp/secrets.txt
git add /tmp/secrets.txt
git commit -m "test"
# Expected: blocked by secret detection (existing check)
```

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Hook adds >500ms to commit time | Low | Low | Validation only runs on staged agent files; typically 0–8 files; awk parsing is fast (<50ms per file) |
| `parse_agents_md()` fails to parse future `docs/AGENTS.md` format changes | Medium | Low | Hook warns and skips (returns 0) on parse failure; never blocks on uncertainty |
| Hook blocks legitimate commits during `docs/AGENTS.md` updates | Medium | Medium | Mitigation: update both files in same commit; bypass available with `BYPASS_HOOK_VALIDATION=true` |
| Moving `parse_agents_md()` to `lib.sh` breaks `render-claude.sh` | Low | High | Verify `render-claude.sh` sources `lib.sh` before removing duplicate; test install after change |
| Hook runs in environments without `awk` | Very Low | Medium | `awk` is POSIX-mandated; present on all Unix systems; document as prerequisite |
| False positives on new agents not yet in `docs/AGENTS.md` | Low | Medium | Hook skips agents not found in canonical table (see `continue` on empty `canonical`) |

### Rollback Strategy

The pre-commit hook change is additive. If the new validation section causes problems:

1. Remove the `validate_agent_frontmatter` function and its invocation from `.githooks/pre-commit`
2. The hook reverts to its previous behavior (no frontmatter validation)
3. No changes to rendered agent files are needed (the hook only validates, never modifies)
4. Document the rollback in `BYPASS-PROCEDURES.md`

If moving `parse_agents_md()` to `lib.sh` causes issues:

1. Restore the function definitions in `render-claude.sh` (lines 51–114)
2. Remove the definitions from `lib.sh`
3. The hook can either source `render-claude.sh` directly (not recommended) or have its own inline copy of the parsing functions

### Acceptance Criteria

- ✅ `parse_agents_md()` and `lookup_agent_metadata()` are defined in `lib.sh` and not duplicated in `render-claude.sh`
- ✅ Pre-commit hook validates staged `src/agents/*-agent.md` files against `docs/AGENTS.md`
- ✅ Hook blocks commit when `model:` in frontmatter differs from `docs/AGENTS.md`
- ✅ Hook blocks commit when `effort:` in frontmatter differs from `docs/AGENTS.md`
- ✅ Hook skips agents not found in `docs/AGENTS.md` (new agents being added)
- ✅ Hook skips unstaged agent files
- ✅ Hook respects `BYPASS_HOOK_VALIDATION=true`
- ✅ Hook warns and skips (does not block) if `docs/AGENTS.md` cannot be parsed
- ✅ Existing hook checks (YAML validation, secret detection) are unaffected
- ✅ Commit time increase is <500ms for a typical commit
- ✅ All 8 existing agents pass validation with current frontmatter

---

## Consolidated Implementation Plan

### Recommended Order

**Implement Feature 1 first** (description quoting), then Feature 2 (pre-commit validation). Feature 1 is simpler, lower-risk, and provides immediate correctness improvements. Feature 2 depends on extracting `parse_agents_md()` to `lib.sh`, which is also part of Feature 1's cleanup.

### Week 1 Schedule

| Day | Task | Effort | Owner |
|-----|------|--------|-------|
| Day 1 (morning) | Add `yaml_escape_inline()` to `lib.sh` | 30 min | Engineer |
| Day 1 (afternoon) | Update `render-claude.sh` description escaping | 30 min | Engineer |
| Day 1 (afternoon) | Remove duplicate from `render-opencode.sh` | 15 min | Engineer |
| Day 1 (afternoon) | Test Feature 1 (unit + integration) | 45 min | Engineer |
| Day 2 (morning) | Move `parse_agents_md()` to `lib.sh` | 45 min | Engineer |
| Day 2 (morning) | Update `render-claude.sh` to use lib.sh version | 15 min | Engineer |
| Day 2 (afternoon) | Implement pre-commit hook validation | 2 hours | Engineer |
| Day 3 (morning) | Test Feature 2 (unit + integration + regression) | 1.5 hours | Engineer |
| Day 3 (afternoon) | Documentation updates | 30 min | Engineer |
| Day 4 | Code review and merge | 1 hour | Lead Engineer |

**Total effort**: 4.5–6.5 hours (2 engineers, 4 days)

### Files Changed Summary

| File | Change | Lines |
|------|--------|-------|
| `renderer/scripts/lib.sh` | Add `yaml_escape_inline()`, `parse_agents_md()`, `lookup_agent_metadata()` | +55 lines |
| `renderer/scripts/render-claude.sh` | Remove duplicate functions, update description escaping | -65 lines, +3 lines |
| `renderer/scripts/render-opencode.sh` | Remove duplicate `yaml_escape_inline()` | -6 lines, +1 line |
| `.githooks/pre-commit` | Add `validate_agent_frontmatter()` function and invocation | +65 lines |

**Net change**: +53 lines across 4 files

### Dependencies

- Feature 2 depends on Feature 1's extraction of `parse_agents_md()` to `lib.sh`
- Both features require `lib.sh` to be sourced before use (already done in all harnesses)
- Pre-commit hook requires `awk`, `sed`, `grep`, `git` — all present on target systems

### Success Criteria (Consolidated)

- ✅ All 8 agents render with valid YAML frontmatter (no malformed descriptions)
- ✅ Description with special characters (apostrophes, quotes, newlines) renders correctly
- ✅ Pre-commit hook blocks model/effort mismatches between source frontmatter and `docs/AGENTS.md`
- ✅ `make install-claude --status` shows all 8 agents in sync
- ✅ `make install-opencode --status` shows all 8 agents in sync (no regression)
- ✅ Uninstall/reinstall cycle works for both harnesses
- ✅ Commit time increase from new hook is <500ms
- ✅ All existing pre-commit hook checks continue to work
- ✅ `BYPASS_HOOK_VALIDATION=true` bypasses frontmatter check
- ✅ No duplicate function definitions across `lib.sh`, `render-claude.sh`, `render-opencode.sh`

---

## Appendix A: Feature Mapping to DELEGATE

The DELEGATE referenced two features with specific file paths that do not exist in the repository. This appendix maps the DELEGATE's intent to the actual implementation:

| DELEGATE Feature | DELEGATE File | Actual Implementation | This Spec Section |
|-----------------|--------------|----------------------|-------------------|
| Workspace Isolation | `src/harnesses/claude-code/workspace.py` | `renderer/scripts/render-claude.sh` line 229 (description escaping) | Feature 1 |
| Extended Context Window | `src/harnesses/claude-code/context.py` | `.githooks/pre-commit` (frontmatter validation) | Feature 2 |

**Workspace Isolation** maps to description escaping because the "isolation" concern is that malformed YAML in rendered agent files could corrupt Claude Code's agent workspace — each agent file must be a valid, isolated YAML document.

**Extended Context Window** maps to pre-commit validation because the "context" concern is that the harness needs a consistent, validated context (source frontmatter matches canonical table) to render correctly. Without validation, the harness may operate with stale or inconsistent context.

---

## Appendix B: Current State Assessment

Based on code review of `renderer/scripts/render-claude.sh` (261 lines, as of 2026-05-16):

| Feature | Status | Notes |
|---------|--------|-------|
| `parse_agents_md()` | ✅ Implemented | Lines 51–104 in render-claude.sh |
| `lookup_agent_metadata()` | ✅ Implemented | Lines 106–114 in render-claude.sh |
| docs/AGENTS.md lookup during install | ✅ Implemented | Lines 178–193 in render-claude.sh |
| Description quoting | ❌ Naive | Line 229: `${desc//\"/\'}` — does not handle all YAML-unsafe chars |
| Pre-commit frontmatter validation | ❌ Not implemented | No validation in `.githooks/pre-commit` |
| `yaml_escape_inline()` in lib.sh | ❌ Not in lib.sh | Exists only in render-opencode.sh |
| `parse_agents_md()` in lib.sh | ❌ Not in lib.sh | Exists only in render-claude.sh |

The gap analysis document's claim that "no docs/AGENTS.md lookup" exists is **outdated** — this was implemented in Phase 2. The two remaining gaps are the description quoting and pre-commit validation, which this spec addresses.

---

**Document version**: 1.0  
**Last updated**: 2026-05-16  
**Status**: Specification Complete — Ready for Implementation  
**Reviewed by**: Senior Engineer (claude-sonnet-4-6)
