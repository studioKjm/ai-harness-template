#!/usr/bin/env bash
# Dismiss a security finding with a documented reason.
# Dismissed findings are excluded from future scans but preserved in findings.json for audit.
#
# Usage:
#   bash .harness/security/dismiss-finding.sh <finding-id> "reason why it's safe"
#
# Example:
#   bash .harness/security/dismiss-finding.sh SEC-003 "Input sanitized upstream in middleware"

set -euo pipefail

SECURITY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DISMISSED_FILE="$SECURITY_DIR/dismissed.txt"
FINDINGS_FILE="$SECURITY_DIR/findings.json"

if [ $# -lt 2 ]; then
  echo "Usage: $0 <finding-id> \"reason\""
  echo "Example: $0 SEC-001 \"False positive — input sanitized in middleware\""
  exit 1
fi

FINDING_ID="$1"
REASON="$2"
DATE=$(date +%Y-%m-%d)
AUTHOR=$(git config user.name 2>/dev/null || echo "unknown")

# Validate the finding ID exists in findings.json
if command -v python3 &>/dev/null && [ -f "$FINDINGS_FILE" ]; then
  EXISTS=$(python3 -c "
import json, sys
try:
    with open('$FINDINGS_FILE') as f:
        data = json.load(f)
    ids = [x.get('id') for x in data.get('findings', [])]
    print('yes' if '$FINDING_ID' in ids else 'no')
except:
    print('unknown')
" 2>/dev/null || echo "unknown")

  if [ "$EXISTS" = "no" ]; then
    echo "[WARN] Finding '$FINDING_ID' not found in findings.json."
    echo "       Available IDs:"
    python3 -c "
import json
with open('$FINDINGS_FILE') as f:
    data = json.load(f)
for f in data.get('findings', []):
    print(f\"  {f.get('id','?')} — {f.get('title','?')} [{f.get('severity','?')}]\")
" 2>/dev/null || true
    echo ""
    read -r -p "Dismiss anyway? [y/N] " confirm
    [[ "$confirm" != "y" && "$confirm" != "Y" ]] && exit 0
  fi
fi

# Check if already dismissed
if grep -qx "$FINDING_ID" "$DISMISSED_FILE" 2>/dev/null; then
  echo "[INFO] $FINDING_ID is already dismissed."
  exit 0
fi

# Append to dismissed.txt
{
  echo "# $DATE | $AUTHOR | $REASON"
  echo "$FINDING_ID"
} >> "$DISMISSED_FILE"

echo "[OK] Dismissed: $FINDING_ID"
echo "     Reason: $REASON"
echo "     Recorded in: .harness/security/dismissed.txt"
echo ""
echo "     Stage and commit this file to share the dismissal with the team:"
echo "       git add .harness/security/dismissed.txt"
