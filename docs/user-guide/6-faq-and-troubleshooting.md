# 6. FAQ and troubleshooting

## Understanding

**Do I need to know how to code?** No. You need to be able to describe what you want, read a plain-language summary, answer questions, and click merge. If a word is unfamiliar, `/explain` it or check the [glossary](../glossary.md).

**Can't I just use one agent?** For a throwaway script, yes. For anything you'll rely on, the team's value is *independent review, tests, and checkpoints*. A cheap compromise: the lean team (builder + separate reviewer).

**What does "independent" really mean?** The reviewer is a separate agent that sees the spec and the work, not the builder's reasoning. In tools without sub-agents you get the same effect by reviewing in a **new chat session**.

**Is it safe to let agents run commands?** They work inside your project folder (or a cloud container) and ask for approval for risky actions. They don't merge or release, they're told never to put secrets in code, and the security checker runs dependency, code, and secret scans. Treat the result the way you'd treat work from a capable new colleague: review the summaries, and don't ship regulated or safety-critical software without a qualified person.

**Which AI model/tool should I use?** Claude Code (terminal, or the Claude app's Code sessions) is the best-supported path today. Other tools get the same team in their native format, but see the status table in the [README](README.md).

**What does it cost?** autocraft is free; your AI tool's usage is what you pay for. More roles and review rounds use more. The worked example reports the number of agent runs for a small app so you can calibrate. Starting lean keeps usage down.

## Getting unstuck

**Nothing happens when I type `/start`.** The team isn't installed in this folder/session. Run `autocraft doctor` (or ask: *"Is the autocraft team installed here? Fix it."*). In the Claude app, make sure you selected the right repository when you started the session, and that the setup was committed.

**The commands exist in my terminal but not in my tool.** You exported for a different tool. `autocraft add-tool <your tool>`.

**"Unknown role / team / tool" error.** Names are exact. `autocraft list roles`, `list teams`, `list tools`.

**An agent says it can't find a file like `.autocraft/protocol.md`.** Re-run `autocraft sync`. If you cloned autocraft somewhere else, use that path for the CLI.

**The builder and reviewer keep going back and forth.** After 3 rounds they stop and ask you. Read both sides, decide, and tell them. If it happens often, your tasks may be too big — ask for smaller ones.

**It's doing too much / too little at once.** Say so. *"One task at a time and stop after each for me to check"* is a valid instruction; so is autonomy level 3 for the opposite.

**I got a wall of technical text.** Reply: `/explain` (it explains the last thing in plain language) or set `experience: beginner` in `.autocraft/config.yml` and `autocraft sync`.

**The checks (CI) are red.** Ask `/status`. The builder owns fixing failures it caused. Never ask an agent to "just skip the failing test" — they will decline and say why.

**I pasted a password/API key into the chat.** Say so immediately. The key must be **replaced** at its source (deleting a message doesn't undo exposure).

**I edited a generated file and my change vanished.** Generated files are overwritten by `autocraft sync`. Put your rules in `.autocraft/custom/` instead (see page 5). `autocraft doctor` tells you when it sees hand-edited generated files.

## Claude app specifics

**Do I need a computer?** Not for Path B (Code session). You need a GitHub account connected to Claude and an existing repository.

**I keep getting approval prompts.** In a Code session you can allow common commands (git, running tests, the autocraft CLI) for the session. In Claude Code you can also type `/fewer-permission-prompts` to build an allow-list from your recent activity.

**It said it can't open a pull request / push to a branch.** Cloud sessions work on the branch they were given and open a pull request only when you ask. Say: *"Open a pull request for this branch."*

**It used a different GitHub command than the guide says.** Cloud sessions have GitHub *tools* instead of the `gh` command. The agents should adapt; if one gets stuck, say *"use the GitHub tools for that"*.

**Where is my work if the session ends?** In your repository, on the session's branch. A new session on the same repo with `/status` picks it up.

## Tools other than Claude

**The rules aren't being applied in Cursor/Copilot/etc.** Run `autocraft doctor`, confirm the tool's files exist (see its page in [docs/tools](../tools/)), restart the tool, and check the vendor's current file-format docs — formats change. Tell us which tool and version (see [feedback](7-give-feedback.md)).

**My tool has no slash commands.** Say the workflow by name: *"Run the start workflow."* Same effect.

## Where to learn more

[Concepts](1-the-idea.md) · [Protocol](../protocol.md) (the exact rules agents follow) · [Orchestration patterns](../orchestration-patterns.md) · [Customizing](../customizing.md)
