"""workflow-review skill package."""
import importlib.util
from pathlib import Path

_script_path = Path(__file__).parent / "scripts" / "workflow_review.py"
_spec = importlib.util.spec_from_file_location("workflow_review", _script_path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

WorkflowReviewer = _module.WorkflowReviewer
WorkflowReport = _module.WorkflowReport

__all__ = ["WorkflowReviewer", "WorkflowReport"]
