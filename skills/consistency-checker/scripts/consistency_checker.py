"""
Consistency Checker — Phase 4 Self-Referential Protocol Implementation.

Automated cross-validation of DELEGATE/HANDBACK queue integrity.

Key features:
- Scan all queue states (incoming/, assigned/, completed/)
- Validate schema compliance (core + extensions)
- Detect structural issues (cycles, orphans, depth/width violations)
- Check rate limits (per-session, per-parent)
- Generate compliance report (pass rate, violations, stats)
- Enable self-referential protocol improvements (95%+ pass rate required)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import time
import sys
import argparse

# Import validators
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'protocol-validator' / 'scripts'))
from protocol_validator import ProtocolValidator

logger = logging.getLogger(__name__)


@dataclass
class StateStats:
    """Statistics for a single queue state (incoming, assigned, completed)."""
    total: int
    valid: int
    invalid: int
    
    @property
    def pass_rate(self) -> float:
        """Pass rate for this state."""
        return self.valid / self.total if self.total > 0 else 1.0


@dataclass
class ConsistencyReport:
    """Full consistency check report."""
    timestamp: str  # ISO 8601
    duration_seconds: float
    
    # Counts
    total_tasks: int
    valid_count: int
    invalid_count: int
    warning_count: int
    
    # Rates
    pass_rate: float  # valid_count / total_tasks
    
    # Details
    violations: List[str]
    warnings: List[str]
    stats: Dict[str, Any]
    
    # Breakdown by queue state
    by_state: Dict[str, Dict[str, int]]


class ConsistencyChecker:
    """
    Automated queue integrity validator.
    
    Scans all DELEGATEs/HANDBACKs, validates schema, detects cycles,
    checks rate limits, generates compliance report.
    """

    def __init__(
        self,
        queue_path: str = "~/.copilot/queue",
        session_id: Optional[str] = None,
        spec_path: str = "specs/protocol-core-v1.0.yaml",
    ):
        """
        Initialize checker.
        
        Args:
            queue_path: Path to queue directory
            session_id: Specific session to check (None = all sessions)
            spec_path: Path to protocol spec
        """
        self.queue_path = Path(queue_path).expanduser()
        self.session_id = session_id
        self.validator = ProtocolValidator(spec_path=spec_path)
        
        if not self.queue_path.exists():
            logger.warning(f"Queue path doesn't exist: {self.queue_path}")

    def check_queue(self) -> ConsistencyReport:
        """
        Run full consistency check on queue.
        
        Returns:
            ConsistencyReport with all validation results
        """
        start_time = time.time()
        
        violations = []
        warnings = []
        stats = {}
        by_state = {}
        
        total_tasks = 0
        valid_count = 0
        invalid_count = 0
        warning_count = 0
        
        # 1. Discover sessions
        sessions = self._discover_sessions()
        if not sessions:
            logger.warning("No sessions found in queue")
            return ConsistencyReport(
                timestamp=datetime.utcnow().isoformat() + 'Z',
                duration_seconds=0.0,
                total_tasks=0,
                valid_count=0,
                invalid_count=0,
                warning_count=0,
                pass_rate=1.0,
                violations=[],
                warnings=["No sessions found in queue"],
                stats={},
                by_state={},
            )
        
        # 2. Scan each session
        all_tasks = {}  # session_id -> {task_id -> task_dict}
        
        for sess_id in sessions:
            session_tasks = self._scan_session(sess_id)
            all_tasks[sess_id] = session_tasks
            
            # Validate each task
            for task_id, task_data in session_tasks.items():
                total_tasks += 1
                is_valid, task_violations, task_warnings = self._validate_task(
                    task_id, task_data, sess_id
                )
                
                if is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1
                
                violations.extend(task_violations)
                warnings.extend(task_warnings)
                warning_count += len(task_warnings)
        
        # 3. Check structural issues (cycles, orphans, depth/width)
        structural_violations = self._check_structural_issues(all_tasks)
        violations.extend(structural_violations)
        
        # 4. Check rate limits
        rate_limit_violations = self._check_rate_limits(all_tasks)
        violations.extend(rate_limit_violations)
        
        # 5. Aggregate by state
        by_state = self._aggregate_by_state(all_tasks)
        
        # 6. Calculate pass rate
        pass_rate = valid_count / total_tasks if total_tasks > 0 else 1.0
        
        # 7. Aggregated stats
        stats = {
            'sessions_checked': len(sessions),
            'total_validation_ms': int((time.time() - start_time) * 1000),
            'avg_task_ms': (time.time() - start_time) * 1000 / total_tasks if total_tasks > 0 else 0,
        }
        
        duration_seconds = time.time() - start_time
        
        return ConsistencyReport(
            timestamp=datetime.utcnow().isoformat() + 'Z',
            duration_seconds=duration_seconds,
            total_tasks=total_tasks,
            valid_count=valid_count,
            invalid_count=invalid_count,
            warning_count=warning_count,
            pass_rate=pass_rate,
            violations=violations,
            warnings=warnings,
            stats=stats,
            by_state=by_state,
        )

    def _discover_sessions(self) -> List[str]:
        """Discover all session directories in queue."""
        if not self.queue_path.exists():
            return []
        
        sessions = []
        for item in self.queue_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                if self.session_id is None or item.name == self.session_id:
                    sessions.append(item.name)
        
        return sorted(sessions)

    def _scan_session(self, session_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Scan a session and return all tasks.
        
        Returns:
            Dict mapping task_id -> {state, data}
        """
        session_path = self.queue_path / session_id
        if not session_path.exists():
            return {}
        
        tasks = {}
        
        # Scan all queue states
        for state_dir in ['incoming', 'assigned', 'completed']:
            state_path = session_path / state_dir
            if not state_path.exists():
                continue
            
            # Combine results from both YAML and JSON files
            yaml_files = list(state_path.glob('*.yaml'))
            json_files = list(state_path.glob('*.json'))
            task_files = yaml_files + json_files
            
            for task_file in task_files:
                try:
                    with open(task_file, 'r') as f:
                        if task_file.suffix == '.yaml':
                            import yaml
                            task_data = yaml.safe_load(f)
                        else:
                            task_data = json.load(f)
                    
                    task_id = task_file.stem
                    tasks[task_id] = {
                        'state': state_dir,
                        'data': task_data,
                        'file': str(task_file),
                    }
                except Exception as e:
                    logger.warning(f"Failed to load task {task_file}: {e}")
        
        return tasks

    def _validate_task(
        self,
        task_id: str,
        task_info: Dict[str, Any],
        session_id: str,
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a single task.
        
        Returns:
            (is_valid, violations, warnings)
        """
        violations = []
        warnings = []
        
        task_data = task_info.get('data', {})
        state = task_info.get('state', 'unknown')
        
        # Determine if DELEGATE or HANDBACK
        if 'skill' in task_data or 'plan' in task_data:  # DELEGATE fields
            result = self.validator.validate_delegate(task_data)
        elif 'status' in task_data or 'metrics' in task_data:  # HANDBACK fields
            result = self.validator.validate_handback(task_data)
        else:
            violations.append(f"Task '{task_id}': cannot determine if DELEGATE or HANDBACK")
            return False, violations, warnings
        
        # Collect validation results
        violations.extend([f"Task '{task_id}': {e}" for e in result.errors])
        warnings.extend([f"Task '{task_id}': {w}" for w in result.warnings])
        
        return result.valid, violations, warnings

    def _check_structural_issues(self, all_tasks: Dict[str, Dict[str, Dict]]) -> List[str]:
        """
        Check structural issues: orphans, cycles, depth/width violations.
        
        Returns:
            List of violations
        """
        violations = []
        
        # Build parent-child map per session
        for session_id, tasks in all_tasks.items():
            parent_map = {}  # parent_task_id -> [children]
            all_task_ids = set(tasks.keys())
            
            # 1. Find all parent relationships
            for task_id, task_info in tasks.items():
                task_data = task_info.get('data', {})
                parent_id = task_data.get('parent_task_id')
                
                if parent_id:
                    # Check if parent exists
                    if parent_id not in all_task_ids:
                        violations.append(
                            f"Session '{session_id}': Task '{task_id}' has orphaned parent '{parent_id}' "
                            f"(parent not found)"
                        )
                    else:
                        if parent_id not in parent_map:
                            parent_map[parent_id] = []
                        parent_map[parent_id].append(task_id)
            
            # 2. Check width constraint (max 10 children per parent)
            for parent_id, children in parent_map.items():
                if len(children) > 10:
                    violations.append(
                        f"Session '{session_id}': Parent '{parent_id}' has {len(children)} children "
                        f"(max 10 allowed)"
                    )
            
            # 3. Check cycles and depth
            visited = set()
            for task_id in all_task_ids:
                if task_id not in visited:
                    cycle_path, max_depth = self._detect_cycle(
                        task_id, all_tasks[session_id], visited, parent_map
                    )
                    if cycle_path:
                        violations.append(
                            f"Session '{session_id}': Cycle detected: {' → '.join(cycle_path)}"
                        )
                    if max_depth > 5:
                        violations.append(
                            f"Session '{session_id}': Chain depth {max_depth} exceeds max depth of 5 "
                            f"(task: {task_id})"
                        )
        
        return violations

    def _detect_cycle(
        self,
        task_id: str,
        tasks: Dict[str, Dict],
        visited: Set[str],
        parent_map: Dict[str, List[str]],
        path: Optional[List[str]] = None,
        depth: int = 0,
    ) -> Tuple[Optional[List[str]], int]:
        """
        Detect cycles and max depth via DFS.
        
        Returns:
            (cycle_path or None, max_depth)
        """
        if path is None:
            path = []
        
        if task_id in path:
            # Cycle detected
            cycle_start = path.index(task_id)
            cycle = path[cycle_start:] + [task_id]
            return cycle, depth
        
        if task_id in visited:
            return None, depth
        
        visited.add(task_id)
        path.append(task_id)
        
        # Follow parent chain
        task_data = tasks.get(task_id, {}).get('data', {})
        parent_id = task_data.get('parent_task_id')
        
        if parent_id:
            cycle, parent_depth = self._detect_cycle(
                parent_id, tasks, visited, parent_map, path, depth + 1
            )
            if cycle:
                return cycle, parent_depth
            return None, parent_depth
        
        path.pop()
        return None, depth

    def _check_rate_limits(self, all_tasks: Dict[str, Dict[str, Dict]]) -> List[str]:
        """
        Check rate limits: per-session (max 100/hour) and per-parent (max 10).
        
        Returns:
            List of violations
        """
        violations = []
        
        # Per-session limit: max 100 tasks/hour (simplified: just count incoming)
        for session_id, tasks in all_tasks.items():
            incoming_count = sum(1 for t in tasks.values() if t['state'] == 'incoming')
            if incoming_count > 100:
                violations.append(
                    f"Session '{session_id}': {incoming_count} incoming tasks "
                    f"(max 100 per hour allowed)"
                )
            
            # Per-parent limit: checked in structural validation
        
        return violations

    def _aggregate_by_state(self, all_tasks: Dict[str, Dict[str, Dict]]) -> Dict[str, Dict[str, int]]:
        """
        Aggregate counts by queue state.
        
        Returns:
            Dict mapping state -> {total, valid, invalid}
        """
        by_state = {
            'incoming': {'total': 0, 'valid': 0, 'invalid': 0},
            'assigned': {'total': 0, 'valid': 0, 'invalid': 0},
            'completed': {'total': 0, 'valid': 0, 'invalid': 0},
        }
        
        for session_id, tasks in all_tasks.items():
            for task_id, task_info in tasks.items():
                state = task_info.get('state', 'unknown')
                if state in by_state:
                    by_state[state]['total'] += 1
                    
                    # Re-validate to count
                    is_valid, _, _ = self._validate_task(task_id, task_info, session_id)
                    if is_valid:
                        by_state[state]['valid'] += 1
                    else:
                        by_state[state]['invalid'] += 1
        
        return by_state


def main():
    """CLI entry point for consistency checking."""
    parser = argparse.ArgumentParser(
        description="Check queue consistency and protocol compliance"
    )
    parser.add_argument(
        '--session',
        help='Check specific session (default: all sessions)'
    )
    parser.add_argument(
        '--queue',
        default='~/.copilot/queue',
        help='Path to queue directory'
    )
    parser.add_argument(
        '--spec',
        default='specs/protocol-core-v1.0.yaml',
        help='Path to protocol spec'
    )
    parser.add_argument(
        '--report',
        help='Save report as JSON to this file'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--delegates-only',
        action='store_true',
        help='Check only DELEGATEs (skip HANDBACKs)'
    )
    
    args = parser.parse_args()
    
    # Initialize checker
    try:
        checker = ConsistencyChecker(
            queue_path=args.queue,
            session_id=args.session,
            spec_path=args.spec,
        )
    except Exception as e:
        print(f"❌ Failed to initialize checker: {e}")
        return 1
    
    # Run check
    try:
        report = checker.check_queue()
    except Exception as e:
        print(f"❌ Failed to check queue: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    # Output results
    if args.verbose:
        print(f"Consistency Check Report")
        print(f"Timestamp: {report.timestamp}")
        print(f"Duration: {report.duration_seconds:.2f}s")
        print(f"\nSummary:")
        print(f"  Total tasks: {report.total_tasks}")
        print(f"  Valid: {report.valid_count}")
        print(f"  Invalid: {report.invalid_count}")
        print(f"  Pass rate: {report.pass_rate:.1%}")
        
        if report.by_state:
            print(f"\nBy State:")
            for state, stats in report.by_state.items():
                if stats['total'] > 0:
                    pass_rate = stats['valid'] / stats['total']
                    print(f"  {state:10} | total: {stats['total']:4} | valid: {stats['valid']:4} | "
                          f"invalid: {stats['invalid']:4} | rate: {pass_rate:.1%}")
        
        if report.violations:
            print(f"\nViolations ({len(report.violations)}):")
            for v in report.violations[:10]:  # Limit to 10
                print(f"  - {v}")
            if len(report.violations) > 10:
                print(f"  ... and {len(report.violations) - 10} more")
        else:
            print(f"\n✅ No violations found")
        
        if report.warnings:
            print(f"\nWarnings ({len(report.warnings)}):")
            for w in report.warnings[:5]:  # Limit to 5
                print(f"  - {w}")
            if len(report.warnings) > 5:
                print(f"  ... and {len(report.warnings) - 5} more")
    else:
        # Concise output
        print(f"{'✅' if report.pass_rate >= 0.95 else '❌'} "
              f"Pass rate: {report.pass_rate:.1%} ({report.valid_count}/{report.total_tasks})")
    
    # Save report if requested
    if args.report:
        report_dict = asdict(report)
        with open(args.report, 'w') as f:
            json.dump(report_dict, f, indent=2)
        print(f"\nReport saved to {args.report}")
    
    return 0 if report.pass_rate >= 0.95 else 1


if __name__ == '__main__':
    exit(main())
