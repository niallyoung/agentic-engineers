---
description: Review pending DELEGATEs and HANDBACKs in the queue
agent: orchestrator
subtask: true
---
Review the current state of the agentic-engineers work queue.

Scan and summarize:

1. **Incoming queue** (`artifacts/queue/incoming/`): List any pending tasks waiting for routing
2. **Processing queue** (`artifacts/queue/processing/`): List tasks in-flight with their status
3. **Done queue** (`artifacts/queue/done/`): Count completed tasks from today
4. **Recent DELEGATEs** (`artifacts/delegates/`): Show DELEGATEs from the last 24 hours

For each item found, show:
- task_id
- role/agent assigned
- status
- timestamp
- any blocking issues

Highlight any items that appear stalled or need attention.
