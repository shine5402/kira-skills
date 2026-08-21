---
name: copilot-review
description: Engaging automated PR review from Copilot — what to act on, what to skip, and when to stop. Use when a Copilot review has landed, when addressing its comments, or when deciding whether to merge with findings still open.
---

Copilot is reliable on local, checkable facts: an unhandled IO path, an inconsistent error code, a genuinely missing header. It is unreliable on whole-system reasoning, and sometimes confidently wrong there. Calibrate on that split before spending a round on anything it says.

On code, the review is a **soft gate** beside CI's hard one: wait for the initial review to land, and engage substantive findings before merging. On docs it isn't a gate — the human is.

**Every finding is a candidate, not a verdict.** Verify it against the code, the contract, or a check that already runs. Discount a finding that contradicts a passing check — Copilot claiming an implicit `any` breaks compilation while `tsc --noEmit` is green — or one that ignores an invariant holding a level up, like arguing about zip-container strictness when an Ed25519 signature over file contents is the real trust boundary.

**Low-confidence and suppressed comments aren't a gate.** They are hidden for a reason. Skim them for a real fact if you want, then move on. Working that list item by item is how a small PR turns into five rounds.

**Design questions aren't Copilot's to answer.** Layout, density, copy, what a surface should show — bring it to the user as a decision, or decline it. Don't act on it directly.

**Don't file follow-up tickets from findings you haven't verified.**

## Docs

For a document that gets loaded constantly — a skill, `CLAUDE.md`, an ADR, a memory — the default flips. An AI reviewer optimises for having something to say, and on prose that means hedges, restatements, and extra caveats: exactly the direction that makes such a document worse.

- Act on factual errors and misleading text. Nothing else.
- Rewrite in place. Add only when an omission misleads, in the shortest form that fixes it, and never a reason nobody decided.
- Reply in the thread. Change the document only when the document is wrong.
- The human approves. A quiet bot isn't approval, so ask for review explicitly.
- If a round leaves the document net longer, the loop has inverted.

## Re-triggering a review

Copilot doesn't re-review on push. Use `gh pr edit <PR#> --add-reviewer @copilot`.

Nothing substitutes for that command when it looks like it isn't working. REST `POST /repos/<owner>/<repo>/pulls/<PR#>/requested_reviewers` returns 200 for this bot and registers nothing; `--add-reviewer copilot-swe-agent` returns the PR URL as if it worked, but that login is Copilot's coding agent, not the reviewer, and no review follows.

To check whether it's attached, use REST: `gh api repos/<owner>/<repo>/pulls/<PR#> --jq '.requested_reviewers[].login'` — but an empty result from it is never evidence of absence, because the request state drifts in time: empty in the gap before Copilot picks the PR up, empty again once the review is submitted and the request is fulfilled, so it cannot tell "not yet" from "already done" and a review can land a minute after you read `[]` — wait for the review itself instead of concluding from the check. `gh pr view --json reviewRequests` goes through GraphQL, which hides bot reviewers and returns `[]` even when Copilot is requested. The timeline is the one positive check that holds: `gh api repos/<owner>/<repo>/issues/<PR#>/timeline` records a `review_requested` event naming `Copilot` (`type: Bot`) for every real request.

Never write `@copilot` in a PR body, comment, review reply, or commit message. In free text it posts under the human's identity and makes GitHub spawn a Copilot coding session on their account, which is not yours to start for them. Refer to it as "Copilot" in prose.

## When to stop

Stop once a round surfaces nothing real and in scope. There is no obligation to reach a clean round, and no fixed cap in either direction — a large PR may warrant several, a one-line fix only the first.

The opposite failure is just as real: merging while ignoring the review. If the initial review hasn't landed, or substantive findings are unaddressed, say so and wait rather than proceeding quietly.
