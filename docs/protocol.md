# Collaboration protocol

The rules that let separate agents work as one team. Every agent definition follows this file.

## 1. State lives in the repo
| What | Where |
|---|---|
| Specs | `docs/specs/*.md` |
| Architecture + status | `docs/architecture/` (`status.md`: `DRAFT / IN REVIEW (round N) / APPROVED`) |
| Architecture reviews | `docs/architecture/reviews/review-N.md` |
| Decisions | `docs/adr/NNNN-*.md` |
| Onboarding evidence | `docs/onboarding-report.md` |
| Live status board | `docs/STATUS.md` |
| Code review state | PR comments + `agent:*` labels |
| Knobs | `.autocraft/config.yml` |

## 2. Handoff block
Every agent ends its work with:

```
HANDOFF
From: <agent>            To: <agent | human>
Status: DONE | NEEDS-CHANGES | BLOCKED | NEEDS-HUMAN
Summary: <2-4 lines>
Artifacts: <paths / PR links>
Open items: <numbered list, or "none">
Next: <what the receiver should do>
```

## 3. Review rules (design reviews and PR reviews)
**Severity prefixes**

| Tag | Meaning | Blocks approval? |
|---|---|---|
| `[BLOCKER]` | wrong, insecure, or breaks things | yes |
| `[MAJOR]` | significant quality, test or design gap | yes |
| `[MINOR]` | should fix; may be deferred with a tracked issue | no (if tracked) |
| `[NIT]` | optional taste | no |
| `[QUESTION]` | needs an answer before judging | until answered |
| `[RELEASE-BLOCKER]` | (release-gatekeeper) would hurt in production | yes |

**Author duties:** answer *every* comment (`Fixed in <sha>` / `Not changing because …`); never resolve the reviewer's threads; re-run tests; re-request review.
**Reviewer duties:** re-verify *each* earlier comment on every round; approve only with zero open BLOCKER/MAJOR and green CI on the latest commit; accept sound pushback; stay specific and kind.
**Round limit:** `max_review_rounds` (default 3). Beyond it: label `needs-human`, summarise both positions neutrally, wait for the human.

## 4. PR label state machine
```
agent:ready ─► agent:in-progress ─► agent:needs-review ─► agent:approved ─► agent:release-ready ─► (human merges)
                                         ▲    │                 │
                                         │    ▼                 │ (gaps found)
                                    agent:changes-requested ◄───┘
anything stuck ─► needs-human
```
Exactly one `agent:*` state label on a PR at a time. Whoever moves the PR forward swaps the label.

## 5. Who may do what
| Action | Agents | Human |
|---|---|---|
| Commit to feature branches, open PRs | ✅ developer | ✅ |
| Review, label, comment | ✅ reviewer, gatekeeper | ✅ |
| Approve architecture | ✅ principal-engineer (+ human at L1/L2) | ✅ |
| **Approve & merge PRs into `main`** | ❌ never | ✅ always |
| Change branch protection / visibility / delete repo | ❌ never without explicit ask | ✅ |
| Create the repo | ✅ after human confirmation | ✅ |

Branch protection enforces the human gate: ≥1 approving review is required, and agents run with your credentials, so the *approval click is yours*.

## 6. Autonomy levels (`.autocraft/config.yml → autonomy_level`)
| Level | You approve | Best for |
|---|---|---|
| **L1 Guided** | every phase boundary (spec, architecture, onboarding, each PR before review) | learning the process |
| **L2 Balanced** (default) | architecture, and every merge | most projects |
| **L3 Hands-off** | merges/releases only | trusted, low-risk work |

Agents never go below "human merges", at any level.

## 7. Definitions
**Definition of Ready (task):** clear acceptance criteria · dependencies merged · test expectations stated · small enough for one PR.
**Definition of Done (PR):** acceptance criteria met · unit + integration tests added and passing · CI green on latest commit · reviewer `VERDICT: APPROVED` · pre-release check passed · docs/changelog updated · human merged.

## 8. Parallelism
Run multiple developers only on independent tasks (see `Depends on` in the work breakdown) touching different files, each in its own branch/worktree. Cap: `max_parallel_developers`.

## 9. Safety rules for all agents
No secrets in code, logs or comments · never disable tests/checks/protections to get green · ask before destructive or outward-facing actions · be honest about what was verified vs assumed.
