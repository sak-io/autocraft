# Getting started (no experience required)

This guide takes you from "I have an idea" to "I have reviewed, tested code waiting for my approval".

## What you need (15 minutes, once)
1. **A GitHub account** — https://github.com/signup
2. **Claude Code** — follow the install steps at https://claude.com/claude-code
3. **GitHub CLI** (`gh`) — https://cli.github.com, then run `gh auth login` and follow the prompts
4. **git** and **jq** installed (`git --version`, `jq --version` should print a version)
5. A paid GitHub plan **or** a public repo if you want branch protection to be enforced on GitHub (see *Plans* below)

## Step 1 – Install the agent team into a project folder
```bash
git clone https://github.com/sak-io/autocraft.git
bash autocraft/scripts/install.sh ~/code/my-first-app --lang node   # or python, go
cd ~/code/my-first-app
claude
```
Pick `--lang` for the technology you'd like the project to use. Not sure? `node` (JavaScript/TypeScript) or `python` are both fine.

## Step 2 – Say `/start`
The guide asks up to five short questions (every one has a default — you can just say "default"). It will ask how involved you want to be:

- **L1 Guided** — it checks with you after every phase. Choose this to learn.
- **L2 Balanced** *(default)* — you approve the design and every merge.
- **L3 Hands-off** — you only approve merges.

## Step 3 – Watch the phases
| Phase | What happens | What you do |
|---|---|---|
| Spec | Analyst writes what the app must do | Answer a few questions; read the summary |
| Architecture | Architect designs; Principal Engineer challenges; they iterate | Read the plain-language summary; approve |
| Onboarding | A private GitHub repo is created with protection, tests and security scans | Confirm when asked; read the ✅/⚠️ report |
| Build | Developer agents code + test; reviewer agent reviews; they iterate | Skim PR summaries; answer questions if escalated |
| Release check | Last gap check; PR marked **release-ready** | **Open the PR, read it, approve, and click Merge** |

## Step 4 – Merge your first PR
When you hear "release-ready": open the PR link → read the *What & why* and the *Pre-release check* comment → check CI is green → **Review changes → Approve → Squash and merge**. That's it; that's the human gate.

## Everyday commands
`/status` (where are we?) · `/build-feature` (next task) · `/review-pr 12` · `/release-check` · `/security-scan` (weekly)

## Plans and limits (honest note)
GitHub's *branch protection* and some security scanners on **private** repos require a paid plan (Pro/Team). On the free plan the onboarder will tell you ⚠️ which protections it couldn't enable. You can still work safely: don't push to `main` directly, and rely on the agents' PR flow.

## When something goes wrong
- *"gh: not logged in"* → `gh auth login`
- *Agents keep disagreeing* → after 3 rounds they stop and ask you; read both positions and decide; the decision is saved as an ADR.
- *CI is red* → ask `/status`; the developer agent fixes CI failures it caused. Never ask an agent to "just skip the test".
- *I don't understand a word* → [glossary](glossary.md).

## Rules of thumb
1. Keep tasks small — small PRs get better reviews.
2. Read the summaries; you're the owner.
3. Never paste secrets (passwords, API keys) into chat or code.
4. If the agents say something is risky, believe them and ask why.
