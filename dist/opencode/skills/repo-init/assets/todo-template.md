# TODO: {project_name}

**Last Updated:** {date}  
**Initialized by:** repo-init skill v1.0  
**Framework Version:** {framework_version}  
**Status:** Active

---

## 🔴 Priority (Must Do First)

- [ ] **INIT-001:** Review and customize generated SPEC.md
  - Path: `docs/SPEC.md`
  - Action: Verify agent assignments, model tiers, quality gate thresholds
  - Owner: Principal Engineer
  - Added: {date}

- [ ] **INIT-002:** Run compatibility validation and fix any warnings
  - Command: `python3 src/skills/repo-init/scripts/validate_compatibility.py --repo-root . --report`
  - Owner: Senior Engineer
  - Added: {date}

{priority_conditional_items}

---

## 🟡 Standard (Active Backlog)

- [ ] **INIT-003:** Write first failing tests (TDD RED-phase)
  - Pattern: `test_<action>_<scenario>_<expected>` in `tests/`
  - Reference: `docs/QUICK-START.md#tdd-workflow`
  - Owner: Engineer
  - Added: {date}

- [ ] **INIT-004:** Configure CI/CD integration
  - Reference: `docs/ONBOARDING.md#cicd`
  - Owner: Engineer
  - Added: {date}

- [ ] **INIT-005:** Review generated docs and customize for project
  - Files: `docs/ONBOARDING.md`, `docs/QUICK-START.md`
  - Owner: Lead Engineer
  - Added: {date}

{standard_conditional_items}

---

## 🔮 Future (Not Yet Scheduled)

- [ ] **INIT-F01:** Add project-specific agent customizations
  - Reference: `agents/README.md`
  - Added: {date}

- [ ] **INIT-F02:** Add custom skills for project-specific automation
  - Reference: `skills/README.md`
  - Use: skill-creator skill
  - Added: {date}

{future_conditional_items}

---

## ✅ Recently Completed (Last 30 Days)

- [x] **INIT-000:** Initialize agentic-engineers framework — *Completed: {date}* — repo-init v1.0

---

*This TODO.md is maintained by the `todo-maintenance` skill. All new items must come
through the delegation queue (see `artifacts/queue/`). Do not add items manually
unless you are a Principal Engineer or Lead Engineer.*
