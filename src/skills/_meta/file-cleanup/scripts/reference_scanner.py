# -*- coding: utf-8 -*-
"""
reference_scanner.py — Find hidden references to files in code and documentation.

Scans for references in:
- Python imports (from X import, import X)
- String literals ("scripts/X.py", 'path/to/X')
- F-strings (f"scripts/{name}.py")
- Subprocess calls (subprocess.run([..., "scripts/X.py"]))
- Makefiles (python scripts/X.py)
- CI workflows (.github/workflows/*.yml)
- Jupyter notebooks (.ipynb)
- Bash scripts (scripts/*.sh)
- Documentation (*.md)
- Comments (# scripts/X.py)
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Reference:
    """A single reference to a file."""

    file_path: Path
    line_number: int
    context: str
    ref_type: str  # import | string | fstring | subprocess | comment | config | doc


class ReferenceScanner:
    """Scans code and documentation for references to files."""

    def __init__(self, root: Path) -> None:
        """Initialize scanner with repo root."""
        self.root = Path(root)
        self._protected_dirs = {".git", ".github/workflows", "venv", ".venv", "__pycache__"}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_all_references(self, script_name: str) -> List[Reference]:
        """
        Find all references to a script in the repository.
        
        Args:
            script_name: Name of the script (e.g., "cleanup.py" or "scripts/cleanup.py")
        
        Returns:
            List of Reference objects
        """
        results: List[Reference] = []

        # Build search patterns
        base_name = Path(script_name).name
        base_stem = Path(script_name).stem

        patterns = [
            re.escape(base_name),
            re.escape(base_stem),
        ]
        if "scripts/" not in script_name:
            patterns.append(re.escape(f"scripts/{base_name}"))

        # Walk all files in repo
        for file_path in self.root.rglob("*"):
            if not file_path.is_file():
                continue
            if self._is_in_protected_dir(file_path):
                continue
            if self._is_binary(file_path):
                continue
            if file_path.name == base_name:
                continue  # Skip the file itself

            refs = self._scan_file(file_path, patterns)
            results.extend(refs)

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_in_protected_dir(self, file_path: Path) -> bool:
        """Check if file is in a protected directory."""
        parts = {p.name for p in file_path.parents}
        protected = {".git", "venv", ".venv", "__pycache__"}
        return bool(parts & protected)

    def _is_binary(self, file_path: Path) -> bool:
        """Check if file is binary."""
        binary_extensions = {".pyc", ".so", ".png", ".jpg", ".gif", ".zip",
                              ".gz", ".tar", ".exe", ".bin", ".ico", ".svg"}
        return file_path.suffix.lower() in binary_extensions

    def _scan_file(self, file_path: Path, patterns: List[str]) -> List[Reference]:
        """Scan a single file for reference patterns."""
        refs: List[Reference] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return refs

        lines = content.splitlines()
        for line_num, line in enumerate(lines, 1):
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    ref_type = self._determine_ref_type(file_path, line)
                    refs.append(Reference(
                        file_path=file_path,
                        line_number=line_num,
                        context=line.strip(),
                        ref_type=ref_type,
                    ))
                    break  # Only one Reference per line

        return refs

    def _determine_ref_type(self, file_path: Path, line: str) -> str:
        """Determine the type of reference based on context."""
        line_lower = line.strip().lower()
        suffix = file_path.suffix.lower()

        if line_lower.startswith("#"):
            return "comment"
        if line_lower.startswith("import ") or line_lower.startswith("from "):
            return "import"
        if 'f"' in line or "f'" in line:
            return "fstring"
        if "subprocess" in line_lower or "popen" in line_lower:
            return "subprocess"
        if suffix in (".md", ".rst", ".txt"):
            return "doc"
        if file_path.name == "Makefile" or suffix in (".mk",):
            return "config"
        if suffix in (".yml", ".yaml"):
            return "config"
        return "string"
