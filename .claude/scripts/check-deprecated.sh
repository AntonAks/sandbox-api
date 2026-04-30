#!/usr/bin/env bash
# PostToolUse hook: scan a just-edited .py file for deprecated library patterns.
# Reads Claude Code hook JSON on stdin, exits 2 with stderr feedback if any pattern matches.
#
# Patterns target Pydantic v1 → v2 and SQLAlchemy 1.x → 2.0 migrations, plus a few
# style rules from docs/rules/code_rules.md that are easy to grep for.
#
# Add a pattern: append a `check '<regex>' '<message>'` line below.

set -eu

f=$(jq -r '.tool_response.filePath // .tool_input.file_path // empty')
case "$f" in
  *.py) ;;
  *) exit 0 ;;
esac

[ -f "$f" ] || exit 0

issues=""

check() {
  pattern="$1"
  message="$2"
  if grep -qE "$pattern" "$f"; then
    issues="${issues}  • ${message}
"
  fi
}

# Pydantic v1 → v2
check 'from pydantic import.*BaseSettings' "Pydantic v1: BaseSettings moved to the 'pydantic_settings' package."
check 'from pydantic import.*\bvalidator\b' "Pydantic v1: '@validator' is deprecated; use '@field_validator'."
check 'from pydantic import.*\broot_validator\b' "Pydantic v1: '@root_validator' is deprecated; use '@model_validator'."

# SQLAlchemy 1.x → 2.0
check 'from sqlalchemy\.ext\.declarative import' "SQLAlchemy 1.x: import 'DeclarativeBase' from 'sqlalchemy.orm' instead."
check '\.query\(' "SQLAlchemy 1.x: '.query()' is deprecated; use 'select()' with 'session.execute(...)'."
check '\buselist[[:space:]]*=' "SQLAlchemy: 'uselist=' is unnecessary with proper Mapped[\"...\"] / Mapped[list[\"...\"]] typing."

# Project rules (from docs/rules/code_rules.md)
check '^\s*#\s*Step\s*[0-9]' "Code style: 'Step N' comments are not allowed."

if [ -n "$issues" ]; then
  printf 'Deprecated/forbidden patterns detected in %s:\n%s\nFix these before continuing.\n' "$f" "$issues" >&2
  exit 2
fi

exit 0
