"""
Queue Migration Monitoring & Metrics (Phase 4).

Tracks health and performance of unified queue architecture:
- Queue latency (DELEGATE reception → HANDBACK completion)
- Throughput (tasks per minute)
- Error rate (failed tasks)
- Migration progress (legacy → new paths)
- Multi-harness performance
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class QueueHealthMetrics:
    """Track queue health: latency, throughput, error rates."""
    
    def __init__(self, metrics_dir: Optional[Path] = None):
        """Initialize queue health metrics collector."""
        self.metrics_dir = metrics_dir or Path.home() / ".agentic-engineers" / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        self.start_time = datetime.now()
        self.tasks_processed = 0
        self.tasks_failed = 0
        self.latencies = []
        
        logger.info(f"QueueHealthMetrics initialized")
    
    def record_task_completion(self, task_id: str, latency_seconds: float, success: bool = True):
        """Record a task completion and latency."""
        self.latencies.append({
            'task_id': task_id,
            'latency': latency_seconds,
            'success': success,
            'timestamp': datetime.now().isoformat(),
        })
        
        if success:
            self.tasks_processed += 1
        else:
            self.tasks_failed += 1
    
    def get_average_latency(self) -> float:
        """Get average task latency in seconds."""
        if not self.latencies:
            return 0.0
        successful = [l['latency'] for l in self.latencies if l['success']]
        return sum(successful) / len(successful) if successful else 0.0
    
    def get_p95_latency(self) -> float:
        """Get 95th percentile latency."""
        if not self.latencies:
            return 0.0
        successful = sorted([l['latency'] for l in self.latencies if l['success']])
        idx = int(len(successful) * 0.95)
        return successful[min(idx, len(successful) - 1)] if successful else 0.0
    
    def get_throughput(self) -> float:
        """Get tasks per minute."""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        return self.tasks_processed / elapsed if elapsed >= 1 else 0.0
    
    def get_error_rate(self) -> float:
        """Get percentage of failed tasks."""
        total = self.tasks_processed + self.tasks_failed
        return (self.tasks_failed / total * 100) if total > 0 else 0.0


class MigrationProgressMetrics:
    """Track migration progress: legacy → new paths."""
    
    def __init__(self, legacy_base: Optional[Path] = None, new_base: Optional[Path] = None):
        """Initialize migration tracking."""
        self.legacy_base = legacy_base or Path.home() / ".copilot" / "queue"
        self.new_base = new_base or Path.home() / ".agentic-engineers" / "artifacts"
        
        self.migration_started = datetime.now()
        self.tasks_migrated = {}
        self.migration_errors = []
    
    def count_legacy_tasks(self, session_id: str) -> int:
        """Count tasks in legacy queue for session."""
        legacy_session = self.legacy_base / session_id
        if not legacy_session.exists():
            return 0
        
        count = 0
        for state in ['incoming', 'processing', 'done']:
            state_dir = legacy_session / state
            if state_dir.exists():
                count += len(list(state_dir.glob('*.yaml')))
        return count
    
    def count_new_tasks(self, session_id: str, harness: str) -> int:
        """Count tasks in new queue for session/harness."""
        new_session = self.new_base / session_id / harness / "queue"
        if not new_session.exists():
            return 0
        
        count = 0
        for state in ['incoming', 'processing', 'done', 'failed']:
            state_dir = new_session / state
            if state_dir.exists():
                count += len(list(state_dir.glob('*.yaml')))
        return count
    
    def record_task_migrated(self, session_id: str):
        """Record a task migration."""
        if session_id not in self.tasks_migrated:
            self.tasks_migrated[session_id] = 0
        self.tasks_migrated[session_id] += 1
    
    def record_migration_error(self, session_id: str, error: str):
        """Record a migration error."""
        self.migration_errors.append({
            'session_id': session_id,
            'error': error,
            'timestamp': datetime.now().isoformat(),
        })
    
    def get_migration_progress(self) -> Dict:
        """Get current migration progress."""
        total_tasks_migrated = sum(self.tasks_migrated.values())
        elapsed = (datetime.now() - self.migration_started).total_seconds() / 60
        
        return {
            'total_tasks_migrated': total_tasks_migrated,
            'sessions_in_progress': len(self.tasks_migrated),
            'migration_errors': len(self.migration_errors),
            'elapsed_minutes': elapsed,
        }


class MultiHarnessMetrics:
    """Track performance per harness (copilot, claude, gpt, local)."""
    
    def __init__(self):
        """Initialize per-harness metrics."""
        self.harness_stats = defaultdict(lambda: {
            'tasks_processed': 0,
            'tasks_failed': 0,
            'latencies': [],
            'last_activity': None,
        })
    
    def record_task(self, harness: str, task_id: str, latency: float, success: bool = True):
        """Record task execution for a harness."""
        stats = self.harness_stats[harness]
        
        if success:
            stats['tasks_processed'] += 1
        else:
            stats['tasks_failed'] += 1
        
        stats['latencies'].append(latency)
        stats['last_activity'] = datetime.now().isoformat()
    
    def get_harness_summary(self) -> Dict:
        """Get performance summary per harness."""
        summary = {}
        
        for harness, stats in self.harness_stats.items():
            total = stats['tasks_processed'] + stats['tasks_failed']
            avg_latency = sum(stats['latencies']) / len(stats['latencies']) if stats['latencies'] else 0.0
            
            summary[harness] = {
                'tasks_processed': stats['tasks_processed'],
                'tasks_failed': stats['tasks_failed'],
                'total_tasks': total,
                'error_rate': (stats['tasks_failed'] / total * 100) if total > 0 else 0.0,
                'avg_latency': avg_latency,
                'last_activity': stats['last_activity'],
            }
        
        return summary


class QueueAlertsAndThresholds:
    """Define and monitor queue health thresholds."""
    
    THRESHOLDS = {
        'latency_max_seconds': 60.0,
        'latency_p95_seconds': 30.0,
        'throughput_min_tpm': 1.0,
        'error_rate_max_percent': 5.0,
    }
    
    def __init__(self):
        """Initialize alerts."""
        self.active_alerts = []
    
    def check_health(self, metrics: QueueHealthMetrics) -> List[Dict]:
        """Check queue health against thresholds."""
        alerts = []
        
        avg_latency = metrics.get_average_latency()
        if avg_latency > self.THRESHOLDS['latency_max_seconds']:
            alerts.append({
                'severity': 'WARNING',
                'metric': 'average_latency',
                'value': avg_latency,
                'message': f'Average latency {avg_latency:.1f}s exceeds threshold',
            })
        
        error_rate = metrics.get_error_rate()
        if error_rate > self.THRESHOLDS['error_rate_max_percent']:
            alerts.append({
                'severity': 'ERROR',
                'metric': 'error_rate',
                'value': error_rate,
                'message': f'Error rate {error_rate:.1f}% exceeds threshold',
            })
        
        self.active_alerts = alerts
        return alerts
