#!/usr/bin/env python3
# ⚠️ DEPRECATED: This script violates SPEC constraints.
# All work must flow through agent SKILLS via DELEGATE/HANDBACK protocol.
# This file is retained for reference only and should NOT be executed directly.
#
"""Analyze token usage history for trends and patterns."""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import statistics

def load_history(history_file):
    """Load JSON Lines history file."""
    entries = []
    if not Path(history_file).exists():
        return entries

    try:
        with open(history_file, 'r') as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
    except (json.JSONDecodeError, IOError) as e:
        print(f"ERROR: Failed to load history: {e}", file=sys.stderr)
        return []

    return entries

def analyze_usage(entries):
    """Analyze usage trends."""
    if not entries:
        return None

    # Parse ISO format timestamps (handle 'Z' suffix for UTC)
    timestamps = [datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')) for e in entries]
    session_pcts = [e['session_usage_pct'] for e in entries]
    weekly_pcts = [e['weekly_usage_pct'] for e in entries]

    analysis = {
        'total_samples': len(entries),
        'time_span': {
            'start': timestamps[0].isoformat(),
            'end': timestamps[-1].isoformat(),
            'duration_hours': round((timestamps[-1] - timestamps[0]).total_seconds() / 3600, 2),
        },
        'session': {
            'current': session_pcts[-1],
            'min': min(session_pcts),
            'max': max(session_pcts),
            'avg': round(statistics.mean(session_pcts), 1),
            'trend': 'rising' if session_pcts[-1] > session_pcts[0] else 'falling',
        },
        'weekly': {
            'current': weekly_pcts[-1],
            'min': min(weekly_pcts),
            'max': max(weekly_pcts),
            'avg': round(statistics.mean(weekly_pcts), 1),
            'trend': 'rising' if weekly_pcts[-1] > weekly_pcts[0] else 'falling',
        },
    }

    # Calculate velocity (change per hour)
    if len(entries) > 1:
        hours = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
        if hours > 0:
            session_velocity = (session_pcts[-1] - session_pcts[0]) / hours
            weekly_velocity = (weekly_pcts[-1] - weekly_pcts[0]) / hours
            analysis['session']['pct_per_hour'] = round(session_velocity, 3)
            analysis['weekly']['pct_per_hour'] = round(weekly_velocity, 3)

            # Estimate time to reset
            if session_velocity > 0:
                hours_to_reset = (100 - session_pcts[-1]) / session_velocity
                if hours_to_reset > 0:
                    analysis['session']['estimated_reset_in_hours'] = round(hours_to_reset, 1)

    return analysis

def print_report(analysis):
    """Pretty-print analysis report."""
    if not analysis:
        print("No usage data captured yet. Run: usage-budget capture")
        return

    print("╔════════════════════════════════════════════════════╗")
    print("║         TOKEN USAGE TRENDS & ANALYSIS              ║")
    print("╚════════════════════════════════════════════════════╝\n")

    print(f"Samples: {analysis['total_samples']}")
    print(f"Time Span: {analysis['time_span']['start']} → {analysis['time_span']['end']}")
    print(f"Duration: {analysis['time_span']['duration_hours']} hours\n")

    print("SESSION USAGE:")
    print(f"  Current:  {analysis['session']['current']:>6.1f}%")
    print(f"  Range:    {analysis['session']['min']:>6.1f}% → {analysis['session']['max']:>6.1f}%")
    print(f"  Average:  {analysis['session']['avg']:>6.1f}%")
    print(f"  Trend:    {analysis['session']['trend'].upper()}")
    if 'pct_per_hour' in analysis['session']:
        print(f"  Velocity: {analysis['session']['pct_per_hour']:>+.3f}% per hour")
    if 'estimated_reset_in_hours' in analysis['session']:
        hours = analysis['session']['estimated_reset_in_hours']
        days = hours / 24
        if hours > 24:
            print(f"  Reset in: ~{days:.1f} days ({hours:.1f} hours)")
        else:
            print(f"  Reset in: ~{hours:.1f} hours")
    print()

    print("WEEKLY USAGE:")
    print(f"  Current:  {analysis['weekly']['current']:>6.1f}%")
    print(f"  Range:    {analysis['weekly']['min']:>6.1f}% → {analysis['weekly']['max']:>6.1f}%")
    print(f"  Average:  {analysis['weekly']['avg']:>6.1f}%")
    print(f"  Trend:    {analysis['weekly']['trend'].upper()}")
    if 'pct_per_hour' in analysis['weekly']:
        print(f"  Velocity: {analysis['weekly']['pct_per_hour']:>+.3f}% per hour")
    print()

    # Status recommendation
    session_pct = analysis['session']['current']
    weekly_pct = analysis['weekly']['current']

    if session_pct > 85:
        status = "🔴 CRITICAL"
    elif session_pct > 70:
        status = "🟡 HIGH"
    else:
        status = "🟢 HEALTHY"

    print(f"STATUS: {status}")
    print(f"  Session usage is {status.split()[1].lower()} at {session_pct:.1f}%")
    print(f"  Weekly usage is at {weekly_pct:.1f}%")

def print_json(analysis):
    """Print analysis as JSON."""
    if analysis:
        print(json.dumps(analysis, indent=2))
    else:
        print(json.dumps({"error": "No usage data captured yet"}, indent=2))

def main():
    # Navigate from scripts → orchestration → agentic-engineers → {service-name} → ERS project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    history_file = project_root / "data" / "metrics" / "usage_history.jsonl"

    # Parse arguments
    json_output = '--json' in sys.argv

    # Load and analyze
    entries = load_history(str(history_file))
    analysis = analyze_usage(entries)

    # Output
    if json_output:
        print_json(analysis)
    else:
        print_report(analysis)

if __name__ == '__main__':
    main()
