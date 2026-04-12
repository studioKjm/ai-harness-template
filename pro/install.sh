#!/usr/bin/env bash
# AI Harness Pro Installer
# Installs the Python-enhanced version on top of the Lite harness.
# Usage: ./pro/install.sh [target-project-path]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_DIR="$(dirname "$SCRIPT_DIR")"
source "$HARNESS_DIR/lib/colors.sh"

TARGET="${1:-.}"
TARGET="$(cd "$TARGET" && pwd)"

header "AI Harness Pro Installer"
info "Target project: $TARGET"
echo ""

# ─── Prerequisites ────────────────────────────────────────────────
header "Step 1: Checking prerequisites"

# Check Python
if ! command -v python3 &>/dev/null; then
  error "Python 3.11+ is required but not found."
  error "Install Python: https://www.python.org/downloads/"
  exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
  error "Python 3.11+ required (found: $PYTHON_VERSION)"
  exit 1
fi
success "Python $PYTHON_VERSION found"

# ─── Install Lite first ───────────────────────────────────────────
header "Step 2: Installing Lite harness"

if [ ! -f "$TARGET/CLAUDE.md" ] || [ ! -d "$TARGET/.harness" ]; then
  info "Running Lite installer first..."
  "$HARNESS_DIR/init.sh" "$TARGET"
else
  success "Lite harness already installed"
fi

# ─── Install Python package ──────────────────────────────────────
header "Step 3: Installing harness-pro Python package"

cd "$SCRIPT_DIR"
pip install -e ".[all]" --quiet 2>/dev/null || pip install -e . --quiet
success "harness-pro package installed"

# ─── Setup Ouroboros directories ─────────────────────────────────
header "Step 4: Setting up Ouroboros structure"

mkdir -p "$TARGET/.harness/ouroboros/seeds"
mkdir -p "$TARGET/.harness/ouroboros/interviews"
mkdir -p "$TARGET/.harness/ouroboros/evaluations"

# Copy scoring checklist
if [ ! -f "$TARGET/.harness/ouroboros/scoring/ambiguity-checklist.yaml" ]; then
  mkdir -p "$TARGET/.harness/ouroboros/scoring"
  cp "$HARNESS_DIR/ouroboros/scoring/ambiguity-checklist.yaml" "$TARGET/.harness/ouroboros/scoring/"
  success "Installed ambiguity checklist"
fi

# Copy seed template
if [ ! -f "$TARGET/.harness/ouroboros/templates/seed-spec.yaml" ]; then
  mkdir -p "$TARGET/.harness/ouroboros/templates"
  cp "$HARNESS_DIR/ouroboros/templates/seed-spec.yaml" "$TARGET/.harness/ouroboros/templates/"
  success "Installed seed template"
fi

success "Ouroboros structure created"

# ─── Install commands ────────────────────────────────────────────
header "Step 5: Installing slash commands"

COMMANDS_TARGET="$TARGET/.claude/commands"
mkdir -p "$COMMANDS_TARGET"

for cmd in "$HARNESS_DIR/commands/"*.md; do
  cmdname=$(basename "$cmd")
  cp "$cmd" "$COMMANDS_TARGET/$cmdname"
done
success "Installed $(ls "$HARNESS_DIR/commands/"*.md | wc -l | tr -d ' ') commands"

# ─── Install agents ─────────────────────────────────────────────
header "Step 6: Installing agent personas"

AGENTS_TARGET="$TARGET/.claude/agents"
mkdir -p "$AGENTS_TARGET"

for agent in "$HARNESS_DIR/agents/"*.md; do
  agentname=$(basename "$agent")
  cp "$agent" "$AGENTS_TARGET/$agentname"
done
success "Installed $(ls "$HARNESS_DIR/agents/"*.md | wc -l | tr -d ' ') agent personas"

# ─── Install Pro hooks ───────────────────────────────────────────
header "Step 7: Configuring Pro hooks"

# Copy hook scripts
mkdir -p "$TARGET/.harness/pro-hooks"
cp "$SCRIPT_DIR/hooks/keyword-detector.py" "$TARGET/.harness/pro-hooks/"
cp "$SCRIPT_DIR/hooks/drift-monitor.py" "$TARGET/.harness/pro-hooks/"
cp "$SCRIPT_DIR/hooks/session-start.py" "$TARGET/.harness/pro-hooks/"
chmod +x "$TARGET/.harness/pro-hooks/"*.py

success "Pro hooks installed"

# ─── Install spec gate ───────────────────────────────────────────
header "Step 8: Installing spec gate"

cp "$HARNESS_DIR/gates/check-spec.sh" "$TARGET/.harness/gates/check-spec.sh"
chmod +x "$TARGET/.harness/gates/check-spec.sh"
success "Spec completeness gate installed"

# ─── Update .gitignore ───────────────────────────────────────────
GITIGNORE="$TARGET/.gitignore"
ENTRIES=(".harness/ouroboros/session.db" ".harness/ouroboros/interviews/" ".harness/ouroboros/evaluations/")

touch "$GITIGNORE"
for entry in "${ENTRIES[@]}"; do
  if ! grep -qxF "$entry" "$GITIGNORE"; then
    echo "$entry" >> "$GITIGNORE"
  fi
done

# ─── Done ────────────────────────────────────────────────────────
header "Harness Pro Installation Complete"
echo ""
echo "  Everything from Lite, plus:"
echo ""
echo "  Ouroboros Workflow:"
echo "    /interview    — Socratic interview with ambiguity scoring"
echo "    /seed          — Generate immutable spec from interview"
echo "    /run           — Double Diamond execution"
echo "    /evaluate      — 3-stage verification"
echo "    /evolve        — Evolution loop with convergence"
echo "    /unstuck       — Multi-perspective problem solver"
echo "    /pm            — PRD generator"
echo ""
echo "  Pro CLI:"
echo "    harness interview 'topic'  — Start interview"
echo "    harness score              — Check ambiguity"
echo "    harness evaluate           — Run evaluation pipeline"
echo "    harness drift <file>       — Measure spec drift"
echo "    harness status             — Show session status"
echo ""
echo "  9 Agent Personas: interviewer, ontologist, seed-architect,"
echo "    evaluator, contrarian, simplifier, researcher, architect, hacker"
echo ""
success "Harness Pro installed successfully!"
