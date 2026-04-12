#!/usr/bin/env bash
# Check dependencies for known vulnerabilities.
# Delegates to native audit tools: npm audit, pip-audit, cargo audit, etc.
# Usage: ./check-deps.sh [project-root] [--fail-on=high]
#
# Severity levels: critical, high, moderate, low
# Default: fails on critical and high

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(pwd)}"

# Colors
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

# ─── Configuration ──────────────────────────────────────────────────
FAIL_ON="high"  # critical, high, moderate, low

for arg in "$@"; do
  case "$arg" in
    --fail-on=*) FAIL_ON="${arg#*=}" ;;
  esac
done

header "Dependency Vulnerability Scan"
info "Fail threshold: $FAIL_ON and above"
echo ""

VIOLATIONS=0
SCANNED=false

# ─── npm / pnpm / yarn audit ───────────────────────────────────────
check_npm_deps() {
  if [ ! -f "$PROJECT_ROOT/package.json" ]; then
    return
  fi
  SCANNED=true

  local audit_cmd=""
  local severity_flag=""

  if [ -f "$PROJECT_ROOT/pnpm-lock.yaml" ]; then
    audit_cmd="pnpm audit"
    # pnpm doesn't support --audit-level directly in older versions
    severity_flag="--audit-level=$FAIL_ON"
  elif [ -f "$PROJECT_ROOT/yarn.lock" ]; then
    audit_cmd="yarn audit"
    severity_flag="--level $FAIL_ON"
  elif [ -f "$PROJECT_ROOT/package-lock.json" ]; then
    audit_cmd="npm audit"
    severity_flag="--audit-level=$FAIL_ON"
  else
    info "No lockfile found for npm audit, skipping"
    return
  fi

  info "Running: $audit_cmd"

  # Run audit and capture output
  local output exit_code
  output=$($audit_cmd $severity_flag 2>&1) && exit_code=0 || exit_code=$?

  if [ "$exit_code" -eq 0 ]; then
    success "npm ecosystem: No vulnerabilities at '$FAIL_ON' level or above"
  else
    # npm audit returns non-zero when vulnerabilities found
    local vuln_count
    vuln_count=$(echo "$output" | grep -cE '(critical|high|moderate|low)' || true)
    if [ "$vuln_count" -gt 0 ]; then
      error "npm ecosystem: Vulnerabilities found"
      echo "$output" | grep -E '(critical|high|moderate|low|Severity)' | head -20
      echo ""
      VIOLATIONS=$((VIOLATIONS + 1))
    else
      # Non-zero exit might be due to other errors (network, etc.)
      warn "npm audit returned non-zero but no clear vulnerabilities found"
      echo "$output" | tail -5
    fi
  fi
}

# ─── Python pip-audit / safety ──────────────────────────────────────
check_python_deps() {
  if [ ! -f "$PROJECT_ROOT/requirements.txt" ] && \
     [ ! -f "$PROJECT_ROOT/pyproject.toml" ] && \
     [ ! -f "$PROJECT_ROOT/Pipfile.lock" ]; then
    return
  fi
  SCANNED=true

  # Try pip-audit first (recommended)
  if command -v pip-audit &>/dev/null; then
    info "Running: pip-audit"
    local output exit_code
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
      output=$(pip-audit -r "$PROJECT_ROOT/requirements.txt" 2>&1) && exit_code=0 || exit_code=$?
    else
      output=$(cd "$PROJECT_ROOT" && pip-audit 2>&1) && exit_code=0 || exit_code=$?
    fi

    if [ "$exit_code" -eq 0 ]; then
      success "Python deps: No known vulnerabilities"
    else
      error "Python deps: Vulnerabilities found"
      echo "$output" | head -20
      echo ""
      VIOLATIONS=$((VIOLATIONS + 1))
    fi
    return
  fi

  # Fallback: safety (if installed)
  if command -v safety &>/dev/null; then
    info "Running: safety check"
    local output exit_code
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
      output=$(safety check -r "$PROJECT_ROOT/requirements.txt" 2>&1) && exit_code=0 || exit_code=$?
    else
      output=$(cd "$PROJECT_ROOT" && safety check 2>&1) && exit_code=0 || exit_code=$?
    fi

    if [ "$exit_code" -eq 0 ]; then
      success "Python deps: No known vulnerabilities"
    else
      error "Python deps: Vulnerabilities found"
      echo "$output" | head -20
      echo ""
      VIOLATIONS=$((VIOLATIONS + 1))
    fi
    return
  fi

  warn "Python deps: No audit tool found. Install pip-audit: pip install pip-audit"
}

# ─── Go vulnerabilities ────────────────────────────────────────────
check_go_deps() {
  if [ ! -f "$PROJECT_ROOT/go.mod" ]; then
    return
  fi
  SCANNED=true

  if command -v govulncheck &>/dev/null; then
    info "Running: govulncheck"
    local output exit_code
    output=$(cd "$PROJECT_ROOT" && govulncheck ./... 2>&1) && exit_code=0 || exit_code=$?

    if [ "$exit_code" -eq 0 ]; then
      success "Go deps: No known vulnerabilities"
    else
      error "Go deps: Vulnerabilities found"
      echo "$output" | head -20
      echo ""
      VIOLATIONS=$((VIOLATIONS + 1))
    fi
  else
    warn "Go deps: govulncheck not found. Install: go install golang.org/x/vuln/cmd/govulncheck@latest"
  fi
}

# ─── Rust cargo audit ──────────────────────────────────────────────
check_rust_deps() {
  if [ ! -f "$PROJECT_ROOT/Cargo.lock" ]; then
    return
  fi
  SCANNED=true

  if command -v cargo-audit &>/dev/null || command -v cargo &>/dev/null; then
    info "Running: cargo audit"
    local output exit_code
    output=$(cd "$PROJECT_ROOT" && cargo audit 2>&1) && exit_code=0 || exit_code=$?

    if [ "$exit_code" -eq 0 ]; then
      success "Rust deps: No known vulnerabilities"
    else
      error "Rust deps: Vulnerabilities found"
      echo "$output" | head -20
      echo ""
      VIOLATIONS=$((VIOLATIONS + 1))
    fi
  else
    warn "Rust deps: cargo-audit not found. Install: cargo install cargo-audit"
  fi
}

# ─── Run all checks ────────────────────────────────────────────────
check_npm_deps
check_python_deps
check_go_deps
check_rust_deps

# ─── Report ────────────────────────────────────────────────────────
echo ""
if ! $SCANNED; then
  info "No dependency files found to audit."
  exit 0
fi

if [ $VIOLATIONS -eq 0 ]; then
  success "All dependency checks passed."
  exit 0
else
  error "$VIOLATIONS dependency vulnerability issue(s) found."
  info "Run the relevant audit tool directly for full details."
  exit 1
fi
