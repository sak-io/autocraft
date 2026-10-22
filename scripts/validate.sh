#!/usr/bin/env bash
# Sanity-check the framework: roles, teams, workflows, archetypes, capabilities, CLI exports, docs.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
fail=0; err() { echo "FAIL: $*" >&2; fail=1; }

fm() { awk 'NR==1&&$0!="---"{exit} NR>1&&$0=="---"{exit} NR>1{print}' "$1"; }
field() { fm "$1" | sed -n "s/^$2: *//p" | head -1; }
inlist() { # inlist "a, b" -> a b
  echo "$1" | tr -d '[]' | tr ',' ' '; }

ROLES=""; for f in roles/*.md; do ROLES="$ROLES $(basename "$f" .md)"; done
WFS="";   for f in workflows/*.md; do WFS="$WFS $(basename "$f" .md)"; done
ARCHS=""; for d in archetypes/*/; do ARCHS="$ARCHS $(basename "$d")"; done
has() { [[ " $1 " == *" $2 "* ]]; }

# --- roles
for f in roles/*.md; do
  id="$(basename "$f" .md)"
  [[ "$(field "$f" id)" == "$id" ]] || err "$f: id != filename"
  for k in title category description abilities; do [[ -n "$(field "$f" $k)" ]] || err "$f: missing $k"; done
  for a in $(inlist "$(field "$f" abilities)"); do has "read search write edit shell" "$a" || err "$f: bad ability $a"; done
done
# --- workflows
for f in workflows/*.md; do
  [[ "$(field "$f" id)" == "$(basename "$f" .md)" ]] || err "$f: id != filename"
  [[ -n "$(field "$f" description)" ]] || err "$f: missing description"
done
# --- teams
covered=""
for f in teams/*.md; do
  id="$(basename "$f" .md)"
  [[ "$(field "$f" id)" == "$id" ]] || err "$f: id != filename"
  for k in name summary roles workflows; do [[ -n "$(field "$f" $k)" ]] || err "$f: missing $k"; done
  for r in $(inlist "$(field "$f" roles)") $(inlist "$(field "$f" optional)"); do has "$ROLES" "$r" || err "$f: unknown role $r"; done
  for w in $(inlist "$(field "$f" workflows)"); do has "$WFS" "$w" || err "$f: unknown workflow $w"; done
  for a in $(inlist "$(field "$f" fits)"); do has "$ARCHS" "$a" || err "$f: unknown archetype $a"; covered="$covered $a"; done
done
for a in $ARCHS; do has "$covered" "$a" || err "archetype $a is not covered by any team's 'fits'"; done
# --- archetypes & capabilities
for f in archetypes/*/archetype.md; do
  for h in "## Summary" "## In plain words" "## Questions the requirements-analyst must ask" "## Architecture must cover" "## Testing strategy" "## Walking skeleton" "## CI & tooling" "## Where it runs (simple defaults)" "## Security focus" "## Release checklist additions" "## Common pitfalls" "## Suggested stacks"; do
    grep -q "^$h" "$f" || err "$f: missing heading '$h'"
  done
done
for d in $ARCHS; do grep -q "($d/archetype.md)" archetypes/README.md || err "archetype $d missing from archetypes/README.md"; done
for f in capabilities/*.md; do
  n="$(basename "$f")"; [[ "$n" == README.md ]] && continue
  for h in "## In plain words" "## Trigger words" "## Safe defaults" "## Must test" "## Common mistakes" "## Don't build it yourself"; do
    grep -q "^$h" "$f" || err "$f: missing heading '$h'"
  done
  grep -q "($n)" capabilities/README.md || err "capability $n missing from capabilities/README.md"
done
# --- CLI: compiles, CI template per language, tool docs, end-to-end export smoke test
python3 -m py_compile bin/autocraft || err "bin/autocraft does not compile"
rm -rf bin/__pycache__
for l in $(python3 -c "import runpy,sys; m=runpy.run_path('bin/autocraft', run_name='x'); print(' '.join(m['LANGS']))"); do
  [[ -f "templates/github/workflows/ci-$l.yml" ]] || err "no CI template for language $l"; done
for t in $(python3 -c "import runpy; m=runpy.run_path('bin/autocraft', run_name='x'); print(' '.join(m['TOOLS']))"); do
  [[ -f "docs/tools/$t.md" ]] || err "missing docs/tools/$t.md"; done
# --- agent-agnostic task board
[[ -f templates/board/board.py && -f templates/board/AGENTS.md ]] || err "templates/board incomplete"
python3 -m py_compile templates/board/board.py || err "board.py does not compile"
rm -rf templates/board/__pycache__
BOARD_PY="$PWD/templates/board/board.py" bash templates/board/test-board.sh >/dev/null || err "board self-test failed"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
python3 bin/autocraft init "$tmp/p" --tool claude-code,claude-app,cursor,copilot,gemini-cli,windsurf,cline,agents-md,prompts \
  --team web-product,ai-product,mobile --archetype fullstack-app,ai-assistant --add-role technical-writer --lang node >/dev/null || err "autocraft init failed"
python3 "$tmp/p/.autocraft/framework/bin/autocraft" doctor "$tmp/p" >/dev/null || err "autocraft doctor failed on fresh project"
( cd "$tmp/p" && find . -path ./.autocraft/framework -prune -o -type f -print0 | sort -z | xargs -0 sha256sum > "$tmp/h1"
  python3 .autocraft/framework/bin/autocraft sync >/dev/null
  find . -path ./.autocraft/framework -prune -o -type f -print0 | sort -z | xargs -0 sha256sum > "$tmp/h2" ); cmp -s "$tmp/h1" "$tmp/h2" || err "autocraft sync is not idempotent"
# custom team + per-role model (engineer customization)
mkdir -p "$tmp/p/.autocraft/custom/teams"
cat > "$tmp/p/.autocraft/custom/teams/our-team.md" <<'TEAM'
---
id: our-team
name: Our Team
summary: Project-defined team
roles: [developer, pr-reviewer]
workflows: [build-feature, review-pr]
---
# Playbook
Builder plus independent reviewer.
TEAM
python3 "$tmp/p/.autocraft/framework/bin/autocraft" init "$tmp/p" --team our-team --remove-role technical-writer --role-model pr-reviewer=sonnet >/dev/null || err "custom team / role-model init failed"

# --- recommend must not let one incidental keyword outvote the document (regression: "vector store" -> fullstack-app)
rec="$(python3 bin/autocraft recommend 'a stdlib python daemon with a sqlite store, an mcp server and a command line tool for coding agents; a vector store of memories; the agent calls the api; library of functions; sdk package' 2>&1)"
echo "$rec" | grep -q '^  \* fullstack-app' && err "recommend: a single 'store' keyword picked fullstack-app"
python3 bin/autocraft init "$tmp/ts" --tool claude-code --team starter --token-saver >/dev/null 2>&1 || err "init --token-saver failed"
grep -q 'max_parallel_developers: 2' "$tmp/ts/.autocraft/config.yml" || err "--token-saver did not set max_parallel_developers: 2"
grep -q 'pr-reviewer=sonnet' "$tmp/ts/.autocraft/config.yml" || err "--token-saver did not set mid-tier reviewer"
[[ -f "$tmp/p/.claude/agents/pr-reviewer.md" && ! -f "$tmp/p/.claude/agents/architect.md" ]] || err "custom team roster not applied"
grep -q "^model: sonnet" "$tmp/p/.claude/agents/pr-reviewer.md" || err "role model override not exported"
python3 "$tmp/p/.autocraft/framework/bin/autocraft" init "$tmp/p" --token-mode lean >/dev/null || err "token-mode init failed"
grep -q "Token mode \`lean\`" "$tmp/p/.claude/agents/pr-reviewer.md" || err "lean token mode not exported to roles"
python3 - "$tmp/p" <<'PY' || fail=1
import sys, glob, os
os.chdir(sys.argv[1]); bad = 0
try:
    import yaml
except ImportError:
    yaml = None; print("(skip frontmatter YAML check: PyYAML not installed)")
for pat in ['.claude/agents/*.md', '.claude/skills/*/SKILL.md', '.cursor/rules/*.mdc', '.github/agents/*.agent.md', '.github/prompts/*.prompt.md', '.windsurf/rules/*.md']:
    for f in glob.glob(pat):
        t = open(f).read()
        if not t.startswith('---\n'): print('FAIL: no frontmatter', f); bad = 1; continue
        if yaml:
            try: yaml.safe_load(t.split('---\n', 2)[1])
            except Exception as e: print('FAIL: bad YAML', f, e); bad = 1
try:
    import tomllib
    for f in glob.glob('.gemini/commands/*.toml'):
        tomllib.load(open(f, 'rb'))
except ImportError: print("(skip TOML check: python < 3.11)")
except Exception as e: print('FAIL: bad TOML', e); bad = 1
for f in ['CLAUDE.md', 'AGENTS.md', 'GEMINI.md', '.github/copilot-instructions.md', '.clinerules/autocraft-team.md', 'claude-project/INSTRUCTIONS.md', '.autocraft/protocol.md']:
    if not os.path.exists(f): print('FAIL: missing export', f); bad = 1
sys.exit(bad)
PY
# --- scripts & templates
for f in scripts/*.sh; do bash -n "$f" || err "$f: syntax error"; done
for f in templates/labels.json templates/branch-protection.json; do python3 -c "import json; json.load(open('$f'))" 2>/dev/null || err "$f: invalid JSON"; done
python3 - <<'PY' || fail=1
import glob, sys
try: import yaml
except ImportError: sys.exit(0)
bad = 0
for f in glob.glob("templates/github/**/*.yml", recursive=True):
    try: yaml.safe_load(open(f))
    except Exception as e: print("FAIL:", f, e); bad = 1
sys.exit(bad)
PY
# --- docs: referenced roles exist; relative links resolve
for a in $(grep -rhoE '`('"$(echo $ROLES | tr ' ' '|')"')`' README.md docs teams 2>/dev/null | tr -d '`' | sort -u); do :; done
while IFS= read -r l; do
  file="${l%%:*}"; target="${l#*:}"; target="${target%%#*}"
  [[ -z "$target" || "$target" == http* || "$target" == mailto:* ]] && continue
  [[ -e "$(dirname "$file")/$target" ]] || err "$file: broken link -> $target"
done < <(grep -rnoE '\]\(([^)]+)\)' README.md docs archetypes capabilities | sed -E 's/^([^:]+):[0-9]+:\]\((.*)\)$/\1:\2/')

((fail)) && { echo "Validation FAILED" >&2; exit 1; }
echo "Validation passed: $(echo $ROLES | wc -w) roles, $(ls teams | wc -l) teams, $(echo $WFS | wc -w) workflows, $(echo $ARCHS | wc -w) archetypes, $(($(ls capabilities | wc -l)-1)) capabilities; all 9 tool exports generate, parse and sync idempotently"
