# Deprecated Skills Index

**Last Updated:** 2026-06-25  
**Total Deprecated Skills:** 4  
**Archive Location:** `docs/archive/deprecated-skills/`

## Overview

This document indexes all deprecated skills in the agentic-engineers framework. Deprecated skills have been archived due to:
- **Low maintenance priority** — Minimal test coverage, few implementation details
- **Functional overlap** — Better served by alternative skills or native tools
- **User concerns** — Design issues (e.g., unsupervised repo modification)
- **Underutilization** — No evidence of active adoption

Each deprecated skill has:
- **Original code archived** in `docs/archive/deprecated-skills/{skill-name}/`
- **RESTORE.md** with restoration instructions and alternatives
- **Deprecation rationale** explaining why it was deprecated
- **Alternatives section** recommending what to use instead

## Deprecated Skills Summary

| Skill | Deprecated | Category | Reason | Archive | Status |
|-------|-----------|----------|--------|---------|--------|
| **repo-init** | 2026-05-30 | orchestration | Already disabled; user concerns about unsupervised repo modification | ✓ | See [RESTORE.md](archive/deprecated-skills/repo-init/RESTORE.md) |
| **skill-creator** | 2026-05-30 | automation | Subsumed by agent-creator; better integration with framework | ✓ | See [RESTORE.md](archive/deprecated-skills/skill-creator/RESTORE.md) |
| **harness-opencode-feature-sync** | 2026-05-30 | integration | OpenCode integration no longer needed; use native OpenCode features | ✓ | See [RESTORE.md](archive/deprecated-skills/harness-opencode-feature-sync/RESTORE.md) |
| **tokenadvisor** | 2026-05-30 | metrics | Overlap with usage-tracking + model-engineer; better to separate concerns | ✓ | See [RESTORE.md](archive/deprecated-skills/tokenadvisor/RESTORE.md) |

## Detailed Deprecation Rationale

### repo-init [DISABLED]

**Status:** Already disabled with explicit user concern  
**Reason:** Unsupervised repository modification is risky; needs explicit approval mechanism  
**When Deprecated:** 2026-05-30  
**Last Active:** Unknown (check git history)  
**Test Coverage:** 0%

**Why Deprecated:**
- Already marked as `disabled: true` in SKILL.md due to user concerns
- Modifies user repositories without clear approval process
- Heavy dependencies (agent-creator, spec-management) increase failure risk
- No test coverage to validate 8-phase bootstrap process
- Scope creep risk with automated repo structure generation

**Alternative Approach:**
- Use `agent-creator` skill for individual agent scaffolding
- Use manual setup following `docs/ONBOARDING.md` workflow
- Gives users full control over what gets modified

**How to Use Instead:**
1. Read `docs/ONBOARDING.md` for manual bootstrap steps
2. Use `agent-creator` for each agent needing scaffolding
3. Manually create structure as needed with full visibility

**When to Restore:** Only if team frequently bootstraps new repos AND adds comprehensive safety mechanisms (dry-run mode, explicit approval, rollback capability).

---

### tokenadvisor [LOW PRIORITY]

**Status:** Active but low maintenance  
**Reason:** usage-tracking + model-engineer provide same capability with better separation of concerns  
**When Deprecated:** 2026-05-30  
**Test Coverage:** 0%

**Why Deprecated:**
- Minimal implementation (1-2 scripts) for complex analysis requirements
- `usage-tracking` provides data collection and forecasting
- `model-engineer` provides analysis and optimization recommendations
- Combining two specialized skills is clearer than one umbrella skill
- No evidence of active daily adoption

**What usage-tracking Provides (Data Layer):**
- Real-time and historical metrics collection
- Analysis by agent, role, task type
- Cost calculation per task
- Forecasting (weekly, monthly projections)
- Anomaly detection

**What model-engineer Provides (Analysis Layer):**
- Analyzes quality/cost tradeoffs
- Identifies inefficient routings
- Recommends model/effort optimizations
- Confidence scoring
- Ranked recommendations (rank_1, rank_2, rank_3)

**Alternative Approach (Recommended):**
1. Use `usage-tracking` for collecting and analyzing metrics
2. Use `model-engineer` for generating optimization recommendations
3. Combine outputs for comprehensive reports
4. Separate concerns: data collection vs. analysis

**Daily Report Workflow (Without tokenadvisor):**
```
1. Orchestrator runs usage-tracking
   → Aggregates metrics by role
   → Identifies cost anomalies
   → Exports to JSON/CSV

2. Orchestrator runs model-engineer
   → Analyzes QE feedback
   → Identifies inefficiencies
   → Generates recommendations

3. Manual consolidation
   → Create daily report from both outputs
   → Share with team
```

**When to Restore:** Only if you want a unified daily report that combines metrics + recommendations in a single skill.

---

## Recommended Alternatives

| Deprecated Skill | Use This Instead | Why | Docs |
|------------------|------------------|-----|------|
| repo-init | agent-creator + manual setup | Manual control, safer | [agent-creator](../SKILLS-AVAILABLE.md) |
| skill-creator | agent-creator | Better integration with framework | [agent-creator](../SKILLS-AVAILABLE.md) |
| harness-opencode-feature-sync | Native OpenCode features | Simpler, no custom sync needed | OpenCode documentation |
| tokenadvisor | usage-tracking + model-engineer | Better separation of concerns | Both skills in SKILLS-AVAILABLE.md |

## Quality Gates for Re-Enabling

Before re-enabling any deprecated skill, it must meet these criteria:

1. **Test Coverage:** ≥90% code coverage with ≥10 tests per major feature
2. **Documentation:** Updated SKILL.md, RESTORE.md, and examples in docs/
3. **Integration:** Clear integration with DELEGATE/HANDBACK protocol
4. **Metrics:** Evidence of value or planned adoption
5. **Safety:** If skill modifies user artifacts, explicit approval mechanism required

## Archive Structure

```
docs/archive/deprecated-skills/
├── repo-init/
│   ├── SKILL.md (original skill definition)
│   ├── scripts/ (original implementation)
│   ├── tests/ (original tests, if any)
│   └── RESTORE.md (restoration guide)
├── skill-creator/
│   ├── SKILL.md
│   ├── scripts/
│   └── RESTORE.md
├── harness-opencode-feature-sync/
│   ├── SKILL.md
│   ├── scripts/
│   └── RESTORE.md
└── tokenadvisor/
    ├── SKILL.md
    ├── scripts/
    └── RESTORE.md
```

Each skill's archive directory contains:
- **SKILL.md** — Original skill definition with metadata
- **scripts/** — All implementation files
- **tests/** — Any existing tests (if applicable)
- **RESTORE.md** — Complete restoration guide with:
  - Git commands to restore from archive or history
  - Steps to re-enable with safety improvements
  - Comprehensive test suite requirements
  - When/if to restore decision matrix

## How to Access Deprecated Skills

### For Historical Reference

```bash
# View original SKILL.md
cat docs/archive/deprecated-skills/repo-init/SKILL.md

# View implementation
ls docs/archive/deprecated-skills/repo-init/scripts/

# View restoration guide
cat docs/archive/deprecated-skills/repo-init/RESTORE.md
```

### To Restore a Skill

**Option A: Restore from archive (fast, in this repo)**
```bash
cp -r docs/archive/deprecated-skills/repo-init ~/.claude/skills/repo-init
# Then follow RESTORE.md steps to re-enable
```

**Option B: Restore from git history (complete, with history)**
```bash
git log --oneline --all -- .claude/skills/repo-init | head -5
git show <commit_hash>:.claude/skills/repo-init > /tmp/backup.tar
tar -xf /tmp/backup.tar ~/.claude/skills/repo-init
```

## Migration Path for Users

If you were using a deprecated skill:

### From repo-init
```bash
# Old approach (deprecated)
# repo-init would bootstrap entire repo

# New approach
# 1. Use agent-creator for individual agents
agent-creator --scaffold my-agent

# 2. Manually create structure as needed
# See docs/ONBOARDING.md for full walkthrough
```

### From tokenadvisor
```bash
# Old approach (deprecated)
# tokenadvisor would provide daily optimization report

# New approach
# 1. Use usage-tracking for metrics: opencode-tokens --session <id>
# 2. Use model-engineer for recommendations: generates automatically
# 3. Combine in daily report manually
```

## Questions?

- **How do I restore a deprecated skill?** See RESTORE.md for each skill
- **When should I use the alternatives?** Check the "Alternatives & Migration Paths" section in each RESTORE.md
- **What if I still need a deprecated skill?** Restore from archive and follow re-enabling steps; add test coverage
- **Can I suggest a skill for deprecation?** File an issue with deprecation rationale and alternatives

## See Also

- [SKILLS-AVAILABLE.md](SKILLS-AVAILABLE.md) — All active skills
- [SKILL-CREATOR.md](SKILL-CREATOR.md) — How to create new skills
