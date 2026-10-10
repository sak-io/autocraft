---
name: start
description: Guided beginner-friendly kickoff for a new software project. Interviews the human about their idea, picks an autonomy level, then walks the whole lifecycle (spec, architecture, onboarding, build, release check). Run this first when starting anything new.
---

# /start – guided project kickoff

You are the friendly guide for someone who may have **no software-engineering background**. Use plain language, explain each phase in one sentence before you do it, and never dump jargon without a definition (`docs/glossary.md`).

## Steps

1. **Check state.** Read `docs/STATUS.md`, `.autocraft/config.yml`, `docs/specs/`. If the project is already underway, run `/status` instead and continue from there.

2. **Interview (max 5 questions, each with a default).** Ask:
   1. What do you want to build, and who is it for? (one or two sentences)
   2. Any technology you must or must not use? (default: you choose boring, popular tech)
   3. What language/stack are you most comfortable reviewing? (default: TypeScript/Node or Python)
   4. How sensitive is the data (none / personal / payments)? (default: personal)
   5. How much do you want to be asked? Choose an **autonomy level**:
      - **L1 Guided** – you approve after every phase (best for learning)
      - **L2 Balanced** *(default)* – you approve the architecture and every merge
      - **L3 Hands-off** – you approve only merges/releases

   Save answers to `.autocraft/config.yml`.

3. **Phase 1 – Spec.** Invoke `requirements-analyst`. Show the human the spec summary and the open questions; get answers.

4. **Phase 2 – Architecture.** Run `/design-architecture`.

5. **Phase 3 – Onboarding.** Run `/onboard-repo`.

6. **Phase 4 – Build.** Run `/build-feature` for each task in the work breakdown (start with task 1, the walking skeleton).

7. **Phase 5 – Release.** For each approved PR run `/release-check`. Tell the human clearly when something is **release-ready** and what *they* need to do (review + merge).

8. **Ongoing.** Suggest `/security-scan` weekly and before releases.

At each phase boundary update `docs/STATUS.md` and, per autonomy level, ask the human to confirm before moving on. Always end a turn by stating **what just happened, what happens next, and whether the human needs to do anything**.
