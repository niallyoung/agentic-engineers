---
name: CloudWatch Insights Queries for Quality Gates
description: Reusable CloudWatch Logs Insights queries for quality gate audit trail analysis
type: reference
created: 2026-04-28
---

# CloudWatch Logs Insights Queries

These queries analyze quality gate audit logs from `/ers/quality-gates/audit-trail` CloudWatch Logs group.

## Query: Quality Gate Success Rate by Service

```sql
fields @timestamp, service, phase, status
| filter ispresent(service)
| stats count() as total by service, status
| stats sum(total) as total by service
```

**Output**: Success rate breakdown by service

---

## Query: Phase Success Rates

```sql
fields phase, status
| stats count() as total by phase, status
| stats sum(total) as total by phase
```

**Output**: Which phases have highest failure rate?

---

## Query: Healer Intervention Frequency

```sql
fields @timestamp, session_id, status
| filter status like /DELEGATE_HEALER|ESCALATE/
| stats count() as healer_count, count(distinct session_id) as unique_sessions
```

**Output**: How often is Healer invoked? What's the escalation rate?

---

## Query: Execution Time Trends

```sql
fields @timestamp, details.execution_time_seconds
| filter ispresent(details.execution_time_seconds)
| stats avg(details.execution_time_seconds) as avg_time,
        max(details.execution_time_seconds) as max_time,
        min(details.execution_time_seconds) as min_time by bin(5m)
```

**Output**: Quality gate execution time trends (5-minute buckets)

---

## Query: Failure Pattern Analysis

```sql
fields details.failure_type, details.issue_type, status
| filter status = "FAIL"
| stats count() as failure_count by issue_type
| sort failure_count desc
```

**Output**: Most common failure types (helps prioritize fixes)

---

## Query: Confidence Score Calibration

```sql
fields details.confidence, details.issue_type, status
| filter ispresent(details.confidence)
| stats count() as total,
        count(select_if(status="PROCEED")) as passed
| eval success_rate = round((passed / total) * 100, 2)
| table details.confidence, total, passed, success_rate
```

**Output**: Actual success rate by confidence level (for calibration)

---

## Query: Session Duration (Start to End)

```sql
fields session_id, @timestamp, phase
| stats min(@timestamp) as start, max(@timestamp) as end by session_id
| eval duration_seconds = (end - start) / 1000
| stats avg(duration_seconds) as avg_duration,
        max(duration_seconds) as max_duration,
        min(duration_seconds) as min_duration
```

**Output**: How long do quality gates take, end to end?

---

## Query: Most Recent Failures

```sql
fields @timestamp, service, phase, details.failure_reason
| filter status = "FAIL"
| sort @timestamp desc
| limit 20
```

**Output**: Latest 20 failures (for troubleshooting)

---

## Query: Healer Success Rate (Empirical)

```sql
fields @timestamp, session_id, phase, status
| filter phase >= 3
| stats max(status) as final_status by session_id
| stats count() as total,
        count(select_if(final_status="PROCEED")) as passed
| eval healer_success_rate = round((passed / total) * 100, 2)
```

**Output**: % of sessions that reached PROCEED after Phase 3 healing

---

## Query: Issues by Type and Confidence

```sql
fields details.issue_type, details.confidence, status
| stats count() as total,
        count(select_if(status="PROCEED")) as success_count,
        count(select_if(status="FAIL")) as fail_count
  by issue_type, confidence
| eval success_rate = round((success_count / total) * 100, 2)
| sort success_rate
```

**Output**: Success rate by issue type and confidence (calibration reference)

---

## Query: Daily Metrics Summary

```sql
fields @timestamp, service, status, phase
| stats count() as total_checks,
        count(select_if(status="PASS")) as passed,
        count(select_if(status="FAIL")) as failed,
        count(select_if(status="ESCALATE")) as escalated
  by bin(1d)
| eval pass_rate = round((passed / total_checks) * 100, 2)
```

**Output**: Daily summary for dashboard or reporting

---

## Query: Anomaly Detection (Unusual Failure Spike)

```sql
fields @timestamp, status
| filter status = "FAIL"
| stats count() as failure_count by bin(1h)
| stats avg(failure_count) as baseline,
        stddev(failure_count) as stddev,
        latest(failure_count) as latest_hour
| eval anomaly_score = (latest_hour - baseline) / stddev
```

**Output**: Identifies hours with unusual number of failures (possible issue)

---

## Query: Healer PR Merge Rate

```sql
fields session_id, details.pr_created, details.pr_merged
| filter ispresent(details.pr_created)
| stats count() as prs_created,
        count(select_if(details.pr_merged="true")) as prs_merged
| eval merge_rate = round((prs_merged / prs_created) * 100, 2)
```

**Output**: % of Healer-created PRs that were merged (not closed without merging)

---

## Query: Service Reliability Ranking

```sql
fields service, status
| stats count() as total,
        count(select_if(status="PASS")) as passed
  by service
| eval pass_rate = round((passed / total) * 100, 2)
| sort pass_rate desc
```

**Output**: Which services have most stable quality gates?

---

## Usage Tips

1. **Time Range**: Use CloudWatch Logs Insights UI to set date range (top-right)
2. **Scheduled Queries**: Save frequent queries for recurring reports
3. **Exporting**: Results can be exported as CSV for analysis in spreadsheet
4. **Alerting**: Use CloudWatch Alarms on metric thresholds (e.g., failure rate > 20%)
5. **Dashboard Integration**: Pin saved queries to CloudWatch Dashboard for real-time monitoring

---

## Integration with Healer Metrics Analyzer

The `healer-metrics-analyzer.py` script uses these query patterns to extract metrics locally. For production, consider:

1. Pushing audit logs to CloudWatch Logs (add to quality-gate-orchestration.sh)
2. Creating CloudWatch custom metrics from log data
3. Scheduling daily metric calculations via EventBridge + Lambda
4. Emailing team weekly summary reports

---

## Related Documentation

- Phase 5.10: Monitoring & Continuous Improvement (PHASE-5.10-MONITORING-PLAN.md)
- Level 3 Graduation Checklist (LEVEL-3-GRADUATION-CHECKLIST.md)
- Healer Engineer (healer-engineer.md)
