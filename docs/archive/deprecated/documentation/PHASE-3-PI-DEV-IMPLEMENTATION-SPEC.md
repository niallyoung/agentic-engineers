# Phase 3 — π.dev Harness Implementation Specification

**Task ID**: 2026-05-16-phase3-pi-dev-impl-spec  
**Author**: Senior Engineer  
**Date**: 2026-05-16  
**Status**: Specification Complete — Ready for Implementation  
**Source Analysis**: `docs/PI-DEV-RENDERER-ANALYSIS.md`  
**Target File**: `renderer/scripts/render-pi-dev.py`

---

## Executive Summary

This document provides detailed implementation specifications for the three highest-priority bugs in the π.dev harness renderer (`render-pi-dev.py`). All three bugs are confirmed through static code review and are documented in `docs/PI-DEV-RENDERER-ANALYSIS.md`. Two are classified HIGH priority (argument parsing heuristic, premature directory creation) and one MEDIUM (missing graceful error handling for the PyYAML dependency). Together they represent approximately 4–7 hours of implementation work and should be executed in the order presented here: Bug 2 first (trivial, highest impact per minute), Bug 3 second (defensive hardening), Bug 1 last (most invasive, requires shell wrapper update).

**Total estimated effort**: 3.75–5.75 hours  
**Recommended implementation order**: Bug 2 → Bug 3 → Bug 1  
**Files affected**: `renderer/scripts/render-pi-dev.py`, `renderer/render-pi.sh`

---

## Bug 1 — Argument Parsing Heuristic

### Classification
- **Priority**: HIGH  
- **Severity**: Silent misrouting (wrong source or destination silently used)  
- **Location**: `render-pi-dev.py`, `main()` function, lines 309–318  
- **Effort estimate**: 2–3 hours (includes shell wrapper update and tests)

### Root Cause Analysis

The `main()` function uses a string-matching heuristic to decide whether a single positional argument is a source directory or a destination directory:

```python
# Current code (lines 309–318) — BUGGY
elif len(argv) == 1:
    if "/.pi" in argv[0] or argv[0].endswith(".pi"):
        script_dir = Path(__file__).parent.parent
        src_dir = script_dir / "pi-dev-src"
        dest_dir = Path(argv[0])
    else:
        src_dir = Path(argv[0])
        dest_dir = Path.home() / ".pi"
```

This heuristic fails silently in at least two documented scenarios:

| Input | Expected | Actual |
|-------|----------|--------|
| `/home/user/.pi-backup/src` | Treat as source | Treated as destination ❌ |
| `/mnt/data/pi-config` | Treat as destination | Treated as source ❌ |

The failure is silent: no error is raised until a downstream file operation fails (e.g., source files not found, or writes going to an unexpected location). This makes the bug particularly dangerous in CI/CD pipelines or automated installs where the wrong path would be used without any immediate indication.

**Root cause**: The script was designed with a convenience shortcut (no explicit `--src`/`--dest` flags) that works for the common case (`~/.pi`) but breaks on any path that contains `.pi` in a non-terminal position or lacks `/.pi` entirely.

### Proposed Fix

Replace the heuristic with `argparse` explicit named flags while preserving backward-compatible positional arguments for existing callers. The key design principle is: **named flags are unambiguous; positional arguments should only be used when two args are provided (unambiguous src + dest)**.

#### Implementation

Replace the entire `main()` function argument parsing block (lines 296–328) with:

```python
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="π.dev Harness Renderer — renders agentic-engineers config to ~/.pi/agent/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Render from default source to ~/.pi
  python3 render-pi-dev.py

  # Render with explicit flags (unambiguous)
  python3 render-pi-dev.py --src /path/to/source --dest ~/.pi

  # Render with positional args (src then dest, backward-compatible)
  python3 render-pi-dev.py /path/to/source ~/.pi

  # Uninstall
  python3 render-pi-dev.py --uninstall
  python3 render-pi-dev.py --dest ~/.pi --uninstall

  # Status check
  python3 render-pi-dev.py --status
  python3 render-pi-dev.py --dest ~/.pi --status
        """
    )

    # Named flags (unambiguous, preferred)
    parser.add_argument(
        "--src",
        default=None,
        metavar="DIR",
        help="Source directory containing pi-dev-src files (default: renderer/pi-dev-src/)"
    )
    parser.add_argument(
        "--dest",
        default=None,
        metavar="DIR",
        help="Destination base directory (default: ~/.pi)"
    )

    # Mode flags
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove managed files from destination"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check installation status without making changes"
    )

    # Backward-compatible positional args (two-arg form only — no heuristic)
    parser.add_argument(
        "src_pos",
        nargs="?",
        default=None,
        metavar="SRC_DIR",
        help="Source directory (positional, use --src for clarity)"
    )
    parser.add_argument(
        "dest_pos",
        nargs="?",
        default=None,
        metavar="DEST_DIR",
        help="Destination directory (positional, use --dest for clarity)"
    )

    args = parser.parse_args()

    # Resolve source directory:
    # Priority: --src flag > src_pos (only if dest_pos also provided) > default
    script_dir = Path(__file__).parent.parent
    default_src = script_dir / "pi-dev-src"
    default_dest = Path.home() / ".pi"

    if args.src is not None:
        src_dir = Path(args.src)
    elif args.src_pos is not None and args.dest_pos is not None:
        # Two positional args: unambiguous (src, dest)
        src_dir = Path(args.src_pos)
    elif args.src_pos is not None and args.dest_pos is None:
        # Single positional arg: DEPRECATED heuristic path
        # Emit a deprecation warning and refuse to guess
        print(
            "⚠️  Ambiguous invocation: single positional argument provided.\n"
            "   Cannot determine if this is a source or destination directory.\n"
            "   Use explicit flags instead:\n"
            f"     --src {args.src_pos}   (if this is the source directory)\n"
            f"     --dest {args.src_pos}  (if this is the destination directory)\n",
            file=sys.stderr
        )
        return 2
    else:
        src_dir = default_src

    # Resolve destination directory:
    # Priority: --dest flag > dest_pos (only if src_pos also provided) > default
    if args.dest is not None:
        dest_dir = Path(args.dest)
    elif args.src_pos is not None and args.dest_pos is not None:
        dest_dir = Path(args.dest_pos)
    else:
        dest_dir = default_dest

    # Ensure paths are absolute
    src_dir = src_dir.resolve()
    dest_dir = dest_dir.resolve()

    renderer = PiDevRenderer(str(src_dir), str(dest_dir))

    if args.uninstall:
        return renderer.uninstall()
    elif args.status:
        return renderer.status()
    else:
        return renderer.render_all()
```

#### Shell Wrapper Update (`render-pi.sh`)

The shell wrapper must be updated to use explicit flags when invoking the Python renderer. Locate the invocation in `render-pi.sh` and update:

```bash
# Before (current — relies on positional heuristic):
python3 "$RENDERER" "$DEST_DIR" --status
python3 "$RENDERER" "$DEST_DIR" --uninstall
python3 "$RENDERER" "$SRC_DIR" "$DEST_DIR"

# After (explicit flags — unambiguous):
python3 "$RENDERER" --dest "$DEST_DIR" --status
python3 "$RENDERER" --dest "$DEST_DIR" --uninstall
python3 "$RENDERER" --src "$SRC_DIR" --dest "$DEST_DIR"
```

### Test Strategy

#### Unit Tests

```python
# tests/test_render_pi_dev_args.py

import pytest
import subprocess
import sys
from pathlib import Path

RENDERER = Path(__file__).parent.parent / "renderer/scripts/render-pi-dev.py"

def run_renderer(*args):
    """Run renderer with given args, return (returncode, stdout, stderr)"""
    result = subprocess.run(
        [sys.executable, str(RENDERER)] + list(args),
        capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr

class TestArgParsing:
    def test_no_args_uses_defaults(self, tmp_path):
        """Zero args: uses default src and ~/.pi dest"""
        # Just verify it doesn't crash with --help
        rc, out, err = run_renderer("--help")
        assert rc == 0
        assert "--src" in out
        assert "--dest" in out

    def test_explicit_src_flag(self, tmp_path):
        """--src flag is unambiguous"""
        rc, out, err = run_renderer("--src", str(tmp_path), "--dest", str(tmp_path), "--status")
        # Should not emit ambiguity warning
        assert "Ambiguous" not in err

    def test_explicit_dest_flag(self, tmp_path):
        """--dest flag is unambiguous"""
        rc, out, err = run_renderer("--dest", str(tmp_path), "--status")
        assert "Ambiguous" not in err

    def test_two_positional_args_unambiguous(self, tmp_path):
        """Two positional args (src dest) are unambiguous"""
        rc, out, err = run_renderer(str(tmp_path), str(tmp_path), "--status")
        assert "Ambiguous" not in err

    def test_single_positional_arg_rejected(self, tmp_path):
        """Single positional arg is now rejected with clear error"""
        rc, out, err = run_renderer(str(tmp_path))
        assert rc == 2
        assert "Ambiguous" in err
        assert "--src" in err or "--dest" in err

    def test_pi_path_no_longer_heuristic(self, tmp_path):
        """Path containing /.pi no longer triggers heuristic"""
        pi_path = tmp_path / ".pi-backup" / "src"
        pi_path.mkdir(parents=True)
        # Single arg with /.pi in path: should be rejected, not silently treated as dest
        rc, out, err = run_renderer(str(pi_path))
        assert rc == 2
        assert "Ambiguous" in err

    def test_uninstall_with_dest_flag(self, tmp_path):
        """--uninstall works with --dest flag"""
        rc, out, err = run_renderer("--dest", str(tmp_path), "--uninstall")
        # Should not crash; nothing to uninstall
        assert rc == 0

    def test_status_with_dest_flag(self, tmp_path):
        """--status works with --dest flag"""
        rc, out, err = run_renderer("--dest", str(tmp_path), "--status")
        # Should report not installed (no agent/ dir)
        assert rc in (0, 1)  # 1 = not installed, which is valid
```

#### Integration Test

```bash
# Verify render-pi.sh uses explicit flags
grep -n "python3.*RENDERER" renderer/render-pi.sh | grep -v "\-\-src\|\-\-dest" && echo "FAIL: still using positional args" || echo "PASS: using explicit flags"
```

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Existing callers using single positional arg break | Low–Medium | Deprecation warning with clear migration message (exit code 2) |
| `render-pi.sh` not updated in sync | Medium | Shell wrapper test in CI catches this |
| `--help` output confuses users with both positional + named flags | Low | Clear epilog with examples; positional args documented as "legacy" |

### Rollback Strategy

The old `main()` function is self-contained. If the new `argparse`-based implementation causes regressions, revert lines 296–328 to the original. No other code in the file is affected by this change.

### Acceptance Criteria

- [ ] `python3 render-pi-dev.py --src /path/to/src --dest ~/.pi` works correctly
- [ ] `python3 render-pi-dev.py --dest ~/.pi --status` works correctly
- [ ] `python3 render-pi-dev.py /some/.pi-backup/src` exits with code 2 and clear error
- [ ] `python3 render-pi-dev.py /src /dest` (two positional args) works correctly
- [ ] `render-pi.sh` updated to use `--src`/`--dest` flags
- [ ] All unit tests in `tests/test_render_pi_dev_args.py` pass
- [ ] `python3 render-pi-dev.py --help` shows clear usage with examples

---

## Bug 2 — Premature Directory Creation in `__init__`

### Classification
- **Priority**: HIGH  
- **Severity**: False-positive status reports; spurious directory creation on clean systems  
- **Location**: `render-pi-dev.py`, `PiDevRenderer.__init__()`, line 65  
- **Effort estimate**: 15–30 minutes (one line moved, one test added)

### Root Cause Analysis

The `PiDevRenderer` constructor unconditionally creates `~/.pi/agent/` regardless of the operation that will follow:

```python
# Current code (lines 59–65) — BUGGY
def __init__(self, src_dir: str, dest_dir: str):
    self.src_dir = Path(src_dir)
    self.dest_dir = Path(dest_dir)
    self.agent_dir = self.dest_dir / "agent"
    
    # Ensure destination directories exist
    self.agent_dir.mkdir(parents=True, exist_ok=True)  # ← BUG: runs for ALL modes
```

The constructor is called unconditionally in `main()` (line 328) before the mode is dispatched. This means `~/.pi/agent/` is created even when the user runs `--status` or `--uninstall` on a clean system.

**Concrete failure**: `status()` checks `if not self.agent_dir.exists()` (line 265) to determine if the harness is installed. Because `__init__` already created the directory, this check always returns `False` (directory exists), so `status()` never reports "Not installed" — it reports "installed" with all files missing. This is a false positive that misleads users.

**Secondary failure**: `--uninstall` on a clean system creates `~/.pi/agent/` and then immediately reports "Uninstall complete! Removed 0 files" — technically correct but misleading, and leaves a spurious empty directory.

### Proposed Fix

Move the `mkdir` call from `__init__` to `render_all()` only. The constructor should be side-effect-free; directory creation is an implementation detail of the install operation.

#### Implementation

**Step 1**: Remove `mkdir` from `__init__`:

```python
# Fixed __init__ (lines 59–65)
def __init__(self, src_dir: str, dest_dir: str):
    self.src_dir = Path(src_dir)
    self.dest_dir = Path(dest_dir)
    self.agent_dir = self.dest_dir / "agent"
    # Do NOT create directories here — defer to render_all()
```

**Step 2**: Add `mkdir` to `render_all()`, before the file copy loop:

```python
# Fixed render_all() — add mkdir at start of install operation
def render_all(self) -> int:
    """Render all config files"""
    
    if not self.src_dir.exists():
        print(f"❌ Source directory not found: {self.src_dir}")
        return 1
    
    print(f"\n{'='*70}")
    print(f"π.dev Harness Renderer (agentic-engineers)")
    print(f"{'='*70}\n")
    
    print(f"Source: {self.src_dir}")
    print(f"Destination: {self.agent_dir}\n")
    
    # Create destination directory only when actually rendering (not in __init__)
    self.agent_dir.mkdir(parents=True, exist_ok=True)
    
    rendered = 0
    errors = 0
    # ... rest of method unchanged ...
```

**Step 3**: Verify `status()` and `uninstall()` do not call `mkdir` — they do not (confirmed by code review). No changes needed to those methods.

This is a **one-line change**: remove line 65 from `__init__`, add the same line as the first statement inside `render_all()` after the source directory check.

### Test Strategy

#### Unit Tests

```python
# tests/test_render_pi_dev_mkdir.py

import pytest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "renderer/scripts"))

from render_pi_dev import PiDevRenderer  # adjust import to match actual module name

class TestPrematureMkdir:
    def test_init_does_not_create_directory(self, tmp_path):
        """Constructor must not create agent_dir"""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        
        renderer = PiDevRenderer(str(src), str(dest))
        
        # agent_dir should NOT exist after construction
        assert not renderer.agent_dir.exists(), (
            f"agent_dir {renderer.agent_dir} was created by __init__ — "
            "this is the premature mkdir bug"
        )

    def test_status_does_not_create_directory(self, tmp_path):
        """--status on clean system must not create agent_dir"""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        
        renderer = PiDevRenderer(str(src), str(dest))
        renderer.status()
        
        assert not renderer.agent_dir.exists(), (
            "status() created agent_dir — should be read-only"
        )

    def test_status_reports_not_installed_on_clean_system(self, tmp_path, capsys):
        """--status on clean system must report 'Not installed', not false positive"""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        
        renderer = PiDevRenderer(str(src), str(dest))
        rc = renderer.status()
        
        captured = capsys.readouterr()
        assert "Not installed" in captured.out or rc == 1, (
            "status() returned false positive on clean system"
        )

    def test_uninstall_does_not_create_directory(self, tmp_path):
        """--uninstall on clean system must not create agent_dir"""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        
        renderer = PiDevRenderer(str(src), str(dest))
        renderer.uninstall()
        
        assert not renderer.agent_dir.exists(), (
            "uninstall() created agent_dir on clean system"
        )

    def test_render_all_creates_directory(self, tmp_path):
        """render_all() must create agent_dir (install operation)"""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        
        # Create minimal source files
        for f in ["SYSTEM.md", "AGENTS.md", "settings.json", "pi.yml", "SUB_AGENT_SETUP.md"]:
            (src / f).write_text(f"# {f}\n" if f.endswith(".md") else "{}" if f.endswith(".json") else "")
        (src / "pi.yml").write_text("version: 1\n")
        (src / "settings.json").write_text('{"model": "test"}')
        
        renderer = PiDevRenderer(str(src), str(dest))
        renderer.render_all()
        
        assert renderer.agent_dir.exists(), (
            "render_all() did not create agent_dir — install broken"
        )
```

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `copy_file()` called without `mkdir` having run | Low | `copy_file()` is only called from `render_all()`, which now calls `mkdir` first |
| `validate_yaml()`/`validate_json()` fail if dir missing | Low | These are called after `copy_file()` in `render_all()`, so dir exists |
| Other callers of `PiDevRenderer.__init__()` assume dir exists | Very Low | Only `main()` instantiates the class; no external callers |

### Rollback Strategy

Add back `self.agent_dir.mkdir(parents=True, exist_ok=True)` to `__init__` and remove it from `render_all()`. This is a two-line revert. The change is fully reversible with no data loss risk.

### Acceptance Criteria

- [ ] `PiDevRenderer.__init__()` does not call `mkdir` or create any directories
- [ ] `python3 render-pi-dev.py --status` on a clean system (no `~/.pi/agent/`) reports "Not installed" (exit code 1) without creating the directory
- [ ] `python3 render-pi-dev.py --uninstall` on a clean system reports "Nothing to uninstall" without creating the directory
- [ ] `python3 render-pi-dev.py` (install) still creates `~/.pi/agent/` and renders all 5 files
- [ ] All unit tests in `tests/test_render_pi_dev_mkdir.py` pass

---

## Bug 3 — Missing Graceful Error Handling for PyYAML Dependency

### Classification
- **Priority**: MEDIUM  
- **Severity**: Hard crash (`ImportError`) on systems without PyYAML installed  
- **Location**: `render-pi-dev.py`, line 33 (`import yaml`)  
- **Effort estimate**: 30–60 minutes (import guard + fallback + documentation)

### Root Cause Analysis

The renderer imports PyYAML unconditionally at module load time:

```python
# Current code (line 33) — BUGGY
import yaml
```

PyYAML is not part of the Python standard library. On minimal Python environments (fresh virtualenvs, CI containers, some Linux distributions), this import fails with:

```
ModuleNotFoundError: No module named 'yaml'
```

This crash occurs before `main()` is even called, so the user sees no helpful error message — just a raw Python traceback. The crash affects all modes: install, uninstall, and status. A user who simply wants to check `--status` cannot do so without first installing a third-party package.

The PyYAML dependency is also undocumented in `PI-DEV-RENDERER.md`, so users have no advance warning.

**Scope of use**: PyYAML is used only in `validate_yaml()` (lines 90–104), which is called only during `render_all()`. It is not needed for `--status` or `--uninstall` modes. This makes the unconditional import particularly wasteful — two of three modes don't need it.

### Proposed Fix

Replace the unconditional `import yaml` with a lazy import guard that:
1. Attempts to import PyYAML at module load
2. Sets a flag (`YAML_AVAILABLE`) indicating whether it's available
3. Falls back gracefully in `validate_yaml()` if PyYAML is absent
4. Prints a clear, actionable warning rather than a traceback

#### Implementation

**Step 1**: Replace unconditional import (line 33) with a guarded import:

```python
# Replace line 33:
#   import yaml
# With:

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
```

**Step 2**: Update `validate_yaml()` to handle the missing dependency gracefully:

```python
def validate_yaml(self, filename: str) -> bool:
    """Validate YAML file structure.
    
    Returns True if valid, False if invalid.
    Returns True (with warning) if PyYAML is not installed — validation skipped.
    """
    file_path = self.agent_dir / filename
    
    if not file_path.exists():
        return False
    
    if not YAML_AVAILABLE:
        print(
            f"⚠️  Skipping YAML validation for {filename}: "
            "PyYAML not installed.\n"
            "   Install it with: pip install pyyaml\n"
            "   (YAML validation is optional — install will proceed)"
        )
        return True  # Non-fatal: proceed without validation
    
    try:
        with open(file_path, 'r') as f:
            yaml.safe_load(f)
        print(f"✅ Validated: {filename} (valid YAML)")
        return True
    except yaml.YAMLError as e:
        print(f"❌ YAML validation failed for {filename}: {e}")
        return False
```

**Step 3**: Update `PI-DEV-RENDERER.md` to document the dependency:

Add a "Prerequisites" section to `PI-DEV-RENDERER.md`:

```markdown
## Prerequisites

- **Python 3.8+** — required
- **PyYAML** — optional but recommended (enables YAML validation of `pi.yml`)
  ```bash
  pip install pyyaml
  # or: pip3 install pyyaml
  ```
  Without PyYAML, the renderer will skip YAML validation and print a warning.
  All other functionality (file rendering, JSON validation, status, uninstall) works without it.
```

#### Alternative: Inline YAML Validation Without PyYAML

For environments where pip is unavailable, a minimal YAML syntax check can be performed without PyYAML by checking for common YAML syntax errors (unclosed brackets, tab indentation). This is a lower-fidelity fallback but provides some protection:

```python
def _validate_yaml_basic(self, content: str, filename: str) -> bool:
    """Minimal YAML syntax check without PyYAML (fallback only)."""
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        if '\t' in line and not line.strip().startswith('#'):
            print(f"⚠️  {filename} line {i}: tab indentation (YAML requires spaces)")
            return False
    return True
```

This fallback is optional and should only be added if the team decides PyYAML is too heavy a dependency. The primary fix (graceful ImportError handling) is sufficient.

### Test Strategy

#### Unit Tests

```python
# tests/test_render_pi_dev_yaml.py

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

class TestYamlFallback:
    def test_validate_yaml_skips_gracefully_without_pyyaml(self, tmp_path, capsys):
        """validate_yaml() must not crash when PyYAML is unavailable"""
        # Simulate PyYAML not installed
        with patch.dict(sys.modules, {'yaml': None}):
            # Re-import module with yaml unavailable
            import importlib
            # This test verifies the behavior when YAML_AVAILABLE = False
            
            src = tmp_path / "src"
            dest = tmp_path / "dest"
            src.mkdir()
            agent_dir = dest / "agent"
            agent_dir.mkdir(parents=True)
            
            # Create a valid YAML file
            (agent_dir / "pi.yml").write_text("version: 1\nagents: []\n")
            
            # Import renderer with mocked YAML_AVAILABLE = False
            import render_pi_dev as renderer_module
            original = renderer_module.YAML_AVAILABLE
            renderer_module.YAML_AVAILABLE = False
            
            try:
                from render_pi_dev import PiDevRenderer
                r = PiDevRenderer(str(src), str(dest))
                result = r.validate_yaml("pi.yml")
                
                captured = capsys.readouterr()
                assert result is True, "validate_yaml should return True (non-fatal) when PyYAML unavailable"
                assert "pip install pyyaml" in captured.out, "Should print install instructions"
                assert "Skipping" in captured.out, "Should indicate validation was skipped"
            finally:
                renderer_module.YAML_AVAILABLE = original

    def test_validate_yaml_works_with_pyyaml(self, tmp_path):
        """validate_yaml() works normally when PyYAML is available"""
        pytest.importorskip("yaml", reason="PyYAML not installed — skipping positive test")
        
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        agent_dir = dest / "agent"
        agent_dir.mkdir(parents=True)
        
        (agent_dir / "pi.yml").write_text("version: 1\nagents: []\n")
        
        from render_pi_dev import PiDevRenderer
        r = PiDevRenderer(str(src), str(dest))
        assert r.validate_yaml("pi.yml") is True

    def test_validate_yaml_fails_on_invalid_yaml(self, tmp_path):
        """validate_yaml() returns False for invalid YAML (when PyYAML available)"""
        pytest.importorskip("yaml", reason="PyYAML not installed — skipping")
        
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        agent_dir = dest / "agent"
        agent_dir.mkdir(parents=True)
        
        (agent_dir / "pi.yml").write_text("key: [unclosed bracket\n")
        
        from render_pi_dev import PiDevRenderer
        r = PiDevRenderer(str(src), str(dest))
        assert r.validate_yaml("pi.yml") is False

    def test_import_succeeds_without_pyyaml(self):
        """render-pi-dev.py must be importable even without PyYAML"""
        # This test verifies the module-level import guard works
        # If the module crashes on import, this test will fail with ImportError
        with patch.dict(sys.modules, {'yaml': None}):
            try:
                import importlib
                import render_pi_dev
                importlib.reload(render_pi_dev)
                assert render_pi_dev.YAML_AVAILABLE is False
            except ImportError as e:
                pytest.fail(f"Module failed to import without PyYAML: {e}")
```

#### Integration Test

```bash
# Verify renderer runs without PyYAML installed
python3 -c "
import sys
sys.modules['yaml'] = None  # Simulate missing PyYAML
import importlib.util
spec = importlib.util.spec_from_file_location('render_pi_dev', 'renderer/scripts/render-pi-dev.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('PASS: Module loads without PyYAML')
print(f'YAML_AVAILABLE = {mod.YAML_AVAILABLE}')
"
```

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `validate_yaml()` returning `True` for invalid YAML when PyYAML absent | Low | Warning is printed; user is informed validation was skipped |
| Invalid `pi.yml` shipped to `~/.pi/agent/` without detection | Low | Source files are validated in CI where PyYAML is available |
| Module-level `YAML_AVAILABLE` flag not thread-safe | Very Low | Single-threaded script; no concurrency concerns |

### Rollback Strategy

Revert to `import yaml` (unconditional) and remove the `YAML_AVAILABLE` guard. This restores the original hard-crash behavior. No data is affected; this is a pure code change.

### Acceptance Criteria

- [ ] `render-pi-dev.py` imports successfully in a Python environment without PyYAML
- [ ] `python3 render-pi-dev.py --status` works without PyYAML (no crash)
- [ ] `python3 render-pi-dev.py --uninstall` works without PyYAML (no crash)
- [ ] `python3 render-pi-dev.py` (install) works without PyYAML, prints warning about skipped YAML validation
- [ ] `YAML_AVAILABLE = False` when PyYAML is absent
- [ ] `PI-DEV-RENDERER.md` has a "Prerequisites" section documenting the optional PyYAML dependency
- [ ] All unit tests in `tests/test_render_pi_dev_yaml.py` pass

---

## Consolidated Implementation Plan

### Recommended Implementation Order

**Phase 3 Week 1 — Execute in this sequence:**

| Step | Bug | Rationale |
|------|-----|-----------|
| 1 | Bug 2 (Premature mkdir) | 15–30 min; highest impact-per-minute; zero risk |
| 2 | Bug 3 (PyYAML fallback) | 30–60 min; defensive hardening; zero risk |
| 3 | Bug 1 (Argument parsing) | 2–3 hours; most invasive; requires shell wrapper update |

**Rationale for order**: Bug 2 is a one-line fix with immediate correctness improvement and no risk of regression. Bug 3 is a small defensive improvement that makes the tool more robust before the larger Bug 1 refactor. Bug 1 is last because it changes the public interface (argument parsing), requires coordinated updates to `render-pi.sh`, and has the highest regression risk.

### Consolidated Effort Estimate

| Bug | Min | Max | Notes |
|-----|-----|-----|-------|
| Bug 2 — Premature mkdir | 0.25 hr | 0.5 hr | One line moved; one test file |
| Bug 3 — PyYAML fallback | 0.5 hr | 1.0 hr | Import guard + fallback + docs update |
| Bug 1 — Argument parsing | 2.0 hr | 3.0 hr | argparse refactor + shell wrapper + tests |
| **Total** | **2.75 hr** | **4.5 hr** | |

### Files Changed

| File | Bugs | Change Type |
|------|------|-------------|
| `renderer/scripts/render-pi-dev.py` | 1, 2, 3 | Modified |
| `renderer/render-pi.sh` | 1 | Modified (flag update) |
| `renderer/PI-DEV-RENDERER.md` | 3 | Modified (Prerequisites section) |
| `tests/test_render_pi_dev_args.py` | 1 | New |
| `tests/test_render_pi_dev_mkdir.py` | 2 | New |
| `tests/test_render_pi_dev_yaml.py` | 3 | New |

### Consolidated Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Bug 1 breaks existing `render-pi.sh` callers | Medium | High | Update shell wrapper in same PR; test both |
| Bug 2 breaks `copy_file()` if called before `mkdir` | Low | Medium | `copy_file()` only called from `render_all()` which now owns `mkdir` |
| Bug 3 masks invalid `pi.yml` in dev environments | Low | Low | CI has PyYAML; warning is printed |
| Test files import `render-pi-dev.py` with hyphens in name | Medium | Low | Use `importlib.util.spec_from_file_location()` or rename to `render_pi_dev.py` |

### Rollback Strategy (Consolidated)

All three bugs are isolated to `render-pi-dev.py` and `render-pi.sh`. A single `git revert` of the implementation commit restores the original behavior. No database migrations, no config changes, no external system effects. The changes are purely internal to the renderer script.

---

## Appendix: Current Code State (Pre-Fix)

For reference, the three bug locations in the current `render-pi-dev.py`:

```python
# BUG 2: Line 65 — premature mkdir in __init__
self.agent_dir.mkdir(parents=True, exist_ok=True)

# BUG 3: Line 33 — unconditional PyYAML import
import yaml

# BUG 1: Lines 309–318 — argument parsing heuristic
elif len(argv) == 1:
    if "/.pi" in argv[0] or argv[0].endswith(".pi"):
        ...
    else:
        ...
```

All three fixes are surgical and do not require changes to the core file-copy logic, validation logic, or uninstall logic. The renderer's fundamental correctness (5 files copied, YAML/JSON validated, marker file managed by shell wrapper) is unaffected.

---

*Specification complete. Ready for Engineer delegation with pre-written plan.*  
*Next step: Orchestrator delegates Bug 2 → Bug 3 → Bug 1 to Engineer with this spec as the plan.*
