# Agentic-Engineers Framework: Architecture & Philosophy

## Core Vision

**agentic-engineers** is a minimal, portable orchestration layer for multi-agent AI workflows that aims to become *unnecessary* as vendors improve their native capabilities.

### The Paradox of Success
Our success metrics are inverse:
- **High engagement** = Framework useful in gap-filling current limitations
- **Framework obsolescence** = All limitations fixed by vendors → framework disappears into provider features
- **Knowledge transfer** = Community learns patterns, applies them elsewhere

---

## Problem We're Solving

### The Harness Lock-In Problem

```
TODAY'S REALITY (2026):
┌─────────────────────────────────────────────────────────┐
│  Your Multi-Agent Orchestration Workflow                │
│  (Delegation, parallelism, security boundaries, etc.)   │
└─────────────────────────────────────────────────────────┘
           ↓ Different for each harness ↓
    ┌──────────┬──────────┬──────────┬──────────┐
    │ OpenCode │  Claude  │ Copilot  │  π.dev   │
    │  Custom  │   Code   │   CLI    │          │
    │ Protocol │  Native  │ Bash CLI │ (future) │
    └──────────┴──────────┴──────────┴──────────┘
           ↓ Lock-in at workflow level ↓
    "If OpenCode changes, rewrite everything"
```

### agentic-engineers Solution

```
PORTABLE WORKFLOWS (2026+):
┌─────────────────────────────────────────────────────────┐
│  Your Multi-Agent Orchestration Workflow                │
│  (Written once, runs everywhere)                        │
└─────────────────────────────────────────────────────────┘
           ↓ Standardized abstraction ↓
    ┌──────────────────────────────────────────────────────┐
    │  agentic-engineers Framework                         │
    │  • Unified DELEGATE/HANDBACK protocol                │
    │  • Model-agnostic agent definitions                  │
    │  • Harness adapters (render to native code)          │
    │  • Cost & budget controls                            │
    │  • Security boundaries & audit trails                │
    └──────────────────────────────────────────────────────┘
           ↓ Renders to native harness APIs ↓
    ┌──────────┬──────────┬──────────┬──────────┐
    │ OpenCode │  Claude  │ Copilot  │  π.dev   │
    │ Native   │   Code   │ Command  │ (future) │
    │ API      │  Skills  │ Line     │ Native   │
    └──────────┴──────────┴──────────┴──────────┘
    ✅ Write once → deploy on any harness
    ✅ Vendor improvements auto-leveraged
    ✅ Easy to evaluate alternatives
```

---

## Framework Architecture

### Layered Design

```
┌──────────────────────────────────────────────────────────────────┐
│                    USER WORKFLOWS                                 │
│  (Your multi-agent orchestration, delegation patterns, logic)     │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│                  FRAMEWORK CORE (Universal)                      │
├──────────────────────────────────────────────────────────────────┤
│ • DELEGATE/HANDBACK Protocol (unified message format)            │
│ • Agent Registry (model + role + effort definitions)             │
│ • Skills Catalog (reusable automation functions)                 │
│ • Orchestrator (task routing, parallelism, escalation)           │
│ • Metrics & Audit (cost tracking, decision logs)                 │
│ • Security (boundaries, approval gates, compliance)              │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│             HARNESS ADAPTERS (Render Layer)                      │
├──────────────────────────────────────────────────────────────────┤
│ • OpenCode Adapter      → Native OpenCode API                    │
│ • Claude Code Adapter   → VS Code Extension Skills               │
│ • Copilot CLI Adapter   → Bash Command Execution                 │
│ • π.dev Adapter         → (Future) π.dev Native API              │
│ • Ollama Adapter        → Local LLM Runtime                       │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│              HARNESS PLATFORMS (Vendors)                         │
├──────────────────────────────────────────────────────────────────┤
│ Anthropic OpenCode | VS Code + Claude | GitHub Copilot | π.dev  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Harness Integration Philosophy

### Native-First Approach

```
Each harness has unique strengths. We DON'T force uniformity.
We ADAPT to native capabilities and improve over time.

┌─────────────────────────────────────────────────────────────────┐
│                    INTEGRATION PRINCIPLE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. UNDERSTAND HARNESS NATIVE FEATURES                          │
│     (OpenCode: native parallelism, Claude Code: skills, etc.)   │
│                                                                  │
│  2. BUILD ADAPTERS THAT LEVERAGE NATIVE STRENGTHS               │
│     (Don't emulate; elevate)                                    │
│                                                                  │
│  3. MAINTAIN MINIMAL COMPATIBILITY LAYER                        │
│     (Only what's needed for portability)                        │
│                                                                  │
│  4. WHEN HARNESS IMPROVES → REDUCE OUR CODE                     │
│     (Anthropic adds multi-agent workflows → we use theirs)      │
│                                                                  │
│  5. WHEN HARNESS CHANGES → FRAMEWORK ABSORBS SHOCK               │
│     (Users continue unchanged, adapters update)                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Example: Multi-Agent Workflows Evolution

```
WEEK 1: Anthropic launches multi-agent workflows
┌─────────────────────────────────────────────────────┐
│ OLD ADAPTER (May 2026)                              │
│ agentic-engineers {                                 │
│   • Manually serialize agents                       │
│   • Manage dependencies                             │
│   • Handle routing logic                            │
│   • Track state                                     │
│ }                                                   │
│ → 2,000 lines of code                               │
└─────────────────────────────────────────────────────┘

WEEK 2-3: Framework updates
┌─────────────────────────────────────────────────────┐
│ NEW ADAPTER (June 2026)                             │
│ agentic-engineers {                                 │
│   • Detect native multi-agent workflows available  │
│   • Delegate to Anthropic's implementation         │
│   • Keep our DELEGATE/HANDBACK as thin layer       │
│ }                                                   │
│ → 200 lines of code (90% reduction!)                │
└─────────────────────────────────────────────────────┘

RESULT: Users unaffected, framework code shrinks,
        vendor improvements auto-leveraged
```

---

## Framework Niche Over Time

### Success is Obsolescence

```
FRAMEWORK CODE SIZE OVER TIME (Aspirational)

    agentic-engineers
    Code Size (LOC)
         ↑
    3000 │     
         │    ╱╲       ← We add features as harnesses lag
    2500 │   ╱  ╲      
         │  ╱    ╲  
    2000 │ ╱      ╲    ╱╲
         │╱        ╲  ╱  ╲ ← Vendor improvements → we reduce code
    1500 │          ╲╱    ╲╱╲
         │                  ╱ ╲  ← Framework stabilizes
    1000 │                 ╱   ╲___
         │                ╱        
     500 │_______________╱ ← "happy path" (framework largely unneeded)
         │                          
         └──────────────────────────→ Time
         2026      2027      2028      2029+

    GOAL: By 2028, most code is either:
    - Core logic (DELEGATE/HANDBACK, agent defs)
    - Documentation & examples
    - Harness adapters (thin layers, vendor-maintained)
```

---

## Multi-Harness Strategy

### Current Portfolio (2026)

```
┌─────────────────────────────────────────────────────┐
│ HARNESS CAPABILITY MATRIX (Q2 2026)                 │
├─────────────┬──────────┬────────────┬──────────────┤
│ Harness     │ Maturity │ Multi-Agent│ Cost Control │
├─────────────┼──────────┼────────────┼──────────────┤
│ OpenCode    │ ✅ High  │ ⚠️ Beta    │ ✅ Yes       │
│ Claude Code │ ✅ High  │ ❌ No      │ ⚠️ Limited   │
│ Copilot CLI │ ⚠️ Beta  │ ✅ Growing │ ❌ No        │
│ π.dev       │ 🚀 New   │ 🤔 TBD     │ 🤔 TBD       │
│ Ollama      │ ✅ High  │ ❌ Single  │ ✅ Free      │
└─────────────┴──────────┴────────────┴──────────────┘

FRAMEWORK FILLS GAPS:
• Multi-agent: implemented in framework (pending vendor native support)
• Cost control: unified layer across all harnesses
• Portability: single workflow definition works everywhere
• Audit/Security: standardized across harnesses
```

---

## Value Proposition by Persona

### For Framework Users

```
✅ WRITE ONCE, RUN EVERYWHERE
   Your orchestration workflow is independent of harness choice

✅ HEDGE BETS ON VENDORS
   If OpenCode changes dramatically, migrate to Claude Code or Copilot
   (Weeks, not months of rewrite)

✅ EVALUATE NEW HARNESSES EASILY
   New provider launches? Test your workflows without rewriting

✅ LEVERAGE HARNESS IMPROVEMENTS AUTOMATICALLY
   When vendors improve (multi-agent, cost controls, etc.),
   framework adapters update → you benefit instantly

✅ STANDARDIZED COST & SECURITY
   Multi-provider cost tracking, unified security boundaries,
   audit trails across all harnesses
```

### For LLM Researchers & Educators

```
✅ LEARN MULTI-AGENT PATTERNS
   See concrete examples of:
   • Agent specialization (Haiku/Sonnet/Opus routing)
   • Delegation protocols (DELEGATE/HANDBACK)
   • Parallelism & escalation patterns
   • Security boundaries & audit trails

✅ EVALUATE HARNESS REQUIREMENTS
   Use this framework as a "requirements spec":
   - What should a good harness provide?
   - How do we reduce vendor lock-in?
   - What standardization would benefit everyone?

✅ CONTRIBUTE & LEARN
   Open source → contribute adapters for new harnesses,
   learn from other implementations, share patterns
```

### For AI Product Teams

```
✅ REFERENCE ARCHITECTURE
   How should multi-agent orchestration work?
   What are the key interfaces and patterns?
   Use agentic-engineers as a guide for your product

✅ COMPETITIVE ANALYSIS
   See what's important in harness evaluation
   (Cost controls, security, native multi-agent support, etc.)

✅ EARLY DETECTION OF GAPS
   Framework actively reveals vendor limitations
   → Opportunity to differentiate your product
```

---

## Learning Path & Evolution

### Phase 1: Gap-Filling (2026 - Current)

```
┌─────────────────────────────────────────────┐
│ AGENTIC-ENGINEERS ROLE: Bridge the Gaps    │
├─────────────────────────────────────────────┤
│ • Vendors don't have multi-agent workflows  │
│   → We implement orchestration              │
│ • Vendors don't have unified cost controls  │
│   → We implement budget enforcement         │
│ • Vendors have different security models    │
│   → We standardize audit trails             │
│ • Vendors don't port between harnesses      │
│   → We enable portability                   │
└─────────────────────────────────────────────┘
```

### Phase 2: Standardization (2027)

```
Framework influences vendor roadmaps:
• Anthropic implements native multi-agent workflows
• All providers add cost control APIs
• Security audit trails become standard
• Vendors consider DELEGATE/HANDBACK patterns
```

### Phase 3: Obsolescence (2028+)

```
Framework becomes thin adapter layer:
• Most logic → vendor native implementations
• agentic-engineers → coordination layer + examples
• Community continues for educational value
• Learnings applied to next-gen problems
```

---

## Educational & Community Impact

### How This Helps Beyond Direct Users

```
┌──────────────────────────────────────────────────────┐
│ KNOWLEDGE TRANSFER MODEL                             │
├──────────────────────────────────────────────────────┤
│                                                      │
│ 1. PATTERNS LIBRARY                                 │
│    → How to design multi-agent systems              │
│    → Security patterns (boundaries, audit)          │
│    → Cost optimization strategies                   │
│    → Parallelism & escalation logic                 │
│                                                      │
│ 2. VENDOR EVALUATION FRAMEWORK                       │
│    → What questions to ask new harnesses           │
│    → How to avoid lock-in                          │
│    → What capabilities matter                       │
│                                                      │
│ 3. OPEN SOURCE REFERENCE                            │
│    → Learn by reading real code                     │
│    → Contribute improvements                        │
│    → Fork & adapt for your use case                 │
│                                                      │
│ 4. RESEARCH PLATFORM                                │
│    → Study multi-agent orchestration                │
│    → Experiment with new patterns                   │
│    → Publish findings & learnings                   │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Sustainability & Support

```
Open source + educational mission means:
• No vendor lock-in of the framework itself
• Community contributions keep it alive
• Donations support maintenance & new research
• MIT/Apache license allows forking & adaptation
• Success = framework becomes unnecessary,
           learnings persist
```

---

## Quick Reference Diagram

### What is agentic-engineers?

```
                    PROBLEM
         ┌─────────────────────────────┐
         │ Vendor Lock-In              │
         │ • Each harness has own API  │
         │ • Workflows can't port      │
         │ • Coordination is manual    │
         │ • Cost is invisible         │
         └─────────────────────────────┘
                        ↓
                    SOLUTION
         ┌─────────────────────────────┐
         │ agentic-engineers           │
         │ • Portable workflows        │
         │ • Unified coordination      │
         │ • Built-in cost controls    │
         │ • Standards-based           │
         └─────────────────────────────┘
                        ↓
                 DEPLOYMENT
    ┌──────────────────┬──────────────────┐
    │ Native rendering │ Auto-adapting    │
    │ to each harness  │ to vendor        │
    │                  │ improvements     │
    └──────────────────┴──────────────────┘
                        ↓
                   SUCCESS METRICS
      • Framework shrinks as vendors improve ✅
      • Users unaffected by harness changes ✅
      • Community learns & applies patterns ✅
      • Vendor features improve faster ✅
      • Framework eventually obsolete ✅ (yay!)
```

---

## Call to Action

### For Users
- Deploy agentic-engineers workflows with confidence
- Switch harnesses without rewriting workflows
- Contribute feedback & improvements
- Learn multi-agent orchestration patterns

### For Vendors & Product Teams
- Use this framework to evaluate your product capabilities
- Contribute harness-specific adapters
- Help us fill gaps with your native features
- Consider standardization around DELEGATE/HANDBACK

### For Researchers & Educators
- Fork & extend for research
- Publish findings using agentic-engineers as platform
- Share new patterns & learnings
- Help build the standard everyone benefits from

### Support This Work
- ⭐ Star the repo (signals: this matters)
- 💬 Share feedback & use cases
- 📝 Contribute code, docs, or adapters
- 💜 Donate (Patreon, GitHub Sponsors, etc.) to support continued development
