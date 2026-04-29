---
name: Complete Roadmap Phases 5-9+
description: Full trajectory from local orchestration (Phase 5.10) to cloud-scale (Phase 9+)
type: roadmap
created: 2026-04-28
---

# Agentic Engineers: Complete Roadmap (Phases 5-9+)

---

## Phase 5.10: Quality Orchestrator Activation (1 week, 2026-05-26 → 2026-06-02)

**Status**: ✅ **COMPLETE & OPTIMIZED**

**What It Does**:
- Triggers on every git commit
- 4 parallel agents scan: security, testing, metrics, health
- Final decision: PROCEED (allow commit) or ESCALATE (reject)
- Transparent to developer (runs in background)

**Key Results**:
- 6 agents implemented (Opus, Sonnet, Haiku optimized)
- Cost: $0.278/commit (28% reduction from initial estimate)
- Latency: 4–5 minutes per commit
- Git hook integration complete

**Testing**: 10+ commits through pipeline during week of 2026-05-26

**Outcome**: Foundation ready for feedback loops

---

## Phase 6: Agent Feedback Loops & Observability (2 weeks, 2026-06-02 → 2026-06-16)

**Status**: ✅ **DESIGN COMPLETE - READY FOR IMPLEMENTATION**

**What It Does**:
- Loop 1: Aggregate sub-agent results → single decision (PROCEED/ESCALATE)
- Loop 2: Analyze token efficiency → recommend optimal model for next run
- Loop 3: Verify fixes work → build confidence in auto-correction

**Key Components**:
- Quality Gate Feedback Handler (sync, <1sec)
- Model Engineer Feedback Handler (async, learns model selection)
- Config Enforcement Feedback Handler (optional, fix verification)
- OpenTelemetry observability (all spans captured)

**Learning Curve**:
- Run 1–5: Collect baseline data
- Run 6–20: Confidence converging (which model is best?)
- Run 20+: Model selection stable, recommendations applied

**Testing**: 50+ commits through full pipeline during week of 2026-06-02

**Outcome**: Self-learning system operational. Model selection auto-optimizes. Proven fixes auto-applied.

---

## Phase 7: Self-Sustaining Optimization Loops (2 weeks, 2026-06-16 → 2026-06-30)

**Status**: 🔄 **NOT YET DESIGNED**

**What It Will Do**:
- Pattern Recognition Agent: Detect recurring issues (tests always fail on Mondays? CI flaky at EOD?)
- Budget Optimizer Agent: Watch cost accumulate, trigger auto-downgrades if over budget
- Quality Analyst Agent: Detect anomalies, propose improvements to detection logic

**How It Works**:
```
Quality Gate runs 100+ times
  ↓
Pattern Recognition: "This service type always has schema validation issues"
  ↓
Propose: "Add pre-commit schema check"
  ↓
Test hypothesis on next 10 commits
  ↓
If reduction in validation escalations: Keep new rule
If no impact: Remove new rule
```

**Continuous Improvement**:
- Cost optimization (auto-downgrade models if budget exceeded)
- Quality improvement (auto-add new checks based on patterns)
- Threshold tuning (auto-adjust decision thresholds based on FP/FN rates)

**Timeline**: Design during week of 2026-06-09, implement during week of 2026-06-16

**Outcome**: Zero-touch optimization. System improves itself without human intervention.

---

## Phase 8: Bedrock Migration Planning (2 weeks, 2026-06-30 → 2026-07-14)

**Status**: 📋 **DOCUMENTATION ONLY (NO IMPLEMENTATION)**

**Goal**: Plan migration to AWS Bedrock managed context, not execute it yet.

**What It Will Enable**:
- Central CloudWatch Logs repository for all traces
- ML models trained on decision history
- Cross-service orchestration (scale beyond single CLI session)
- Cost metering via CloudWatch

**Migration Strategy**:
```
Phase 5–7: Local (artifacts/ directory, Claude CLI)
    ↓
Phase 8: Export decision history to S3 + CloudWatch Logs
    ↓
Phase 9+: Bedrock-managed context (multi-region, high-availability)
    ↓
Phase 10+: Multi-vendor model routing (Anthropic + OpenAI + Google + Meta)
```

**No Code Changes**:
- OpenTelemetry spans already CloudWatch-compatible
- JSONL logs already structured for export
- artifacts/ directory remains local (backward compatible)

**Documentation**: Design specs for Bedrock integration (optional reading)

---

## Phase 9+: artifacts/ Backend Abstraction & Scaling

**Status**: 📋 **DOCUMENTATION ONLY (NO IMPLEMENTATION)**

**Goal**: Formalize artifacts/ as communication substrate. Design for scale.

**What It Enables**:
- Local: artifacts/ directory (current)
- Cloud: S3 + DynamoDB backend (future)
- Distributed: Multi-region, multi-service orchestration
- Federated: Multiple organizations sharing orchestration infrastructure

**Architecture Evolution**:
```
Phase 5–7 (Current):
  artifacts/ ← filesystem, single machine
         ↓
Phase 9 (Abstraction):
  artifacts/ ← filesystem OR S3+DynamoDB (switchable)
         ↓
Phase 10 (Scaling):
  artifacts/ ← distributed backend, eventual consistency
         ↓
Phase 11 (Federated):
  artifacts/ ← shared infrastructure, per-tenant isolation
```

**Zero User-Facing Change**: Developer still uses `git commit`. System scales behind the scenes.

---

## How Models Will Evolve: Non-Anthropic Support

**Phase 5.10** (Today): Anthropic only
- Haiku, Sonnet, Opus selected by capability

**Phase 6–7** (In progress): Anthropic optimized
- Model selection converging
- Cost optimized (28% reduction)

**Phase 8** (Planning): Vendor diversity
- Benchmark: OpenAI GPT-4o mini, Google Gemini 2, Meta Llama
- Add to MODEL-SELECTION-STRATEGY.md

**Phase 9+** (Future): Multi-vendor routing
- If Anthropic unavailable → fallback to OpenAI
- If cost spike → try cheaper alternative
- Transparent model swapping based on performance

**Example** (Phase 9 style):
```yaml
Testing Agent:
  primary: haiku
  fallback: gpt-4o-mini
  backup: gemini-2-flash
  
Decision logic:
  Try haiku first (cost $0.034)
  If unavailable: Use gpt-4o-mini (cost $0.048)
  If both down: Use gemini-2-flash (cost $0.025)
```

---

## Cost Trajectory

| Phase | Model Strategy | Cost/Commit | Daily (10) | Monthly | Notes |
|-------|----------------|-------------|-----------|---------|-------|
| 5.0 (Initial) | All Sonnet | $0.389 | $3.90 | $117 | Conservative, safe |
| 5.10 (Now) | Optimized (Haiku) | $0.278 | $2.78 | $83 | 28% reduction via downgrades |
| 6 (Feedback) | Learning-based | ~$0.250 | $2.50 | $75 | Additional optimization from loops |
| 7 (Self-sustaining) | Auto-optimized | ~$0.200 | $2.00 | $60 | Budget optimization kicks in |
| 8 (Bedrock) | Cloud-metered | TBD | TBD | TBD | May differ (managed vs self-hosted) |
| 9+ (Multi-vendor) | Best of breed | ~$0.150 | $1.50 | $45 | Fallback chains, cost optimization |

**Annual Trajectory**:
- Today: ~$1,000–$2,000
- Phase 7: ~$800 (auto-optimized)
- Phase 9+: ~$500–$700 (multi-vendor, fallback chains)

---

## Observability Evolution

**Phase 5.10**: Local OpenTelemetry spans
- Files: `artifacts/SPAN-*.yaml`
- Format: YAML (human-readable)
- Query: Manual file inspection

**Phase 6**: Append-only decision logs
- Files: `artifacts/feedback/*.jsonl`
- Format: JSONL (machine-readable)
- Query: Simple grep/awk scripts

**Phase 7**: Pattern detection & anomalies
- Files: Same, but with pattern analysis
- Query: Pattern Recognition Agent identifies anomalies

**Phase 8**: CloudWatch Logs export
- Files: S3 + CloudWatch Logs
- Format: JSON (CloudWatch standard)
- Query: CloudWatch Insights, Athena

**Phase 9+**: Distributed tracing
- Files: Same, plus distributed context
- Format: OpenTelemetry Protocol (OTLP)
- Query: Commercial APM (Honeycomb, Datadog, New Relic)

---

## Deployment Timeline

```
2026-05-26  Phase 5.10 Testing Starts
              10+ commits through orchestrator
              Validate: 0% false decisions
              
2026-06-02  Phase 5.10 Testing Complete ✅
            Phase 6 Implementation Starts
              Build feedback loop handlers
              
2026-06-16  Phase 6 Implementation Complete ✅
            Phase 7 Design Starts
              Pattern Recognition, Budget Optimizer
              
2026-06-30  Phase 7 Implementation Complete ✅
            Phase 8 Planning Starts
              Bedrock migration strategy
              
2026-07-14  Phase 8 Documentation Complete ✅
            Phase 9+ Design Starts
              artifacts/ backend abstraction
              
2026-08-01  Phase 9+ Documentation Complete ✅
            Ready for 2H 2026 implementation
```

---

## What "Ready for X Phase" Means

### Phase 5.10 ✅ READY FOR TESTING
- All code written and tested locally
- Specifications complete (agent specs, handler logic, decision trees)
- No implementation needed; just run 10+ commits through it
- Success = 0 false escalations

### Phase 6 ✅ READY FOR IMPLEMENTATION
- All designs finalized
- Handler logic specified in detail
- Success criteria clear
- No design decisions needed; just implement the handlers

### Phase 7 🔄 NOT READY YET
- Designs don't exist
- Need to design Pattern Recognition, Budget Optimizer, Quality Analyst agents
- Timeline: Design during Phase 6, implement during Phase 7

### Phase 8 📋 DOCUMENTATION ONLY
- Will not implement
- Will only document strategy
- Implementation deferred to 2H 2026

### Phase 9+ 📋 DOCUMENTATION ONLY
- Will not implement
- Will only document architecture for scale
- Implementation deferred to 2H 2026+

---

## Success Metrics: Full Roadmap

**By End of Phase 5.10** (2026-06-02):
- ✅ 10+ commits with 0% false escalations
- ✅ Cost savings validated ($50/month)
- ✅ Team familiar with flow

**By End of Phase 6** (2026-06-16):
- ✅ 50+ commits through full pipeline
- ✅ Model recommendations trending
- ✅ Feedback loops operational
- ✅ Confidence converging

**By End of Phase 7** (2026-06-30):
- ✅ Self-sustaining loops running
- ✅ Auto-optimization working (model downgrades, cost optimization)
- ✅ Pattern detection finding real issues
- ✅ Zero manual tuning needed

**By Phase 8** (2026-07-14):
- ✅ Bedrock migration plan documented
- ✅ Decision history exported to CloudWatch
- ✅ Ready for migration (optional)

**By Phase 9+** (2026-08-01+):
- ✅ artifacts/ backend abstraction designed
- ✅ Multi-vendor routing designed
- ✅ Ready for scaling to enterprise (optional)

---

## Key Design Decisions (Locked In)

### 1. Model Selection by Capability
✅ **Locked**: Models chosen by task requirements, not vendor.
- Testing Agent: Haiku (structured parsing strength)
- Security Agent: Opus (zero false negatives requirement)
- Healing Agent: Sonnet (code generation complexity)

### 2. Append-Only Audit Trails
✅ **Locked**: Decision history immutable, queryable, ready for ML.
- JSONL format (CloudWatch-compatible)
- Append-only (never modified)
- Enables Phase 8 export to S3

### 3. Local-First, Cloud-Ready
✅ **Locked**: Phase 5–7 runs local. Phase 8+ can export to cloud without re-architecture.
- artifacts/ directory (local)
- OpenTelemetry spans (CloudWatch-compatible)
- No vendor lock-in

### 4. Feedback Loops Drive Improvement
✅ **Locked**: Every result feeds back to parent for learning.
- Model recommendations refine over 20+ runs
- Config fixes update confidence after re-verification
- Patterns detected automatically

### 5. No Manual Tuning
✅ **Locked**: System improves itself. Thresholds, models, fixes auto-optimize.
- Phase 6: Model selection converges
- Phase 7: Patterns detected, improvements proposed
- Phase 8+: Cost optimization, anomaly detection

---

## FAQ: What If...?

**Q: What if a Model Engineer recommendation is wrong?**
A: Confidence will decrease. After a few failures, system reverts to previous model. No harm done, just learning cost.

**Q: What if a config fix makes things worse?**
A: Config Enforcement Feedback Handler detects it (compliance score doesn't improve). Confidence decreases, fix escalated next time.

**Q: What if OpenTelemetry storage fills up?**
A: Phase 5–7 stores locally. Rotate artifacts/ older than 30 days. Phase 8+ exports to S3, unlimited.

**Q: What if we want to migrate to Bedrock?**
A: Phase 8 designs it. Phase 9+ implements it. Zero code changes required to Phase 5–7 logic.

**Q: What if a new model from OpenAI is cheaper?**
A: Phase 8+ design includes vendor fallback chains. Can add GPT-4o mini as fallback for Sonnet tasks.

**Q: What if we want to pause Phase 7 optimization?**
A: Just don't implement it. Phase 5–6 still work. Phase 7 is optional enhancement.

---

## Decision: What to Build vs. Document

| Phase | Build | Document | Reason |
|-------|-------|----------|--------|
| 5.10 | ✅ | — | Core feature, needed for testing |
| 6 | ✅ | ✅ | Implementation + design guidance |
| 7 | — | 🔄 (design) | Will implement after 6 testing |
| 8 | — | ✅ | Migration strategy, no code |
| 9+ | — | ✅ | Scaling strategy, no code |

**Rationale**: Focus on local, proven loops first. Cloud migration & multi-vendor support are nice-to-haves, not blockers.

---

## Reading Order for Stakeholders

**For Developers**:
1. `PHASE-5.10-INTEGRATION-GUIDE.md` — How the orchestrator works
2. `PHASE-6-INTEGRATION-GUIDE.md` — Feedback loops (once Phase 6 is live)

**For Architects**:
1. `MODEL-SELECTION-STRATEGY.md` — Model selection framework
2. `FEEDBACK-LOOPS.md` — Cost model & feedback loop architecture
3. `PHASE-6-INTEGRATION-GUIDE.md` — How everything ties together

**For Operations**:
1. `SESSION-2026-04-28-SUMMARY.md` — What was done today
2. Cost tables in `PHASE-5.10-COMPLETION-SUMMARY.md` — Budget impact

**For Planning**:
1. `TODO.md` — Current status & next steps
2. This file (ROADMAP-PHASES-5-9.md) — Full trajectory
3. `PHASE-6-INTEGRATION-GUIDE.md` → Phase 7 design → Phase 8 planning
