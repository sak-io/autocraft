# Brief for requirements-analyst (token_mode lean: <=35k tokens, <=15 tool calls, report <=15 lines)
Read docs/idea.md and .claude/agents/requirements-analyst.md only. Do not explore elsewhere.
Write ONE file docs/specs/receipt-tally.md (<=120 lines) containing, in this order:
1. Goal + non-goals (3-5 lines). Non-goals must include: no network access, no GUI, no editing the bank files.
2. Numbered acceptance criteria AC-1.. (each testable, Given/When/Then in one line). Cover: two CSV layouts (configurable column mapping in the rules/config file), money as exact decimals (no floats), category rules (first match wins, case-insensitive substring, plus an 'Uncategorised' bucket), month summary (per category totals, income vs spending, top 5 largest spends, uncategorised count), bad input (missing file, bad row -> report line number, continue), dry-run default prints only to screen, `--out` writes a file only when asked, idempotent/deterministic output, no network (test enforces).
3. Non-functional goals table: privacy (no network, no logs of descriptions), simplicity (stdlib only, one package, <=400 lines of code), token efficiency (built within a stated budget), accessibility of output (plain text, readable without colour).
4. Design in <=25 lines: module list with one-line purposes, data shapes, config file format example (rules.txt / config.toml sample), error handling. Keep it as simple as safely possible.
5. Task list: max 3 tasks (T1 core parse+rules+summary, T2 CLI + errors + docs, T3 optional) each with the AC numbers it covers and a `verify:` command.
6. Open questions: at most 3, each with a recommended default (do not block on them).
Reply with <=15 lines.
