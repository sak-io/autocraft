#!/usr/bin/env python3
"""Claude Code PreToolUse hook (matcher: Bash). Blocks production deploys until a human sets RELEASE_APPROVAL.
Exit 2 blocks the command and shows the message to the agent; exit 0 allows it. Edit the keywords to match your pipeline."""
import json
import os
import sys

try:
    cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command", "")
except Exception:
    sys.exit(0)
low = cmd.lower()
if "deploy" in low and ("production" in low or "prod " in low + " ") and not os.environ.get("RELEASE_APPROVAL"):
    sys.stderr.write("Production deploys need a release authorization. Ask the owner to approve, then set RELEASE_APPROVAL (a change ticket or release-manager sign-off) for this run.\n")
    sys.exit(2)
sys.exit(0)
