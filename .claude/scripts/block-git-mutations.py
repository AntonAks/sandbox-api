#!/usr/bin/env python3
"""PreToolUse Bash hook: block git push/commit/reset (reserved for the user)."""

import json
import sys

BLOCKED = ("git push", "git commit", "git reset")
REASON = "git push/commit/reset are reserved for the user — run them manually."

cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "")

if any(p in cmd for p in BLOCKED):
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": REASON,
            }
        },
        sys.stdout,
    )
