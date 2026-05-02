#!/usr/bin/env python3
"""
Copilot CLI Agent Renderer
Converts src/agents/*.md to ~/.copilot/agents/*.agent.md with Copilot CLI spec compliance
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, Tuple

class CopilotAgentRenderer:
    """Renders source agent definitions to Copilot CLI agent profiles"""
    
    def __init__(self, src_dir: str, dest_dir: str):
        self.src_dir = Path(src_dir)
        self.dest_dir = Path(dest_dir)
        
        # Ensure destination exists
        self.dest_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_frontmatter(self, content: str) -> Tuple[Dict[str, str], str]:
        """Extract YAML frontmatter and body from markdown"""
        # Match frontmatter: --- at start, YAML, --- separator
        match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
        if not match:
            raise ValueError("File must start with YAML frontmatter (---)")
        
        yaml_block = match.group(1)
        body = match.group(2)
        
        # Parse YAML manually (simple key: value format)
        frontmatter = {}
        for line in yaml_block.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                frontmatter[key.strip()] = value.strip()
        
        return frontmatter, body
    
    def validate_frontmatter(self, frontmatter: Dict[str, str]) -> None:
        """Ensure required YAML fields are present"""
        required = ['name', 'description', 'model']
        missing = [f for f in required if f not in frontmatter]
        
        if missing:
            raise ValueError(f"Missing required frontmatter fields: {missing}")
    
    def render_agent(self, src_file: Path) -> None:
        """Render a single source agent to Copilot CLI format"""
        
        with open(src_file, 'r') as f:
            content = f.read()
        
        # Extract and validate
        frontmatter, body = self.extract_frontmatter(content)
        self.validate_frontmatter(frontmatter)
        
        # Build output filename: engineer.md → engineer.agent.md
        agent_name = src_file.stem
        dest_file = self.dest_dir / f"{agent_name}.agent.md"
        
        # Rebuild with clean frontmatter (spec-compliant)
        output = f"""---
name: {frontmatter['name']}
description: {frontmatter['description']}
model: {frontmatter['model']}
---

{body}"""
        
        # Write to destination
        with open(dest_file, 'w') as f:
            f.write(output)
        
        print(f"✅ Rendered: {src_file.name} → {dest_file.name}")
        return dest_file
    
    def render_all(self) -> int:
        """Render all source agents"""
        
        if not self.src_dir.exists():
            print(f"❌ Source directory not found: {self.src_dir}")
            return 1
        
        # Get all .md files except README
        all_files = list(self.src_dir.glob('*.md'))
        agent_files = [f for f in all_files if f.name != 'README.md']
        if not agent_files:
            print(f"❌ No agent definitions found in {self.src_dir}")
            return 1
        
        print(f"🎨 Rendering {len(agent_files)} agents from {self.src_dir}")
        print(f"📁 Output: {self.dest_dir}\n")
        
        rendered = 0
        errors = 0
        
        for src_file in sorted(agent_files):
            try:
                self.render_agent(src_file)
                rendered += 1
            except Exception as e:
                print(f"❌ Error rendering {src_file.name}: {e}")
                errors += 1
        
        print(f"\n✅ Rendering complete!")
        print(f"   {rendered} agents rendered, {errors} errors")
        
        if errors > 0:
            return 1
        
        return 0

def main():
    # Parse arguments
    if len(sys.argv) < 2:
        # Default: render to ~/.copilot/agents
        src_dir = 'src/agents'
        dest_dir = os.path.expanduser('~/.copilot/agents')
    else:
        src_dir = sys.argv[1]
        dest_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser('~/.copilot/agents')
    
    # Get absolute paths
    script_dir = Path(__file__).parent.parent
    src_path = (script_dir / src_dir).resolve()
    dest_path = Path(dest_dir).expanduser().resolve()
    
    print(f"\n{'='*60}")
    print(f"Copilot CLI Agent Renderer")
    print(f"{'='*60}\n")
    
    renderer = CopilotAgentRenderer(str(src_path), str(dest_path))
    exit_code = renderer.render_all()
    
    if exit_code == 0:
        print(f"✅ All agents ready for Copilot CLI!")
        print(f"📍 Location: {dest_path}")
        print(f"\nUsage in Copilot CLI:")
        print(f"  /agent                      # Select agent interactively")
        print(f"  copilot --agent=engineer    # Explicit selection")
        print(f"  Use the security-engineer   # Auto-inference in prompts")
    
    return exit_code

if __name__ == '__main__':
    sys.exit(main())
