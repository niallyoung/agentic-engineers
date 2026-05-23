#!/usr/bin/env python3
"""
pi.dev Harness Renderer
Renders agentic-engineers config into ~/.pi/agent/ for pi.dev integration

Generates:
- ~/.pi/agent/SYSTEM.md        — Complete system prompt (replaces pi default)
- ~/.pi/agent/AGENTS.md        — Global agent context and role definitions
- ~/.pi/agent/settings.json    — Model and UI settings
- ~/.pi/agent/pi.yml           — Sub-agent orchestration configuration
- ~/.pi/agent/SUB_AGENT_SETUP.md — User documentation for setup

Usage:
  python3 render-pi-dev.py [src_dir] [dest_dir] [--uninstall] [--status]

Examples:
  # Render from default source to ~/.pi
  python3 render-pi-dev.py
  
  # Render from custom source
  python3 render-pi-dev.py /path/to/source ~/.pi
  
  # Uninstall (remove managed files)
  python3 render-pi-dev.py ~/.pi --uninstall
  
  # Status check
  python3 render-pi-dev.py ~/.pi --status
"""

import os
import sys
import json
import shutil
import argparse
import time
from pathlib import Path
from typing import Dict, Tuple, List
from datetime import datetime


# ---------------------------------------------------------------------------
# ANSI color helpers — suppressed when NO_COLOR is set or stdout is not a TTY
# ---------------------------------------------------------------------------
def _use_color() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")

def _green(s: str) -> str:
    return f"\033[32m{s}\033[0m" if _use_color() else s

def _yellow(s: str) -> str:
    return f"\033[33m{s}\033[0m" if _use_color() else s

def _red(s: str) -> str:
    return f"\033[31m{s}\033[0m" if _use_color() else s

def _dim(s: str) -> str:
    return f"\033[2m{s}\033[0m" if _use_color() else s

# Graceful PyYAML import with fallback
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class PiDevRenderer:
    """Renders agentic-engineers config to pi.dev harness"""
    
    # Files that should be rendered
    MANAGED_FILES = [
        "SYSTEM.md",
        "AGENTS.md",
        "settings.json",
        "pi.yml",
        "SUB_AGENT_SETUP.md",
    ]
    
    # Files/dirs managed by Pi itself (never touch)
    PI_MANAGED = {
        "auth.json",
        "bin",
        "sessions",
    }
    
    def __init__(self, src_dir: str, dest_dir: str):
        self.src_dir = Path(src_dir)
        self.dest_dir = Path(dest_dir)
        self.agent_dir = self.dest_dir / "agent"
        # Do NOT create directories here — defer to render_all()
    
    def copy_file(self, src_name: str, dest_name: str = None) -> bool:
        """Copy a file from source to destination"""
        dest_name = dest_name or src_name
        src_file = self.src_dir / src_name
        dest_file = self.agent_dir / dest_name
        
        if not src_file.exists():
            print(f"❌ Source not found: {src_file}")
            return False
        
        try:
            with open(src_file, 'r') as f:
                content = f.read()
            
            with open(dest_file, 'w') as f:
                f.write(content)
            
            print(f"✅ Rendered: {src_name} → ~/.pi/agent/{dest_name}")
            return True
        except Exception as e:
            print(f"❌ Error rendering {src_name}: {e}")
            return False
    
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
    
    def validate_json(self, filename: str) -> bool:
        """Validate JSON file structure"""
        file_path = self.agent_dir / filename
        
        if not file_path.exists():
            return False
        
        try:
            with open(file_path, 'r') as f:
                json.load(f)
            print(f"✅ Validated: {filename} (valid JSON)")
            return True
        except json.JSONDecodeError as e:
            print(f"❌ JSON validation failed for {filename}: {e}")
            return False
    
    def _install_git_hooks(self) -> bool:
        """Install git hooks from source repo to enforce SDLC compliance
        
        Pi.dev harness: hooks are installed from REPO_ROOT/.githooks to enforce consistency.
        Returns True if hooks were installed or already present, False if not found.
        """
        import subprocess
        
        # Try to find the repo root by looking for .git directory
        repo_root = self.src_dir
        while repo_root != repo_root.parent:
            if (repo_root / ".git").exists():
                break
            repo_root = repo_root.parent
        
        if not (repo_root / ".git").exists():
            print(f"⚠️  Git repository not found (expected .git in {repo_root})")
            return False
        
        hooks_dir = repo_root / ".githooks"
        if not hooks_dir.exists():
            print(f"⚠️  Git hooks not found at {hooks_dir}")
            return False
        
        try:
            # Configure git to use .githooks directory
            subprocess.run(
                ["git", "-C", str(repo_root), "config", "core.hooksPath", ".githooks"],
                check=True,
                capture_output=True
            )
            
            # Make all hooks executable
            for hook_file in hooks_dir.glob("*"):
                if hook_file.is_file():
                    hook_file.chmod(0o755)
            
            print(f"✅ Git hooks installed (core.hooksPath = .githooks)")
            return True
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Failed to configure git hooks: {e}")
            return False
        except Exception as e:
            print(f"⚠️  Error installing git hooks: {e}")
            return False
    
    def render_all(self) -> int:
        """Render all config files"""
        
        if not self.src_dir.exists():
            print(f"{_red('❌')} Source directory not found: {self.src_dir}")
            print(f"    Working directory: {Path.cwd()}", file=sys.stderr)
            print(f"    Script location: {Path(__file__).resolve()}", file=sys.stderr)
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
        install_start = time.time()
        
        for filename in self.MANAGED_FILES:
            file_start = time.time()
            ok = self.copy_file(filename)
            elapsed = time.time() - file_start
            if ok:
                rendered += 1
                print(f"  {_green('✅')} {filename} {_dim(f'({elapsed:.2f}s)')}")
            else:
                errors += 1
        
        # Validate critical files
        print(f"\n{'='*70}")
        print("Validating rendered files...\n")
        
        self.validate_yaml("pi.yml")
        self.validate_json("settings.json")
        
        # Install git hooks from source repo
        print(f"\n{'='*70}")
        print("Installing git hooks...\n")
        
        hooks_installed = self._install_git_hooks()
        
        install_duration = time.time() - install_start
        print(f"\n{'='*70}")
        print(f"Rendering complete!")
        print(f"{_green('✅')} {rendered} files rendered, {_red('❌') if errors else ''}{errors} errors, hooks: {_green('✅') if hooks_installed else _yellow('⚠️')} {_dim(f'({install_duration:.1f}s total)')}")
        print(f"{'='*70}\n")
        
        if errors == 0:
            print(f"🎉 π.dev is ready for agentic-engineers!\n")
            print(f"To start using it:")
            print(f"  cd /path/to/your/project")
            print(f"  pi\n")
            print(f"Files loaded from: ~/.pi/agent/")
            print(f"  • SYSTEM.md - System prompt")
            print(f"  • AGENTS.md - Agent context")
            print(f"  • settings.json - Model settings")
            print(f"  • pi.yml - Sub-agent orchestration")
            print(f"  • SUB_AGENT_SETUP.md - Usage guide\n")
            return 0
        
        return 1
    
    def uninstall(self) -> int:
        """Remove managed files (keep Pi-managed files)"""
        
        print(f"\n{'='*70}")
        print(f"π.dev Harness Uninstaller")
        print(f"{'='*70}\n")
        
        if not self.agent_dir.exists():
            print(f"Nothing to uninstall: {self.agent_dir} not found")
            return 0
        
        removed = 0
        
        for filename in self.MANAGED_FILES:
            file_path = self.agent_dir / filename
            if file_path.exists():
                try:
                    file_path.unlink()
                    print(f"✅ Removed: {filename}")
                    removed += 1
                except Exception as e:
                    print(f"❌ Error removing {filename}: {e}")
        
        print(f"\n{'='*70}")
        print(f"✅ Uninstall complete! Removed {removed} files")
        print(f"\nPi-managed files preserved:")
        for item in self.PI_MANAGED:
            path = self.agent_dir / item
            if path.exists():
                print(f"  ✓ {item}")
        print(f"{'='*70}\n")
        
        return 0
    
    def status(self) -> int:
        """Check installation status"""
        
        print(f"\n{'='*70}")
        print(f"π.dev Installation Status")
        print(f"{'='*70}\n")
        
        if not self.agent_dir.exists():
            print(f"❌ Not installed: {self.agent_dir} not found\n")
            return 1
        
        print(f"Location: {self.agent_dir}\n")
        
        print(f"Managed files (agentic-engineers):")
        for filename in self.MANAGED_FILES:
            file_path = self.agent_dir / filename
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"  ✅ {filename:<25} ({size:>6} bytes)")
            else:
                print(f"  ❌ {filename:<25} (missing)")
        
        print(f"\nPi-managed files (do not modify):")
        for item in self.PI_MANAGED:
            path = self.agent_dir / item
            if path.exists():
                if path.is_dir():
                    print(f"  ✓ {item:<25} (directory)")
                else:
                    size = path.stat().st_size
                    print(f"  ✓ {item:<25} ({size:>6} bytes)")
            else:
                print(f"  ○ {item:<25} (not present)")
        
        print(f"\n{'='*70}\n")
        return 0


def main():
    # DEBUG: Detailed tracing for CI troubleshooting
    import os
    print(f"[DEBUG] main() called with argv={sys.argv}", file=sys.stderr)
    print(f"[DEBUG] CWD={os.getcwd()}, __file__={__file__}", file=sys.stderr)
    sys.stderr.flush()
    
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
    
    # DEBUG: Trace after successful parsing
    sys.stderr.write(f"[TRACE] parse_args() succeeded with: --src={args.src}, --dest={args.dest}, --uninstall={args.uninstall}, --status={args.status}, src_pos={args.src_pos}, dest_pos={args.dest_pos}\n")
    sys.stderr.flush()

    # Resolve source directory:
    # Priority: --src flag > src_pos (only if dest_pos also provided) > default
    # SECURITY FIX: Use robust path resolution that works in all environments
    #   1. Try __file__ resolution first (works in most cases)
    #   2. Fall back to cwd-based resolution if needed
    #   3. Search upward for pi-dev-src if all else fails
    
    def find_pi_dev_src():
        """Find pi-dev-src directory using multiple strategies"""
        results = []
        
        # Strategy 1: __file__-based resolution
        try:
            script_path = Path(__file__).resolve()
            candidate = script_path.parent.parent / "pi-dev-src"
            exists = candidate.exists()
            results.append(f"Strategy1(__file__={__file__}): {candidate} exists={exists}")
            if exists:
                return candidate
        except (NameError, AttributeError) as e:
            results.append(f"Strategy1 failed: {e}")
        
        # Strategy 2: Look in current working directory
        cwd_candidate = Path.cwd() / "renderer" / "pi-dev-src"
        cwd_exists = cwd_candidate.exists()
        results.append(f"Strategy2(cwd={Path.cwd()}): {cwd_candidate} exists={cwd_exists}")
        if cwd_exists:
            return cwd_candidate
        
        # Strategy 3: Search upward from current working directory
        current = Path.cwd()
        for i in range(5):  # Look up to 5 levels
            candidate = current / "renderer" / "pi-dev-src"
            candidate_exists = candidate.exists()
            results.append(f"Strategy3.{i}(current={current}): {candidate} exists={candidate_exists}")
            if candidate_exists:
                return candidate
            if current.parent == current:  # Reached filesystem root
                break
            current = current.parent
        
        # Log all strategies for debugging
        for r in results:
            sys.stderr.write(f"  find_pi_dev_src: {r}\n")
        sys.stderr.flush()
        
        # Default fallback (will fail with clear error in render_all())
        return Path.cwd() / "renderer" / "pi-dev-src"
    
    default_src = find_pi_dev_src()
    
    # SECURITY FIX: Handle missing HOME environment variable (containers, restricted envs)
    try:
        default_dest = Path.home() / ".pi"
    except RuntimeError:
        # Fallback if HOME is not set in restricted environments
        default_dest = Path("/tmp") / ".pi"
        print(f"⚠️  HOME not set, using fallback destination: {default_dest}", file=sys.stderr)

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
    
    # DEBUG: Trace resolved paths before creating renderer
    sys.stderr.write(f"[TRACE] Resolved paths: src_dir={src_dir} (exists={src_dir.exists()}), dest_dir={dest_dir}\n")
    sys.stderr.flush()

    renderer = PiDevRenderer(str(src_dir), str(dest_dir))
    
    # DEBUG: Trace final execution path
    if args.uninstall:
        sys.stderr.write(f"[TRACE] Executing: uninstall()\n")
        sys.stderr.flush()
        return renderer.uninstall()
    elif args.status:
        sys.stderr.write(f"[TRACE] Executing: status()\n")
        sys.stderr.flush()
        return renderer.status()
    else:
        sys.stderr.write(f"[TRACE] Executing: render_all()\n")
        sys.stderr.flush()
        return renderer.render_all()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        # Enhanced error diagnostics for CI/CD troubleshooting
        import traceback
        print(f"\n❌ FATAL ERROR: {e}", file=sys.stderr)
        print(f"\nEnvironment Diagnostics:", file=sys.stderr)
        print(f"  Python: {sys.version}", file=sys.stderr)
        print(f"  CWD: {os.getcwd()}", file=sys.stderr)
        print(f"  __file__: {__file__}", file=sys.stderr)
        print(f"  sys.argv: {sys.argv}", file=sys.stderr)
        print(f"  HOME: {os.environ.get('HOME', 'NOT SET')}", file=sys.stderr)
        print(f"\nTraceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
