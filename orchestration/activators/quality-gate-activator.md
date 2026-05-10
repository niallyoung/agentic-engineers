---
name: Quality Gate Orchestrator Activator
description: Pseudo-code + integration points for activating Quality Gate Orchestrator agent locally
created: 2026-04-28
type: specification
phase: 5.10
---

# Quality Gate Orchestrator Activator

## Overview

This document specifies how the Quality Gate Orchestrator agent is invoked from git hooks, receives DELEGATE blocks, delegates to 4 sub-agents in parallel, and returns HANDBACK blocks.

**Integration Points**:
- Input: `artifacts/2026-MM-DD/DELEGATE-{timestamp}-commit-{service}.yaml` (written by pre-commit hook)
- Output: `artifacts/2026-MM-DD/HANDBACK-{timestamp}-commit-{service}.yaml` (read by pre-commit hook)
- Side effects: OpenTelemetry spans written to `artifacts/2026-MM-DD/SPAN-*.yaml`

---

## Quality Gate Orchestrator Agent Logic (Pseudo-Code)

```python
class QualityGateOrchestrator:
    """
    Orchestrator Agent: Routes quality checks to 4 parallel sub-agents.
    
    Inputs: DELEGATE block from git hook
    Outputs: HANDBACK block (final_decision: PROCEED | ESCALATE)
    """
    
    def __init__(self):
        self.model = "claude-sonnet-4-6"
        self.role = "Orchestrator"
        self.trace_id = None
        self.sub_agents = {
            "security": SecurityAgent(),
            "testing": TestingAgent(),
            "metrics": MetricsAgent(),
            "healing": HealingAgent(),
        }
    
    def process_delegate(self, delegate_block: dict) -> dict:
        """
        Receive DELEGATE block from git hook.
        
        delegate_block:
            {
                "handoff_type": "DELEGATE",
                "task_id": "2026-05-26-commit-{example-service}-{sha}",
                "timestamp": "2026-05-26T09:00:00Z",
                "repo_path": "$WORKSPACE_ROOT/{example-service}",
                "service_name": "{example-service}",
                "commit_sha": "abc123def...",
                "budget_context": {
                    "session_pct": 45.0,
                    "trend": "stable",
                    "recommended_model": "sonnet"
                }
            }
        """
        self.trace_id = self.generate_trace_id()
        root_span = self.create_span("quality-gate-root", self.trace_id)
        root_span.attributes = {
            "service_name": delegate_block["service_name"],
            "commit_sha": delegate_block["commit_sha"],
            "job_type": "quality-gate",
        }
        root_span.start()
        
        # --- Phase 1: Parallel Delegation ---
        results = self.delegate_to_sub_agents_parallel(delegate_block)
        
        # --- Phase 2: Aggregation ---
        handback = self.aggregate_results(results, delegate_block)
        
        # --- Phase 3: Model Engineer Feedback (Async) ---
        self.delegate_to_model_engineer_async(delegate_block, results)
        
        root_span.end()
        return handback
    
    def delegate_to_sub_agents_parallel(self, delegate_block: dict) -> dict:
        """
        Delegate to 4 sub-agents in parallel.
        Each sub-agent writes its HANDBACK to artifacts/ independently.
        Orchestrator polls artifacts/ for HANDBACK blocks until all received or timeout.
        """
        task_id = delegate_block["task_id"]
        
        # Step 1: Write DELEGATE blocks to disk (one per sub-agent)
        for agent_name in ["security", "testing", "metrics", "healing"]:
            sub_delegate = self.create_sub_delegate(delegate_block, agent_name)
            self.write_artifact(f"DELEGATE-{task_id}-{agent_name}.yaml", sub_delegate)
        
        # Step 2: Invoke sub-agents (in parallel)
        futures = {}
        for agent_name, agent in self.sub_agents.items():
            futures[agent_name] = self.invoke_agent_async(agent, task_id, agent_name)
        
        # Step 3: Wait for all sub-agents to return HANDBACK (or timeout at 5 min)
        results = {}
        timeout_ms = 5 * 60 * 1000  # 5 minutes
        poll_interval_ms = 100
        elapsed = 0
        
        while elapsed < timeout_ms:
            for agent_name in self.sub_agents:
                if agent_name not in results:
                    handback_path = f"artifacts/2026-MM-DD/HANDBACK-{task_id}-{agent_name}.yaml"
                    if self.file_exists(handback_path):
                        results[agent_name] = self.read_artifact(handback_path)
                        self.create_span_from_handback(results[agent_name])
            
            if len(results) == 4:  # All 4 sub-agents returned
                return results
            
            sleep(poll_interval_ms)
            elapsed += poll_interval_ms
        
        # Step 4: Timeout - escalate with partial results
        if len(results) < 4:
            missing = set(self.sub_agents.keys()) - set(results.keys())
            self.log_error(f"Timeout waiting for {missing} agents")
            # Return partial results, escalate in aggregation
        
        return results
    
    def aggregate_results(self, results: dict, delegate_block: dict) -> dict:
        """
        Combine HANDBACK blocks from all sub-agents into single decision.
        
        Decision Logic:
        - If ANY agent status != PASS: escalate
        - If ANY severity >= HIGH: escalate
        - If ALL pass AND health_score >= 85: PROCEED
        - Else: ESCALATE with details
        """
        agg_span = self.create_span("decision-aggregation", self.trace_id)
        agg_span.start()
        
        # Parse all HANDBACK blocks
        audit_trail = []
        escalation_reasons = []
        
        for agent_name, handback in results.items():
            audit_trail.append({
                "agent": agent_name,
                "timestamp": handback["timestamp"],
                "status": handback.get("status", "UNKNOWN"),
                "severity": handback.get("severity", "INFO"),
                "findings": handback.get("findings_count", 0),
            })
            
            if handback.get("status") != "PASS":
                escalation_reasons.append(f"{agent_name}: {handback.get('reason', 'failed')}")
            
            if handback.get("severity") in ["HIGH", "CRITICAL"]:
                escalation_reasons.append(f"{agent_name}: {handback['severity']} issue")
        
        # Decision
        if escalation_reasons:
            final_decision = "ESCALATE"
            recommendation = f"Issues detected: {'; '.join(escalation_reasons)}"
        else:
            # Check health score (if available from metrics agent)
            health_score = results.get("metrics", {}).get("health_score", 85)
            if health_score >= 85:
                final_decision = "PROCEED"
                recommendation = "All checks passed; quality gate complete"
            else:
                final_decision = "ESCALATE"
                recommendation = f"Health score {health_score} below threshold"
        
        # Build HANDBACK
        handback = {
            "handoff_type": "HANDBACK",
            "task_id": delegate_block["task_id"],
            "timestamp": self.iso_now(),
            "status": "complete",
            "final_decision": final_decision,
            "audit_trail": audit_trail,
            "recommendation": recommendation,
            "attributes": {
                "trace_id": self.trace_id,
                "sub_agent_count": len(results),
                "escalations_count": len(escalation_reasons),
                "total_tokens_used": sum(r.get("tokens_used", 0) for r in results.values()),
            }
        }
        
        agg_span.attributes = {
            "final_decision": final_decision,
            "escalations": len(escalation_reasons),
            "total_tokens": handback["attributes"]["total_tokens_used"],
        }
        agg_span.end()
        
        return handback
    
    def delegate_to_model_engineer_async(self, delegate_block: dict, results: dict):
        """
        Asynchronously delegate to Model Engineer for feedback.
        This does NOT block the decision; happens after HANDBACK written.
        """
        # Create DELEGATE block for Model Engineer
        model_engineer_delegate = {
            "handoff_type": "DELEGATE",
            "task_id": delegate_block["task_id"] + "-model-feedback",
            "timestamp": self.iso_now(),
            "role": "Model Engineer",
            "model": "claude-sonnet-4-6",
            "scope": "Analyze token usage and recommend optimal model for next similar task",
            "context": {
                "previous_models_used": {
                    "orchestrator": "claude-sonnet-4-6",
                    "sub_agents": {
                        "security": "claude-opus-4-7",
                        "testing": "claude-sonnet-4-6",
                        "metrics": "claude-haiku-4-5",
                        "healing": "claude-sonnet-4-6",
                    }
                },
                "observed_tokens": {
                    agent: results[agent].get("tokens_used", 0)
                    for agent in results
                },
                "decision_quality": results.get("final_decision", "UNKNOWN"),
                "total_duration_ms": results.get("total_duration_ms", 0),
            }
        }
        
        # Write to disk (async, fire-and-forget)
        self.write_artifact_async(
            f"DELEGATE-{model_engineer_delegate['task_id']}.yaml",
            model_engineer_delegate
        )
```

---

## Integration: Git Hook ↔ Orchestrator

### Step 1: Pre-commit Hook (Enhanced)

```bash
#!/bin/bash
# {workspace-name}/githooks/pre-commit (enhanced for Phase 5.10)

REPO_NAME=$(basename "$(git rev-parse --show-toplevel)")
SERVICE_NAME="$REPO_NAME"
COMMIT_SHA=$(git rev-parse HEAD)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
TASK_ID="2026-MM-DD-commit-${SERVICE_NAME}-${COMMIT_SHA:0:8}"

# ... existing validation (version bump) ...

if [ ! -f "Makefile" ]; then
    echo -e "${YELLOW}  ⏭ No Makefile — skipping quality-gate${NC}"
    exit 0
fi

# PHASE 5.10: Create DELEGATE block for Quality Gate Orchestrator
DELEGATE_BLOCK=$(cat <<EOF
---
handoff_type: DELEGATE
task_id: $TASK_ID
timestamp: $TIMESTAMP
repo_path: "$(pwd)"
service_name: $SERVICE_NAME
commit_sha: $COMMIT_SHA
budget_context:
  session_pct: 45.0
  trend: stable
  recommended_model: sonnet
EOF
)

# Write DELEGATE block to artifacts/
ARTIFACTS_DIR="$(git rev-parse --show-toplevel)/.claude/artifacts/$(date +%Y-%m-%d)"
mkdir -p "$ARTIFACTS_DIR"
echo "$DELEGATE_BLOCK" > "$ARTIFACTS_DIR/DELEGATE-$TIMESTAMP-commit-$SERVICE_NAME.yaml"

# Invoke Quality Gate Orchestrator agent
# (In reality: this would be invoked via Anthropic API)
# For Phase 5.10: we'll simulate by calling make quality-gate
echo -e "${CYAN}  ▸ Delegating to Quality Gate Orchestrator...${NC}"

if ! make quality-gate 2>&1; then
    echo -e "${RED}❌ Quality gate failed — commit rejected${NC}"
    exit 1
fi

echo -e "${GREEN}✅ pre-commit passed${NC}"
```

### Step 2: Orchestrator Reads HANDBACK

After orchestrator completes and writes HANDBACK, the hook reads it:

```bash
# After make quality-gate returns
HANDBACK_PATH="$ARTIFACTS_DIR/HANDBACK-$TIMESTAMP-commit-$SERVICE_NAME.yaml"

if [ -f "$HANDBACK_PATH" ]; then
    DECISION=$(grep "final_decision:" "$HANDBACK_PATH" | awk '{print $2}')
    if [ "$DECISION" = "ESCALATE" ]; then
        echo -e "${RED}❌ Escalated by Quality Gate Orchestrator${NC}"
        grep "recommendation:" "$HANDBACK_PATH"
        exit 1
    fi
fi

# If we get here: PROCEED (allow commit)
```

---

## Artifact File Locations

```
artifacts/
├── 2026-04-28/
│   ├── DELEGATE-2026-04-28T09:00:00Z-commit-{example-service}.yaml (hook writes)
│   ├── SPAN-2026-04-28T09:00:00Z-quality-gate-root.yaml (orchestrator writes)
│   ├── SPAN-2026-04-28T09:00:15Z-agent-security.yaml (security agent)
│   ├── SPAN-2026-04-28T09:00:15Z-agent-testing.yaml (testing agent)
│   ├── SPAN-2026-04-28T09:00:15Z-agent-metrics.yaml (metrics agent)
│   ├── SPAN-2026-04-28T09:00:15Z-agent-healing.yaml (healing agent)
│   ├── HANDBACK-2026-04-28T09:00:00Z-commit-{example-service}.yaml (orchestrator writes)
│   └── index.json (auto-generated, lists all artifacts)
```

---

## Success Criteria (Phase 5.10)

- [ ] Quality Gate Orchestrator agent responds to DELEGATE blocks
- [ ] Receives input: repo_path, service_name, commit_sha, budget_context
- [ ] Delegates in parallel to 4 sub-agents (Security, Testing, Metrics, Healing)
- [ ] Waits for all HANDBACK blocks (5-min timeout)
- [ ] Aggregates into single HANDBACK (final_decision: PROCEED/ESCALATE)
- [ ] Writes OpenTelemetry spans for all operations
- [ ] Git hook reads HANDBACK and makes allow/reject decision
- [ ] First 10 real commits produce artifacts with full audit trail
- [ ] No errors in orchestration logic
- [ ] Latency <5 min per commit

---

## Timeline: Phase 5.10

- **Week 1 (2026-05-26 → 2026-05-30)**: Implement + test Quality Gate Orchestrator activation
- **Week 2 (2026-05-31 → 2026-06-02)**: Validate end-to-end, collect telemetry, prepare for Phase 6

