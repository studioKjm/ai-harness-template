#!/usr/bin/env bash
# Install pre-commit hook that runs harness gates.
# Usage: ./install-hooks.sh [project-root]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(pwd)}"

if [ -f "$SCRIPT_DIR/../lib/colors.sh" ]; then
  source "$SCRIPT_DIR/../lib/colors.sh"
else
  info() { echo "[INFO] $*"; }
  success() { echo "[OK] $*"; }
  warn() { echo "[WARN] $*"; }
  error() { echo "[ERROR] $*"; }
fi

if [ ! -d "$PROJECT_ROOT/.git" ]; then
  error "Not a git repository: $PROJECT_ROOT"
  exit 1
fi

HOOKS_DIR="$PROJECT_ROOT/.git/hooks"
PRE_COMMIT="$HOOKS_DIR/pre-commit"
HARNESS_MARKER="# === AI HARNESS GATES ==="

# Check if harness hooks are already installed
if [ -f "$PRE_COMMIT" ] && grep -q "$HARNESS_MARKER" "$PRE_COMMIT" 2>/dev/null; then
  info "Harness hooks already installed. Updating..."
  # Remove old harness section
  sed -i.bak "/$HARNESS_MARKER/,/# === END HARNESS ===/d" "$PRE_COMMIT"
  rm -f "$PRE_COMMIT.bak"
fi

# Create pre-commit if it doesn't exist
if [ ! -f "$PRE_COMMIT" ]; then
  cat > "$PRE_COMMIT" << 'HOOK'
#!/usr/bin/env bash
# Pre-commit hook
HOOK
  chmod +x "$PRE_COMMIT"
fi

# Append harness gates
cat >> "$PRE_COMMIT" << 'HOOK'

# === AI HARNESS GATES ===
# Auto-installed by AI Harness. Do not edit this section manually.

HARNESS_DIR="$(git rev-parse --show-toplevel)/.harness"

if [ -d "$HARNESS_DIR/gates" ]; then
  echo ""
  echo "=== Running Harness Gates ==="
  echo ""

  GATE_FAILED=0

  # Check for secret leaks (staged files only)
  if [ -f "$HARNESS_DIR/gates/check-secrets.sh" ]; then
    if ! "$HARNESS_DIR/gates/check-secrets.sh" "$(git rev-parse --show-toplevel)" --staged; then
      GATE_FAILED=1
    fi
  fi

  # Check dependency boundaries
  if [ -f "$HARNESS_DIR/gates/check-boundaries.sh" ]; then
    if ! "$HARNESS_DIR/gates/check-boundaries.sh" "$(git rev-parse --show-toplevel)"; then
      GATE_FAILED=1
    fi
  fi

  if [ $GATE_FAILED -ne 0 ]; then
    echo ""
    echo "[HARNESS] Commit blocked. Fix violations above before committing."
    echo "[HARNESS] To bypass (NOT recommended): git commit --no-verify"
    echo ""
    exit 1
  fi

  echo ""
  echo "[HARNESS] All gates passed."
  echo ""
fi
# === END HARNESS ===
HOOK

chmod +x "$PRE_COMMIT"
success "Pre-commit hook installed at $PRE_COMMIT"
