#!/usr/bin/env python3
"""PreToolUse hook: warn when `gh` is too old to request a Copilot review.

`gh pr edit --add-reviewer @copilot` only exists as of gh 2.87.0. On anything
older the flag value is passed through as an ordinary login, so the command exits
0 having registered nothing — a silent failure that reads as "GitHub changed the
rules" and invites documenting a workaround for a missing feature.

Scope is deliberately tight so nothing else pays for it: only this one command
triggers the check, and only the first time in a session. Ordinary `gh` work
never runs it.
"""
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile

# The release that added Copilot as a reviewer to `gh pr edit`, per gh's own
# changelog: v2.87.0 (2026-02-18), cli/cli#12567. Nothing to bump — later
# releases keep the feature. (`gh pr create --reviewer @copilot` arrived one
# release later, in v2.88.0, but this repo never requests on open: Copilot
# auto-reviews on PR-open / Draft -> Ready.)
MIN_GH_VERSION = (2, 87, 0)

try:
    payload = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(0)

command = (payload.get("tool_input") or {}).get("command", "") or ""

# Cheap substring gate first: skip the tokenizer for the vast majority of
# commands, which mention neither a reviewer flag nor Copilot.
lowered = command.lower()
if "copilot" not in lowered or "reviewer" not in lowered:
    sys.exit(0)


def executable_name(token):
    """Bare command name: basename, lowercased, `.exe` dropped.

    This hook is registered for PowerShell as well as Bash, where the binary is
    `gh.exe` — and on a case-insensitive filesystem it may be spelled any way.
    Splits on both separators, since os.path.basename ignores `\\` off Windows.
    """
    name = re.split(r"[\\/]", token)[-1].lower()
    return name[:-4] if name.endswith(".exe") else name


def requests_copilot_review(command):
    """True iff a segment is `gh pr edit --add-reviewer @copilot`.

    Only that flag: `gh pr edit` has no `--reviewer`, so a command using it fails
    loudly with an unknown-flag error and needs no version hint.

    Tokenizes with shlex rather than regex so the text appearing inside a quoted
    argument (an echo, a here-doc, a PR body) is a token and never mistaken for a
    real invocation. A line that won't lex is skipped; for an advisory hook the
    only cost of a miss is a missing nudge.
    """
    for line in command.split("\n"):
        try:
            lex = shlex.shlex(line, posix=True, punctuation_chars=";|&")
            lex.whitespace_split = True
            tokens = list(lex)
        except ValueError:
            continue
        segments, cur = [], []
        for tok in tokens:
            if tok and all(c in ";|&" for c in tok):  # an operator run (; | || && &)
                segments.append(cur)
                cur = []
            else:
                cur.append(tok)
        segments.append(cur)

        for seg in segments:
            i = 0
            while i < len(seg) and re.match(r"^[A-Za-z_]\w*=", seg[i]):
                i += 1  # leading `VAR=val` assignments
            seg = seg[i:]
            if len(seg) < 3 or executable_name(seg[0]) != "gh" or seg[1:3] != ["pr", "edit"]:
                continue
            for j, tok in enumerate(seg):
                flag, _, inline = tok.partition("=")
                if flag != "--add-reviewer":
                    continue
                value = inline if inline else (seg[j + 1] if j + 1 < len(seg) else "")
                # gh's special value exactly — not any login that merely contains
                # "copilot" (`mycopilotuser` is a person). The flag takes a
                # comma-separated list, so check each entry.
                if any(v.strip().lower() == "@copilot" for v in value.split(",")):
                    return True
    return False


if not requests_copilot_review(command):
    sys.exit(0)

# Fall back to the pid, never a constant: a shared literal would put one marker
# in the temp dir for every session at once, so the hint would fire once per
# machine until temp was cleared instead of once per session. Per-pid degrades
# the other way — the check may repeat, which is the harmless direction.
session_id = str(payload.get("session_id") or os.getpid())
marker = os.path.join(
    tempfile.gettempdir(),
    "ace-gh-version-checked-" + re.sub(r"[^A-Za-z0-9_.-]", "_", session_id),
)
if os.path.exists(marker):
    sys.exit(0)

try:
    proc = subprocess.run(
        ["gh", "--version"], capture_output=True, text=True, timeout=10
    )
except (OSError, subprocess.SubprocessError):
    sys.exit(0)  # gh missing or unrunnable — not this hook's problem

# e.g. "gh version 2.96.0 (2026-07-02)"
match = re.search(r"gh version (\d+)\.(\d+)\.(\d+)", proc.stdout or "")
if not match:
    sys.exit(0)  # unknown output shape — say nothing rather than guess

# Marker goes down only once a version was actually read, so one check per
# session means one *answered* check: a transient probe failure doesn't consume
# it. Best-effort — if the marker can't be written, the check simply repeats.
try:
    open(marker, "w").close()
except OSError:
    pass

version = tuple(int(g) for g in match.groups())
if version >= MIN_GH_VERSION:
    sys.exit(0)

# The facts, then the one instruction. Deliberately not *how* to upgrade: this
# hook can't know how gh was installed here, and `which gh` already tells you.
message = (
    "Installed gh is {cur}. `--add-reviewer @copilot` requires gh {min} or newer; "
    "below that the command exits 0 without registering the review request. "
    "You MUST upgrade the gh to make it happen.".format(
        min=".".join(str(n) for n in MIN_GH_VERSION),
        cur=".".join(str(n) for n in version),
    )
)

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": message,
    }
}))
sys.exit(0)
