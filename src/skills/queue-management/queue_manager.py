"""
Queue Management Skill - Task queuing automation.

Enables convenient task addition to both queue/ and TODO.md simultaneously.
Implements QUEUE-PROTOCOL validation, DELEGATE generation, and git integration.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# queue-isolation integration (optional — graceful fallback if not importable)
# ---------------------------------------------------------------------------
_QUEUE_ISOLATION_SCRIPTS = Path(__file__).parent.parent / "_meta" / "queue-isolation" / "scripts"

def _try_import_queue_isolation():
    """Attempt to import queue_isolation; return module or None on failure."""
    try:
        if str(_QUEUE_ISOLATION_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(_QUEUE_ISOLATION_SCRIPTS))
        import queue_isolation as _qi  # noqa: PLC0415
        return _qi
    except ImportError:
        return None


# Custom exceptions
class QueueManagementError(Exception):
    """Base exception for queue management."""
    pass


class ValidationError(QueueManagementError):
    """Raised when spec validation fails."""
    pass


class DuplicateTaskError(QueueManagementError):
    """Raised when task_id already exists."""
    pass


class GitError(QueueManagementError):
    """Raised when git operations fail."""
    pass


class QueueManager:
    """
    Main queue management class.
    Handles parsing, validation, DELEGATE generation, TODO.md updates, and git commits.
    """

    # Required fields for QUEUE-PROTOCOL
    REQUIRED_FIELDS = ["task_id", "role", "scope", "plan", "success_criteria"]

    # Valid roles (from AGENTS.md — 8 canonical roles)
    VALID_ROLES = [
        "Engineer", "Senior Engineer", "Lead Engineer", "Principal Engineer",
        "Quality Engineer", "Security Engineer", "Model Engineer", "Orchestrator",
    ]

    def __init__(
        self,
        queue_dir: Optional[str] = None,
        todo_path: Optional[str] = None,
    ):
        """Initialize QueueManager."""
        self.queue_dir = queue_dir or self._get_default_queue_dir()
        self.todo_path = todo_path or self._get_default_todo_path()
        self._ensure_queue_structure()

    @staticmethod
    def _get_default_queue_dir() -> str:
        """Get default queue directory using queue-isolation for harness/session scoping.

        Uses ``queue_isolation.get_queue_path()`` when the queue-isolation skill is
        available (preferred).  Falls back to the legacy ``~/.agentic-engineers/`` path
        so that existing deployments are not broken.

        Isolation path:
            ~/.agentic-engineers/artifacts/{session_id}/{harness}/queue/incoming/

        Legacy fallback path:
            ~/.agentic-engineers/{session_id}/incoming/
        """
        qi = _try_import_queue_isolation()
        if qi is not None:
            session_id = qi.get_session_id()
            harness = qi.detect_harness()
            queue_root = qi.get_queue_path(session_id, harness)
            # Initialise the full structure (idempotent)
            qi.init_queue_structure(session_id, harness)
            return str(queue_root / "incoming")

        # ---- Legacy fallback (backward compatibility) ----
        session_id = os.environ.get("COPILOT_SESSION_ID")
        if not session_id:
            session_id = os.environ.get("CLAUDE_SESSION_ID")
        if not session_id:
            session_id = "local"

        queue_base = os.path.expanduser("~/.agentic-engineers/")
        return os.path.join(queue_base, session_id, "incoming")

    @staticmethod
    def _get_default_todo_path() -> str:
        """Get default TODO.md path from current git repo."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                repo_root = result.stdout.strip()
                return os.path.join(repo_root, "TODO.md")
        except Exception:
            pass
        return "TODO.md"

    def _ensure_queue_structure(self) -> None:
        """Ensure queue directory structure exists."""
        os.makedirs(self.queue_dir, exist_ok=True)

    def parse_spec(
        self,
        spec: Dict[str, Any],
        format_type: str = "json",
    ) -> Dict[str, Any]:
        """
        Parse task specification (JSON or dict format).
        
        Args:
            spec: Task specification dictionary
            format_type: Format type ("json" or "dict")
            
        Returns:
            Parsed specification dictionary
            
        Raises:
            ValueError: If spec is missing required fields
        """
        # Validate all required fields are present
        missing = [f for f in self.REQUIRED_FIELDS if f not in spec]
        if missing:
            raise ValueError(
                f"Missing required field(s): {', '.join(missing)}. "
                f"Required: {', '.join(self.REQUIRED_FIELDS)}"
            )
        
        return spec

    def parse_spec_from_cli(self, args: List[str]) -> Dict[str, Any]:
        """
        Parse task specification from CLI arguments.
        
        Format: --task-id X --role Y --scope Z --plan P1,P2 --criteria C1,C2
        
        Args:
            args: CLI argument list
            
        Returns:
            Parsed specification dictionary
            
        Raises:
            ValueError: If required CLI parameters are missing
        """
        spec = {}
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--task-id" and i + 1 < len(args):
                spec["task_id"] = args[i + 1]
                i += 2
            elif arg == "--role" and i + 1 < len(args):
                spec["role"] = args[i + 1]
                i += 2
            elif arg == "--scope" and i + 1 < len(args):
                spec["scope"] = args[i + 1]
                i += 2
            elif arg == "--effort" and i + 1 < len(args):
                spec["effort"] = args[i + 1]
                i += 2
            elif arg == "--priority" and i + 1 < len(args):
                spec["priority"] = args[i + 1]
                i += 2
            else:
                i += 1
        
        # Validate minimum required parameters
        if "task_id" not in spec:
            raise ValueError("Missing required parameter: --task-id")
        if "role" not in spec:
            raise ValueError("Missing required parameter: --role")
        if "scope" not in spec:
            raise ValueError("Missing required parameter: --scope")
        
        # Set defaults for optional fields
        if "plan" not in spec:
            spec["plan"] = [spec["scope"]]  # Use scope as default plan
        if "success_criteria" not in spec:
            spec["success_criteria"] = ["Task completed"]
        
        return spec

    def validate_protocol(self, spec: Dict[str, Any]) -> None:
        """
        Validate spec against QUEUE-PROTOCOL format.
        
        Args:
            spec: Task specification to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in spec:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate task_id format (kebab-case)
        task_id = spec["task_id"]
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", task_id):
            raise ValidationError(
                f"task_id must be kebab-case (lowercase letters, numbers, hyphens). "
                f"Got: {task_id}"
            )
        
        # Validate role
        if spec["role"] not in self.VALID_ROLES:
            raise ValidationError(
                f"Invalid role: {spec['role']}. "
                f"Must be one of: {', '.join(self.VALID_ROLES)}"
            )
        
        # Validate plan is not empty
        if not spec["plan"] or len(spec["plan"]) == 0:
            raise ValidationError("plan must not be empty")
        
        # Validate success_criteria is not empty
        if not spec["success_criteria"] or len(spec["success_criteria"]) == 0:
            raise ValidationError("success_criteria must not be empty")

    def check_duplicate(self, task_id: str) -> None:
        """
        Check for duplicate task_id in existing queue and TODO.md.
        
        Args:
            task_id: Task ID to check
            
        Raises:
            DuplicateTaskError: If task_id already exists
        """
        # Check in queue directory (handle both queue_dir being incoming/ or parent of it)
        search_paths = [self.queue_dir]
        
        # If queue_dir contains an 'incoming' subdirectory, also search there
        incoming_path = os.path.join(self.queue_dir, "incoming")
        if os.path.isdir(incoming_path):
            search_paths.append(incoming_path)
        
        for search_path in search_paths:
            try:
                for file in os.listdir(search_path):
                    if task_id in file:
                        raise DuplicateTaskError(
                            f"Task ID '{task_id}' already exists in queue: {search_path}/{file}"
                        )
            except FileNotFoundError:
                pass
        
        # Check in TODO.md
        if os.path.exists(self.todo_path):
            with open(self.todo_path, 'r') as f:
                content = f.read()
                if f"**{task_id}:**" in content or f"- [ ] {task_id}" in content:
                    raise DuplicateTaskError(
                        f"Task ID '{task_id}' already exists in TODO.md"
                    )

    def generate_delegate(self, spec: Dict[str, Any]) -> str:
        """
        Generate DELEGATE JSON file.
        
        Args:
            spec: Task specification
            
        Returns:
            Path to generated DELEGATE file
        """
        task_id = spec["task_id"]
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Create delegates directory structure
        delegates_dir = os.path.join(
            os.path.dirname(self.queue_dir),
            "delegates",
            date_str,
        )
        os.makedirs(delegates_dir, exist_ok=True)
        
        # Create DELEGATE file in queue/incoming/
        delegate_file = os.path.join(self.queue_dir, f"{task_id}.json")
        
        # DELEGATE content
        delegate = {
            "task_id": spec["task_id"],
            "description": spec["scope"],
            "role": spec["role"],
            "plan": spec["plan"],
            "success_criteria": spec["success_criteria"],
            "effort": spec.get("effort", "medium"),
            "priority": spec.get("priority", "normal"),
            "constraints": spec.get("constraints", []),
            "context": spec.get("context", ""),
            "created_at": datetime.now().isoformat(),
        }
        
        # Write DELEGATE file
        with open(delegate_file, 'w') as f:
            json.dump(delegate, f, indent=2)
        
        return delegate_file

    def add_todo_entry(self, spec: Dict[str, Any]) -> None:
        """
        Add entry to TODO.md in appropriate phase section.
        
        Args:
            spec: Task specification
        """
        task_id = spec["task_id"]
        scope = spec["scope"]
        role = spec["role"]
        effort = spec.get("effort", "medium")
        phase = spec.get("phase", "2")  # Default to Phase 2
        
        # Read existing TODO.md
        if os.path.exists(self.todo_path):
            with open(self.todo_path, 'r') as f:
                lines = f.readlines()
        else:
            lines = ["# TODO: agentic-engineers Implementation Roadmap\n\n"]
        
        # Find appropriate phase section
        phase_marker = f"## 🟢 PHASE {phase}" if phase == "2" else f"## 🔴 PHASE {phase}"
        
        # Find insertion point (after phase header)
        insert_idx = None
        for i, line in enumerate(lines):
            if phase_marker in line:
                # Find next non-empty line or next section
                insert_idx = i + 1
                while insert_idx < len(lines) and lines[insert_idx].strip() == "":
                    insert_idx += 1
                break
        
        if insert_idx is None:
            # Phase section doesn't exist, create it
            lines.append(f"\n{phase_marker}\n\n")
            insert_idx = len(lines)
        
        # Create TODO entry
        entry = (
            f"- [ ] **{task_id}:** {scope}\n"
            f"  - Effort: {effort}\n"
            f"  - Owner: {role}\n\n"
        )
        
        lines.insert(insert_idx, entry)
        
        # Write updated TODO.md
        with open(self.todo_path, 'w') as f:
            f.writelines(lines)

    def commit_to_git(self, spec: Dict[str, Any], message: str = "") -> None:
        """
        Commit both DELEGATE and TODO.md atomically.
        
        Args:
            spec: Task specification
            message: Custom commit message
            
        Raises:
            GitError: If git operations fail
        """
        task_id = spec["task_id"]
        
        if not message:
            message = f"queue: add task {task_id} to queue and TODO"
        
        # Pin git operations to the repository that owns TODO.md rather than the
        # ambient process cwd. Relying on os.getcwd() is unsafe: under concurrent
        # test execution another thread can change the working directory mid-call,
        # causing commits to land in the wrong repository.
        repo_cwd = os.path.dirname(os.path.abspath(self.todo_path)) or "."
        
        try:
            # Stage files
            subprocess.run(
                ["git", "add", self.queue_dir, self.todo_path],
                check=True,
                capture_output=True,
                cwd=repo_cwd,
            )
            
            # Commit
            subprocess.run(
                ["git", "commit", "-m", message],
                check=True,
                capture_output=True,
                cwd=repo_cwd,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Git commit failed: {e.stderr.decode()}")

    def process_task(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Full workflow: Parse → Validate → Check duplicate → Generate → Add TODO → Commit.
        
        Args:
            spec: Task specification
            
        Returns:
            Result dictionary with status, paths, and metrics
            
        Raises:
            ValidationError: If validation fails (can be caught by caller)
            DuplicateTaskError: If duplicate detected
        """
        result = {
            "status": "success",
            "task_id": spec.get("task_id"),
            "delegate_path": None,
            "todo_updated": False,
            "committed": False,
            "errors": [],
        }
        
        try:
            # Parse
            parsed = self.parse_spec(spec)
            
            # Validate (may raise ValidationError)
            self.validate_protocol(parsed)
            
            # Check for duplicates (may raise DuplicateTaskError)
            self.check_duplicate(parsed["task_id"])
            
            # Generate DELEGATE
            result["delegate_path"] = self.generate_delegate(parsed)
            
            # Add TODO entry
            self.add_todo_entry(parsed)
            result["todo_updated"] = True
            
            # Commit to git
            try:
                self.commit_to_git(parsed)
                result["committed"] = True
            except GitError as e:
                result["errors"].append(f"Git commit failed (files created): {e}")
                result["committed"] = False
        
        except (ValidationError, DuplicateTaskError) as e:
            # Re-raise validation and duplicate errors to caller
            raise
        except ValueError as e:
            # Parse errors become failed status with errors list
            result["status"] = "failed"
            result["errors"].append(str(e))
        
        return result
