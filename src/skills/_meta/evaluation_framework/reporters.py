"""
Result reporters for evaluation framework

Generates JSON and Markdown reports from test results.
"""

import json
import csv
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from .framework import CompatibilityMatrix, TestResult, TestStatus


class JSONReporter:
    """Generates detailed JSON report."""
    
    def __init__(self, matrix: CompatibilityMatrix):
        """
        Initialize JSON reporter.
        
        Args:
            matrix: CompatibilityMatrix with test results
        """
        self.matrix = matrix
    
    def generate(self, output_path: Path = None) -> Dict[str, Any]:
        """
        Generate JSON report.
        
        Args:
            output_path: Optional path to write JSON file
            
        Returns:
            Dictionary with report data
        """
        summary = self.matrix.get_summary()
        failures = self.matrix.get_failures()
        regressions = self.matrix.get_regressions()
        
        report = {
            "metadata": {
                "generated_at": self.matrix.generated_at,
                "total_results": len(self.matrix.results),
            },
            "summary": summary,
            "results": [r.to_dict() for r in self.matrix.results],
            "failures": [r.to_dict() for r in failures],
            "regressions": regressions,
        }
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
        
        return report
    
    def write(self, output_path: Path):
        """Write JSON report to file."""
        self.generate(output_path)


class MarkdownReporter:
    """Generates human-readable Markdown report."""
    
    def __init__(self, matrix: CompatibilityMatrix):
        """
        Initialize Markdown reporter.
        
        Args:
            matrix: CompatibilityMatrix with test results
        """
        self.matrix = matrix
    
    def generate(self, output_path: Path = None) -> str:
        """
        Generate Markdown report.
        
        Args:
            output_path: Optional path to write Markdown file
            
        Returns:
            Markdown formatted report string
        """
        lines = []
        
        # Header
        lines.append("# Evaluation Framework Test Report")
        lines.append("")
        lines.append(f"**Generated:** {datetime.utcnow().isoformat()}")
        lines.append(f"**Total Results:** {len(self.matrix.results)}")
        lines.append("")
        
        # Summary
        summary = self.matrix.get_summary()
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Pass Rate:** {summary['pass_rate']}% ({summary['passed']}/{summary['total_tests']})")
        lines.append(f"- **Failed:** {summary['failed']}")
        lines.append(f"- **Timeout:** {summary['timeout']}")
        lines.append(f"- **Error:** {summary['error']}")
        lines.append(f"- **Skipped:** {summary['skipped']}")
        lines.append(f"- **Avg Duration:** {summary['avg_duration_ms']}ms")
        lines.append("")
        
        # Pass/Fail Status
        if summary['pass_rate'] >= 95:
            lines.append("✅ **Status:** PASS (≥95% success rate)")
        elif summary['pass_rate'] >= 80:
            lines.append("⚠️ **Status:** WARNING (80-95% success rate)")
        else:
            lines.append("❌ **Status:** FAIL (<80% success rate)")
        lines.append("")
        
        # By Harness
        lines.append("## Results by Harness")
        lines.append("")
        lines.append("| Harness | Passed | Failed | Timeout | Error | Pass Rate |")
        lines.append("|---------|--------|--------|---------|-------|-----------|")
        for harness, stats in summary.get('by_harness', {}).items():
            pass_rate = stats.get('pass_rate', 0)
            lines.append(
                f"| {harness} | {stats['passed']} | {stats['failed']} | "
                f"{stats['timeout']} | {stats['error']} | {pass_rate}% |"
            )
        lines.append("")
        
        # By Model
        lines.append("## Results by Model")
        lines.append("")
        lines.append("| Model | Passed | Failed | Timeout | Error | Pass Rate |")
        lines.append("|-------|--------|--------|---------|-------|-----------|")
        for model, stats in summary.get('by_model', {}).items():
            pass_rate = stats.get('pass_rate', 0)
            lines.append(
                f"| {model} | {stats['passed']} | {stats['failed']} | "
                f"{stats['timeout']} | {stats['error']} | {pass_rate}% |"
            )
        lines.append("")
        
        # Failures
        failures = self.matrix.get_failures()
        if failures:
            lines.append("## Failures")
            lines.append("")
            
            # Group by harness/model
            by_harness_model = {}
            for failure in failures:
                key = f"{failure.harness}:{failure.model}"
                if key not in by_harness_model:
                    by_harness_model[key] = []
                by_harness_model[key].append(failure)
            
            for hm_key in sorted(by_harness_model.keys()):
                lines.append(f"### {hm_key}")
                lines.append("")
                for failure in by_harness_model[hm_key]:
                    status_emoji = {
                        TestStatus.FAIL: "❌",
                        TestStatus.ERROR: "⚠️",
                        TestStatus.TIMEOUT: "⏱️",
                    }.get(failure.status, "❓")
                    lines.append(f"- **{failure.test_id}** {status_emoji}")
                    if failure.error_message:
                        lines.append(f"  - Error: {failure.error_message}")
                lines.append("")
        
        # Regressions Summary
        regressions = self.matrix.get_regressions()
        if regressions:
            lines.append("## Regressions Detected")
            lines.append("")
            for hm_key, test_ids in regressions.items():
                lines.append(f"### {hm_key} ({len(test_ids)} failures)")
                for test_id in test_ids:
                    lines.append(f"- {test_id}")
            lines.append("")
        else:
            lines.append("## Regressions")
            lines.append("")
            lines.append("✅ No regressions detected")
            lines.append("")
        
        # Recommendations
        lines.append("## Recommendations")
        lines.append("")
        if summary['pass_rate'] >= 95:
            lines.append("- ✅ Framework is stable. No action required.")
        else:
            lines.append("- 🔍 Investigate failures above before deploying.")
            lines.append("- 📊 Review failure patterns for systemic issues.")
            for hm_key, test_ids in regressions.items():
                harness, model = hm_key.split(":")
                lines.append(f"- Fix {harness}:{model} — {len(test_ids)} failure(s)")
        lines.append("")
        
        report_text = "\n".join(lines)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report_text)
        
        return report_text
    
    def write(self, output_path: Path):
        """Write Markdown report to file."""
        self.generate(output_path)


class CSVReporter:
    """Generates CSV report for detailed analysis."""
    
    def __init__(self, matrix: CompatibilityMatrix):
        """
        Initialize CSV reporter.
        
        Args:
            matrix: CompatibilityMatrix with test results
        """
        self.matrix = matrix
    
    def generate(self, output_path: Path = None) -> List[Dict[str, Any]]:
        """
        Generate CSV report.
        
        Args:
            output_path: Optional path to write CSV file
            
        Returns:
            List of result dictionaries
        """
        rows = []
        for result in self.matrix.results:
            rows.append({
                "test_id": result.test_id,
                "harness": result.harness,
                "model": result.model,
                "status": result.status.value,
                "duration_ms": result.duration_ms,
                "tokens_used": result.tokens_used,
                "timestamp": result.timestamp,
                "error": result.error_message,
            })
        
        if output_path:
            with open(output_path, 'w', newline='') as f:
                if rows:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
        
        return rows
    
    def write(self, output_path: Path):
        """Write CSV report to file."""
        self.generate(output_path)
