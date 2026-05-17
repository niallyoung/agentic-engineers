# Phase 3: Implementation & Optimization Plan

## Overview
Phase 1 & 2 completed comprehensive analysis of harness consistency and parallel delegation. Phase 3 focuses on implementing the highest-priority improvements identified in the analysis.

## Phase 3 Goals

### Goal 1: Implement Tier 1 Harness Gaps
**Effort**: 4-6 weeks
**Impact**: Improve harness parity across π.dev, Claude Code, Copilot CLI, OpenCode

### Goal 2: Deploy Parallel Delegation (Orchestrator)
**Effort**: 2-3 weeks
**Impact**: Enable 100+ concurrent agents, 4-5× parallelism factor

### Goal 3: Integrate Token Visibility
**Effort**: 1-2 weeks
**Impact**: Real-time token tracking, cost optimization

### Goal 4: Optimize Model Selection
**Effort**: 1-2 weeks
**Impact**: Cost reduction, quality improvement via dynamic model routing

## Tier 1 Harness Gaps (by priority)

### π.dev (3 bugs)
1. **Argument parsing bug** (HIGH)
   - Issue: Arguments not passed correctly to renderer
   - Impact: Breaks feature testing
   - Effort: 2-4 hours
   - Files: src/harnesses/pi-dev/renderer.py

2. **Premature mkdir** (HIGH)
   - Issue: Directory created before validation
   - Impact: Leaves orphaned directories on error
   - Effort: 1-2 hours
   - Files: src/harnesses/pi-dev/setup.py

3. **Missing error handling** (MEDIUM)
   - Issue: No graceful error recovery
   - Impact: Crashes on invalid input
   - Effort: 2-3 hours
   - Files: src/harnesses/pi-dev/main.py

### Claude Code (2 features)
1. **Workspace isolation** (HIGH)
   - Issue: No workspace-level isolation
   - Impact: Cross-project contamination
   - Effort: 4-6 hours
   - Files: src/harnesses/claude-code/workspace.py

2. **Extended context window** (MEDIUM)
   - Issue: Limited to 32k tokens
   - Impact: Cannot handle large files
   - Effort: 3-4 hours
   - Files: src/harnesses/claude-code/context.py

### Copilot CLI (1 feature)
1. **Streaming output** (HIGH)
   - Issue: No streaming support
   - Impact: Long waits for large outputs
   - Effort: 3-4 hours
   - Files: src/harnesses/copilot-cli/streaming.py

## Tier 1 Orchestrator Improvements

### 1. Dry-Run Mode (CRITICAL)
**Effort**: 4-6 hours
**Impact**: Safe testing before production deployment

Tasks:
- [ ] Implement dry-run flag in parallel_delegate.py
- [ ] Create test suite for dry-run mode
- [ ] Document dry-run usage and examples
- [ ] Add dry-run to AGENTS.md

### 2. Shadow Mode (CRITICAL)
**Effort**: 6-8 hours
**Impact**: Gradual rollout with monitoring

Tasks:
- [ ] Implement shadow mode (10% traffic)
- [ ] Create metrics collection for shadow mode
- [ ] Add shadow mode configuration to decomposition_config.yaml
- [ ] Document shadow mode rollout strategy

### 3. Gradual Rollout (CRITICAL)
**Effort**: 4-6 hours
**Impact**: Safe production deployment

Tasks:
- [ ] Implement rollout stages (10% → 25% → 50% → 75% → 100%)
- [ ] Create feature flag system
- [ ] Add rollout monitoring and alerts
- [ ] Document rollout procedure

### 4. Monitoring & Observability (HIGH)
**Effort**: 8-10 hours
**Impact**: Real-time visibility into parallel delegation

Tasks:
- [ ] Create metrics dashboard (Grafana)
- [ ] Add alerts for decomposition failures
- [ ] Implement tracing for parallel tasks
- [ ] Document monitoring setup

## Token Visibility Integration

### Tasks
1. **Integrate token-aggregator plugin** (2-3 hours)
   - [ ] Add token tracking to parallel_delegate.py
   - [ ] Update metrics collection
   - [ ] Create token visibility dashboard

2. **Cost optimization** (3-4 hours)
   - [ ] Analyze token usage by agent type
   - [ ] Identify cost reduction opportunities
   - [ ] Implement cost optimization recommendations

3. **Documentation** (1-2 hours)
   - [ ] Update AGENTS.md with token visibility section
   - [ ] Create token optimization guide
   - [ ] Add cost tracking examples

## Model Selection Strategy

### Available Models (Keep Claude for now)
- **Claude Haiku 4.5** (0.33x): Current orchestrator model
- **Claude Sonnet 4.5/4.6** (1x): Balanced, general purpose
- **Claude Opus 4.7** (15x): Best reasoning (available if needed)

### Future Options (Available but not yet deployed)
- **GPT-5.5** (7.5x): Extended thinking, ultra-high complexity
- **GPT-5.4** (1x): Default OpenAI model
- **GPT-5.3-Codex** (1x): Code generation

### Phase 3 Strategy
- Continue using Claude models exclusively
- Haiku for routing/coordination
- Sonnet for standard work
- Opus available if consolidation tasks need extra reasoning
- **No model changes yet** — keep current selection

### Phase 4+ Strategy
- Evaluate GPT-5.5 for extended thinking tasks
- Consider cost-quality tradeoffs
- Run A/B tests if switching models
- Keep Claude as fallback

## Phase 3 Timeline

### Week 1: Planning & Setup
- [ ] Finalize Phase 3 plan
- [ ] Create implementation roadmap
- [ ] Set up monitoring infrastructure
- [ ] Prepare test environments

### Week 2-3: Harness Gaps Implementation
- [ ] Implement π.dev fixes (3 bugs)
- [ ] Implement Claude Code features (2 features)
- [ ] Implement Copilot CLI features (1 feature)
- [ ] Test and validate all fixes

### Week 3-4: Orchestrator Improvements
- [ ] Implement dry-run mode
- [ ] Implement shadow mode
- [ ] Implement gradual rollout
- [ ] Set up monitoring and alerts

### Week 4-5: Token Visibility & Model Optimization
- [ ] Integrate token visibility
- [ ] Implement complexity-based routing
- [ ] Run A/B tests for model selection
- [ ] Optimize cost-quality tradeoff

### Week 5-6: Testing & Validation
- [ ] Comprehensive testing of all improvements
- [ ] Performance benchmarking
- [ ] Cost analysis and optimization
- [ ] Documentation and training

### Week 6+: Production Deployment
- [ ] Dry-run phase (Week 1)
- [ ] Shadow mode (Week 2)
- [ ] Gradual rollout (Weeks 3-4)
- [ ] Full production (Week 5+)

## Success Metrics

### Harness Consistency
- [ ] All Tier 1 gaps implemented
- [ ] Feature parity across all 4 harnesses
- [ ] Zero critical bugs in production
- [ ] 95%+ test coverage

### Parallel Delegation
- [ ] 100+ concurrent agents in production
- [ ] 4-5× parallelism factor achieved
- [ ] Zero decomposition failures
- [ ] <5% overhead from decomposition

### Token Visibility
- [ ] Real-time token tracking enabled
- [ ] Cost visibility for all agents
- [ ] 20%+ cost reduction achieved
- [ ] Token forecasting accuracy >90%

### Model Optimization
- [ ] Strategy documented
- [ ] A/B testing framework ready
- [ ] Available models documented (Claude, GPT-5.5)
- [ ] Ready for Phase 4 implementation

## Risk Mitigation

### Risk 1: Parallel Delegation Failures
- Mitigation: Dry-run mode, shadow mode, gradual rollout
- Fallback: Feature flag to disable parallel delegation

### Risk 2: Token Cost Overrun
- Mitigation: Token visibility, cost monitoring, alerts
- Fallback: Revert to single-DELEGATE mode

### Risk 3: Quality Degradation
- Mitigation: A/B testing, quality metrics, monitoring
- Fallback: Revert to previous model selection

### Risk 4: Harness Incompatibilities
- Mitigation: Comprehensive testing, validation
- Fallback: Maintain separate harness implementations

## Next Steps

1. **Approve Phase 3 plan**
   - Review and validate timeline
   - Confirm resource allocation
   - Identify any blockers

2. **Create detailed implementation specs**
   - Break down each task into subtasks
   - Assign owners and deadlines
   - Set up tracking and monitoring

3. **Begin Week 1 planning**
   - Finalize implementation roadmap
   - Set up monitoring infrastructure
   - Prepare test environments

4. **Start Week 2 implementation**
   - Begin harness gaps implementation
   - Parallel Orchestrator improvements
   - Token visibility integration
