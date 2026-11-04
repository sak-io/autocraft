# Reviewing large PRs

When a team of agents builds a whole project, the pull request that finally reaches the human can be enormous, and most of it is not what the human should read. This page explains what autocraft does about that, why, and how to use each piece. Everything here is deterministic (plain `git` and a stdlib script) unless it says a *reviewer role* does it.

## The evidence

A real project built with autocraft (Engram, a Python daemon and MCP server) produced a PR that looked like **283 files / ~22,600 added lines**. Only **20 files (~5,600 lines)** were product code. **157 files** were the vendored framework copy under `.autocraft/` and **14** were generated agent/skill files. A human could not tell what to review. The team then hand-wrote a reviewer's guide, and the lessons from doing it became this feature set:

| Lesson | What autocraft does |
|---|---|
| Generated files drown the diff, and GitHub only collapses what is marked | `init`/`sync` maintain a **`linguist-generated` block in `.gitattributes`** |
| The framework install should not be mixed with product commits | **`init --commit` / `sync --commit`**: one dedicated commit, nothing else in it |
| The factual part of a guide (diff stats, whether `path:symbol` exists) was wrong in the first draft (bad helper names, bad line counts) until checked by hand | **`autocraft review-map`** computes the numbers, and **`--verify-guide`** checks every reference |
| The judgment part (invariants, trust boundaries, what is unverified) must not be written by the builder | the **`/review-guide`** workflow: a *fresh* `pr-reviewer` writes it from the code |
| A guide on every PR is noise | **thresholds in config** decide when one is recommended |
| Splitting a huge diff into stacked PRs is valuable but invasive | **offered** (`--slices`, `--emit-split-script`), done only after an explicit yes |

For Engram, `review-map` run against the merged PR (`e66a4ba..9733ba1`) reports 284 files (the hand guide's 283 plus the guide itself) / 22,739 added; `engram/` has exactly **20 product files / 5,601 lines**; `.autocraft/` has 157 files; 14 files under `.claude/` are generated; the generated class is 168 files = 59% of the diff.

## 1. Generated-file markers (`.gitattributes`)

`autocraft init` and `autocraft sync` keep a managed block in the project's `.gitattributes`:

```
# autocraft:begin generated (managed block - do not edit between the markers)
.autocraft/framework/** linguist-generated=true
.claude/agents/** linguist-generated=true
...
# autocraft:end
```

GitHub collapses `linguist-generated` files in pull request diffs and excludes them from language statistics. Rules:

- Only files autocraft writes **wholly** are listed: `.autocraft/framework/**`, `.autocraft/templates/**`, `.autocraft/archetypes/**`, `.autocraft/capabilities/**`, `.autocraft/protocol.md`, `.autocraft/manifest.json`, the neutral copies `.autocraft/roles/**` and `.autocraft/workflows/**` (for tools that need them), and each configured tool's whole-file outputs (`.claude/agents/**`, `.claude/skills/**`, `claude-project/**`, `prompts/**`, the `role-*`/`workflow-*`/`autocraft-team` rule files of Cursor and Windsurf, `.clinerules/autocraft-team.md`, and the exact Copilot/Gemini files from the manifest). Derived from the manifest and the exporters; a new exporter output nobody listed is still marked file by file.
- **Never** listed: files that merely contain a managed *block* inside a file you edit (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md`), `.autocraft/config.yml`, `.autocraft/custom/**`, `.claude/settings.json`, your own files in shared directories (`.github/agents/mine.agent.md`).
- Everything outside the block is preserved byte for byte; a second run changes nothing (the file is not even rewritten); removing a tool removes its entries on the next sync.
- Opt out with `autocraft init --no-gitattributes` (stored as `generated_markers: false` in `.autocraft/config.yml`; sync then leaves `.gitattributes` alone).
- `autocraft doctor` warns (exit code stays 0) if the block is missing or stale. If your own `.gitattributes` has a rule that switches `linguist-generated` off (`-linguist-generated`, `=false`) for a path in the block, `sync` and `doctor` print a warning naming the line and who wins: git uses the **last** matching line, so autocraft's block wins when it comes after your rule and yours wins when it comes after the block.

## 2. The install is its own commit (`--commit`)

```
autocraft init . --tool claude-code --team starter --commit     # chore(autocraft): install agent team (generated files)
autocraft sync --commit                                          # chore(autocraft): sync agent team (generated files)
```

One commit containing only autocraft-owned paths: the manifest files, the managed-block files (`CLAUDE.md` etc., only the block changes), `.autocraft/config.yml`, `.autocraft/manifest.json`, `.autocraft/framework`, `.autocraft/templates`, the `.gitattributes` block file, and scaffolding it **created** in this run (`.autocraft/custom/*`, `.claude/settings.json`, `docs/` skeleton). Guarantees:

- Only inside a git work tree (checked before anything is written); works in a repository with no commits.
- Staged with explicit pathspecs (never `git add -A`) and committed *with a pathspec*, so unrelated staged or unstaged changes of yours stay exactly as they were.
- If `CLAUDE.md` or `.gitattributes` has uncommitted edits of yours outside the managed block, it is left out of the commit and the output says so. Ignored paths are skipped with a note.
- Hooks run (never `--no-verify`). If the commit fails, git's message is shown, the exit code is non-zero and what autocraft staged is unstaged again (the files stay on disk).
- Nothing to commit: says so and commits nothing; exit code 0 for both `init` and `sync` (re-running on an up-to-date repository is not an error). It never pushes. The success line names the branch (or the detached HEAD) it committed on.

**Why:** the bootstrap is generated, large and not worth reviewing; keeping it in its own commit (before any product work) lets reviewers filter it. If the owner wants human review of a PR, open the bootstrap commit as a small separate PR first, or rely on the generated markers to collapse it.

## 3. `autocraft review-map`

```
autocraft review-map [DIR] [--base REF] [--head REF] [--json] [--top N] [--slices] [--target-lines N] [--emit-split-script] [--verify-guide FILE]
```

Deterministic, read-only, zero model tokens. `DIR` is the repository (default `.`); any path works, not only the current directory. The diff is `git diff --numstat -M BASE...HEAD`. Default head `HEAD`; default base = the merge-base of HEAD with `origin/<default_branch>` if that exists, else the local `<default_branch>` (config, default `main`). Exit codes: `0` success (an empty diff is success), `1` stale references (`--verify-guide`), `2` usage or environment error (not a git repo, unknown ref, no base, shallow clone without the merge-base: the message says to run `git fetch --unshallow` or pass `--base`).

### Classification (first match wins; table-driven)

| class | rules |
|---|---|
| generated | paths in `.autocraft/manifest.json`; `linguist-generated` entries of `.gitattributes`; the configured tools' generated globs; `.autocraft/framework/**`; lockfiles (`*.lock`, `package-lock.json`, `pnpm-lock.yaml`, `go.sum`, ...); `*.min.*`; `dist/` `build/` `vendor/` `node_modules/` `*.egg-info/` |
| tests | `tests/` `test/` `__tests__/` `spec/` `test_helpers/` `testing/` `fixtures/` `testdata/` `__fixtures__/`; `test_*.*` `*_test.*` `*.test.*` `*.spec.*`; `conftest.py` |
| docs | `docs/`; `*.md` `*.rst` `*.txt` `*.adoc`; `LICENSE`, `CHANGELOG`, ... (outside tests) |
| ci_config | `.github/`; `requirements*.txt`; `*.toml` `*.yml` `*.yaml` `*.json` `*.ini` `*.cfg`; `Dockerfile`, `Makefile`, `.gitignore`, `.gitattributes`, `MANIFEST.in`, ... |
| product | every other code file (known code extensions, or an extension-less script) |
| other | everything else (images, data, binaries, dotfiles) |

Known heuristics: a root-level `test_utils.py` counts as tests (name-based); a product package whose directory is literally called `testing/` or `fixtures/` would also count as tests (add it to a config glob or rename it); JSON fixtures under `data/` stay `ci_config` (`*.json`), which is acceptable because they are not product code. Pattern syntax: `dir/` = that directory anywhere in the path; `name` / `*.ext` = the file name at any depth; `a/b/**` = anchored at the repository root. Extend from `.autocraft/config.yml`: `review_map_extra_generated: [globs]`, `review_map_extra_tests: [globs]`. The manifest, tools and `.gitattributes` are read from the **head commit**, not the working tree, so an old range is classified as it was then. Same rules in `autocraft review-map --help`.

Output: a table (class, files, added, deleted, share of files and of added lines), the product files by added lines (top `--top`, default 15), a summary line (`284 files / 22739 added: 24 product files (5751 lines), 55 test files (8542 lines), ...`), a warning when generated files exceed 30% of the files, and the guide recommendation. `--json` has the same data plus every file with its class, `guide_recommended`, `guide_reason`, `split_recommended` and `split_reason`.

### When is a guide recommended? (config)

```yaml
human_review: optional              # optional | required
review_guide: auto                  # auto | always | never
review_guide_min_files: 60
review_guide_min_product_lines: 1500
```

`guide_recommended` is false when `review_guide: never`; true when `always`; with `auto` true if files changed > `review_guide_min_files`, or added product lines > `review_guide_min_product_lines`, or `human_review: required`. `guide_reason` says which rule fired. `split_recommended` is true when files or product lines exceed **twice** those thresholds. `autocraft doctor` validates these keys. Small PRs do not need a guide.

### `--verify-guide FILE`

Checks a markdown guide against the tree at `--head`. References recognised (outside fenced code blocks, which are skipped and counted): `path/to/file.ext:123`, `:123-140`, `path#L3` / `#L3-L9` (GitHub style), `file.ext:symbol`, `` `path/to/file.ext` ``, markdown link targets (the path of an ordinary markdown link; http(s)/mailto/anchors ignored; resolved from the repo root, then from the guide's own directory), bare paths in text (a token with a `/` and a known extension), and Windows paths (`lib\mod.py:3` is normalised); also inside tables. A leading `./` is stripped.

- **Paths:** a reference with a directory must be the **exact** path in the tree (`lib/deleted.py` does not match `vendor/lib/deleted.py`). Only a bare file name may resolve by suffix: exactly one match prints `ok (resolved by suffix -> path)`, several print `AMBIGUOUS` (exit 1), none is `STALE`.
- **Lines:** the number must be within the file (`STALE` otherwise).
- **Symbols** (case-sensitive whole word): `STALE` if absent from the file, `NOT DEFINED` (exit 1) if it occurs only in a comment, a string literal or a plain use, `ok` if defined. "Defined" means it follows `def`/`async def`/`class`/`function`/`const`/`let`/`var`/`interface`/`type`/`enum`/`struct`/`fn`/`func`/`impl`/`trait`/`module`/`package`, starts an assignment or declaration (`NAME = ...`, `NAME: T = ...`, `NAME := ...`, with `export`/`pub`/`static`... prefixes), is a `NAME:` key at the start of a line (YAML/markdown front matter), a shell function (`NAME()`), a method declared with modifiers (`public ... NAME(`), or a heading in a markdown file. Before looking for definitions, comment-only lines (`#` `//` `--` `;` `*` `/*`) and one-line string literals are blanked, and trailing `#`/`//` comments removed. This is best effort and language-agnostic: multi-line strings or docstrings and unusual definition syntaxes are not understood. `--allow-mentioned` downgrades `NOT DEFINED` to `mentioned (allowed)` (exit 0).
- **Runtime artifacts:** a guide may legitimately cite something the product creates at runtime. Declare it on the same line or the line before with `<!-- verify-guide: runtime -->` (alias `ignore`), or list a glob in `verify_guide_ignore: [...]` in the config. These are shown as `declared (runtime)` and counted separately, never silently dropped.
- Every run ends with `checked N references (K declared); skipped F fenced-code lines; U unparsed candidates` (also in `--json` `summary`): the last number counts path-looking link targets and code spans that were not accepted as references, so you can see what was not checked.

Exit 1 if any reference is `STALE`, `AMBIGUOUS` or `NOT DEFINED`.

### Is there already a guide? (`guide_status`)

`review-map --json` (and the text output) report `guide_status` for the configured `review_guide_path` (default `docs/review-guide.md`): `missing`, `current` or `stale`. The guide's **first line** is `<!-- review-guide: base=<sha> head=<sha> -->` (the template has it; the workflow fills in `merge_base` and `head` from `review-map --json`). `current` = that head is the one being described, or only documentation changed since; anything else is `stale`; no valid marker is `stale`. The workflows skip regeneration when it is `current`.

### `--slices` and `--emit-split-script`

See "Splitting a large diff" below.

## 4. The `/review-guide` workflow and template

`workflows/review-guide.md` (needs `pr-reviewer`; exported to every tool like the other workflows) and `templates/review/review-guide.md` (installed to `.autocraft/templates/review/`). Eight sections: (1) what is in the diff (the `review-map` output pasted verbatim), (2) the system on one page and the trust boundaries, (3) the properties that must always hold (property | enforced in `path:symbol` | tested in | how to try to break it), (4) a reading order with time boxes labelled as estimates, (5) how to verify rather than trust, (6) **what has NOT been independently verified** (mandatory, never empty; states who reviewed, and says so plainly if every review was by AI agents; lists what was never run live, synthetic data, untested platforms, skipped tests), (7) decisions that need the owner, (8) making it reviewable.

Rules the workflow enforces: numbers come from `review-map --json` and are never retyped; the guide is written by a **fresh** `pr-reviewer` that did not build the change, from the code, not from builder summaries; `--verify-guide` must exit 0 before publishing; saved as `docs/review-guide.md` and linked in one sentence at the very top of the PR description; concise enough to read in one sitting. `kickoff`, `release-check` and `build-feature` (when it is the last task) end with: run `review-map`; if `guide_recommended`, run `/review-guide`; if `split_recommended`, also offer the split.

## Splitting a large diff

`--slices` proposes a split of the **non-generated** changes into stacked slices of at most `--target-lines` (default 1500) added lines:

- Group by top-level directory, then sub-directory; keep each product file with its tests (same stem, `test_<stem>`, `<stem>_test`, `<stem>.test.*`, `tests/<dir>` mirror; a test with no same-stem file goes with the module it mentions most) and docs of the same stem; order slices by directory path.
- **Slice 0, "bootstrap (generated)"**: all generated files, to land **first** as their own PR (or to be ignored since they are marked generated). First, because everything after it is then free of that noise, and because its content does not depend on product code.
- Docs and config leftovers go in the last slice.
- A product file plus its tests is never split; if one such group exceeds the target it is flagged as larger than the target.

**It is a heuristic proposal, not dependency-aware.** Slices are ordered by path, not by imports, so slice N may need code from slice N+1.

`--emit-split-script` **prints, and never runs,** a bash script. Review it, then run it yourself in a clean work tree (it refuses otherwise):

```
git checkout -b slice-0-bootstrap "$BASE"        # BASE = merge-base
git checkout "$HEAD" -- <paths of the slice>      # deleted/renamed paths are removed with git rm
git commit -m "chore: bootstrap (generated files)"
# git push -u origin slice-0-bootstrap            # then open a PR
git checkout -b slice-1 slice-0-bootstrap          # each branch starts on the previous one
...
git diff --stat slice-N "$HEAD"                    # prints nothing when the stack reproduces head exactly
```

Doing it safely:

1. **Offer, never impose.** If `split_recommended` the lead shows the owner the plan (number of slices, sizes, bootstrap first) and asks. Without an explicit yes, nothing is split.
2. **Every slice branch must pass the tests on its own.** Check out `slice-1`, `slice-2`, ... in order and run the build and the full suite on each. A failure usually means a missing dependency from a later slice: merge the two slices (raise `--target-lines`) or reorder them.
3. **Stacked PR bases:** `slice-0-bootstrap` targets the default branch; `slice-N` targets `slice-(N-1)`. When the lower PR merges, retarget the next one to the default branch (GitHub does this automatically when the base branch is deleted after merge).
4. **A later slice changes an earlier slice's files:** the script gives each file to exactly one slice (its final content from head), so this does not occur in the generated stack. If you restructure by hand and a later slice must touch an earlier file, put the change in the earlier slice, then rebase the later branches on it (`git rebase --onto`), rather than editing history on a branch that is already under review.
5. The last branch equals head: verify with the final `git diff --stat`.

## Summary of the numbers

| | Engram PR (`e66a4ba..9733ba1`) |
|---|---|
| files / added lines | 284 / 22,739 (hand guide: 283 / ~22,600; +1 = the guide) |
| product (`engram/`) | 20 files / 5,601 lines (hand guide: 20 / ~5,600); `review-map` also counts 4 small `scripts/` files as product (24 / 5,751) |
| `.autocraft/` | 157 files (hand guide: 157) |
| generated class | 168 files (59%): 154 under `.autocraft/`, 14 under `.claude/` |
| tests | 55 files / 8,542 lines (hand guide: 59 incl. some scripts) |
