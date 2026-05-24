# -*- coding: utf-8 -*-
"""Reference detector: Find existing integration references."""

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Reference:
    """A reference to a script in the codebase."""

    file_path: Path
    line_number: int
    context: str


class ReferenceDetector:
    """Find existing integration references."""

    _SKIP_DIRS = {"__pycache__", ".git", "venv", ".venv"}

    def __init__(self, repo_root: Path) -> None:
        """Initialize detector with repository root."""
        self.repo_root = Path(repo_root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_references(self, script_name: str) -> List[Reference]:
        """Find all references to script in codebase."""
        references: List[Reference] = []
        references.extend(self.search_makefile(script_name))
        references.extend(self.search_ci_workflows(script_name))
        references.extend(self.search_python_imports(script_name))
        references.extend(self.search_documentation(script_name))
        return references

    # ------------------------------------------------------------------
    # Search locations
    # ------------------------------------------------------------------

    def search_makefile(self, script_name: str) -> List[Reference]:
        """Find script mentioned in Makefile targets."""
        references: List[Reference] = []
        makefile_path = self.repo_root / "Makefile"
        if not makefile_path.exists():
            return references

        try:
            content = makefile_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return references

        # Strip .py extension for matching
        script_base = script_name.replace(".py", "").replace(".sh", "")

        for i, line in enumerate(content.splitlines(), 1):
            if script_name in line or script_base in line:
                references.append(Reference(
                    file_path=makefile_path,
                    line_number=i,
                    context=line.strip(),
                ))

        return references

    def search_ci_workflows(self, script_name: str) -> List[Reference]:
        """Find script in .github/workflows/."""
        references: List[Reference] = []
        workflows_dir = self.repo_root / ".github" / "workflows"
        if not workflows_dir.exists():
            return references

        script_base = script_name.replace(".py", "").replace(".sh", "")
        workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))

        for workflow_file in workflow_files:
            try:
                content = workflow_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for i, line in enumerate(content.splitlines(), 1):
                if script_name in line or script_base in line:
                    references.append(Reference(
                        file_path=workflow_file,
                        line_number=i,
                        context=line.strip(),
                    ))

        return references

    def search_python_imports(self, script_name: str) -> List[Reference]:
        """Find 'from scripts.X import' or 'import scripts.X'."""
        references: List[Reference] = []
        script_base = script_name.replace(".py", "")

        import_patterns = [
            f"from scripts.{script_base}",
            f"import scripts.{script_base}",
            f"from .{script_base}",
        ]

        py_files = list(self.repo_root.rglob("*.py"))
        skip = self._SKIP_DIRS
        py_files = [p for p in py_files
                    if not any(s in [part.name for part in p.parents] for s in skip)]

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for i, line in enumerate(content.splitlines(), 1):
                for pattern in import_patterns:
                    if pattern in line:
                        references.append(Reference(
                            file_path=py_file,
                            line_number=i,
                            context=line.strip(),
                        ))
                        break

        return references

    def search_documentation(self, script_name: str) -> List[Reference]:
        """Find script mentioned in .md files."""
        references: List[Reference] = []
        script_base = script_name.replace(".py", "").replace(".sh", "")

        md_files = list(self.repo_root.rglob("*.md"))
        skip = self._SKIP_DIRS
        md_files = [p for p in md_files
                    if not any(s in [part.name for part in p.parents] for s in skip)]

        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for i, line in enumerate(content.splitlines(), 1):
                if script_name in line or script_base in line:
                    references.append(Reference(
                        file_path=md_file,
                        line_number=i,
                        context=line.strip(),
                    ))

        return references
