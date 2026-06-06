#!/usr/bin/env python3
"""detect_circular_imports.py — Circular import detection gate (Phase 5.1+).

Scans all Python packages under src/ for circular import chains.
Uses a simple static analysis approach: parse ``import`` and ``from ... import``
statements and build a directed dependency graph, then run DFS cycle detection.

Exit codes:
    0 — No circular imports detected
    1 — One or more circular import chains found
    2 — Invocation error

Usage:
    python scripts/detect_circular_imports.py
    python scripts/detect_circular_imports.py --root src/skills
    python scripts/detect_circular_imports.py --verbose
"""
from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _iter_python_files(root: Path) -> Iterator[Path]:
    """Yield all .py files under *root*, skipping __pycache__ and _meta dirs."""
    for p in root.rglob("*.py"):
        if "__pycache__" in p.parts or "_meta" in p.parts:
            continue
        yield p


def _module_name(file: Path, root: Path) -> str:
    """Convert a file path to a dot-separated module name relative to *root*."""
    rel = file.relative_to(root)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _parse_imports(file: Path) -> List[str]:
    """Return absolute-ish import targets from a Python file.

    We collect:
    - ``import foo.bar`` → [``foo.bar``]
    - ``from foo.bar import baz`` → [``foo.bar``]

    Only intra-package imports (those starting with ``src.``) are returned to
    avoid flagging stdlib / third-party circular references.
    """
    try:
        source = file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(file))
    except SyntaxError:
        return []

    imports: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("src."):
                    imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0 and node.module.startswith("src."):
                imports.append(node.module)
    return imports


def build_graph(root: Path) -> Dict[str, Set[str]]:
    """Build a directed import graph: module → set of modules it imports."""
    graph: Dict[str, Set[str]] = defaultdict(set)
    src_root = root.parent  # so module names start with src.*

    for py_file in _iter_python_files(root):
        mod = _module_name(py_file, src_root)
        for imported in _parse_imports(py_file):
            if imported != mod:
                graph[mod].add(imported)

    return dict(graph)


# ---------------------------------------------------------------------------
# Cycle detection (DFS)
# ---------------------------------------------------------------------------

def find_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Return all elementary cycles as lists of module names (Johnson's alg, simplified)."""
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    cycles: List[List[str]] = []
    path: List[str] = []

    def dfs(node: str) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbour in graph.get(node, set()):
            if neighbour not in visited:
                dfs(neighbour)
            elif neighbour in rec_stack:
                # Found a cycle — extract it from path
                idx = path.index(neighbour)
                cycle = path[idx:] + [neighbour]
                # Deduplicate by canonical form
                canonical = tuple(sorted(cycle[:-1]))
                if canonical not in {tuple(sorted(c[:-1])) for c in cycles}:
                    cycles.append(cycle)

        path.pop()
        rec_stack.discard(node)

    for node in list(graph.keys()):
        if node not in visited:
            dfs(node)

    return cycles


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--root",
        default="src",
        help="Root directory to scan (default: src/)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print full import graph in addition to cycle report",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    scan_root = repo_root / args.root

    if not scan_root.is_dir():
        print(f"ERROR: --root directory not found: {scan_root}", file=sys.stderr)
        return 2

    print(f"Scanning for circular imports in: {scan_root}")
    graph = build_graph(scan_root)

    if args.verbose:
        print(f"\nImport graph ({len(graph)} modules with outgoing edges):")
        for mod, deps in sorted(graph.items()):
            for dep in sorted(deps):
                print(f"  {mod} → {dep}")

    cycles = find_cycles(graph)

    if not cycles:
        print(f"\n✅ No circular imports detected ({len(graph)} modules scanned).")
        return 0

    print(f"\n❌ Found {len(cycles)} circular import chain(s):\n")
    for i, cycle in enumerate(cycles, 1):
        print(f"  [{i}] " + " → ".join(cycle))

    print(
        f"\nFix: restructure imports to eliminate the cycle(s) above.\n"
        f"     Circular imports cause ImportError at runtime and slow startup.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
