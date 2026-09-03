#!/usr/bin/env python3
"""PreToolUse hook: nudge when checking PR reviewers with `--json reviewRequests`.

`gh pr view <PR#> --json reviewRequests` goes through GraphQL, which OMITS bot
reviewers. So it returns `[]` even when Copilot *is* requested — and an agent that
reads that empty result routinely concludes "Copilot didn't attach" and wastes a
turn (or burns a review round) re-requesting it.

Two facts fix this, and this hook injects them as advisory context (it does NOT
block — checking human reviewers via GraphQL is perfectly fine, and a hook can't
tell "checking for Copilot" from "checking for humans"):

  1. Copilot's review is auto-requested on PR-open and on Draft -> Ready. If you
     just did either, you can safely ASSUME Copilot is attached — no need to check.
     A manual re-request is only warranted AFTER you push fix-up commits.
  2. `--json reviewRequests` (GraphQL) hides bot reviewers, so `[]` here does NOT
     mean Copilot is absent.

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
    independently (newlines separate commands); a line that can't be lexed
    (unbalanced quotes) is skipped, which for an advisory hook just means no nudge.

    Unlike the sibling block-copilot-mention.py — which must stay regex-simple and
    over-block, because a real bot @-mention lives inside a quoted body — precise
    parsing here only ever trades a spurious nudge for none, so it's safe.
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


def queries_review_requests(tokens):
    """True iff a `--json` flag in this segment lists the reviewRequests field."""
    for i, tok in enumerate(tokens):
        if tok == "--json" and i + 1 < len(tokens) and "reviewRequests" in tokens[i + 1]:
            return True
        if tok.startswith("--json=") and "reviewRequests" in tok:
            return True
    return False


def is_pr_view_reviewrequests(tokens):
    tokens = strip_assignments(tokens)
    return tokens[:3] == ["gh", "pr", "view"] and queries_review_requests(tokens)


if not any(is_pr_view_reviewrequests(seg) for seg in command_segments(command)):
    sys.exit(0)

message = (
    "`--json reviewRequests` uses GraphQL, which hides bot reviewers — `[]` here "
    "doesn't mean Copilot is absent. Copilot auto-attaches on PR-open / "
    "Draft -> Ready, so you can assume it's there."
)

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": message,
    }
}))
sys.exit(0)
