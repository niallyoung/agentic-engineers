#!/usr/bin/env python3
"""
GitHub Actions run monitor with adaptive polling (30s/60s intervals).

Usage:
    python gh_actions_monitor.py \
      --run-id 26667949955 \
      --repo niallyoung/agentic-engineers \
      --output /tmp/findings.md
"""

import subprocess
import json
import time
import sys
import argparse
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
        # Stabilize after 5 consecutive unchanged status checks
        if self.status_unchanged_count >= 5:
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
            return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
        except Exception as e:
            return f"Error extracting logs: {e}"
    
    def get_pr_comments(self) -> List[Dict]:
        """Extract all review comments from associated PR."""
        try:
            # Find associated PR via head branch
            result = subprocess.run(
                ["gh", "run", "view", self.run_id, "--repo", self.repo, "--json", "headBranch"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                return []
            
            head_branch = json.loads(result.stdout).get("headBranch", "")
            if not head_branch:
                return []
            
            # Fetch PR associated with branch
            pr_result = subprocess.run(
                ["gh", "pr", "list", "--repo", self.repo, "--head", head_branch, 
                 "--state", "open", "--json", "number"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if pr_result.returncode != 0:
                return []
            
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
            
            if comments_result.returncode == 0:
                data = json.loads(comments_result.stdout)
                return data.get("comments", [])
            return []
        except Exception as e:
            print(f"⚠️  Could not extract PR comments: {e}")
            return []
    
    def analyze_logs(self, logs: str) -> Dict:
        """Extract failures and error patterns from logs."""
        failures = []
        errors = []
        
        for line in logs.split("\n"):
            if "error:" in line.lower():
                errors.append(line.strip())
            elif "FAILED" in line or "✗" in line:
                failures.append(line.strip())
        
        return {
            "total_failures": len(failures),
            "total_errors": len(errors),
            "failures": failures[:10],
            "errors": errors[:10]
        }
    
    def poll_until_complete(self, max_iterations: int = 120) -> Optional[Dict]:
        """Poll run until completion (max 120 iterations = ~2 hours)."""
        poll_count = 0
        
        while poll_count < max_iterations:
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
            interval = self.get_adaptive_interval()
            
            status_str = f"status={current_status}, conclusion={conclusion}"
            print(f"[{elapsed:7.0f}s] Poll #{poll_count:3d}: {status_str} "
                  f"(next interval: {interval}s)")
            
            # Exit on completion
            if conclusion is not None or current_status == "completed":
                print(f"✅ Run completed in {elapsed:.0f}s after {poll_count} polls "
                      f"(avg {elapsed/poll_count:.1f}s/poll)")
                return {
                    "status": status,
                    "poll_count": poll_count,
                    "elapsed_seconds": int(elapsed),
                    "avg_interval": elapsed / poll_count
                }
            
            # Sleep with adaptive interval
            time.sleep(interval)
        
        print(f"⏱️  Polling timeout: {max_iterations} iterations reached")
        return {
            "status": status,
            "poll_count": poll_count,
            "elapsed_seconds": int(time.time() - self.start_time),
            "timeout": True
        }
    
    def generate_report(self) -> str:
        """Generate structured findings report."""
        print("📊 Generating findings report...\n")
        
        # Poll until complete
        poll_info = self.poll_until_complete()
        if not poll_info:
            return "Failed to monitor run"
        
        # Extract logs and comments
        print("\n📋 Extracting logs...")
        logs = self.extract_logs()
        analysis = self.analyze_logs(logs)
        
        print("💬 Extracting PR comments...")
        comments = self.get_pr_comments()
        
        # Compile report
        timeout_note = "\n⚠️  **TIMEOUT**: Polling reached max iterations" if poll_info.get("timeout") else ""
        
        report = f"""# GitHub Actions Monitor Report

## Run Summary
- **Run ID**: {self.run_id}
- **Repository**: {self.repo}
- **Duration**: {poll_info['elapsed_seconds']} seconds
- **Polls**: {poll_info['poll_count']} (avg {poll_info['avg_interval']:.1f}s/poll)
- **Status**: {poll_info['status'].get('status', 'unknown')}
- **Conclusion**: {poll_info['status'].get('conclusion', 'pending')}{timeout_note}

## Log Analysis
- **Failures Found**: {analysis['total_failures']}
- **Errors Found**: {analysis['total_errors']}

### Sample Failures
```
{chr(10).join(analysis['failures']) if analysis['failures'] else '(None detected)'}
```

### Sample Errors
```
{chr(10).join(analysis['errors']) if analysis['errors'] else '(None detected)'}
```

## PR Review Comments
- **Total Comments**: {len(comments)}

{f'''### Comments
```
{chr(10).join(f"- {c.get('author', {{}}).get('login', 'unknown')}: {c.get('body', '')[:80]}" for c in comments[:10])}
```''' if comments else '(No comments found)'}

## Recommendations
1. Review any failures for blocking issues
2. Address errors according to severity
3. Respond to review comments
4. Re-run if transient failure detected
"""
        
        # Write report
        Path(self.output_file).write_text(report)
        print(f"\n✅ Report written to {self.output_file}")
        
        return report

def main():
    parser = argparse.ArgumentParser(
        description="Monitor GitHub Actions run with adaptive polling"
    )
    parser.add_argument("--run-id", required=True, help="GitHub Actions run ID")
    parser.add_argument("--repo", required=True, help="Repository (owner/name)")
    parser.add_argument("--output", required=True, help="Output file for findings")
    
    args = parser.parse_args()
    
    monitor = GHActionsMonitor(args.run_id, args.repo, args.output)
    report = monitor.generate_report()
    print("\n" + "="*70)
    print(report)
    print("="*70)

if __name__ == "__main__":
    main()
