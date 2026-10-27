# Guardrails

autocraft lets agents move quickly inside limits you control. This page lists the guardrails that exist, says **who enforces each one**, and is open about the gaps.

Two kinds of guardrail are mixed together in any agent framework, and it matters which is which:

- **Instructed**: written into the role files and the [protocol](protocol.md); agents follow them and reviewers check them. They work well in practice but nothing stops an agent that ignores them.
- **Enforced**: a tool refuses the action regardless of what the agent does (a CI check, GitHub branch protection, the Claude Code permission list, a script).

This list comes from reading the protocol, roles, CLI and templates in this repository. It is not a security audit.

## In place

### Human control
| Guardrail | Detail | Kind |
|---|---|---|
| Humans merge | Agents never approve or merge into `main`, at any autonomy level ([protocol §5](protocol.md)). A developer never merges its own PR or bypasses CI or branch protection (`roles/developer.md`). The release gatekeeper cannot edit code, merge or approve (`roles/release-gatekeeper.md`). | Instructed. **Enforced** if branch protection is on. |
| Branch protection | `templates/branch-protection.json`, applied by `scripts/onboard-repo.sh`: one approving review, required `ci` check, up-to-date branch, admins included, no force-push, no deletion, linear history, conversations resolved. | Enforced by GitHub (opt-in). |
| Gates you choose | `autonomy_level` 1-3 sets which phases need your approval: spec, plan, release. Money, legal and account decisions always come to you ([protocol §6](protocol.md)). | Instructed |
| Quiet git by default | `git_mode: session-branch` keeps work on the session branch; no extra remote branches or pull requests unless you ask ([protocol §14](protocol.md)). | Instructed |

### Review and quality
| Guardrail | Detail | Kind |
|---|---|---|
| Independent review | A different agent, in a fresh session that sees only the spec, diff and protocol, re-runs the tests itself ([protocol §3, §12](protocol.md)). | Instructed |
| Severity tags and approval rules | `[BLOCKER]`, `[MAJOR]`, `[MINOR]`, `[NIT]`, `[QUESTION]`, `[RELEASE-BLOCKER]`; approval only with zero open BLOCKER/MAJOR and green CI; the reviewer re-verifies every earlier comment each round. | Instructed |
| Round limit and escalation | After `max_review_rounds` (default 3; 2 with `--token-saver`) the work is labelled `needs-human` and both positions are summarised neutrally. | Instructed |
| Definition of Ready / Done | Clear acceptance criteria before building; tests, green CI, reviewer approval, pre-release check and human merge before done ([protocol §7](protocol.md)). | Instructed |
| Parallelism cap | `max_parallel_developers`; only independent tasks, each in its own worktree ([protocol §8](protocol.md)). | Instructed |
| Team sanity check | `autocraft doctor` reports a team with no independent reviewer or no builder, unknown archetypes, capabilities or tools, missing source documents and missing or drifted generated files. | Enforced by script |
| Big-diff reviewability | `autocraft review-map` (no model tokens) classifies a diff and recommends a reviewer's guide; the guide must say what has **not** been independently verified and `--verify-guide` checks its `path:line` references ([reviewing large PRs](reviewing-large-prs.md)). | Script plus instruction |

### Safety and security
| Guardrail | Detail | Kind |
|---|---|---|
| Safety rules for all agents | No secrets in code, logs or comments; never disable tests, checks or protections to get green; ask before destructive or outward-facing actions; be honest about what was verified versus assumed ([protocol §9](protocol.md)). | Instructed |
| Security auditor | Triages dependency, code and secret scans; cannot modify product code; may not dismiss an alert without written justification; a leaked secret means "rotate now" (`roles/security-auditor.md`). | Instructed |
| CI templates | Language CI for 8 stacks with a required status check named `ci`. Dependency-audit steps for .NET, Go, Java, Node, Python and Rust (Flutter relies on Dependabot). CodeQL, Dependabot, CODEOWNERS, PR template and SECURITY.md templates. | Enforced by CI once installed (`autocraft github`) |
| Secret scanning | A weekly scheduled gitleaks and dependency scan; GitHub secret scanning and push protection turned on by `scripts/onboard-repo.sh`. | Enforced by CI/GitHub once installed |
| Safe defaults per domain | Capability profiles (authentication, payments, database, email, uploads, search, secrets, hosting, privacy and more) with safe defaults and must-test lists that architects, developers, reviewers and auditors check. | Instructed |
| Prompt-injection defence for AI products | The `ai-engineer` role treats retrieved text and user input as untrusted data, and the `ai-product` team includes an injection red-team. | Instructed (AI-product teams only) |
| Command permissions (Claude Code) | The generated `.claude/settings.json` pre-approves a short list of routine git, test and autocraft commands instead of everything. | Enforced by Claude Code |

### Cost controls
| Guardrail | Detail | Kind |
|---|---|---|
| Lean mode | `token_mode: lean` tells every role to work from briefs, run cheap automated checks first, keep reports short and match review depth to risk ([protocol §15](protocol.md)). Quality gates do not change. | Instructed |
| Token saver | `autocraft init --token-saver`: mid-tier models for reviewer, QA, auditor and analyst, 2 review rounds, 2 parallel developers. An explicit `--role-model` still wins. | Configuration |
| Per-run budgets | A stated tool-call or token budget in each brief; the agent stops and reports what remains. Measuring tokens per run (for example `agent-runs.csv` in the examples) is a convention. | Instructed |

### Framework integrity
| Guardrail | Detail | Kind |
|---|---|---|
| Validation in CI | `scripts/validate.sh` checks structure and cross-references, generates all nine tool exports, parses YAML/TOML, exercises custom teams and per-role models, and confirms `sync` is idempotent. It runs on every pull request. | Enforced by CI |
| Generated files are marked | Exports are marked `linguist-generated`, the install is its own commit (`init --commit`), and git hooks are honoured, never bypassed. `init --commit` never pushes. | Script |

## Known gaps

These are real limits today. Each has a suggested next step.

1. **Most guardrails are instructions, not enforcement.** Hard enforcement exists only where branch protection, CI or the Claude Code permission list are installed. Other tools receive the same written rules but no permission list. *Next:* say so per tool in the tool pages, and generate each tool's own permission or rules file where it has one.
2. **Branch protection is opt-in and best-effort.** It is applied only by `scripts/onboard-repo.sh`, which warns and carries on when a control is not available for the repository (this depends on the GitHub plan and repository type). Without it, "never merge to `main`" rests on instructions. *Next:* make `doctor` check that protection is on and report clearly when it cannot be.
3. **The generated permission list has no deny rules and some broad prefixes.** It pre-approves `git push -u origin:*` (any branch, not only the session branch), `git checkout:*`, `git merge:*` and `npm run:*` (any script in the project's `package.json`). Nothing blocks force-pushes, pushing to `main`, `rm -rf`, or reading `.env` files. *Next:* generate `deny` entries and narrow the allow list. See [raising the floor](#raising-the-floor-today) for a manual version.
4. **Cost budgets are advisory.** Token and tool-call budgets are written into prompts; the framework has no hard stop that ends a run at a limit. *Next:* wire in the AI tool's own spend or turn limit where it has one, and log input, output and cache tokens per run so budgets can be checked afterwards.
5. **Handoff blocks are not machine-checked.** The format is fixed, but nothing validates the required fields, the status value or that the listed artifact paths exist. A hand-back that just said "pending" has happened in practice. *Next:* a handoff lint in `doctor` (tracked in [issue #18](https://github.com/sak-io/autocraft/issues/18)) and a constraints file that every task brief must reference.
6. **Loop limits cover review rounds only.** There is no documented cap on QA-to-fix cycles or on repeated CI-fix attempts. *Next:* add a cap and the same `needs-human` escalation.
7. **Independence means separate context and role, not a different model.** A reviewer from the same model family can share blind spots with the builder. `role_models` can pick a different tier, but cross-vendor review is not built in. *Next:* document how to run the reviewer on a different tool, and measure what independent review catches against a single-agent baseline.
8. **Secret scanning is not a per-pull-request gate by default.** The gitleaks workflow is scheduled weekly. GitHub push protection helps if it is enabled. *Next:* add a secret scan to the CI templates that runs on every pull request.
9. **Untrusted input is covered only for AI products.** No general rule tells every role to treat issue text, web pages or instructions embedded in owner documents as data, not commands. *Next:* add one line to the protocol's safety rules.
10. **No automatic audit trail.** Handoff files, review files and the optional `agent-runs.csv` are conventions, not a generated, tamper-evident log of what each agent did. *Next:* a small run log written by the CLI or by hooks.
11. **Only the Claude path has been exercised end to end.** Exports for the other tools follow vendors' documented formats but have not been run in those products.

## Raising the floor today

You can close several gaps yourself without waiting for framework changes:

- Turn on branch protection and secret scanning: run `scripts/onboard-repo.sh <owner/name> --lang <lang>` (use `--dry-run` first), then check the repository settings, because some controls depend on your GitHub plan.
- Keep `autonomy_level` at 1 or 2 until you trust the team on your kind of project.
- In Claude Code, add deny rules to `.claude/settings.json` (`sync` never overwrites it). Example, to be checked against your tool's current permission syntax:

  ```json
  { "permissions": { "deny": ["Bash(git push --force:*)", "Bash(git push origin main:*)", "Bash(rm -rf:*)", "Read(./.env)"] } }
  ```

- Use your AI tool's own spend or turn limit if it has one, in addition to the budget in the brief.
- Read every review file and handoff for the steps that matter (security, money, data loss) before you merge.
