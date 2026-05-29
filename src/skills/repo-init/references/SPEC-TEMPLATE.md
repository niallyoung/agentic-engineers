# repo-init: SPEC.md Authoring Guide

**Purpose:** Documents how repo-init generates `docs/SPEC.md` for a new repository.  
**Template:** See `assets/spec-template.md` for the actual template used.

---

## SPEC.md Philosophy

The generated SPEC.md follows three principles:

1. **Conservative defaults** — All defaults are the safest, lowest-cost option.
   Easy to extend upward; hard to break by starting too high.
2. **Self-contained** — The SPEC.md alone should be enough context for any
   agent to understand the project's constraints and conventions.
3. **Versioned** — Every change to SPEC.md is logged with a timestamp and author.

---

## Generated SPEC.md Structure

```
## 1. Project Identity
   - name, description, language, framework, license

## 2. Framework Configuration
   - framework_version, model_harness, date_initialized

## 3. Agent Team
   - Enabled agent roles for this repo
   - Model assignment per role
   - Effort defaults per role

## 4. Quality Gates
   - Minimum test coverage threshold
   - HANDBACK required (true/false)
   - Spec compliance required (true/false)
   - Code review required (true/false)

## 5. Tool Availability
   - Pre-filled from Phase 1 + Phase 6 analysis
   - git, python, bash, jq, curl status

## 6. Delegation Protocol
   - DELEGATE block format required
   - HANDBACK block format required
   - Queue location (~/.agentic-engineers/)

## 7. Escalation Paths
   - engineer → senior-engineer
   - senior-engineer → lead-engineer
   - security concerns → security-engineer
   - architecture decisions → principal-engineer

## 8. Conventions
   - Naming conventions (kebab-case, snake_case per language)
   - Commit message format
   - Branch naming
   - Test naming format (test_<action>_<scenario>_<expected>)

## 9. Change Log
   - Managed by spec-management skill
   - Initial entry from repo-init
```

---

## Conservative Defaults Rationale

| Setting | Conservative Default | Why |
|---------|---------------------|-----|
| Engineer model | `claude-haiku-4.5` | Cheapest capable model; upgrade when needed |
| Senior model | `claude-sonnet-4.6` | Balance of cost and capability |
| Lead model | `claude-sonnet-4.6` | Same tier; promote to opus when complex |
| Principal model | `claude-opus-4.8` | Highest capability for architecture decisions |
| Default effort | `low` | Prevents runaway token spend |
| Coverage threshold | `85%` | Industry standard; lower for legacy code |
| Require HANDBACK | `true` | Always get a structured result |
| Require spec compliance | `true` | Enforce from day one |

---

## SPEC.md Sections: What Agents Read

Agents read SPEC.md to answer these questions:

| Question | Section |
|----------|---------|
| What model should I use? | §3 Agent Team |
| How hard should I try? | §3 Agent Team (effort) |
| What quality is required? | §4 Quality Gates |
| What tools are available? | §5 Tool Availability |
| How do I format my output? | §6 Delegation Protocol |
| Who do I escalate to? | §7 Escalation Paths |
| What are the naming conventions? | §8 Conventions |

---

## Modifying SPEC.md After init

After init, SPEC.md is **read-only** except via the `spec-management` skill.

To propose a change:
```yaml
DELEGATE:
  task: spec-management
  skill: spec-management
  action: propose-change
  section: "§3 Agent Team"
  proposed_change: "Upgrade engineer model to claude-sonnet-4.6"
  justification: "Project complexity warrants higher capability"
  authority: lead-engineer
```

The `spec-management` skill handles authorization, impact analysis, and changelog.

---

## Template Variables Reference

All variables are wrapped in `{curly_braces}` in `assets/spec-template.md`.

### Inferred from Analysis (Phase 1)

```
{project_name}         Project directory name, lowercased, spaces→hyphens
{primary_language}     Most common file extension language
{package_manager}      First detected package manager
{test_framework}       Detected test framework or "unknown"
{ci_provider}          Detected CI or "none"
{license}              LICENSE file content first line or "unknown"
{git_remote}           First git remote URL or ""
{contributor_count}    `git log --format='%ae' | sort -u | wc -l`
{total_files}          `find . -type f | wc -l` (excluding .git)
{is_monorepo}          "true" or "false"
```

### From Config (User-Provided or Defaults)

```
{project_description}  User-provided or ""
{model_harness}        "claude" | "gpt5" | "local"
{framework_version}    Pinned version string
{date}                 ISO-8601 date of initialization
```

### From Compatibility Check (Phase 6)

```
{engineer_model}       Model selected for engineer role
{senior_model}         Model selected for senior-engineer role
{lead_model}           Model selected for lead-engineer role
{principal_model}      Model selected for principal-engineer role
{quality_threshold}    Coverage % (85 or 70 for large repos)
{tool_git}             "✅" or "❌"
{tool_python}          "✅" or "❌"
{tool_bash}            "✅" or "⚠️"
{tool_jq}              "✅" or "⚠️"
```
