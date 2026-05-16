"""
CLI interface for queue-management skill.

Commands:
  add-to-queue --task-id X --role Y --scope Z
  add-to-queue --spec-file spec.json
"""
import json
import sys
from typing import Any, Dict, List, Optional

from .queue_manager import QueueManager, QueueManagementError


def add_to_queue_cli(args: List[str]) -> Dict[str, Any]:
    """
    CLI command: add-to-queue
    
    Usage:
        add-to-queue --task-id X --role Y --scope Z [--effort E] [--priority P]
        add-to-queue --spec-file spec.json
    
    Args:
        args: CLI arguments
        
    Returns:
        Result dictionary with status and details
    """
    result = {
        "success": False,
        "message": "",
        "details": {},
    }
    
    try:
        qm = QueueManager()
        
        # Check if using spec file
        spec_file = None
        i = 0
        while i < len(args):
            if args[i] == "--spec-file" and i + 1 < len(args):
                spec_file = args[i + 1]
                break
            i += 1
        
        if spec_file:
            # Load from spec file
            with open(spec_file, 'r') as f:
                spec = json.load(f)
        else:
            # Parse from CLI arguments
            spec = qm.parse_spec_from_cli(args)
        
        # Process task
        process_result = qm.process_task(spec)
        
        if process_result["status"] == "success":
            result["success"] = True
            result["message"] = (
                f"✅ Task '{spec['task_id']}' added to queue successfully!\n"
                f"  - DELEGATE: {process_result['delegate_path']}\n"
                f"  - TODO.md: Updated\n"
                f"  - Git: {'Committed' if process_result['committed'] else 'Not committed'}"
            )
            result["details"] = process_result
        else:
            result["success"] = False
            result["message"] = "❌ Task processing failed:"
            for error in process_result["errors"]:
                result["message"] += f"\n  - {error}"
            result["details"] = process_result
    
    except QueueManagementError as e:
        result["success"] = False
        result["message"] = f"❌ Error: {e}"
    except FileNotFoundError as e:
        result["success"] = False
        result["message"] = f"❌ File not found: {e}"
    except json.JSONDecodeError as e:
        result["success"] = False
        result["message"] = f"❌ Invalid JSON in spec file: {e}"
    except Exception as e:
        result["success"] = False
        result["message"] = f"❌ Unexpected error: {e}"
    
    return result


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print(
            "Queue Management Skill - Add tasks to queue and TODO.md\n\n"
            "Usage:\n"
            "  add-to-queue --task-id X --role Y --scope Z [--effort E] [--priority P]\n"
            "  add-to-queue --spec-file spec.json\n\n"
            "Arguments:\n"
            "  --task-id      Task ID (kebab-case, required)\n"
            "  --role         Role (Engineer, Senior Engineer, etc., required)\n"
            "  --scope        Task scope/description (required)\n"
            "  --effort       Effort level: low, medium, high (optional)\n"
            "  --priority     Priority: low, normal, high (optional)\n"
            "  --spec-file    JSON spec file (alternative to CLI args)\n"
        )
        sys.exit(1)
    
    # Skip script name and command name
    args = sys.argv[2:] if len(sys.argv) > 2 and sys.argv[1] == "add-to-queue" else sys.argv[1:]
    
    result = add_to_queue_cli(args)
    
    print(result["message"])
    
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
