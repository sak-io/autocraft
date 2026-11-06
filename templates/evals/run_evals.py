#!/usr/bin/env python3
"""Tool-neutral eval runner. Runs each evals/*.json task with the agent command in AUTOCRAFT_EVAL_AGENT
(use {prompt} where the quoted prompt goes), inside a fresh git worktree, then runs the task's checks.
Exit 1 when the pass rate is below EVAL_MIN_PASS_RATE (default 0.8). Standard library only."""
import glob
import json
import os
import shlex
import subprocess
import sys
import tempfile


def run(cmd, cwd, timeout):
    return subprocess.run(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)


def main():
    agent = os.environ.get("AUTOCRAFT_EVAL_AGENT", "")
    if "{prompt}" not in agent:
        sys.exit("set AUTOCRAFT_EVAL_AGENT to the command that runs your agent non-interactively, with {prompt} where the prompt goes")
    threshold = float(os.environ.get("EVAL_MIN_PASS_RATE", "0.8"))
    timeout = int(os.environ.get("EVAL_TIMEOUT", "900"))
    pattern = os.environ.get("EVAL_GLOB", "evals/*.json")
    root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()
    tasks = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(root, pattern)))]
    if not tasks:
        sys.exit(f"no eval tasks match {pattern}")
    passed, results = 0, []
    for t in tasks:
        wt = tempfile.mkdtemp(prefix="eval-")
        subprocess.check_call(["git", "worktree", "add", "--detach", "-q", wt, "HEAD"], cwd=root)
        try:
            try:
                a = run(agent.replace("{prompt}", shlex.quote(t["prompt"])), wt, timeout)
                ok = a.returncode == 0
                failed = [] if ok else ["agent exited %d" % a.returncode]
            except subprocess.TimeoutExpired:
                ok, failed = False, ["agent timed out"]
            if ok:
                for c in t.get("checks", []):
                    if run(c, wt, timeout).returncode != 0:
                        ok = False
                        failed.append(c)
        finally:
            subprocess.call(["git", "worktree", "remove", "--force", wt], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        passed += ok
        results.append({"id": t.get("id", "?"), "passed": ok, "failed": failed, "tags": t.get("tags", [])})
        print(("PASS " if ok else "FAIL ") + t.get("id", "?") + ("" if ok else "  <- " + "; ".join(failed)))
    rate = passed / len(tasks)
    print(f"pass rate {rate:.2f} ({passed}/{len(tasks)}), threshold {threshold:.2f}")
    if os.environ.get("EVAL_RESULTS"):
        json.dump({"pass_rate": rate, "results": results}, open(os.environ["EVAL_RESULTS"], "w"), indent=1)
    sys.exit(0 if rate >= threshold else 1)


if __name__ == "__main__":
    main()
