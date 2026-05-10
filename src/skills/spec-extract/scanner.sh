#!/bin/bash
#
# spec-extract scanner.sh
# Hybrid pattern detection engine with regex phase + template validation
# Detects all 8 ERS architectural patterns and generates confidence scores
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_PATH=""
OUTPUT_DIR="./specs"
PATTERNS_FILTER=""
CONFIDENCE_THRESHOLD=""
OUTPUT_FORMAT="markdown"
DRY_RUN=0

# Pattern definitions
PATTERNS=("P-001" "P-002" "P-003" "P-004" "P-005" "P-006" "P-007" "P-008")
PATTERN_NAMES=(
  "Makefile 3-Phase"
  "Environment Sourcing"
  "GitHub Actions"
  "CDK Stack"
  "Go Modules"
  "Lambda Handler"
  "Table-Driven Testing"
  "Security Patterns"
)

# Temporary file for results (use a named temp file that persists during the run)
RESULTS_FILE="/tmp/spec-extract-results.$$"
trap "rm -f $RESULTS_FILE" EXIT

# ==============================================================================
# Utility Functions
# ==============================================================================

log_info() {
  echo -e "${BLUE}[INFO]${NC} $*" >&2
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_success() {
  echo -e "${GREEN}[OK]${NC} $*" >&2
}

# Extract service name from path
get_service_name() {
  basename "$1" | sed 's/^ers-//' | sed 's/-app$/app/'
}

# Save pattern result to temp file (use ~~ as delimiter to avoid conflicts with | in evidence)
save_result() {
  local pattern=$1
  local present=$2
  local confidence=$3
  local evidence=$4
  local variations=$5
  local files=$6

  # Replace | with | to preserve structure, but use ~~ between fields
  printf '%s~~%s~~%s~~%s~~%s~~%s\n' "$pattern" "$present" "$confidence" "$evidence" "$variations" "$files" >> "$RESULTS_FILE"
}

# Read all results
read_results() {
  if [[ -f "$RESULTS_FILE" ]]; then
    cat "$RESULTS_FILE"
  fi
}

# ==============================================================================
# Pattern Detectors (P-001 through P-008)
# ==============================================================================

detect_p001_makefile() {
  local pattern="P-001"
  log_info "Scanning P-001 (Makefile 3-Phase)..."

  local makefile="$SERVICE_PATH/Makefile"

  if [[ ! -f "$makefile" ]]; then
    log_warn "P-001: Makefile not found"
    save_result "$pattern" "0" "0%" "" "" ""
    return
  fi

  local evidence="File exists at service root"
  local files="$makefile"

  # Check for required targets
  local targets=("lint" "test" "build" "deploy")
  local found_targets=0
  for target in "${targets[@]}"; do
    if grep -q "^$target:" "$makefile"; then
      ((found_targets++))
      evidence="$evidence|Target '$target' present"
    fi
  done

  # Check .PHONY declaration
  if grep -q "^\.PHONY:" "$makefile"; then
    evidence="$evidence|.PHONY declaration present"
  fi

  # Check error propagation
  if grep -q "&&" "$makefile"; then
    evidence="$evidence|Error propagation with && chains"
  fi

  # Check for composite targets (variation)
  local variations=""
  if grep -qE "^[a-z]+: " "$makefile"; then
    local composite_count=$(grep -cE "^[a-z]+: [a-z\.]+" "$makefile" || true)
    if [[ $composite_count -gt 3 ]]; then
      variations="Composite targets found (targets delegate to sub-targets)"
    fi
  fi

  # Confidence scoring
  local confidence="100%"
  if [[ $found_targets -ge 4 ]]; then
    confidence="100%"
  elif [[ $found_targets -ge 3 ]]; then
    confidence="88%"
  elif [[ $found_targets -ge 2 ]]; then
    confidence="75%"
  else
    confidence="50%"
  fi

  save_result "$pattern" "1" "$confidence" "$evidence" "$variations" "$files"
  log_success "P-001: Found with $confidence confidence"
}

detect_p002_env_sourcing() {
  local pattern="P-002"
  log_info "Scanning P-002 (Environment Sourcing)..."

  local env_dir="$SERVICE_PATH/env"
  local makefile="$SERVICE_PATH/Makefile"

  if [[ ! -d "$env_dir" ]]; then
    log_warn "P-002: env/ directory not found"
    save_result "$pattern" "0" "0%" "" "" ""
    return
  fi

  local evidence="env/ directory exists"
  local files="$env_dir"

  # Check for env files
  local env_files=0
  if [[ -f "$env_dir/.env.dev" ]]; then
    evidence="$evidence|env/.env.dev present"
    ((env_files++))
  fi
  if [[ -f "$env_dir/.env.prod" ]]; then
    evidence="$evidence|env/.env.prod present"
    ((env_files++))
  fi

  # Check Makefile sourcing pattern
  if [[ -f "$makefile" ]]; then
    if grep -qE "^\-?include.*env/" "$makefile"; then
      evidence="$evidence|Makefile contains -include env/ pattern"
    fi
  fi

  # Check for quotes in env files (anti-pattern)
  local has_quotes=0
  for f in "$env_dir"/.env*; do
    if [[ -f "$f" ]] && grep -q '="' "$f"; then
      ((has_quotes++))
    fi
  done

  if [[ $has_quotes -eq 0 ]]; then
    evidence="$evidence|No shell quotes in env files (correct pattern)"
  fi

  # Confidence scoring
  local confidence="50%"
  if [[ $env_files -ge 2 ]] && [[ -f "$makefile" ]] && grep -qE "^\-?include.*env/" "$makefile"; then
    confidence="100%"
  elif [[ $env_files -ge 1 ]]; then
    confidence="88%"
  fi

  save_result "$pattern" "1" "$confidence" "$evidence" "" "$files"
  log_success "P-002: Found with $confidence confidence"
}

detect_p003_github_actions() {
  local pattern="P-003"
  log_info "Scanning P-003 (GitHub Actions)..."

  local workflows_dir="$SERVICE_PATH/.github/workflows"

  if [[ ! -d "$workflows_dir" ]]; then
    log_warn "P-003: .github/workflows/ directory not found"
    save_result "$pattern" "0" "0%" "" "" ""
    return
  fi

  local evidence=".github/workflows/ directory exists"
  local files="$workflows_dir"

  # Check for branch workflow
  local branch_workflow=""
  if [[ -f "$workflows_dir/branch.yaml" ]]; then
    branch_workflow="$workflows_dir/branch.yaml"
    evidence="$evidence|branch.yaml workflow found"
  fi

  # Check for main workflow
  local main_workflow=""
  if [[ -f "$workflows_dir/main.yaml" ]]; then
    main_workflow="$workflows_dir/main.yaml"
    evidence="$evidence|main.yaml workflow found"
  fi

  # Validate triggers
  if [[ -f "$branch_workflow" ]]; then
    if grep -q "branches-ignore:\|pull_request" "$branch_workflow"; then
      evidence="$evidence|branch.yaml has correct triggers (non-main)"
    fi
  fi

  if [[ -f "$main_workflow" ]]; then
    if grep -q "branches.*main" "$main_workflow"; then
      evidence="$evidence|main.yaml triggers on main branch"
    fi
  fi

  # Check for make invocation
  local make_count=$(grep -rc "make " "$workflows_dir" 2>/dev/null || echo "0")
  if [[ $make_count -gt 0 ]]; then
    evidence="$evidence|Workflows invoke make targets"
  fi

  # Confidence scoring
  local confidence="50%"
  if [[ -n "$branch_workflow" ]] && [[ -n "$main_workflow" ]] && [[ $make_count -gt 0 ]]; then
    confidence="100%"
  elif [[ -n "$branch_workflow" ]] || [[ -n "$main_workflow" ]]; then
    confidence="88%"
  fi

  save_result "$pattern" "1" "$confidence" "$evidence" "" "$files"
  log_success "P-003: Found with $confidence confidence"
}

detect_p004_cdk_stack() {
  local pattern="P-004"
  log_info "Scanning P-004 (CDK Stack)..."

  local cdk_dir="$SERVICE_PATH/cdk"

  if [[ ! -d "$cdk_dir" ]]; then
    log_warn "P-004: cdk/ directory not found"
    save_result "$pattern" "0" "0%" "" "" ""
    return
  fi

  local evidence="cdk/ directory exists"
  local files="$cdk_dir"

  # Check for main CDK file
  local cdk_main=""
  if [[ -f "$cdk_dir/main.go" ]]; then
    cdk_main="$cdk_dir/main.go"
    evidence="$evidence|cdk/main.go found"
  elif [[ -f "$cdk_dir/cdk.go" ]]; then
    cdk_main="$cdk_dir/cdk.go"
    evidence="$evidence|cdk/cdk.go found"
  fi

  if [[ -z "$cdk_main" ]]; then
    log_warn "P-004: No main CDK file found"
    save_result "$pattern" "1" "50%" "$evidence" "" "$files"
    return
  fi

  # Check for aws-cdk-go import
  if grep -q "aws-cdk-go\|awscdk" "$cdk_main"; then
    evidence="$evidence|aws-cdk-go import present"
  fi

  # Check for ENV_NAME and DNS_ROOT_DOMAIN usage
  local env_usage=0
  if grep -q "ENV_NAME" "$cdk_main"; then
    evidence="$evidence|Reads ENV_NAME from environment"
    ((env_usage++))
  fi
  if grep -q "DNS_ROOT_DOMAIN" "$cdk_main"; then
    evidence="$evidence|Reads DNS_ROOT_DOMAIN from environment"
    ((env_usage++))
  fi

  # Check for stack construction
  if grep -qE "New.*Stack|awscdk.NewStack" "$cdk_main"; then
    evidence="$evidence|Stack construction pattern present"
  fi

  # Confidence scoring
  local confidence="75%"
  if [[ $env_usage -ge 2 ]]; then
    confidence="100%"
  elif [[ $env_usage -ge 1 ]]; then
    confidence="88%"
  fi

  save_result "$pattern" "1" "$confidence" "$evidence" "" "$files"
  log_success "P-004: Found with $confidence confidence"
}

detect_p005_go_modules() {
  local pattern="P-005"
  log_info "Scanning P-005 (Go Modules)..."

  local go_mod=""
  if [[ -f "$SERVICE_PATH/go.mod" ]]; then
    go_mod="$SERVICE_PATH/go.mod"
  elif [[ -f "$SERVICE_PATH/cdk/go.mod" ]]; then
    go_mod="$SERVICE_PATH/cdk/go.mod"
  elif [[ -d "$SERVICE_PATH/lambda" ]]; then
    go_mod=$(find "$SERVICE_PATH/lambda" -name "go.mod" -print -quit 2>/dev/null || echo "")
  fi

  if [[ -z "$go_mod" ]]; then
    log_warn "P-005: No go.mod found"
    save_result "$pattern" "0" "0%" "" "" ""
    return
  fi

  local evidence="go.mod file found"
  local files="$go_mod"

  # Extract module path
  local module_path=$(grep "^module" "$go_mod" | awk '{print $2}' || echo "")
  if [[ $module_path == "github.com/{your-org}"* ]]; then
    evidence="$evidence|Module path follows organization naming convention"
  fi

  # Check Go version
  local go_version=$(grep "^go" "$go_mod" | awk '{print $2}' || echo "")
  if [[ -n "$go_version" ]]; then
    evidence="$evidence|Go version $go_version specified"
  fi

  # Check for AWS SDK
  local aws_deps=0
  if grep -q "aws-lambda-go" "$go_mod"; then
    ((aws_deps++))
    evidence="$evidence|aws-lambda-go dependency"
  fi
  if grep -q "aws-sdk-go-v2" "$go_mod"; then
    ((aws_deps++))
    evidence="$evidence|aws-sdk-go-v2 dependency"
  fi

  # Check for GOPRIVATE in Makefile
  local makefile="$SERVICE_PATH/Makefile"
  if [[ -f "$makefile" ]] && grep -q "GOPRIVATE" "$makefile"; then
    evidence="$evidence|GOPRIVATE set for shared libraries"
  fi

  # Confidence scoring
  local confidence="75%"
  if [[ $aws_deps -ge 2 ]]; then
    confidence="100%"
  elif [[ $aws_deps -ge 1 ]]; then
    confidence="88%"
  fi

  save_result "$pattern" "1" "$confidence" "$evidence" "" "$files"
  log_success "P-005: Found with $confidence confidence"
}

detect_p006_lambda_handler() {
  local pattern="P-006"
  log_info "Scanning P-006 (Lambda Handler)..."

  local handler_file=""

  # Check for lambda/*/main.go
  if [[ -d "$SERVICE_PATH/lambda" ]]; then
    handler_file=$(find "$SERVICE_PATH/lambda" -name "main.go" -print -quit 2>/dev/null || echo "")
  fi

  # Fall back to root main.go if no lambda subdirectory
  if [[ -z "$handler_file" ]] && [[ -f "$SERVICE_PATH/main.go" ]]; then
    handler_file="$SERVICE_PATH/main.go"
  fi

  if [[ -z "$handler_file" ]]; then
    log_warn "P-006: No Lambda handler found"
    save_result "$pattern" "0" "0%" "" "" ""
    return
  fi

  local evidence="Lambda main.go file found"
  local files="$handler_file"

  # Check for aws-lambda-go imports
  if grep -q "aws-lambda-go" "$handler_file"; then
    evidence="$evidence|aws-lambda-go import present"
  fi

  # Check for lambda.Start()
  if grep -q "lambda\.Start" "$handler_file"; then
    evidence="$evidence|lambda.Start() invocation present"
  fi

  # Check for event types
  if grep -q "APIGatewayProxyRequest\|SNSEvent\|SQSEvent" "$handler_file"; then
    evidence="$evidence|Event type imports present"
  fi

  # Count Lambda handler files
  local handler_count=$(find "$SERVICE_PATH/lambda" -name "main.go" 2>/dev/null | wc -l || echo "1")
  local variations=""
  if [[ $handler_count -gt 1 ]]; then
    variations="Multiple Lambda handlers ($handler_count total)"
  fi

  # Confidence scoring
  local confidence="75%"
  if grep -q "lambda\.Start" "$handler_file"; then
    confidence="100%"
  fi

  save_result "$pattern" "1" "$confidence" "$evidence" "$variations" "$files"
  log_success "P-006: Found with $confidence confidence"
}

detect_p007_testing() {
  local pattern="P-007"
  log_info "Scanning P-007 (Table-Driven Testing)..."

  # Check for test files
  local test_files=0
  local table_driven_tests=0

  # Count Go test files
  test_files=$(find "$SERVICE_PATH" -name "*_test.go" -type f 2>/dev/null | wc -l || echo "0")

  # Count files with table-driven pattern
  table_driven_tests=$(grep -r "tests := \[\]struct" "$SERVICE_PATH" 2>/dev/null | wc -l || echo "0")

  # Check for TypeScript/Playwright tests
  local playwright_tests=$(find "$SERVICE_PATH" -name "*.spec.ts" 2>/dev/null | wc -l || echo "0")

  if [[ $test_files -eq 0 ]] && [[ $playwright_tests -eq 0 ]]; then
    log_warn "P-007: No test files found"
    save_result "$pattern" "0" "0%" "" "" ""
    return
  fi

  local evidence="Found $test_files Go test files"
  local files=""

  if [[ $table_driven_tests -gt 0 ]]; then
    evidence="$evidence|Table-driven test pattern found in $table_driven_tests files"
  fi

  if [[ $playwright_tests -gt 0 ]]; then
    evidence="$evidence|Playwright E2E tests ($playwright_tests specs)"
  fi

  # Check for coverage target in Makefile
  local makefile="$SERVICE_PATH/Makefile"
  if [[ -f "$makefile" ]] && grep -q "coverage\|cover" "$makefile"; then
    evidence="$evidence|Coverage target in Makefile"
  fi

  # Confidence scoring based on test count
  local confidence="50%"
  if [[ $test_files -gt 10 ]]; then
    confidence="100%"
  elif [[ $test_files -gt 5 ]]; then
    confidence="88%"
  elif [[ $test_files -gt 2 ]]; then
    confidence="75%"
  fi

  # Adjust for Playwright
  if [[ $playwright_tests -gt 10 ]]; then
    confidence="100%"
  fi

  save_result "$pattern" "1" "$confidence" "$evidence" "" "$files"
  log_success "P-007: Found with $confidence confidence"
}

detect_p008_security_patterns() {
  local pattern="P-008"
  log_info "Scanning P-008 (Security Patterns)..."

  local security_evidence=0
  local evidence=""

  # Check for JWT-related patterns (exclude .git directory)
  if grep -r "JWT\|JWKS\|jwt\|jwks" "$SERVICE_PATH" --include="*.go" --include="*.ts" --include="*.tsx" --exclude-dir=".git" 2>/dev/null | grep -q .; then
    security_evidence=$((security_evidence + 1))
    evidence="$evidence|JWT validation patterns detected"
  fi

  # Check for OAuth2 patterns
  if grep -r "oauth\|OAuth\|Cognito" "$SERVICE_PATH" --include="*.go" --include="*.ts" --include="*.tsx" --exclude-dir=".git" 2>/dev/null | grep -q .; then
    security_evidence=$((security_evidence + 1))
    evidence="$evidence|OAuth2/Cognito integration detected"
  fi

  # Check for SigV4 signing
  if grep -r "SigV4\|Signer\|aws.*sign" "$SERVICE_PATH" --include="*.go" --include="*.ts" --include="*.tsx" --exclude-dir=".git" 2>/dev/null | grep -q .; then
    security_evidence=$((security_evidence + 1))
    evidence="$evidence|SigV4 signing detected"
  fi

  # Check for CORS headers
  if grep -r "Access-Control\|CORS" "$SERVICE_PATH" --include="*.go" --include="*.ts" --include="*.tsx" --exclude-dir=".git" 2>/dev/null | grep -q .; then
    security_evidence=$((security_evidence + 1))
    evidence="$evidence|CORS headers detected"
  fi

  if [[ $security_evidence -eq 0 ]]; then
    log_warn "P-008: No security patterns detected"
    save_result "$pattern" "0" "0%" "" "" ""
    return
  fi

  # Confidence based on evidence count
  local confidence="75%"
  if [[ $security_evidence -ge 3 ]]; then
    confidence="100%"
  elif [[ $security_evidence -ge 2 ]]; then
    confidence="88%"
  fi

  save_result "$pattern" "1" "$confidence" "$evidence" "" ""
  log_success "P-008: Found with $confidence confidence"
}

# ==============================================================================
# Main Scanning Logic
# ==============================================================================

scan_service() {
  log_info "Starting service scan: $SERVICE_PATH"

  if [[ ! -d "$SERVICE_PATH" ]]; then
    log_error "Service path does not exist: $SERVICE_PATH"
    exit 1
  fi

  # Run pattern detectors
  detect_p001_makefile
  detect_p002_env_sourcing
  detect_p003_github_actions
  detect_p004_cdk_stack
  detect_p005_go_modules
  detect_p006_lambda_handler
  detect_p007_testing
  detect_p008_security_patterns

  log_success "Scan complete"
}

# ==============================================================================
# Output Formatting
# ==============================================================================

print_console_summary() {
  local service_name=$(get_service_name "$SERVICE_PATH")

  echo ""
  echo "Scanning: $service_name"

  local pattern_count=0
  local found_count=0
  local total_confidence=0

  while IFS='~~' read -r pattern present confidence evidence variations files; do
    # Trim whitespace
    pattern=$(echo "$pattern" | xargs)

    if [[ -z "$pattern" ]]; then
      continue
    fi

    local idx=-1
    for i in "${!PATTERNS[@]}"; do
      if [[ "${PATTERNS[$i]}" == "$pattern" ]]; then
        idx=$i
        break
      fi
    done

    if [[ $idx -ge 0 ]]; then
      local name="${PATTERN_NAMES[$idx]}"
      ((pattern_count++))

      if [[ "$present" == "1" ]]; then
        ((found_count++))
        printf "  %-40s ✓ %s\n" "$pattern $name" "$confidence"
      else
        printf "  %-40s ✗ Not found\n" "$pattern $name"
      fi
    fi
  done < <(read_results)

  local percentage=$((found_count * 100 / pattern_count))
  echo ""
  echo "Overall Compliance: $found_count/$pattern_count patterns ($percentage%)"

  if [[ $DRY_RUN -eq 0 ]]; then
    echo "Spec files written to: $OUTPUT_DIR"
  else
    echo "Dry-run mode (no files written)"
  fi
  echo ""
}

# ==============================================================================
# File Output
# ==============================================================================

write_spec_files() {
  local service_name=$(get_service_name "$SERVICE_PATH")

  mkdir -p "$OUTPUT_DIR"

  while IFS='~~' read -r pattern present confidence evidence variations files; do
    # Trim whitespace
    pattern=$(echo "$pattern" | xargs)
    present=$(echo "$present" | xargs)

    if [[ -z "$pattern" ]] || [[ "$present" != "1" ]]; then
      continue
    fi

    local idx=-1
    for i in "${!PATTERNS[@]}"; do
      if [[ "${PATTERNS[$i]}" == "$pattern" ]]; then
        idx=$i
        break
      fi
    done

    if [[ $idx -ge 0 ]]; then
      local name="${PATTERN_NAMES[$idx]}"
      local output_file="$OUTPUT_DIR/${service_name}-${pattern}.md"

      # Start with YAML frontmatter
      cat > "$output_file" << EOF
---
pattern_id: $pattern
pattern_name: $name
service: $service_name
confidence: "$confidence"
last_verified: "$(date +%Y-%m-%d)"
compliance: "✓ Full"
files:
EOF

      # Add files to YAML
      if [[ -n "$files" ]]; then
        echo "$files" | tr '|' '\n' | while read -r item; do
          if [[ -n "$item" ]]; then
            echo "  - \"$item\"" >> "$output_file"
          fi
        done
      else
        echo "  []" >> "$output_file"
      fi

      # Add evidence to YAML
      echo "evidence:" >> "$output_file"
      if [[ -n "$evidence" ]]; then
        echo "$evidence" | tr '|' '\n' | while read -r item; do
          if [[ -n "$item" ]]; then
            echo "  - \"$item\"" >> "$output_file"
          fi
        done
      else
        echo "  []" >> "$output_file"
      fi

      # Add variations to YAML
      echo "variations:" >> "$output_file"
      if [[ -n "$variations" ]]; then
        echo "$variations" | tr '|' '\n' | while read -r item; do
          if [[ -n "$item" ]]; then
            echo "  - \"$item\"" >> "$output_file"
          fi
        done
      else
        echo "  []" >> "$output_file"
      fi

      cat >> "$output_file" << EOF
false_positives: []
---

## Pattern: $name

Service: **$service_name**
Confidence: **$confidence**

### Evidence Found

EOF

      # Add evidence items to markdown
      if [[ -n "$evidence" ]]; then
        echo "$evidence" | tr '|' '\n' | while read -r item; do
          if [[ -n "$item" ]]; then
            echo "- $item" >> "$output_file"
          fi
        done
      fi

      cat >> "$output_file" << EOF

### Files Analyzed

EOF

      # Add files to markdown
      if [[ -n "$files" ]]; then
        echo "$files" | tr '|' '\n' | while read -r item; do
          if [[ -n "$item" ]]; then
            echo "- \`$item\`" >> "$output_file"
          fi
        done
      fi

      if [[ -n "$variations" ]]; then
        cat >> "$output_file" << EOF

### Variations

EOF
        echo "$variations" | tr '|' '\n' | while read -r item; do
          if [[ -n "$item" ]]; then
            echo "- $item" >> "$output_file"
          fi
        done
      fi

      cat >> "$output_file" << EOF

---

Generated: $(date)
EOF

      log_success "Wrote: $output_file"
    fi
  done < <(read_results)
}

# ==============================================================================
# Main Entry Point
# ==============================================================================

main() {
  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --output-dir)
        OUTPUT_DIR="$2"
        shift 2
        ;;
      --patterns)
        PATTERNS_FILTER="$2"
        shift 2
        ;;
      --confidence-threshold)
        CONFIDENCE_THRESHOLD="$2"
        shift 2
        ;;
      --json)
        OUTPUT_FORMAT="json"
        shift
        ;;
      --no-write)
        DRY_RUN=1
        shift
        ;;
      *)
        if [[ -z "$SERVICE_PATH" ]]; then
          SERVICE_PATH="$1"
        else
          log_error "Unknown argument: $1"
          exit 1
        fi
        shift
        ;;
    esac
  done

  # Resolve service path
  if [[ -z "$SERVICE_PATH" ]]; then
    SERVICE_PATH=$(pwd)
  fi

  SERVICE_PATH=$(cd "$SERVICE_PATH" && pwd)

  # Resolve output directory to absolute path
  if [[ ! "$OUTPUT_DIR" = /* ]]; then
    OUTPUT_DIR="$SERVICE_PATH/$OUTPUT_DIR"
  fi

  # Run scan
  scan_service

  # Print results
  print_console_summary

  # Write files
  if [[ $DRY_RUN -eq 0 ]]; then
    write_spec_files
  fi

  # Clean up results file
  rm -f "$RESULTS_FILE"
}

main "$@"
