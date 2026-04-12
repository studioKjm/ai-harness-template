#!/usr/bin/env bash
# Simple template renderer. No external dependencies.
# Usage: ./render-template.sh <template-file> <KEY=VALUE> [KEY=VALUE ...]
# Template syntax: {{KEY}} for variable substitution
#                  {{#IF_KEY}} ... {{/IF_KEY}} for conditional blocks (kept if KEY is truthy)

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <template-file> [KEY=VALUE ...]" >&2
  exit 1
fi

TEMPLATE_FILE="$1"
shift

if [ ! -f "$TEMPLATE_FILE" ]; then
  echo "Error: Template file not found: $TEMPLATE_FILE" >&2
  exit 1
fi

# Start with template content
CONTENT="$(cat "$TEMPLATE_FILE")"

# Process each KEY=VALUE argument
KEYS=""
for arg in "$@"; do
  key="${arg%%=*}"
  value="${arg#*=}"
  KEYS="$KEYS $key"

  if [ -n "$value" ] && [ "$value" != "false" ] && [ "$value" != "0" ]; then
    # Key is truthy: keep IF block content, remove markers
    CONTENT="$(echo "$CONTENT" | sed "s/{{#IF_${key}}}//g" | sed "s/{{\/IF_${key}}}//g")"
  else
    # Key is falsy: remove entire IF block
    # Use awk for multi-line deletion (more reliable than sed across platforms)
    CONTENT="$(echo "$CONTENT" | awk "
      /\{\{#IF_${key}\}\}/{skip=1; next}
      /\{\{\/IF_${key}\}\}/{skip=0; next}
      !skip{print}
    ")"
  fi

  # Replace {{KEY}} with value
  escaped_value="$(echo "$value" | sed 's/[&/\]/\\&/g')"
  CONTENT="$(echo "$CONTENT" | sed "s/{{${key}}}/${escaped_value}/g")"
done

# Clean up any remaining undefined IF blocks
CONTENT="$(echo "$CONTENT" | awk '
  /\{\{#IF_[A-Z_]+\}\}/{skip=1; next}
  /\{\{\/IF_[A-Z_]+\}\}/{skip=0; next}
  !skip{print}
')"

echo "$CONTENT"
