# Standards Alignment Roadmap
**agentic-engineers Framework**

**Date:** 2025-05-09  
**Status:** EXECUTABLE IMPLEMENTATION PLAN  
**Version:** 1.0  

---

## Executive Summary

This roadmap details the **phase-by-phase implementation plan** to achieve 95%+ compliance with emerging agent standards while maintaining our unique architectural strengths.

**Timeline:** 5 phases over 8 months (Q2 2025 → Q4 2025)

**Target State:** 
- ✅ Full Linux Foundation AGENTS.md compliance
- ✅ Full GitHub Copilot standards compliance  
- ✅ 90%+ Claude Code standard compliance
- ✅ 85%+ CrewAI pattern compatibility
- ⚠️ 50%+ OpenAI/LangChain interoperability (intentional divergence)

**Success Metrics:**
- Automated compliance validation in CI/CD
- Zero compliance regressions
- Standards-aware documentation
- Cross-standard validation passing
- Quarterly standards review

---

## Phase 0: Current State Assessment (Completed ✅)

**Status:** DONE (2025-05-09)

**Deliverables:**
- [x] Standards research document (STANDARDS-ALIGNMENT.md)
- [x] Compliance matrix (STANDARDS-COMPLIANCE-MATRIX.md)
- [x] This roadmap
- [x] Identified 15 critical gaps
- [x] Created implementation backlog

**Current Scores:**
```
AGENTS.md:          100% ✅
Copilot:            100% ✅
Claude Code:         60% ⚠️
CrewAI:              70% ✅
OpenAI SDK:          40% ⚠️
LangChain:           30% ⚠️
─────────────────────────────
Overall:             65% ⚠️
```

---

## Phase 1: Claude Code Integration (Q2 2025 — May 16 to Jun 13)

**Priority:** ★★★★★ CRITICAL  
**Effort:** 2-3 days  
**Owner:** Principal Engineer + Senior Engineer  
**Dependencies:** None (Phase 0 complete)

### Goals
- Create formal agent registry in Claude Code format
- Enable Claude IDE to discover and load agents
- Add Claude-specific metadata
- Validate with Claude Code environment

### Tasks

#### Task 1.1: Create `/.claude/agents/` Structure
**Effort:** 2 hours  
**Acceptance Criteria:**
- [ ] Directory exists: `/.claude/agents/`
- [ ] 8 agent definition files created
- [ ] All files have proper YAML frontmatter
- [ ] All files reference corresponding `/src/agents/` specs

**Implementation:**

```bash
# Create directory
mkdir -p .claude/agents

# Create files for each agent
for agent in orchestrator engineer senior-engineer lead-engineer \
             principal-engineer quality-engineer security-engineer spec-engineer; do
  cp src/agents/${agent}.md .claude/agents/${agent}.md
done
```

**Files to Create:**
1. `/.claude/agents/orchestrator.md`
2. `/.claude/agents/engineer.md`
3. `/.claude/agents/senior-engineer.md`
4. `/.claude/agents/lead-engineer.md`
5. `/.claude/agents/principal-engineer.md`
6. `/.claude/agents/quality-engineer.md`
7. `/.claude/agents/security-engineer.md`
8. `/.claude/agents/spec-engineer.md`

#### Task 1.2: Add Claude-Specific Metadata
**Effort:** 4 hours  
**Acceptance Criteria:**
- [ ] Each agent has name, description, model fields
- [ ] tools array populated for each agent
- [ ] permissionMode specified (restricted/full)
- [ ] maxTurns set per agent complexity
- [ ] isolation level specified
- [ ] color assigned (unique per agent)
- [ ] Metadata validated against Claude schema

**Metadata Mapping:**

```markdown
---
name: Orchestrator
description: Routes engineering tasks to appropriate specialist agents
model: claude-haiku-4-5
tools: [bash, grep, view, task, read_agent, write_agent, list_agents]
permissionMode: full
maxTurns: 100
isolation: process
color: "#2563EB"  # Blue
---
```

**Color Scheme for Agents:**
| Agent | Color | Rationale |
|---|---|---|
| **Orchestrator** | #2563EB (Blue) | Command & control |
| **Engineer** | #10B981 (Green) | Implementation/building |
| **Senior Engineer** | #F59E0B (Amber) | Complex decisions |
| **Lead Engineer** | #8B5CF6 (Purple) | Leadership/review |
| **Principal Engineer** | #DC2626 (Red) | Strategic decisions |
| **Quality Engineer** | #0891B2 (Cyan) | Testing/validation |
| **Security Engineer** | #EA580C (Orange) | Security focus |
| **Spec Engineer** | #6366F1 (Indigo) | Specification |

#### Task 1.3: Update Permission Model
**Effort:** 2 hours  
**Acceptance Criteria:**
- [ ] `/.claude/settings.local.json` reviewed
- [ ] Permission model aligns with agent capabilities
- [ ] permissionMode field updated in each agent
- [ ] Documentation of permission levels created

**Permission Levels:**
```yaml
restricted:
  - Read operations only
  - bash: cat, grep, view, find
  - No write or execute

moderate:
  - Read + write operations
  - bash: cat, grep, view, find, edit, create
  - No git operations

full:
  - All operations including git
  - bash: all except force operations
  - edit, create, view, grep, bash
  - Require explicit approval for destructive ops
```

**Mapping Per Agent:**
| Agent | Permission Level | Rationale |
|---|---|---|
| Orchestrator | full | Needs queue management |
| Engineer | moderate | Coding & testing |
| Senior Engineer | moderate | Design & implementation |
| Lead Engineer | moderate | Code review |
| Principal Engineer | full | Strategic decisions |
| Quality Engineer | moderate | Testing only |
| Security Engineer | moderate | Audit, no execution |
| Spec Engineer | restricted | Read-only validation |

#### Task 1.4: Validate with Claude Code
**Effort:** 2 hours  
**Acceptance Criteria:**
- [ ] Claude Code IDE recognizes all agents
- [ ] Agent metadata displays correctly
- [ ] Tools are available per agent definition
- [ ] No validation errors in Claude environment
- [ ] Can switch between agents without error

**Validation Steps:**
```bash
# 1. Check YAML syntax
for file in .claude/agents/*.md; do
  head -20 "$file" | python3 -c "import sys, yaml; yaml.safe_load(sys.stdin)"
done

# 2. Verify required fields
for file in .claude/agents/*.md; do
  grep -E "^name:|^description:|^model:|^tools:|^permissionMode:" "$file" || exit 1
done

# 3. Check tool availability
grep -h "^tools:" .claude/agents/*.md | sort | uniq

# 4. Manual validation in Claude Code IDE
echo "Open Claude Code and verify agents load correctly"
```

#### Task 1.5: Documentation & Migration Guide
**Effort:** 1 hour  
**Acceptance Criteria:**
- [ ] CLAUDE-SETUP.md created
- [ ] Migration guide for existing users
- [ ] Backward compatibility maintained
- [ ] Known limitations documented

**Document Template:**
```markdown
# Claude Code Setup Guide

## Using agentic-engineers in Claude

### Automatic Discovery
All agents in `/.claude/agents/` are automatically discovered:

1. Open Claude Code
2. Navigate to agentic-engineers repo
3. Agents appear in "Available Agents" panel
4. Click to load desired agent

### Manual Agent Activation
If agents don't auto-discover:

1. Open Command Palette (Cmd+Shift+P)
2. Search "Load Custom Agents"
3. Select .claude/agents directory
4. Agents will load

### Known Limitations
- MCP servers not yet integrated
- Some skills require manual setup
- Queue operations require local artifacts/

### Troubleshooting
[...]
```

---

### Phase 1 Deliverables

| Deliverable | Owner | Status |
|---|---|---|
| `/.claude/agents/` directory | Engineer | Ready |
| 8 agent definition files | Engineer | Ready |
| Updated `settings.local.json` | Engineer | Ready |
| CLAUDE-SETUP.md guide | Principal Engineer | TBD |
| CI/CD validation added | Engineer | TBD |

### Phase 1 Acceptance Criteria

- [ ] All 8 agents in `/.claude/agents/` with proper metadata
- [ ] Claude Code IDE recognizes all agents
- [ ] No validation errors
- [ ] Documentation complete
- [ ] Backward compatibility maintained
- [ ] CI/CD validates structure

**Target Completion:** June 13, 2025  
**New Compliance Score:** 85% (up from 65%)

---

## Phase 2: MCP Server Integration (Q3 2025 — Jul 14 to Aug 11)

**Priority:** ★★★★☆ HIGH  
**Effort:** 1 week  
**Owner:** Senior Engineer + Model Engineer  
**Dependencies:** Phase 1 complete

### Goals
- Define MCP (Model Context Protocol) servers for skills
- Create `.mcp.json` configuration
- Enable agent ↔ skill communication
- Implement MCP wrappers for key skills

### Tasks

#### Task 2.1: Inventory Available Skills
**Effort:** 2 hours  
**Acceptance Criteria:**
- [ ] All skills identified in `/skills/` directory
- [ ] Capability per skill documented
- [ ] Tool requirements mapped
- [ ] MCP viability assessed

**Skills to Integrate:**
```
skills/
├── ab-testing/          → MCP: A/B test execution
├── metrics-etl/         → MCP: Metrics aggregation
├── model-engineer/      → MCP: Cost-quality analysis
├── skill-creator/       → MCP: Skill generation
├── tokenadvisor/        → MCP: Token optimization
├── usage-tracking/      → MCP: Usage monitoring
├── voice-notify/        → MCP: Audio notifications
└── customize-cloud-agent/ → MCP: Cloud agent setup
```

#### Task 2.2: Define `.mcp.json` Schema
**Effort:** 3 hours  
**Acceptance Criteria:**
- [ ] `.mcp.json` template created
- [ ] MCP server naming convention defined
- [ ] Tool-to-MCP mapping documented
- [ ] Environment variables specified
- [ ] Schema validation working

**`.mcp.json` Structure:**

```json
{
  "mcpServers": {
    "queue-management": {
      "command": "python",
      "args": ["-m", "mcp_servers.queue_management"],
      "env": {
        "QUEUE_PATH": "./artifacts/queue",
        "LOG_LEVEL": "INFO"
      },
      "disabled": false,
      "alwaysAllow": ["list_queue", "poll_queue"],
      "timeout": 30
    },
    "metrics-etl": {
      "command": "python", 
      "args": ["-m", "mcp_servers.metrics_etl"],
      "env": {
        "METRICS_DB": "./data/metrics.db",
        "AGGREGATION_INTERVAL": "3600"
      }
    },
    "tokenadvisor": {
      "command": "python",
      "args": ["-m", "mcp_servers.tokenadvisor"],
      "env": {
        "USAGE_LOG": "./data/token_usage.log"
      }
    },
    "usage-tracking": {
      "command": "python",
      "args": ["-m", "mcp_servers.usage_tracking"],
      "env": {
        "TRACKING_ENABLED": "true"
      }
    },
    "voice-notify": {
      "command": "bash",
      "args": ["scripts/mcp/voice_notify_server.sh"],
      "env": {
        "VOICE_ENABLED": "true"
      }
    },
    "ab-testing": {
      "command": "python",
      "args": ["-m", "mcp_servers.ab_testing"],
      "env": {
        "EXPERIMENT_DB": "./data/experiments.db"
      }
    }
  }
}
```

#### Task 2.3: Create MCP Server Wrappers
**Effort:** 5 days  
**Acceptance Criteria:**
- [ ] MCP wrapper for queue-management created
- [ ] MCP wrapper for metrics-etl created
- [ ] MCP wrapper for tokenadvisor created
- [ ] MCP wrapper for usage-tracking created
- [ ] All wrappers implement MCP protocol
- [ ] All wrappers tested in isolation

**MCP Server Template:**

```python
# mcp_servers/queue_management.py
import json
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("queue-management")

@server.call_tool()
async def list_queue(directory: str) -> list[str]:
    """List pending tasks in queue"""
    # Implementation
    return tasks

@server.call_tool()
async def poll_queue() -> dict:
    """Poll for next task"""
    # Implementation
    return next_task

@server.call_tool()
async def mark_done(task_id: str) -> bool:
    """Mark task as complete"""
    # Implementation
    return success

server.register_tools([
    Tool(name="list_queue", description="..."),
    Tool(name="poll_queue", description="..."),
    Tool(name="mark_done", description="..."),
])
```

#### Task 2.4: Implement MCP Tools in Agents
**Effort:** 3 hours  
**Acceptance Criteria:**
- [ ] Orchestrator can call MCP queue-management
- [ ] Engineer can call MCP metrics-etl
- [ ] Model Engineer can call MCP tokenadvisor
- [ ] All agents can call MCP voice-notify
- [ ] No breaking changes to existing code
- [ ] Fallback to direct calls if MCP unavailable

**Agent Integration Pattern:**

```python
# In agent handler
from mcp.client import ClientSession

async def route_task(task):
    async with ClientSession() as session:
        # Try MCP first
        try:
            queue_service = session.get("queue-management")
            task = await queue_service.list_queue()
        except MCPUnavailable:
            # Fallback to direct implementation
            task = direct_list_queue()
    
    return task
```

#### Task 2.5: MCP Documentation
**Effort:** 2 hours  
**Acceptance Criteria:**
- [ ] MCP server documentation created
- [ ] API reference for each server
- [ ] Integration examples provided
- [ ] Troubleshooting guide written

**Documentation Location:** `/docs/MCP-INTEGRATION.md`

---

### Phase 2 Deliverables

| Deliverable | Owner | Status |
|---|---|---|
| `.mcp.json` configuration | Senior Engineer | TBD |
| 6 MCP server wrappers | Senior Engineer | TBD |
| MCP integration guide | Principal Engineer | TBD |
| Agent MCP integration | Engineer | TBD |
| CI/CD MCP validation | Engineer | TBD |

### Phase 2 Acceptance Criteria

- [ ] `.mcp.json` defined and validated
- [ ] All 6 MCP servers implemented
- [ ] All agents can call MCP services
- [ ] Fallback handling working
- [ ] Documentation complete
- [ ] All tests passing

**Target Completion:** August 11, 2025  
**New Compliance Score:** 80% (up from 85%)

---

## Phase 3: CrewAI Pattern Bridge (Q3 2025 — Aug 12 to Aug 26)

**Priority:** ★★★☆☆ MEDIUM  
**Effort:** 1 week  
**Owner:** Senior Engineer  
**Dependencies:** Phase 1 complete

### Goals
- Create CrewAI-compatible agent definitions
- Implement task translation layer
- Enable dual-mode execution (agentic-engineers + CrewAI)
- Document compatibility patterns

### Tasks

#### Task 3.1: Analyze CrewAI Patterns
**Effort:** 1 day  
**Acceptance Criteria:**
- [ ] CrewAI Agent class analyzed
- [ ] CrewAI Task class analyzed
- [ ] CrewAI Crew orchestration understood
- [ ] Mapping to our agents identified
- [ ] Report: CrewAI-agentic-engineers mapping

**Key Mappings:**

| Our Concept | CrewAI Equivalent | Notes |
|---|---|---|
| Agent role | Agent.role | Direct mapping |
| Agent capabilities | Agent.tools | Different schema |
| Orchestrator | Manager in CrewAI 2.0 | Similar pattern |
| Task delegation | Task class | Similar pattern |
| HANDBACK metrics | Task output | Different format |

#### Task 3.2: Create CrewAI Adapter
**Effort:** 3 days  
**Acceptance Criteria:**
- [ ] Converter: AGENTS.md → CrewAI Agent
- [ ] Converter: DELEGATE → CrewAI Task
- [ ] Converter: HANDBACK → CrewAI output
- [ ] Adapter can load from agents-manifest.yaml
- [ ] All 8 agents have CrewAI equivalents
- [ ] Tool mappings working

**Adapter Implementation:**

```python
# adapters/crewai_adapter.py

from crewai import Agent, Task, Crew
from src.orchestration.agents_manifest import load_manifest

def agents_manifest_to_crewai():
    """Convert agents-manifest.yaml to CrewAI agents"""
    manifest = load_manifest()
    
    crewai_agents = []
    for agent_name, agent_config in manifest['agents'].items():
        crewai_agent = Agent(
            role=agent_config['role'],
            goal=agent_config['description'],
            backstory=generate_backstory(agent_config),
            tools=map_tools(agent_config['tools']),
            model=agent_config['model'],
            memory=True,
            verbose=True
        )
        crewai_agents.append(crewai_agent)
    
    return crewai_agents

def delegate_to_task(delegate):
    """Convert DELEGATE to CrewAI Task"""
    return Task(
        description=delegate['scope'],
        agent=find_agent(delegate['role']),
        expected_output=delegate['success_criteria'],
        tools=delegate.get('tools', [])
    )

def crew_from_manifest():
    """Create CrewAI Crew from manifest"""
    agents = agents_manifest_to_crewai()
    return Crew(
        agents=agents,
        process=Process.hierarchical,
        manager_agent=agents[0],  # Orchestrator
        verbose=True
    )
```

#### Task 3.3: Create Translation Layer
**Effort:** 2 days  
**Acceptance Criteria:**
- [ ] AGENTS.md → CrewAI Task translator
- [ ] DELEGATE format → CrewAI Task format
- [ ] HANDBACK → CrewAI output format
- [ ] All translations bidirectional
- [ ] No data loss in translation
- [ ] Tests passing

**Translation Workflow:**

```
agentic-engineers format
        ↓
    Adapter
        ↓
CrewAI format
        ↓
CrewAI.kickoff()
        ↓
CrewAI output
        ↓
    Reverse adapter
        ↓
HANDBACK format
        ↓
agentic-engineers queue
```

#### Task 3.4: Documentation
**Effort:** 1 day  
**Acceptance Criteria:**
- [ ] CrewAI bridge documentation created
- [ ] Usage examples provided
- [ ] Known limitations documented
- [ ] Troubleshooting guide included

**Documentation:** `/docs/CREWAI-BRIDGE.md`

---

### Phase 3 Deliverables

| Deliverable | Owner | Status |
|---|---|---|
| CrewAI analysis report | Senior Engineer | TBD |
| CrewAI adapter | Senior Engineer | TBD |
| Translation layer | Engineer | TBD |
| Test suite | Quality Engineer | TBD |
| Documentation | Principal Engineer | TBD |

### Phase 3 Acceptance Criteria

- [ ] All agents convertible to CrewAI
- [ ] Task translation working bidirectionally
- [ ] CrewAI Crew executes our tasks
- [ ] Output translates back to HANDBACK
- [ ] Documentation complete
- [ ] All tests passing

**Target Completion:** August 26, 2025  
**New Compliance Score:** 85% (CrewAI now at 85%+)

---

## Phase 4: Framework Bridges & Deprecations (Q4 2025 — Sep 27 to Oct 31)

**Priority:** ★★☆☆☆ LOW  
**Effort:** 1 week  
**Owner:** Senior Engineer  
**Dependencies:** Phases 1-3 complete

### Goals
- Create OpenAI/LangChain bridge documentation
- Explain intentional divergence
- Provide migration paths if needed
- Document long-term standards strategy

### Deliverables

1. **OpenAI-BRIDGE.md** — Why we use Claude, migration path if needed
2. **LANGCHAIN-INTEGRATION.md** — How to use agentic-engineers with LangChain
3. **STANDARDS-RATIONALE.md** — Strategic decisions explained
4. **ARCHITECTURE-DECISION-RECORD.md** — ADR for platform choices

---

## Phase 5: Continuous Validation (Ongoing — Monthly)

**Priority:** ★★★★★ CRITICAL  
**Effort:** 1-2 hours/month  
**Owner:** Quality Engineer + Principal Engineer

### Monthly Tasks

1. **Standards Compliance Check**
   - Run validation script
   - Track compliance drift
   - Update compliance matrix

2. **Framework Version Monitoring**
   - Check CrewAI releases
   - Monitor OpenAI Agents SDK
   - Track LangChain updates
   - Review Claude API changes

3. **Documentation Review**
   - Update for new features
   - Fix broken references
   - Refresh examples

4. **Validation Automation**
   - Add new validation rules
   - Update CI/CD checks
   - Improve error messages

---

## Timeline Summary

```
Q2 2025 (May 16 - Jun 13)
├── Phase 1: Claude Code Integration ← START HERE
└── Compliance: 65% → 85%

Q3 2025 (Jul 14 - Aug 26)
├── Phase 2: MCP Integration (Jul 14 - Aug 11)
│   └── Compliance: 85% → 80% (broader scope)
├── Phase 3: CrewAI Bridge (Aug 12 - Aug 26)
│   └── Compliance: 80% → 85%
└── Total effort: 2 weeks

Q4 2025 (Sep 27 - Oct 31)
├── Phase 4: Framework Bridges (Sep 27 - Oct 31)
│   └── Compliance: 85% → 90%
├── Phase 5: Continuous Validation (Ongoing)
│   └── Compliance: 90% → 95%+ (stabilize)
└── Total effort: 1 week + 1-2 hours/month

OVERALL TIMELINE: 5 phases, 4 weeks active work + ongoing maintenance
TARGET STATE: 95%+ compliance by Q4 2025
```

---

## Success Metrics & KPIs

### Technical Metrics

| Metric | Current | Target | Phase |
|---|---|---|---|
| AGENTS.md compliance | 100% | 100% | ✅ |
| Copilot compliance | 100% | 100% | ✅ |
| Claude Code compliance | 60% | 90% | Phase 1 |
| MCP server availability | 0% | 100% | Phase 2 |
| CrewAI bridge coverage | 0% | 85% | Phase 3 |
| OpenAI bridge docs | 0% | Available | Phase 4 |
| CI/CD validation rules | 3 | 15+ | Phases 1-4 |

### Process Metrics

| Metric | Target | Owner |
|---|---|---|
| Compliance drift detection | < 1 week | QE |
| Standards monitoring | Monthly | PE |
| Documentation update | Per release | PE |
| Validation automation | Continuous | QE |
| Cross-standard testing | Pre-commit | CI/CD |

### Quality Metrics

| Metric | Target | Phase |
|---|---|---|
| Test coverage (standards) | 95%+ | Phase 1 |
| Documentation completeness | 100% | Phase 1-4 |
| Breaking changes | 0 | All phases |
| Backward compatibility | 100% | All phases |

---

## Risk Mitigation

### Risk 1: Standards Churn
**Risk:** New standards emerge, existing ones change  
**Mitigation:** 
- Monthly standards review (Phase 5)
- Track 5 standards on watch list
- Built-in extension points

### Risk 2: Framework Incompatibility
**Risk:** CrewAI/OpenAI/LangChain introduce breaking changes  
**Mitigation:**
- Adapter pattern (allows version isolation)
- Vendored dependencies for critical paths
- Abstract interface layer

### Risk 3: Performance Degradation
**Risk:** MCP adds latency to agent coordination  
**Mitigation:**
- Direct call fallback
- Async/await throughout
- Benchmarking in Phase 2
- Caching strategies

### Risk 4: Scope Creep
**Risk:** Standards alignment work expands beyond phases  
**Mitigation:**
- Fixed scope per phase (documented above)
- Clear acceptance criteria
- Escalation to Principal Engineer if scope changes

---

## Dependencies & Prerequisites

### Before Phase 1
- [ ] STANDARDS-ALIGNMENT.md reviewed
- [ ] STANDARDS-COMPLIANCE-MATRIX.md approved
- [ ] Team understands requirements
- [ ] Budget allocated (20-30 hours)

### Before Phase 2
- [ ] Phase 1 complete and approved
- [ ] Claude Code agents working
- [ ] Senior Engineer available

### Before Phase 3
- [ ] Phase 2 complete
- [ ] MCP integration stable
- [ ] CrewAI environment available

### Before Phase 4
- [ ] Phases 1-3 complete
- [ ] 85%+ compliance achieved
- [ ] Documentation up-to-date

---

## Approval & Sign-Off

**Document Owner:** Principal Engineer  
**Approved By:** [Principal Engineer Sign-Off Required]  
**Status:** Ready for Phase 1 execution  
**Next Steps:** Assign Phase 1 tasks to engineers  

---

## Appendix: Detailed Task Breakdown

### Phase 1 Task Details

**Task 1.1 Resources:**
- Time: 2 hours
- Tools: bash, mkdir, cp
- No external dependencies

**Task 1.2 Resources:**
- Time: 4 hours
- Tools: text editor, YAML validator
- Reference: Claude documentation

**Task 1.3 Resources:**
- Time: 2 hours
- Tools: JSON editor
- Reference: permissions.json schema

**Task 1.4 Resources:**
- Time: 2 hours
- Manual testing in Claude Code IDE
- Reference: Claude documentation

**Task 1.5 Resources:**
- Time: 1 hour
- Tools: Markdown editor
- Reference: other setup guides

### Phase 2 Task Details

[Detailed task breakdown continues...]

---

**Document Version:** 1.0  
**Last Updated:** 2025-05-09  
**Next Phase Start:** May 16, 2025  
**Quarterly Review:** August 9, 2025
