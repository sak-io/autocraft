#!/usr/bin/env python3
"""Shell gate for AI coding tools (Claude Code PreToolUse, Cursor beforeShellExecution, Gemini CLI BeforeTool).
Reads the hook's JSON on stdin, takes the shell command (`tool_input.command` or top-level `command`), and blocks
(exit 2, reason on stderr) production deploys until a human sets RELEASE_APPROVAL, and irreversible commands
(force-push, push to main/master, rm -rf). Exit 0 allows. Edit the patterns to match your pipeline."""
import json
import os
import re
import sys

try:
    data = json.load(sys.stdin)
    cmd = (data.get("tool_input") or {}).get("command") or data.get("command") or ""
except Exception:
    sys.exit(0)
low = cmd.lower()
IRREVERSIBLE = [r"\bgit\s+push\b.*(--force\b|\s-f\b|--force-with-lease)", r"\bgit\s+push\b.*\b(origin\s+)?(main|master)\b", r"\brm\s+-[a-z]*r[a-z]*f|\brm\s+-[a-z]*f[a-z]*r"]
if any(re.search(p, low) for p in IRREVERSIBLE):
    sys.stderr.write("Blocked: irreversible command (force-push, push to main/master, or rm -rf). Ask the owner to run it themselves.\n")
    sys.exit(2)
if "deploy" in low and ("production" in low or "prod " in low + " ") and not os.environ.get("RELEASE_APPROVAL"):
    sys.stderr.write("Production deploys need a release authorization. Ask the owner to approve, then set RELEASE_APPROVAL (a change ticket or release-manager sign-off) for this run.\n")
    sys.exit(2)
sys.exit(0)
