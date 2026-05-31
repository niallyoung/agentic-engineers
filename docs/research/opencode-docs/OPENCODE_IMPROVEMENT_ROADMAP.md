# OPENCODE IMPROVEMENT ROADMAP

**Created**: May 28, 2026  
**Scope**: Safe enhancements to OpenCode render without affecting Copilot/Claude/Pi  
**Risk Level**: ZERO (all changes additive, no deletions or breaking changes)

---

## PHASED ROADMAP

### PHASE 1: CRITICAL FOUNDATIONS (1-2 days)

Deploy essential permission boundaries and documentation fixes.

#### 1.1 Add Per-Agent Permission Boundaries

**Problem Statement**: All agents currently have unrestricted access to all tools. This violates least-privilege principle and allows Engineer to (theoretically) push code or modify SPEC.md.

**Why It Matters**:
- SPEC.md is protocol source-of-truth; accidental modifications corrupt agentic-engineers
- Engineer shouldn't have git push capability (violates routing protocol)
- Security Engineer should have exclusive write access to security/ directory
- Documents constraints at tool level, making violations obvious

**How It Helps agentic-engineers**:
- Enforces SPEC.md immutability (only Principal Engineer or git hooks can modify)
- Enforces protocol (Engineer can't bypass routing)
- Self-documents role boundaries

**Implementation Approach**:
1. Edit `~/.config/opencode/opencode.jsonc`
2. Add per-agent `permission` overrides for Orchestrator, Engineer, Security Engineer, Principal Engineer
3. Test with mock tasks to verify permissions trigger

**Risk Assessment**: 
- Breaking changes: ZERO
- Functionality impact: ZERO (makes existing constraints explicit)
- Copilot/Claude/Pi render: NO IMPACT (they use different harness config)

**Effort Estimate**: **Haiku-tier** (30 min - 1 hour config work, 30 min testing)

**Owner**: Engineer

**Config Changes**:
```jsonc
// ~/.config/opencode/opencode.jsonc additions

"agent": {
  "engineer": {
    "permission": {
      "bash": {
        "*": "ask",
        "git status *": "allow",
        "git diff *": "allow",
        "npm test": "allow",
        "npm run verify": "allow",
        "grep *": "allow",
        "git push *": "deny",          // No direct pushes
        "git commit *": "ask",         // Ask before commits (Orchestrator does final push)
        "rm -rf *": "deny",            // No destructive commands
        "make install": "allow"
      },
      "edit": {
        "*": "ask",
        "src/**": "allow",            // Implementation code
        "tests/**": "allow",          // Test code
        "docs/guidelines/**": "allow",
        "SPEC.md": "deny",            // Protocol untouchable
        ".githooks/**": "deny",       // Git hooks protected
        "AGENTS.md": "deny"           // Global rules protected
      }
    }
  },
  
  "security-engineer": {
    "permission": {
      "edit": {
        "security/**": "allow",       // Exclusive write access to security
        "**": "deny"                  // Read-only elsewhere (enforced via read permission)
      },
      "bash": {
        "*": "ask",
        "grep *": "allow",
        "git status *": "allow"
      }
    }
  },
  
  "principal-engineer": {
    // Keep full access for highest-authority role
    // (or make it explicit if we want restricted principal)
  },
  
  "orchestrator": {
    // Keep full access (Orchestrator must manage queue, create DELEGATEs)
  }
}

// Global permission override (applies to all agents unless overridden)
"permission": {
  "read": "allow",
  "edit": "allow",
  "bash": "allow",
  "task": "allow",
  "glob": "allow",
  "grep": "allow",
  "webfetch": "allow",
  // Add protection for critical files
  "external_directory": {
    "~/.agentic-engineers/**": "allow"  // Allow queue access
  }
}
```

**Success Criteria**:
- ✅ Engineer cannot edit SPEC.md (denied)
- ✅ Engineer cannot push code (denied)
- ✅ Engineer can still edit src/ (allowed)
- ✅ Security Engineer can edit security/ (allowed)
- ✅ Orchestrator still has full access
- ✅ No errors in opencode.jsonc validation

---

#### 1.2 Protect SPEC.md from Accidental Modification

**Problem Statement**: SPEC.md is the protocol source-of-truth. Any agent (including bugs in model behavior) could theoretically edit it.

**Why It Matters**:
- Protocol spec changes should go through approval process (spec-management skill)
- Accidental modification could corrupt agentic-engineers behavior across all harnesses
- Single point of truth needs protection

**How It Helps agentic-engineers**:
- Prevents accidental drift from SPEC.md baseline
- Forces intentional spec changes through governance process
- Documented constraint makes violation obvious to observers

**Implementation Approach**:
1. Add `"SPEC.md": "deny"` to Engineer/Senior/Lead/Model Engineer `edit` permission
2. Keep Principal Engineer unrestricted (they approve spec changes)
3. Document that spec changes require Principal Engineer + Pull Request

**Risk Assessment**: 
- Breaking changes: ZERO
- Functionality impact: ZERO (spec shouldn't be edited via OpenCode anyway)

**Effort Estimate**: **Haiku-tier** (10 min config, 10 min testing)

**Owner**: Engineer

**Config Changes**: (included in 1.1 above)

---

#### 1.3 Add Secure Defaults to Global Permission Block

**Problem Statement**: No global protection against common dangerous patterns (rm -rf, dropping databases, etc.).

**Why It Matters**:
- Prevents accidental catastrophic failures
- Documents intended constraints
- Provides audit trail

**Implementation Approach**:
1. Add dangerous pattern denials to global `permission.bash`
2. Whitelist safe patterns per role

**Risk Assessment**: ZERO (makes explicit what should already be prevented by code review)

**Effort Estimate**: **Haiku-tier** (20 min)

**Owner**: Engineer

**Config Changes**:
```jsonc
"permission": {
  "bash": {
    "*": "ask",                    // Default: ask before any bash
    "git status *": "allow",       // Safe reads
    "npm test": "allow",           // Tests
    "make verify": "allow",        // Verification
    "rm -rf *": "deny",            // NEVER allow recursive delete
    "git push *": "ask",           // Ask before any push (Orchestrator decides)
    "> /dev/null": "deny"          // Suspicious pattern
  }
}
```

---

### PHASE 2: PRINCIPLE ALIGNMENT (3-5 days)

Enhance configuration to better reflect agentic-engineers values.

#### 2.1 Add Per-Role AGENTS.md Guidance Files

**Problem Statement**: Single global AGENTS.md documents system-level constraints. No per-role guidance for specific responsibilities and conventions.

**Why It Matters**:
- Reinforces role boundaries without config changes
- Enables role-specific behavior customization
- Follows OpenCode's multi-AGENTS.md precedence model
- Easier to maintain (role changes don't require central config edit)

**How It Helps agentic-engineers**:
- Engineer guidance separate from Principal guidance
- Role-specific escalation patterns documented
- Each agent can have task-type examples

**Implementation Approach**:
1. Create `~/.config/opencode/agents/engineer/AGENTS.md` with Engineer-specific rules
2. Create similar files for other key roles
3. Each file documents role-specific expectations, not system rules

**Risk Assessment**: ZERO (additive documentation)

**Effort Estimate**: **Haiku-tier** (1 hour per role file, total 3-4 hours for 5 key roles)

**Owner**: Engineer

**Example Content** (engineer/AGENTS.md):
```markdown
# Engineer — Role-Specific Guidelines

## Your Responsibilities
1. Execute well-scoped tasks with pre-written plans
2. Follow the plan step-by-step; escalate blockers
3. Validate against success criteria before returning HANDBACK
4. Report accurate token metrics for Model Engineer optimization

## When to Escalate
- Plan is vague or missing
- Scope exceeds 3000 tokens
- Multiple domains involved (hint: delegate to Senior Engineer first)
- Architecture questions arise
- Security implications exist (ask Security Engineer)

## Task Acceptance
You ACCEPT tasks with:
- ✅ Step-by-step plan provided
- ✅ Success criteria defined
- ✅ Scope bounded (<3000 tokens)
- ✅ Files and line numbers referenced

You ESCALATE tasks without:
- ❌ No plan provided
- ❌ Vague scope ("refactor everything")
- ❌ Cross-service implications
- ❌ Architectural decisions

## Example Workflow
1. Receive DELEGATE from Orchestrator or Senior Engineer
2. Validate plan completeness (not your job to design, only implement)
3. Execute plan step by step
4. Run verification: `make verify`
5. Return HANDBACK with metrics
6. Await next task

## Common Patterns
- Feature: scope + plan from Orchestrator ✓
- Bug fix: scope + plan from Senior Engineer ✓
- Refactor: ESCALATE (needs design phase first) ✗
```

---

#### 2.2 Expand Command Library

**Problem Statement**: Only 3 commands defined in global opencode.jsonc. Common workflows require long prompts.

**Why It Matters**:
- Makes workflows discoverable (`/help` shows available commands)
- Reduces friction (type `/review` vs. long prompt)
- Documents intended use cases
- Faster context switches between roles

**How It Helps agentic-engineers**:
- `/delegate-engineer` quickly sets up Engineer task template
- `/metrics` shows token usage by role (Model Engineer data)
- `/check-protocol` validates DELEGATE/HANDBACK compliance

**Implementation Approach**:
1. Add 8-10 commands to `opencode.jsonc` under `command` section
2. Each command has template with pre-filled prompt structure
3. Route to appropriate agent (e.g., `/metrics` → model-engineer)

**Risk Assessment**: ZERO (optional, doesn't change core functionality)

**Effort Estimate**: **Haiku-tier** (1.5 hours config + 1 hour testing)

**Owner**: Engineer

**New Commands**:
```jsonc
"command": {
  "delegate-engineer": {
    "description": "Create a new Engineer DELEGATE with template",
    "agent": "orchestrator",
    "template": "Create a DELEGATE for Engineer with scope: {ARGUMENTS}. Include plan and success criteria."
  },
  "delegate-senior": {
    "description": "Escalate to Senior Engineer with design phase",
    "agent": "orchestrator",
    "template": "Route to Senior Engineer: {ARGUMENTS}. Need design/planning phase first."
  },
  "review": {
    "description": "Start a Quality Engineer review session",
    "agent": "quality-engineer",
    "template": "Review the following code/design: {ARGUMENTS}. Check for protocol compliance, edge cases, quality issues."
  },
  "metrics": {
    "description": "Show token usage and efficiency metrics by role",
    "agent": "model-engineer",
    "template": "Analyze metrics from the last 24 hours. Show token spend by role, efficiency scores, and recommendations for optimization."
  },
  "check-protocol": {
    "description": "Validate DELEGATE/HANDBACK protocol compliance",
    "agent": "orchestrator",
    "template": "Scan all DELEGATEs and HANDBACKs in the queue. Validate schema compliance, check for missing fields, detect protocol violations."
  },
  "queue-status": {
    "description": "Show pending tasks and their status",
    "agent": "orchestrator",
    "template": "List all pending DELEGATEs and HANDBACKs. Show age, assigned role, status, and any blockers."
  },
  "test-all": {
    "description": "Run full test suite with coverage",
    "agent": "engineer",
    "template": "Run `make verify` to execute full test suite including coverage. Report pass/fail and coverage percentage."
  },
  "security-audit": {
    "description": "Perform a security audit on codebase",
    "agent": "security-engineer",
    "template": "Audit the codebase for: injection vulnerabilities, auth/authz flaws, data exposure, dependency vulnerabilities. Prioritize by severity."
  }
}
```

---

#### 2.3 Enable Extended Thinking for Opus Agents

**Problem Statement**: Principal Engineer and Security Engineer use Opus, but extended thinking (reasoning) not configured.

**Why It Matters**:
- Opus can allocate tokens to reasoning/thinking
- Better for complex decisions (architecture, security)
- Improves quality for high-stakes decisions

**How It Helps agentic-engineers**:
- Principal Engineer gets better architectural decisions
- Security Engineer gets more thorough vulnerability analysis
- Cost-justified for high-stakes decisions

**Implementation Approach**:
1. Add `thinking` configuration to Opus model options
2. Budget 8000 tokens for thinking (reasonable balance)
3. Test with Principal/Security tasks to verify

**Risk Assessment**: 
- Token cost: +8k per Opus call (justified for Principal)
- Breaking changes: ZERO

**Effort Estimate**: **Haiku-tier** (30 min config, 1 hour testing)

**Owner**: Engineer

**Config Changes**:
```jsonc
"provider": {
  "github-copilot": {
    "models": {
      "claude-opus-4-6": {
        "options": {
          "thinking": {
            "type": "enabled",
            "budgetTokens": 8000
          }
        }
      },
      "claude-opus-4-7": {
        "options": {
          "thinking": {
            "type": "enabled",
            "budgetTokens": 8000
          }
        }
      }
    }
  }
}
```

---

#### 2.4 Add External Instruction Files

**Problem Statement**: AGENTS.md documents constraints, but doesn't reference external docs (CONTRIBUTING.md, design guidelines, etc.).

**Why It Matters**:
- Centralizes guidance without cluttering AGENTS.md
- Can share instructions across repos (via git submodule or symlink)
- Follows OpenCode's `instructions` field pattern

**Implementation Approach**:
1. Add `instructions` field to global opencode.jsonc
2. Reference key docs (SPEC.md excerpt, CONTRIBUTING.md, design guidelines)
3. OpenCode loads them into context automatically

**Risk Assessment**: ZERO (optional, improves context only)

**Effort Estimate**: **Haiku-tier** (30 min config)

**Owner**: Engineer

**Config Changes**:
```jsonc
{
  "instructions": [
    "AGENTS.md",                    // Global rules (already configured)
    "docs/CONTRIBUTING.md",         // Development workflow
    "SPEC.md",                      // Protocol specification
    ".githooks/README.md"           // Git hook documentation
  ]
}
```

---

### PHASE 3: FEATURE ENHANCEMENT (1-2 weeks)

Advanced integration and tooling.

#### 3.1 Configure MCP Servers (GitHub Integration)

**Problem Statement**: No MCP servers configured. Missing opportunity for IDE integration and GitHub context awareness.

**Why It Matters**:
- Enables queue visibility in VS Code extension
- PR context could inform code review decisions
- Future-proofs for external tool integration
- Shows "best practices" to users building MCP integrations

**How It Helps agentic-engineers**:
- Engineer can see PR review requirements when implementing
- Quality Engineer can access PR discussion context
- IDE dashboards can show queue status

**Implementation Approach**:
1. Add GitHub MCP server (disabled by default, to avoid token bloat)
2. Document how to enable it
3. Document use cases (PR review context, issue linking)

**Risk Assessment**: 
- Token cost: Disabled by default (ZERO impact if off)
- Breaking changes: ZERO
- Functionality: Additive only

**Effort Estimate**: **Sonnet-tier** (2-3 hours: 1 hour config, 2 hours testing + doc)

**Owner**: Senior Engineer

**Config Changes**:
```jsonc
"mcp": {
  "github": {
    "type": "remote",
    "url": "https://mcp.github.com/",
    "enabled": false,              // Disabled by default (token cost)
    "oauth": true,
    "timeout": 10000
  }
}
```

**Documentation**:
```markdown
### Enable GitHub MCP for PR Context

To enable GitHub integration:

1. `opencode mcp auth github` (one-time OAuth flow)
2. Edit `~/.config/opencode/opencode.jsonc`: set `github.enabled: true`
3. Use in prompts: `@review-pr` or `Show PR context for this code`

Use cases:
- Code review: See PR requirements before implementing
- Quality Engineer: Access PR discussion for context
- Engineer: Link implementation to GitHub issues
```

---

#### 3.2 Create MCP Server for Queue Operations

**Problem Statement**: Queue operations (list, create DELEGATE, query status) not exposed to external tools.

**Why It Matters**:
- IDE extension could query queue status
- Web dashboard could show queue visualization
- External tooling (GitHub Actions, Slack) could push tasks
- Enables ecosystem around agentic-engineers

**Implementation Approach**:
1. Create `~/.agentic-engineers/mcp/queue-server.js` (Node.js MCP)
2. Implement tools: `queue_list()`, `delegate_create()`, `handback_get()`, `queue_stats()`
3. Register in opencode.jsonc as local MCP

**Risk Assessment**: 
- Breaking changes: ZERO
- Functionality: Additive
- Security: Requires authentication (token-based)

**Effort Estimate**: **Sonnet-tier** (4-6 hours: 3 hours dev, 2-3 hours testing + doc)

**Owner**: Senior Engineer

**MCP Server Tools**:
```javascript
// ~/.agentic-engineers/mcp/queue-server.js

tools: {
  queue_list: {
    description: "List pending DELEGATEs and HANDBACKs",
    inputSchema: {
      type: "object",
      properties: {
        status: { type: "string", enum: ["pending", "processing", "done"] }
      }
    }
  },
  delegate_create: {
    description: "Create a new DELEGATE",
    inputSchema: {
      type: "object",
      properties: {
        role: { type: "string" },
        task_id: { type: "string" },
        scope: { type: "string" },
        plan: { type: "array" }
      }
    }
  },
  queue_stats: {
    description: "Get queue statistics (pending count, avg age, by role)"
  }
}
```

---

#### 3.3 Define Model Variants (Thinking Modes)

**Problem Statement**: No way to easily switch between fast/deep reasoning modes for same model.

**Why It Matters**:
- Enables experiments: fast mode (1h estimate) vs. deep mode (thorough analysis)
- Cost exploration: cheap vs. expensive reasoning
- Quality trade-off testing

**Implementation Approach**:
1. Define `variants` for Opus and Sonnet models
2. "deep-thinking" variant: full reasoning budget
3. "quick" variant: no reasoning (fast)
4. Agent can cycle via `variant_cycle` keybind

**Risk Assessment**: ZERO (optional experimentation tool)

**Effort Estimate**: **Haiku-tier** (1 hour config + testing)

**Owner**: Engineer

**Config Changes**:
```jsonc
"provider": {
  "github-copilot": {
    "models": {
      "claude-opus-4-6": {
        "variants": {
          "deep-thinking": {
            "thinking": {
              "type": "enabled",
              "budgetTokens": 16000
            }
          },
          "quick": {
            "thinking": {
              "type": "disabled"
            }
          }
        }
      }
    }
  }
}
```

---

#### 3.4 Create OpenCode Plugin for Protocol Validation

**Problem Statement**: No automated validation of DELEGATE/HANDBACK schema at write-time.

**Why It Matters**:
- Prevents malformed protocol files from entering queue
- Provides immediate feedback to user
- Enforces schema at entry point

**Implementation Approach**:
1. Create OpenCode plugin with `tool.execute` hooks
2. Before write: validate protocol schema
3. After write: log to audit trail

**Risk Assessment**: 
- Breaking changes: ZERO
- Functionality: Additive validation only

**Effort Estimate**: **Opus-tier** (8-12 hours: 5 hours plugin dev, 4 hours testing + doc)

**Owner**: Principal Engineer

**Plugin Hook**:
```javascript
// ~/.config/opencode/plugins/protocol-validator.js

tool.execute.before = (input) => {
  if ((input.filePath?.includes('DELEGATE') || input.filePath?.includes('HANDBACK')) 
      && input.tool === 'write') {
    
    // Parse YAML frontmatter
    const match = input.content.match(/^---\n([\s\S]*?)\n---/);
    if (!match) {
      throw new Error("DELEGATE/HANDBACK must have YAML frontmatter");
    }
    
    const data = YAML.parse(match[1]);
    
    // Validate required fields
    const required = ['handoff_type', 'task_id', 'timestamp', 'status'];
    for (const field of required) {
      if (!data[field]) {
        throw new Error(`Missing required field: ${field}`);
      }
    }
    
    // Validate handoff_type
    if (!['DELEGATE', 'HANDBACK'].includes(data.handoff_type)) {
      throw new Error(`Invalid handoff_type: ${data.handoff_type}`);
    }
    
    console.log(`✓ Protocol validated: ${data.handoff_type} (${data.task_id})`);
  }
};
```

---

#### 3.5 Create Custom Tools for Queue Operations

**Problem Statement**: Queue operations available via bash only. Could be cleaner via custom tools.

**Why It Matters**:
- Cleaner integration than bash scripts
- Discoverable via `/help`
- Better error handling and structured output
- Agents can call queue tools programmatically

**Implementation Approach**:
1. Define custom tools or MCP endpoints
2. Wrap common queue operations
3. Add to opencode.jsonc

**Risk Assessment**: ZERO (optional, improves UX only)

**Effort Estimate**: **Sonnet-tier** (3-4 hours)

**Owner**: Senior Engineer

---

## IMPLEMENTATION TIMELINE

```
Week 1:
  Day 1-2: Phase 1 (permissions, SPEC.md protection)
           - 1.1: Per-agent permissions (Haiku, 1 hour)
           - 1.2: SPEC.md protection (Haiku, 20 min)
           - 1.3: Dangerous pattern denials (Haiku, 20 min)
           Total: ~2 hours + testing

Week 1-2:
  Day 3-5: Phase 2 (alignment improvements)
           - 2.1: Per-role AGENTS.md (Haiku, 3-4 hours)
           - 2.2: Commands expansion (Haiku, 2.5 hours)
           - 2.3: Extended thinking (Haiku, 1.5 hours)
           - 2.4: External instructions (Haiku, 30 min)
           Total: ~8 hours + testing

Week 2-3:
  Day 6-10: Phase 3 (feature enhancement)
            - 3.1: GitHub MCP (Sonnet, 3 hours)
            - 3.2: Queue MCP (Sonnet, 5 hours)
            - 3.3: Model variants (Haiku, 1 hour)
            - 3.4: Protocol validation plugin (Opus, 10 hours)
            - 3.5: Queue custom tools (Sonnet, 3 hours)
            Total: ~22 hours + testing
```

**Total effort**: ~32-35 hours across 3-4 weeks

**Recommended pace**:
1. Complete Phase 1 this week (CRITICAL — unblocks other work)
2. Complete Phase 2 next week (ALIGNMENT — strengthens principles)
3. Phase 3 as opportunity allows (NICE-TO-HAVE — ecosystem)

---

## SAFETY & ROLLBACK

**All changes are additive** (no deletions, no breaking changes):
- Adding permissions restricts access but doesn't change existing functionality
- New commands don't remove old workflows
- MCP servers are optional
- Plugins don't affect existing behavior

**Rollback procedure** (if needed):
1. Revert `~/.config/opencode/opencode.jsonc` to previous version
2. Remove any newly created plugin files
3. Restart OpenCode

**No impact on**:
- Copilot harness (`dist/copilot/`)
- Claude harness (`dist/claude/`)
- Pi harness (`dist/pi/`)
- SPEC.md
- Core DELEGATE/HANDBACK protocol
- Existing workflow

---

## SUCCESS CRITERIA

**Phase 1 Success**:
- ✅ Engineer cannot edit SPEC.md
- ✅ Engineer cannot push code
- ✅ Security Engineer can edit security/ only
- ✅ No workflow regressions

**Phase 2 Success**:
- ✅ Per-role guidance files created (5 roles)
- ✅ 8+ new commands added and tested
- ✅ Extended thinking configured for Opus
- ✅ External instructions loaded without errors

**Phase 3 Success**:
- ✅ GitHub MCP optional and disabled by default
- ✅ Queue MCP tools functional (queue_list, etc.)
- ✅ Model variants switchable via keybind
- ✅ Protocol validation prevents malformed files
- ✅ Queue custom tools available

---

## OWNERS & ASSIGNMENTS

| Phase | Owner | Estimated Hours |
|-------|-------|-----------------|
| 1 | Engineer | 2 |
| 2 | Engineer + Senior Engineer | 8 |
| 3 | Senior Engineer + Principal Engineer | 22 |

**Total team capacity needed**: ~32-35 hours

**Recommended split**:
- Week 1: Engineer does Phase 1 (2 hours)
- Week 1-2: Engineer does Phase 2.1-2.3 (5 hours), Senior does 2.4 (30 min)
- Week 2-3: Senior Engineer leads Phase 3 with Principal Engineer on 3.4

---

## QUESTIONS FOR TEAM

1. **Permission model**: Should we restrict Engineer further (e.g., bash: deny entirely)?
2. **MCP strategy**: GitHub MCP enabled by default or opt-in?
3. **Plugin validation**: Required for this sprint or future?
4. **Variants**: Should we experiment with fast/deep thinking modes?
5. **Custom tools**: Priority or defer to later phase?

---

## REFERENCES

- OpenCode Config: https://opencode.ai/config.json
- OpenCode Permissions: https://opencode.ai/docs/permissions/
- OpenCode Agents: https://opencode.ai/docs/agents/
- OpenCode MCP: https://opencode.ai/docs/mcp-servers/
- OpenCode Plugin Hooks: https://opencode.ai/docs/plugins/
- SPEC.md: docs/SPEC.md (local)
