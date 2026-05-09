---
handoff_type: DELEGATE
task_id: 2026-04-24-quickref-card
role: Engineer
model: claude-haiku-4-5
effort: medium
scope: Create agentic-engineers quick reference card for on-screen use

context:
  - File: agentic-engineers/
  - Problem: Team has extensive docs but needs a 1-page cheat sheet for quick lookup during task execution
  - Goal: Single markdown file (fits on laptop screen, printable)

plan:
  1. Extract key tables/definitions from AGENTS.md, HANDOFF.md, QUALITY.md
  2. Create agentic-engineers/QUICK_REFERENCE.md with:
     - 7-role model (table: Role | Model | Cost)
     - DELEGATE/HANDBACK markup example (side-by-side comparison)
     - Quality Gate checklist (Tier 1 only, essentials)
     - Routing decision tree (short form)
     - Key contact points (who to escalate to)
  3. Add to agentic-engineers/README.md (link at top)
  4. Write test to validate markdown rendering

success_criteria:
  - QUICK_REFERENCE.md is <3 KB (fits one screen)
  - All 7 roles covered in role table
  - DELEGATE/HANDBACK examples are complete and accurate
  - Quality Gate essentials captured (5-7 items max)
  - README.md links to QUICK_REFERENCE.md at top under "Quick Start"
  - `make verify` passes (if applicable) or markdown lints cleanly

---
