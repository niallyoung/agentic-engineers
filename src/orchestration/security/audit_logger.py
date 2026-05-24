"""
Audit Logger — Immutable audit trail for all DELEGATE/HANDBACK transitions.

Records all state transitions with timestamps, agents, and outcomes for
compliance, debugging, and security auditing.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

# Audit log directory
AUDIT_DIR = Path.home() / ".agentic-engineers" / "audit"


class AuditLogger:
    """
    Append-only audit trail for protocol transitions.
    
    Records:
    - Task delegation (DELEGATE)
    - Task completion (HANDBACK)
    - Quality validation results
    - Security checks
    - Error conditions
    """
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize audit logger.
        
        Args:
            log_dir: Directory for audit logs (default: ~/.agentic-engineers/audit/)
        """
        self.log_dir = log_dir or AUDIT_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Current audit file (rotated daily)
        self.current_log = self._get_current_log_file()
    
    def _get_current_log_file(self) -> Path:
        """Get today's audit log file."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return self.log_dir / f"audit-{today}.jsonl"
    
    def _ensure_rotation(self) -> None:
        """Check if log file should be rotated (new day)."""
        new_log = self._get_current_log_file()
        if new_log != self.current_log:
            self.current_log = new_log
    
    def _calculate_checksum(self, entry: Dict[str, Any]) -> str:
        """
        Calculate SHA256 checksum of entry for tamper detection.
        
        Excludes checksum field itself from calculation.
        """
        entry_copy = {k: v for k, v in entry.items() if k != 'checksum'}
        json_str = json.dumps(entry_copy, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def log_delegate(self, task_id: str, delegate: Dict[str, Any], 
                    agent: str, source: str = "user") -> bool:
        """
        Log DELEGATE creation.
        
        Args:
            task_id: Task ID from DELEGATE
            delegate: The DELEGATE block
            agent: Target agent role
            source: Source of delegation (user, orchestrator, etc.)
            
        Returns:
            True if successfully logged
        """
        self._ensure_rotation()
        
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'DELEGATE',
            'task_id': task_id,
            'role': agent,
            'source': source,
            'effort': delegate.get('effort', 'unknown'),
            'status': 'created',
        }
        entry['checksum'] = self._calculate_checksum(entry)
        
        return self._append_entry(entry)
    
    def log_validation(self, task_id: str, validation_result: Dict[str, Any],
                      validator: str = "quality_validator") -> bool:
        """
        Log validation result (quality gate, security check, etc).
        
        Args:
            task_id: Task ID being validated
            validation_result: Validation result data
            validator: Name of validator that ran
            
        Returns:
            True if successfully logged
        """
        self._ensure_rotation()
        
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'VALIDATION',
            'task_id': task_id,
            'validator': validator,
            'passed': validation_result.get('passed', False),
            'score': validation_result.get('score', 0),
            'issues': validation_result.get('issues', []),
        }
        entry['checksum'] = self._calculate_checksum(entry)
        
        return self._append_entry(entry)
    
    def log_security_check(self, task_id: str, check_name: str, 
                          passed: bool, findings: List[str]) -> bool:
        """
        Log security check result.
        
        Args:
            task_id: Task ID that was checked
            check_name: Name of security check (e.g., 'entropy_detection')
            passed: Whether check passed
            findings: List of findings/issues
            
        Returns:
            True if successfully logged
        """
        self._ensure_rotation()
        
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'SECURITY_CHECK',
            'task_id': task_id,
            'check': check_name,
            'passed': passed,
            'findings_count': len(findings),
            'findings': findings[:10],  # Limit to first 10
        }
        entry['checksum'] = self._calculate_checksum(entry)
        
        return self._append_entry(entry)
    
    def log_handback(self, task_id: str, handback: Dict[str, Any],
                    agent: str, status: str, quality_score: int) -> bool:
        """
        Log HANDBACK completion.
        
        Args:
            task_id: Task ID being returned
            handback: The HANDBACK block
            agent: Agent that completed the task
            status: Completion status (complete, failed, partial)
            quality_score: Quality score (0-100)
            
        Returns:
            True if successfully logged
        """
        self._ensure_rotation()
        
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'HANDBACK',
            'task_id': task_id,
            'agent': agent,
            'status': status,
            'quality_score': quality_score,
            'tokens_in': handback.get('tokens_in', 0),
            'tokens_out': handback.get('tokens_out', 0),
        }
        entry['checksum'] = self._calculate_checksum(entry)
        
        return self._append_entry(entry)
    
    def log_rate_limit_violation(self, agent: str, agent_id: str, 
                                threshold: int) -> bool:
        """
        Log rate limit violation.
        
        Args:
            agent: Agent role or name
            agent_id: Unique agent ID
            threshold: Rate limit threshold that was exceeded
            
        Returns:
            True if successfully logged
        """
        self._ensure_rotation()
        
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'RATE_LIMIT_VIOLATION',
            'agent': agent,
            'agent_id': agent_id,
            'threshold': threshold,
            'severity': 'warning',
        }
        entry['checksum'] = self._calculate_checksum(entry)
        
        return self._append_entry(entry)
    
    def log_budget_violation(self, agent: str, spent: int, limit: int,
                            period: str = "day") -> bool:
        """
        Log token budget violation.
        
        Args:
            agent: Agent role or name
            spent: Tokens spent
            limit: Budget limit
            period: Period (day, week, month)
            
        Returns:
            True if successfully logged
        """
        self._ensure_rotation()
        
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'BUDGET_VIOLATION',
            'agent': agent,
            'tokens_spent': spent,
            'budget_limit': limit,
            'period': period,
            'severity': 'critical' if spent > limit else 'warning',
        }
        entry['checksum'] = self._calculate_checksum(entry)
        
        return self._append_entry(entry)
    
    def log_compliance_check(self, item: str, check_type: str, 
                            passed: bool, details: str = "") -> bool:
        """
        Log compliance check result.
        
        Args:
            item: Item being checked (e.g., commit sha, file path)
            check_type: Type of check (SPEC_DRIFT, CREDENTIALS, etc.)
            passed: Whether check passed
            details: Additional details
            
        Returns:
            True if successfully logged
        """
        self._ensure_rotation()
        
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'COMPLIANCE_CHECK',
            'item': item,
            'check_type': check_type,
            'passed': passed,
            'details': details[:256],  # Limit length
        }
        entry['checksum'] = self._calculate_checksum(entry)
        
        return self._append_entry(entry)
    
    def _append_entry(self, entry: Dict[str, Any]) -> bool:
        """
        Append entry to audit log (append-only).
        
        Args:
            entry: Entry to append
            
        Returns:
            True if successfully appended
        """
        try:
            with open(self.current_log, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            return True
        except Exception as e:
            logger.error(f"Failed to append audit log entry: {e}")
            return False
    
    def query_events(self, task_id: Optional[str] = None,
                    event_type: Optional[str] = None,
                    limit: int = 100) -> List[Dict[str, Any]]:
        """
        Query audit log for events.
        
        Args:
            task_id: Filter by task_id (optional)
            event_type: Filter by event type (optional)
            limit: Maximum events to return
            
        Returns:
            List of matching entries
        """
        events = []
        
        # Scan recent log files
        for log_file in sorted(self.log_dir.glob("audit-*.jsonl"), reverse=True)[:7]:  # Last 7 days
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        
                        entry = json.loads(line)
                        
                        # Apply filters
                        if task_id and entry.get('task_id') != task_id:
                            continue
                        if event_type and entry.get('event_type') != event_type:
                            continue
                        
                        events.append(entry)
                        
                        if len(events) >= limit:
                            return events[:limit]
            except Exception as e:
                logger.warning(f"Failed to read audit log {log_file}: {e}")
                continue
        
        return events
    
    def verify_tamper_detection(self, entry: Dict[str, Any]) -> bool:
        """
        Verify entry hasn't been tampered with (checksum verification).
        
        Args:
            entry: Entry to verify
            
        Returns:
            True if checksum matches
        """
        stored_checksum = entry.pop('checksum', None)
        calculated_checksum = self._calculate_checksum(entry)
        entry['checksum'] = stored_checksum  # Restore
        
        return stored_checksum == calculated_checksum
