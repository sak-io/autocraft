---
id: release-check
needs: [release-gatekeeper]
description: Final pre-release gate on an approved PR. The release-gatekeeper finds remaining gaps, developers fix them, and when clean the PR is labelled release-ready and the human owner is notified.
---


# /release-check [PR number]

Precondition: PR labelled `agent:approved`, CI green.

```
loop (max_review_rounds):
  Invoke `release-gatekeeper` on the PR.
    all clear  -> label agent:release-ready, notify human, exit
    gaps found -> Invoke the builder role to resolve each [RELEASE-BLOCKER], then repeat
```

On success, tell the human, in plain language:
- **What ships** (one sentence), **risk** (low/med/high and why), **rollback plan**.
- **Your move:** open the PR, read the checklist comment, and if you're happy, approve and merge it. (Branch protection requires your approval.)

**Last step, before telling the human to merge: map the diff.** Run `python3 .autocraft/framework/bin/autocraft review-map` (free; no model tokens). If `guide_recommended` is true in `--json`, run `/review-guide` (a fresh `pr-reviewer` writes `docs/review-guide.md`; every reference is script-verified) and link it at the top of the pull request description. If `split_recommended` is true (the diff exceeds twice the thresholds), also **offer** the owner the stacked-PR split (`review-map --slices`) and do it only after an explicit yes. See `docs/reviewing-large-prs.md`.

If the loop limit is hit, label `needs-human` and explain what is unresolved.
