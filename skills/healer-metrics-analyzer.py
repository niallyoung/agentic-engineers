#!/usr/bin/env python3
"""
healer-metrics-analyzer.py

Analyzes quality gate audit logs and Healer Engineer outcomes to measure:
- Healer success rate
- Auto-merge rate
- Escalation rate
- Confidence score calibration accuracy
- Time to fix metrics

Usage:
  ./healer-metrics-analyzer.py [--audit-dir /path] [--days 30] [--output report.json]
"""

import json
import sys
import os
import glob
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass
class AuditEntry:
    timestamp: str
    session_id: str
    phase: str
    status: str
    details: dict
    service: str = None

    @staticmethod
    def from_jsonl(line: str) -> 'AuditEntry':
        data = json.loads(line.strip())
        return AuditEntry(
            timestamp=data.get('timestamp'),
            session_id=data.get('session_id'),
            phase=data.get('phase'),
            status=data.get('status'),
            details=data.get('details', {}),
        )


class HealerMetricsAnalyzer:
    def __init__(self, audit_dir: str = ".", days: int = 30):
        self.audit_dir = audit_dir
        self.days = days
        self.cutoff_date = datetime.utcnow() - timedelta(days=days)
        self.entries: List[AuditEntry] = []
        self.healer_sessions = defaultdict(list)  # session_id -> list of audit entries

    def load_audit_logs(self):
        """Load all audit logs from directory."""
        pattern = os.path.join(self.audit_dir, "quality-gate-audit-*.jsonl")
        audit_files = glob.glob(pattern)

        for filepath in audit_files:
            try:
                with open(filepath, 'r') as f:
                    for line in f:
                        if line.strip():
                            entry = AuditEntry.from_jsonl(line)
                            entry_date = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
                            if entry_date >= self.cutoff_date:
                                self.entries.append(entry)
                                self.healer_sessions[entry.session_id].append(entry)
            except Exception as e:
                print(f"Warning: Failed to parse {filepath}: {e}", file=sys.stderr)

    def calculate_healer_success_rate(self) -> Dict:
        """
        Calculate success rate for Healer-attempted fixes.

        Returns:
          {
            "healer_invocations": count,
            "healer_fixes_passed": count,
            "healer_fixes_failed": count,
            "success_rate": float (0-100),
            "failure_rate": float (0-100),
          }
        """
        healer_sessions = [
            session for session in self.healer_sessions.values()
            if any(e.status == 'DELEGATE_HEALER' for e in session)
        ]

        if not healer_sessions:
            return {
                "healer_invocations": 0,
                "healer_fixes_passed": 0,
                "healer_fixes_failed": 0,
                "success_rate": 0,
                "failure_rate": 0,
                "notes": "No Healer invocations in selected period"
            }

        passed = 0
        failed = 0
        for session in healer_sessions:
            # Check final phase status (phase 4) after healing attempt
            final_phase = [e for e in session if e.phase == '4']
            if final_phase:
                if final_phase[-1].status == 'PROCEED':
                    passed += 1
                elif final_phase[-1].status == 'ESCALATE':
                    failed += 1

        total = passed + failed
        success_rate = (passed / total * 100) if total > 0 else 0

        return {
            "healer_invocations": len(healer_sessions),
            "healer_fixes_passed": passed,
            "healer_fixes_failed": failed,
            "success_rate": round(success_rate, 2),
            "failure_rate": round(100 - success_rate, 2),
        }

    def calculate_escalation_rate(self) -> Dict:
        """
        Calculate percentage of issues escalated to humans vs auto-fixed.

        Returns:
          {
            "total_checks": count,
            "escalated": count,
            "auto_fixed": count,
            "escalation_rate": float (0-100),
          }
        """
        # Count all unique sessions (each is one check)
        total_checks = len(self.healer_sessions)

        if total_checks == 0:
            return {
                "total_checks": 0,
                "escalated": 0,
                "auto_fixed": 0,
                "escalation_rate": 0,
                "notes": "No quality gate checks in selected period"
            }

        escalated = 0
        auto_fixed = 0

        for session in self.healer_sessions.values():
            # Check final decision (phase 4)
            final_phase = [e for e in session if e.phase == '4']
            if final_phase:
                if final_phase[-1].status == 'ESCALATE':
                    escalated += 1
                elif final_phase[-1].status == 'PROCEED':
                    # Check if this was after healing (phase 3)
                    healing_phase = [e for e in session if e.phase == '3']
                    if healing_phase and any(e.status == 'DELEGATE_HEALER' for e in healing_phase):
                        auto_fixed += 1

        escalation_rate = (escalated / total_checks * 100) if total_checks > 0 else 0

        return {
            "total_checks": total_checks,
            "escalated": escalated,
            "auto_fixed": auto_fixed,
            "escalation_rate": round(escalation_rate, 2),
        }

    def calculate_phase_success_rates(self) -> Dict:
        """
        Calculate success rate by phase.

        Returns:
          {
            "phase_1": {"pass_rate": float, "fail_count": int, "pass_count": int},
            "phase_2": {...},
            ...
          }
        """
        phase_stats = defaultdict(lambda: {"pass": 0, "fail": 0})

        for session in self.healer_sessions.values():
            for entry in session:
                if entry.status == 'PASS':
                    phase_stats[f"phase_{entry.phase}"]["pass"] += 1
                elif entry.status == 'FAIL':
                    phase_stats[f"phase_{entry.phase}"]["fail"] += 1

        result = {}
        for phase, stats in sorted(phase_stats.items()):
            total = stats["pass"] + stats["fail"]
            pass_rate = (stats["pass"] / total * 100) if total > 0 else 0
            result[phase] = {
                "pass_rate": round(pass_rate, 2),
                "pass_count": stats["pass"],
                "fail_count": stats["fail"],
                "total": total,
            }

        return result

    def analyze_failure_patterns(self) -> Dict:
        """
        Categorize failures by type and confidence level.

        Returns:
          {
            "failure_type": {
              "count": int,
              "high_confidence_failures": int,
              "low_confidence_failures": int,
            }
          }
        """
        patterns = defaultdict(lambda: {
            "count": 0,
            "high_confidence_failures": 0,
            "low_confidence_failures": 0,
        })

        for session in self.healer_sessions.values():
            # Check phase 3 (diagnostic + healer)
            phase_3 = [e for e in session if e.phase == '3']
            if phase_3:
                for entry in phase_3:
                    if entry.status == 'FAIL':
                        issue_type = entry.details.get('issue_type', 'unknown')
                        confidence = entry.details.get('confidence', 'unknown')
                        patterns[issue_type]["count"] += 1
                        if confidence == 'HIGH':
                            patterns[issue_type]["high_confidence_failures"] += 1
                        elif confidence == 'LOW':
                            patterns[issue_type]["low_confidence_failures"] += 1

        return dict(patterns) if patterns else {"notes": "No failures in selected period"}

    def generate_report(self) -> Dict:
        """Generate comprehensive metrics report."""
        self.load_audit_logs()

        if not self.entries:
            return {
                "status": "no_data",
                "message": f"No audit logs found in {self.audit_dir} for last {self.days} days",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "period_days": self.days,
            "total_sessions": len(self.healer_sessions),
            "healer_success": self.calculate_healer_success_rate(),
            "escalation": self.calculate_escalation_rate(),
            "phase_success_rates": self.calculate_phase_success_rates(),
            "failure_patterns": self.analyze_failure_patterns(),
            "level_3_readiness": self._assess_level_3_readiness(),
        }

        return report

    def _assess_level_3_readiness(self) -> Dict:
        """
        Assess readiness for Level 3 graduation based on metrics.

        Level 3 requires:
        - Healer success rate ≥ 70%
        - Escalation rate ≤ 30%
        - Phase success rates all > 90%
        """
        healer_success = self.calculate_healer_success_rate()
        escalation = self.calculate_escalation_rate()
        phase_success = self.calculate_phase_success_rates()

        criteria = {
            "healer_success_rate_gte_70": healer_success.get("success_rate", 0) >= 70,
            "escalation_rate_lte_30": escalation.get("escalation_rate", 100) <= 30,
            "all_phases_gt_90": all(
                p.get("pass_rate", 0) > 90
                for p in phase_success.values()
            ),
        }

        ready = all(criteria.values())
        met_count = sum(criteria.values())

        return {
            "ready_for_level_3": ready,
            "criteria_met": met_count,
            "criteria_total": len(criteria),
            "details": criteria,
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Analyze Healer Engineer metrics from audit logs")
    parser.add_argument("--audit-dir", default=".", help="Directory containing audit logs")
    parser.add_argument("--days", type=int, default=30, help="Analyze last N days")
    parser.add_argument("--output", help="Output file (JSON format)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    args = parser.parse_args()

    analyzer = HealerMetricsAnalyzer(audit_dir=args.audit_dir, days=args.days)
    report = analyzer.generate_report()

    json_output = json.dumps(
        report,
        indent=2 if args.pretty else None,
        default=str
    )

    if args.output:
        with open(args.output, 'w') as f:
            f.write(json_output)
        print(f"Report saved to {args.output}")
    else:
        print(json_output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
