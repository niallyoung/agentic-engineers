#!/usr/bin/env python3
"""
Memory ETL Pipeline - Aggregate DELEGATE/HANDBACK/logs for session memory

Reads protocol files from session artifact directory and aggregates them
into a comprehensive memory index.

Usage:
    ./memory_etl.py --session abc-123 --aggregate
    ./memory_etl.py --session abc-123 --export json [--output memory.json]
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional


class MemoryETL:
    """Extract, transform, and load session memory."""

    def __init__(self, session_id: str, base_dir: Optional[str] = None):
        """Initialize Memory ETL."""
        if base_dir is None:
            base_dir = os.path.expanduser("~/.agentic-engineers")
        
        self.session_id = session_id
        self.base_dir = Path(base_dir)
        self.session_dir = self.base_dir / session_id
        self.memory_dir = self.session_dir / "memory"

    def aggregate_delegates(self) -> Dict[str, Any]:
        """
        Aggregate all DELEGATE files from this session.
        
        Returns:
            Dict with delegate statistics and details
        """
        delegates_dir = self.session_dir / "delegates"
        if not delegates_dir.exists():
            return {"count": 0, "delegates": [], "by_role": {}}
        
        delegates = []
        by_role = {}
        
        for yaml_file in delegates_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r") as f:
                    content = f.read()
                    delegate_info = self._parse_yaml_fields(
                        content, ["task_id", "role", "model", "effort", "scope"]
                    )
                    delegate_info["file"] = str(yaml_file.relative_to(self.base_dir))
                    delegates.append(delegate_info)
                    
                    # Track by role
                    role = delegate_info.get("role", "unknown")
                    if role not in by_role:
                        by_role[role] = 0
                    by_role[role] += 1
            except IOError:
                continue
        
        return {
            "count": len(delegates),
            "by_role": by_role,
            "delegates": delegates,
        }

    def aggregate_handbacks(self) -> Dict[str, Any]:
        """
        Aggregate all HANDBACK files from this session.
        
        Returns:
            Dict with handback statistics and details
        """
        handbacks_dir = self.session_dir / "handbacks"
        if not handbacks_dir.exists():
            return {"count": 0, "handbacks": [], "by_status": {}}
        
        handbacks = []
        by_status = {}
        
        for yaml_file in handbacks_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r") as f:
                    content = f.read()
                    handback_info = self._parse_yaml_fields(
                        content, ["task_id", "status", "quality_score", "confidence", "tokens"]
                    )
                    handback_info["file"] = str(yaml_file.relative_to(self.base_dir))
                    handbacks.append(handback_info)
                    
                    # Track by status
                    status = handback_info.get("status", "unknown")
                    if status not in by_status:
                        by_status[status] = 0
                    by_status[status] += 1
            except IOError:
                continue
        
        return {
            "count": len(handbacks),
            "by_status": by_status,
            "handbacks": handbacks,
        }

    def aggregate_logs(self) -> Dict[str, Any]:
        """
        Aggregate all log files from this session.
        
        Returns:
            Dict with log statistics
        """
        logs_dir = self.memory_dir / "logs"
        if not logs_dir.exists():
            return {"count": 0, "logs": []}
        
        logs = []
        for log_file in logs_dir.glob("*.log"):
            try:
                size = log_file.stat().st_size
                modified = datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                logs.append({
                    "file": str(log_file.relative_to(self.base_dir)),
                    "size_bytes": size,
                    "modified": modified,
                })
            except IOError:
                continue
        
        return {
            "count": len(logs),
            "logs": logs,
        }

    def aggregate_memory(self) -> Dict[str, Any]:
        """
        Aggregate memory summary from artifact directory.
        
        Returns:
            Dict with complete memory aggregation
        """
        return {
            "session_id": self.session_id,
            "aggregated_at": datetime.now().isoformat(),
            "delegates": self.aggregate_delegates(),
            "handbacks": self.aggregate_handbacks(),
            "logs": self.aggregate_logs(),
        }

    def _parse_yaml_fields(self, content: str, fields: List[str]) -> Dict[str, Any]:
        """
        Simple YAML field extraction (no external dependencies).
        
        Args:
            content: YAML file content
            fields: List of fields to extract
        
        Returns:
            Dict with extracted fields
        """
        result = {}
        lines = content.split("\n")
        
        for field in fields:
            for line in lines:
                if line.startswith(f"{field}:"):
                    value = line.split(":", 1)[1].strip()
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    result[field] = value
                    break
        
        return result

    def export_json(self) -> str:
        """Export aggregated memory as JSON."""
        aggregate = self.aggregate_memory()
        return json.dumps(aggregate, indent=2, default=str)

    def generate_report(self) -> str:
        """Generate human-readable report."""
        aggregate = self.aggregate_memory()
        
        lines = [
            f"=== Session Memory Report ===\n",
            f"Session: {self.session_id}\n",
            f"Generated: {datetime.now().isoformat()}\n\n",
        ]
        
        # Delegates summary
        delegates = aggregate.get("delegates", {})
        lines.append(f"Delegates: {delegates.get('count', 0)} total\n")
        for role, count in delegates.get("by_role", {}).items():
            lines.append(f"  - {role}: {count}\n")
        lines.append("")
        
        # Handbacks summary
        handbacks = aggregate.get("handbacks", {})
        lines.append(f"Handbacks: {handbacks.get('count', 0)} total\n")
        for status, count in handbacks.get("by_status", {}).items():
            lines.append(f"  - {status}: {count}\n")
        lines.append("")
        
        # Logs summary
        logs = aggregate.get("logs", {})
        lines.append(f"Logs: {logs.get('count', 0)} files\n\n")
        
        return "".join(lines)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Memory ETL Pipeline - Aggregate session memory"
    )
    parser.add_argument(
        "--session",
        required=True,
        help="Session ID to aggregate memory from",
    )
    parser.add_argument(
        "--aggregate",
        action="store_true",
        help="Aggregate memory and show report",
    )
    parser.add_argument(
        "--export",
        choices=["json"],
        help="Export format",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file (default stdout)",
    )
    parser.add_argument(
        "--base-dir",
        default=None,
        help="Base artifact directory (default ~/.agentic-engineers)",
    )

    args = parser.parse_args()

    etl = MemoryETL(session_id=args.session, base_dir=args.base_dir)
    
    # Generate output
    if args.export == "json":
        output = etl.export_json()
    else:
        # Default: show report
        output = etl.generate_report()
    
    # Write output
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"✓ Written to {args.output}")
    else:
        print(output)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
