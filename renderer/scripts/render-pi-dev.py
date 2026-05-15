#!/usr/bin/env python3
"""
pi.dev Harness Renderer
Renders agentic-engineers config into ~/.pi/agent/ for pi.dev integration

Generates:
- ~/.pi/agent/SYSTEM.md    — Complete system prompt (replaces pi default)
- ~/.pi/agent/AGENTS.md    — Global agent context and role definitions
- ~/.pi/agent/settings.json — Model and UI settings
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Tuple


class PiDevRenderer:
    """Renders agentic-engineers config to pi.dev harness"""
    
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
        
        files_to_render = [
            ("SYSTEM.md", "SYSTEM.md"),
            ("AGENTS.md", "AGENTS.md"),
            ("settings.json", "settings.json"),
        ]
        
        rendered = 0
        errors = 0
        
        for src_name, dest_name in files_to_render:
            if self.copy_file(src_name, dest_name):
                rendered += 1
            else:
                errors += 1
        
        print(f"\n{'='*70}")
        print(f"Rendering complete!")
        print(f"✅ {rendered} files rendered, ❌ {errors} errors")
        print(f"{'='*70}\n")
        
        if errors == 0:
            print(f"🎉 π.dev is ready for agentic-engineers!\n")
            print(f"To start using it:")
            print(f"  cd /path/to/your/project")
            print(f"  pi\n")
            print(f"System prompt will be loaded from: ~/.pi/agent/SYSTEM.md")
            print(f"Agent context from: ~/.pi/agent/AGENTS.md")
            print(f"Model settings from: ~/.pi/agent/settings.json")
            return 0
        
        return 1


def main():
    # Parse arguments
    if len(sys.argv) < 2:
        # Default: render from renderer/pi-dev-src to ~/.pi
        script_dir = Path(__file__).parent.parent
        src_dir = script_dir / "pi-dev-src"
        dest_dir = Path.home() / ".pi"
    else:
        src_dir = Path(sys.argv[1])
        dest_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home() / ".pi"
    
    # Ensure paths are absolute
    src_dir = src_dir.resolve()
    dest_dir = dest_dir.resolve()
    
    renderer = PiDevRenderer(str(src_dir), str(dest_dir))
    return renderer.render_all()


if __name__ == '__main__':
    sys.exit(main())
