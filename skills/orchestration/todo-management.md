# TODO Management Skill — Planning & Task Tracking

**Used by:** Orchestrator (daily), Lead Engineer, Principal Engineer, Security Engineer (as needed)

**Model:** Haiku 4.5 | **Effort:** low | **Token Multiplier:** 1x

---

## What This Role DOES

- ✅ Creates task-scoped TODO.md files in project directories for planning active work
- ✅ Tracks task completion with clear status markers (TODO, IN_PROGRESS, DONE, BLOCKED)
- ✅ Keeps recently completed items visible for a short window (24-48 hours) before cleanup
- ✅ Archives old tasks to keep main TODO.md concise and actionable
- ✅ Uses TODO.md as the single source of truth for active planning (not scattered .md files)
- ✅ Escalates BLOCKED tasks with clear blocker description
- ✅ Provides daily checkpoint: "X tasks complete, Y in-progress, Z blocked"

---

## What This Role DOES NOT DO

- ❌ Does not plan work in git branches or comments
- ❌ Does not scatter tasks across multiple TODO files (consolidate in project root)
- ❌ Does not leave completed tasks indefinitely (archive after 2 days)
- ❌ Does not create TODO items without clear ownership or acceptance criteria
- ❌ Does not skip the BLOCKED state — all blockers must be documented
- ❌ Does not use TODO.md as a general-purpose notes file (structured planning only)

---

## TODO.md Format

### Location
- **Project root:** `./TODO.md` (single source of truth for that project)
- **Multi-project sessions:** Create separate TODO in each project directory

### Structure

```markdown
# TODO — [Project Name] | [Session Date]

**Session Owner:** [Role name] | **Duration:** [start–end] | **Status:** [ACTIVE|PAUSED|COMPLETE]

## Current Checkpoint
- ✅ **Completed:** 5 tasks (avg 12 min each)
- 🔄 **In Progress:** 2 tasks (blockers: auth config missing)
- 📋 **Backlog:** 8 tasks

## Active Tasks (In-Progress)

### 1. [TITLE] — [Owner Role]
- **Status:** IN_PROGRESS
- **Acceptance Criteria:**
  - [ ] Criterion 1
  - [ ] Criterion 2
- **Effort:** [low|medium|high] — ~[N] minutes
- **Notes:** Started [time], current blocker: [description]

### 2. [TITLE] — [Owner Role]
- **Status:** IN_PROGRESS
- **Acceptance Criteria:** ...
- **Blocker:** [clear description, escalation path]

---

## Recently Completed (Cleanup in 24h)

### [TITLE] — [Owner Role] ✅
- **Completed at:** [HH:MM UTC]
- **Duration:** [elapsed time]
- **Result:** [brief summary, link to commit/PR if applicable]
- **Next step:** [what task this unblocks, or none]

---

## Backlog (Next Up)

### [TITLE] — [Assigned to Role]
- **Effort:** [low|medium|high]
- **Dependencies:** [other tasks to complete first, or none]
- **Notes:** [context from user, urgency, etc.]

---

## Blocked Tasks

### [TITLE] — [Owner]
- **Blocker:** [what's preventing progress]
- **Escalation:** [to which role, why]
- **Expected unblock:** [time estimate, or pending user decision]

---

## Metrics (Optional — Updated Hourly)

- **Session start:** [HH:MM UTC]
- **Tasks completed:** [N]
- **Avg task duration:** [N] min
- **Estimated remaining:** [HH] hours
- **Token burn:** [optional — if tracking usage]
- **Model efficiency:** [optional — which roles performed best]
```

---

## Daily Workflow (Orchestrator)

### Morning (Session Start)
1. Create fresh `TODO.md` for the session (or reuse if continuing)
2. List all incoming tasks from user in **Backlog**
3. Set initial checkpoint: "0 complete, X backlog, Y in-progress"
4. Mark first task(s) as **IN_PROGRESS**, assign to roles

### Hourly (Checkpoint)
1. Update **Current Checkpoint** with completed count
2. Move any blockers to **Blocked Tasks** section
3. Note blockers and escalation path
4. Update **Estimated remaining**

### Task Completion
1. Move task from IN_PROGRESS to **Recently Completed** with:
   - Completion timestamp
   - Duration (actual vs. estimate)
   - Brief result summary
   - What task this unblocks (if any)
2. Mark next backlog task as IN_PROGRESS
3. Update checkpoint

### End of Session (or 24h mark)
1. Archive completed tasks: `cp TODO.md .TODO.archive.$(date +%Y-%m-%d).md`
2. Remove tasks from **Recently Completed** that are >24h old
3. Keep **Backlog** and any **Blocked** for next session
4. Note final metrics: tasks completed, total duration, efficiency

---

## Escalation & Blocking

### When to Mark as BLOCKED
- External dependency missing (config, credentials, repo access)
- Task exceeds assigned role's expertise — needs escalation
- User decision pending (design choice, feature scope)
- Service/system issue preventing work (deployment failed, database down)

### Escalation Path (from Orchestrator's TODO)

```
Orchestrator identifies blocker
  → Notes blocker in TODO.md with clear reason
  → If blocker is role expertise: escalate to Senior/Lead/Principal
  → If blocker is external (user decision): mark "AWAITING_USER_INPUT"
  → If blocker is technical (service down): mark with ETA
  → Check back every 15 min if critical path, else hourly
```

---

## Examples

### Example 1: Simple Session (3 backlog, 1 in-progress)

```markdown
# TODO — {service-name} TypeScript Fixes | 2026-04-24

**Session Owner:** Engineer | **Duration:** 14:00–14:45 UTC | **Status:** ACTIVE

## Current Checkpoint
- ✅ **Completed:** 1 task (14 min)
- 🔄 **In Progress:** 1 task
- 📋 **Backlog:** 2 tasks

## Active Tasks (In-Progress)

### 1. Fix CallbackPage infinite loop — Engineer
- **Status:** IN_PROGRESS (started 14:15 UTC)
- **Acceptance Criteria:**
  - [ ] Page does not loop on valid callback code
  - [ ] Graceful error on invalid code (user sees message)
  - [ ] E2E test passes with CI=true
- **Effort:** medium — ~15 minutes
- **Notes:** Root cause: missing state validation on redirect. Fix is straightforward.

---

## Recently Completed (Cleanup in 24h)

### Fix TypeScript compilation errors — Engineer ✅
- **Completed at:** 14:15 UTC
- **Duration:** 14 minutes
- **Result:** Replaced `global` with `globalThis`, removed unused field, fixed Uint8Array type. Commit: cf9d22c
- **Next step:** Unblocks CallbackPage fix

---

## Backlog (Next Up)

### Add sessionStorage consistency test — Engineer
- **Effort:** low
- **Dependencies:** CallbackPage fix must be merged first
- **Notes:** Verify all token reads/writes use sessionStorage, no localStorage writes

### Update E2E auth flow for session-only tokens — Quality Engineer
- **Effort:** medium
- **Dependencies:** sessionStorage fix must be complete
- **Notes:** Validate E2E suite passes with new sessionStorage-only approach
```

### Example 2: Blocked Task (awaiting user input)

```markdown
## Blocked Tasks

### Implement AWS_IAM auth for {service-name} — Engineer
- **Blocker:** {service-name} config not deployed to dev environment
- **Escalation:** Orchestrator reached out to DevOps (through ticket #42)
- **Expected unblock:** 2026-04-24 16:00 UTC (estimated)
- **Workaround:** None — auth is required for this work
- **Notes:** Task assigned to Engineer but cannot proceed without config
```

### Example 3: Session with Mixed Roles

```markdown
# TODO — Security Hardening Sprint | 2026-04-24

**Session Owner:** Orchestrator | **Duration:** 12:00–18:00 UTC | **Status:** ACTIVE

## Current Checkpoint
- ✅ **Completed:** 4 tasks (avg 22 min)
- 🔄 **In Progress:** 3 tasks (1 blocker: JWKS fetch failure in test)
- 📋 **Backlog:** 2 tasks
- ⛔ **Blocked:** 1 task (awaiting Principal decision on architecture)

## Active Tasks (In-Progress)

### 1. Implement RS256 JWT verification — Senior Engineer
- **Status:** IN_PROGRESS (started 14:30 UTC)
- **Acceptance Criteria:**
  - [ ] JWKS fetch returns error on failure (no permissive fallback)
  - [ ] RSA key reconstruction works with test JWKS data
  - [ ] VerifyPKCS1v15 validates signature correctly
  - [ ] TESTING=1 bypass works for unit tests
  - [ ] All tests pass with `go test ./...`
- **Effort:** high — ~45 minutes
- **Notes:** Started on-time. Blocker hit: JWKS test data format differs from Guardian spec. Researching correct JWKS format.
- **Blocker:** JWKS test data format — researching, no escalation needed yet (expected resolution in 5 min)

### 2. Add CloudFront security headers — Engineer
- **Status:** IN_PROGRESS (started 15:00 UTC)
- **Acceptance Criteria:**
  - [ ] ResponseHeadersPolicy created with HSTS, CSP, X-Frame-Options
  - [ ] Policy attached to DefaultBehavior
  - [ ] `make cdk.build` includes policy in synth output
  - [ ] E2E validation confirms headers present in response
- **Effort:** medium — ~20 minutes
- **Notes:** CDK pattern review in progress. On track.

### 3. Review JWT signature verification design — Principal Engineer
- **Status:** IN_PROGRESS (started 15:30 UTC, estimated completion 16:15 UTC)
- **Acceptance Criteria:**
  - [ ] Architecture review complete
  - [ ] Decision on key rotation strategy documented
  - [ ] Feedback provided to Senior Engineer for implementation
- **Effort:** medium — ~30 minutes
- **Notes:** Providing real-time feedback to Senior Engineer on RS256 approach. No blockers.

---

## Recently Completed (Cleanup in 24h)

### Fix {service-name} collision detection — Senior Engineer ✅
- **Completed at:** 14:30 UTC
- **Duration:** 22 minutes
- **Result:** Implemented event hash comparison in `eventContentMatches()`. Test added and passing. Commit: 0d03223
- **Next step:** Unblocks production event ingestion

### Move cidc-watch to shared/ — Orchestrator ✅
- **Completed at:** 13:45 UTC
- **Duration:** 12 minutes
- **Result:** File moved, all role references updated in orchestrator.md and quality-engineer.md
- **Next step:** Quality Engineer can now reference shared/cidc-watch

### Consolidate playwright files — Orchestrator ✅
- **Completed at:** 13:20 UTC
- **Duration:** 15 minutes
- **Result:** Merged engineer/playwright-ui-testing + quality-engineer/e2e-playwright into shared/playwright-testing with Part 1/2 split
- **Next step:** Both Engineer and QE can reference unified skill

### Create MANIFEST.md index — Orchestrator ✅
- **Completed at:** 12:45 UTC
- **Duration:** 18 minutes
- **Result:** 400+ line manifest with all 70 files, multiple discovery paths. Added to main README.
- **Next step:** Unblocks file discoverability (solves GitHub Copilot/Claude Code parity)

---

## Blocked Tasks

### Implement Lambda permission boundary refactor — Principal Engineer
- **Blocker:** Decision needed on CDK stack layering strategy (affects 3 repos)
- **Escalation:** Escalated to Architecture review (needs security input on least-privilege scoping)
- **Expected unblock:** After Principal + Security Engineer design review (~30 min)
- **Workaround:** None — core architectural decision required
- **Notes:** Paused pending feedback. Not critical path.

---

## Backlog (Next Up)

### Add HSTS headers to {service-name} — Engineer
- **Effort:** low
- **Dependencies:** CloudFront security headers task must be merged
- **Notes:** Standard pattern, should take ~10 min

### Run full E2E suite with new token storage — Quality Engineer
- **Effort:** medium
- **Dependencies:** {service-name} sessionStorage fixes merged to dev
- **Notes:** CI=true mode, validate no regressions
```

---

## Metrics & Reporting

### Hourly Checkpoint Template

```
🔄 Checkpoint [HH:MM UTC]:
  ✅ Completed: N tasks (+M since last hour)
  🔄 Active: X tasks
  ⛔ Blocked: Y tasks (escalations: [list])
  📋 Backlog: Z tasks
  ⏱ Estimated done: HH:MM UTC
  🧠 Model performance: [optional — which roles most efficient?]
  💾 Token burn: [optional — if tracking per session]
```

### End-of-Session Report Template

```
📊 Session Complete — Summary for next session:

**Timeline:** [start] → [end] ([duration])
**Completed:** N tasks (avg X min each)
**Blocker resolutions:** M escalations resolved, Y still pending
**Efficiency:** [tokens used, cost, which roles overperformed]
**Carryover:** X tasks still in backlog (for next session)

**Next session should start with:**
- Backlog state (in TODO.md)
- Any unresolved blockers
- Recommendations from current session
```

---

## Integration with Task System

If using Claude's `TaskCreate`/`TaskUpdate` tools:
- **TODO.md is the primary source** for Orchestrator's local planning
- **Task system** is used for cross-session, user-visible progress tracking
- **Sync:** TODO.md tasks → TaskCreate (visible to user at end of session)
- **Both tracked:** Don't duplicate; use TODO.md for rapid hourly updates, Tasks for summary reporting

---

## Tips for Success

1. **Clarity over formality** — Write what's actually being done, not template-speak
2. **Timestamps matter** — Track when tasks start/complete for accurate metrics
3. **Blockers are not failures** — Clear blocker documentation helps escalation, don't hide them
4. **Keep it short** — If TODO.md gets >50 lines, archive completed items now
5. **Reuse across sessions** — If backlog carries over, just update the session date and checkpoint
6. **Voice it** — Use Orchestrator's voice for daily checkpoints: "3 tasks done, 2 blocked on auth config"

---

## When to Create a New TODO.md

- Per-project session ({service-name} security fixes, etc.)
- Multi-day initiative (architecture review spanning 3 days)
- Role-specific planning (Security Engineer running threat assessment)
- Fresh start (old session is archived and complete)

**Don't create:** Separate TODO for each small task. Batch related work in one TODO.md per initiative.

---

## Cleanup & Archival

After session ends or task completes:

```bash
# Archive old TODO with timestamp
cp TODO.md .TODO.archive.$(date +%Y-%m-%d_%H%M).md

# Keep only recent (< 24h) completions and active items
# Remove finished items from Recently Completed section
# Preserve Blocked/Backlog for next session
```

Archived files serve as session logs — useful for pattern analysis and metrics (avg task duration, common blockers, etc.).

---

## See Also

- `orchestration/task-routing.md` — How to assign tasks to roles
- `orchestration/AGENTS.md` — Role decision tree
- `monitoring/metrics-collection.md` — Track session metrics
- Root `CLAUDE.md` — ERS platform conventions
