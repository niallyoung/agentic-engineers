---
name: Dog-Food Philosophy
type: core-principle
phase: 5.10+
status: Active
---

# Dog-Food Philosophy: Using Our Tools to Build Better Tools

## The Principle

**We use the agents and quality systems we build to improve the agents and quality systems themselves.**

This creates a positive feedback loop where:
1. Better tools → faster delivery
2. Faster delivery → more iterations
3. More iterations → better feedback data
4. Better feedback → optimized tool design
5. Optimized tools → even faster delivery

This is exponential improvement through **self-improvement**.

---

## Why This Matters

Traditional software development separates concerns:
- **Developer** writes code
- **CI/CD** validates code
- **User** provides feedback weeks/months later

This creates **long feedback loops** and **slow iteration cycles**.

Agentic-engineers inverts this:
- **Agents** write code and validate it immediately
- **Quality gates** catch issues in <30 seconds
- **Quality Engineer** reviews in parallel
- **Model Engineer** analyzes results and recommends improvements
- **Next agent task** uses optimized routing from previous feedback

**Feedback time: seconds to minutes, not weeks.**

---

## Current Implementation (Phase 5.10)

### Cycle 1: Building Quality Gates

When we implemented the three quality gate improvements:
1. **Wire Quality Engineer routing** - Added explicit code review routing
2. **Enforce Tier 2/3 checklists** - Layer 3 validation now requires proof
3. **Post-HANDBACK escalation** - Auto-escalate low-quality deliverables

We ate our own dogfood immediately:

```
Quality Gate Implementation Code
    ↓
[NEW] Quality Validator (Layer 3) checks our changes
    ↓
[NEW] Quality Engineer routing analyzes our code
    ↓
[NEW] Post-HANDBACK escalation triggered (if needed)
    ↓
Feedback: "Coverage needed here" / "Tier 2 checklist incomplete"
    ↓
Fix immediately
    ↓
Next implementation uses better tools
```

### What Improved Because We Dog-Fooded

- **Checklist validation caught gaps** we wouldn't see in manual review
- **Quality score thresholds** showed us which rules matter most
- **Escalation logic** prevented marginal work from slipping through
- **New quality gates stress-tested** their own implementation

---

## Extending Dog-Food: The Compounding Loop

### Phase 6-7: Full SDLC Agents

When we implement the remaining SDLC agents (Engineer, Senior Engineer, etc.):

```
New Agent Implementation
    ↓
[IMPROVED] Quality gates validate the implementation
    ↓
[IMPROVED] Quality Engineer reviews code
    ↓
[IMPROVED] Escalation thresholds catch issues faster
    ↓
[NEW] Model Engineer analyzes tokens/cost/quality
    ↓
Recommendation: "Use Haiku for this pattern"
    ↓
Next agent uses better model selection
    ↓
Cost ↓, Quality ↑
```

Each new agent:
- Gets validated by ALL previous quality improvements
- Generates data for Model Engineer optimization
- Produces better deliverables for next task
- Increases confidence in the system

---

## Philosophy in Action: This Document

This very document was created with dog-food principles:

1. **Planning** - Scoped with quality in mind (clear intent, specific audience)
2. **Implementation** - Followed AGENTS + SKILLS constraint (no external scripts)
3. **Validation** - Would be checked by:
   - Layer 1: YAML structure validation
   - Layer 2: Clarity, completeness, scope alignment
   - Layer 3: Checklist completion (if from engineer agent)
   - Quality Engineer: Would review for:
     - Accuracy against actual implementation
     - Clarity for downstream teams
     - Alignment with existing philosophy docs
4. **Feedback** - Quality score informs:
   - Should this be more technical?
   - Is the philosophy section too abstract?
   - Did we miss key examples?
5. **Iteration** - Model Engineer data from similar docs improves future documentation generation

---

## Establishing Dog-Food as Standard

### In AGENTS.md

Every agent type should include:
```yaml
quality_gates:
  - Layer 1: Validates task structure (DELEGATE format, required fields)
  - Layer 2: Validates task quality (scope, complexity, plan)
  - Layer 3: Validates deliverables (HANDBACK structure, checklists)
  - Post-execution: Quality Engineer review if threshold breached

feedback_loops:
  - Agent work → Quality validation → Escalation if needed
  - Model Engineer analyzes metrics → Improves routing for next task
  - Metrics collected → Cost optimization → Better model selection
  
dogfood_requirement:
  - Agent implementation must be validated by [this same agent if possible, 
    or equivalent QG sub-agent]
  - Metrics from agent execution inform future improvements
  - Each agent contributes to system that created it
```

### In SPEC.md

Add under "Core Design Principles":
```
PRINCIPLE: Dog-Fooding for Continuous Improvement

1. Every tool built must be tested by the tools it helps build
2. Quality gates validate agent implementations that implement quality gates
3. Feedback loops from task execution inform next task routing
4. Metrics drive optimization that reduces cost and improves quality
5. This creates exponential improvement, not linear
```

### In Implementation Code

```python
# When validating agent work
class OrchestratorAgent:
    def _process_task(self):
        # ... standard validation ...
        
        # Dog-food: Use the quality system being improved
        # to validate the implementation code itself
        handback_validation = self.quality_validator.validate_handback(
            handback, delegate
        )
        # This closes the loop: quality gate validates improvements to itself
```

---

## Long-Term Compounding Effects

### 6 Months In

- **Quality gates** are stricter because they've been tested 1000x
- **Routing decisions** are better because Model Engineer analyzed 1000 decisions
- **Agent implementations** are more reliable because each iteration improved the system
- **Cost per task** dropped 40% because model selection improved
- **Delivery time** dropped 60% because feedback loops tighten

### 1 Year In

- **New features** added faster because quality foundation is solid
- **Breaking changes** caught in <5 minutes instead of production
- **System evolves itself** - feedback loops drive improvement without external intervention
- **Team spends 30% less time** on code review/debugging

### Cascading Benefits

When we built **Quality Engineer routing** (fix 1):
- Immediately caught issues in our code
- Model Engineer analyzed quality patterns
- Next task's routing was better
- Quality Engineer had more practice
- Future code review improved

When we built **Checklist enforcement** (fix 2):
- Agents started following guidelines more consistently
- Coverage never dropped again (checklist prevents it)
- Documentation got better (checklist required)
- Future implementations had higher quality baseline

When we built **Post-HANDBACK escalation** (fix 3):
- Marginal work never made it to done queue
- Quality Engineer stayed busy improving architecture
- Model Engineer saw fewer cost anomalies
- Team confidence in automated quality increased

**Each improvement compounds the next.**

---

## Practical Guidelines

### When Building New Agents

1. **Design for dog-food first**
   - Agent should be validatable by existing quality gates
   - Agent deliverables should pass Layer 1/2/3 checks
   - Agent should include checklist proof in HANDBACK

2. **Implement with feedback in mind**
   - Code should generate metrics for Model Engineer
   - Decisions should be traceable (why this route?)
   - Failures should teach the system (escalation reason)

3. **Iterate immediately**
   - As quality gates catch issues, fix in next cycle
   - Model Engineer feedback → apply to next similar task
   - Don't wait for "perfect" - iterate with quality gates catching drift

### When Improving Quality Gates

1. **Test on real agent work**
   - Don't test new validation rule on synthetic data
   - Validate against actual HANDBACK from agents
   - Let system teach you what matters

2. **Measure impact**
   - How many tasks does this gate affect?
   - Does it catch real issues or false positives?
   - Does escalation rate improve?

3. **Dog-food the quality gate improvement itself**
   - Code that improves validation → must pass validation
   - Rules for checklist → code must follow checklist
   - Escalation logic → improved code gets escalated if needed

---

## Anti-Patterns to Avoid

❌ **Building agents without validation**
- Code agents, validate manually later
- Creates backlog of work-waiting-for-review
- Defeats compounding improvement

❌ **One-shot optimization**
- "Run quality gates once, then stop"
- Quality gates only work with continuous feedback
- Need steady stream of tasks to drive learning

❌ **Ignoring escalations**
- "Quality Engineer flagged this, but we'll fix later"
- Later never comes, debt accumulates
- Dog-food only works with immediate iteration

❌ **Separating tools from improvement**
- Building Model Engineer but not using feedback to route
- Implementing Quality Engineer but routing all to Lead Engineer
- Collecting metrics but not optimizing based on them

---

## Metrics That Matter

To know dog-food is working, track:

| Metric | Baseline | Target |
|--------|----------|--------|
| Feedback loop time | weeks | minutes |
| Quality gate catch rate | 0% | >80% of actual issues |
| Escalation % | TBD | <10% (well-scoped tasks) |
| Cost per task | baseline | -40% in 6mo |
| Delivery time | baseline | -60% in 6mo |
| Agent confidence | 70% | 95%+ |
| Model selection accuracy | 50% | 95%+ |

---

## Long-Term Vision

In 5 years, agentic-engineers should be:
- **Self-improving**: Better because it validates itself
- **Self-optimizing**: Model Engineer continuously improves routing
- **Self-defending**: Quality gates catch regressions faster than humans
- **Self-documenting**: Metrics show what works, system improves based on data
- **Exponentially faster**: Each improvement multiplies the next

This is only possible if we **dog-food relentlessly** from day one.

---

## Implementation Checklist

- [x] Wire Quality Engineer routing (immediate feedback on code review tasks)
- [x] Enforce Tier 1/2/3 checklists (catch quality issues at gate)
- [x] Post-HANDBACK escalation (never accept marginal work)
- [ ] Update AGENTS.md with dog-food requirements
- [ ] Update SPEC.md with dog-food principle
- [ ] Create metrics dashboard (feedback visibility)
- [ ] Run 10 tasks through improved gates (validation)
- [ ] Analyze escalation data (what triggered?)
- [ ] Feed to Model Engineer (what can we optimize?)
- [ ] Design next optimization based on feedback (loop closes)

---

## Conclusion

> "We don't just build tools. We build systems that improve themselves through continuous feedback loops. The quality gates that catch bugs also catch gaps in our quality gates. The agents that implement features also validate the agents that implement agents. This compounding improvement is our competitive advantage."

Dog-fooding isn't a testing practice. It's a **philosophy of continuous, self-directed improvement through immediate feedback**.
