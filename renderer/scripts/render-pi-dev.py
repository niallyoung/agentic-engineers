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
import yaml
import shutil
from pathlib import Path
from typing import Dict, Tuple, List
from datetime import datetime


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
        
        # Ensure destination directories exist
        self.agent_dir.mkdir(parents=True, exist_ok=True)
    
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
        """Validate YAML file structure"""
        file_path = self.agent_dir / filename
        
        if not file_path.exists():
            return False
        
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
            print(f"❌ Source directory not found: {self.src_dir}")
            return 1
        
        print(f"\n{'='*70}")
        print(f"π.dev Harness Renderer (agentic-engineers)")
        print(f"{'='*70}\n")
        
        print(f"Source: {self.src_dir}")
        print(f"Destination: {self.agent_dir}\n")
        
        rendered = 0
        errors = 0
        
        for filename in self.MANAGED_FILES:
            if self.copy_file(filename):
                rendered += 1
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
        
        print(f"\n{'='*70}")
        print(f"Rendering complete!")
        print(f"✅ {rendered} files rendered, ❌ {errors} errors, hooks: {'✅' if hooks_installed else '⚠️'}")
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
    # Parse arguments
    uninstall_mode = "--uninstall" in sys.argv
    status_mode = "--status" in sys.argv
    
    # Remove flags from argv for positional arg parsing
    argv = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    
    if len(argv) < 1:
        # Default: render from renderer/pi-dev-src to ~/.pi
        script_dir = Path(__file__).parent.parent
        src_dir = script_dir / "pi-dev-src"
        dest_dir = Path.home() / ".pi"
    elif len(argv) == 1:
        # Single arg: could be source or destination
        # If it looks like a home dir path, treat as destination
        if "/.pi" in argv[0] or argv[0].endswith(".pi"):
            script_dir = Path(__file__).parent.parent
            src_dir = script_dir / "pi-dev-src"
            dest_dir = Path(argv[0])
        else:
            src_dir = Path(argv[0])
            dest_dir = Path.home() / ".pi"
    else:
        # Two args: source and destination
        src_dir = Path(argv[0])
        dest_dir = Path(argv[1])
    
    # Ensure paths are absolute
    src_dir = src_dir.resolve()
    dest_dir = dest_dir.resolve()
    
    renderer = PiDevRenderer(str(src_dir), str(dest_dir))
    
    if uninstall_mode:
        return renderer.uninstall()
    elif status_mode:
        return renderer.status()
    else:
        return renderer.render_all()


if __name__ == '__main__':
    sys.exit(main())
