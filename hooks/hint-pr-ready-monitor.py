#!/usr/bin/env python3
"""PreToolUse hook: on `gh pr ready`, remind that Copilot's review is now incoming.

Flipping a PR Draft -> Ready is the "please review" signal — it auto-requests
Copilot's review. Agents routinely flip and move on, then merge before the review
lands or without engaging its findings. This injects a short advisory (it does NOT
block) so the agent knows to monitor the PR and treat Copilot's review as a soft
merge gate. `--undo` (back to draft) is left alone.

See skill: copilot-review.
"""
import json
import re
import shlex
import sys

try:
    payload = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(0)

command = (payload.get("tool_input") or {}).get("command", "") or ""
if not command:
    sys.exit(0)


def command_segments(command):
    """Split `command` into pipeline segments as token lists, quote/escape-aware.

    Uses shlex (a real shell tokenizer) rather than regex so that separators or the
    trigger text appearing *inside* quotes — including escaped quotes like `\\"` — are
    part of a token and never mistaken for a real invocation. Each line is lexed
    independently; a line that can't be lexed (unbalanced quotes) is skipped, which
    for an advisory hook just means no nudge.
    """
    segments = []
    for line in command.split("\n"):
        try:
            lex = shlex.shlex(line, posix=True, punctuation_chars=";|&")
            lex.whitespace_split = True
            tokens = list(lex)
        except ValueError:
            continue
        cur = []
        for tok in tokens:
            if tok and all(c in ";|&" for c in tok):  # an operator run (; | || && &)
                segments.append(cur)
                cur = []
            else:
                cur.append(tok)
        segments.append(cur)
    return segments


def strip_assignments(tokens):
    """Drop leading `VAR=val` env-assignment tokens so `FOO=1 gh ...` still matches."""
    i = 0
    while i < len(tokens) and re.match(r"^[A-Za-z_]\w*=", tokens[i]):
        i += 1
    return tokens[i:]


def is_pr_ready_flip(tokens):
    tokens = strip_assignments(tokens)
    # `--undo` flips back to draft (no review triggered) — only suppress when it's
    # in THIS `gh pr ready` segment, not anywhere else in the command line.
    return tokens[:3] == ["gh", "pr", "ready"] and "--undo" not in tokens


if not any(is_pr_ready_flip(seg) for seg in command_segments(command)):
    sys.exit(0)

message = (
    "Flipping to Ready auto-requests Copilot's review — no need to add it. It "
    "posts shortly; monitor the PR (CI + Copilot's review) and engage its findings "
    "before merging."
)

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": message,
    }
}))
sys.exit(0)
