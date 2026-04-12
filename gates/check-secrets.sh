#!/usr/bin/env bash
# Check for leaked secrets in staged files or all tracked files.
# Usage: ./check-secrets.sh [project-root] [--staged]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(pwd)}"
CHECK_STAGED=false
[ "${2:-}" = "--staged" ] && CHECK_STAGED=true

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

header "Secret Leak Detection"

VIOLATIONS=0

# ─── Pattern Definitions ──────────────────────────────────────────

# High-confidence patterns (specific formats)
PATTERNS=(
  # AWS
  'AKIA[0-9A-Z]{16}'                          # AWS Access Key ID
  'ASIA[0-9A-Z]{16}'                          # AWS Temporary Access Key

  # OpenAI / Stripe
  'sk-[a-zA-Z0-9]{20,}'                       # OpenAI / Stripe secret key
  'sk_live_[a-zA-Z0-9]+'                      # Stripe live secret key
  'pk_live_[a-zA-Z0-9]+'                      # Stripe live public key
  'rk_live_[a-zA-Z0-9]+'                      # Stripe restricted key

  # GitHub
  'ghp_[a-zA-Z0-9]{36}'                       # GitHub Personal Access Token
  'gho_[a-zA-Z0-9]{36}'                       # GitHub OAuth Token
  'ghs_[a-zA-Z0-9]{36}'                       # GitHub App Installation Token
  'ghr_[a-zA-Z0-9]{36}'                       # GitHub Refresh Token
  'github_pat_[a-zA-Z0-9_]{22,}'              # GitHub Fine-grained PAT

  # GitLab
  'glpat-[a-zA-Z0-9\-]{20,}'                  # GitLab Personal Access Token

  # Slack
  'xoxb-[0-9]+-[0-9]+-[a-zA-Z0-9]+'           # Slack Bot Token
  'xoxp-[0-9]+-[0-9]+-[0-9]+-[a-f0-9]+'       # Slack User Token
  'xoxr-[0-9]+-[a-zA-Z0-9]+'                  # Slack Refresh Token
  'xapp-[0-9]+-[A-Za-z0-9\-]+'                # Slack App Token

  # Twilio
  'SK[0-9a-fA-F]{32}'                         # Twilio API Key SID
  'AC[0-9a-fA-F]{32}'                         # Twilio Account SID

  # SendGrid
  'SG\.[a-zA-Z0-9_\-]{22}\.[a-zA-Z0-9_\-]{43}' # SendGrid API Key

  # Auth0
  'eyJ[a-zA-Z0-9_\-]*\.eyJ[a-zA-Z0-9_\-]*\.[a-zA-Z0-9_\-]*' # JWT Token (Auth0 and others)

  # Firebase / Google
  'AIza[0-9A-Za-z\-_]{35}'                    # Google / Firebase API Key
  '"type"[[:space:]]*:[[:space:]]*"service_account"' # GCP Service Account JSON

  # Vercel
  'vercel_[a-zA-Z0-9_]{24,}'                  # Vercel Token

  # Supabase
  'sbp_[a-zA-Z0-9]{40,}'                      # Supabase Service Key

  # Anthropic
  'sk-ant-[a-zA-Z0-9\-]{20,}'                 # Anthropic API Key

  # Private Keys
  'BEGIN RSA PRIVATE KEY'
  'BEGIN OPENSSH PRIVATE KEY'
  'BEGIN EC PRIVATE KEY'
  'BEGIN PGP PRIVATE KEY'
  'BEGIN DSA PRIVATE KEY'
  'BEGIN PRIVATE KEY'

  # Connection Strings
  'postgres://[^[:space:]]+'                   # PostgreSQL URI
  'postgresql://[^[:space:]]+'                 # PostgreSQL URI (alternate)
  'mysql://[^[:space:]]+'                      # MySQL URI
  'mongodb://[^[:space:]]*@[^[:space:]]+'      # MongoDB URI with credentials
  'mongodb\+srv://[^[:space:]]+'               # MongoDB Atlas URI
  'redis://:[^[:space:]]+'                     # Redis URI with password
  'rediss://[^[:space:]]+'                     # Redis TLS URI
  'amqp://[^[:space:]]*@[^[:space:]]+'         # RabbitMQ URI
)

# Generic patterns (lower confidence, checked in non-test/non-example files)
GENERIC_PATTERNS=(
  'password[[:space:]]*=[[:space:]]*"[^"]{8,}"'
  'secret[[:space:]]*=[[:space:]]*"[^"]{8,}"'
  'api_key[[:space:]]*=[[:space:]]*"[^"]{8,}"'
  'token[[:space:]]*=[[:space:]]*"[^"]{8,}"'
  'DATABASE_URL[[:space:]]*=[[:space:]]*"[^"]{10,}"'
  'PRIVATE_KEY[[:space:]]*=[[:space:]]*"[^"]{10,}"'
)

# ─── File-level checks ──────────────────────────────────────────────

# Check if .env files are being committed
check_env_files() {
  local files
  if $CHECK_STAGED; then
    files=$(cd "$PROJECT_ROOT" && git diff --cached --name-only 2>/dev/null || true)
  else
    files=$(cd "$PROJECT_ROOT" && git ls-files 2>/dev/null || find . -type f -not -path '*/.git/*' -not -path '*/node_modules/*')
  fi

  while IFS= read -r file; do
    [ -z "$file" ] && continue
    local basename=$(basename "$file")

    # Check for .env files (except safe templates/examples)
    if [[ "$basename" =~ ^\.env(\..+)?$ ]] && [[ "$basename" != ".env.example" ]] && [[ "$basename" != ".env.template" ]] && [[ "$basename" != ".env.sample" ]] && [[ ! "$basename" =~ \.example$ ]]; then
      error "BLOCKED: $file"
      echo "  .env files must not be committed. Add to .gitignore."
      echo ""
      VIOLATIONS=$((VIOLATIONS + 1))
    fi

    # Check for key/credential files
    if [[ "$basename" =~ \.(pem|key|p12|pfx|jks)$ ]]; then
      error "BLOCKED: $file"
      echo "  Credential file detected. Do not commit private keys."
      echo ""
      VIOLATIONS=$((VIOLATIONS + 1))
    fi
  done <<< "$files"
}

# ─── Content-level checks ──────────────────────────────────────────

check_content() {
  local files_to_check

  if $CHECK_STAGED; then
    files_to_check=$(cd "$PROJECT_ROOT" && git diff --cached --name-only 2>/dev/null || true)
  else
    files_to_check=$(cd "$PROJECT_ROOT" && find . -type f \
      -not -path '*/.git/*' \
      -not -path '*/node_modules/*' \
      -not -path '*/__pycache__/*' \
      -not -path '*/.next/*' \
      -not -path '*/dist/*' \
      -not -path '*/build/*' \
      -not -path '*/*.lock' \
      -not -path '*/package-lock.json' \
      -not -path '*/*.min.js' \
      -not -path '*/*.min.css' \
      -not -path '*/.harness/*' \
      -not -name '*.png' -not -name '*.jpg' -not -name '*.gif' \
      -not -name '*.ico' -not -name '*.woff*' -not -name '*.ttf' \
      -not -name '*.mp4' -not -name '*.mp3' \
      2>/dev/null)
  fi

  while IFS= read -r file; do
    [ -z "$file" ] && continue
    [ ! -f "$PROJECT_ROOT/$file" ] && continue

    local full_path="$PROJECT_ROOT/$file"

    # Skip binary files
    file -b --mime "$full_path" 2>/dev/null | grep -q "text/" || continue

    # Check high-confidence patterns
    for pattern in "${PATTERNS[@]}"; do
      local matches
      matches=$(grep -nE "$pattern" "$full_path" 2>/dev/null | head -3 || true)
      [ -z "$matches" ] && continue
      while IFS= read -r match; do
        local line_num=$(echo "$match" | cut -d: -f1)
        error "SECRET DETECTED: $file:$line_num"
        echo "  Pattern: $pattern"
        echo "  Line: $(echo "$match" | cut -d: -f2- | head -c 100)..."
        echo ""
        VIOLATIONS=$((VIOLATIONS + 1))
      done <<< "$matches"
    done

    # Check generic patterns in non-test, non-example files
    local basename=$(basename "$file")
    if [[ ! "$file" =~ (test|spec|example|fixture|mock|__test__|_test\.) ]]; then
      for pattern in "${GENERIC_PATTERNS[@]}"; do
        local matches
        matches=$(grep -nE "$pattern" "$full_path" 2>/dev/null | head -3 || true)
        [ -z "$matches" ] && continue
        while IFS= read -r match; do
          local line_num=$(echo "$match" | cut -d: -f1)
          warn "POTENTIAL SECRET: $file:$line_num"
          echo "  Pattern: $pattern (generic — verify manually)"
          echo "  Line: $(echo "$match" | cut -d: -f2- | head -c 100)..."
          echo ""
          VIOLATIONS=$((VIOLATIONS + 1))
        done <<< "$matches"
      done
    fi
  done <<< "$files_to_check"
}

# ─── Run checks ──────────────────────────────────────────────────

check_env_files
check_content

# Report
echo ""
if [ $VIOLATIONS -eq 0 ]; then
  success "No secrets detected."
  exit 0
else
  error "$VIOLATIONS potential secret(s) found. Fix before committing."
  exit 1
fi
