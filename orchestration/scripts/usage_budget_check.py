#!/usr/bin/env python3
# ⚠️ DEPRECATED: This script violates SPEC constraints.
# All work must flow through agent SKILLS via DELEGATE/HANDBACK protocol.
# This file is retained for reference only and should NOT be executed directly.
#
"""
Usage Budget Manager — Real-time token budget monitoring and recommendations.

Queries current session/weekly usage limits and provides intelligent recommendations
for staying within budget while maximizing efficiency.

Usage:
  python3 usage-budget-check.py --session-used 91 --weekly-used 40
  python3 usage-budget-check.py --report  # Print full status
  python3 usage-budget-check.py --check-reset  # Check if session about to reset
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, Tuple

# Usage limits (from claude.ai /usage API)
SESSION_LIMIT_PCT = 100
WEEKLY_LIMIT_PCT = 100

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def get_budget_status(session_pct: int, weekly_pct: int) -> Dict:
    """Determine budget status and recommendations."""

    status = {
        'session_pct': session_pct,
        'weekly_pct': weekly_pct,
        'session_status': 'GREEN',
        'weekly_status': 'GREEN',
        'overall_status': 'GREEN',
    }

    # Session status
    if session_pct >= 85:
        status['session_status'] = 'RED'
    elif session_pct >= 60:
        status['session_status'] = 'YELLOW'

    # Weekly status
    if weekly_pct >= 85:
        status['weekly_status'] = 'RED'
    elif weekly_pct >= 60:
        status['weekly_status'] = 'YELLOW'

    # Overall (take most restrictive)
    if status['session_status'] == 'RED' or status['weekly_status'] == 'RED':
        status['overall_status'] = 'RED'
    elif status['session_status'] == 'YELLOW' or status['weekly_status'] == 'YELLOW':
        status['overall_status'] = 'YELLOW'

    return status


def get_model_recommendation(status: Dict) -> Tuple[str, str]:
    """Recommend model tier based on budget status."""

    if status['overall_status'] == 'RED':
        return 'haiku', 'Session/weekly budget critical. Use Haiku only.'
    elif status['overall_status'] == 'YELLOW':
        return 'sonnet', 'Budget moderate. Prefer Sonnet, use Haiku for simple tasks.'
    else:
        return 'sonnet', 'Budget green. Use best model for task complexity.'


def format_report(session_pct: int, weekly_pct: int, session_resets_in_mins: int = None) -> str:
    """Format human-readable budget report."""

    status = get_budget_status(session_pct, weekly_pct)
    model, reason = get_model_recommendation(status)

    # Color code the report
    def colorize(text: str, level: str) -> str:
        if level == 'RED':
            return Colors.RED + text + Colors.END
        elif level == 'YELLOW':
            return Colors.YELLOW + text + Colors.END
        else:
            return Colors.GREEN + text + Colors.END

    lines = []
    lines.append(Colors.BOLD + "=" * 60 + Colors.END)
    lines.append(Colors.BOLD + "Usage Budget Manager — Real-Time Report" + Colors.END)
    lines.append(Colors.BOLD + "=" * 60 + Colors.END)
    lines.append("")

    # Session status
    lines.append(f"Current Session:  {colorize(f'{session_pct}%', status['session_status'])} used")
    if session_resets_in_mins is not None:
        if session_resets_in_mins <= 1:
            lines.append(f"  → {Colors.RED}⚠️  RESETS IN {session_resets_in_mins}m{Colors.END}")
        elif session_resets_in_mins <= 5:
            lines.append(f"  → {Colors.YELLOW}⚠️  Resets in {session_resets_in_mins}m{Colors.END}")
        else:
            lines.append(f"  → Resets in {session_resets_in_mins}m")

    lines.append("")

    # Weekly status
    lines.append(f"Weekly Budget:    {colorize(f'{weekly_pct}%', status['weekly_status'])} used")
    lines.append(f"  → {100 - weekly_pct}% remaining this week")
    lines.append("")

    # Recommendation
    lines.append(Colors.BOLD + "Recommendation:" + Colors.END)
    lines.append(f"  Model: {model.upper()}")
    lines.append(f"  Reason: {reason}")
    lines.append("")

    # Action items based on status
    if status['overall_status'] == 'RED':
        lines.append(Colors.RED + "🛑 ACTION REQUIRED:" + Colors.END)
        if session_pct >= 85:
            lines.append("  1. Consider pausing for session reset (~1 min)")
            lines.append("  2. Or continue with Haiku 4.5 for 1-2 small tasks")
            lines.append("  3. Get explicit user approval before proceeding")
        if weekly_pct >= 85:
            lines.append("  • Weekly budget nearing limit (resets Tue 6:00 AM)")
            lines.append("  • Plan carefully; expensive tasks may overflow budget")
    elif status['overall_status'] == 'YELLOW':
        lines.append(Colors.YELLOW + "⚠️  STATUS: MODERATE" + Colors.END)
        lines.append("  • Bias toward Sonnet; avoid Opus unless critical")
        lines.append("  • Use Haiku for routine/well-defined tasks")
    else:
        lines.append(Colors.GREEN + "✓ GREEN LIGHT:" + Colors.END)
        lines.append("  • Use best model for task requirements")
        lines.append("  • Plan complex work with Opus if needed")

    lines.append("")
    lines.append(Colors.BOLD + "=" * 60 + Colors.END)

    return '\n'.join(lines)


def check_reset_needed(session_pct: int) -> bool:
    """Return True if session reset is approaching/recommended."""
    return session_pct >= 85


def main():
    parser = argparse.ArgumentParser(
        description='Usage Budget Manager — Token budget monitoring'
    )
    parser.add_argument(
        '--session-used',
        type=int,
        help='Session usage percentage (0-100)'
    )
    parser.add_argument(
        '--weekly-used',
        type=int,
        help='Weekly usage percentage (0-100)'
    )
    parser.add_argument(
        '--session-resets-in',
        type=int,
        help='Session resets in N minutes'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Print full status report'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output JSON instead of human-readable'
    )
    parser.add_argument(
        '--check-reset',
        action='store_true',
        help='Check if reset is recommended (exit 0=no, 1=yes)'
    )

    args = parser.parse_args()

    # Default values if not provided
    session_pct = args.session_used or 0
    weekly_pct = args.weekly_used or 0
    session_resets_in = args.session_resets_in

    if args.check_reset:
        # Return exit code for shell scripts
        sys.exit(1 if check_reset_needed(session_pct) else 0)

    if args.json:
        status = get_budget_status(session_pct, weekly_pct)
        model, reason = get_model_recommendation(status)
        status['recommended_model'] = model
        status['recommendation_reason'] = reason
        print(json.dumps(status, indent=2))
    else:
        print(format_report(session_pct, weekly_pct, session_resets_in))


if __name__ == '__main__':
    main()
