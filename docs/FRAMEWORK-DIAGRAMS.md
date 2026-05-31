---
title: "agentic-engineers: Framework Architecture & Niche"
---

# Architecture Overview

```mermaid
graph TB
    subgraph User["👤 User Workflows"]
        WF["Your Multi-Agent Orchestration<br/>(Write Once, Deploy Everywhere)"]
    end
    
    subgraph Core["🎯 agentic-engineers Core"]
        PROTO["DELEGATE/HANDBACK<br/>Protocol"]
        AGENT["Agent Registry<br/>(Model + Role)"]
        SKILLS["Skills Catalog"]
        ORCH["Orchestrator<br/>(Route + Parallelize)"]
        COST["Cost & Metrics"]
        SEC["Security & Audit"]
    end
    
    subgraph Adapters["🔌 Harness Adapters<br/>(Render Layer)"]
        OC["OpenCode<br/>Adapter"]
        CC["Claude Code<br/>Adapter"]
        COP["Copilot CLI<br/>Adapter"]
        PI["π.dev<br/>Adapter"]
        OL["Ollama<br/>Adapter"]
    end
    
    subgraph Harnesses["🏭 Harness Platforms"]
        OCN["Anthropic<br/>OpenCode"]
        CCN["VS Code +<br/>Claude"]
        COPN["GitHub<br/>Copilot"]
        PIN["π.dev<br/>Platform"]
        OLN["Ollama<br/>Runtime"]
    end
    
    WF --> Core
    Core --> Adapters
    OC --> OCN
    CC --> CCN
    COP --> COPN
    PI --> PIN
    OL --> OLN
    
    classDef user fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef core fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef adapter fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef harness fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    
    class User user
    class Core core
    class Adapters adapter
    class Harnesses harness
```

# Problem: Vendor Lock-In

```mermaid
graph LR
    subgraph Problem["❌ TODAY"]
        WF1["Your Workflow"]
        WF1 -->|Different code<br/>for each harness| OC1["OpenCode"]
        WF1 -->|Different code<br/>for each harness| CC1["Claude Code"]
        WF1 -->|Different code<br/>for each harness| COP1["Copilot"]
        OC1 -.->|Harness changes?<br/>Rewrite everything| Problem2["🔓 LOCK-IN"]
    end
    
    subgraph Solution["✅ WITH FRAMEWORK"]
        WF2["Your Workflow<br/>(Write Once)"]
        FW["agentic-engineers<br/>(Universal)"]
        WF2 --> FW
        FW -->|Native<br/>OpenCode| OC2["OpenCode"]
        FW -->|Native<br/>Claude| CC2["Claude Code"]
        FW -->|Native<br/>Copilot| COP2["Copilot"]
        FW -.->|Harness improves?<br/>Adapters update| Solution2["✅ PORTABLE"]
    end
    
    classDef bad fill:#ffebee,stroke:#c62828,stroke-width:2px
    classDef good fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef locked fill:#c62828,color:#fff,stroke-width:2px
    classDef portable fill:#1b5e20,color:#fff,stroke-width:2px
    
    class Problem bad
    class Solution good
    class Problem2 locked
    class Solution2 portable
```

# Harness Integration Philosophy

```mermaid
graph TD
    A["Understand Harness<br/>Native Features"] -->|OpenCode: parallelism<br/>Claude Code: skills<br/>Copilot: CLI| B["Build Adapters<br/>That Leverage Strengths"]
    B -->|Don't emulate<br/>Elevate!| C["Maintain Minimal<br/>Compatibility Layer"]
    C -->|Only what's needed<br/>for portability| D["When Harness Improves<br/>Reduce Our Code"]
    D -->|Anthropic adds multi-agent<br/>→ We use theirs| E["Framework Absorbs<br/>Vendor Shock"]
    E -->|Users continue unchanged<br/>Adapters update| F["✅ Success:<br/>Framework Obsolete"]
    
    classDef step fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef success fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    
    class A,B,C,D,E step
    class F success
```

# Evolution Example: Multi-Agent Workflows

```mermaid
timeline
    title Multi-Agent Workflows Adoption
    
    section Week 1
        MAY 2026: Anthropic launches multi-agent workflows
        agentic-engineers: Still implements own orchestration
        Status: 2,000 lines of code (Framework manages agents)
    
    section Week 2-3
        EARLY JUNE: Framework detects native support available
        Update: Delegate to Anthropic's multi-agent API
        Status: 200 lines of code (Framework coordinates only)
        Result: 90% code reduction!
    
    section Late JUNE
        USER EXPERIENCE: Completely unchanged
        Behind scenes: Framework leverages vendor feature
        Benefit: Faster performance, better support
        Outcome: Users auto-benefit from Anthropic improvements
```

# Framework Code Size Over Time

```mermaid
xychart-beta
    title "agentic-engineers Code Size (LOC) - Aspirational Trajectory"
    x-axis [2026, 2027, 2028, 2029, 2030]
    y-axis "Code Size (LOC)" 500 --> 3500
    line [2500, 2800, 2200, 1500, 1200] title "agentic-engineers"
    line [500, 600, 700, 800, 900] title "Harness Adapters (minimal)"
    line [500, 400, 300, 200, 100] title "Vendor Gap-Filling"
```

**Goal**: By 2028, framework is 90% smaller, mostly documentation & examples

# Success = Obsolescence

```mermaid
graph TD
    A["Framework Fills Vendor Gaps<br/>(2026)"] -->|Vendors see demand| B["Vendors Implement Features<br/>(2027)"]
    B -->|Framework code shrinks| C["Framework Becomes Thin Layer<br/>(2028)"]
    C -->|Learnings persist| D["✅ Mission Accomplished<br/>Framework Mostly Obsolete"]
    E["Open Source Knowledge<br/>Patterns + Architecture"] -->|Lives on in| F["Community Projects<br/>Vendor Products<br/>Research"]
    D -->|Creates| E
    
    classDef phase1 fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef phase2 fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef phase3 fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef legacy fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    
    class A phase1
    class B phase2
    class C phase3
    class D,F phase3
    class E legacy
```

# Multi-Harness Strategy (Q2 2026)

```mermaid
xychart-beta
    title "Harness Capability Matrix - Framework Fill"
    x-axis [Multi-Agent, Cost Control, Portability, Security]
    y-axis "Harness Maturity" 0 --> 100
    line [40, 80, 100, 85] title "OpenCode"
    line [30, 50, 70, 90] title "Claude Code"
    line [70, 30, 60, 70] title "Copilot CLI"
    line [50, 40, 50, 50] title "π.dev"
    line [0, 100, 90, 85] title "Framework Contribution"
```

# Value Proposition: The Three Circles

```mermaid
graph TB
    subgraph Users["👥 USERS<br/>(What you get)"]
        U1["Write Once,<br/>Run Everywhere"]
        U2["Hedge Vendor Bets<br/>(Easy migration)"]
        U3["Auto-benefit from<br/>Vendor Improvements"]
    end
    
    subgraph Community["🌐 COMMUNITY<br/>(What you learn)"]
        C1["Multi-Agent<br/>Patterns"]
        C2["Vendor Requirements<br/>(How to evaluate)"]
        C3["Anti-Lock-In<br/>Strategies"]
    end
    
    subgraph Vendors["🏢 VENDORS<br/>(What you build)"]
        V1["Reference<br/>Architecture"]
        V2["See What's<br/>Important"]
        V3["Competitive<br/>Advantage"]
    end
    
    classDef user fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef comm fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef vendor fill:#fff3e0,stroke:#e65100,stroke-width:2px
    
    class Users user
    class Community comm
    class Vendors vendor
```

# Call to Action

```mermaid
graph LR
    FW["agentic-engineers<br/>Framework"]
    
    FW -->|⭐ Star| GH["GitHub<br/>Repo"]
    FW -->|💬 Share| FB["Feedback &<br/>Use Cases"]
    FW -->|📝 Contribute| CODE["Code,<br/>Docs,<br/>Adapters"]
    FW -->|💜 Support| DONATE["Donate<br/>Patreon/<br/>Sponsors"]
    
    GH -->|Signals| IMPACT["Impact:<br/>Community<br/>Knows<br/>This<br/>Matters"]
    FB -->|Informs| ROADMAP["Roadmap:<br/>What<br/>Vendors<br/>Should<br/>Build"]
    CODE -->|Extends| ECOSYSTEM["Ecosystem:<br/>More<br/>Adapters<br/>More<br/>Harnesses"]
    DONATE -->|Enables| SUSTAIN["Sustain:<br/>Keep<br/>Building<br/>Learning<br/>Sharing"]
    
    IMPACT -->|Virtuous<br/>Cycle| SUSTAIN
    ROADMAP -->|Virtuous<br/>Cycle| SUSTAIN
    ECOSYSTEM -->|Virtuous<br/>Cycle| SUSTAIN
    
    classDef action fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    classDef outcome fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    
    class GH,FB,CODE,DONATE action
    class IMPACT,ROADMAP,ECOSYSTEM,SUSTAIN outcome
```
