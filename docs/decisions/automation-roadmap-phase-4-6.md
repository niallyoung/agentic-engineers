# Automation Roadmap (Phase 4–6) — historical record

**Status:** historical. Moved out of `docs/CONTRIBUTING/README.md` on 2026-09-02 because
it records roadmap state and unshipped design intent, not guidance a contributor needs to
follow. Retained because the "not done" items below are real, unclosed findings.

Nothing in this document describes current behavior unless it is explicitly marked as
shipped. Treat `src/AGENTS.md` and `docs/PROTOCOL.md` as authoritative for what the
framework actually does today.

---

## Automation Roadmap (Phase 4–6)

This section consolidates opportunities to automate manual workflows and reduce human churn.

### Phase 4: Git Hooks Enforcement (HIGH PRIORITY)

**Current State:** Pre-commit and pre-push hooks validate but only warn; they do not reject commits.
**Gap:** Several checks should REJECT commits instead of warning.

#### 4.1 Pre-Commit: File Permissions Enforcement
- **Implementation:** Update `.githooks/pre-commit` to REJECT commits with executable `.md`, `.yaml`, `.json` files
- **Reject if:** Scripts are NOT executable (`+x`)
- **Allow bypass:** `ENFORCE_PERMS=0` for git-related workflows (rare)
- **Effort:** 30 minutes

#### 4.2 Pre-Commit: Staging Purity
- **Implementation:** Validate that only staged changes are committed (no uncommitted changes outside staging area)
- **Reject if:** `git status --short` shows unstaged changes
- **Exception:** `.gitignore`'d files are OK
- **Effort:** 45 minutes

#### 4.3 Commit Message Task ID Enforcement
- **Current State:** `commit-msg` hook validates format; warnings are informational only
- **Gap:** Task ID format and conventional commits should be ERRORS (not warnings)
- **Implementation:**
  - Require task ID format: `YYYY-MM-DD-kebab-case`
  - Require conventional commit: `type(scope): subject`
  - Reject if missing (allow `GIT_SKIP_HOOKS=1` bypass with audit trail)
- **Effort:** 20 minutes

**Implementation Priority:**
| Item | Effort | Impact | Blocker? |
|------|--------|--------|----------|
| File permissions REJECT | 30min | Medium | No |
| Staging purity check | 45min | Medium | No |
| Task ID enforcement | 20min | High | No |

---

### Phase 5: PR & Merge Automation (MEDIUM PRIORITY)

#### 5.1 PR Body Auto-Generation (Future)
- **Input:** Commit messages + SPEC.md cross-references
- **Output:** Structured PR body (scannable, consistent)
- **New skill:** `pr-body-generator` (reusable)
- **Trigger:** CI on PR creation, or on-demand
- **Effort:** 2–3 hours

#### 5.2 Merge Strategy Enforcement (Future)
- **Policy:** Always squash feature branches
- **Implementation:** GitHub branch protection (simpler than custom workflow)
- **Effort:** 1 hour

#### 5.3 Post-Merge Branch Cleanup (NICE-TO-HAVE)
- **Current:** Manual `gh pr merge --delete-branch`
- **Future:** GitHub Actions post-merge workflow
- **Effort:** 30 minutes

---

### Phase 6: Extended Memory & Observability (FUTURE)

**Current Status:** Code ready for merge (all CI checks passing, no regressions).

**Deferred Phases:**
- **Phase 5:** External memory-API infrastructure (REST/GraphQL backend)

---

## OpenCode Renderer (Phase 4 Details) — PARTIALLY IMPLEMENTED

The `renderer/scripts/render-opencode.sh` emits agent frontmatter and `opencode.jsonc`
for OpenCode integration. Two defects were originally identified: a no-op `thinking:`
block, and overstated permission enforcement. **Only the first is fixed.** The second —
per-role spawn/permission gating — is **not implemented**, and this section previously
claimed otherwise. That was corrected here on 2026-08-09 after independent verification
(see below); treat the "IMPLEMENTED"/"COMPLETE" language that used to be on this
section as having been inaccurate.

### Defect 1: No-op `thinking:` Block — FIXED

**Was:** Emitted a `thinking:` key, but OpenCode ignores it (not in `KNOWN_KEYS`), so extended thinking was never enabled for principal-engineer / security-engineer.
**Fix (done):** The `thinking:` block was removed and replaced with the supported `variant:` key (`effort_to_variant`: medium→medium, high/max→high, low→omit). `variant` is in OpenCode `KNOWN_KEYS` and maps to Anthropic extended-thinking budgets. Protocol metadata (`role`/`accepts`/`returns`), which are also non-`KNOWN_KEYS`, were moved under the recognized `options:` block so they are preserved rather than silently swept away.

### Defect 2: Uniform Permissions vs. Claimed Granularity — NOT IMPLEMENTED

**Verified current behavior (2026-08-09):** `render-opencode.sh` (around lines 353-360)
emits a single **global** `permission` block into `opencode.jsonc` — not a per-role
one:

```json
"permission": {
  "read": "allow",
  "edit": "allow",
  "bash": "allow",
  "task": "allow",
  "glob": "allow",
  "grep": "allow",
  "webfetch": "allow"
}
```

Every agent gets this same allow-all block, including `task` — the permission that
gates spawning a sub-agent. The renderer's own generated `AGENTS.md` rules file says as
much explicitly ("All agents use uniform **allow-all** permissions"). There is no
`emit_permission_block()` function and no per-role permission lookup in the OpenCode
renderer today — that was aspirational, not shipped.

**What the real permission model is, and where it lives:** the intended least-privilege
design — including which roles may spawn sub-agents — is the **tools-frontmatter
permission model** defined per-role in `src/agents/*-agent.md` (`tools: [spawn_subagent]`
vs. `tools: []`) and documented in
`src/AGENTS.md` § Tools-Frontmatter Permission Model.
Per that document, spawn authority (`spawn_subagent`) is granted to **five** roles —
orchestrator, senior-engineer, lead-engineer, principal-engineer, and security-engineer
— not just orchestrator and senior-engineer as an earlier version of the matrix below
implied. **No renderer currently propagates this model into any harness.** It is a
contract each agent's own definition and prompt must self-enforce; nothing in
OpenCode's (or any other harness's) generated config blocks or refuses an unauthorized
or over-deep spawn. Fan-out-5 is likewise unenforced. The depth-3 limit and ancestry cycle
detection are a partial exception (see `src/AGENTS.md` § Recursion Limits): the Claude
harness's `PreToolUse` guard, `renderer/scripts/claude-delegate-guard.py`, *does* reject
a DELEGATE declaring `depth` > 3 or naming the target role in its own `ancestry`. But
both fields are optional, the guard sees one spawn at a time, and no other harness has
an equivalent — so a DELEGATE that simply omits them is unchecked.

### Per-Role Permission Matrix — INTENDED DESIGN, NOT YET IMPLEMENTED BY ANY RENDERER

The table below reflects the *intended* least-privilege design (spawn authority per
`src/AGENTS.md`'s Tools-Frontmatter Permission Model; other columns per this project's
original least-privilege intent for OpenCode). None of it is live — every OpenCode
agent currently gets the uniform allow-all block shown above instead.

| Role | read | glob | grep | webfetch | websearch | edit | bash | task (spawn) |
|------|:----:|:----:|:----:|:--------:|:---------:|:----:|:----:|:----:|
| orchestrator      | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| principal-engineer| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| senior-engineer   | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| engineer          | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| lead-engineer     | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| quality-engineer  | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| security-engineer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| model-engineer    | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

**Rationale (design intent, not current behavior):** Orchestrator routes without direct
edits. Review roles are read-only. Implementation roles get edit/bash. Spawn authority
(`task`) is intended for orchestrator, senior-engineer, lead-engineer,
principal-engineer, and security-engineer per `src/AGENTS.md`; engineer,
quality-engineer, and model-engineer are meant to be leaves.

### Implementation Steps (Phase 4) — OUTSTANDING

1. ✅ Removed the `thinking:` case from `render-opencode.sh`
2. ✅ Added per-role reasoning `variant` emission (`effort_to_variant`)
3. ✅ Provider blocks in `opencode.jsonc` declare `reasoning: true` per model
4. ❌ **Not done:** replace the uniform global `permission` block with a least-privilege per-role lookup
5. ❌ **Not done:** gate `task` permission to the five spawn-authorized roles per `src/AGENTS.md`
6. ❌ **Not done:** differentiate `websearch` by role (currently uniform `allow`, bundled into the same global block)
7. ✅ Moved no-op protocol keys (`role`/`accepts`/`returns`) under the recognized `options:` block
8. ❓ **Unverified:** whether `harness-opencode-feature-sync` reports drift for this gap — re-run it rather than trusting the old "No drift detected" claim, since that claim was made about a permission model that (per this correction) was never actually shipped
