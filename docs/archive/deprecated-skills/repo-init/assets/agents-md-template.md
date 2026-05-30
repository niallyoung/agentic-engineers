# Agents — {project_name}

**Framework Version:** {framework_version}  
**Generated:** {date} by repo-init v1.0  
**Model Harness:** {model_harness}

---

## Agent Roster

| Role | Model | Effort | Status |
|------|-------|--------|--------|
| Orchestrator | {senior_model} | low | ✅ Enabled |
| Engineer | {engineer_model} | low | ✅ Enabled |
| Senior Engineer | {senior_model} | medium | ✅ Enabled |
| Lead Engineer | {lead_model} | medium | ✅ Enabled |
| Quality Engineer | {senior_model} | medium | ✅ Enabled |
| Security Engineer | {principal_model} | medium | ✅ Enabled |
| Principal Engineer | {principal_model} | high | ✅ Enabled |

---

## Task Routing Table

| Task Type | Agent | Effort |
|-----------|-------|--------|
| Bug fix | Engineer | low |
| Feature implementation | Engineer | low |
| Complex feature | Senior Engineer | medium |
| Deep debugging | Senior Engineer | medium |
| Code review | Lead Engineer | medium |
| Standards enforcement | Lead Engineer | medium |
| Testing / coverage | Quality Engineer | medium |
| Security review | Security Engineer | medium |
| Architecture decision | Principal Engineer | high |
| Cross-service integration | Senior Engineer | medium |
| Mentoring | Senior Engineer | medium |
| Onboarding | Engineer | low |

---

## Escalation Paths

```
Engineer
  ├── Scope too large → Senior Engineer
  └── Standards question → Lead Engineer

Senior Engineer
  ├── Architecture question → Principal Engineer
  ├── Security concern → Security Engineer
  └── Code review needed → Lead Engineer

Lead Engineer
  ├── Organization-wide decision → Principal Engineer
  └── Security incident → Security Engineer

Quality Engineer
  └── Architecture-level quality issue → Principal Engineer

Any Agent
  └── Security vulnerability found → Security Engineer (immediate)
```

---

## Model Assignments

See `.agentic-engineers/config.yaml` for complete configuration.

```yaml
# Summary
engineer: {engineer_model}
senior-engineer: {senior_model}
lead-engineer: {lead_model}
quality-engineer: {senior_model}
security-engineer: {principal_model}
principal-engineer: {principal_model}
orchestrator: {senior_model}
```

---

## Effort Guide

| Effort | When to Use | Approximate Scope |
|--------|-------------|-------------------|
| `low` | Routine tasks, well-defined scope | < 2 hours of work |
| `medium` | Complex tasks, some ambiguity | 2–8 hours of work |
| `high` | Architecture decisions, large scope | > 8 hours of work |

Default effort is `low`. Increase only when the task genuinely warrants it.

---

## Queue Locations

| Queue | Path | Purpose |
|-------|------|---------|
| Incoming | `~/.agentic-engineers/incoming/` | New DELEGATE tasks |
| Done | `~/.agentic-engineers/done/` | Completed tasks |
| Failed | `~/.agentic-engineers/failed/` | Failed tasks (for retry) |

---

*Managed by the agentic-engineers framework. See `docs/SPEC.md` for framework spec.*
