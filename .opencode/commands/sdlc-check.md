---
description: Validate SDLC workflow compliance — check queue, DELEGATEs, and HANDBACKs
agent: orchestrator
subtask: true
---
Perform a SDLC workflow compliance check for the agentic-engineers framework.

Run the following checks and report results:

1. **Queue health**: Check `artifacts/queue/` for any stalled items:
   - Files in `incoming/` older than 1 hour (may be stalled)
   - Files in `processing/` without a corresponding HANDBACK
   - Any malformed YAML in queue files

2. **DELEGATE/HANDBACK integrity**: Scan `artifacts/delegates/` for:
   - DELEGATEs without a matching HANDBACK
   - HANDBACKs with status != complete that are older than 2 hours
   - Missing required fields (task_id, timestamp, role, scope)

3. **Git hooks status**: Verify enforcement hooks are active:
   - Run: `git config core.hooksPath` — should return `.githooks`
   - Check `.githooks/pre-commit`, `commit-msg`, `pre-push` exist and are executable

4. **SPEC compliance**: Quick check that no violations exist:
   - No `.py` or `.sh` files in `orchestration/scripts/` (if directory exists)
   - No `.cron` files in `orchestration/config/` (if directory exists)

Report findings in a structured summary with ✅/⚠️/❌ status for each check.
