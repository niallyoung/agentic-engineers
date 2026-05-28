#!/usr/bin/env python3
"""
Agent Verification Wrapper (src/orchestration/agent-verification.py)

Provides CLI interface for agent SHA verification.

Usage:
    python3 agent-verification.py generate <agents_file> [output_file]
    python3 agent-verification.py validate <agents_file> <delegate_file>
    python3 agent-verification.py validate-queue <agents_file> <incoming_dir> <done_dir>
    python3 agent-verification.py verify-model <role> <model> <agents_file>
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add skills directory to path
SKILL_DIR = Path(__file__).parent.parent / "skills" / "_meta" / "agent-definition-verifier" / "scripts"
sys.path.insert(0, str(SKILL_DIR))

from agent_definition_verifier import (
    generate_agents_sha256,
    verify_sha_matches,
    validate_agent_in_roster,
    validate_all_shas_in_queue
)


def cmd_generate(args):
    """Generate SHA256 of AGENTS.md and write to file"""
    if len(args) < 1:
        print("Usage: agent-verification.py generate <agents_file> [output_file]", file=sys.stderr)
        return False
    
    agents_file = args[0]
    output_file = args[1] if len(args) > 1 else ".agents_verification_sha"
    
    try:
        sha = generate_agents_sha256(agents_file)
        
        # Write to file
        timestamp = datetime.utcnow().isoformat() + "Z"
        content = f"agent_sha256={sha}\ngenerated_at={timestamp}\n"
        
        with open(output_file, 'w') as f:
            f.write(content)
        
        print(f"✅ SHA generated: {sha}")
        print(f"✅ Written to: {output_file}")
        return True
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return False


def cmd_validate(args):
    """Validate DELEGATE/HANDBACK SHA"""
    if len(args) < 2:
        print("Usage: agent-verification.py validate <agents_file> <delegate_file>", file=sys.stderr)
        return False
    
    agents_file = args[0]
    delegate_file = args[1]
    
    try:
        # Get current SHA
        current_sha = generate_agents_sha256(agents_file)
        
        # Load delegate
        import yaml
        with open(delegate_file, 'r') as f:
            delegate = yaml.safe_load(f)
        
        # Verify
        if verify_sha_matches(delegate, current_sha):
            print(f"✅ SHA verification PASSED")
            print(f"   File: {delegate_file}")
            print(f"   SHA:  {current_sha}")
            return True
        else:
            delegate_sha = delegate.get('model_verification_sha', 'MISSING')
            print(f"❌ SHA verification FAILED", file=sys.stderr)
            print(f"   File:     {delegate_file}", file=sys.stderr)
            print(f"   Expected: {current_sha}", file=sys.stderr)
            print(f"   Got:      {delegate_sha}", file=sys.stderr)
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return False


def cmd_validate_queue(args):
    """Validate all DELEGATE/HANDBACK files in queue"""
    if len(args) < 3:
        print("Usage: agent-verification.py validate-queue <agents_file> <incoming_dir> <done_dir>", file=sys.stderr)
        return False
    
    agents_file = args[0]
    incoming_dir = args[1]
    done_dir = args[2]
    
    try:
        # Get current SHA
        current_sha = generate_agents_sha256(agents_file)
        print(f"ℹ️  Current AGENTS.md SHA: {current_sha}")
        print()
        
        all_valid = True
        
        # Check incoming queue
        if os.path.exists(incoming_dir):
            print(f"📨 Checking incoming queue: {incoming_dir}")
            results = validate_all_shas_in_queue(incoming_dir, current_sha)
            
            if results["valid"]:
                print(f"  ✅ Valid: {len(results['valid'])} files")
                for f in results["valid"]:
                    print(f"    ✅ {Path(f).name}")
            
            if results["invalid"]:
                print(f"  ❌ Invalid: {len(results['invalid'])} files")
                for item in results["invalid"]:
                    print(f"    ❌ {Path(item['file']).name}: {item['reason']}")
                all_valid = False
            
            if results["errors"]:
                print(f"  ⚠️  Errors: {len(results['errors'])} files")
                for item in results["errors"]:
                    print(f"    ⚠️  {Path(item['file']).name}: {item['error']}")
        
        print()
        
        # Check done queue
        if os.path.exists(done_dir):
            print(f"📬 Checking done queue: {done_dir}")
            results = validate_all_shas_in_queue(done_dir, current_sha)
            
            if results["valid"]:
                print(f"  ✅ Valid: {len(results['valid'])} files")
                for f in results["valid"]:
                    print(f"    ✅ {Path(f).name}")
            
            if results["invalid"]:
                print(f"  ❌ Invalid: {len(results['invalid'])} files")
                for item in results["invalid"]:
                    print(f"    ❌ {Path(item['file']).name}: {item['reason']}")
                all_valid = False
            
            if results["errors"]:
                print(f"  ⚠️  Errors: {len(results['errors'])} files")
                for item in results["errors"]:
                    print(f"    ⚠️  {Path(item['file']).name}: {item['error']}")
        
        return all_valid
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return False


def cmd_verify_model(args):
    """Verify model is valid for role"""
    if len(args) < 3:
        print("Usage: agent-verification.py verify-model <role> <model> <agents_file>", file=sys.stderr)
        return False
    
    role = args[0]
    model = args[1]
    agents_file = args[2]
    
    try:
        if validate_agent_in_roster(role, model, agents_file):
            print(f"✅ Model verification PASSED")
            print(f"   Role:  {role}")
            print(f"   Model: {model}")
            return True
        else:
            print(f"❌ Model verification FAILED", file=sys.stderr)
            print(f"   Role:  {role}", file=sys.stderr)
            print(f"   Model: {model}", file=sys.stderr)
            print(f"   Reason: Model not valid for this role in AGENTS.md", file=sys.stderr)
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: agent-verification.py <command> [args...]", file=sys.stderr)
        print("", file=sys.stderr)
        print("Commands:", file=sys.stderr)
        print("  generate <agents_file> [output_file]", file=sys.stderr)
        print("  validate <agents_file> <delegate_file>", file=sys.stderr)
        print("  validate-queue <agents_file> <incoming_dir> <done_dir>", file=sys.stderr)
        print("  verify-model <role> <model> <agents_file>", file=sys.stderr)
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    handlers = {
        "generate": cmd_generate,
        "validate": cmd_validate,
        "validate-queue": cmd_validate_queue,
        "verify-model": cmd_verify_model,
    }
    
    if command not in handlers:
        print(f"❌ Unknown command: {command}", file=sys.stderr)
        sys.exit(1)
    
    try:
        success = handlers[command](args)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
