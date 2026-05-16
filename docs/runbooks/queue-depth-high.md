# Runbook: Queue Depth High

**Alert**: `OrchestratorQueueDepthHigh` / `OrchestratorQueueDepthCritical`
**Severity**: Warning (>100) / Critical (>500)
**Threshold**: Queue depth exceeds 100 tasks for 5 minutes

---

## Symptoms

- `orchestrator_queue_depth` gauge is elevated
- New tasks not being processed promptly
- Increasing task latency

## Immediate Actions

1. **Check queue sizes**
   ```bash
   ls artifacts/queue/incoming/ | wc -l
   ls artifacts/queue/processing/ | wc -l
   ```

2. **Check if processing is stalled**
   ```bash
   # Look for tasks stuck in processing
   find artifacts/queue/processing/ -mmin +120 -name "*.yaml"
   ```

3. **Check orchestrator health**
   ```bash
   curl http://localhost:8080/health
   ```

## Diagnosis

### Queue growing but processing normal:
- Burst of incoming tasks — may self-resolve
- Check if tasks are completing: `ls artifacts/queue/done/ | wc -l`

### Processing stalled (tasks stuck):
- Orchestrator may have crashed mid-task
- Check for zombie processes
- Look for lock files

### Queue not draining:
- Agent capacity may be insufficient
- Check model API rate limits
- Review task complexity distribution

## Resolution

1. **If burst**: Wait and monitor — queue should drain naturally
2. **If stalled processing**:
   ```bash
   # Move stuck tasks back to incoming
   find artifacts/queue/processing/ -mmin +120 -exec mv {} artifacts/queue/incoming/ \;
   ```
3. **If capacity issue**: Reduce task complexity or increase parallelism

## Prevention

- Set up queue depth monitoring with 15-minute rolling average
- Implement backpressure when queue > 50 tasks
