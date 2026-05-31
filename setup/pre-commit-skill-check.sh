#!/bin/bash
#
# Pre-commit hook for skill standardization checks
#
# Enforces:
# - SKILL.md structure compliance
# - ≥85% test coverage per skill
# - Type hints on all functions
# - Docstrings on all public functions
# - Linting compliance (black, flake8)
#
# This hook blocks commits that violate standardization requirements.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Paths
REPO_ROOT="$(git rev-parse --show-toplevel)"
STANDARDIZATION_DIR="${REPO_ROOT}/src/standardization"
HOOK_LOG="${REPO_ROOT}/.git/hooks/skill-check.log"

# Configuration
MIN_COVERAGE=85
MAX_VIOLATIONS=0

echo "Running skill standardization checks..." | tee -a "${HOOK_LOG}"

# Check if we have changes to SKILL.md files
CHANGED_SKILLS=$(git diff --cached --name-only | grep -E "SKILL.md$" || true)

if [ -z "$CHANGED_SKILLS" ]; then
    echo "No SKILL.md files changed, skipping skill checks"
    exit 0
fi

echo "Found $(echo "$CHANGED_SKILLS" | wc -l) changed SKILL.md files"

# Run Python standardization checks
python3 << 'EOF'
import sys
from pathlib import Path

# Add repo to path
repo_root = Path.cwd()
sys.path.insert(0, str(repo_root))

from src.standardization import (
    SkillStandardizer,
    QualityEnforcer,
    ComplianceLevel,
)

def check_skills():
    """Run standardization checks on changed skills."""
    standardizer = SkillStandardizer(repo_root)
    
    # Get changed SKILL.md files
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
    )
    changed_files = result.stdout.strip().split("\n")
    skill_files = [f for f in changed_files if f.endswith("SKILL.md")]
    
    if not skill_files:
        print("No SKILL.md files to check")
        return True
    
    print(f"\nChecking {len(skill_files)} changed SKILL.md files...")
    all_passed = True
    
    for skill_file in skill_files:
        skill_path = repo_root / skill_file
        if not skill_path.exists():
            continue
            
        print(f"\n  Auditing: {skill_file}")
        result = standardizer.audit_skill(skill_path)
        
        # Check compliance level
        if result.compliance_level != ComplianceLevel.COMPLIANT:
            print(f"    ❌ NOT COMPLIANT (Score: {result.score:.1f}/100)")
            for issue in result.issues:
                print(f"      [{issue.severity.upper()}] {issue.message}")
            all_passed = False
        else:
            print(f"    ✓ COMPLIANT (Score: {result.score:.1f}/100)")
    
    return all_passed

if __name__ == "__main__":
    success = check_skills()
    sys.exit(0 if success else 1)
EOF

SKILL_CHECK_EXIT=$?

if [ $SKILL_CHECK_EXIT -ne 0 ]; then
    echo -e "${RED}✗ Skill standardization checks FAILED${NC}"
    echo "Fix the issues above and try again"
    exit 1
fi

echo -e "${GREEN}✓ All skill standardization checks passed${NC}"
exit 0
