#!/usr/bin/env bash
# Methodology dispatcher — manages plugin activation/deactivation.
#
# Usage (called by /methodology slash command or scripts):
#   source lib/methodology.sh
#   methodology_list
#   methodology_use <name>
#   methodology_deactivate <name>
#   methodology_current
#   methodology_info <name>
#   methodology_compose <name1> <name2> ...
#
# Dependencies: yq (preferred) or python3 (fallback)
# Reads:
#   .harness/methodology/_registry.yaml
#   .harness/methodology/_state.yaml
#   .harness/methodologies/<name>/manifest.yaml
# Writes:
#   .harness/methodology/_state.yaml
#   .claude/commands/<methodology-cmd>.md  (on activate)
#   .harness/methodologies/<name>/state/   (on activate)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/colors.sh" ]; then
  # shellcheck source=colors.sh
  source "$SCRIPT_DIR/colors.sh"
else
  info() { echo "[INFO] $*"; }
  success() { echo "[OK] $*"; }
  warn() { echo "[WARN] $*"; }
  error() { echo "[ERROR] $*"; }
  step() { echo "  -> $*"; }
fi

# ─────────────────────────────────────────────────────────
# Path resolution
# ─────────────────────────────────────────────────────────

# Project root — where .harness lives. Auto-detected via git or PWD.
_methodology_project_root() {
  if git rev-parse --show-toplevel >/dev/null 2>&1; then
    git rev-parse --show-toplevel
  else
    pwd
  fi
}

_methodology_paths() {
  local root
  root="$(_methodology_project_root)"
  echo "$root"
}

# ─────────────────────────────────────────────────────────
# YAML reader (yq preferred, python3 fallback)
# ─────────────────────────────────────────────────────────

_yaml_get() {
  local file="$1"
  local path="$2"   # e.g., '.name' or '.commands[].name'
  if command -v yq >/dev/null 2>&1; then
    yq -r "$path // \"\"" "$file" 2>/dev/null || echo ""
  elif command -v python3 >/dev/null 2>&1; then
    python3 - "$file" "$path" <<'PY'
import sys, yaml, re
file, path = sys.argv[1], sys.argv[2]
with open(file) as f:
    data = yaml.safe_load(f) or {}
# Minimal jq-ish path: .a.b or .a[].b (no filters)
parts = re.findall(r'\.([a-zA-Z_][a-zA-Z_0-9]*)|\[\]', path)
def walk(node, parts):
    if not parts:
        if isinstance(node, list):
            for x in node: print(x if x is not None else "")
        else:
            print("" if node is None else node)
        return
    head, rest = parts[0], parts[1:]
    if head == "":
        if isinstance(node, list):
            for x in node: walk(x, rest)
        return
    if isinstance(node, dict):
        walk(node.get(head), rest)
walk(data, parts)
PY
  else
    error "Need 'yq' or 'python3+pyyaml' to parse YAML"
    return 1
  fi
}

_yaml_set_active() {
  # Replace the 'active' list in _state.yaml with given names (in order)
  local state_file="$1"; shift
  local names=("$@")
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$state_file" "${names[@]}" <<'PY'
import sys, yaml, datetime
state_file = sys.argv[1]
names = sys.argv[2:]
with open(state_file) as f:
    data = yaml.safe_load(f) or {}
now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
existing = {a.get("name"): a for a in data.get("active") or []}
data["active"] = [
    {
        "name": n,
        "activated_at": (existing.get(n, {}).get("activated_at") or now),
        "activated_by": (existing.get(n, {}).get("activated_by") or "user"),
    }
    for n in names
]
data["last_modified"] = now
hist = data.get("history") or []
hist.insert(0, {"action": "set_active", "names": names, "timestamp": now, "actor": "user"})
data["history"] = hist[:50]
with open(state_file, "w") as f:
    yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
PY
  else
    error "python3 required to update state file"
    return 1
  fi
}

# ─────────────────────────────────────────────────────────
# Registry & state lookup
# ─────────────────────────────────────────────────────────

_methodology_registry_file() {
  local root; root="$(_methodology_project_root)"
  if [ -f "$root/.harness/methodology/_registry.yaml" ]; then
    echo "$root/.harness/methodology/_registry.yaml"
  elif [ -f "$root/methodology/_registry.yaml" ]; then
    echo "$root/methodology/_registry.yaml"
  else
    return 1
  fi
}

_methodology_state_file() {
  local root; root="$(_methodology_project_root)"
  echo "$root/.harness/methodology/_state.yaml"
}

_methodology_dir() {
  # Where methodologies/ plugin home lives
  local root; root="$(_methodology_project_root)"
  if [ -d "$root/.harness/methodologies" ]; then
    echo "$root/.harness/methodologies"
  elif [ -d "$root/methodologies" ]; then
    echo "$root/methodologies"
  else
    return 1
  fi
}

_methodology_manifest() {
  local name="$1"
  local dir; dir="$(_methodology_dir)" || return 1
  local manifest="$dir/$name/manifest.yaml"
  [ -f "$manifest" ] || return 1
  echo "$manifest"
}

# ─────────────────────────────────────────────────────────
# Public commands
# ─────────────────────────────────────────────────────────

methodology_list() {
  local registry; registry="$(_methodology_registry_file)" || {
    error "Registry not found. Run init.sh or check .harness/methodology/"
    return 1
  }
  local state; state="$(_methodology_state_file)"
  local active_names=""
  if [ -f "$state" ]; then
    active_names="$(_yaml_get "$state" '.active[].name' | tr '\n' ' ')"
  fi

  printf "\n%s\n" "Available methodologies:"
  printf "%s\n" "─────────────────────────────────────────────────────"

  local names; names="$(_yaml_get "$registry" '.methodologies[].name')"
  while IFS= read -r name; do
    [ -z "$name" ] && continue
    local manifest; manifest="$(_methodology_manifest "$name" 2>/dev/null || echo "")"
    local display="" desc="" icon=""
    if [ -n "$manifest" ] && [ -f "$manifest" ]; then
      display="$(_yaml_get "$manifest" '.display_name')"
      desc="$(_yaml_get "$manifest" '.description')"
      icon="$(_yaml_get "$manifest" '.icon')"
    fi
    local marker="○"
    if echo " $active_names " | grep -q " $name "; then
      marker="✓"
    fi
    printf "  %s %s %-20s %s\n" "$marker" "${icon:-  }" "$name" "${desc:-$display}"
  done <<< "$names"
  printf "\n"
  printf "  ✓ active   ○ available   Use: /methodology use <name>\n\n"
}

methodology_current() {
  local state; state="$(_methodology_state_file)"
  if [ ! -f "$state" ]; then
    warn "No state file. Run /methodology use ouroboros to initialize."
    return 1
  fi
  printf "\nCurrently active:\n"
  printf "─────────────────────────────────────────────────────\n"
  local names; names="$(_yaml_get "$state" '.active[].name')"
  while IFS= read -r name; do
    [ -z "$name" ] && continue
    local manifest; manifest="$(_methodology_manifest "$name" 2>/dev/null || echo "")"
    local desc=""
    [ -f "$manifest" ] && desc="$(_yaml_get "$manifest" '.description')"
    printf "  ✓ %-20s %s\n" "$name" "$desc"
  done <<< "$names"
  printf "\n"
}

methodology_info() {
  local name="${1:-}"
  if [ -z "$name" ]; then error "Usage: /methodology info <name>"; return 1; fi
  local manifest; manifest="$(_methodology_manifest "$name")" || {
    error "Methodology '$name' not found in $(_methodology_dir)"
    return 1
  }
  printf "\n%s\n" "Methodology: $name"
  printf "─────────────────────────────────────────────────────\n"
  printf "  Display name : %s\n" "$(_yaml_get "$manifest" '.display_name')"
  printf "  Version      : %s\n" "$(_yaml_get "$manifest" '.version')"
  printf "  Author       : %s\n" "$(_yaml_get "$manifest" '.author')"
  printf "  Description  : %s\n" "$(_yaml_get "$manifest" '.description')"
  printf "  Tags         : %s\n" "$(_yaml_get "$manifest" '.tags[]' | tr '\n' ' ')"
  printf "  Requires     : %s\n" "$(_yaml_get "$manifest" '.requires[]' | tr '\n' ' ')"
  printf "  Conflicts    : %s\n" "$(_yaml_get "$manifest" '.conflicts_with[]' | tr '\n' ' ')"
  printf "\n  Commands provided:\n"
  _yaml_get "$manifest" '.commands[].name' | while IFS= read -r c; do
    [ -z "$c" ] && continue
    printf "    • %s\n" "$c"
  done
  printf "\n  Gates added when active:\n"
  _yaml_get "$manifest" '.adds_gates[].file' | while IFS= read -r g; do
    [ -z "$g" ] && continue
    printf "    • %s\n" "$g"
  done
  printf "\n"
}

# Validate prerequisites — returns 0 if all pass, 1 if any fail
methodology_check_prereqs() {
  local name="$1"
  local manifest; manifest="$(_methodology_manifest "$name")" || return 1
  local proj_root; proj_root="$(_methodology_project_root)"

  # Use python3 to walk prerequisites array — bash struggles with nested yaml
  if ! command -v python3 >/dev/null 2>&1; then
    warn "python3 missing — skipping prereq validation"
    return 0
  fi

  python3 - "$manifest" "$proj_root" <<'PY'
import sys, yaml, os, glob
manifest_path, root = sys.argv[1], sys.argv[2]
with open(manifest_path) as f:
    m = yaml.safe_load(f) or {}
prereqs = m.get("prerequisites") or []
failures = []
for p in prereqs:
    t = p.get("type", "")
    msg = p.get("message", "")
    if t == "file_exists":
        path = p.get("path", "")
        if not path:
            continue
        # Support glob patterns
        target = os.path.join(root, path) if not os.path.isabs(path) else path
        matches = glob.glob(target)
        if not matches and not os.path.exists(target):
            failures.append(msg or f"file not found: {path}")
    elif t == "command_exists":
        name = p.get("name", "")
        if name:
            from shutil import which
            if not which(name):
                failures.append(msg or f"command not in PATH: {name}")
    elif t == "env_var":
        name = p.get("name", "")
        expected = p.get("value", "")
        actual = os.environ.get(name, "")
        if not actual or (expected and actual != expected):
            failures.append(msg or f"env var unset/mismatch: {name}")
    else:
        # Unknown types: warn but don't fail
        sys.stderr.write(f"[methodology] unknown prereq type '{t}' — skipped\n")
for f in failures:
    print(f)
sys.exit(1 if failures else 0)
PY
}

methodology_use() {
  local name="${1:-}"
  if [ -z "$name" ]; then error "Usage: /methodology use <name>"; return 1; fi
  local manifest; manifest="$(_methodology_manifest "$name")" || {
    error "Methodology '$name' not found"
    return 1
  }
  if ! methodology_check_prereqs "$name"; then
    error "Prerequisites not met for '$name'"
    return 1
  fi
  local state; state="$(_methodology_state_file)"
  mkdir -p "$(dirname "$state")"
  if [ ! -f "$state" ]; then
    local registry_dir; registry_dir="$(dirname "$(_methodology_registry_file)")"
    if [ -f "$registry_dir/_state.template.yaml" ]; then
      cp "$registry_dir/_state.template.yaml" "$state"
    else
      printf "schema_version: 1\nactive: []\nhistory: []\n" > "$state"
    fi
  fi
  _yaml_set_active "$state" "$name"
  success "Activated methodology: $name"
  step "Run /methodology current to see active state"
}

methodology_compose() {
  if [ "$#" -lt 2 ]; then error "Usage: /methodology compose <name1> <name2> [...]"; return 1; fi
  for n in "$@"; do
    _methodology_manifest "$n" >/dev/null || { error "Unknown methodology: $n"; return 1; }
    methodology_check_prereqs "$n" || { error "Prereqs failed: $n"; return 1; }
  done
  local state; state="$(_methodology_state_file)"
  mkdir -p "$(dirname "$state")"
  [ -f "$state" ] || printf "schema_version: 1\nactive: []\nhistory: []\n" > "$state"
  _yaml_set_active "$state" "$@"
  success "Composed methodologies: $*"
}

methodology_deactivate() {
  local name="${1:-}"
  if [ -z "$name" ]; then error "Usage: /methodology deactivate <name>"; return 1; fi
  local state; state="$(_methodology_state_file)"
  [ -f "$state" ] || { warn "No state file"; return 0; }
  local current; current="$(_yaml_get "$state" '.active[].name' | tr '\n' ' ')"
  local kept=()
  for n in $current; do
    [ "$n" = "$name" ] && continue
    kept+=("$n")
  done
  if [ "${#kept[@]}" -eq 0 ]; then
    warn "Cannot deactivate '$name' — at least one methodology must remain active"
    warn "Falling back to default (ouroboros)"
    kept=("ouroboros")
  fi
  _yaml_set_active "$state" "${kept[@]}"
  success "Deactivated: $name (active now: ${kept[*]})"
}

# Dispatch entry point
methodology() {
  local cmd="${1:-list}"; shift || true
  case "$cmd" in
    list)        methodology_list "$@" ;;
    current)     methodology_current "$@" ;;
    info)        methodology_info "$@" ;;
    use)         methodology_use "$@" ;;
    compose)     methodology_compose "$@" ;;
    deactivate)  methodology_deactivate "$@" ;;
    *)
      error "Unknown subcommand: $cmd"
      echo "Valid: list | current | info <name> | use <name> | compose <a> <b> ... | deactivate <name>"
      return 1
      ;;
  esac
}

# CLI entry — runs when script is executed directly (not sourced)
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  methodology "$@"
fi
