# STANDARDS-DOCUMENTATION-PLAN.md

**Date:** 2025-05-09  
**Author:** Senior Engineer  
**Status:** DESIGN — Awaiting Implementation  
**Purpose:** Detailed plan for what to add/update in SPEC.md and README.md, plus the new STANDARDS.md

---

## Overview

The agentic-engineers framework targets several AI agent ecosystem standards. Currently, none of these are documented. This plan defines:
1. What to add to `docs/SPEC.md` (new section only — no existing content changes)
2. What to add to `README.md` (new "Standards Compliance" section)
3. The complete content plan for new `STANDARDS.md`

---

## 1. Standards We Target

### 1.1 AGENTS.md Convention
- **What it is:** A community-emerging standard for describing AI agents and their routing/invocation rules. Files named `AGENTS.md` in a repository describe how AI agents should behave, what tools they have access to, and how orchestration should work.
- **Our implementation:** `src/docs/AGENTS.md` — routing decision tree, role definitions, delegation rules
- **Official reference:** Community standard; see also OpenAI's Codex guidance on AGENTS.md format
- **Compliance criteria:**
  - [ ] `src/docs/AGENTS.md` exists and is machine-parseable
  - [ ] Defines all agent roles with model, capability, and routing rules
  - [ ] Referenced by Orchestrator skill as authoritative routing source
  - [ ] Updated whenever a new agent role is added

### 1.2 Claude Code (Anthropic)
- **What it is:** Anthropic's Claude coding environment and `.claude/` directory convention. Supports `CLAUDE.md` for project-level instructions and `~/.claude/agents/`, `~/.claude/skills/` for agent/skill installation.
- **Our implementation:** `renderer/render-claude.sh` renders to `~/.claude/agents/` and `~/.claude/skills/`; `docs/guides/CLAUDE.md` provides Claude-specific guidance
- **Official reference:** https://docs.anthropic.com/en/docs/claude-code
- **Compliance criteria:**
  - [ ] All agent definitions render cleanly to `~/.claude/agents/<name>.md`
  - [ ] Frontmatter stripped correctly per Claude Code format
  - [ ] Model aliases use Claude Code names (haiku, sonnet, opus)
  - [ ] Skills render to `~/.claude/skills/<name>/` with valid `SKILL.md`
  - [ ] `CLAUDE.md` at project root or `docs/guides/CLAUDE.md` provides project context

### 1.3 GitHub Copilot (Microsoft)
- **What it is:** GitHub Copilot's agent and skill framework. Supports `~/.copilot/agents/` and `~/.copilot/skills/` for agent installation; `copilot-instructions.md` for project-level context.
- **Our implementation:** `renderer/render-copilot.sh` and `render-copilot-agents.py` render to `~/.copilot/agents/` and `~/.copilot/skills/`; `renderer/instructions/copilot-instructions.md` provides project context
- **Official reference:** https://docs.github.com/en/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot
- **Compliance criteria:**
  - [ ] All agent definitions render cleanly to `~/.copilot/agents/`
  - [ ] All skill directories render to `~/.copilot/skills/<name>/`
  - [ ] `copilot-instructions.md` exists and describes the project correctly
  - [ ] Agent frontmatter is valid YAML per Copilot spec
  - [ ] `render-copilot-agents.py` validates output format

### 1.4 agentskills.io Specification
- **What it is:** An emerging specification for portable AI agent skills. Defines the `SKILL.md` frontmatter format, directory structure, and metadata schema.
- **Our implementation:** All skills in `src/skills/*/SKILL.md` follow this format; `src/skills/skill-creator/SKILL.md` helps create compliant skills
- **Official reference:** https://agentskills.io/specification
- **Compliance criteria:**
  - [ ] All `SKILL.md` files have valid frontmatter (`name`, `description` required)
  - [ ] `name` is lowercase, hyphens only, 1-64 chars
  - [ ] `description` is 1-1024 chars, explains when/why to use
  - [ ] Optional fields (`license`, `compatibility`, `metadata`) are present where applicable
  - [ ] No skills violate the directory layout spec

---

## 2. Changes to `docs/SPEC.md`

### What to Add

Append the following section to the **end** of `docs/SPEC.md`. Do not modify any existing content.

**Section heading:** `## Standards Alignment`

**Content outline:**
```markdown
## Standards Alignment

This specification aligns with the following external standards. 
Compliance with these standards ensures the framework operates correctly 
across the supported AI development environments.

### Targeted Standards

| Standard | Authority | Implementation | Status |
|----------|-----------|----------------|--------|
| AGENTS.md Convention | Community | src/docs/AGENTS.md | ✅ Compliant |
| Claude Code | Anthropic | renderer/render-claude.sh | ✅ Compliant |
| GitHub Copilot | Microsoft/GitHub | renderer/render-copilot*.{sh,py} | ✅ Compliant |
| agentskills.io | agentskills.io | src/skills/*/SKILL.md | ✅ Compliant |

### Compliance Requirements

For each standard, implementation requirements are:
[List compliance criteria for each standard as defined in STANDARDS.md]

### Adding New Standards

New standards may only be added to this section by Lead Engineer or Principal Engineer.
Changes to this section require:
1. New standard assessed against all existing skills and agents
2. Compliance gap analysis documented
3. Remediation plan approved
4. This section updated with status
```

**Implementation rules:**
- This section is appended, never replaces existing content
- Only Lead Engineer or Principal Engineer may make changes to this section
- Must update compliance status column whenever a standard requirement changes

---

## 3. Changes to `README.md`

### What to Add

Add the following section after the "Architecture" section and before "Getting Started" (or wherever appropriate in the existing flow):

**Section heading:** `## Standards Compliance`

**Content outline:**
```markdown
## Standards Compliance

Agentic Engineers is designed to work within the major AI agent ecosystems:

| Standard | Purpose | Our Implementation |
|----------|---------|---------------------|
| **AGENTS.md** | Agent routing & role definitions | `src/docs/AGENTS.md` |
| **Claude Code** | Anthropic agent installation | `~/.claude/agents/`, `~/.claude/skills/` |
| **GitHub Copilot** | GitHub agent installation | `~/.copilot/agents/`, `~/.copilot/skills/` |
| **agentskills.io** | Portable skill specification | `src/skills/*/SKILL.md` |

For full compliance matrix, roadmap, and contribution guide, see [STANDARDS.md](./STANDARDS.md).
```

**Implementation rules:**
- Keep it brief — README.md is already 1,326 lines
- Link to STANDARDS.md for details
- Do not duplicate information from STANDARDS.md

---

## 4. New File: `STANDARDS.md`

**Location:** Repository root (parallel to README.md)  
**Size target:** 150-250 lines  
**Audience:** Contributors, integrators, standards reviewers

### 4.1 File Structure

```markdown
# Standards Alignment

## 1. Overview
Brief intro: why standards compliance matters for the project

## 2. Targeted Standards
For each standard:
- What it is
- Official reference + link
- How agentic-engineers implements it
- Current compliance status

## 3. Compliance Matrix
Table: Standard × Requirement × Status (✅/⚠️/❌)

## 4. Compliance Roadmap
- Items currently ⚠️ or ❌ with plan to reach ✅
- Tracking: link to TODO.md items

## 5. How to Contribute Standards Improvements
- Process for proposing new standard alignment
- Process for flagging compliance gaps
- Who approves compliance changes (Lead/Principal Engineer)

## 6. Version History
- When this document was last updated
- What changed
```

### 4.2 Compliance Matrix Detail

The matrix should cover at minimum:

**AGENTS.md:**
- AGENTS.md file exists → ✅
- All roles defined with model + routing → ✅
- Machine-parseable format → ⚠️ (structured prose, not YAML schema yet)

**Claude Code:**
- Agents render to `~/.claude/agents/` → ✅
- Frontmatter stripped correctly → ✅
- Model aliases correct → ✅
- Skills render to `~/.claude/skills/` → ✅
- CLAUDE.md present → ✅ (in docs/guides/)

**GitHub Copilot:**
- Agents render to `~/.copilot/agents/` → ✅
- Skills render to `~/.copilot/skills/` → ✅
- copilot-instructions.md present → ✅
- Agent frontmatter valid → ✅

**agentskills.io:**
- All SKILL.md have name + description → ✅ (needs verification)
- name format compliance → ⚠️ (needs audit)
- directory structure compliance → ✅

### 4.3 Roadmap Items

Initial roadmap items to document:
1. Audit all `SKILL.md` files for `name` field format compliance (agentskills.io)
2. Consider structured YAML schema for `AGENTS.md` (machine-parseability)
3. Verify `copilot-instructions.md` is up to date with current architecture
4. Add compliance check to CI (`make verify` or new `make check-standards`)

---

## 5. Implementation Sequence

```
Step 1: Create STANDARDS.md (standalone, no dependencies)
Step 2: Add "Standards Compliance" section to README.md
Step 3: Append "Standards Alignment" section to docs/SPEC.md
         └─ Requires: Lead/Principal Engineer sign-off
Step 4: Add TODO items for compliance gaps identified in matrix
```

**Note:** Steps 1-2 can be done by Senior Engineer. Step 3 requires Lead or Principal Engineer approval per SPEC.md protection rules.

---

## Related Documents

- `CLEANUP-STRATEGY.md` — Phase 1 of cleanup plan
- `STANDARDS.md` — (to be created) Comprehensive standards reference
- `docs/SPEC.md` — System specification (protected)
- `docs/decisions/` — Architecture Decision Records
