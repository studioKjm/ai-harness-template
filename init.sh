#!/usr/bin/env bash
# AI Harness Installer
# Usage: ./init.sh [target-project-path] [options]
# Options:
#   --yes, -y           Skip all confirmations (use defaults)
#   --preset PRESET     Permission preset: strict | standard | permissive (default: standard)
#   --name NAME         Project name (default: target dirname)
# Detects tech stack, generates CLAUDE.md, installs gates & boundaries.

set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HARNESS_DIR/lib/colors.sh"

# Parse args
TARGET="."
AUTO_YES=0
PRESET=""
CUSTOM_PROJECT_NAME=""
while [ $# -gt 0 ]; do
  case "$1" in
    --yes|-y) AUTO_YES=1; shift ;;
    --preset) PRESET="$2"; shift 2 ;;
    --name) CUSTOM_PROJECT_NAME="$2"; shift 2 ;;
    -*) error "Unknown option: $1"; exit 1 ;;
    *) TARGET="$1"; shift ;;
  esac
done

# ─── Preflight checks ───────────────────────────────────────────────
if [ ! -d "$TARGET" ]; then
  error "Target directory does not exist: $TARGET"
  exit 1
fi

TARGET="$(cd "$TARGET" && pwd)"

if [ ! -w "$TARGET" ]; then
  error "Target directory is not writable: $TARGET"
  exit 1
fi

# Verify harness source files are intact
for required in "lib/detect-stack.sh" "lib/render-template.sh" "templates/CLAUDE.md.hbs" "templates/architecture-invariants.md.hbs"; do
  if [ ! -f "$HARNESS_DIR/$required" ]; then
    error "Missing required file: $HARNESS_DIR/$required"
    error "Harness installation may be corrupted. Re-clone the repository."
    exit 1
  fi
done

header "AI Harness Installer"
info "Target project: $TARGET"
echo ""

# ─── Step 1: Detect stack ───────────────────────────────────────────
header "Step 1: Detecting tech stack"

STACK_JSON="$("$HARNESS_DIR/lib/detect-stack.sh" "$TARGET")" || {
  error "Stack detection failed."
  exit 1
}

# Robust JSON parsing: flatten to single line, then extract fields
STACK_JSON_FLAT=$(echo "$STACK_JSON" | tr -d '\n' | tr -s ' ')
STACKS=$(echo "$STACK_JSON_FLAT" | sed 's/.*"stacks"[[:space:]]*:[[:space:]]*\[//;s/\].*//' | tr -d '"' | tr ',' '\n' | tr -d ' ')
PKG_MANAGER=$(echo "$STACK_JSON_FLAT" | sed 's/.*"package_manager"[[:space:]]*:[[:space:]]*"//;s/".*//')
FRONTEND_DIR=$(echo "$STACK_JSON_FLAT" | sed 's/.*"frontend_dir"[[:space:]]*:[[:space:]]*"//;s/".*//')
BACKEND_DIR=$(echo "$STACK_JSON_FLAT" | sed 's/.*"backend_dir"[[:space:]]*:[[:space:]]*"//;s/".*//')

echo "$STACK_JSON" | sed 's/^/  /'
echo ""

STACKS_COMMA=$(echo "$STACKS" | tr '\n' ',' | sed 's/,$//')

info "Detected stacks: ${BOLD}${STACKS_COMMA}${NC}"
info "Package manager: ${BOLD}${PKG_MANAGER}${NC}"
echo ""

if [ "$AUTO_YES" -eq 0 ]; then
  read -p "Continue with these settings? [Y/n] " -n 1 -r CONFIRM
  echo ""
  if [[ "$CONFIRM" =~ ^[Nn]$ ]]; then
    warn "Aborted by user."
    exit 0
  fi
fi

# ─── Step 2: Permission preset ─────────────────────────────────────
header "Step 2: Claude Code permission preset"
if [ -z "$PRESET" ]; then
  if [ "$AUTO_YES" -eq 1 ]; then
    PRESET="standard"
  else
    echo "  1) strict      - Production/client projects (most restrictive)"
    echo "  2) standard    - Regular development (recommended)"
    echo "  3) permissive  - Prototyping (minimal restrictions)"
    echo ""
    read -p "Select preset [1-3, default=2]: " -n 1 -r PRESET_CHOICE
    echo ""
    case "${PRESET_CHOICE:-2}" in
      1) PRESET="strict" ;;
      3) PRESET="permissive" ;;
      *) PRESET="standard" ;;
    esac
  fi
fi

# Validate preset value
case "$PRESET" in
  strict|standard|permissive) ;;
  *) error "Invalid preset: $PRESET (must be strict|standard|permissive)"; exit 1 ;;
esac

success "Preset: $PRESET"

# ─── Step 3: Project name ──────────────────────────────────────────
header "Step 3: Project name"
PROJECT_NAME="${CUSTOM_PROJECT_NAME:-$(basename "$TARGET")}"
if [ -z "$CUSTOM_PROJECT_NAME" ] && [ "$AUTO_YES" -eq 0 ]; then
  read -p "Project name [$PROJECT_NAME]: " -r INPUT_NAME
  PROJECT_NAME="${INPUT_NAME:-$PROJECT_NAME}"
fi
success "Project name: $PROJECT_NAME"

# ─── Step 4: Generate CLAUDE.md ────────────────────────────────────
header "Step 4: Generating CLAUDE.md"

# Determine which stack sections to include
HAS_NEXTJS=""; HAS_NESTJS=""; HAS_FASTAPI=""; HAS_DJANGO=""; HAS_PYTHON=""; HAS_TYPESCRIPT=""
HAS_PRISMA=""; HAS_ALEMBIC=""; HAS_DOCKER=""; HAS_MONOREPO=""

for stack in $STACKS; do
  case "$stack" in
    nextjs)     HAS_NEXTJS="true" ;;
    nestjs)     HAS_NESTJS="true" ;;
    fastapi)    HAS_FASTAPI="true" ;;
    django)     HAS_DJANGO="true" ;;
    python)     HAS_PYTHON="true" ;;
    typescript) HAS_TYPESCRIPT="true" ;;
    prisma)     HAS_PRISMA="true" ;;
    alembic)    HAS_ALEMBIC="true" ;;
    docker)     HAS_DOCKER="true" ;;
    monorepo|turborepo) HAS_MONOREPO="true" ;;
  esac
done

if ! "$HARNESS_DIR/lib/render-template.sh" "$HARNESS_DIR/templates/CLAUDE.md.hbs" \
  "PROJECT_NAME=$PROJECT_NAME" \
  "STACKS=$STACKS_COMMA" \
  "FRONTEND_DIR=$FRONTEND_DIR" \
  "BACKEND_DIR=$BACKEND_DIR" \
  "PKG_MANAGER=$PKG_MANAGER" \
  "HAS_NEXTJS=$HAS_NEXTJS" \
  "HAS_NESTJS=$HAS_NESTJS" \
  "HAS_FASTAPI=$HAS_FASTAPI" \
  "HAS_DJANGO=$HAS_DJANGO" \
  "HAS_PYTHON=$HAS_PYTHON" \
  "HAS_TYPESCRIPT=$HAS_TYPESCRIPT" \
  "HAS_PRISMA=$HAS_PRISMA" \
  "HAS_ALEMBIC=$HAS_ALEMBIC" \
  "HAS_DOCKER=$HAS_DOCKER" \
  "HAS_MONOREPO=$HAS_MONOREPO" \
  > "$TARGET/CLAUDE.md"; then
  error "Failed to generate CLAUDE.md. Check template and render-template.sh."
  exit 1
fi

success "Generated CLAUDE.md"

# ─── Step 5: Generate Architecture Invariants ──────────────────────
header "Step 5: Generating ARCHITECTURE_INVARIANTS.md"

if ! "$HARNESS_DIR/lib/render-template.sh" "$HARNESS_DIR/templates/architecture-invariants.md.hbs" \
  "PROJECT_NAME=$PROJECT_NAME" \
  "STACKS=$STACKS_COMMA" \
  "HAS_NEXTJS=$HAS_NEXTJS" \
  "HAS_NESTJS=$HAS_NESTJS" \
  "HAS_FASTAPI=$HAS_FASTAPI" \
  "HAS_DJANGO=$HAS_DJANGO" \
  "HAS_PRISMA=$HAS_PRISMA" \
  "HAS_ALEMBIC=$HAS_ALEMBIC" \
  "HAS_DOCKER=$HAS_DOCKER" \
  > "$TARGET/ARCHITECTURE_INVARIANTS.md"; then
  error "Failed to generate ARCHITECTURE_INVARIANTS.md."
  exit 1
fi

success "Generated ARCHITECTURE_INVARIANTS.md"

# ─── Step 6: Copy reference docs ──────────────────────────────────
header "Step 6: Setting up reference documents"

mkdir -p "$TARGET/docs"

if [ ! -f "$TARGET/docs/code-convention.yaml" ]; then
  cp "$HARNESS_DIR/templates/code-convention.yaml" "$TARGET/docs/code-convention.yaml"
  success "Created docs/code-convention.yaml"
else
  warn "docs/code-convention.yaml already exists, skipping"
fi

if [ ! -f "$TARGET/docs/adr.yaml" ]; then
  cp "$HARNESS_DIR/templates/adr.yaml" "$TARGET/docs/adr.yaml"
  success "Created docs/adr.yaml"
else
  warn "docs/adr.yaml already exists, skipping"
fi

# ─── Step 7: Install Claude Code settings ──────────────────────────
header "Step 7: Configuring Claude Code boundaries"

mkdir -p "$TARGET/.claude"

if [ ! -f "$TARGET/.claude/settings.local.json" ]; then
  cp "$HARNESS_DIR/boundaries/presets/$PRESET.json" "$TARGET/.claude/settings.local.json"
  success "Installed settings.local.json (preset: $PRESET)"
else
  warn ".claude/settings.local.json already exists"
  if [ "$AUTO_YES" -eq 1 ]; then
    info "Kept existing settings (--yes mode)"
  else
    read -p "  Overwrite with $PRESET preset? [y/N] " -n 1 -r OVERWRITE
    echo ""
    if [[ "$OVERWRITE" =~ ^[Yy]$ ]]; then
      cp "$HARNESS_DIR/boundaries/presets/$PRESET.json" "$TARGET/.claude/settings.local.json"
      success "Overwritten with $PRESET preset"
    else
      info "Kept existing settings"
    fi
  fi
fi

# ─── Step 8: Install Ouroboros commands & agents ─────────────────
header "Step 8: Installing Ouroboros commands & agents"

COMMANDS_TARGET="$TARGET/.claude/commands"
mkdir -p "$COMMANDS_TARGET"
cmd_count=0
for cmd in "$HARNESS_DIR/commands/"*.md; do
  [ -f "$cmd" ] || continue
  cp "$cmd" "$COMMANDS_TARGET/"
  cmd_count=$((cmd_count + 1))
done
if [ "$cmd_count" -eq 0 ]; then
  warn "No command files found in $HARNESS_DIR/commands/"
else
  success "Installed $cmd_count slash commands"
fi

AGENTS_TARGET="$TARGET/.claude/agents"
mkdir -p "$AGENTS_TARGET"
agent_count=0
for agent in "$HARNESS_DIR/agents/"*.md; do
  [ -f "$agent" ] || continue
  cp "$agent" "$AGENTS_TARGET/"
  agent_count=$((agent_count + 1))
done
if [ "$agent_count" -eq 0 ]; then
  warn "No agent files found in $HARNESS_DIR/agents/"
else
  success "Installed $agent_count agent personas"
fi

# Copy topology.yaml if exists
if [ -f "$HARNESS_DIR/agents/topology.yaml" ]; then
  cp "$HARNESS_DIR/agents/topology.yaml" "$AGENTS_TARGET/"
  success "Installed agent orchestration topology"
fi

# Install Ouroboros templates
mkdir -p "$TARGET/.ouroboros/seeds" "$TARGET/.ouroboros/interviews" "$TARGET/.ouroboros/evaluations"
if [ -d "$HARNESS_DIR/ouroboros/templates" ]; then
  mkdir -p "$TARGET/.ouroboros/templates"
  cp "$HARNESS_DIR/ouroboros/templates/"* "$TARGET/.ouroboros/templates/" 2>/dev/null || true
fi
if [ -d "$HARNESS_DIR/ouroboros/scoring" ]; then
  mkdir -p "$TARGET/.ouroboros/scoring"
  cp "$HARNESS_DIR/ouroboros/scoring/"* "$TARGET/.ouroboros/scoring/" 2>/dev/null || true
fi
success "Ouroboros structure created"

# ─── Step 9: Copy gate rules ──────────────────────────────────────
header "Step 9: Installing CI/CD gates & spec gate"

HARNESS_TARGET="$TARGET/.harness"
mkdir -p "$HARNESS_TARGET/gates/rules"
mkdir -p "$HARNESS_TARGET/hooks"

# Copy gate scripts
gate_files=(
  "gates/check-boundaries.sh"
  "gates/check-layers.sh"
  "gates/check-secrets.sh"
  "gates/check-security.sh"
  "gates/check-structure.sh"
  "gates/check-spec.sh"
  "gates/check-complexity.sh"
  "gates/check-deps.sh"
  "gates/check-mutation.sh"
  "gates/check-performance.sh"
  "gates/check-ai-antipatterns.sh"
)
for gf in "${gate_files[@]}"; do
  if [ -f "$HARNESS_DIR/$gf" ]; then
    cp "$HARNESS_DIR/$gf" "$HARNESS_TARGET/gates/"
  else
    warn "Missing gate file: $gf"
  fi
done

for rf in "gates/rules/boundaries.yaml" "gates/rules/structure.yaml"; do
  if [ -f "$HARNESS_DIR/$rf" ]; then
    cp "$HARNESS_DIR/$rf" "$HARNESS_TARGET/gates/rules/"
  else
    warn "Missing rule file: $rf"
  fi
done

# Copy gate documentation (default vs opt-in tiers)
if [ -f "$HARNESS_DIR/gates/GATES.md" ]; then
  cp "$HARNESS_DIR/gates/GATES.md" "$HARNESS_TARGET/gates/"
fi
chmod +x "$HARNESS_TARGET/gates/"*.sh 2>/dev/null || true

# Copy hooks
for hf in "boundaries/hooks/post-edit-lint.sh" "boundaries/hooks/pre-commit-gate.sh"; do
  if [ -f "$HARNESS_DIR/$hf" ]; then
    cp "$HARNESS_DIR/$hf" "$HARNESS_TARGET/hooks/"
  else
    warn "Missing hook file: $hf"
  fi
done
chmod +x "$HARNESS_TARGET/hooks/"*.sh 2>/dev/null || true

# Copy feedback tools
if [ -f "$HARNESS_DIR/feedback/detect-violations.sh" ]; then
  cp "$HARNESS_DIR/feedback/detect-violations.sh" "$HARNESS_TARGET/"
  chmod +x "$HARNESS_TARGET/detect-violations.sh"
else
  warn "Missing feedback tool: detect-violations.sh"
fi

success "Installed gates and hooks to .harness/"

# ─── Step 10: Install pre-commit hook ─────────────────────────────
header "Step 10: Installing pre-commit hook"

if [ -d "$TARGET/.git" ]; then
  "$HARNESS_DIR/gates/install-hooks.sh" "$TARGET"
  success "Pre-commit hook installed"
else
  warn "Not a git repository. Pre-commit hook skipped."
  info "Run 'git init' then '$HARNESS_DIR/gates/install-hooks.sh $TARGET' to install later."
fi

# ─── Step 11: Install GitHub Actions workflow (optional) ─────────
header "Step 11: GitHub Actions CI"

if [ -f "$HARNESS_DIR/templates/github-actions-gates.yaml" ]; then
  if [ "$AUTO_YES" -eq 1 ]; then
    INSTALL_GHA="y"
  else
    read -p "Install GitHub Actions workflow for gates? [y/N] " -n 1 -r INSTALL_GHA
    echo ""
  fi
  if [[ "$INSTALL_GHA" =~ ^[Yy]$ ]]; then
    mkdir -p "$TARGET/.github/workflows"
    cp "$HARNESS_DIR/templates/github-actions-gates.yaml" "$TARGET/.github/workflows/harness-gates.yaml"
    success "Installed .github/workflows/harness-gates.yaml"
  else
    info "Skipped GitHub Actions setup"
  fi
else
  warn "GitHub Actions template not found, skipping"
fi

# ─── Step 12: Update .gitignore ────────────────────────────────────
header "Step 12: Updating .gitignore"

GITIGNORE="$TARGET/.gitignore"
ENTRIES=(".env" ".env.local" ".env.*.local" ".review-artifacts/" ".ouroboros/session.db")

touch "$GITIGNORE"
for entry in "${ENTRIES[@]}"; do
  if ! grep -qxF "$entry" "$GITIGNORE"; then
    echo "$entry" >> "$GITIGNORE"
    step "Added: $entry"
  fi
done
success ".gitignore updated"

# ─── Done ──────────────────────────────────────────────────────────
header "Installation Complete"
echo ""
echo "  Files created:"
echo "    CLAUDE.md                       - AI agent context file"
echo "    ARCHITECTURE_INVARIANTS.md      - Architecture rules"
echo "    docs/code-convention.yaml       - Coding conventions"
echo "    docs/adr.yaml                   - Architecture Decision Records"
echo "    .claude/settings.local.json     - Claude Code permissions ($PRESET)"
echo "    .claude/commands/               - Ouroboros slash commands"
echo "    .claude/agents/                 - 9 agent personas"
echo "    .harness/                       - Gates, hooks, and tools"
echo "    .ouroboros/                     - Seed specs, interviews, evaluations"
echo ""
echo "  Ouroboros Workflow:"
echo "    /interview 'topic'  → Socratic interview (clarify requirements)"
echo "    /seed               → Generate immutable spec"
echo "    /run                → Execute Double Diamond"
echo "    /evaluate           → 3-stage verification"
echo "    /evolve             → Evolution loop"
echo ""
echo "  Next steps:"
echo "    1. Edit CLAUDE.md to add project-specific rules"
echo "    2. Edit ARCHITECTURE_INVARIANTS.md to define your invariants"
echo "    3. Try /interview 'feature description' to start spec-first workflow"
echo "    4. Edit .harness/gates/rules/boundaries.yaml for import rules"
echo "    5. Run '.harness/detect-violations.sh' to check current violations"
echo ""
echo "  Want Python-powered features (real scoring, drift monitoring, persistence)?"
echo "    Run: $HARNESS_DIR/pro/install.sh $TARGET"
echo ""
success "Harness installed successfully!"
