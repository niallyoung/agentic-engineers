# PLAN: Skill Improvements & Self-Improvement Architecture (2026-06-13)

Three DELEGATEs to execute in order. Each produces a HANDBACK with deliverables; subsequent rounds implement those deliverables.

---

## DELEGATE-2026-06-13-001: Skill Audit & Enhancement

**Role:** lead-engineer  
**Model:** claude-sonnet-4.6  
**Effort:** high  
**Task ID:** 2026-06-13-skill-audit-enhancement

**Scope:**
Review this session's manual work. Identify what should move into existing skills or trigger new skill proposals. Session revealed:
- Manual artifacts/ pruning (105→86 files) — no cleanup skill
- Manual HANDBACK enum drift detection — protocol-validator didn't catch
- Manual SPEC residual detection (glossary, tree, erratum) — doc-quality-monitor didn't scan for phantom references
- Manual escalation-path consolidation — queue-management didn't flag divergence

**Success Criteria:**
1. Enhanced `doc-quality-monitor` (src/skills/doc-quality-monitor/): add scans for phantom references (grep known-dead classes: AutomationController, deprecated paths), stale docstrings (match against SPEC versions)
2. Enhanced `protocol-validator` (src/skills/protocol-validator/): add enum drift detection (handback-schema status enum vs code acceptors), protocol divergence detection (multiple escalation implementations)
3. Propose new `session-analyzer` meta-skill or enhancement to existing skill to detect repetitive patterns in session transcripts
4. Document each enhancement with tests

**Output (HANDBACK):**
- List of enhanced/new skills with file paths
- Tests added (cite test file:line ranges)
- Proposal for session-analyzer (if new skill)

---

## DELEGATE-2026-06-13-002: Model Adaptability Config Design

**Role:** principal-engineer  
**Model:** claude-opus-4.8  
**Effort:** high  
**Task ID:** 2026-06-13-model-adaptability-config

**Scope:**
Design runtime model-selection system. Framework should adapt to available providers (Anthropic, OpenAI, Ollama, etc.) without code changes.

**Core Design:**
- **Role requirements** (not model names): "needs reasoning", "needs cost-aware", "needs defensive-only", etc.
- **Model registry**: Loaded from provider APIs or `~/.agentic-engineers/model-config.yaml`
- **Auto-mapper**: Given role + available models, pick best fit; fallback chain
- **Config centralization**: `~/.agentic-engineers/model-config.yaml` (analyzable, versioned in repo)

**Success Criteria:**
1. Architecture proposal document (300–500 words): role requirements spec, model registry schema, mapper logic, integration points
2. Example `model-config.yaml` showing Anthropic + OpenAI + Ollama with fallback chains
3. Outline changes to `src/AGENTS.md` (role requirements vs hardcoded models)
4. Integration point checklist: which skills/code read this config? (cost-aware-router, Orchestrator, Model Engineer)
5. One proof-of-concept: Orchestrator reads config at startup

**Output (HANDBACK):**
- Proposal document (docs/design/model-adaptability-config.md or similar)
- Example config file
- Integration checklist with file:line references
- Confidence score on feasibility

---

## DELEGATE-2026-06-13-003: Meta-Skill Proposal — Session Analysis

**Role:** model-engineer  
**Model:** claude-sonnet-4.5  
**Effort:** high  
**Task ID:** 2026-06-13-meta-skill-session-analyzer

**Scope:**
Design skill that reads session transcripts and identifies automation candidates. This session showed patterns (plan review, doc audit, protocol checking) that should be skills, not manual prompts.

**Analysis inputs:**
- Session DELEGATE specs (what work was requested)
- HANDBACK results (what was delivered, quality scores)
- Conversation history (manual steps, repetitive prompts)
- Execution metrics (time, tokens, cost per task)

**Analysis outputs:**
- Repetitive patterns (this step happened 3+ times → skill candidate)
- Quality anomalies (this type of task always scores low → routing issue?)
- Drift detection (this config/doc drifted during session → monitoring candidate?)
- Effort mismatch (claimed low effort, took high effort → estimation issue?)

**Success Criteria:**
1. Skill definition (SKILL.md with integration points, CLI interface)
2. Analysis schema (YAML structure for analysis.yaml output files)
3. Example run on this session: manual audit → what session-analyzer should flag
4. Integration with existing skills (queue-query, usage-tracking, metrics-etl)
5. Output location: `~/.agentic-engineers/sessions/{session-id}/analysis.yaml` (centralized, not harness dirs)

**Output (HANDBACK):**
- SKILL.md file (ready to integrate into src/skills/)
- Analysis schema (YAML example + documentation)
- Example analysis report for 2026-06-13 session
- Integration points (which existing skills read this data?)

---

## Execution Order

1. **DELEGATE-001 (Skill Audit)** — Lead Engineer review of this session
2. **DELEGATE-002 (Model Config Design)** — Principal Architect designs adaptability system
3. **DELEGATE-003 (Meta-Skill)** — Model Engineer proposes session analysis

Then:
- **Round 2**: Implement the three outputs (engineer work, with QE review)
- **Round 3**: SPEC-2026-003 (AutomationController reference fix via spec-management), small doc/docstring fixes (lead-engineer)

---

## Storage & Automation Notes

- **All DELEGATEs routed via Orchestrator** — enqueue via `queue-management` skill, never manual file writes
- **Data centralization**: Analysis outputs, model configs, session reports → `~/.agentic-engineers/` (owned by framework, analyzable, not harness-specific)
- **Next session**: Invoke Orchestrator with these three specs; it routes to appropriate agents
- **Skills enhancement principle**: Avoid hardcoding in code; move logic to skills that can be versioned, tested, and invoked via DELEGATE
- **Core agent responsibility**: Every Agent consults docs/SPEC.md and existing SKILLS before inventing work. Framework alignment is a first-class skill; all agents remain in sync on core responsibilities and expectations.

See TODO.md "## Next: Skill Improvements" for tracking.

---

## Discovery During Orchestrator Integration

### Issue: DELEGATEs Not Picked Up on Fresh Install
**Session 2026-06-13 (afternoon)**

While testing if queued DELEGATEs were discovered on fresh `make install`, found that
Orchestrator was not picking up the initial three DELEGATEs. Diagnosis revealed:

1. **Root cause**: Path structure mismatch
   - Documented (incorrectly): `~/.agentic-engineers/{session-id}/{harness}/queue/`
   - Actual (correct): `~/.agentic-engineers/{harness}/{session-id}/queue/`
   - Initial placement: `~/.agentic-engineers/queue/2026-06-13/incoming/` ❌

2. **Why this happened**: 
   - Orchestrator.py docstrings (lines 5, 548) had backwards path documentation
   - Queue-isolation.py (line 143-158) implements correct path but documentation wasn't consistent
   - Systematic drift: 16+ files incorrectly document path format

### Fixes Applied
1. ✅ Corrected Orchestrator.py docstrings (lines 5, 548)
2. ✅ Moved initial 3 DELEGATEs to correct path: `~/.agentic-engineers/claude/2026-06-13/queue/incoming/`
3. ✅ Queued new DELEGATE: **2026-06-13-queue-path-audit-fix** (principal-engineer)

### New DELEGATE: Queue Path Documentation Audit

**Role:** principal-engineer  
**Task ID:** 2026-06-13-queue-path-audit-fix  
**Scope:**
Audit and fix systematic queue path documentation drift (16+ files with incorrect
`{session-id}/{harness}` instead of `{harness}/{session-id}`). Provide comprehensive
fix strategy with priority ranking by impact.

**Deliverables:**
- Complete audit report with grep results (file:line format)
- Root cause analysis (when/why drift occurred)
- Impact assessment (user-facing docs vs tests vs comments)
- Prioritized fix list with git-ready patches
- Risk assessment: any code logic depends on incorrect ordering?

**Files to audit:**
- src/agents/orchestrator-agent.md
- src/skills/queue-management/tests/test_queue_ops.py
- src/skills/_meta/queue-path-validator/SKILL.md (multiple refs)
- src/skills/_meta/queue-path-validator/scripts/queue_path_validator.py (multiple refs)
- src/skills/_meta/queue-path-validator/tests/test_queue_path_validator.py
- src/skills/_meta/queue-path-validator/queue_path_validator.py
- src/opencode/__init__.py
- Plus ~9 more files detected via grep

**Follow-up:** Once principal-engineer HANDBACK is received, queue engineer DELEGATEs
to implement fixes (high priority: user-facing docs first, then tests, then comments).

---

## Queue Management Audit & Improvements (2026-06-13, continued)

### CRITICAL DISCOVERY: Harness Context Dependency
During Orchestrator queue responsibility review, discovered that queue discovery is
**harness-context-dependent**:

1. **Root cause**: queue-isolation.detect_harness() defaults to 'local' unless:
   - AGENTIC_HARNESS env var is set, OR
   - CLAUDE_SESSION_ID is set, OR
   - COPILOT_SESSION_ID is set, etc.

2. **Impact**: DELEGATEs queued at `~/.agentic-engineers/claude/{session}/queue/` won't
   be discovered when Orchestrator runs in 'local' harness context (the default)

3. **Immediate fix**: Moved DELEGATEs to `~/.agentic-engineers/local/2026-06-13-session/queue/`
   for discovery in default context

### Queue Management Gaps Identified

#### Critical Gaps (Impact: DELEGATEs may not be processed)
- ❌ No harness context awareness: Orchestrator runs in one context, queues exist per harness
- ❌ No queue staleness detection: Tasks can sit in incoming/ indefinitely
- ❌ No stalled task detection: Processing tasks without heartbeat don't timeout
- ❌ No automatic recovery: Failed/stalled tasks don't retry or escalate

#### Missing Features (Impact: Operational reliability)
- ❌ No SLA enforcement: No timeout policies defined (max age per state)
- ❌ No heartbeat mechanism: Long-running tasks don't signal liveness
- ❌ No multi-harness support: Orchestrator can't scan all harness queues
- ❌ No monitoring: No metrics for queue health, staleness, aging

#### SPEC Gaps (Impact: Framework governance)
- ❌ SPEC.md missing queue management section
- ❌ No defined SLA thresholds (when is a task "stale"?)
- ❌ No recovery procedures documented
- ❌ No Orchestrator responsibilities codified

### DELEGATEs QUEUED FOR FIXES

#### Priority 1: Orchestrator Audit (Principal Engineer)
- **Task**: 2026-06-13-orchestrator-queue-audit-complete
- **Scope**: Full audit of queue state, harness context detection, gaps vs SPEC
- **Deliverable**: Recommendations for critical fixes

#### Priority 2: Skill Improvements (Original 3 DELEGATEs)
1. 2026-06-13-skill-audit-enhancement (lead-engineer)
2. 2026-06-13-model-adaptability-config (principal-engineer)
3. 2026-06-13-meta-skill-session-analyzer (model-engineer)

#### Priority 3: Queue Improvements (New 3 DELEGATEs)
1. **2026-06-13-queue-staleness-detection** (engineer)
   - Implement timestamp tracking and staleness monitoring
   - Alert on aged tasks, escalate very old ones
   
2. **2026-06-13-queue-wake-timers** (engineer)
   - Implement configurable polling intervals
   - Add stalled task heartbeat detection
   - Automatic timeout and recovery
   
3. **2026-06-13-spec-queue-sla-design** (principal-engineer)
   - Design queue SLA requirements
   - Define timeout thresholds and recovery procedures
   - Propose SPEC.md updates

### Location of Queued Work
**All DELEGATEs**: `~/.agentic-engineers/local/2026-06-13-session/queue/incoming/`

**Status**: Ready for Orchestrator discovery (local harness context)

### Next Steps
1. Orchestrator picks up and routes DELEGATEs to appropriate agents
2. Principal engineers investigate gaps and design solutions
3. Engineers implement queue staleness/timer/SPEC improvements
4. Quality engineer validates implementations
5. Integration: Updated Orchestrator with improved queue management

---

## PARALLEL AGENT DELIVERY COMPLETE (2026-06-13 afternoon)

Three principal/lead engineers completed parallel audits in ~11 minutes (268K tokens):

### ORCHESTRATOR QUEUE AUDIT ✅
**Critical P0 findings** (confidence 0.9–0.95):
- Two divergent orchestrators (OrchestratorAgent vs OrchestratorSkill) — must choose one
- Harness-context fragmentation: 17 orphan session UUIDs in 1 second
- Dead crash-recovery code (exists but never called)
- Zero staleness detection, zero heartbeat, hardcoded timeouts
- SPEC completely silent on queue policy (no staleness/timeout definitions)

**Blocking decision**: Which orchestrator is canonical? Gates all queue fixes.

### SKILL AUDIT & ENHANCEMENT ✅  
**Delivered** (101/101 tests passing):
- Enhanced doc-quality-monitor: phantom reference detection (9 new tests)
- Enhanced protocol-validator: enum drift detection (found 3 LIVE BUGS)
- Proposed session-analyzer: complete SKILL.md + TDD spec ready

**Bugs found**:
- 3 files using legacy status enum (complete/failed instead of success/failure)
- 10 phantom AutomationController references in docs

**Queued for fixes**:
- enum-drift-fix (trivial: 3-file search-replace)
- phantom-ref-cleanup (trivial: 10 doc refs removal)
- session-analyzer-implementation (medium effort)

### MODEL ADAPTABILITY CONFIG ✅
**Design delivered** (confidence 0.82):
- Capability-based runtime selection (quality bands, not floors)
- Provider discovery + auto-mapper + fallback chains
- Integration checklist (7 components to update)
- Framework already has 80% of this — integration layer only

**Key insight**: Role requirements + available providers → auto-select best model
- Preserves governance locks (.githooks/LOCKED_MODELS.sh)
- Example config with Anthropic + OpenAI + Ollama
- Ready for engineer implementation after risk closure

### QUEUED: 11 DELEGATEs TOTAL
1. 2026-06-13-orchestrator-architecture-decision (P0 decision)
2. 2026-06-13-enum-drift-fix (P0 bug fix)
3. 2026-06-13-phantom-ref-cleanup (P0 bug fix)
4. 2026-06-13-queue-staleness-detection (P1)
5. 2026-06-13-queue-wake-timers (P1)
6. 2026-06-13-spec-queue-sla-design (P1)
7. 2026-06-13-session-analyzer-implementation (P1)
8. 2026-06-13-skill-audit-enhancement (delivered — original)
9. 2026-06-13-model-adaptability-config (delivered — original)
10. 2026-06-13-meta-skill-session-analyzer (original)
11. 2026-06-13-orchestrator-queue-audit-complete (audit HANDBACK)

**Location**: ~/.agentic-engineers/local/2026-06-13-session/queue/incoming/

**Next**: Operator reviews P0 architectural decision; bug fixes execute immediately.
