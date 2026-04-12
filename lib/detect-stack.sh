#!/usr/bin/env bash
# Detect project tech stack by scanning files in the target directory.
# Usage: ./detect-stack.sh [project-path]
# Output: JSON object with detected stacks

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/colors.sh"

TARGET="${1:-.}"
TARGET="$(cd "$TARGET" && pwd)"

STACKS=()
PKG_MANAGER="unknown"
FRONTEND_DIR=""
BACKEND_DIR=""

# --- Helper ---
has_file()  { [ -f "$TARGET/$1" ] || [ -f "$TARGET/$2" ] 2>/dev/null; }
has_dir()   { [ -d "$TARGET/$1" ]; }
has_glob()  { compgen -G "$TARGET/$1" > /dev/null 2>&1; }
contains()  { grep -q "$2" "$TARGET/$1" 2>/dev/null; }

# --- Package Manager ---
if [ -f "$TARGET/pnpm-lock.yaml" ]; then
  PKG_MANAGER="pnpm"
elif [ -f "$TARGET/yarn.lock" ]; then
  PKG_MANAGER="yarn"
elif [ -f "$TARGET/bun.lockb" ] || [ -f "$TARGET/bun.lock" ]; then
  PKG_MANAGER="bun"
elif [ -f "$TARGET/package-lock.json" ]; then
  PKG_MANAGER="npm"
elif [ -f "$TARGET/uv.lock" ]; then
  PKG_MANAGER="uv"
elif [ -f "$TARGET/poetry.lock" ]; then
  PKG_MANAGER="poetry"
elif [ -f "$TARGET/Pipfile.lock" ]; then
  PKG_MANAGER="pipenv"
elif [ -f "$TARGET/requirements.txt" ] || [ -f "$TARGET/pyproject.toml" ]; then
  PKG_MANAGER="pip"
elif [ -f "$TARGET/go.mod" ]; then
  PKG_MANAGER="go"
elif [ -f "$TARGET/Cargo.lock" ]; then
  PKG_MANAGER="cargo"
elif [ -f "$TARGET/pom.xml" ] || [ -f "$TARGET/build.gradle" ] || [ -f "$TARGET/build.gradle.kts" ]; then
  PKG_MANAGER="maven/gradle"
fi

# --- Node.js / TypeScript ---
if [ -f "$TARGET/package.json" ]; then
  STACKS+=("nodejs")

  if contains "package.json" '"typescript"'; then
    STACKS+=("typescript")
  fi
  if [ -f "$TARGET/tsconfig.json" ]; then
    STACKS+=("typescript")
  fi
fi

# --- Next.js ---
detect_nextjs() {
  local dir="$1"
  [ ! -d "$dir" ] && return 1
  if compgen -G "$dir/next.config.*" > /dev/null 2>&1; then
    STACKS+=("nextjs")
    FRONTEND_DIR="$dir"
    return 0
  fi
  if [ -f "$dir/package.json" ] && grep -q '"next"' "$dir/package.json" 2>/dev/null; then
    STACKS+=("nextjs")
    FRONTEND_DIR="$dir"
    return 0
  fi
  return 1
}

# Check root, then common subdirectories
detect_nextjs "$TARGET" 2>/dev/null || \
detect_nextjs "$TARGET/frontend" 2>/dev/null || \
detect_nextjs "$TARGET/dashboard" 2>/dev/null || \
detect_nextjs "$TARGET/web" 2>/dev/null || \
detect_nextjs "$TARGET/client" 2>/dev/null || \
detect_nextjs "$TARGET/apps/web" 2>/dev/null || true

# --- NestJS ---
detect_nestjs() {
  local dir="$1"
  [ ! -d "$dir" ] && return 1
  if [ -f "$dir/nest-cli.json" ]; then
    STACKS+=("nestjs")
    BACKEND_DIR="$dir"
    return 0
  fi
  if [ -f "$dir/package.json" ] && grep -q '"@nestjs/core"' "$dir/package.json" 2>/dev/null; then
    STACKS+=("nestjs")
    BACKEND_DIR="$dir"
    return 0
  fi
  return 1
}

detect_nestjs "$TARGET" 2>/dev/null || \
detect_nestjs "$TARGET/backend" 2>/dev/null || \
detect_nestjs "$TARGET/server" 2>/dev/null || \
detect_nestjs "$TARGET/api" 2>/dev/null || \
detect_nestjs "$TARGET/apps/api" 2>/dev/null || true

# --- Python frameworks ---
detect_python() {
  local found=false

  # FastAPI
  if grep -rq "from fastapi" "$TARGET/src" "$TARGET/app" "$TARGET/main.py" "$TARGET/backend" 2>/dev/null || \
     grep -q "fastapi" "$TARGET/requirements.txt" "$TARGET/pyproject.toml" 2>/dev/null; then
    STACKS+=("fastapi")
    BACKEND_DIR="${BACKEND_DIR:-$TARGET}"
    found=true
  fi

  # Django
  if [ -f "$TARGET/manage.py" ] || \
     grep -q "django" "$TARGET/requirements.txt" "$TARGET/pyproject.toml" 2>/dev/null || \
     grep -rq "from django" "$TARGET/backend" "$TARGET/src" 2>/dev/null; then
    STACKS+=("django")
    BACKEND_DIR="${BACKEND_DIR:-$TARGET}"
    found=true
  fi

  # Flask
  if grep -q "flask" "$TARGET/requirements.txt" "$TARGET/pyproject.toml" 2>/dev/null || \
     grep -rq "from flask" "$TARGET/app.py" "$TARGET/src" 2>/dev/null; then
    STACKS+=("flask")
    BACKEND_DIR="${BACKEND_DIR:-$TARGET}"
    found=true
  fi

  # Generic Python
  if [ -f "$TARGET/requirements.txt" ] || [ -f "$TARGET/pyproject.toml" ] || [ -f "$TARGET/setup.py" ]; then
    STACKS+=("python")
    found=true
  fi

  $found
}
detect_python 2>/dev/null || true

# --- Monorepo ---
# Require workspace config, not just a packages/ directory (reduces false positives)
if [ -f "$TARGET/pnpm-workspace.yaml" ] || [ -f "$TARGET/lerna.json" ]; then
  STACKS+=("monorepo")
elif has_dir "packages" && [ -f "$TARGET/package.json" ] && grep -q '"workspaces"' "$TARGET/package.json" 2>/dev/null; then
  STACKS+=("monorepo")
fi
if [ -f "$TARGET/turbo.json" ]; then
  STACKS+=("turborepo")
fi

# --- ORM / DB ---
if has_dir "prisma" || has_glob "*/prisma/schema.prisma"; then
  STACKS+=("prisma")
fi
if has_dir "alembic" || [ -f "$TARGET/alembic.ini" ]; then
  STACKS+=("alembic")
fi
if grep -rq "drizzle" "$TARGET/package.json" "$TARGET/drizzle.config.*" 2>/dev/null; then
  STACKS+=("drizzle")
fi

# --- Infrastructure ---
if has_glob "docker-compose*.yml" || has_glob "docker-compose*.yaml"; then
  STACKS+=("docker")
fi
if has_dir ".github/workflows"; then
  STACKS+=("github-actions")
fi

# --- React (standalone, not Next.js) ---
if [ -f "$TARGET/package.json" ] && contains "package.json" '"react"' && ! printf '%s\n' "${STACKS[@]}" | grep -q "nextjs"; then
  STACKS+=("react")
fi

# --- Vue.js ---
if [ -f "$TARGET/package.json" ] && contains "package.json" '"vue"'; then
  STACKS+=("vue")
  if contains "package.json" '"nuxt"' || [ -f "$TARGET/nuxt.config.ts" ] || [ -f "$TARGET/nuxt.config.js" ]; then
    STACKS+=("nuxt")
  fi
  [ -z "$FRONTEND_DIR" ] && FRONTEND_DIR="$TARGET"
fi

# --- Svelte ---
if [ -f "$TARGET/package.json" ] && contains "package.json" '"svelte"'; then
  STACKS+=("svelte")
  if contains "package.json" '"@sveltejs/kit"' || [ -f "$TARGET/svelte.config.js" ] || [ -f "$TARGET/svelte.config.ts" ]; then
    STACKS+=("sveltekit")
  fi
  [ -z "$FRONTEND_DIR" ] && FRONTEND_DIR="$TARGET"
fi

# --- Remix ---
if [ -f "$TARGET/package.json" ] && (contains "package.json" '"@remix-run/react"' || contains "package.json" '"remix"'); then
  STACKS+=("remix")
  [ -z "$FRONTEND_DIR" ] && FRONTEND_DIR="$TARGET"
fi

# --- Astro ---
if [ -f "$TARGET/package.json" ] && contains "package.json" '"astro"'; then
  STACKS+=("astro")
  [ -z "$FRONTEND_DIR" ] && FRONTEND_DIR="$TARGET"
fi

# --- Express ---
if [ -f "$TARGET/package.json" ] && contains "package.json" '"express"' && ! printf '%s\n' "${STACKS[@]}" | grep -q "nestjs"; then
  STACKS+=("express")
  [ -z "$BACKEND_DIR" ] && BACKEND_DIR="$TARGET"
fi

# --- Fastify ---
if [ -f "$TARGET/package.json" ] && contains "package.json" '"fastify"'; then
  STACKS+=("fastify")
  [ -z "$BACKEND_DIR" ] && BACKEND_DIR="$TARGET"
fi

# --- Hono ---
if [ -f "$TARGET/package.json" ] && contains "package.json" '"hono"'; then
  STACKS+=("hono")
  [ -z "$BACKEND_DIR" ] && BACKEND_DIR="$TARGET"
fi

# --- Go ---
if [ -f "$TARGET/go.mod" ]; then
  STACKS+=("go")
  [ -z "$BACKEND_DIR" ] && BACKEND_DIR="$TARGET"
  if grep -q "gin-gonic" "$TARGET/go.mod" 2>/dev/null; then
    STACKS+=("gin")
  fi
  if grep -q "go-chi" "$TARGET/go.mod" 2>/dev/null || grep -q "chi/v5" "$TARGET/go.mod" 2>/dev/null; then
    STACKS+=("chi")
  fi
fi

# --- Rust ---
if [ -f "$TARGET/Cargo.toml" ]; then
  STACKS+=("rust")
  [ -z "$BACKEND_DIR" ] && BACKEND_DIR="$TARGET"
  if grep -q "actix-web" "$TARGET/Cargo.toml" 2>/dev/null; then
    STACKS+=("actix")
  fi
  if grep -q "axum" "$TARGET/Cargo.toml" 2>/dev/null; then
    STACKS+=("axum")
  fi
fi

# --- Java / Kotlin ---
if [ -f "$TARGET/pom.xml" ] || [ -f "$TARGET/build.gradle" ] || [ -f "$TARGET/build.gradle.kts" ]; then
  if has_glob "**/*.kt" || [ -f "$TARGET/build.gradle.kts" ]; then
    STACKS+=("kotlin")
  else
    STACKS+=("java")
  fi
  if grep -rq "spring" "$TARGET/pom.xml" "$TARGET/build.gradle" "$TARGET/build.gradle.kts" 2>/dev/null; then
    STACKS+=("spring")
  fi
  [ -z "$BACKEND_DIR" ] && BACKEND_DIR="$TARGET"
fi

# --- Deduplicate ---
UNIQUE_STACKS=($(printf '%s\n' "${STACKS[@]}" | sort -u))

# --- Output JSON ---
STACKS_JSON=$(printf '"%s",' "${UNIQUE_STACKS[@]}" | sed 's/,$//')
FRONTEND_DIR_REL=""
BACKEND_DIR_REL=""
if [ -n "$FRONTEND_DIR" ]; then
  FRONTEND_DIR_REL="${FRONTEND_DIR#$TARGET/}"
  [ "$FRONTEND_DIR_REL" = "$TARGET" ] && FRONTEND_DIR_REL="."
fi
if [ -n "$BACKEND_DIR" ]; then
  BACKEND_DIR_REL="${BACKEND_DIR#$TARGET/}"
  [ "$BACKEND_DIR_REL" = "$TARGET" ] && BACKEND_DIR_REL="."
fi

cat <<EOF
{
  "stacks": [${STACKS_JSON}],
  "package_manager": "${PKG_MANAGER}",
  "frontend_dir": "${FRONTEND_DIR_REL:-.}",
  "backend_dir": "${BACKEND_DIR_REL:-.}"
}
EOF
