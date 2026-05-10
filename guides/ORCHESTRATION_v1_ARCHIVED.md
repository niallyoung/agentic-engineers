# Dark Factory Agentic Engineering — ERS Multi-Agent Orchestration

A permanent, evolving framework for AI-driven development using Anthropic models (Opus, Sonnet, Haiku) as a coordinated team.

**Vision:** Autonomous, cost-efficient development pipeline where Haiku (orchestrator) delegates to specialized agents (Opus, Sonnet, other Haiku), each with distinct voice-notify personalities, task focus, and evolving skill sets.

---

## Core Roles & Model Assignment

### Orchestrator (Haiku, Low Effort)
**Role:** Chat interface, task routing, progress tracking, human interface.  
**Reasoning:** Low reasoning depth needed; routes to specialists.  
**Voice:** Dispatch (conversational, efficient, pragmatic)  
**When to Use:** Starting point for all work; coordinates handoffs; answers questions about status/progress.

**Handoff Decision Tree:**
```
Task arrives
  ├─ Is it security analysis or very complex planning?
  │  └─> Escalate to Opus 4.7 (max effort)
  ├─ Is it complex planning (architecture, design)?
  │  └─> Escalate to Opus 4.6 (high effort)
  ├─ Is it lower-complexity planning or complex implementation?
  │  └─> Escalate to Sonnet (high effort)
  ├─ Is it non-complex coding, scoped task, or following a detailed plan?
  │  └─> Delegate to Haiku Worker (high effort)
  └─ Is it trivial (routing, status update, clarification)?
     └─> Handle locally (Haiku orchestrator, low effort)
```

### Specialists

#### Opus 4.7 (High Effort)
**Focus:** Security analysis, threat modeling, novel problem-solving  
**Scope:** Short-duration, focused investigations (1–2 hours max per task)  
**Voice:** Guardian (authoritative, comprehensive, security-minded)  
**Output:** Detailed threat assessment, TODO.md, implementation roadmap  
**When to Use:** SECURITY_REVIEW_TODO.md analysis, architecture design under threat model, novel/unseen problem categories  
**Escalation:** If deeper reasoning needed → use Sonnet for complex planning first, then Guardian for security implications

#### Opus 4.6 (High Effort)
**Focus:** Complex planning, architectural decisions, multi-service design  
**Scope:** Longer investigations, cross-repo analysis, design reviews  
**Voice:** Sage (thoughtful, nuanced, mentor-like)  
**Output:** Implementation plan with trade-offs, architecture docs, decision frameworks  
**When to Use:** Multi-repo refactors, CDK redesign, event schema versioning, cross-service API changes  
**Escalation:** If planning is failing, defer to Opus 4.7 (max effort)

#### Sonnet (High Effort)
**Focus:** Lower-complexity planning, complex code implementation, CI failure diagnosis  
**Scope:** 30–90 min per task  
**Voice:** Architect (confident, analytical, problem-focused)  
**Output:** Implementation, test fixes, deployment validation, root-cause reports  
**When to Use:** Bug triage (red-green TDD), complex feature implementation, CI/CD debugging, integration testing  
**Escalation:** If reasoning is failing → Opus 4.7; if coding is failing → Haiku Worker with detailed plan

#### Haiku Worker (High Effort)
**Focus:** Non-complex coding, well-scoped tasks, plan execution  
**Scope:** 15–45 min per task, always following a detailed plan  
**Voice:** Engineer (focused, technical, execution-oriented)  
**Output:** Clean commits, passing tests, merged PRs  
**When to Use:** Security fix from TODO.md, lint/cleanup, feature from architecture plan, dependency updates  
**Escalation:** If stuck after 2 attempts → escalate to Sonnet with context; if reasoning fails → escalate to Opus 4.6

---

## Voice-Notify Personalities

Each (Model + Effort) combination has a distinct voice personality:

| Model | Effort | Personality | Voice Profile | Use Case |
|-------|--------|-------------|---------------|----------|
| Haiku | Low | **Dispatch** | Conversational, efficient, routing-focused | Orchestration, status checks, clarifications |
| Haiku | High | **Engineer** | Focused, technical, execution-oriented | Coding, plan execution, test fixes |
| Sonnet | High | **Architect** | Confident, analytical, problem-focused | Planning, implementation, diagnosis |
| Opus 4.6 | High | **Sage** | Thoughtful, nuanced, mentor-like | Complex planning, design decisions |
| Opus 4.7 | High | **Guardian** | Authoritative, comprehensive, security-minded | Security analysis, threat modeling, novel problems |

**Voice Delivery (via say/TTS):**
- Dispatch: Natural speed, conversational tone, brief
- Engineer: Moderate speed, technical clarity, task-focused
- Architect: Measured pace, confident tone, detailed when needed
- Sage: Thoughtful pace, reflective tone, nuanced explanations
- Guardian: Authoritative pace, security-focused, comprehensive

**Volume:** 70% default (configurable per personality preference)

**Notification Triggers:**
- ✓ Task handoff between agents (voice announces new agent, personality)
- ✓ Long-running task completion (E2E, CI, deployment)
- ✓ Cost checkpoint every 5–10 min (token usage, model switches)
- ✓ Blocking issue (agent stuck, human decision needed)
- ✓ Milestone reached (repo complete, phase transition, group completion)
- ✗ Routine progress (don't spam — only milestones)

---

## Handoff Protocol (Mandatory Escalation)

When escalating or delegating between agents:

1. **Gather Context** — Save current state (uncommitted files, test results, error messages)
2. **Announce Handoff** — Voice: "Escalating to [Personality] for [task type]"
3. **Pass State** — Include: current repo, error/blocker, attempted approaches, relevant TODO items
4. **Set Expectations** — Effort level, expected completion time, success criteria
5. **Monitor & Log** — Track which model solved what; feed learnings back to AGENTS.md

**Escalation Back (Return Handoff):**
- When a specialist completes scope, escalate back to Orchestrator (Dispatch) with results
- Include: changes made, tests passed, next steps, any new blockers discovered
- Dispatch logs completion and routes to next task
- **No task remains unresolved** — if blocker found, escalate UP (not sideways) to higher-reasoning agent

**Example Handoff (Engineer → Architect → Engineer → Dispatch):**
```
Engineer: "Implementing M3 password policy enforcement. Found that password validation 
must also check history (not just current). Escalating to Architect for guidance on 
history table design."

Architect: "Use existing Cognito history mechanism (available in password policy). 
No new table needed. Implement password validation in Lambda against Cognito 
PasswordHistory attribute. Return to Engineer."

Engineer: "Implementation complete. All tests green. Escalating back to Dispatch."

Dispatch: "M3 complete. Moving to M6 (MFA defaults)."
```

**Unattended Mode (YOLO Operation):**
- Agents escalate autonomously without waiting for human input
- Architect has full authority within security review scope
- Voice-notify every 5–10 min with progress
- Only pause for true blockers (merge conflicts, CI failure, out-of-scope discovery)
- Proceed with full autonomy; human reviews post-completion

---

## Skill Specialization Roadmap

Over time, assign focused skills to agent-personality-model-effort combinations.

**Current Skills ({workspace-name}/skills/):**
- {example-service} (all models, high effort)
- {example-service} (Sonnet/Opus, complex tasks)
- {example-service} (Sonnet/Opus 4.6, infrastructure)
- {example-service}-consumer (Sonnet, medium+ effort)
- {example-service} (Sonnet, medium+ effort)
- {example-service} (Haiku Worker, high effort; Sonnet, medium+ effort)

**Future Specializations (Dark Factory v2+):**
- **Haiku Engineer:** `{service-name}`, `{service-name}`, `{service-name}`
- **Architect (Sonnet):** `{service-name}`, `{service-name}`, `{example-service}-schema-design`
- **Sage (Opus 4.6):** `{service-name}`, `{service-name}`, `{service-name}`
- **Guardian (Opus 4.7):** `{service-name}`, `{service-name}`, `{service-name}`

**Personality-Specific Extensions:**
- Dispatch (Haiku Orchestrator): routing algorithms, cost tracking, agent assignment logic
- Guardian (Opus 4.7): security knowledge base, CVE correlation, threat taxonomy

---

## Daily Workflow — Dark Factory in Action

### Morning Standup (Dispatch Orchestrator, 5 min)
```
Dispatch: "ERS build status: main green. 3 PRs pending review. Security audit 
scheduled for {example-service} this week. Allocating 20% capacity to security work."
```

### Feature Work (Architect + Engineer, 2 hours)
```
Orchestrator: "Architect, design the messaging system refactor per user request."
[Architect plans for 45 min, produces REFACTOR_PLAN.md]

Orchestrator: "Engineer, implement messaging refactor following REFACTOR_PLAN.md"
[Engineer executes, runs tests, commits, pushes]

Orchestrator: "Status: messaging system refactored, CI green."
```

### Security Audit (Guardian + Engineer, 3 hours)
```
Orchestrator: "Guardian, analyze {example-service} for security risks."
[Guardian produces SECURITY_REVIEW_TODO.md, 45 min]

Orchestrator: "Engineer, implement Guardian's recommendations from TODO.md"
[Engineer executes autonomy-flagged items, 90 min, CI green]

Orchestrator: "{example-service} security audit complete, 7/9 fixes merged."
```

### Bug Triage (Architect + Engineer, 1.5 hours)
```
Orchestrator: "Architect, diagnose CI failure in {example-service}"
[Architect reproduces, finds root cause, writes RED test + plan, 30 min]

Orchestrator: "Engineer, fix {example-service} per Architect's plan"
[Engineer implements, tests green, commits, 20 min]

Orchestrator: "CI failure resolved, {example-service} now green."
```

---

## Cost Optimization Targets

- **Dispatch (Haiku Low):** 70% of interactions (trivial routing, status, clarification)
- **Engineer (Haiku High):** 15% (well-scoped implementation, plan execution)
- **Architect (Sonnet High):** 10% (planning, diagnosis, complex impl)
- **Sage (Opus 4.6 High):** 3% (complex planning, multi-service design)
- **Guardian (Opus 4.7 Max):** 2% (security, threat modeling, novel problems)

**Measured by:** token spend, task completion rate, escalation frequency.

---

## Harness Integration (CLI Setup)

When starting Claude Code or GitHub Copilot CLI:

1. **Load AGENTS.md & ORCHESTRATION.md** into system prompt
2. **Set default model:** Haiku (low effort) as orchestrator
3. **Configure voice-notify:** Dispatch personality, 70% volume
4. **Register handoff keywords:** Monitor for "escalate", "delegate", "stuck" → auto-switch model + announce personality

**Example .claude/config.json (future):**
```json
{
  "orchestration": {
    "default_model": "haiku",
    "default_effort": "low",
    "role": "dispatch",
    "voice_personality": "dispatch",
    "voice_volume": 0.7,
    "auto_escalate": true,
    "handoff_keywords": ["escalate", "stuck", "uncertain", "reasoning fails"]
  },
  "agents": {
    "haiku_low": {"personality": "dispatch", "effort": "low"},
    "haiku_high": {"personality": "engineer", "effort": "high"},
    "sonnet_high": {"personality": "architect", "effort": "high"},
    "opus46_high": {"personality": "sage", "effort": "high"},
    "opus47_max": {"personality": "guardian", "effort": "max"}
  }
}
```

---

## Evolution Roadmap

**v1 (Current):** Voice personalities, handoff protocol, skill roadmap defined.  
**v2:** Better TTS voices, more nuanced personalities, personality-specific skills.  
**v3:** Agent persistence (memory, preference learning), cross-session continuity.  
**v4:** Fully autonomous day (no human intervention except crisis), self-optimizing cost targets.

---

## FAQ

**Q: What if Orchestrator doesn't know how to route a task?**  
A: Escalate to Opus 4.7 (Guardian) for classification + recommendation. Then delegate to appropriate specialist.

**Q: Can I override the routing decision?**  
A: Yes. Say "use Sonnet" or "use Haiku Engineer" — Orchestrator will comply and log the override.

**Q: How do I know if a handoff was successful?**  
A: Monitor voice-notify personality switch (e.g., "Dispatch → Architect"), then check output matches expected effort level.

**Q: Can two agents work in parallel?**  
A: Yes, if they're working different repos or non-overlapping files. Orchestrator coordinates; voice-notify alerts on milestones.

**Q: Should I modify AGENTS.md or ORCHESTRATION.md?**  
A: AGENTS.md = decision matrices, effort levels. ORCHESTRATION.md = roles, voices, handoff protocol. Both evolve together quarterly.

---

## Update Log

- **2026-04-19:** Initial ORCHESTRATION.md established as foundation for Dark Factory Agentic Engineering.
- **Quarterly Reviews:** Every 3 months, assess cost targets, personality effectiveness, skill gaps.
