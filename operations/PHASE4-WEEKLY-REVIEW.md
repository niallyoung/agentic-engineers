# Phase 4 Weekly Review — QE Operations Card

**Quick reference for Monday/Wednesday/Friday cadence.**  
Full strategy: `docs/phase4-metrics-tracking.md`

---

## Monday — Data Collection Checklist

- [ ] Pull last week's Engineer HANDBACKs from `artifacts/`
- [ ] Search HANDBACK `notes` for: `Actions`, `pipeline`, `CI`, `cicd-watch`, `gh run` → update **M1 table**
- [ ] Identify Senior Engineer planning tasks → update **M2 table** (filter to decomposition/design only)
- [ ] Review QE assessments produced last week → update **M3 table** (self-check: 8 dims + band + YAML?)
- [ ] Cross-check Lead APPROVE/REWORK vs QE scores → update **M4 table**
- [ ] Check Lead review comments on pattern PRs (api-resilience, event-consumer) → update **M5 table**
- [ ] Review all HANDBACK `status: failed` + escalation reasons → update **M6 table**
- [ ] Update all "Running totals" rows in each table

---

## Wednesday — Red Flag Check

Run through this in order. First red flag triggered = intervention required by Friday.

```
M1  Engineer cicd-watch      [ ] ≥80%?    Current: __%
M2  Senior todo-management   [ ] ≥75%?    Current: __%  (2-week avg)
M3  QE baseline compliance   [ ] ≥80%?    Current: __%
M4  Lead + QE agreement      [ ] ≥90%?    Current: __%  (2-week avg)
M5  Pattern misapplication   [ ] ≤5%?     Current: __%  (2-week avg)
M6  Skill-gap escalations    [ ] = 0?     Count: __
```

**Any box unchecked?** Write the intervention note in the Weekly Analysis Log.

---

## Friday — Intervention Execution (only if red flags exist)

| Red Flag | Who acts | What to do |
|----------|----------|------------|
| M1 <80% | QE | Add note to `skills/roles/engineer.md` cicd-watch skill reference |
| M2 <75% (2 weeks) | QE | Add note to `skills/roles/senior-engineer.md` todo-management skill reference |
| M3 <80% | QE (self) | Start next assessment with YAML template from quality-assessment-baseline.md Section 4 |
| M4 <90% (2 weeks) | QE schedules sync | 30-min Lead + QE calibration — use 2–3 disagreement examples |
| M5 >5% (2 weeks) | QE flags to Senior | Senior adds "Common Mistakes" section to pattern file |
| M6 any skill gap | QE IMMEDIATE | Fix role file within 24h — see M6 playbook |

---

## Weekly Log Entry (complete Wednesday)

```
Week __ (__ to __)
M1: __% | M2: __% | M3: __% | M4: __% | M5: __% | M6: __
Red flags: [none / M1 M2 M3 M4 M5 M6]
Interventions: [none / <description>]
Note: 
```

---

## Key File Locations

| Resource | Path |
|----------|------|
| Engineer role | `skills/roles/engineer.md` |
| Senior Engineer role | `skills/roles/senior-engineer.md` |
| Lead Engineer role | `skills/roles/lead-engineer.md` |
| Quality Engineer role | `skills/roles/quality-engineer.md` |
| Quality Assessment Baseline | `shared/quality-assessment-baseline.md` |
| cicd-watch skill | `skills/monitoring/cicd-watch.md` |
| todo-management skill | `skills/orchestration/todo-management.md` |
| api-resilience pattern | `skills/patterns/api-resilience.md` |
| event-consumer pattern | `skills/patterns/event-consumer.md` |
| Full tracking tables | `docs/phase4-metrics-tracking.md` |
| Week 4 report template | `docs/phase4-metrics-tracking.md` (Deliverable 4) |
