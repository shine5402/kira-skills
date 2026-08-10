#!/usr/bin/env python3
"""PreToolUse hook: block `@copilot` bot @-mentions in gh/git command text.

Writing `@copilot` (or any bot @-mention) into a PR body, PR/issue comment, review
reply, or commit message does NOT request a Copilot code review — it posts under the
human user's identity and makes GitHub spawn a Copilot *agent coding session* on
their account. That is not ours to initiate on the user's behalf.

The legitimate way to (re-)request a Copilot review is the reviewer mechanism:
  gh pr edit <PR#> --add-reviewer @copilot
so `--add-reviewer`/`--reviewer @copilot` is allowed and stripped before the check.
Any other `@copilot` left in a gh command, or in a `git commit`/`git tag` message,
is blocked.

See skill: copilot-review (the "@copilot in free text" prohibition).
"""
import json
import re
import sys

try:
    payload = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(0)

command = (payload.get("tool_input") or {}).get("command", "") or ""
if not command:
    sys.exit(0)

# Only police GitHub-posting commands: a real `gh ...` or `git commit`/`git tag`
# invocation. Match on the *executable* — the first token of each pipeline segment,
# after any leading `VAR=val` assignments — so a command that merely mentions these
# strings inside a quoted argument (e.g. `echo "gh pr comment ... @copilot"`, a
# `python -c` snippet, or a here-doc) is not policed.
#
# We deliberately do NOT tokenize the whole command to locate the @copilot: once a
# segment IS a gh/git-message invocation, we scan the entire command for @copilot.
# A precise per-arg parse would let a body containing shell metacharacters (`;`/`|`)
# split and slip an @copilot through — and for a safety guard, over-blocking is the
# safe failure mode, while a false negative is the exact bypass we're preventing.
def segment_is_posting_command(segment):
    segment = re.sub(r"^(?:[A-Za-z_]\w*=\S*\s+)+", "", segment.strip())
    return bool(
        re.match(r"gh\b", segment)
        or re.match(r"git\s+(?:commit|tag)\b", segment)
    )

segments = re.split(r"[\n;|&]+", command)
if not any(segment_is_posting_command(s) for s in segments):
    sys.exit(0)
if not re.search(r"@copilot", command, re.IGNORECASE):
    sys.exit(0)

# Strip the ALLOWED reviewer-flag usages (the value may legitimately be @copilot),
# then see whether any @copilot @-mention still remains in the command text.
stripped = re.sub(
    r"--(?:add-reviewer|reviewer)(?:=|\s+)\S+",
    "",
    command,
    flags=re.IGNORECASE,
)

if re.search(r"@copilot", stripped, re.IGNORECASE):
    sys.stderr.write(
        "Blocked by hook (block-copilot-mention): `@copilot` @-mention in a gh/git\n"
        "command body or message.\n"
        "\n"
        "Why: `@copilot` in a PR body, comment, review reply, or commit message does\n"
        "NOT trigger a Copilot review. It posts under the human user's identity and\n"
        "makes GitHub spawn a Copilot AGENT CODING SESSION on their account — which is\n"
        "not yours to initiate on their behalf.\n"
        "\n"
        "To (re-)request a Copilot review, use the reviewer mechanism instead:\n"
        "  gh pr edit <PR#> --add-reviewer @copilot\n"
        "\n"
        "In any free text (PR/issue body, comments, commit messages), refer to it as\n"
        '"Copilot" in prose — never @-mention the bot.\n'
        "\n"
        "See skill: copilot-review\n"
    )
    sys.exit(2)

sys.exit(0)
