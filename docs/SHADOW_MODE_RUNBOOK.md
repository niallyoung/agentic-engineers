# Shadow Mode Operations Runbook

## Quick Start

### Enable Shadow Mode

```bash
# Set environment variables
export SHADOW_MODE_ENABLED=true
export SHADOW_MODE_TRAFFIC_PCT=10

# Restart orchestrator
make orchestrator-start
```

### Disable Shadow Mode

```bash
export SHADOW_MODE_ENABLED=false

# Restart orchestrator
make orchestrator-restart
```

### Check Shadow Mode Status

```bash
# Check environment variables
echo "Shadow mode enabled: $SHADOW_MODE_ENABLED"
echo "Traffic percentage: $SHADOW_MODE_TRAFFIC_PCT"

# Check metrics directory
ls -la artifacts/shadow-mode/

# Count results from today
date_str=$(date +%Y-%m-%d)
ls artifacts/shadow-mode/${date_str}-*-shadow.yaml | wc -l
```

## Daily Operations

### Morning: Review Previous Day's Metrics

```bash
#!/bin/bash
# review_shadow_metrics.sh

YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
METRICS_DIR="artifacts/shadow-mode"

echo "=== Shadow Mode Metrics for $YESTERDAY ==="

# Count results
TOTAL=$(ls ${METRICS_DIR}/${YESTERDAY}-*-shadow.yaml 2>/dev/null | wc -l)
echo "Total results: $TOTAL"

# Check for errors
ERRORS=$(grep -l "shadow_error:" ${METRICS_DIR}/${YESTERDAY}-*-shadow.yaml 2>/dev/null | wc -l)
echo "Tasks with shadow errors: $ERRORS"

# Check match rate
MATCHES=$(grep "results_match: true" ${METRICS_DIR}/${YESTERDAY}-*-shadow.yaml 2>/dev/null | wc -l)
MISMATCHES=$(grep "results_match: false" ${METRICS_DIR}/${YESTERDAY}-*-shadow.yaml 2>/dev/null | wc -l)
if [ $((MATCHES + MISMATCHES)) -gt 0 ]; then
    MATCH_PCT=$((MATCHES * 100 / (MATCHES + MISMATCHES)))
    echo "Match rate: ${MATCH_PCT}% ($MATCHES/$((MATCHES + MISMATCHES)))"
fi

# Check performance
echo ""
echo "=== Top 5 Slowest Shadow Executions ==="
grep "shadow_latency_ms:" ${METRICS_DIR}/${YESTERDAY}-*-shadow.yaml 2>/dev/null | \
    sort -t: -k2 -rn | head -5
```

### Monitor: Check Health During Day

```bash
#!/bin/bash
# monitor_shadow_health.sh

METRICS_DIR="artifacts/shadow-mode"
TODAY=$(date +%Y-%m-%d)

echo "=== Shadow Mode Health Check ==="
echo "Time: $(date)"
echo ""

# Check latest results
LATEST=$(ls -t ${METRICS_DIR}/${TODAY}-*-shadow.yaml 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
    echo "❌ No results today"
    exit 1
fi

echo "✅ Latest result: $(basename $LATEST)"

# Check error rate
TOTAL=$(ls ${METRICS_DIR}/${TODAY}-*-shadow.yaml 2>/dev/null | wc -l)
ERRORS=$(grep -l "shadow_error:" ${METRICS_DIR}/${TODAY}-*-shadow.yaml 2>/dev/null | wc -l)

if [ $TOTAL -gt 0 ]; then
    ERROR_PCT=$((ERRORS * 100 / TOTAL))
    echo "Error rate: ${ERROR_PCT}% ($ERRORS/$TOTAL)"
    
    if [ $ERROR_PCT -gt 10 ]; then
        echo "⚠️  High error rate detected"
    fi
fi

# Check for recent mismatches
MISMATCHES=$(grep "results_match: false" ${METRICS_DIR}/${TODAY}-*-shadow.yaml 2>/dev/null | wc -l)
if [ $MISMATCHES -gt 0 ]; then
    echo "⚠️  Found $MISMATCHES result mismatches"
fi
```

### Evening: Generate Daily Report

```bash
#!/bin/bash
# generate_shadow_report.sh

python3 << 'EOF'
from src.orchestration.agents.shadow_mode import ShadowModeAggregator
from datetime import datetime, timedelta

# Generate report for yesterday
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

aggregator = ShadowModeAggregator()
metrics = aggregator.aggregate_daily(yesterday)

print(f"\n{'='*60}")
print(f"Shadow Mode Daily Report - {yesterday}")
print(f"{'='*60}\n")

print(f"Total tasks: {metrics.total_tasks}")
print(f"Sampled tasks: {metrics.sampled_tasks}")
print(f"Sampling rate: {metrics.sampling_rate:.1%}\n")

print(f"Correctness:")
print(f"  Match rate: {metrics.match_rate:.1%}")
print(f"  Matching: {metrics.matching_results}")
print(f"  Mismatched: {metrics.mismatched_results}\n")

print(f"Errors:")
print(f"  Production errors: {metrics.production_errors}")
print(f"  Shadow errors: {metrics.shadow_errors}")
print(f"  Error correlation: {metrics.error_correlation:.1%}\n")

print(f"Performance:")
print(f"  Avg production latency: {metrics.avg_production_latency_ms:.2f}ms")
print(f"  Avg shadow latency: {metrics.avg_shadow_latency_ms:.2f}ms")
print(f"  Avg performance ratio: {metrics.avg_performance_ratio:.2f}x\n")

# Save report
report_path = aggregator.save_aggregated_report(metrics, yesterday)
print(f"Report saved to: {report_path}")

# Alert if issues detected
if metrics.match_rate < 0.95:
    print("\n⚠️  WARNING: Match rate below 95%")

if metrics.shadow_errors > metrics.total_tasks * 0.05:
    print("\n⚠️  WARNING: Shadow error rate above 5%")

if metrics.avg_performance_ratio > 1.5:
    print("\n⚠️  WARNING: Shadow code 50% slower than production")

EOF
```

## Incident Response

### High Shadow Error Rate

```bash
#!/bin/bash
# incident_high_error_rate.sh

THRESHOLD=0.10  # 10%
METRICS_DIR="artifacts/shadow-mode"
TODAY=$(date +%Y-%m-%d)

# Calculate error rate
TOTAL=$(ls ${METRICS_DIR}/${TODAY}-*-shadow.yaml 2>/dev/null | wc -l)
ERRORS=$(grep -l "shadow_error:" ${METRICS_DIR}/${TODAY}-*-shadow.yaml 2>/dev/null | wc -l)

if [ $TOTAL -eq 0 ]; then
    exit 0
fi

ERROR_RATE=$(echo "scale=2; $ERRORS / $TOTAL" | bc)

if (( $(echo "$ERROR_RATE > $THRESHOLD" | bc -l) )); then
    echo "🚨 INCIDENT: High shadow error rate detected"
    echo "Error rate: ${ERROR_RATE} (threshold: ${THRESHOLD})"
    echo ""
    echo "Recent errors:"
    grep -h "shadow_error:" ${METRICS_DIR}/${TODAY}-*-shadow.yaml 2>/dev/null | \
        sort | uniq -c | sort -rn | head -10
    echo ""
    echo "ACTIONS:"
    echo "1. Review shadow code for bugs"
    echo "2. Check for missing dependencies"
    echo "3. Reduce traffic percentage"
    echo "4. Disable shadow mode if necessary"
fi
```

### Low Match Rate

```bash
#!/bin/bash
# incident_low_match_rate.sh

THRESHOLD=0.95  # 95%
METRICS_DIR="artifacts/shadow-mode"
TODAY=$(date +%Y-%m-%d)

# Calculate match rate
MATCHES=$(grep "results_match: true" ${METRICS_DIR}/${TODAY}-*-shadow.yaml 2>/dev/null | wc -l)
MISMATCHES=$(grep "results_match: false" ${METRICS_DIR}/${TODAY}-*-shadow.yaml 2>/dev/null | wc -l)
TOTAL=$((MATCHES + MISMATCHES))

if [ $TOTAL -eq 0 ]; then
    exit 0
fi

MATCH_RATE=$(echo "scale=2; $MATCHES / $TOTAL" | bc)

if (( $(echo "$MATCH_RATE < $THRESHOLD" | bc -l) )); then
    echo "🚨 INCIDENT: Low match rate detected"
    echo "Match rate: ${MATCH_RATE} (threshold: ${THRESHOLD})"
    echo "Matches: $MATCHES, Mismatches: $MISMATCHES"
    echo ""
    echo "Sample mismatches:"
    ls -t ${METRICS_DIR}/${TODAY}-*-shadow.yaml 2>/dev/null | \
        xargs grep -l "results_match: false" | head -3 | \
        while read f; do
            echo "File: $(basename $f)"
            grep -A 5 "detailed_differences:" "$f"
            echo ""
        done
    echo ""
    echo "ACTIONS:"
    echo "1. Review detailed differences in result files"
    echo "2. Check for non-deterministic behavior"
    echo "3. Validate comparison logic"
    echo "4. Reduce traffic percentage"
fi
```

### Performance Degradation

```bash
#!/bin/bash
# incident_performance_degradation.sh

THRESHOLD=1.5  # 50% slower
METRICS_DIR="artifacts/shadow-mode"
TODAY=$(date +%Y-%m-%d)

python3 << EOF
import yaml
from pathlib import Path

metrics_dir = Path("${METRICS_DIR}")
today = "${TODAY}"

# Load all results
results = []
for f in metrics_dir.glob(f"{today}-*-shadow.yaml"):
    with open(f) as fp:
        results.append(yaml.safe_load(fp))

if not results:
    exit(0)

# Calculate average performance ratio
ratios = [r.get('performance_ratio', 1.0) for r in results if r.get('sampled')]
if not ratios:
    exit(0)

avg_ratio = sum(ratios) / len(ratios)

if avg_ratio > ${THRESHOLD}:
    print(f"🚨 INCIDENT: Performance degradation detected")
    print(f"Avg performance ratio: {avg_ratio:.2f}x (threshold: ${THRESHOLD}x)")
    print("")
    print("Slowest executions:")
    sorted_results = sorted(
        [r for r in results if r.get('sampled')],
        key=lambda x: x.get('performance_ratio', 1.0),
        reverse=True
    )
    for r in sorted_results[:5]:
        print(f"  {r['task_id']}: {r['performance_ratio']:.2f}x")
    print("")
    print("ACTIONS:")
    print("1. Profile shadow code")
    print("2. Optimize hot paths")
    print("3. Check for unnecessary operations")
    print("4. Reduce traffic percentage")
EOF
```

## Escalation Procedures

### Level 1: Automatic Alerting

```yaml
# Alert conditions
alerts:
  - name: HighShadowErrorRate
    condition: shadow_errors / total_tasks > 0.10
    action: Log warning, notify team
  
  - name: LowMatchRate
    condition: match_rate < 0.95
    action: Log warning, notify team
  
  - name: PerformanceDegradation
    condition: avg_performance_ratio > 1.5
    action: Log warning, notify team
```

### Level 2: Manual Review

If alerts trigger:
1. Review shadow mode metrics
2. Check error logs
3. Analyze mismatches
4. Reduce traffic percentage if needed

### Level 3: Disable Shadow Mode

If issues persist:
```bash
export SHADOW_MODE_ENABLED=false
make orchestrator-restart
```

### Level 4: Rollback

If shadow code causes production issues:
1. Disable shadow mode immediately
2. Revert shadow code changes
3. Investigate root cause
4. Plan new implementation

## Maintenance Tasks

### Weekly: Cleanup Old Results

```bash
#!/bin/bash
# cleanup_old_shadow_results.sh

METRICS_DIR="artifacts/shadow-mode"
RETENTION_DAYS=30

# Remove results older than 30 days
find ${METRICS_DIR} -name "*-shadow.yaml" -mtime +${RETENTION_DAYS} -delete

echo "Cleaned up shadow mode results older than ${RETENTION_DAYS} days"
```

### Monthly: Analyze Trends

```bash
#!/bin/bash
# analyze_shadow_trends.sh

python3 << 'EOF'
from src.orchestration.agents.shadow_mode import ShadowModeAggregator
from datetime import datetime, timedelta

aggregator = ShadowModeAggregator()

print("\n" + "="*60)
print("Shadow Mode Monthly Trend Analysis")
print("="*60 + "\n")

# Analyze last 30 days
for i in range(30, 0, -1):
    date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
    metrics = aggregator.aggregate_daily(date)
    
    if metrics.total_tasks == 0:
        continue
    
    print(f"{date}: {metrics.total_tasks:4d} tasks, "
          f"{metrics.match_rate:.1%} match, "
          f"{metrics.avg_performance_ratio:.2f}x perf")

print("\n" + "="*60)
EOF
```

### Quarterly: Capacity Planning

```bash
#!/bin/bash
# capacity_planning.sh

python3 << 'EOF'
from src.orchestration.agents.shadow_mode import ShadowModeAggregator
from datetime import datetime, timedelta
from pathlib import Path

aggregator = ShadowModeAggregator()
metrics_dir = Path("artifacts/shadow-mode")

# Calculate storage usage
total_size = sum(f.stat().st_size for f in metrics_dir.glob("*-shadow.yaml"))
total_size_mb = total_size / (1024 * 1024)

# Estimate growth
days = 90
avg_files_per_day = len(list(metrics_dir.glob("*-shadow.yaml"))) / max(days, 1)
avg_size_per_file = total_size / max(len(list(metrics_dir.glob("*-shadow.yaml"))), 1)

print(f"Current storage: {total_size_mb:.2f} MB")
print(f"Avg files per day: {avg_files_per_day:.0f}")
print(f"Avg file size: {avg_size_per_file:.0f} bytes")
print(f"Projected annual storage: {(avg_files_per_day * 365 * avg_size_per_file) / (1024*1024):.2f} MB")
EOF
```

## Dashboards

### Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "Shadow Mode Metrics",
    "panels": [
      {
        "title": "Daily Task Volume",
        "targets": [
          {
            "expr": "shadow_mode_total_tasks"
          }
        ]
      },
      {
        "title": "Match Rate",
        "targets": [
          {
            "expr": "shadow_mode_match_rate"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "shadow_mode_error_rate"
          }
        ]
      },
      {
        "title": "Performance Ratio",
        "targets": [
          {
            "expr": "shadow_mode_performance_ratio"
          }
        ]
      }
    ]
  }
}
```

## Troubleshooting Checklist

- [ ] Shadow mode is enabled in environment variables
- [ ] `artifacts/shadow-mode/` directory exists and is writable
- [ ] Results are being written to disk
- [ ] No permission errors in logs
- [ ] Shadow code is being executed (check latency metrics)
- [ ] Results are being compared correctly
- [ ] Metrics are being aggregated daily
- [ ] No disk space issues
- [ ] No memory leaks in shadow execution

## Contact & Escalation

- **On-Call Engineer**: See PagerDuty rotation
- **Shadow Mode Owner**: @engineering-lead
- **Slack Channel**: #shadow-mode-alerts
- **Runbook**: This document
