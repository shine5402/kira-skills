---
name: trim-memory
description: Trim memory hard and aggressively, so the agent doesn't get misled by stale or speculative entries.
disable-model-invocation: true
---

# Aggressively trim the auto-memory.

Memory is precious, unversioned, unreviewed space loaded blind into every session — and a stale entry can silently override correct repo guidance (this has burned us a lot). Durable, shareable knowledge belongs in the repo (code, docs, ADR, issue, PR), not here. So bias hard toward deletion.

Go through every memory file and the index. For each, classify:

- Already elsewhere — the fact is in code, an ADR, a skill, a doc, an issue, or a merged PR → delete (say where it lives).
- Historical — describes a bug now fixed, a step now removed, or a prototype now superseded → delete.
- Speculative — "when X lands", "reopen when…", future-conditional → delete.
- Recoverable — could be re-derived cheaply by reading the code or running a command → delete.
- Suspicious — looks stale, can't be quickly confirmed against the current repo, or could actively mislead an action (build flags, versions, paths) → delete. When in doubt, trim rather than keep.
- Worth preserving durably — genuinely valuable AND better homed in the repo → do NOT delete yet. Add it to a "move to repo" list.

Then, before deleting anything in the "move to repo" bucket, surface that list to me and wait for confirmation — tell me what each item is and where you'd put it (which file/ADR/issue). Everything in the pure-delete buckets, just delete.

Keep only what is non-obvious, still-live, has no better home, and won't mislead. Report what you deleted (grouped by reason), what you propose moving to the repo, and what you kept and why. Update MEMORY.md to match.