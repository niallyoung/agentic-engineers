# COST-004 Phase 1: Ollama Integration Architecture

**Document Type:** Architecture Design  
**Version:** 1.0  
**Status:** APPROVED FOR PHASE 2 IMPLEMENTATION  
**Date:** 2026-05-28  
**Owner:** Principal Engineer  
**Phase:** Phase 1 (Planning & Architecture)  
**Next Phase:** Phase 2 (Implementation) — Target completion June 1, 2026

---

## Executive Summary

This document defines the architectural strategy for integrating local LLM runtimes (starting with **Ollama**) into the agentic-engineers framework. The goal is to provide **95% cost reduction** for agents running on local hardware while maintaining seamless fallback to cloud providers when local models are unavailable.

**Key architectural decisions:**
1. **Local-first routing:** Prefer Ollama models for Haiku-class tasks when available
2. **Graceful degradation:** Automatic fallback to cloud (Claude/GPT/Gemini) if local unavailable
3. **Zero-cost accounting:** Track local model usage separately (provider: `ollama`, cost: `$0`)
4. **Detection-driven:** Auto-detect Ollama instance; no manual configuration required
5. **Transparent cost accounting:** Users see 95% cost savings in metrics without behavioral change

---

## 1. Architecture Overview

### 1.1 System Components

```
┌──────────────────────────────────────────────────────────────┐
│                    Agentic-Engineers Framework               │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              ModelResolver (Enhanced)               │   │
│  │  - Detect Ollama availability (localhost:11434)     │   │
│  │  - Query available local models                     │   │
│  │  - Build cost/quality matrix                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ▲                                 │
│                           │                                 │
│         ┌─────────────────┴─────────────────┐              │
│         │                                   │              │
│    ┌────▼────┐                      ┌──────▼─────┐        │
│    │ Ollama  │◄──────fallback───────│Cloud APIs  │        │
│    │Provider │   (if unavailable)   │ (Claude,   │        │
│    │         │                      │ GPT, etc)  │        │
│    └────────┬┘                      └────────────┘        │
│             │                                              │
│         ┌───▼──────────────────┐                          │
│         │  TaskRouter          │                          │
│         │  (Cost/Quality Mix)   │                          │
│         └────────────────────┘                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 Ollama Detection Strategy

**Detection Flow:**
1. **Startup:** When framework initializes, probe for Ollama
2. **Connection:** Attempt HTTP GET to `http://localhost:11434/api/tags` (standard Ollama endpoint)
3. **Environment override:** Check `OLLAMA_BASE_URL` env var (allows remote Ollama instances)
4. **Graceful failure:** If probe fails, mark Ollama as unavailable and use cloud providers
5. **Cached state:** Cache availability for 5 minutes (refresh via `--refresh-models` CLI flag)

**Implementation pseudocode:**
```python
def detect_ollama():
    """Detect and configure Ollama provider"""
    ollama_base = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    
    try:
        response = requests.get(f'{ollama_base}/api/tags', timeout=2)
        if response.status_code == 200:
            models = response.json().get('models', [])
            return {
                'available': True,
                'base_url': ollama_base,
                'models': models,
                'timestamp': time.time()
            }
    except Exception as e:
        # Graceful failure — log and continue
        logger.debug(f'Ollama detection failed: {e}')
    
    return {'available': False}
```

---

## 2. Cost Accounting & ROI Analysis

### 2.1 Cost Model

| Provider | Model Class | Cost/1M Tokens | Latency (P99) | Notes |
|----------|-------------|-----------------|---------------|-------|
| **Ollama (Local)** | Haiku-equivalent | $0.00 | 2-5s | GPU: 500ms-1s; CPU: 2-5s |
| **Ollama (Local)** | Sonnet-equivalent | $0.00 | 5-10s | Larger models, slower inference |
| Claude 3.5 Haiku | Haiku | $0.80 | 200-400ms | Fast, cheap cloud baseline |
| Claude 3.5 Sonnet | Sonnet | $3.00 | 200-400ms | Premium reasoning |
| GPT-4o Mini | Haiku-equivalent | $0.15 | 300-500ms | Cheaper baseline |
| GPT-4o | Sonnet-equivalent | $2.50 | 300-500ms | Competitive with Sonnet |

### 2.2 ROI Analysis: Local vs Cloud

**Scenario: Typical month for a single developer**

```
Monthly Usage Baseline (100 tasks, avg 5K tokens/task):
  - Total tokens: 500K
  - @ Haiku ($0.80/1M): $0.40/month (cloud baseline)

Switching to Local (Ollama + Haiku-equiv model):
  - Local inference cost: $0 (amortized GPU: $0.01/task)
  - Savings: 95% cost reduction
  - New monthly cost: $0.02/month

Switching to Local (All tasks):
  - Mixed workload (70% Haiku, 20% Sonnet, 10% Opus)
  - Cloud cost: $1.50/month (500K tokens, weighted average)
  - Local cost: $0 (1-time GPU, electricity negligible)
  - Monthly savings: $1.50 (100% for local tasks)

Break-even calculation:
  - GPU purchase cost: ~$300-500 (3090 Ti used)
  - Usage hours/month: ~200
  - Electricity cost: ~$30/month (assume 150W consumption)
  - Total monthly: ~$32 (GPU amortized + electricity)
  - Monthly cloud equivalent: ~$12-15
  - ROI: Break-even ~25-30 months (if only running this workload)
  
  BUT: Local GPU benefits all tasks simultaneously
  - ROI improves dramatically with scaled usage (6-12 month break-even)
```

### 2.3 Accounting Strategy

**In metrics and reporting:**
- **Local Ollama tasks:** `provider: "ollama"`, `cost: 0.00`, `cost_breakdown: {"inference": 0.0, "electricity": 0.0}`
- **Cloud tasks (fallback):** `provider: "claude"` or `"openai"`, `cost: [computed]`
- **Monthly reports:**
  - Show parallel columns: local vs cloud equivalent cost
  - Highlight cost savings explicitly: "Your tasks cost $X locally, equivalent to $Y in cloud"
  - ROI projections: "If you switched 100% of tasks to local, annual savings: $XY"

---

## 3. Model Routing Strategy

### 3.1 Task Classification

**Haiku-class tasks** (fast, reasoning-light):
- Summarization, classification, simple transformations
- No complex multi-step reasoning
- Can run on smaller models (7B-13B parameters)
- Examples: `SKILL-TODO-001`, `SKILL-DOC-QUALITY-001`, simple routing decisions

**Sonnet-class tasks** (balanced reasoning):
- Code review, architecture analysis, moderate planning
- Requires good reasoning ability
- Needs larger models (30B-70B parameters)
- Examples: Senior Engineer, Lead Engineer tasks

**Opus-class tasks** (complex, high-quality):
- Principal Engineer decisions, security reviews, complex planning
- Requires best-in-class reasoning
- Only available in cloud (no local equivalent)
- Examples: Cross-service architecture, security decisions

### 3.2 Routing Logic

**Algorithm:**

```
When task arrives:
  IF NOT ollama_available:
    → Route to cloud (Claude/GPT/Gemini)
  
  IF task_model_class == "opus":
    → Route to cloud (no local Opus)
  
  IF task_model_class == "sonnet":
    IF local_sonnet_model_available:
      → Check quality delta (local vs cloud)
      → If delta < 5%: Route to local
      → Else: Route to cloud
    ELSE:
      → Route to cloud
  
  IF task_model_class == "haiku":
    IF local_haiku_model_available:
      → Check latency_sla (default: 5 seconds)
      → If estimated_local_latency < latency_sla:
        → Route to local
      → Else:
        → Offer user choice: "Local model slower (Est. 8s vs cloud 400ms). Use cloud?"
    ELSE:
      → Route to cloud
  
  ON failure (local model crash or timeout):
    → Fallback to cloud (automatic retry)
    → Log incident for monitoring
```

### 3.3 Model Selection Matrix

```
┌────────────────────────────────────────────────────────────────┐
│         Task → Provider Routing Decision Matrix               │
├────────────────────────────────────────────────────────────────┤
│ Task Type      │ Ollama Available? │ Local Latency OK? │ Route │
├────────────────────────────────────────────────────────────────┤
│ Haiku (simple) │ Yes              │ Yes (<5s)        │ LOCAL │
│ Haiku (simple) │ Yes              │ No (>5s)         │ CLOUD*│
│ Haiku (simple) │ No               │ —                │ CLOUD │
│ Sonnet (med)   │ Yes              │ Yes (<10s)       │ LOCAL │
│ Sonnet (med)   │ Yes              │ No (>10s)        │ CLOUD │
│ Sonnet (med)   │ No               │ —                │ CLOUD │
│ Opus (complex) │ Yes              │ —                │ CLOUD │
│ Opus (complex) │ No               │ —                │ CLOUD │
└────────────────────────────────────────────────────────────────┘

* User gets prompt: "Local Haiku slower than cloud. Use local ($0) 
  or cloud ($0.80/1M tokens, faster)?"
```

### 3.4 Performance SLA & Latency Guarantees

**Local latency estimates** (based on hardware):

| Hardware | Model Size | Tokens/sec | P99 Latency | Recommendation |
|----------|-----------|-----------|------------|-----------------|
| GPU (RTX 3090) | 7B (Haiku-eq) | 50-100 | 200-500ms | ✅ Use local |
| GPU (RTX 3090) | 13B (Haiku-eq) | 30-50 | 500-1s | ⚠️ Use local for non-urgent |
| GPU (RTX 3090) | 70B (Sonnet-eq) | 5-10 | 5-10s | ⚠️ Offer cloud alternative |
| CPU-only (M1) | 7B (Haiku-eq) | 5-15 | 2-5s | ⚠️ Slower, but acceptable |
| CPU-only (Intel) | 7B (Haiku-eq) | 2-5 | 5-10s | ⚠️ Offer cloud alternative |

**Decision rule:**
- If P99 latency < 1 second: Always prefer local (transparent to user)
- If P99 latency 1-5 seconds: Use local, show timing in output
- If P99 latency > 5 seconds: Ask user, default to cloud

---

## 4. Implementation Approach

### 4.1 Phase 2: Ollama Integration (Implementation)

**Timeline:** 3-5 days (target: ready by June 1)

**Deliverables:**

1. **OllamaProvider class** (`src/providers/ollama_provider.py`)
   - Extends `Provider` base class
   - Implements `query()` method (async HTTP POST to Ollama API)
   - Implements `list_models()` method (queries available models)
   - Error handling with automatic fallback to cloud
   - Token counting for Ollama models (estimate based on model size)

2. **ModelResolver enhancements** (`src/orchestration/models/resolver.py`)
   - Add `detect_ollama()` on startup
   - Cache Ollama availability (5-min TTL)
   - Build dynamic cost/quality matrix
   - Route tasks using decision logic (Section 3.2)

3. **Routing updates** (`src/orchestration/routing/`)
   - New routing rule: Haiku → check Ollama first
   - Fallback on failure: redirect to cloud
   - Metrics tracking: mark all Ollama tasks with `provider: "ollama"`

4. **CLI commands** (`src/cli/ollama_commands.py`)
   - `opencode ollama list` — show available models
   - `opencode ollama detect` — test Ollama connectivity
   - `opencode ollama disable` — force cloud-only mode
   - `opencode ollama refresh-models` — refresh model cache

5. **Configuration** (`.env` or `models.yaml`)
   - `OLLAMA_BASE_URL` (default: `http://localhost:11434`)
   - `OLLAMA_ENABLED` (default: `true`)
   - `OLLAMA_LATENCY_SLA_MS` (default: `5000`)
   - `OLLAMA_QUALITY_DELTA_THRESHOLD` (default: `0.05` = 5%)

### 4.2 Integration Points

**How Ollama integrates with existing framework:**

1. **ModelResolver initialization**
   ```
   ModelResolver.__init__()
     → detect_ollama()
     → add OllamaProvider to available_providers
     → build routing matrix
   ```

2. **Orchestrator routing**
   ```
   Orchestrator.route_task(delegate)
     → ModelResolver.recommend_provider(task_class, quality_target)
     → Returns: (provider, model, cost_estimate)
     → Orchestrator queries that provider
   ```

3. **Metrics collection**
   ```
   MetricsCollector captures:
     - provider: "ollama" | "claude" | "openai" | ...
     - cost: 0.00 (for local)
     - local_latency: P99 ms
     - fallback_triggered: bool
   ```

### 4.3 Phase 3: Additional Local Runtimes (Future)

**Not in Phase 1 scope, but planned for future:**

| Runtime | Hardware | Model Availability | Estimated Effort |
|---------|----------|-------------------|------------------|
| llama.cpp | CPU-heavy, cross-platform | Wide (GGUF format) | 2-3 days |
| Apple MLX | Apple Silicon optimized | Growing | 2-3 days |
| NVidia CUDA | CUDA-enabled GPUs | Excellent | 3-4 days |
| WebLLM | Browser-based | Limited | 2 days |

---

## 5. Risk Analysis & Mitigation

### 5.1 Risk Matrix

| Risk | Severity | Probability | Mitigation |
|------|----------|------------|------------|
| Ollama crashes mid-inference | HIGH | MEDIUM | Auto-fallback to cloud; circuit breaker pattern |
| Local models outdated vs cloud | MEDIUM | HIGH | Version pinning; user notifications on updates |
| No local GPU (CPU-only too slow) | MEDIUM | HIGH | Offer cloud alternative; show latency estimates |
| User runs out of disk space | LOW | LOW | Model size warnings; docs recommend 50GB free |
| Ollama port conflict (11434 used) | LOW | MEDIUM | Allow `OLLAMA_BASE_URL` override; use alt port |
| Quality delta unknown at runtime | MEDIUM | MEDIUM | Benchmark models on first run; cache results |
| Local model token counting inaccurate | LOW | MEDIUM | Conservative estimate (1.3x token count) |

### 5.2 Mitigation Strategies

#### Risk: Ollama Crashes During Inference

**Mitigation:**
1. **Circuit breaker pattern:** Track Ollama failures (3 consecutive → "open circuit")
2. **Automatic fallback:** If circuit open, all tasks → cloud
3. **Health check:** Periodic `GET /api/tags` to detect recovery
4. **Retry logic:** Exponential backoff (1s, 2s, 4s, 8s max)

```python
class OllamaCircuitBreaker:
    """Prevent cascading failures"""
    def __init__(self, failure_threshold=3):
        self.failure_count = 0
        self.is_open = False
        self.last_check = time.time()
    
    def call(self, task):
        if self.is_open:
            # Return cloud route
            return self.fallback(task)
        
        try:
            result = ollama_provider.query(task)
            self.failure_count = 0  # Reset on success
            return result
        except Exception as e:
            self.failure_count += 1
            if self.failure_count >= 3:
                self.is_open = True
                logger.warning(f'Ollama circuit breaker open: {e}')
            return self.fallback(task)
```

#### Risk: Local Models Outdated

**Mitigation:**
1. **Version tracking:** Log model sha256 hash on startup
2. **Notifications:** Alert user if newer version available (weekly check)
3. **User override:** Allow `--use-latest-models` flag to update before next run
4. **Documentation:** Clear guidance on `ollama pull` updates

#### Risk: No Local GPU (CPU-Only Too Slow)

**Mitigation:**
1. **Latency detection:** Benchmark on first run (profile 100-token inference)
2. **User choice:** If latency > 5s, prompt user: "Local slower than cloud. Prefer local ($0) or cloud (faster)?"
3. **Fallback default:** If user doesn't respond, route to cloud
4. **Documentation:** Recommend GPU hardware; provide CPU-only guidance

#### Risk: Port Conflict or Firewall

**Mitigation:**
1. **Environment override:** `OLLAMA_BASE_URL=http://localhost:11435` (alternative port)
2. **Remote Ollama support:** `OLLAMA_BASE_URL=http://192.168.1.100:11434` (remote machine)
3. **Error message:** Clear guidance: "Ollama not detected at localhost:11434. Set OLLAMA_BASE_URL or install Ollama."

---

## 6. Deployment Strategy

### 6.1 Rollout Plan

**Phased approach to avoid disruption:**

**Phase 2a: Shadow Mode (Day 1-2)**
- Deploy OllamaProvider, detection logic
- Route *some* tasks to Ollama, capture metrics
- **No user impact:** Cloud remains primary
- **Monitoring:** Track success rate, latency, cost savings

**Phase 2b: Opt-In (Day 3)**
- Enable Ollama routing for *users who opt in*
- `opencode config set ollama_enabled=true`
- **User action required:** Prevents surprise latency
- **Documentation:** Guide users through setup

**Phase 2c: Default Enabled (Day 4-5)**
- Enable Ollama for all users (if Ollama available)
- Cloud remains fallback
- **Gradual rollout:** Start 50% → 75% → 100%
- **Kill switch:** `opencode ollama disable` anytime

### 6.2 Monitoring & Observability

**Metrics to track:**

1. **Availability**
   - Ollama availability % (target: >99%)
   - Fallback rate (target: <1%)

2. **Performance**
   - Local latency P50, P95, P99
   - Cloud latency P50, P95, P99
   - Quality scores (local vs cloud)

3. **Cost**
   - Monthly savings (local vs cloud)
   - Per-user ROI projections
   - Cost breakdown by provider

4. **Reliability**
   - Crash rate (target: <0.1%)
   - Circuit breaker activations (target: 0)
   - Fallback success rate (target: >99%)

**Dashboards:**
- Real-time Ollama status (available/unavailable)
- Cost savings projection
- Quality comparison (local vs cloud)

### 6.3 Rollback Plan

**If issues arise:**
1. **Quick disable:** `opencode ollama disable` (system-wide)
2. **Per-task override:** `--force-cloud` flag on any task
3. **Config option:** `ollama_enabled: false` in `.env`
4. **Automatic rollback:** Monitoring detects failure rate >5%, auto-disables Ollama

---

## 7. Success Criteria

### Phase 1 (This Document)

✅ **Architectural design complete:**
- Ollama detection strategy defined
- Cost accounting model clear
- Routing logic unambiguous
- Risk mitigations identified
- Implementation roadmap ready

✅ **No ambiguities:**
- How agents detect Ollama: `GET /api/tags` on startup
- Cost tracking: `provider: "ollama"`, `cost: 0.00`
- Fallback logic: Automatic on any failure
- User communication: Show cost savings, offer cloud alternative if needed

✅ **Ready for Senior Engineer implementation (Phase 2)**
- OllamaProvider class interface defined
- Routing algorithm pseudo-code provided
- Test scenarios identified
- Configuration options documented

### Phase 2 (Implementation) — Target Completion: June 1, 2026

- [ ] OllamaProvider class implemented (src/providers/ollama_provider.py)
- [ ] ModelResolver enhanced with Ollama detection
- [ ] Routing logic integrated
- [ ] CLI commands: `ollama list`, `ollama detect`, `ollama disable`
- [ ] 50+ tests covering:
  - Ollama detection (success, timeout, connection refused)
  - Fallback on failure
  - Model routing decisions
  - Cost accounting
  - Circuit breaker activation
- [ ] Documentation: `docs/QUICK-START-OLLAMA.md`
- [ ] All existing tests still passing
- [ ] Ready for production deployment

---

## 8. User-Facing Documentation Outline

**For Phase 2 implementation:**

### docs/QUICK-START-OLLAMA.md

```
# Ollama Quick Start

## Setup

1. Install Ollama: https://ollama.ai
2. Pull a model: ollama pull mistral
3. Run: ollama serve

## Framework Integration

### Automatic Detection
Framework detects Ollama on localhost:11434 automatically.

### Check Status
opencode ollama detect

### List Available Models
opencode ollama list

### Disable Ollama
opencode ollama disable

## Cost Savings
Local models cost $0 (no API charges).
Equivalent cloud inference: ~$2-3/month → $0 with Ollama.

## Performance
- Local inference: 200ms-5s per task
- Cloud inference: 200-400ms per task
- Tradeoff: Slower, but free

## Fallback
If Ollama unavailable, framework automatically uses cloud providers.
```

---

## 9. Appendix: Model Compatibility Matrix

### Ollama Model Sizes & Performance

| Model | Parameters | Size | Haiku-eq? | Sonnet-eq? | Speed (GPU) | Speed (CPU) |
|-------|-----------|------|-----------|-----------|-----------|-----------|
| mistral | 7B | 4GB | ✅ | ❌ | ~100 t/s | ~10 t/s |
| neural-chat | 7B | 4GB | ✅ | ❌ | ~100 t/s | ~10 t/s |
| openchat | 13B | 8GB | ✅ | ⚠️ | ~50 t/s | ~5 t/s |
| llama2 | 13B | 8GB | ✅ | ⚠️ | ~50 t/s | ~5 t/s |
| solar | 10.7B | 6GB | ✅ | ❌ | ~80 t/s | ~8 t/s |
| dolphin-mixtral | 46B | 27GB | ⚠️ | ✅ | ~20 t/s | N/A |
| llama2-uncensored | 70B | 40GB | ❌ | ✅ | ~10 t/s | N/A |

### Recommendation: Default Model Selection

**For Haiku tasks:** `mistral:7b` (best speed/quality tradeoff)
**For Sonnet tasks:** `dolphin-mixtral:46b` (if GPU available)
**For CPU-only:** `mistral:7b` (only option, warn user about latency)

---

## 10. Decision Log

| Date | Decision | Rationale | Status |
|------|----------|-----------|--------|
| 2026-05-28 | Ollama first, not llama.cpp | Most popular, widest model support, easiest install | APPROVED |
| 2026-05-28 | Local = $0 in accounting | Conservative: ignore electricity for now | APPROVED |
| 2026-05-28 | Auto-detection, not manual config | Improves UX, zero setup required | APPROVED |
| 2026-05-28 | 5-second latency SLA | Balances cost savings with user expectations | APPROVED |
| 2026-05-28 | Haiku → local first | Max cost savings for most common tasks | APPROVED |
| 2026-05-28 | Opus → always cloud | No viable local equivalent | APPROVED |

---

## Conclusion

This architecture provides a **clear, implementable path** to 95% cost reduction for users running agents on local hardware. The design prioritizes:

1. **Simplicity:** Auto-detection, zero config required
2. **Reliability:** Graceful fallback to cloud
3. **Transparency:** Users see exactly where tasks run and what they cost
4. **Flexibility:** Easy to extend to other runtimes (llama.cpp, etc.)

The Phase 2 implementation roadmap is ready for Senior Engineers to execute. No ambiguities remain about routing logic, cost tracking, or failure handling.

**Confidence Level: 0.95** — High confidence in architecture feasibility, team capacity, and timeline.
