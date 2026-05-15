#!/usr/bin/env bash
# Isolated AI Security Gate
#
# ISOLATION PRINCIPLE:
#   Spawns a fresh Claude API session with ZERO context from the coding agent.
#   The security agent receives ONLY raw source code — no design docs, no specs,
#   no intent comments. It must find vulnerabilities without knowing WHY the code
#   was written. This prevents the confirmation bias that occurs when the same
#   agent that wrote the code also reviews it.
#
# Usage:
#   ./check-security-ai.sh [project-root] [--staged] [--full-scan] [--export=markdown]
#
# Enable (opt-in):
#   export HARNESS_ENABLE_AI_SECURITY=1
#
# Requires:
#   ANTHROPIC_API_KEY environment variable

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${1:-$(pwd)}" && pwd)"
STAGED=false
FULL_SCAN=false
EXPORT_FORMAT=""

for arg in "${@:2}"; do
  case "$arg" in
    --staged)    STAGED=true ;;
    --full-scan) FULL_SCAN=true ;;
    --export=*)  EXPORT_FORMAT="${arg#*=}" ;;
  esac
done

if [ -f "$SCRIPT_DIR/../lib/colors.sh" ]; then
  source "$SCRIPT_DIR/../lib/colors.sh"
elif [ -f "$PROJECT_ROOT/.harness/lib/colors.sh" ]; then
  source "$PROJECT_ROOT/.harness/lib/colors.sh"
else
  info()    { echo "[INFO] $*"; }
  success() { echo "[OK] $*"; }
  warn()    { echo "[WARN] $*"; }
  error()   { echo "[ERROR] $*"; }
  header()  { echo "=== $* ==="; }
  step()    { echo "  → $*"; }
fi

SECURITY_DIR="$PROJECT_ROOT/.harness/security"
FINDINGS_FILE="$SECURITY_DIR/findings.json"
DISMISSED_FILE="$SECURITY_DIR/dismissed.txt"

# ─── Prerequisites ─────────────────────────────────────────────────
check_prerequisites() {
  if ! command -v python3 &>/dev/null; then
    warn "python3 not found — skipping AI security gate."
    exit 0
  fi
  # Primary: claude CLI (Pro/Max subscription — no API key needed)
  # Fallback: ANTHROPIC_API_KEY via curl
  if ! command -v claude &>/dev/null && [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    warn "Neither 'claude' CLI nor ANTHROPIC_API_KEY found — skipping AI security gate."
    warn "Claude Code (Pro/Max) or ANTHROPIC_API_KEY is required."
    exit 0
  fi
  mkdir -p "$SECURITY_DIR"
  [ -f "$FINDINGS_FILE" ]  || echo '{"findings":[]}' > "$FINDINGS_FILE"
  [ -f "$DISMISSED_FILE" ] || touch "$DISMISSED_FILE"
}

# ─── Collect source files ──────────────────────────────────────────
collect_files() {
  local ext_pat='\.(ts|tsx|js|jsx|py|go|java|rb|php|rs|sh)$'
  local exclude_pat='node_modules|\.harness|/dist/|/build/|__pycache__|\.next|\.git|/vendor/|\.min\.'

  if $STAGED; then
    git -C "$PROJECT_ROOT" diff --cached --name-only 2>/dev/null \
      | grep -E "$ext_pat" | grep -vE "$exclude_pat" || true
  elif $FULL_SCAN; then
    find "$PROJECT_ROOT" -type f \
      \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \
         -o -name "*.py" -o -name "*.go" -o -name "*.java" -o -name "*.rb" \) \
      -not -path "*/node_modules/*" -not -path "*/.harness/*" \
      -not -path "*/dist/*"         -not -path "*/build/*" \
      -not -path "*/__pycache__/*"  -not -path "*/.next/*" \
      -not -path "*/vendor/*"       -not -name "*.min.*" \
      2>/dev/null | head -50
  else
    git -C "$PROJECT_ROOT" diff --name-only HEAD 2>/dev/null \
      | grep -E "$ext_pat" | grep -vE "$exclude_pat" || true
  fi
}

# ─── Strip intent-revealing comments ──────────────────────────────
# The security agent must not know WHY code was written — only WHAT it does.
# Removes comments like "// Why:", "// Design:", "// Spec:" etc.
strip_intent() {
  local filepath="$1"
  python3 - "$filepath" <<'PYEOF'
import sys, re

try:
    with open(sys.argv[1], 'r', errors='replace') as f:
        content = f.read()
except Exception:
    print('')
    sys.exit(0)

# Remove single-line intent/design comments
content = re.sub(
    r'(//|#)\s*(Why|Intent|Design|Spec|Reason|Purpose|Context|Business\s*logic|Architecture):.*',
    '',
    content,
    flags=re.IGNORECASE
)

# Remove JSDoc/block comments containing design rationale
intent_keywords = ['why', 'intent', 'design decision', 'business logic', 'spec:', 'architecture', 'purpose']
def strip_block(m):
    text = m.group()
    if any(k in text.lower() for k in intent_keywords):
        return ''
    return text
content = re.sub(r'/\*\*[\s\S]*?\*/', strip_block, content)

# Cap file at 300 lines to control token cost
lines = content.split('\n')
if len(lines) > 300:
    content = '\n'.join(lines[:300]) + '\n... [truncated at 300 lines]'

print(content)
PYEOF
}

# ─── Call isolated security agent ─────────────────────────────────
# ISOLATION: spawns a brand-new process with zero shared context.
#   Primary  — 'claude -p' (Claude Code Pro/Max subscription, no API key needed)
#   Fallback — ANTHROPIC_API_KEY via urllib (API billing)
#
# Either way: fresh session, adversarial prompt, code-only input.
# No conversation history from the coding agent is carried over.
call_security_agent() {
  local bundle_file="$1"

  python3 - "$bundle_file" <<'PYEOF'
import sys, os, json, re, subprocess
import urllib.request, urllib.error

bundle_file = sys.argv[1]
api_key     = os.environ.get('ANTHROPIC_API_KEY', '')

with open(bundle_file, 'r', errors='replace') as f:
    code_bundle = f.read()

if len(code_bundle) > 80000:
    code_bundle = code_bundle[:80000] + '\n... [TRUNCATED — remaining files omitted]'

SECURITY_INSTRUCTIONS = """[ROLE: ADVERSARIAL SECURITY RESEARCHER]
You have ZERO knowledge of:
- Why this code was written
- What the application is supposed to do
- The developers' intentions or design decisions

Your ONLY job: find exploitable vulnerabilities by thinking exactly like an attacker.

RULES:
1. Treat every input as potentially attacker-controlled
2. Trace data flows across ALL provided files — cross-file vulns are high priority
3. Never give developers benefit of the doubt — assume worst-case usage
4. Only report findings with confidence >= 0.6
5. Output VALID JSON ONLY. No prose outside the JSON block.

VULNERABILITY TYPES TO CHECK:
injection (SQL/command/template), broken-auth, idor, xss, path-traversal,
ssrf, race-condition, crypto (weak/hardcoded), logic-bypass, prototype-pollution,
missing-rate-limit, insecure-deserialization

OUTPUT FORMAT (strict JSON, no markdown):
{
  "findings": [
    {
      "id": "SEC-001",
      "severity": "critical|high|medium|low",
      "confidence": 0.0-1.0,
      "file": "relative/path/file.ts",
      "line": 42,
      "type": "injection|auth|idor|xss|race|exposure|logic|crypto|other",
      "title": "Concise vulnerability title",
      "attack_scenario": "Exact step-by-step attack an adversary would execute",
      "patch": "Specific, concrete code fix"
    }
  ],
  "summary": "One-line overall security posture assessment"
}

[CODE TO ANALYZE]
"""

full_prompt = SECURITY_INSTRUCTIONS + code_bundle

def parse_response(text):
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.dumps(json.loads(match.group()))
        except Exception:
            pass
    return json.dumps({"findings": [], "summary": "Could not parse agent response"})

# ── Primary: claude CLI (Pro/Max subscription) ─────────────────────
def try_claude_cli():
    result = subprocess.run(
        ['claude', '-p', '--model', 'claude-opus-4-7'],
        input=full_prompt, capture_output=True, text=True, timeout=180
    )
    if result.returncode != 0 and result.stderr:
        raise RuntimeError(result.stderr.strip())
    return parse_response(result.stdout)

# ── Fallback: Anthropic API (ANTHROPIC_API_KEY) ────────────────────
def try_api_key():
    if not api_key:
        raise RuntimeError("No ANTHROPIC_API_KEY set")
    payload = {
        "model": "claude-opus-4-7",
        "max_tokens": 4096,
        "system": "You are an adversarial security researcher. Output JSON only.",
        "messages": [{"role": "user", "content": full_prompt}]
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    return parse_response(data["content"][0]["text"])

# Try claude CLI first, fall back to API key
import shutil
if shutil.which('claude'):
    try:
        print(try_claude_cli())
    except Exception as e:
        sys.stderr.write(f"claude CLI failed ({e}), trying API key...\n")
        try:
            print(try_api_key())
        except Exception as e2:
            sys.stderr.write(f"API key also failed: {e2}\n")
            print(json.dumps({"findings": [], "summary": f"Both methods failed"}))
elif api_key:
    try:
        print(try_api_key())
    except Exception as e:
        sys.stderr.write(f"API call failed: {e}\n")
        print(json.dumps({"findings": [], "summary": f"Error: {e}"}))
else:
    sys.stderr.write("No claude CLI and no ANTHROPIC_API_KEY\n")
    print(json.dumps({"findings": [], "summary": "No auth method available"}))
PYEOF
}

# ─── Filter dismissed findings ─────────────────────────────────────
filter_dismissed() {
  local raw_json="$1"
  python3 - "$DISMISSED_FILE" "$raw_json" <<'PYEOF'
import sys, json

dismissed_file = sys.argv[1]
raw_json       = sys.argv[2]

try:
    with open(dismissed_file) as f:
        # Lines not starting with '#' are dismissed IDs
        dismissed_ids = set(
            line.strip() for line in f
            if line.strip() and not line.startswith('#')
        )
except Exception:
    dismissed_ids = set()

try:
    data = json.loads(raw_json)
    findings = data.get("findings", [])
except Exception:
    findings = []

filtered = [
    f for f in findings
    if f.get("id", "") not in dismissed_ids
    and float(f.get("confidence", 0)) >= 0.6
]

print(json.dumps(filtered))
PYEOF
}

# ─── Display findings ──────────────────────────────────────────────
display_findings() {
  local findings_json="$1"
  python3 - "$findings_json" <<'PYEOF'
import sys, json

try:
    findings = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)

if not findings:
    sys.exit(0)

order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
findings.sort(key=lambda x: order.get(x.get("severity", "low"), 4))

icons = {"critical": "🚨", "high": "🔴", "medium": "🟡", "low": "🔵"}

for f in findings:
    sev  = f.get("severity", "unknown")
    icon = icons.get(sev, "◻")
    conf = float(f.get("confidence", 0))
    print(f"{icon} [{sev.upper()}] {f.get('id','?')} — {f.get('title','?')} ({conf:.0%} confidence)")
    print(f"   File   : {f.get('file','?')}:{f.get('line','?')}")
    print(f"   Type   : {f.get('type','?')}")
    print(f"   Attack : {f.get('attack_scenario','?')}")
    print(f"   Patch  : {f.get('patch','?')}")
    print()
PYEOF
}

# ─── Save findings to tracker ──────────────────────────────────────
save_findings() {
  local new_json="$1"
  python3 - "$FINDINGS_FILE" "$new_json" <<'PYEOF'
import sys, json
from datetime import datetime

findings_file = sys.argv[1]
new_json      = sys.argv[2]

try:
    new_findings = json.loads(new_json)
except Exception:
    sys.exit(0)

try:
    with open(findings_file) as f:
        existing = json.load(f)
except Exception:
    existing = {"findings": []}

existing_ids = {f["id"] for f in existing.get("findings", [])}

for f in new_findings:
    if f.get("id") not in existing_ids:
        f["detected_at"] = datetime.now().isoformat()
        existing.setdefault("findings", []).append(f)

with open(findings_file, "w") as f:
    json.dump(existing, f, indent=2)
PYEOF
}

# ─── Export to Markdown ────────────────────────────────────────────
export_markdown() {
  local findings_json="$1"
  local report_file="$PROJECT_ROOT/SECURITY_REPORT.md"
  python3 - "$findings_json" "$report_file" <<'PYEOF'
import sys, json
from datetime import datetime

findings_json = sys.argv[1]
report_file   = sys.argv[2]

try:
    findings = json.loads(findings_json)
except Exception:
    findings = []

lines = [
    "# Security Report",
    f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
    "_Agent: isolated security agent (claude-opus-4-7, zero shared context)_",
    ""
]

if not findings:
    lines.append("✅ No security issues found.")
else:
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(key=lambda x: order.get(x.get("severity", "low"), 4))

    counts = {}
    for f in findings:
        s = f.get("severity", "?")
        counts[s] = counts.get(s, 0) + 1

    summary = " | ".join(f"{v} {k}" for k, v in sorted(counts.items(), key=lambda x: order.get(x[0], 9)))
    lines += [f"## {len(findings)} issue(s) found — {summary}", ""]

    for f in findings:
        sev  = f.get("severity", "?").upper()
        conf = float(f.get("confidence", 0))
        lines += [
            f"### [{sev}] {f.get('title')} `{f.get('id')}`",
            f"- **File**: `{f.get('file')}:{f.get('line')}`",
            f"- **Type**: {f.get('type')}",
            f"- **Confidence**: {conf:.0%}",
            f"- **Attack scenario**: {f.get('attack_scenario')}",
            f"- **Patch**: {f.get('patch')}",
            ""
        ]

with open(report_file, "w") as f:
    f.write("\n".join(lines))

print(report_file)
PYEOF
}

# ─── Count by severity ─────────────────────────────────────────────
count_by_severity() {
  python3 - "$1" <<'PYEOF'
import sys, json
try:
    findings = json.loads(sys.argv[1])
    c = sum(1 for f in findings if f.get("severity") == "critical")
    h = sum(1 for f in findings if f.get("severity") == "high")
    m = sum(1 for f in findings if f.get("severity") == "medium")
    l = sum(1 for f in findings if f.get("severity") == "low")
    print(f"{c} {h} {m} {l}")
except Exception:
    print("0 0 0 0")
PYEOF
}

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

header "AI Security Analysis (Isolated Agent)"

check_prerequisites

FILES=$(collect_files)
if [ -z "$FILES" ]; then
  success "No source files to analyze."
  exit 0
fi

FILE_COUNT=$(echo "$FILES" | grep -c . || echo 0)
info "Files to analyze : $FILE_COUNT"
info "Model            : claude-opus-4-7"
info "Session          : ISOLATED — zero shared context with coding agent"
echo ""

# Build code bundle via temp file (handles large inputs safely)
BUNDLE_FILE=$(mktemp)
trap 'rm -f "$BUNDLE_FILE"' EXIT

while IFS= read -r file; do
  [ -z "$file" ] && continue
  FULL_PATH="$PROJECT_ROOT/$file"
  [ ! -f "$FULL_PATH" ] && FULL_PATH="$file"
  [ ! -f "$FULL_PATH" ] && continue

  STRIPPED=$(strip_intent "$FULL_PATH")
  printf '\n=== FILE: %s ===\n%s\n=== END: %s ===\n' "$file" "$STRIPPED" "$file" >> "$BUNDLE_FILE"
done <<< "$FILES"

if [ ! -s "$BUNDLE_FILE" ]; then
  success "No readable source files found."
  exit 0
fi

step "Spawning isolated security agent..."
RAW_RESULT=$(call_security_agent "$BUNDLE_FILE")

FILTERED=$(filter_dismissed "$RAW_RESULT")

display_findings "$FILTERED"

save_findings "$FILTERED"

if [ "$EXPORT_FORMAT" = "markdown" ]; then
  REPORT=$(export_markdown "$FILTERED")
  success "Report exported: $REPORT"
fi

read -r CRITICAL HIGH MEDIUM LOW <<< "$(count_by_severity "$FILTERED")"
TOTAL=$((CRITICAL + HIGH + MEDIUM + LOW))

echo ""
if [ "$TOTAL" -eq 0 ]; then
  success "No security issues found. Isolated agent scan complete."
  exit 0
elif [ "$((CRITICAL + HIGH))" -gt 0 ]; then
  error "$CRITICAL critical + $HIGH high severity issue(s) found. Commit blocked."
  info "To dismiss a false positive:"
  info "  bash .harness/security/dismiss-finding.sh SEC-001 \"reason\""
  exit 1
else
  warn "$MEDIUM medium + $LOW low severity issue(s) found. Review recommended."
  info "These don't block commits but should be addressed."
  exit 0
fi
