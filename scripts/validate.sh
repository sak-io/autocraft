#!/usr/bin/env bash
# Sanity-check the framework itself: agent/skill frontmatter, templates, scripts, doc links.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
fail=0; err() { echo "FAIL: $*" >&2; fail=1; }

fm() { awk 'NR==1&&$0!="---"{exit} NR>1&&$0=="---"{exit} NR>1{print}' "$1"; }  # print frontmatter
field() { fm "$1" | sed -n "s/^$2: *//p" | head -1; }

for f in .claude/agents/*.md; do
  n="$(field "$f" name)"; d="$(field "$f" description)"
  [[ "$n" == "$(basename "$f" .md)" ]] || err "$f: name '$n' != filename"
  [[ -n "$d" ]] || err "$f: missing description"
  [[ -n "$(field "$f" tools)" ]] || err "$f: missing tools"
done
for f in .claude/skills/*/SKILL.md; do
  n="$(field "$f" name)"; d="$(field "$f" description)"
  [[ "$n" == "$(basename "$(dirname "$f")")" ]] || err "$f: name '$n' != directory"
  [[ -n "$d" ]] || err "$f: missing description"
done
for f in scripts/*.sh; do bash -n "$f" || err "$f: syntax error"; done
for f in templates/labels.json templates/branch-protection.json; do
  python3 -c "import json,sys; json.load(open('$f'))" 2>/dev/null || err "$f: invalid JSON"
done
python3 - <<'PY' || fail=1
import glob, sys
try: import yaml
except ImportError: print("(skip YAML check: PyYAML not installed)"); sys.exit(0)
bad = 0
for f in glob.glob("templates/github/**/*.yml", recursive=True) + glob.glob("templates/*.yml"):
    try: yaml.safe_load(open(f))
    except Exception as e: print("FAIL:", f, e); bad = 1
sys.exit(bad)
PY
# every agent referenced in docs/skills exists
for a in $(grep -rhoE '`(requirements-analyst|architect|principal-engineer|repo-onboarder|developer|pr-reviewer|release-gatekeeper|security-auditor|delivery-lead)`' docs .claude README.md | tr -d '`' | sort -u); do
  [[ -f ".claude/agents/$a.md" ]] || err "referenced agent missing: $a"
done
# relative markdown links resolve
while IFS= read -r l; do
  file="${l%%:*}"; target="${l#*:}"; target="${target%%#*}"
  [[ -z "$target" || "$target" == http* ]] && continue
  [[ -e "$(dirname "$file")/$target" ]] || err "$file: broken link -> $target"
done < <(grep -rnoE '\]\(([^)]+)\)' README.md docs | sed -E 's/^([^:]+):[0-9]+:\]\((.*)\)$/\1:\2/')

((fail)) && { echo "Validation FAILED" >&2; exit 1; }
echo "Validation passed: $(ls .claude/agents | wc -l) agents, $(ls .claude/skills | wc -l) skills"
