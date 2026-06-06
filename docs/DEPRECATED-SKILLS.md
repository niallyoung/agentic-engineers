# Deprecated Skills Index

**Last Updated:** 2026-06-06  
**Total Deprecated Skills:** 6  
**Archive Location:** `docs/archive/deprecated-skills/`

## Overview

This document indexes all deprecated skills in the agentic-engineers framework. Deprecated skills have been archived due to:
- **Low maintenance priority** — Minimal test coverage, few implementation details
- **Functional overlap** — Better served by alternative skills or native tools
- **User concerns** — Design issues (e.g., unsupervised repo modification)
- **Underutilization** — No evidence of active adoption

Each deprecated skill has:
- **Original code archived** in `docs/archive/deprecated-skills/{skill-name}/`
- **RESTORATION.md** with restoration instructions and alternatives
- **Deprecation rationale** explaining why it was deprecated
- **Alternatives section** recommending what to use instead

## Deprecated Skills Summary

| Skill | Deprecated | Category | Reason | Archive | Status |
|-------|-----------|----------|--------|---------|--------|
| **repo-init** | 2026-05-30 | orchestration | Already disabled; user concerns about unsupervised repo modification | ✓ | See [RESTORATION.md](archive/deprecated-skills/repo-init/RESTORATION.md) |
| **cicd-monitor** | 2026-05-30 | monitoring | Overlap with GitHub Actions; consistency-checker provides protocol validation | ✓ | See [RESTORATION.md](archive/deprecated-skills/cicd-monitor/RESTORATION.md) |
| **ab-testing** | 2026-05-30 | optimization | Overlap with model-engineer; simple routing handles most cases | ✓ | See [RESTORATION.md](archive/deprecated-skills/ab-testing/RESTORATION.md) |
| **metrics-etl** | 2026-05-30 | metrics | Overlap with usage-tracking; Prometheus/Grafana not standard; CSV export sufficient | ✓ | See [RESTORATION.md](archive/deprecated-skills/metrics-etl/RESTORATION.md) |
| **tokenadvisor** | 2026-05-30 | metrics | Overlap with usage-tracking + model-engineer; better to separate concerns | ✓ | See [RESTORATION.md](archive/deprecated-skills/tokenadvisor/RESTORATION.md) |
| **voice-notify** | 2026-06-06 | notifications | Simplification; audio notifications no longer needed in framework | ✗ | Removed entirely; use system notifications or logging instead |

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
- Use `skill-creator` skill for individual skill scaffolding
- Manually combine them in `docs/ONBOARDING.md` workflow
- Gives users full control over what gets modified

**How to Use Instead:**
1. Read `docs/ONBOARDING.md` for manual bootstrap steps
2. Use `agent-creator` for each agent needing scaffolding
3. Use `skill-creator` for each skill
4. Commit changes manually with full visibility

**When to Restore:** Only if team frequently bootstraps new repos AND adds comprehensive safety mechanisms (dry-run mode, explicit approval, rollback capability).

---

### cicd-monitor [LOW PRIORITY]

**Status:** Active but low maintenance  
**Reason:** GitHub Actions provides native CI/CD monitoring; consistency-checker provides framework validation  
**When Deprecated:** 2026-05-30  
**Test Coverage:** 0%

**Why Deprecated:**
- Minimal implementation (1 script) despite complex 4-phase workflow
- GitHub Actions already provides workflow monitoring natively
- `consistency-checker` skill already validates DELEGATE/HANDBACK protocol post-push
- No clear value over using GitHub's built-in notifications
- No evidence of active usage in practice

**What GitHub Actions Provides (Built-In):**
- Workflow failure notifications (email, Slack, GitHub)
- Branch protection rules with required status checks
- Workflow status badges on README
- Detailed logs per run
- Artifact retention and retrieval
- All without needing a custom skill

**What consistency-checker Provides (Framework-Specific):**
- Validates DELEGATE/HANDBACK protocol compliance
- Detects cycles, rate limit violations, schema issues
- Runs via `make pre-push` hook
- Prevents protocol violations from entering the queue

**Alternative Approach:**
1. Use `.github/workflows/ci.yml` for CI pipeline
2. Use `.github/workflows/on_failure_notify.yml` for notifications
3. Use `consistency-checker` for protocol validation
4. Use branch protection rules for enforcement

**How to Use Instead:**
```bash
# CI runs via native GitHub Actions
.github/workflows/ci.yml

# Protocol validation via consistency-checker
make pre-push  # Runs automatically before git push
```

**When to Restore:** Only if custom CI orchestration is needed beyond GitHub Actions (e.g., custom escalation logic, specialized error categorization).

---

### ab-testing [LOW PRIORITY]

**Status:** Active but low maintenance  
**Reason:** Experimentation handled by model-engineer; simple routing sufficient for most cases  
**When Deprecated:** 2026-05-30  
**Test Coverage:** 0%

**Why Deprecated:**
- Minimal implementation (1 script) despite Welch's t-test and early stopping requirements
- `model-engineer` skill provides similar capability (analyzes metrics, recommends models)
- A/B testing of routes can be done via explicit routing rules in orchestrator
- Continuous automated A/B testing not standard practice (most teams do manual experiments)
- No evidence of active usage

**What model-engineer Provides (Better Approach):**
- Analyzes quality/cost feedback from QE
- Recommends optimal model/effort combinations with confidence scores
- Runs automatically after each task completion
- Integrates directly with DELEGATE/HANDBACK protocol
- Builds up recommendations over time (learning)

**Alternative Approach for A/B Testing:**
1. **Simple routing:** Use explicit rules in `.opencode/agent-router.yaml` to toggle models
2. **Manual experimentation:** Run same task with different models, compare results
3. **Model-engineer recommendations:** Let it suggest best model for task type
4. **GitHub Experiments:** Use if available; native integration with Actions

**How to Use Instead:**
```yaml
# Define routing rules in .opencode/agent-router.yaml
- condition: "task_type == 'complex_planning'"
  model_options:
    - model: claude-opus-4.8
      confidence: 0.95
    - model: claude-sonnet-4.6
      confidence: 0.80
```

**When to Restore:** Only if sophisticated continuous A/B testing is needed with automated statistical significance testing and early stopping across many model variants.

---

### metrics-etl [LOW PRIORITY]

**Status:** Active but low maintenance  
**Reason:** Simple CSV/JSON export sufficient; usage-tracking provides data collection; Grafana not standard deployment  
**When Deprecated:** 2026-05-30  
**Test Coverage:** 0%

**Why Deprecated:**
- Minimal implementation (1 script) for complex ETL pipeline
- `usage-tracking` skill already collects all necessary metrics
- Prometheus/Grafana setup is optional and deployment-specific
- Simple CSV or JSON export works for most teams
- No evidence of active usage with Grafana

**What usage-tracking Provides (Better Approach):**
- Real-time and historical token usage capture
- Analysis of metrics by agent, role, task type
- Forecasting capabilities
- Simple export to JSON/CSV
- Directly integrated with framework

**Alternative Approach for Metrics:**
1. **CSV Export:** Simple Python script (10 lines) to export metrics to CSV
2. **JSON Export:** Use `usage-tracking` skill with JSON output format
3. **Grafana (Optional):** If you have Grafana deployed, use custom Prometheus exporter
4. **GitHub Insights:** Use if all data is in GitHub Actions

**How to Use Instead:**
```bash
# Get metrics in JSON format
opencode-tokens --session <session-id> --format json > metrics.json

# Or export to CSV manually
python3 scripts/metrics_to_csv.py ~/.agentic-engineers/metrics/ > metrics.csv
```

**When to Restore:** Only if Grafana is already deployed as your standard metrics platform and you need complex time-series aggregation.

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

## Archive Structure

```
docs/archive/deprecated-skills/
├── repo-init/
│   ├── SKILL.md (original skill definition)
│   ├── scripts/ (original implementation)
│   ├── tests/ (original tests, if any)
│   └── RESTORATION.md (this file's equivalent)
├── cicd-monitor/
│   ├── SKILL.md
│   ├── scripts/
│   └── RESTORATION.md
├── ab-testing/
│   ├── SKILL.md
│   ├── scripts/
│   └── RESTORATION.md
├── metrics-etl/
│   ├── SKILL.md
│   ├── scripts/
│   └── RESTORATION.md
└── tokenadvisor/
    ├── SKILL.md
    ├── scripts/
    └── RESTORATION.md
```

Each skill's archive directory contains:
- **SKILL.md** — Original skill definition with metadata
- **scripts/** — All implementation files
- **tests/** — Any existing tests (if applicable)
- **RESTORATION.md** — Complete restoration guide with:
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
cat docs/archive/deprecated-skills/repo-init/RESTORATION.md
```

### To Restore a Skill

**Option A: Restore from archive (fast, in this repo)**
```bash
cp -r docs/archive/deprecated-skills/repo-init ~/.claude/skills/repo-init
# Then follow RESTORATION.md steps to re-enable
```

**Option B: Restore from git history (complete, with history)**
```bash
git log --oneline --all -- .claude/skills/repo-init | head -5
git show <commit_hash>:.claude/skills/repo-init > /tmp/backup.tar
tar -xf /tmp/backup.tar ~/.claude/skills/repo-init
```

## Recommended Alternatives

| Deprecated Skill | Use This Instead | Why | Docs |
|------------------|------------------|-----|------|
| repo-init | agent-creator + skill-creator | Manual control, safer | [agent-creator](../SKILLS-AVAILABLE.md) |
| cicd-monitor | GitHub Actions + consistency-checker | Native CI/CD, protocol validation | `.github/workflows/ci.yml` |
| ab-testing | model-engineer | Better integrated, automatic recommendations | [model-engineer](../SKILLS-AVAILABLE.md) |
| metrics-etl | usage-tracking | Simpler, already integrated | [usage-tracking](../SKILLS-AVAILABLE.md) |
| tokenadvisor | usage-tracking + model-engineer | Better separation of concerns | Both skills in SKILLS-AVAILABLE.md |

## Quality Gates for Re-Enabling

Before re-enabling any deprecated skill, it must meet these criteria:

1. **Test Coverage:** ≥90% code coverage with ≥10 tests per major feature
2. **Documentation:** Updated SKILL.md, RESTORATION.md, and examples in docs/
3. **Integration:** Clear integration with DELEGATE/HANDBACK protocol
4. **Metrics:** Evidence of value or planned adoption
5. **Safety:** If skill modifies user artifacts, explicit approval mechanism required

## Migration Path for Users

If you were using a deprecated skill:

### From repo-init
```bash
# Old approach (deprecated)
# repo-init would bootstrap entire repo

# New approach
# 1. Use agent-creator for each agent
agent-creator --scaffold my-agent

# 2. Use skill-creator for each skill
skill-creator --scaffold my-skill

# 3. Manually create structure as needed
# See docs/ONBOARDING.md for full walkthrough
```

### From cicd-monitor
```bash
# Old approach (deprecated)
# cicd-monitor would monitor and escalate CI failures

# New approach
# 1. Use GitHub Actions for CI/CD (native)
# 2. Use consistency-checker via pre-push hook
#    make pre-push (automatic validation)
# 3. Manual escalation via GitHub Issues if needed
```

### From ab-testing
```bash
# Old approach (deprecated)
# ab-testing would manage A/B tests across models

# New approach
# 1. Use model-engineer for recommendations
# 2. Update .opencode/agent-router.yaml with preferred model
# 3. Let model-engineer suggest optimizations over time
```

### From metrics-etl
```bash
# Old approach (deprecated)
# metrics-etl would export to Prometheus for Grafana

# New approach
# 1. Use usage-tracking for metrics collection
# 2. Export to JSON: usage-tracking --format json
# 3. If you have Grafana, use JSON as source
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

- **How do I restore a deprecated skill?** See RESTORATION.md for each skill
- **When should I use the alternatives?** Check the "Alternatives & Migration Paths" section in each RESTORATION.md
- **What if I still need a deprecated skill?** Restore from archive and follow re-enabling steps; add test coverage
- **Can I suggest a skill for deprecation?** File an issue with deprecation rationale and alternatives

## See Also

- [SKILLS-AVAILABLE.md](SKILLS-AVAILABLE.md) — All active skills
- [SKILL-CREATOR.md](../docs/SKILL-CREATOR.md) — How to create new skills
- [RESTORATION-PROCEDURES.md](RESTORATION-PROCEDURES.md) — Detailed restoration guide
