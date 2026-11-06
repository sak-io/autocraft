# Agent evals

Regression tests for the agent configuration: `team-rules.md`, roles, the instruction files autocraft generates, and the guardrail hooks. When a model, a prompt or a rule changes, the suite says whether the agent still does the work to the same standard.

## Add a task
1. Pick a real task from recent work (or a production incident) with an outcome the team accepted.
2. Copy `example-eval.json` to `evals/<id>.json` in your repo. Fields:
   - `prompt`: what you would say to the agent.
   - `checks`: shell commands that must exit 0 afterwards (tests pass, lint clean, a forbidden file untouched, a required file present).
   - `tags`: optional (for example `incident`, `security`).
3. Aim for 20 to 50 tasks. Retire cases that every model now passes; add one for every incident.

## Run it (any tool)
```bash
AUTOCRAFT_EVAL_AGENT='claude -p {prompt}' python3 .autocraft/templates/evals/run_evals.py        # Claude Code
AUTOCRAFT_EVAL_AGENT='gemini -p {prompt}' python3 .autocraft/templates/evals/run_evals.py        # Gemini CLI
AUTOCRAFT_EVAL_AGENT='./my-agent.sh {prompt}' python3 .autocraft/templates/evals/run_evals.py    # anything that can take a prompt non-interactively
```
`{prompt}` is replaced with the quoted prompt. Each task runs in a fresh git worktree of `HEAD`, so a failed task cannot dirty your checkout. Set `EVAL_MIN_PASS_RATE` (default `0.8`) to the threshold that fails the run, and make the run a required check for changes to the rules and hooks (see `.autocraft/templates/github/workflows/agent-evals.yml`; it is off until you copy it and add an API key secret).

Runs cost model calls, so run them on a schedule and on configuration changes rather than on every push. The evals are a floor, not a proof: a pass means the agent met the checks you wrote.
