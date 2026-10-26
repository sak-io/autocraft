# Pre-release check - Receipt Tally (T1+T2, branch `master`, head bc92dfe)

No GitHub PR and no CI exist; the local branch is treated as the PR and local test runs stand in for CI. Entry condition: review-2.md verdict APPROVED, no open BLOCKER/MAJOR - met.

| # | Item | Result | Evidence / note |
|---|---|---|---|
| 1 | Scope; no debug code/secrets/untracked TODOs | PASS | `git status` clean; 7 modules, 320 lines (limit 400). grep for TODO/FIXME/pdb/breakpoint: none. Only `print` calls are the intended CLI output. Secret grep on tracked project files: nothing. `__pycache__`/`.pytest_cache` are git-ignored. |
| 2 | Tests / CI on head commit; integration ran | PASS (local) | `python3 -m unittest discover -s tests` -> 45 tests OK (Python 3.13.17). No CI exists (accepted for a personal local tool). CLI tests run the real program as a subprocess. |
| 3 | SCA/SAST/secret scans | PASS / N/A | Stdlib only, no dependencies to audit. Manual secret grep clean. No scanner installed, none run. |
| 4 | Migrations | N/A | No database or stored state. |
| 5 | Config / env vars / secrets | PASS | No env vars or secrets. One TOML config, documented in README with both layouts; examples/config_a.toml and config_b.toml both run. |
| 6 | Compatibility / breaking changes | PASS | First release. Spec items AC-9, 11, 12, 15 confirmed live: missing file -> `error: cannot find bank file ...`, exit 2, no traceback; no `--out` -> screen only; second `--out` run refused without `--force`, exit 2. Layout B example gives expected totals. |
| 7 | Logs/alerts; rollback plan | PASS | Spec says no logs (AC-16); errors are one line. Nothing is installed or stored; rollback = delete the folder, or `git revert`. Bank files are never modified (AC-15 test). |
| 8 | Docs, ADRs, CHANGELOG | FAIL (see B1, B2) | README exists and the example command works. `docs/STATUS.md` does not exist (protocol rule 7). No CHANGELOG. No ADRs (none needed). |
| 9 | Version / squash message | N/A | No version convention for a personal script; no package metadata. Suggested squash title: "feat: Receipt Tally CLI - monthly bank CSV summary". |
| S1 | Script: dry-run verified on real data | PASS | Default run (no `--out`) writes nothing. `git status` clean after runs. Not tried on a real bank export, only the shipped examples. |
| S2 | Script: backup/undo path | PASS | Tool is read-only on input; it only writes the single `--out` file, which never overwrites without `--force` and refuses to overwrite the bank file or config. |
| S3 | Script: README setup + examples | PARTIAL (see G1, G2) | Good plain-language README, both config samples shown. |
| S4 | Script: secrets documented / failure alerts | N/A | No secrets; runs on demand, not unattended. |

## [RELEASE-BLOCKER] items
- **B1** Review finding 12 (AC-17) is neither fixed nor tracked. Reproduced: a CSV amount cell containing ESC (`ESC[1m1.00`) makes the tool print the raw escape byte in `error: no usable rows ... bad amount '^[[1m1.00'` (same for the `line N: bad date/amount '...'` lines). Spec AC-17 says no ANSI codes in output. Review-2 allowed "fix now or note in docs/STATUS.md"; neither happened. Fix: pass the echoed cell text through the same control-character cleaning used for descriptions (and cap its length), add a test. Or, if the owner knowingly accepts it, record that in STATUS.md.
- **B2** `docs/STATUS.md` is missing (protocol rule 7; also review-2 asks to note open items there). Create it with: what shipped, open items (finding 12 if not fixed, nits 11 and 13), how to run.

## Notable gaps (not blockers)
- G1 README says "Check it works: `python -m pytest tests`", but pytest is not stdlib and may not be installed for Sam. Use `python -m unittest discover -s tests`.
- G2 README says Python 3.11+ is needed (`tomllib`). Not verified what an older Python shows (likely a traceback on import). Only Python 3.13 was available here.
- G3 `.50` and `5.` amounts are skipped as bad rows (loud, not wrong). Review nits 11 (non-ASCII digits accepted) is harmless.
- G4 Not tried against a real bank export; layout assumptions come from the two fixtures.

**Risk:** low - read-only on the bank file, no network, stdlib only; worst case is a skipped row, which is reported loudly, never a wrong total.
**Rollback:** delete the folder (or `git revert`); nothing else was installed or changed.
**Verdict:** BLOCKED (see B1, B2). Both are small. Re-run the full checklist after the developer's fix; then RELEASE-READY is expected.
