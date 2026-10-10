#!/usr/bin/env bash
# Create + harden a GitHub repository for an autocraft project.
#
# Usage: onboard-repo.sh <owner/name> --lang node|python|go|flutter [--public] [--dir PATH] [--dry-run]
#
# Works in two situations:
#   * run from a project folder that already has autocraft installed (.autocraft/config.yml):
#     that folder becomes the repository.
#   * run from the autocraft clone: a new folder ./<name> is created and installed first.
# Requires: git, gh (authenticated), jq.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -d "$HERE/.claude/agents" ]]; then FRAMEWORK="$HERE"; TPL="$HERE/templates"   # autocraft clone
else FRAMEWORK=""; TPL="$HERE/templates"; fi                                        # installed copy (.autocraft/)

REPO="${1:-}"; shift || true
LANG_=""; VIS="private"; DRY=0; DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) LANG_="${2:-}"; shift 2 ;;
    --public) VIS="public"; shift ;;
    --dir) DIR="${2:-}"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
[[ "$REPO" == */* ]] || { echo "Usage: $0 <owner/name> --lang node|python|go|flutter [--public] [--dir PATH] [--dry-run]" >&2; exit 2; }
case "$LANG_" in node|python|go|flutter) ;; *) echo "--lang is required: node | python | go | flutter" >&2; exit 2 ;; esac
NAME="${REPO#*/}"
if [[ -z "$DIR" ]]; then if [[ -f .autocraft/config.yml ]]; then DIR="$PWD"; else DIR="$PWD/$NAME"; fi; fi

WARN=0
step() { printf '\n==> %s\n' "$*"; }
run()  { if ((DRY)); then printf '+ %s\n' "$*"; else "$@"; fi; }
try()  { # a control that may be unavailable on this GitHub plan: warn, don't abort
  if ((DRY)); then printf '+ %s\n' "$*"; return 0; fi
  if ! "$@" >/dev/null 2>&1; then printf '  WARN: could not apply: %s\n' "$*" >&2; WARN=$((WARN+1)); fi
}

step "Preflight"
command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
if ((DRY)); then echo "(dry run: nothing will be changed)"; else
  command -v gh >/dev/null || { echo "GitHub CLI 'gh' is required: https://cli.github.com" >&2; exit 1; }
  command -v jq >/dev/null || { echo "'jq' is required" >&2; exit 1; }
  gh auth status >/dev/null 2>&1 || { echo "Run 'gh auth login' first." >&2; exit 1; }
fi
echo "  project folder: $DIR"

step "1. Prepare the project folder (agents, skills, CI, security config)"
if [[ ! -f "$DIR/.autocraft/config.yml" ]]; then
  [[ -n "$FRAMEWORK" ]] || { echo "No autocraft install found in $DIR. Run scripts/install.sh from the autocraft clone first." >&2; exit 1; }
  run bash "$FRAMEWORK/scripts/install.sh" "$DIR" --lang "$LANG_"
elif [[ ! -f "$DIR/.github/workflows/ci.yml" ]]; then
  echo "  adding CI + CodeQL for $LANG_"
  case "$LANG_" in node) CQ=javascript-typescript ;; python) CQ=python ;; go) CQ=go ;; flutter) CQ="" ;; esac
  if ! ((DRY)); then
    mkdir -p "$DIR/.github/workflows"
    cp "$TPL/github/workflows/ci-$LANG_.yml" "$DIR/.github/workflows/ci.yml"
    [[ -z "$CQ" ]] || sed "s/__CODEQL_LANGUAGE__/$CQ/" "$TPL/github/workflows/codeql.yml" > "$DIR/.github/workflows/codeql.yml"
  fi
else echo "  already prepared"; fi

step "2. Commit locally"
if ! ((DRY)); then
  [[ -d "$DIR/.git" ]] || git -C "$DIR" init -q -b main
  git -C "$DIR" add -A
  if git -C "$DIR" diff --cached --quiet; then echo "  nothing to commit"; else
    git -C "$DIR" commit -q -m "chore: onboard with autocraft agent team (CI, security scanning, templates)"
  fi
else echo "+ git init -b main && git add -A && git commit"; fi

step "3. Create GitHub repository $REPO ($VIS) and push main"
if ((DRY)); then echo "+ gh repo create $REPO --$VIS --source . --remote origin --push"
elif git -C "$DIR" remote get-url origin >/dev/null 2>&1; then
  echo "  remote 'origin' already set; pushing"
  git -C "$DIR" push -u origin HEAD
elif gh repo view "$REPO" >/dev/null 2>&1; then
  echo "  repo exists; attaching as origin and pushing"
  git -C "$DIR" remote add origin "$(gh repo view "$REPO" --json url -q .url).git"
  git -C "$DIR" push -u origin HEAD
else
  gh repo create "$REPO" "--$VIS" --source "$DIR" --remote origin --push
fi

step "4. Labels"
if ! ((DRY)); then
  jq -c '.[]' "$TPL/labels.json" | while read -r l; do
    gh label create "$(jq -r .name <<<"$l")" --color "$(jq -r .color <<<"$l")" \
      --description "$(jq -r .description <<<"$l")" --force -R "$REPO" >/dev/null
  done; echo "  labels created"
else echo "+ create labels from templates/labels.json"; fi

step "5. Repository settings (squash-only, auto-delete merged branches)"
try gh api -X PATCH "repos/$REPO" -F allow_squash_merge=true -F allow_merge_commit=false \
  -F allow_rebase_merge=false -F delete_branch_on_merge=true

step "6. Security: SCA, SAST, secrets"
try gh api -X PUT "repos/$REPO/vulnerability-alerts"
try gh api -X PUT "repos/$REPO/automated-security-fixes"
try gh api -X PATCH "repos/$REPO" \
  -f 'security_and_analysis[secret_scanning][status]=enabled' \
  -f 'security_and_analysis[secret_scanning_push_protection][status]=enabled'
echo "  (CodeQL + Dependabot are configured by the files committed under .github/)"

step "7. Branch protection on main"
if ((DRY)); then echo "+ gh api -X PUT repos/$REPO/branches/main/protection --input templates/branch-protection.json"
elif ! gh api -X PUT "repos/$REPO/branches/main/protection" --input "$TPL/branch-protection.json" >/dev/null 2>&1; then
  echo "  WARN: branch protection failed. Private repos need GitHub Pro/Team/Enterprise (or make the repo public)." >&2
  WARN=$((WARN+1))
fi

step "8. Verify (read back, don't assume)"
if ! ((DRY)); then
  gh api "repos/$REPO/branches/main/protection" --jq '{pr_reviews: .required_pull_request_reviews.required_approving_review_count, checks: .required_status_checks.contexts, enforce_admins: .enforce_admins.enabled, force_push: .allow_force_pushes.enabled}' 2>/dev/null \
    || echo "  main is NOT protected"
  gh api "repos/$REPO" --jq '{private: .private, secret_scanning: .security_and_analysis.secret_scanning.status, push_protection: .security_and_analysis.secret_scanning_push_protection.status}' 2>/dev/null || true
fi

printf '\nFinished with %d warning(s). Next: the repo-onboarder agent adapts CI to your real stack and writes docs/onboarding-report.md.\n' "$WARN"
