#!/usr/bin/env python3
"""
Agent Definition Verifier (FIX #3)

Implements tri-level verification:
1. Git hook: Verify model_verification_sha in DELEGATE/HANDBACK
2. Schema field: Add model_verification_sha to DELEGATE schema
3. Runtime: Orchestrator verifies model exists in AGENTS.md before invoking

Usage:
    from agent_definition_verifier import generate_agents_sha256, verify_sha_matches
    
    sha = generate_agents_sha256("src/AGENTS.md")
    print(f"agent_sha256={sha}")
"""

import hashlib
import re
import sys
from pathlib import Path
from typing import Dict, Optional, Any


def generate_agents_sha256(agents_file: str) -> str:
    """
    Generate SHA256 hash of AGENTS.md file.
    
    Args:
        agents_file: Path to AGENTS.md file
        
    Returns:
        64-character hex string (SHA256 hash)
        
    Raises:
        FileNotFoundError: If file does not exist
    """
    agents_path = Path(agents_file)
    
    if not agents_path.exists():
        raise FileNotFoundError(f"Agents file not found: {agents_file}")
    
    # Read file content
    content = agents_path.read_text(encoding='utf-8')
    
    # Generate SHA256 hash
    sha256_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    return sha256_hash


def load_agents_manifest(agents_file: str) -> Dict[str, str]:
    """
    Load agent roster from AGENTS.md and extract role→model mapping.
    
    Parses the agent roster table and extracts:
    - Role (converted to snake_case)
    - Model (e.g., claude-opus-4.7)
    
    Args:
        agents_file: Path to AGENTS.md file
        
    Returns:
        Dictionary mapping role (snake_case) → model string
        
    Example:
        {
            "orchestrator": "claude-haiku-4.5",
            "engineer": "claude-haiku-4.5",
            "security_engineer": "claude-opus-4.7",
            ...
        }
    """
    agents_path = Path(agents_file)
    
    if not agents_path.exists():
        raise FileNotFoundError(f"Agents file not found: {agents_file}")
    
    content = agents_path.read_text(encoding='utf-8')
    
    roster = {}
    
    # Look for agent roster table (marked by header "Agent Roster" and table with Role/Model)
    # Table format:
    # | # | Role | Model | ...
    # |---|------|-------|...
    # | 1 | Orchestrator | claude-haiku-4.5 | ...
    
    # Split into lines and find table rows
    lines = content.split('\n')
    in_roster_table = False
    
    for line in lines:
        # Detect roster table start (header line with "Role" and "Model")
        if '| Role |' in line and '| Model |' in line:
            in_roster_table = True
            continue
        
        # Skip separator line (|---|---|...)
        if in_roster_table and line.strip().startswith('|---'):
            continue
        
        # Parse table rows
        if in_roster_table and line.strip().startswith('|'):
            # Extract columns: | # | Role | Model | ...
            parts = [p.strip() for p in line.split('|')]
            
            # Expected: ['', '#', 'Role Name', 'Model', ...]
            if len(parts) >= 4:
                role_col = parts[2].strip()
                model_col = parts[3].strip()
                
                # Skip header rows and separator rows
                if role_col.lower() == 'role' or not role_col:
                    continue
                
                # Clean up markdown formatting (**, `, etc.)
                role_col = role_col.replace('**', '').replace('`', '').strip()
                model_col = model_col.replace('**', '').replace('`', '').strip()
                
                # Convert role name to snake_case and lowercase
                role_key = role_col.replace(' ', '_').lower()
                
                # Extract just the model name (e.g., "claude-opus-4.7")
                model_name = model_col.strip()
                
                # Validate model looks reasonable (contains 'claude' or known pattern)
                if model_name and ('claude' in model_name.lower() or model_name.startswith('gpt')):
                    roster[role_key] = model_name
        
        # Stop when we hit another section heading
        if in_roster_table and line.strip().startswith('## ') and '## Agent Roster' not in line:
            in_roster_table = False
    
    return roster


def validate_agent_in_roster(role: str, model: str, agents_file: str) -> bool:
    """
    Validate that a role→model pair exists in AGENTS.md roster.
    
    Used to block model downgrade attacks:
    - SPEC says Security Engineer = Opus-4.7
    - Attacker claims Sonnet-4.6
    - Function checks AGENTS.md and rejects the downgrade
    
    Args:
        role: Role name (e.g., 'security-engineer', 'security_engineer')
        model: Model string (e.g., 'claude-opus-4.7')
        agents_file: Path to AGENTS.md file
        
    Returns:
        True if role→model pair is valid in current roster, False otherwise
    """
    # Normalize role name: 'security-engineer' → 'security_engineer'
    normalized_role = role.replace('-', '_').lower()
    
    try:
        roster = load_agents_manifest(agents_file)
    except FileNotFoundError:
        return False
    
    # Check if role exists in roster
    if normalized_role not in roster:
        return False
    
    # Check if model matches expected model for this role
    expected_model = roster[normalized_role]
    
    return model == expected_model


def verify_sha_matches(delegate: Dict[str, Any], current_agents_sha: str) -> bool:
    """
    Verify that DELEGATE's model_verification_sha matches current AGENTS.md SHA.
    
    Args:
        delegate: DELEGATE block (dict with task_id, role, model, model_verification_sha)
        current_agents_sha: Current SHA256 of AGENTS.md file
        
    Returns:
        True if delegate has matching SHA, False if missing or mismatched
    """
    if not isinstance(delegate, dict):
        return False
    
    # Check if model_verification_sha field exists
    if 'model_verification_sha' not in delegate:
        return False
    
    delegate_sha = delegate.get('model_verification_sha', '')
    
    # Must be exactly 64 hex characters
    if not isinstance(delegate_sha, str) or len(delegate_sha) != 64:
        return False
    
    # Check if it's valid hex
    try:
        int(delegate_sha, 16)
    except (ValueError, TypeError):
        return False
    
    # Compare SHAs
    return delegate_sha == current_agents_sha


def verify_handback_sha(handback: Dict[str, Any], current_agents_sha: str) -> bool:
    """
    Verify that HANDBACK's model_verification_sha matches current AGENTS.md SHA.
    
    Same logic as verify_sha_matches but for HANDBACK blocks.
    
    Args:
        handback: HANDBACK block
        current_agents_sha: Current SHA256 of AGENTS.md file
        
    Returns:
        True if handback has matching SHA, False if missing or mismatched
    """
    return verify_sha_matches(handback, current_agents_sha)


def validate_all_shas_in_queue(queue_dir: str, current_agents_sha: str) -> Dict[str, Any]:
    """
    Validate all DELEGATE/HANDBACK files in queue have matching model_verification_sha.
    
    Args:
        queue_dir: Path to queue directory containing DELEGATE/HANDBACK YAML files
        current_agents_sha: Current SHA256 of AGENTS.md
        
    Returns:
        Results dict with format:
        {
            "valid": [list of valid file paths],
            "invalid": [list of invalid file paths with reasons],
            "errors": [list of parse errors]
        }
    """
    queue_path = Path(queue_dir)
    results = {"valid": [], "invalid": [], "errors": []}
    
    if not queue_path.exists():
        results["errors"].append(f"Queue directory not found: {queue_dir}")
        return results
    
    # Find all YAML files
    yaml_files = list(queue_path.glob("*.yaml")) + list(queue_path.glob("*.yml"))
    
    for yaml_file in yaml_files:
        try:
            # Try to parse as YAML (basic parsing)
            import yaml
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
            
            if not isinstance(data, dict):
                results["invalid"].append({
                    "file": str(yaml_file),
                    "reason": "Not a valid YAML dict"
                })
                continue
            
            # Check for model_verification_sha
            if 'model_verification_sha' not in data:
                results["invalid"].append({
                    "file": str(yaml_file),
                    "reason": "Missing model_verification_sha field"
                })
                continue
            
            # Verify SHA matches
            if not verify_sha_matches(data, current_agents_sha):
                results["invalid"].append({
                    "file": str(yaml_file),
                    "reason": f"SHA mismatch. Expected {current_agents_sha}, got {data.get('model_verification_sha')}"
                })
                continue
            
            results["valid"].append(str(yaml_file))
            
        except Exception as e:
            results["errors"].append({
                "file": str(yaml_file),
                "error": str(e)
            })
    
    return results


if __name__ == "__main__":
    # Command-line interface for generating SHA
    if len(sys.argv) < 2:
        print("Usage: agent_definition_verifier.py <agents_file>")
        print("       agent_definition_verifier.py <agents_file> validate <delegate_file>")
        sys.exit(1)
    
    agents_file = sys.argv[1]
    
    if len(sys.argv) == 2:
        # Generate SHA
        try:
            sha = generate_agents_sha256(agents_file)
            print(f"agent_sha256={sha}")
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif len(sys.argv) >= 4 and sys.argv[2] == "validate":
        # Validate DELEGATE/HANDBACK
        delegate_file = sys.argv[3]
        try:
            sha = generate_agents_sha256(agents_file)
            
            # Load delegate
            import yaml
            with open(delegate_file, 'r') as f:
                delegate = yaml.safe_load(f)
            
            if verify_sha_matches(delegate, sha):
                print("✅ SHA verification PASSED")
                sys.exit(0)
            else:
                print("❌ SHA verification FAILED")
                sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
