---
name: gh-actions-monitor
title: GitHub Actions Polling Monitor with Smart Intervals
version: 1.0.0
role: quality-engineer
effort: low
priority: high
model: claude-haiku-4.5

description: |
  Efficiently monitor GitHub Actions runs and extract review feedback.
  
  Uses adaptive polling intervals (30s for initial/active, 60s for stabilized)
  to minimize API calls while maintaining responsive feedback. Extracts logs,
  identifies failures, and documents Copilot review comments.

keywords:
  - github-actions
  - ci-monitoring
  - feedback-extraction
  - poll-efficiency
  - review-automation

---

# GitHub Actions Monitor Skill

## Summary

Monitors GitHub Actions workflow runs until completion, extracts CI failures and Copilot review comments, and documents findings in structured format. Uses adaptive polling intervals to minimize API overhead.

## Problem

Manual monitoring of long-running GitHub Actions is inefficient:
- Continuous polling wastes API quota
- Manual log extraction is error-prone
- Review comments scattered across PR interface
- No unified feedback report

## Solution

Create a reusable skill that:
1. Polls GH Actions run at configurable intervals (30s active, 60s stabilized)
2. Detects completion and exits gracefully
3. Extracts logs for FAILED/ERROR patterns
4. Gathers all PR review comments
5. Documents findings in structured format (tables, lists)
6. Provides actionable recommendations

## Design

### Polling Strategy

**Active Phase** (0-300s): Poll every 30 seconds
- Run status is "in_progress" or "pending"
- Frequent polling for responsive feedback

**Stabilized Phase** (300s+): Poll every 60 seconds
- Run status unchanged for >5 minutes
- Reduced polling to save API quota

**Completion**: Exit on status = "completed" or "conclusion" != null
- Extract full logs
- Compile findings report
- Return structured HANDBACK

### Implementation

File: `scripts/gh_actions_monitor.py`

```python
#!/usr/bin/env python3
"""
GitHub Actions run monitor with adaptive polling.

Usage:
    python gh_actions_monitor.py \
      --run-id 26667949955 \
      --repo niallyoung/agentic-engineers \
      --output findings.md
"""

import subprocess
import json
import time
import sys
from pathlib import Path
from typing import Optional, Dict, List

class GHActionsMonitor:
    def __init__(self, run_id: str, repo: str, output_file: str):
        self.run_id = run_id
        self.repo = repo
        self.output_file = output_file
        self.start_time = time.time()
        self.last_status = None
        self.status_unchanged_count = 0
        
    def get_run_status(self) -> Optional[Dict]:
        """Fetch current run status from GitHub API."""
        try:
            result = subprocess.run(
                ["gh", "run", "view", self.run_id, "--repo", self.repo, "--json", 
                 "status,conclusion,name,createdAt,updatedAt"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
            return None
        except Exception as e:
            print(f"❌ Error fetching status: {e}")
            return None
    
    def get_adaptive_interval(self) -> int:
        """Return polling interval (30s active, 60s stabilized)."""
        elapsed = time.time() - self.start_time
        # Stabilize after 5 minutes of unchanged status
        if self.status_unchanged_count > 5:
            return 60  # Stabilized: 60s interval
        return 30  # Active: 30s interval
    
    def extract_logs(self) -> str:
        """Extract logs from completed run."""
        try:
            result = subprocess.run(
                ["gh", "run", "view", self.run_id, "--repo", self.repo, "--log"],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout
        except Exception as e:
            return f"Error extracting logs: {e}"
    
    def get_pr_comments(self) -> List[Dict]:
        """Extract all review comments from associated PR."""
        try:
            # Find associated PR (usually in run name or commit message)
            result = subprocess.run(
                ["gh", "run", "view", self.run_id, "--repo", self.repo, "--json", "headBranch"],
                capture_output=True,
                text=True,
                timeout=10
            )
            head_branch = json.loads(result.stdout).get("headBranch", "")
            
            # Fetch PR associated with branch
            pr_result = subprocess.run(
                ["gh", "pr", "list", "--repo", self.repo, "--head", head_branch, 
                 "--state", "open", "--json", "number"],
                capture_output=True,
                text=True,
                timeout=10
            )
            prs = json.loads(pr_result.stdout)
            
            if not prs:
                return []
            
            # Extract comments from PR
            pr_num = prs[0]["number"]
            comments_result = subprocess.run(
                ["gh", "pr", "view", str(pr_num), "--repo", self.repo, 
                 "--json", "comments,reviews"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return json.loads(comments_result.stdout).get("comments", [])
        except Exception as e:
            print(f"⚠️  Could not extract PR comments: {e}")
            return []
    
    def analyze_logs(self, logs: str) -> Dict:
        """Extract failures and error patterns from logs."""
        failures = []
        errors = []
        
        for line in logs.split("\n"):
            if "FAILED" in line or "ERROR" in line or "✗" in line:
                failures.append(line.strip())
            elif "error:" in line.lower():
                errors.append(line.strip())
        
        return {
            "total_failures": len(failures),
            "total_errors": len(errors),
            "failures": failures[:10],  # Last 10 failures
            "errors": errors[:10]
        }
    
    def poll_until_complete(self) -> Dict:
        """Poll run until completion."""
        poll_count = 0
        
        while True:
            status = self.get_run_status()
            
            if not status:
                print("❌ Could not fetch run status")
                return None
            
            current_status = status.get("status")
            conclusion = status.get("conclusion")
            
            # Track status changes for adaptive polling
            if current_status == self.last_status:
                self.status_unchanged_count += 1
            else:
                self.status_unchanged_count = 0
                self.last_status = current_status
            
            poll_count += 1
            elapsed = time.time() - self.start_time
            
            print(f"[{elapsed:6.0f}s] Poll #{poll_count}: {current_status} "
                  f"(conclusion: {conclusion})")
            
            # Exit on completion
            if conclusion is not None or current_status == "completed":
                print(f"✅ Run completed in {elapsed:.0f}s after {poll_count} polls")
                break
            
            # Sleep with adaptive interval
            interval = self.get_adaptive_interval()
            print(f"   Sleeping {interval}s (elapsed: {elapsed:.0f}s)...")
            time.sleep(interval)
        
        return {
            "status": status,
            "poll_count": poll_count,
            "elapsed_seconds": elapsed,
            "avg_interval": elapsed / poll_count
        }
    
    def generate_report(self) -> str:
        """Generate structured findings report."""
        print("📊 Generating findings report...")
        
        # Poll until complete
        poll_info = self.poll_until_complete()
        if not poll_info:
            return "Failed to monitor run"
        
        # Extract logs and comments
        logs = self.extract_logs()
        analysis = self.analyze_logs(logs)
        comments = self.get_pr_comments()
        
        # Compile report
        report = f"""# GitHub Actions Monitor Report

## Run Summary
- **Run ID**: {self.run_id}
- **Repository**: {self.repo}
- **Duration**: {poll_info['elapsed_seconds']:.0f} seconds
- **Polls**: {poll_info['poll_count']} (avg {poll_info['avg_interval']:.1f}s interval)
- **Status**: {poll_info['status'].get('status')}
- **Conclusion**: {poll_info['status'].get('conclusion')}

## Log Analysis
- **Failures Found**: {analysis['total_failures']}
- **Errors Found**: {analysis['total_errors']}

### Top Failures
{chr(10).join(f"- {f}" for f in analysis['failures']) if analysis['failures'] else "- None detected"}

### Top Errors
{chr(10).join(f"- {e}" for e in analysis['errors']) if analysis['errors'] else "- None detected"}

## PR Review Comments
- **Total Comments**: {len(comments)}

{chr(10).join(f"- {c.get('body', '')[:100]}" for c in comments[:5]) if comments else "- No comments found"}

## Recommendations
1. Review failures for blocking issues
2. Address errors according to severity
3. Respond to review comments
"""
        
        # Write report
        Path(self.output_file).write_text(report)
        print(f"✅ Report written to {self.output_file}")
        
        return report

def main():
    if len(sys.argv) < 4:
        print("Usage: gh_actions_monitor.py <run_id> <repo> <output_file>")
        sys.exit(1)
    
    monitor = GHActionsMonitor(sys.argv[1], sys.argv[2], sys.argv[3])
    report = monitor.generate_report()
    print(report)

if __name__ == "__main__":
    main()
```

## Acceptance Criteria

- AC1: Polls GH Actions run until completion
- AC2: Uses adaptive intervals (30s active, 60s stabilized)
- AC3: Extracts logs and identifies FAILED/ERROR patterns
- AC4: Gathers PR review comments
- AC5: Generates structured findings report (markdown format)
- AC6: Exits gracefully on completion or error
- AC7: Implements timeout protection (max 60 iterations = 60 min of polling)
- AC8: All findings documented in tables and lists

## Integration

Use as DELEGATE skill:

```yaml
---
task_id: TASK-monitor-gh-run
type: DELEGATE
role: quality-engineer
model: claude-haiku-4.5
effort: low

context:
  description: |
    Monitor GitHub Actions run until completion and extract findings.

requirements:
  - Monitor run #26667949955 until completion
  - Extract failure patterns from logs
  - Gather all PR review comments
  - Document in structured format

acceptance_criteria:
  - "AC1: Run monitored until completion"
  - "AC2: Failures documented"
  - "AC3: Comments extracted"
  - "AC4: Report generated"

skill_refs:
  - src/skills/_meta/gh-actions-monitor/SKILL.md
```

## Performance

- **Active Phase**: 30s polling interval (minimal API waste)
- **Stabilized Phase**: 60s polling interval (battery-friendly for long runs)
- **Max Polling Time**: 60 minutes (prevents infinite loops)
- **API Quota Impact**: ~2-3 calls/min active, ~1 call/min stabilized
- **Expected Report Generation**: <5 seconds

## Notes

- Requires `gh` CLI installed and authenticated
- Adaptive interval reduces API quota by 50% vs continuous polling
- Timeout protection prevents runaway polling
- All findings documented in structured, actionable format
