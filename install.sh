#!/usr/bin/env bash
# Install Claude Code skills from this repo into a user-global or project-local location.
#
# Usage:
#   ./install.sh --target {user|project} [--mode {symlink|copy}] [--project-dir DIR]
#                [--only tf-test,tf-refactor,tf-cost] [--dry-run] [--force]
#
# Examples:
#   ./install.sh --target user --mode symlink
#   ./install.sh --target project --mode copy --project-dir ~/Projects/my-tf-repo
#   ./install.sh --target user --mode copy --only tf-test,tf-cost

set -euo pipefail

ALL_SKILLS=("tf-test" "tf-refactor" "tf-cost" "tf-analyze")

TARGET=""
MODE="symlink"
PROJECT_DIR=""
ONLY=""
DRY_RUN=0
FORCE=0

usage() {
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)      TARGET="$2"; shift 2 ;;
    --mode)        MODE="$2"; shift 2 ;;
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    --only)        ONLY="$2"; shift 2 ;;
    --dry-run)     DRY_RUN=1; shift ;;
    --force)       FORCE=1; shift ;;
    -h|--help)     usage 0 ;;
    *) echo "Unknown argument: $1"; usage 1 ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "ERROR: --target is required (user | project)" >&2
  usage 1
fi

case "$TARGET" in
  user)
    DEST_ROOT="${HOME}/.claude/skills"
    ;;
  project)
    if [[ -z "$PROJECT_DIR" ]]; then
      echo "ERROR: --project-dir is required when --target project" >&2
      usage 1
    fi
    if [[ ! -d "$PROJECT_DIR" ]]; then
      echo "ERROR: project directory does not exist: $PROJECT_DIR" >&2
      exit 1
    fi
    DEST_ROOT="${PROJECT_DIR%/}/.claude/skills"
    ;;
  *)
    echo "ERROR: --target must be user or project (got: $TARGET)" >&2
    usage 1
    ;;
esac

case "$MODE" in
  symlink|copy) ;;
  *) echo "ERROR: --mode must be symlink or copy (got: $MODE)" >&2; usage 1 ;;
esac

# Resolve repo root so the script is runnable from anywhere
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SRC="${REPO_ROOT}/skills"

# Build the skill list
if [[ -n "$ONLY" ]]; then
  IFS=',' read -r -a SKILLS <<< "$ONLY"
else
  SKILLS=("${ALL_SKILLS[@]}")
fi

# Validate requested skills exist
for s in "${SKILLS[@]}"; do
  if [[ ! -f "${SKILL_SRC}/${s}/SKILL.md" ]]; then
    echo "ERROR: unknown skill '${s}' — no SKILL.md at ${SKILL_SRC}/${s}/" >&2
    exit 1
  fi
done

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run] %s\n' "$*"
  else
    "$@"
  fi
}

echo "Installing skills: ${SKILLS[*]}"
echo "  From:   ${SKILL_SRC}"
echo "  To:     ${DEST_ROOT}"
echo "  Mode:   ${MODE}"
[[ "$DRY_RUN" -eq 1 ]] && echo "  Dry-run: yes"
echo

run mkdir -p "$DEST_ROOT"

for s in "${SKILLS[@]}"; do
  SRC="${SKILL_SRC}/${s}"
  DEST="${DEST_ROOT}/${s}"

  if [[ -e "$DEST" || -L "$DEST" ]]; then
    if [[ "$FORCE" -eq 1 ]]; then
      echo "  [${s}] removing existing ${DEST}"
      run rm -rf "$DEST"
    else
      echo "  [${s}] SKIP — ${DEST} already exists (use --force to overwrite)"
      continue
    fi
  fi

  if [[ "$MODE" == "symlink" ]]; then
    echo "  [${s}] symlink ${SRC} → ${DEST}"
    run ln -s "$SRC" "$DEST"
  else
    echo "  [${s}] copy    ${SRC} → ${DEST}"
    run cp -R "$SRC" "$DEST"
  fi
done

echo
echo "Done. Verify in Claude Code with:  /  (expect to see ${SKILLS[*]})"
