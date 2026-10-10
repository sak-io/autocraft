#!/usr/bin/env bash
# Install the autocraft agent team into a project directory.
# Usage: scripts/install.sh <target-dir> [--lang node|python|go|flutter] [--archetype a,b]
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-}"; shift || true
LANG_=""; ARCH=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) LANG_="${2:-}"; shift 2 ;;
    --archetype) ARCH="${2:-}"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
[[ -n "$TARGET" ]] || { echo "Usage: $0 <target-dir> [--lang node|python|go|flutter] [--archetype api-service,web-app,...]" >&2; exit 2; }
case "$LANG_" in ""|node|python|go|flutter) ;; *) echo "--lang must be node, python, go or flutter" >&2; exit 2 ;; esac
for a in ${ARCH//,/ }; do [[ -f "$SRC/archetypes/$a/archetype.md" ]] || { echo "Unknown archetype: $a (see archetypes/)" >&2; exit 2; }; done

mkdir -p "$TARGET"
TARGET="$(cd "$TARGET" && pwd)"

copy_new() { # copy without clobbering existing user files
  local from="$1" to="$2"
  if [[ -e "$to" ]]; then echo "  skip (exists): ${to#"$TARGET"/}"; else mkdir -p "$(dirname "$to")"; cp "$from" "$to"; echo "  add: ${to#"$TARGET"/}"; fi
}

echo "Installing agents and skills..."
mkdir -p "$TARGET/.claude/agents" "$TARGET/.claude/skills"
cp -R "$SRC/.claude/agents/." "$TARGET/.claude/agents/"
cp -R "$SRC/.claude/skills/." "$TARGET/.claude/skills/"

echo "Installing project files..."
copy_new "$SRC/templates/CLAUDE.project.md" "$TARGET/CLAUDE.md"
copy_new "$SRC/templates/autocraft-config.yml" "$TARGET/.autocraft/config.yml"
copy_new "$SRC/docs/protocol.md" "$TARGET/docs/protocol.md"
copy_new "$SRC/docs/glossary.md" "$TARGET/docs/glossary.md"

# Archetype profiles (all installed; config selects which are active)
mkdir -p "$TARGET/.autocraft/archetypes"
for f in "$SRC"/archetypes/*/archetype.md; do cp "$f" "$TARGET/.autocraft/archetypes/$(basename "$(dirname "$f")").md"; done

# Templates and helper scripts the agents refer to
mkdir -p "$TARGET/.autocraft/templates" "$TARGET/.autocraft/scripts"
cp -R "$SRC/templates/." "$TARGET/.autocraft/templates/"
cp "$SRC/scripts/onboard-repo.sh" "$TARGET/.autocraft/scripts/"

# Docs scaffolding
for d in docs/specs docs/architecture/reviews docs/adr docs/security; do
  mkdir -p "$TARGET/$d"; [[ -e "$TARGET/$d/.gitkeep" ]] || : > "$TARGET/$d/.gitkeep"
done
copy_new "$SRC/templates/architecture/status.md" "$TARGET/docs/architecture/status.md"

echo "Installing GitHub config..."
G="$SRC/templates/github"
copy_new "$G/pull_request_template.md" "$TARGET/.github/pull_request_template.md"
copy_new "$G/CODEOWNERS" "$TARGET/.github/CODEOWNERS"
copy_new "$G/SECURITY.md" "$TARGET/.github/SECURITY.md"
copy_new "$G/dependabot.yml" "$TARGET/.github/dependabot.yml"
copy_new "$G/ISSUE_TEMPLATE/task.md" "$TARGET/.github/ISSUE_TEMPLATE/task.md"
copy_new "$G/ISSUE_TEMPLATE/bug.md" "$TARGET/.github/ISSUE_TEMPLATE/bug.md"
copy_new "$G/workflows/security-scheduled.yml" "$TARGET/.github/workflows/security-scheduled.yml"

if [[ -n "$LANG_" ]]; then
  copy_new "$G/workflows/ci-$LANG_.yml" "$TARGET/.github/workflows/ci.yml"
  case "$LANG_" in node) CQ=javascript-typescript; ECO=npm ;; python) CQ=python; ECO=pip ;; go) CQ=go; ECO=gomod ;; flutter) CQ=""; ECO=pub ;; esac
  if [[ -n "$CQ" && ! -e "$TARGET/.github/workflows/codeql.yml" ]]; then
    sed "s/__CODEQL_LANGUAGE__/$CQ/" "$G/workflows/codeql.yml" > "$TARGET/.github/workflows/codeql.yml"; echo "  add: .github/workflows/codeql.yml"
  fi
  # enable the matching dependabot ecosystem in the copied file
  sed -i -E "/package-ecosystem: $ECO\$/,+2 s/^  # /  /" "$TARGET/.github/dependabot.yml" 2>/dev/null || true
  sed -i "s/^language: \"\"/language: \"$LANG_\"/" "$TARGET/.autocraft/config.yml"
else
  echo "  (no --lang given: CI/CodeQL workflows not installed; the repo-onboarder will add them)"
fi

if [[ -n "$ARCH" ]]; then
  sed -i "s/^archetypes: \[\]/archetypes: [${ARCH//,/, }]/" "$TARGET/.autocraft/config.yml"
  echo "  archetypes: $ARCH"
fi

cat <<MSG

Done. Next:
  cd "$TARGET"
  claude            # start Claude Code in this folder
  /start            # guided kickoff
MSG
