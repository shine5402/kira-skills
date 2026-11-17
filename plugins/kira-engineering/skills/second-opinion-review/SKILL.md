---
name: second-opinion-review
description: The second-opinion gate before a PR merges — one round from an independent agentic reviewer (Copilot, Claude Code's built-in code-review, …), requested deliberately and engaged before the merge. Use when marking a PR ready for review, before merging a PR, or when a reviewer's findings land.
---

Before a PR merges, an independent reviewer reads it: the **second opinion**. It is a soft gate beside CI's hard one — a different reader catching what the author, and `spec-review` run from the author's side, were too close to see.

## Requesting the round

Request it when the PR is marked ready for review: by then the change has settled, and a round on a draft reviews code that is still moving.

Use the repo's documented default reviewer, or whichever agentic reviewer is available — GitHub Copilot (the `copilot-review` skill has its mechanics) or Claude Code's built-in `code-review` posting to the PR. The user's pick overrides the default: a reviewer can be out of credit or down.

Check first that a round isn't already on its way — a repo can request a reviewer automatically on the ready flip. A second request buys the same opinion twice.

**One round per PR.** Every round spends credit or tokens, and a running review can't be called back. Fixes for its findings don't earn a re-review; request another round only when the user asks for one.

## Waiving the gate

The waiver is the user's, not the agent's. The user may have reviewed the change themselves, or judge it not worth a round — a docs-only change, a one-line fix. When a PR looks like that, say so and let them decide; until they waive it, the round runs. A waiver covers the PR it was given for.

## Before merging

The gate holds when the round has landed and its findings are engaged, or when the user waived it. A round that's still pending is a reason to wait: it's paid for whether or not anyone reads it, so merging past it throws the opinion away.

## Engaging findings

Each finding is a candidate, not a verdict. Verify it against the code, the contract, or a check that already runs, and discount one that contradicts a passing check or ignores an invariant held a level up.

- Fix what's real, and reply on each thread with what you did or why you declined.
- Design questions — layout, copy, what a surface should show — go to the user as decisions; the reviewer doesn't settle them.
- Low-confidence and suppressed comments sit outside the gate.
- File follow-up tickets only from findings you've verified.

On prose an agent loads — a skill, `CLAUDE.md`, an ADR, a memory — act on factual errors and misleading text only. A reviewer optimises for having something to say, and on prose that means hedges and caveats, the direction that makes such a document worse. Rewrite in place; a round that leaves the document net longer has inverted.
