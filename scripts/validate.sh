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
for f in archetypes/*/archetype.md; do
  for h in "## Summary" "## In plain words" "## Questions the requirements-analyst must ask" "## Architecture must cover" "## Testing strategy" "## Walking skeleton" "## CI & tooling" "## Where it runs (simple defaults)" "## Security focus" "## Release checklist additions" "## Common pitfalls" "## Suggested stacks"; do
    grep -q "^$h" "$f" || err "$f: missing heading '$h'"
  done
done
for f in capabilities/*.md; do
  [[ "$(basename "$f")" == README.md ]] && continue
  for h in "## In plain words" "## Trigger words" "## Safe defaults" "## Must test" "## Common mistakes" "## Don't build it yourself"; do
    grep -q "^$h" "$f" || err "$f: missing heading '$h'"
  done
done
for f in .claude/agents/*.md; do
  [[ "$(basename "$f")" == "ux-designer.md" || "$(basename "$f")" == "delivery-lead.md" ]] || grep -q "Archetype awareness" "$f" || err "$f: missing Archetype awareness section"
  grep -q "Capabilities & audience" "$f" || err "$f: missing Capabilities & audience section"
done
# every supported language has a CI template; archetypes listed in the catalog exist and vice versa
# shellcheck source=lang.sh
. scripts/lang.sh
for l in $LANGS; do [[ -f "templates/github/workflows/ci-$l.yml" ]] || err "no CI template for language $l"; done
for d in archetypes/*/; do n="$(basename "$d")"; grep -q "($n/archetype.md)" archetypes/README.md || err "archetype $n missing from archetypes/README.md"; done
for f in capabilities/*.md; do n="$(basename "$f")"; [[ "$n" == README.md ]] || grep -q "($n)" capabilities/README.md || err "capability $n missing from capabilities/README.md"; done
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
for a in $(grep -rhoE '`(requirements-analyst|architect|principal-engineer|repo-onboarder|developer|pr-reviewer|release-gatekeeper|security-auditor|delivery-lead|ux-designer)`' docs .claude README.md | tr -d '`' | sort -u); do
  [[ -f ".claude/agents/$a.md" ]] || err "referenced agent missing: $a"
done
# relative markdown links resolve
while IFS= read -r l; do
  file="${l%%:*}"; target="${l#*:}"; target="${target%%#*}"
  [[ -z "$target" || "$target" == http* ]] && continue
  [[ -e "$(dirname "$file")/$target" ]] || err "$file: broken link -> $target"
done < <(grep -rnoE '\]\(([^)]+)\)' README.md docs archetypes capabilities | sed -E 's/^([^:]+):[0-9]+:\]\((.*)\)$/\1:\2/')

((fail)) && { echo "Validation FAILED" >&2; exit 1; }
echo "Validation passed: $(ls .claude/agents | wc -l) agents, $(ls .claude/skills | wc -l) skills, $(ls -d archetypes/*/ | wc -l) archetypes, $(($(ls capabilities | wc -l)-1)) capabilities, $(echo $LANGS | wc -w) languages"
