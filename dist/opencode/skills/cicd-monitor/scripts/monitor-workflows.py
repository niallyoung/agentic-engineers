#!/usr/bin/env python3
"""
CI/CD workflow monitor: Detects GitHub Actions failures, analyzes root causes,
and escalates to appropriate specialists via DELEGATE.

Usage:
    monitor-workflows.py --branch main --repo owner/repo --interval 5

Exit codes:
    0 — All workflows passing
    1 — Failures detected and DELEGATE created
    2 — Configuration or API error
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import time


class WorkflowMonitor:
    """Monitor GitHub Actions workflows for failures."""

    def __init__(self, repo: str, branch: str = "main"):
        self.repo = repo
        self.branch = branch
        self.repo_root = Path.cwd()
        
    def get_latest_workflows(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch latest workflow runs from GitHub."""
        try:
            cmd = [
                "gh", "run", "list",
                "--repo", self.repo,
                "--branch", self.branch,
                "--limit", str(limit),
                "--json", "name,status,conclusion,createdAt,headSha,url"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error fetching workflows: {e.stderr}", file=sys.stderr)
            return []

    def analyze_failure(self, workflow: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Analyze a failed workflow to extract root cause."""
        if workflow.get("conclusion") not in ["failure", "failure"]:
            return None

        run_id = workflow.get("databaseId") or workflow.get("id")
        name = workflow.get("name", "Unknown")
        
        # Fetch detailed logs
        try:
            cmd = [
                "gh", "run", "view", str(run_id),
                "--repo", self.repo,
                "--log"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            logs = result.stdout
        except Exception as e:
            logs = f"(Could not fetch logs: {e})"

        # Classify error type
        error_type = "unknown"
        if "FAILED" in logs or "failed" in logs:
            if "test" in logs.lower():
                error_type = "test_failure"
            elif "build" in logs.lower() or "compile" in logs.lower():
                error_type = "build_failure"
            elif "lint" in logs.lower() or "format" in logs.lower():
                error_type = "lint_failure"
            elif "security" in logs.lower():
                error_type = "security_failure"
        
        # Extract first error line
        error_detail = "Unknown error"
        for line in logs.split("\n"):
            if "error" in line.lower() or "failed" in line.lower():
                error_detail = line.strip()[:200]  # First 200 chars
                break

        return {
            "workflow_name": name,
            "error_type": error_type,
            "error_detail": error_detail,
            "logs": logs[:500],  # Truncate for DELEGATE
            "run_url": workflow.get("url", "")
        }

    def route_specialist(self, error_type: str) -> str:
        """Route failure to appropriate specialist."""
        routing = {
            "build_failure": "Senior Engineer",
            "test_failure": "Quality Engineer",
            "lint_failure": "Engineer",
            "security_failure": "Security Engineer",
            "deploy_failure": "Principal Engineer",
            "unknown": "Senior Engineer",
        }
        return routing.get(error_type, "Senior Engineer")

    def create_delegate(self, workflow: Dict[str, Any], analysis: Dict[str, str]) -> bool:
        """Create a DELEGATE for fixing the workflow failure."""
        specialist = self.route_specialist(analysis["error_type"])
        
        delegate_content = f"""---
task_id: fix-ci-{int(time.time())}
title: "Fix {analysis['workflow_name']} failure on {self.branch}"
task_type: bug
severity: high
root_cause: |
  {analysis['error_type'].replace('_', ' ').title()}
  {analysis['error_detail']}
  
  Workflow URL: {analysis['run_url']}
  
  Error logs (truncated):
  {analysis['logs']}
assigned_to: {specialist}
fix_strategy: |
  1. Analyze the workflow logs
  2. Identify root cause
  3. Make targeted fix
  4. Re-run workflow to verify
expected_outcome: All checks passing
created_at: {datetime.now().isoformat()}
retry_count: 1
max_retries: 3
next_check_at: {(datetime.now() + timedelta(minutes=5)).isoformat()}
"""
        
        # Write to queue
        queue_dir = Path.home() / ".copilot" / "queue" / "incoming"
        queue_dir.mkdir(parents=True, exist_ok=True)
        
        delegate_file = queue_dir / f"fix-ci-{int(time.time())}.yaml"
        delegate_file.write_text(delegate_content)
        
        print(f"✅ Created DELEGATE: {delegate_file}")
        return True

    def monitor(self, verbose: bool = False) -> int:
        """Run workflow monitoring."""
        if verbose:
            print(f"🔍 Monitoring workflows for {self.repo}/{self.branch}")
        
        workflows = self.get_latest_workflows()
        if not workflows:
            print("⚠️  No workflows found")
            return 2

        failures = []
        for workflow in workflows:
            if workflow.get("conclusion") == "failure":
                analysis = self.analyze_failure(workflow)
                if analysis:
                    failures.append((workflow, analysis))
                    if verbose:
                        print(f"❌ {workflow['name']}: {analysis['error_type']}")

        if not failures:
            print(f"✅ All {len(workflows)} recent workflows passing")
            return 0

        # Escalate failures
        print(f"⚠️  Found {len(failures)} failing workflows. Creating DELEGATEs...")
        for workflow, analysis in failures:
            self.create_delegate(workflow, analysis)

        return 1


def main():
    parser = argparse.ArgumentParser(description="Monitor CI/CD workflows for failures")
    parser.add_argument("--branch", default="main", help="Branch to monitor")
    parser.add_argument("--repo", help="Repository (owner/repo)")
    parser.add_argument("--interval", type=int, default=5, help="Check interval (minutes)")
    parser.add_argument("--retries", type=int, default=3, help="Max retries before escalation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()

    # Infer repo if not provided
    if not args.repo:
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True
            )
            # Extract owner/repo from git URL
            git_url = result.stdout.strip()
            if "github.com" in git_url:
                parts = git_url.split("/")
                args.repo = f"{parts[-2]}/{parts[-1].replace('.git', '')}"
        except:
            print("❌ Could not infer repository. Use --repo owner/repo", file=sys.stderr)
            return 2

    monitor = WorkflowMonitor(args.repo, args.branch)
    return monitor.monitor(verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
