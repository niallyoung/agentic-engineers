"""
todo-maintenance skill: Auto-sync queue DELEGATEs ↔ TODO.md

This module provides bidirectional synchronization between:
- DELEGATE files in artifacts/queue/incoming/
- HANDBACK files in artifacts/queue/done/
- TODO.md (main task tracking file)

Features:
1. DELEGATE → TODO.md sync (add pending tasks)
2. HANDBACK → TODO.md sync (mark tasks complete)
3. Bidirectional sync with conflict detection
4. Weekly sync report generation
5. Orphan task detection (in TODO but not in queue)
6. Missing task detection (in queue but not in TODO)
"""

import re
import json
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
    ESCALATED = "escalated"


@dataclass
class DelegateEntry:
    """Represents a DELEGATE entry"""
    task_id: str
    role: str
    scope: str
    effort: str
    plan: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        """Validate entry after initialization"""
        if not self.task_id or not self.task_id.strip():
            raise ValueError("task_id cannot be empty")
        if not self.role or not self.role.strip():
            raise ValueError("role cannot be empty")

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "DelegateEntry":
        """Parse DELEGATE from YAML content"""
        # Handle YAML with multiple documents (separated by ---)
        # Use load_all to get the first document
        docs = list(yaml.safe_load_all(yaml_content))
        if not docs or not docs[0]:
            raise ValueError("Invalid YAML content")
        data = docs[0]
        return cls(
            task_id=data.get("task_id", ""),
            role=data.get("role", ""),
            scope=data.get("scope", "").strip(),
            effort=data.get("effort", "medium"),
            plan=data.get("plan", []),
            created_at=datetime.now().isoformat(),
        )

    @classmethod
    def from_file(cls, file_path: Path) -> "DelegateEntry":
        """Parse DELEGATE from file"""
        content = file_path.read_text()
        return cls.from_yaml(content)

    def to_todo_line(self) -> str:
        """Convert to TODO.md line format"""
        # Extract first line of scope for summary
        scope_summary = self.scope.split('\n')[0][:60]
        return f"- [ ] **{self.task_id}:** {scope_summary} (Owner: {self.role})"

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "role": self.role,
            "scope": self.scope,
            "effort": self.effort,
            "plan": self.plan,
            "created_at": self.created_at,
        }


@dataclass
class HandbackEntry:
    """Represents a HANDBACK entry"""
    task_id: str
    status: str
    timestamp: str
    quality_score: int = 0
    confidence: float = 0.0
    deliverables: List[str] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> "HandbackEntry":
        """Parse HANDBACK from dictionary"""
        return cls(
            task_id=data.get("task_id", ""),
            status=data.get("status", "unknown"),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            quality_score=data.get("quality_score", 0),
            confidence=data.get("confidence", 0.0),
            deliverables=data.get("deliverables", []),
            tests=data.get("tests", []),
        )

    @classmethod
    def from_file(cls, file_path: Path) -> "HandbackEntry":
        """Parse HANDBACK from file"""
        content = file_path.read_text()
        data = json.loads(content)
        return cls.from_dict(data)

    def to_todo_line(self) -> str:
        """Convert to TODO.md line format (marked complete)"""
        # Extract date from timestamp
        date_str = self.timestamp.split('T')[0]
        return f"- [x] **{self.task_id}:** Completed {date_str} (Quality: {self.quality_score}%)"

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "timestamp": self.timestamp,
            "quality_score": self.quality_score,
            "confidence": self.confidence,
            "deliverables": self.deliverables,
            "tests": self.tests,
        }


@dataclass
class SyncConflict:
    """Represents a sync conflict"""
    task_id: str
    source: str  # "todo" or "queue"
    queue_version: str
    todo_version: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SyncReport:
    """Represents a weekly sync report"""
    week_start: str
    week_end: str
    total_tasks: int
    completed_tasks: int
    orphaned_tasks: int
    missing_tasks: int
    conflicts: int
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def generate(self) -> str:
        """Generate report as markdown string"""
        completion_rate = (
            (self.completed_tasks / self.total_tasks * 100)
            if self.total_tasks > 0
            else 0
        )
        return f"""# TODO Sync Report

**Week:** {self.week_start} to {self.week_end}  
**Generated:** {self.generated_at}

## Summary

| Metric | Count |
|--------|-------|
| Total Tasks | {self.total_tasks} |
| Completed | {self.completed_tasks} |
| Completion Rate | {completion_rate:.1f}% |
| Orphaned Tasks | {self.orphaned_tasks} |
| Missing Tasks | {self.missing_tasks} |
| Conflicts | {self.conflicts} |

## Details

### Completion Status
- **Completed:** {self.completed_tasks}/{self.total_tasks} tasks
- **Completion Rate:** {completion_rate:.1f}%

### Data Quality Issues
- **Orphaned Tasks:** {self.orphaned_tasks} (in TODO but not in queue)
- **Missing Tasks:** {self.missing_tasks} (in queue but not in TODO)
- **Conflicts:** {self.conflicts} (conflicting versions)

## Recommendations

"""
        if self.orphaned_tasks > 0:
            report += f"- Review {self.orphaned_tasks} orphaned tasks in TODO.md\n"
        if self.missing_tasks > 0:
            report += f"- Add {self.missing_tasks} missing tasks to TODO.md\n"
        if self.conflicts > 0:
            report += f"- Resolve {self.conflicts} conflicts between TODO.md and queue\n"

        return report

    def write_to_file(self, file_path: Path) -> None:
        """Write report to file"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(self.generate())


class TodoSyncManager:
    """Main synchronization manager"""

    def __init__(self, todo_path: Path, queue_path: Path):
        """Initialize sync manager"""
        self.todo_path = Path(todo_path)
        self.queue_path = Path(queue_path)
        self.conflicts: List[SyncConflict] = []

    def read_todo_md(self) -> List[Dict]:
        """Read and parse TODO.md file"""
        if not self.todo_path.exists():
            return []

        content = self.todo_path.read_text()
        entries = []

        # Parse TODO.md format: - [ ] **TASK-ID:** description (Owner: role)
        # Also handle: - [x] **TASK-ID:** description (Owner: role)
        # Note: The colon is INSIDE the bold markers: **TASK-ID:**
        pattern = r'- \[(.)\] \*\*(.+?):\*\* (.+?) \(Owner: ([^)]+)\)'
        for match in re.finditer(pattern, content):
            status = "complete" if match.group(1) == "x" else "pending"
            entries.append({
                "task_id": match.group(2).strip(),
                "description": match.group(3).strip(),
                "owner": match.group(4).strip(),
                "status": status,
            })

        return entries

    def sync_delegate_to_todo(self, delegate_data: Dict) -> bool:
        """Sync DELEGATE entry to TODO.md"""
        try:
            entry = DelegateEntry(
                task_id=delegate_data.get("task_id", ""),
                role=delegate_data.get("role", ""),
                scope=delegate_data.get("scope", ""),
                effort=delegate_data.get("effort", "medium"),
                plan=delegate_data.get("plan", []),
            )

            # Read current TODO.md
            if not self.todo_path.exists():
                todo_content = "# TODO\n\n## IN PROGRESS\n\n## COMPLETED\n"
            else:
                todo_content = self.todo_path.read_text()

            # Check if task already exists
            if entry.task_id in todo_content:
                return False  # Task already exists

            # Add to IN PROGRESS section
            in_progress_marker = "## IN PROGRESS"
            if in_progress_marker in todo_content:
                # Insert after the marker
                parts = todo_content.split(in_progress_marker)
                todo_content = (
                    parts[0]
                    + in_progress_marker
                    + "\n"
                    + entry.to_todo_line()
                    + "\n"
                    + parts[1]
                )
            else:
                # Append to file
                todo_content += "\n" + entry.to_todo_line() + "\n"

            # Write back
            self.todo_path.write_text(todo_content)
            return True

        except Exception as e:
            print(f"Error syncing DELEGATE: {e}")
            return False

    def sync_handback_to_todo(self, handback_data: Dict) -> bool:
        """Sync HANDBACK entry to TODO.md (mark complete)"""
        try:
            entry = HandbackEntry.from_dict(handback_data)

            if not self.todo_path.exists():
                return False

            todo_content = self.todo_path.read_text()

            # Find and replace the task line - change [ ] to [x]
            # Pattern: - [ ] **TASK-ID:** ...
            pattern = rf'- \[ \] \*\*{re.escape(entry.task_id)}:\*\*'
            if re.search(pattern, todo_content):
                # Replace [ ] with [x]
                todo_content = re.sub(
                    pattern,
                    f"- [x] **{entry.task_id}:**",
                    todo_content,
                )

                # Write back
                self.todo_path.write_text(todo_content)
                return True

            return False

        except Exception as e:
            print(f"Error syncing HANDBACK: {e}")
            return False

    def detect_orphaned_tasks(self) -> List[Dict]:
        """Detect tasks in TODO but not in queue"""
        todo_entries = self.read_todo_md()
        queue_task_ids = self._get_queue_task_ids()

        orphaned = []
        for entry in todo_entries:
            if entry["task_id"] not in queue_task_ids:
                orphaned.append(entry)

        return orphaned

    def detect_missing_tasks(self) -> List[Dict]:
        """Detect tasks in queue but not in TODO"""
        todo_entries = self.read_todo_md()
        todo_task_ids = {e["task_id"] for e in todo_entries}
        queue_entries = self._get_queue_entries()

        missing = []
        for entry in queue_entries:
            if entry["task_id"] not in todo_task_ids:
                missing.append(entry)

        return missing

    def detect_conflicts(self) -> List[SyncConflict]:
        """Detect conflicts between TODO and queue"""
        self.conflicts = []
        todo_entries = {e["task_id"]: e for e in self.read_todo_md()}
        queue_entries = {e["task_id"]: e for e in self._get_queue_entries()}

        # Check for modified tasks
        for task_id in todo_entries:
            if task_id in queue_entries:
                todo_desc = todo_entries[task_id].get("description", "")
                queue_desc = queue_entries[task_id].get("scope", "")

                # Simple conflict detection: different descriptions (first 30 chars)
                # Normalize whitespace for comparison
                todo_normalized = " ".join(todo_desc.split())[:30]
                queue_normalized = " ".join(queue_desc.split())[:30]
                
                if todo_normalized and queue_normalized and todo_normalized != queue_normalized:
                    conflict = SyncConflict(
                        task_id=task_id,
                        source="both",
                        queue_version=queue_desc,
                        todo_version=todo_desc,
                    )
                    self.conflicts.append(conflict)

        return self.conflicts

    def resolve_conflict(self, conflict: SyncConflict) -> str:
        """Resolve conflict using merge strategy"""
        # Strategy: TODO.md manual edits take precedence
        # This ensures human edits are not overwritten
        return conflict.todo_version

    def bidirectional_sync(self) -> Dict:
        """Perform bidirectional sync"""
        result = {
            "delegates_synced": 0,
            "handbacks_synced": 0,
            "conflicts": 0,
            "orphaned": 0,
            "missing": 0,
        }

        # Sync all DELEGATEs
        delegate_files = list(self.queue_path.glob("incoming/DELEGATE-*.yaml"))
        for delegate_file in delegate_files:
            try:
                delegate_data = yaml.safe_load(delegate_file.read_text())
                if self.sync_delegate_to_todo(delegate_data):
                    result["delegates_synced"] += 1
            except Exception as e:
                print(f"Error processing {delegate_file}: {e}")

        # Sync all HANDBACKs
        handback_files = list(self.queue_path.glob("done/HANDBACK-*.json"))
        for handback_file in handback_files:
            try:
                handback_data = json.loads(handback_file.read_text())
                if self.sync_handback_to_todo(handback_data):
                    result["handbacks_synced"] += 1
            except Exception as e:
                print(f"Error processing {handback_file}: {e}")

        # Detect issues
        result["orphaned"] = len(self.detect_orphaned_tasks())
        result["missing"] = len(self.detect_missing_tasks())
        result["conflicts"] = len(self.detect_conflicts())

        return result

    def generate_weekly_report(self, week_start: str = None) -> SyncReport:
        """Generate weekly sync report"""
        if not week_start:
            # Default to last Monday
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday())

        week_start_str = week_start.strftime("%Y-%m-%d") if hasattr(week_start, 'strftime') else week_start
        week_end = datetime.fromisoformat(week_start_str) + timedelta(days=6)
        week_end_str = week_end.strftime("%Y-%m-%d")

        todo_entries = self.read_todo_md()
        completed = sum(1 for e in todo_entries if e["status"] == "complete")
        total = len(todo_entries)

        orphaned = len(self.detect_orphaned_tasks())
        missing = len(self.detect_missing_tasks())
        conflicts = len(self.detect_conflicts())

        return SyncReport(
            week_start=week_start_str,
            week_end=week_end_str,
            total_tasks=total,
            completed_tasks=completed,
            orphaned_tasks=orphaned,
            missing_tasks=missing,
            conflicts=conflicts,
        )

    def _get_queue_task_ids(self) -> set:
        """Get all task IDs from queue"""
        task_ids = set()

        # Get from DELEGATE files
        for delegate_file in self.queue_path.glob("*/DELEGATE-*.yaml"):
            try:
                data = yaml.safe_load(delegate_file.read_text())
                if "task_id" in data:
                    task_ids.add(data["task_id"])
            except Exception:
                pass

        # Get from HANDBACK files
        for handback_file in self.queue_path.glob("*/HANDBACK-*.json"):
            try:
                data = json.loads(handback_file.read_text())
                if "task_id" in data:
                    task_ids.add(data["task_id"])
            except Exception:
                pass

        return task_ids

    def _get_queue_entries(self) -> List[Dict]:
        """Get all entries from queue"""
        entries = []

        # Get from DELEGATE files
        for delegate_file in self.queue_path.glob("*/DELEGATE-*.yaml"):
            try:
                data = yaml.safe_load(delegate_file.read_text())
                entries.append({
                    "task_id": data.get("task_id", ""),
                    "scope": data.get("scope", ""),
                    "role": data.get("role", ""),
                    "type": "delegate",
                })
            except Exception:
                pass

        # Get from HANDBACK files
        for handback_file in self.queue_path.glob("*/HANDBACK-*.json"):
            try:
                data = json.loads(handback_file.read_text())
                entries.append({
                    "task_id": data.get("task_id", ""),
                    "status": data.get("status", ""),
                    "type": "handback",
                })
            except Exception:
                pass

        return entries


def main():
    """Main entry point for CLI"""
    import argparse

    parser = argparse.ArgumentParser(
        description="todo-maintenance skill: Auto-sync queue ↔ TODO.md"
    )
    parser.add_argument(
        "--todo-path",
        type=Path,
        default=Path.cwd() / "TODO.md",
        help="Path to TODO.md file",
    )
    parser.add_argument(
        "--queue-path",
        type=Path,
        default=Path.cwd() / "artifacts" / "queue",
        help="Path to queue directory",
    )
    parser.add_argument(
        "command",
        choices=["sync", "report", "check"],
        help="Command to execute",
    )

    args = parser.parse_args()

    manager = TodoSyncManager(todo_path=args.todo_path, queue_path=args.queue_path)

    if args.command == "sync":
        result = manager.bidirectional_sync()
        print(f"Sync complete:")
        print(f"  DELEGATEs synced: {result['delegates_synced']}")
        print(f"  HANDBACKs synced: {result['handbacks_synced']}")
        print(f"  Conflicts: {result['conflicts']}")
        print(f"  Orphaned: {result['orphaned']}")
        print(f"  Missing: {result['missing']}")

    elif args.command == "report":
        report = manager.generate_weekly_report()
        print(report.generate())

    elif args.command == "check":
        conflicts = manager.detect_conflicts()
        orphaned = manager.detect_orphaned_tasks()
        missing = manager.detect_missing_tasks()

        if conflicts:
            print(f"Found {len(conflicts)} conflicts:")
            for conflict in conflicts:
                print(f"  - {conflict.task_id}: {conflict.source}")

        if orphaned:
            print(f"Found {len(orphaned)} orphaned tasks:")
            for task in orphaned:
                print(f"  - {task['task_id']}")

        if missing:
            print(f"Found {len(missing)} missing tasks:")
            for task in missing:
                print(f"  - {task['task_id']}")


if __name__ == "__main__":
    main()
