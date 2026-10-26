# Bootstrap prompt — let an agent set up your agent team

Use this when you **don't know how to configure agents**. Open your AI tool in an empty (or existing) project folder and paste one of these. The agent becomes your *Team Builder*: it asks about your idea and tool, then installs and explains the right team.

## For agentic tools with a terminal (Claude Code, Cursor, Copilot agent mode, Gemini CLI, Cline, Windsurf, Codex …)
```text
I want to build software with a team of AI agents, but I don't know how to set that up.
Please act as the "team-builder" from https://github.com/sak-io/autocraft :
1. Clone it into a temporary folder (outside my project) and read roles/team-builder.md and workflows/build-my-team.md.
2. Interview me in plain language (my idea, which AI tool I'm using, how experienced I am).
3. Recommend a lean team and a full team for my kind of software, explaining each role in one line.
4. After I confirm, install it with: python3 <clone>/bin/autocraft init . --tool <my tool> --team ... --archetype ...
5. Tell me exactly how to start using it in my tool. Don't ask me to choose technologies; recommend defaults.
```

## You already have a product concept / technical plan in a repo (Claude app Code session, or any agentic tool)
Easiest: add the small `CLAUDE.md` pointer described in [kickoff-existing-docs.md](kickoff-existing-docs.md), then just say *"Kick off this project with autocraft."* Or paste this instead:
```text
This repository contains my product documents (list them: e.g. docs/product-concept.md and docs/technical-plan.md). Build the product with an autocraft agent team:
1. Get https://github.com/sak-io/autocraft into this session (clone it to /tmp/autocraft; use the add_repo tool if it is not in scope).
2. Act as the team-builder (/tmp/autocraft/roles/team-builder.md): read my documents, tell me in plain words what you understood, recommend a lean or full team, ask me at most 4 questions.
3. After I confirm: python3 /tmp/autocraft/bin/autocraft init . --tool claude-code --sources <my documents> --git-mode session-branch --team ... --commit ; push this session's branch. (--commit makes the installation its own commit, separate from product work.)
4. Then follow /tmp/autocraft/workflows/kickoff.md: spec from my documents (flag gaps and contradictions), validate my technical plan, ask for my approvals, then build with parallel developers, independent reviewers, QA and a security check. Do not open a pull request or merge unless I ask.
```

## For chat-only use (Claude app, ChatGPT, Gemini app …)
```text
I want to build software with a team of AI roles inside this conversation. Act as a Team Lead who plays these roles one at a time,
announcing "Acting as: <role>" each time: requirements-analyst (turns my idea into a spec with acceptance criteria), architect
(designs it), reviewer (strictly reviews anything built, as if someone else wrote it), and security-auditor.
Ask me up to 4 plain-language questions about my idea first, with a default for each. Never skip review. Keep a STATUS block at the end of each
reply (phase, done, next, what I need to do). Explain any jargon in a few words. I make the final decisions.
```
(For a proper setup with files and tests, switch to an agentic tool later and use the first prompt — your spec carries over.)

## For Claude on the web / phone (Claude Code sessions)
Attach your repository to the session, then paste the first prompt. The files the Team Builder creates are committed to your repo and load automatically in every future session.
