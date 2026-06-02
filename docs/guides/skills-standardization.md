# Skills Standardization Framework

## Overview

The Skills Standardization Framework provides comprehensive standardization, quality enforcement, and automated updates for all SKILL.md files in the agentic-engineers framework.

**Key Components:**
- **Standardization Engine**: Audits all skills against a unified template
- **Quality Enforcer**: Validates type hints, docstrings, linting, coverage, and detects dead code
- **Auto-Updater**: Automatically standardizes skills while preserving existing content
- **Pre-commit Hook**: Enforces standards on commit
- **Comprehensive Tests**: 52 unit tests with full coverage

## Standardization Requirements

### SKILL.md Template

Every skill must follow this standard structure:

```yaml
---
name: skill-name
description: Brief description of what this skill does and when to use it.
license: Proprietary
compatibility: agentic-engineers framework
metadata:
  author: agentic-engineers
  version: "1.0"
  category: orchestration  # Choose: orchestration, monitoring, optimization, etc.
  role: engineer            # Choose: engineer, senior-engineer, lead-engineer, etc.
---

## Overview

{Detailed explanation of what the skill does, including:
- Key features
- When to use it
- Expected use cases}

## Invocation

{Instructions for how to invoke this skill:
- Manual invocation steps
- Automated/cron invocation
- Code examples
- Environment variables}

## Integration

{How this skill integrates with other components:
- Input sources
- Output destinations
- Dependencies}

## Configuration

{Configuration options:
- Environment variables
- Configuration files
- Customization points}

## Examples

{Practical examples:
- Common use cases
- Code snippets
- Expected output}
```

### Required Sections

Every SKILL.md must include:

| Section | Min Content | Purpose |
|---------|-------------|---------|
| **Overview** | 50+ chars | Explain what the skill does and when to use it |
| **Invocation** | 30+ chars | Show how to run/invoke the skill |

### Optional but Recommended Sections

| Section | Purpose |
|---------|---------|
| **Integration** | Document ecosystem integration points |
| **Configuration** | List all customization options |
| **Examples** | Show real-world usage scenarios |
| **Voice Notifications** | Document voice alert messages |
| **Advanced Configuration** | Document expert-level settings |
| **Troubleshooting** | Document common issues and fixes |

### Metadata Requirements

The `metadata` section must include:

```yaml
metadata:
  author: agentic-engineers
  version: "1.0"
  category: orchestration
  role: engineer
```

**Valid categories:**
- orchestration
- monitoring
- optimization
- patterns
- security
- testing
- shared
- architecture
- review
- roles

**Valid roles:**
- engineer
- senior-engineer
- lead-engineer
- orchestrator
- principal-engineer

## Quality Gates

### Type Hints

All public functions must have type hints:

```python
def process_data(input_data: Dict[str, Any], timeout: int) -> str:
    """Process data with timeout."""
    return result
```

**Coverage target:** 100% of public functions

### Docstrings

All public functions and classes must have docstrings:

```python
def calculate_score(x: float, y: float) -> float:
    """Calculate quality score from metrics.
    
    Args:
        x: First metric value
        y: Second metric value
        
    Returns:
        Combined quality score (0-100)
    """
    return (x + y) / 2
```

**Coverage target:** 100% of public functions and classes

### Linting Standards

All code must pass linting checks:

- **black**: Code formatting (line length: 100)
- **flake8**: Style compliance (E501 disabled)
- **mypy**: Type checking

```bash
# Run linting
black src/skills/skill-name/
flake8 src/skills/skill-name/ --max-line-length=100
mypy src/skills/skill-name/
```

### Test Coverage

All skills must have ≥85% test coverage:

```bash
# Check coverage
pytest tests/standardization/ --cov=src/standardization/ --cov-report=term
```

**Requirements:**
- ≥85% line coverage
- ≥85% branch coverage
- All critical paths tested

### Overall Quality Score

**Target: ≥92/100 with ≥95% confidence**

Score calculation:
- Type hints: +25 points
- Docstrings: +25 points
- Linting: +20 points
- Test coverage: +20 points
- Dead code: +10 points
- Optional sections: +5 points

## Using the Standardization Framework

### 1. Run Compliance Audit

```python
from src.standardization import SkillStandardizer

# Initialize standardizer
standardizer = SkillStandardizer(repository_root=Path("/repo"))

# Audit all skills
results = standardizer.audit_all_skills()

# Generate compliance report
report = standardizer.generate_compliance_report()
print(f"Compliant skills: {report['compliant']}/{report['total_skills']}")

# Export report
standardizer.export_report(Path("compliance_report.json"))
```

### 2. Run Quality Enforcement

```python
from src.standardization import QualityEnforcer

# Check quality for a skill
enforcer = QualityEnforcer(Path("src/skills/my-skill"))

# Run all checks
report = enforcer.run_all_checks()

print(f"Quality score: {report.overall_score:.1f}/100")
print(f"Compliant: {report.is_compliant}")

# Export report
enforcer.export_report(Path("quality_report.json"))
```

### 3. Automatically Update Skills

```python
from src.standardization import SkillAutoUpdater

# Initialize updater
updater = SkillAutoUpdater()

# Update all skills
results = updater.update_all_skills(repository_root=Path("/repo"))

# Check what changed
report = updater.generate_update_report()
print(f"Skills updated: {report['total_skills_updated']}")
print(f"Total changes: {report['total_changes_made']}")
```

### 4. Create New Standardized Skill

When creating a new skill:

1. Create skill directory:
   ```bash
   mkdir -p src/skills/my-skill/{scripts,references,assets}
   ```

2. Create SKILL.md with standard template:
   ```bash
   cp templates/SKILL_TEMPLATE.md src/skills/my-skill/SKILL.md
   ```

3. Edit metadata and sections

4. Run audit to verify:
   ```bash
   python3 -c "from src.standardization import SkillStandardizer; \
     s = SkillStandardizer(); \
     r = s.audit_skill(Path('src/skills/my-skill/SKILL.md')); \
     print(f'Compliant: {r.compliance_level}')"
   ```

## Pre-commit Hook

The pre-commit hook automatically validates skills on commit:

```bash
# Install hook
chmod +x setup/pre-commit-skill-check.sh
cp setup/pre-commit-skill-check.sh .git/hooks/pre-commit
```

The hook:
- ✓ Validates SKILL.md structure
- ✓ Enforces required sections
- ✓ Checks type hints presence
- ✓ Verifies docstrings
- ✓ Validates linting compliance
- ✓ Blocks non-compliant commits

## Compliance Levels

### COMPLIANT ✓

- No critical issues
- No warnings
- Score ≥ 92/100
- All required sections present
- Type hints on all functions
- Docstrings on all public items
- Passes linting checks
- ≥85% test coverage

### PARTIAL ⚠️

- No critical issues
- Some warnings present
- Score 75-91/100
- May have optional sections missing
- Some type hints missing
- Some docstrings incomplete
- Minor linting issues

### NON_COMPLIANT ✗

- Critical issues present
- Score < 75/100
- Missing required sections
- No type hints
- No docstrings
- Failing linting checks
- Low test coverage

## Running Tests

```bash
# Run all standardization tests
pytest tests/standardization/ -v

# Run with coverage
pytest tests/standardization/ --cov=src/standardization/ --cov-report=html

# Run specific test class
pytest tests/standardization/test_skill_standardizer.py::TestSkillNameValidation -v

# Run with verbose output
pytest tests/standardization/ -vv
```

**Test Coverage:**
- 52 unit tests total
- ≥85% coverage of src/standardization/
- Tests for all quality checks
- Edge case handling
- Error scenarios

## Test Categories

### 1. Template Validation (14 tests)
- Skill name format validation
- Description length and quality
- Frontmatter structure
- Section extraction
- Compliance scoring

### 2. Quality Enforcement (20 tests)
- Type hints validation
- Docstring presence
- Linting standards
- Dead code detection
- Quality scoring

### 3. Auto-Update (16 tests)
- Frontmatter reconstruction
- Section addition
- Content preservation
- Batch updates
- Update tracking

### 4. Error Handling (2 tests)
- Missing files
- Unreadable files
- Malformed YAML
- Syntax errors

## Compliance Checking

### Check Single Skill

```python
from src.standardization import SkillStandardizer
from pathlib import Path

standardizer = SkillStandardizer()
result = standardizer.audit_skill(Path("src/skills/my-skill/SKILL.md"))

if result.compliance_level.value == "COMPLIANT":
    print(f"✓ Compliant (score: {result.score})")
else:
    print(f"✗ Issues found:")
    for issue in result.issues:
        print(f"  [{issue.severity}] {issue.message}")
```

### Check All Skills

```python
from src.standardization import SkillStandardizer
from pathlib import Path

standardizer = SkillStandardizer(Path("."))
results = standardizer.audit_all_skills()
report = standardizer.generate_compliance_report()

print(f"Total skills: {report['total_skills']}")
print(f"Compliant: {report['compliant']}")
print(f"Compliance: {report['compliance_percentage']:.1f}%")
```

## Integration with CI/CD

The standardization framework can be integrated into CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Check skill compliance
  run: |
    python3 -m pytest tests/standardization/ -v
    python3 scripts/audit-skills.py --report compliance.json
```

## Troubleshooting

### Issue: "Missing module-level docstring"

**Fix:** Add docstring at the top of Python file:

```python
"""Module description and purpose.

This module implements X functionality for Y purpose.
"""
```

### Issue: "Missing type hint"

**Fix:** Add type annotations to function parameters and return:

```python
# Before
def process(data):
    return result

# After
def process(data: Dict[str, Any]) -> str:
    return result
```

### Issue: "Code formatting does not match black style"

**Fix:** Run black formatter:

```bash
black src/skills/skill-name/
```

### Issue: "SKILL.md structure invalid"

**Fix:** Check frontmatter and sections:

1. Ensure frontmatter is between `---` markers
2. Check YAML syntax (no trailing spaces, proper indentation)
3. Ensure required sections exist: `## Overview` and `## Invocation`

## Best Practices

### 1. Structure

- Keep SKILL.md under 500 lines
- Move detailed docs to `references/` subdirectory
- Use relative file references: `[link](references/REFERENCE.md)`
- One responsibility per section

### 2. Documentation

- Write clear, actionable descriptions
- Include real code examples
- Document all configuration options
- List all dependencies

### 3. Quality

- Run audit before pushing
- Fix all critical issues
- Aim for ≥95/100 score
- Keep docstrings concise but complete
- Test all code paths

### 4. Maintenance

- Update SKILL.md when changing functionality
- Run pre-commit hook before committing
- Review compliance reports weekly
- Keep test coverage high

## Reference

### Files Structure

```
src/standardization/
├── __init__.py                  # Package exports
├── skill_standardizer.py        # Core standardization engine
├── quality_enforcer.py          # Quality validation
├── auto_updater.py              # Automated updates

tests/standardization/
├── __init__.py
├── test_skill_standardizer.py   # Standardizer tests (17 tests)
├── test_quality_enforcer.py     # Quality tests (20 tests)
├── test_auto_updater.py         # Updater tests (16 tests)

setup/
└── pre-commit-skill-check.sh    # Pre-commit hook
```

### Key Classes

- **SkillStandardizer**: Main audit engine
- **SkillStandardTemplate**: Template and validation rules
- **SkillAuditResult**: Audit result data structure
- **QualityEnforcer**: Quality validation engine
- **QualityReport**: Quality check results
- **SkillAutoUpdater**: Automated update engine

### Command Line Usage

```bash
# Audit all skills
python3 -c "from src.standardization import SkillStandardizer; \
  from pathlib import Path; \
  s = SkillStandardizer(Path('.')); \
  s.audit_all_skills(); \
  print(s.generate_compliance_report())"

# Update all skills
python3 -c "from src.standardization import SkillAutoUpdater; \
  from pathlib import Path; \
  u = SkillAutoUpdater(); \
  results = u.update_all_skills(Path('.')); \
  print(f'Updated {len(results)} skills')"

# Run quality checks
python3 -c "from src.standardization import QualityEnforcer; \
  from pathlib import Path; \
  e = QualityEnforcer(Path('src/skills/my-skill')); \
  report = e.run_all_checks(); \
  print(f'Score: {report.overall_score}')"
```

## License

Proprietary - agentic-engineers framework

## Support

For issues or questions about the standardization framework:
1. Review this documentation
2. Check the test suite for examples
3. Run individual validators for debugging
4. Report issues with compliance details and suggestions
