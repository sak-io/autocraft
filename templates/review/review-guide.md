<!-- review-guide: base=<sha> head=<sha> -->
# Reviewer's guide to <PR / branch>

<!-- First line: fill base and head with `merge_base` and `head` from `autocraft review-map --json` (full commit ids). `review-map --json` compares it with HEAD to report guide_status: current (or only docs changed since) / stale / missing, so nobody writes a second guide. A reference to a file the product creates at runtime goes on the same line as, or the line after, `<!-- verify-guide: runtime -->` (or list a glob in `verify_guide_ignore`); it is then reported as declared, never dropped. -->

> Written by a fresh `pr-reviewer` that did not build this change (workflow `/review-guide`). Numbers in section 1 are computed by `autocraft review-map`, not typed. Every `path:line` and `path:symbol` below is checked by `autocraft review-map --verify-guide docs/review-guide.md`. Line numbers drift; symbol names are the stable handle. Delete this note's instructions when you fill the template; keep the guide readable in one sitting.

## 1. What is in the diff

<!-- Paste the output of `autocraft review-map` here, verbatim (the table, the product list and the summary line). Do not retype numbers. Then one line per area saying read / skim / skip and why. -->

```
(paste autocraft review-map output)
```

| Area | Review stance |
| :-- | :-- |
| product code | **Read.** Sections 3 and 4 give an order. |
| tests | Verification. Read the tests named in section 3; skim the rest. |
| generated / vendored | **Skip.** Marked `linguist-generated`; not product code. |
| docs, config | Read only what section 4 names. |

## 2. The system on one page

<!-- A small diagram or list of components and data flow: 10-20 lines. -->

**Trust boundaries (where untrusted input enters):**
1. <!-- e.g. anything a user or agent types; stored text later injected into prompts -->
2. <!-- e.g. local processes / network clients talking to a socket or port -->
3. <!-- e.g. files this software reads or edits that the user also edits -->

## 3. Properties that must always hold

<!-- One row per invariant that would be a silent or security-relevant bug if broken. Prefer 8-15 rows. "Enforced in" and "Tested in" use `path:symbol`. -->

| # | Property | Enforced in | Tested in | Try breaking it |
| :-- | :-- | :-- | :-- | :-- |
| P1 | <!-- what must hold --> | `path/to/file.ext:symbol` | `tests/test_x.ext` | <!-- one-line mutation; the named test should fail --> |

## 4. Suggested reading order

Time boxes are estimates for a careful reader, not measurements. `autocraft review-map --slices` gives a starting grouping.

| Slice | Files | Focus | Estimate |
| :-- | :-- | :-- | :-- |
| A | `path/to/file.ext` | <!-- what to look for --> | <!-- e.g. 1-2 h --> |

If time is short, read only: <!-- the properties/slices where a bug is silent or security-relevant -->.

## 5. How to verify rather than trust

```
# the exact commands: full test suite, a real manual try, the build
```

- <!-- how to break a property on purpose and see a named test fail -->

## 6. What has NOT been independently verified

<!-- MANDATORY. Must not be empty. Be specific; "we do not know" is a valid answer. -->

- **Who reviewed this code:** <!-- If every review was done by AI agents, say exactly that and that no human has read it. Say where their findings are recorded. -->
- **Never run live:** <!-- real services, real hosts/installs, real accounts, production-like load -->
- **Synthetic data:** <!-- which fixtures/corpora/benchmarks were written by the build agents rather than coming from real use -->
- **Untested platforms / versions:** <!-- OS, runtimes, browsers, devices -->
- **Skipped or conditional tests:** <!-- which, and why (e.g. needs root, needs network, slow) -->
- **Known gaps:** <!-- documented limitations, missing hardening -->

## 7. Decisions that need the owner

- <!-- defaults chosen on the owner's behalf: licence, names, thresholds, scope cuts, accepted risks -->

## 8. Making it reviewable

<!-- Summary of `autocraft review-map --slices`: number of slices and sizes, the generated bootstrap first. If the diff exceeds twice the thresholds the lead OFFERS the split to the owner; say here whether it was accepted, declined or not yet asked. Never split without an explicit yes. -->
