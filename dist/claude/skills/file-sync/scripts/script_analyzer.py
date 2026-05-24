# -*- coding: utf-8 -*-
"""Script analyzer: Discover and analyze scripts in repository."""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ScriptMetadata:
    """Metadata about a discovered script."""

    path: Path
    name: str
    extension: str
    size_bytes: int = 0
    docstring: str = ""
    purpose: str = ""
    dependencies: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    cli_signature: Dict[str, Any] = field(default_factory=dict)
    lines_of_code: int = 0


class ScriptAnalyzer:
    """Analyze scripts to extract metadata."""

    # Sub-directories that contain scripts
    _SCRIPT_DIRS = ["scripts", "renderer", "tools", ".githooks"]
    # Supported extensions
    _EXTENSIONS = {".py", ".sh"}
    # Sub-directories to skip
    _SKIP_DIRS = {"__pycache__", ".git", "venv", ".venv", "node_modules"}

    def __init__(self, repo_root: Path) -> None:
        """Initialize analyzer with repository root."""
        self.repo_root = Path(repo_root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def discover_scripts(self) -> List[Path]:
        """Find all scripts in repo (scripts/, renderer/scripts/, tools/, .githooks/)."""
        scripts: List[Path] = []
        search_dirs = [self.repo_root / d for d in self._SCRIPT_DIRS]
        extensions = self._EXTENSIONS
        skip_dirs = self._SKIP_DIRS

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            for path in search_dir.rglob("*"):
                if path.is_file() and path.suffix in extensions:
                    # Skip __pycache__ or other skip directories anywhere in path
                    if any(skip_dir in [p.name for p in path.parents] for skip_dir in skip_dirs):
                        continue
                    scripts.append(path)

        return sorted(scripts)

    def analyze(self, script_path: Path) -> ScriptMetadata:
        """Parse script and extract metadata."""
        path = Path(script_path)
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            content = ""

        name = path.stem
        extension = path.suffix
        size_bytes = path.stat().st_size if path.exists() else 0

        docstring = self.extract_docstring(content)
        purpose = self.extract_purpose(docstring, path.name)
        dependencies = self.extract_dependencies(content)
        entry_points = self.extract_entry_points(content, extension)
        cli_signature = self.extract_cli_signature(content, extension)
        lines_of_code = self.count_lines_of_code(content)

        return ScriptMetadata(
            path=path,
            name=name,
            extension=extension,
            size_bytes=size_bytes,
            docstring=docstring,
            purpose=purpose,
            dependencies=dependencies,
            entry_points=entry_points,
            cli_signature=cli_signature,
            lines_of_code=lines_of_code,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def extract_docstring(self, content: str) -> str:
        """Extract module docstring."""
        # Try AST parse first (Python files)
        try:
            tree = ast.parse(content)
            doc = ast.get_docstring(tree)
            if doc:
                return doc
        except SyntaxError:
            pass

        # Fallback: regex for """ or ''' at start
        match = re.search(r'^"""(.+?)"""', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        match = re.search(r"^'''(.+?)'''", content, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Shell-style: first comment line after shebang
        lines = content.splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#!/"):
                continue
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()

        return ""

    def extract_purpose(self, docstring: str, filename: str) -> str:
        """Infer purpose from docstring or filename pattern."""
        if docstring:
            first_line = docstring.strip().splitlines()[0]
            return first_line

        # Derive from filename
        name_clean = filename.replace(".py", "").replace(".sh", "").replace("_", " ").replace("-", " ")
        return name_clean or "Unknown"

    def extract_dependencies(self, content: str) -> List[str]:
        """Find all imported modules."""
        deps: List[str] = []

        # Try AST for Python
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        deps.append(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        deps.append(node.module.split(".")[0])
        except SyntaxError:
            # Fallback: regex
            for match in re.finditer(r"^(?:from|import)\s+(\w+)", content, re.MULTILINE):
                deps.append(match.group(1))

        return sorted(set(deps))

    def extract_entry_points(self, content: str, lang: str) -> List[str]:
        """Find public functions/classes."""
        entry_points: List[str] = []

        if lang == ".py":
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if not node.name.startswith("_"):
                            entry_points.append(node.name)
            except SyntaxError:
                pass
        else:
            # Shell: find function definitions
            for match in re.finditer(r"^(\w+)\s*\(\)", content, re.MULTILINE):
                entry_points.append(match.group(1))

        return entry_points

    def extract_cli_signature(self, content: str, lang: str) -> Dict[str, Any]:
        """Detect CLI interface (argparse, click, etc)."""
        sig: Dict[str, Any] = {"has_cli": False}

        if lang == ".py":
            has_argparse = "argparse" in content
            has_click = "click" in content
            sig["has_argparse"] = has_argparse
            sig["has_click"] = has_click
            sig["has_cli"] = has_argparse or has_click
            sig["has_type_hints"] = " -> " in content or ": str" in content or ": int" in content or ": bool" in content or ": Path" in content or ": List" in content or ": Dict" in content or ": Optional" in content
            sig["has_error_handling"] = "try:" in content or "except " in content
        else:
            sig["has_argparse"] = False
            sig["has_click"] = False
            sig["has_type_hints"] = False
            sig["has_error_handling"] = False

        return sig

    def count_lines_of_code(self, content: str) -> int:
        """Count LOC excluding comments, blanks."""
        lines = content.splitlines()
        loc = 0
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = not in_docstring
                continue
            if in_docstring:
                continue
            if not stripped or stripped.startswith("#"):
                continue
            loc += 1
        return loc
