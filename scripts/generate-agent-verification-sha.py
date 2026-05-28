#!/usr/bin/env python3
"""Generate SHA256 of agent definitions for verification."""

import hashlib
import sys
from datetime import datetime
from pathlib import Path


def generate_agent_sha():
    """Generate SHA256 of agent definitions."""
    # Read src/orchestration/agents-manifest.yaml
    agents_file = Path("src/orchestration/agents-manifest.yaml")
    
    if not agents_file.exists():
        print(f"Error: {agents_file} not found", file=sys.stderr)
        sys.exit(1)
    
    # Calculate SHA256
    sha256 = hashlib.sha256(agents_file.read_bytes()).hexdigest()
    
    # Write to .agents_verification_sha
    verification_file = Path(".agents_verification_sha")
    verification_file.write_text(
        f"agent_sha256={sha256}\n"
        f"generated_at={datetime.now().isoformat()}\n"
    )
    
    print(f"✅ Generated agent verification SHA: {sha256}")
    return sha256


if __name__ == "__main__":
    generate_agent_sha()
