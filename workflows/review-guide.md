---
id: review-guide
needs: [pr-reviewer]
description: Writes a reviewer's guide for a large change - what is in the diff (computed, not typed), the properties that must hold and where they are enforced and tested, a reading order, how to verify, and a mandatory section on what has NOT been independently verified. Written by a fresh pr-reviewer that did not build the change; every cited path:symbol is checked by a script. Use when `autocraft review-map` says guide_recommended, or before asking a human to review a big PR.
---

# /review-guide [base..head]

A human should be able to review a big change in one sitting. This workflow produces `docs/review-guide.md` (configurable) so they know what to read, what to skip, what must hold, and what nobody has verified. Background and numbers: `docs/reviewing-large-prs.md`.

Do **not** run it for every PR. Small changes do not need a guide; `autocraft review-map` decides (config: `human_review`, `review_guide`, `review_guide_min_files`, `review_guide_min_product_lines`).

## Rules
1. **Numbers come from the script, never from you.** First run `python3 .autocraft/framework/bin/autocraft review-map --json` (add `--base`/`--head` if the range is not "this branch against the default branch") and paste its table into section 1 *verbatim*. Never retype or recompute a count, a line total or a file list. If the output changes later, re-run and re-paste.
2. **Written by a fresh `pr-reviewer`** that did not build the change and has not seen the builders' reasoning or summaries. It works from the code, tests, ADRs and git history. The lead must not write it, and must not paste builder summaries into the brief.
3. **Judgment is the reviewer's job; facts are the script's.** The reviewer writes: the properties table, trust boundaries, reading order, break-it tips, the unverified section, owner decisions. Everything countable comes from `review-map`.
4. **Verify before publishing.** Run `python3 .autocraft/framework/bin/autocraft review-map --verify-guide docs/review-guide.md` and fix every failing reference (STALE: wrong file or line beyond the file or symbol absent; NOT DEFINED: the symbol only occurs in a comment, string or use; AMBIGUOUS: a bare file name that matches several files) until it exits 0 **with every non-declared reference ok**. A path with a directory must be the exact repository path; a bare file name may resolve by suffix only if unique (printed as `ok (resolved by suffix -> path)`: prefer citing the full path). A reference to something the product creates at runtime (not in the repository) is declared on the same or the previous line with `<!-- verify-guide: runtime -->`, or by a `verify_guide_ignore` glob in the config; it is listed as `declared (runtime)` and counted, never dropped. Read the footer (`checked N references (K declared); skipped F fenced-code lines; U unparsed candidates`) to see what was NOT checked. Line numbers drift: say in the guide that symbol names are the stable handle.
5. **Section 6 is mandatory and must not be empty.** It states who reviewed the code (if every review was by an AI agent, say so in plain words and that no human has read it), what was never run live (real services, real hosts, real installs, real data), what data is synthetic, which platforms and versions are untested, which tests were skipped and why, and known gaps. An honest "we do not know" beats a confident gap.
6. **Concise.** The guide must be readable in one sitting; link to files rather than quoting them. Estimates are labelled as estimates.
7. **Mark it.** The first line of the guide is `<!-- review-guide: base=<merge_base> head=<head> -->` with the full commit ids from `review-map --json`; that is how `guide_status` is computed.
8. **Save and link.** Save to `docs/review-guide.md` (or the path in the invocation), commit it, and put one sentence linking it at the very top of the PR description (or, with no PR, at the top of the summary to the owner): "Start with the [reviewer's guide](docs/review-guide.md)."

## Steps
1. Lead: run `review-map --json`; if `guide_recommended` is false and the owner did not insist, stop and say so. If `guide_status` is `current` (the guide's first-line marker matches HEAD, or only documentation changed since), **skip regeneration** and just link it; if `stale`, update it rather than starting a second one. Brief the reviewer with only: the range, the paths of the spec, architecture/ADRs, and this workflow.
2. Reviewer: copy `.autocraft/templates/review/review-guide.md` to `docs/review-guide.md` and fill it in:
   1. *What is in the diff* - the `review-map` output, verbatim.
   2. *The system on one page* + trust boundaries - a small diagram or list, and where untrusted input enters.
   3. *Properties that must always hold* - table: property | enforced in `path:symbol` | tested in | how to try to break it.
   4. *Suggested reading order* - slices (`review-map --slices` gives a starting point) with rough time boxes, labelled estimates.
   5. *How to verify rather than trust* - the exact commands.
   6. *What has NOT been independently verified* - mandatory (rule 5).
   7. *Decisions that need the owner*.
   8. *Making it reviewable* - the split proposal (summary of `review-map --slices`), or why a split is not worth it.
3. Reviewer: run `--verify-guide` and fix until exit 0; report the final line of its output.
4. Lead: commit the guide, link it as in rule 7, and tell the owner what to read first. If `split_recommended` is true in the `review-map --json` output, also **offer** the stacked-PR split (section 8 of the guide); see "Split offer" below.

## Split offer (only offer; never do it unasked)
If the diff exceeds **twice** the thresholds (`split_recommended`), show the owner the plan from `review-map --slices` (number of slices, sizes, the generated bootstrap slice first) and ask: "Split into N stacked PRs?" Perform it **only after an explicit yes**. How to do it mechanically and safely is in `docs/reviewing-large-prs.md` ("Splitting a large diff"): `review-map --emit-split-script` prints the commands; every slice branch must build and pass the tests on its own; the generated bootstrap goes first; open each PR against the previous slice's branch. Without a yes, continue with the single PR plus the guide.
