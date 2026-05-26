#!/usr/bin/env python3
"""PreToolUse Bash hook: block destructive shell commands.

Extend BLOCKED with new substring patterns as needed.
"""

import json
import sys

BLOCKED = (
    "rm -rf",
    "rm -fr",
    "rm -Rf",
    "rm -fR",
    "rm --recursive --force",
    "rm --force --recursive",
    "mkfs",
    "dd if=",
    ":(){ :|:& };:",
)

cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "")

for pattern in BLOCKED:
    if pattern in cmd:
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        f"Blocked destructive pattern: {pattern!r}. "
                        "Run it manually if you really mean it."
                    ),
                }
            },
            sys.stdout,
        )
        break
