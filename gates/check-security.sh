#!/usr/bin/env bash
# Static Application Security Testing (SAST) gate.
# Delegates to Semgrep (multi-lang) or Bandit (Python) for vulnerability scanning.
# Usage: ./check-security.sh [project-root] [--severity=high]
#
# AI-generated code has 2.74x higher vulnerability rates.
# Focus: injection, broken auth, insecure dependencies, XSS.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(pwd)}"

if [ -f "$SCRIPT_DIR/../lib/colors.sh" ]; then
  source "$SCRIPT_DIR/../lib/colors.sh"
elif [ -f "$PROJECT_ROOT/.harness/lib/colors.sh" ]; then
  source "$PROJECT_ROOT/.harness/lib/colors.sh"
else
  info() { echo "[INFO] $*"; }
  success() { echo "[OK] $*"; }
  warn() { echo "[WARN] $*"; }
  error() { echo "[ERROR] $*"; }
  header() { echo "=== $* ==="; }
fi

SEVERITY="warning"  # error, warning, info
for arg in "$@"; do
  case "$arg" in
    --severity=*) SEVERITY="${arg#*=}" ;;
  esac
done

header "Static Application Security Testing (SAST)"
info "Min severity: $SEVERITY"
echo ""

VIOLATIONS=0
SCANNED=false

# ─── Semgrep (multi-language) ──────────────────────────────────────
run_semgrep() {
  if ! command -v semgrep &>/dev/null; then
    return 1
  fi
  SCANNED=true
  info "Running: semgrep (multi-language SAST)"

  local rules="auto"
  # Use project-specific rules if they exist
  if [ -f "$PROJECT_ROOT/.semgrep.yml" ] || [ -d "$PROJECT_ROOT/.semgrep" ]; then
    rules="$PROJECT_ROOT/.semgrep.yml"
  fi

  local output exit_code
  output=$(cd "$PROJECT_ROOT" && semgrep scan --config "$rules" \
    --severity "$SEVERITY" \
    --exclude="node_modules" --exclude="dist" --exclude="build" \
    --exclude="__pycache__" --exclude=".next" --exclude=".harness" \
    --json 2>/dev/null) && exit_code=0 || exit_code=$?

  local finding_count
  finding_count=$(echo "$output" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data.get('results', [])))
except:
    print(0)
" 2>/dev/null || echo "0")

  if [ "$finding_count" -eq 0 ]; then
    success "Semgrep: No security issues found"
  else
    error "Semgrep: $finding_count security issue(s) found"
    # Show top findings
    echo "$output" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for r in data.get('results', [])[:10]:
        path = r.get('path', '?')
        line = r.get('start', {}).get('line', '?')
        msg = r.get('extra', {}).get('message', r.get('check_id', '?'))
        sev = r.get('extra', {}).get('severity', '?')
        print(f'  [{sev}] {path}:{line}')
        print(f'    {msg[:120]}')
        print()
except:
    pass
" 2>/dev/null
    VIOLATIONS=$((VIOLATIONS + finding_count))
  fi
  return 0
}

# ─── Bandit (Python) ───────────────────────────────────────────────
run_bandit() {
  if ! command -v bandit &>/dev/null; then
    return 1
  fi

  # Only run if Python files exist
  local py_count
  py_count=$(find "$PROJECT_ROOT" -name "*.py" -not -path "*/node_modules/*" \
    -not -path "*/__pycache__/*" -not -path "*/.harness/*" 2>/dev/null | grep -c . || true)
  [ "$py_count" -eq 0 ] && return 1

  SCANNED=true
  info "Running: bandit (Python SAST)"

  local sev_flag=""
  case "$SEVERITY" in
    error|high) sev_flag="-ll" ;;  # high + critical only
    warning|medium) sev_flag="-l" ;;  # medium and above
    *) sev_flag="" ;;  # all
  esac

  local output exit_code
  output=$(cd "$PROJECT_ROOT" && bandit -r . $sev_flag \
    --exclude="./.harness,./node_modules,./__pycache__,./dist,./.next" \
    -f json 2>/dev/null) && exit_code=0 || exit_code=$?

  local finding_count
  finding_count=$(echo "$output" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data.get('results', [])))
except:
    print(0)
" 2>/dev/null || echo "0")

  if [ "$finding_count" -eq 0 ]; then
    success "Bandit: No security issues found"
  else
    error "Bandit: $finding_count security issue(s) found"
    echo "$output" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for r in data.get('results', [])[:10]:
        fname = r.get('filename', '?')
        line = r.get('line_number', '?')
        issue = r.get('issue_text', '?')
        sev = r.get('issue_severity', '?')
        print(f'  [{sev}] {fname}:{line}')
        print(f'    {issue[:120]}')
        print()
except:
    pass
" 2>/dev/null
    VIOLATIONS=$((VIOLATIONS + finding_count))
  fi
  return 0
}

# ─── Built-in pattern checks (no external tools needed) ────────────
run_builtin_checks() {
  info "Running: built-in security pattern checks"
  SCANNED=true

  # Common AI-generated security mistakes
  local patterns=(
    'eval('
    'exec('
    'innerHTML\s*='
    'dangerouslySetInnerHTML'
    '__proto__'
    'document\.write'
    'child_process\.exec\('
    'shell=True'
    'verify=False'
    'CSRF.*disable'
    'allowAll\|permit_all\|@PermitAll'
  )

  local descriptions=(
    "eval() — code injection risk"
    "exec() — code injection risk"
    "innerHTML — XSS risk"
    "dangerouslySetInnerHTML — XSS risk"
    "__proto__ — prototype pollution risk"
    "document.write — XSS risk"
    "child_process.exec — command injection risk"
    "shell=True — command injection risk"
    "verify=False — SSL verification disabled"
    "CSRF disabled — CSRF protection disabled"
    "permit all — overly permissive authorization"
  )

  local builtin_violations=0

  for i in "${!patterns[@]}"; do
    local pattern="${patterns[$i]}"
    local desc="${descriptions[$i]}"

    local matches
    matches=$(grep -rn "$pattern" "$PROJECT_ROOT" \
      --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" \
      --include="*.py" --include="*.java" --include="*.go" \
      2>/dev/null | \
      grep -v "node_modules" | grep -v "__pycache__" | grep -v ".harness" | \
      grep -v "\.test\." | grep -v "\.spec\." | grep -v "check-security" | \
      head -5 || true)

    [ -z "$matches" ] && continue

    while IFS= read -r match; do
      local file_line=$(echo "$match" | cut -d: -f1-2)
      local rel_path="${file_line#$PROJECT_ROOT/}"
      warn "SECURITY: $rel_path — $desc"
      builtin_violations=$((builtin_violations + 1))
    done <<< "$matches"
  done

  if [ "$builtin_violations" -eq 0 ]; then
    success "Built-in checks: No common security anti-patterns found"
  else
    echo ""
    VIOLATIONS=$((VIOLATIONS + builtin_violations))
  fi
}

# ─── Run checks ────────────────────────────────────────────────────
run_semgrep || run_bandit || true
run_builtin_checks

# ─── Report ────────────────────────────────────────────────────────
echo ""
if ! $SCANNED; then
  info "No scannable code found."
  exit 0
fi

if [ $VIOLATIONS -eq 0 ]; then
  success "No security issues detected."
  exit 0
else
  error "$VIOLATIONS security issue(s) found."
  info "Fix issues before committing. See OWASP Top 10 for guidance."
  exit 1
fi
