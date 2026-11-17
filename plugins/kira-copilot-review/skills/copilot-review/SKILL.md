---
name: copilot-review
description: GitHub Copilot as a PR reviewer — requesting a round, checking whether it's attached, and telling when it has landed. Use when requesting a Copilot review, checking whether Copilot is on a PR, or waiting for its review.
---

Copilot is one reviewer the second-opinion gate can use; the `second-opinion-review` skill decides when a round runs and how to engage what it finds. This skill is the GitHub mechanics, several of which fail silently.

## Requesting

Check whether the base branch already requests Copilot on its own: `gh api repos/<owner>/<repo>/rules/branches/<base> --jq '.[] | select(.type=="copilot_code_review")'`. A rule with `review_draft_pull_requests: false` requests a round when the PR is marked ready, and requesting by hand on top of it buys a second round.

Otherwise request it with `gh pr edit <PR#> --add-reviewer @copilot`. Nothing substitutes for that command when it looks like it isn't working. REST `POST /repos/<owner>/<repo>/pulls/<PR#>/requested_reviewers` returns 200 for this bot and registers nothing; `--add-reviewer copilot-swe-agent` returns the PR URL as if it worked, but that login is Copilot's coding agent, not the reviewer, and no review follows.

Copilot doesn't re-review on push, so a request is a deliberate round every time.

## Checking it's attached

The timeline is the one positive check that holds: `gh api repos/<owner>/<repo>/issues/<PR#>/timeline` records a `review_requested` event naming `Copilot` (`type: Bot`) for every real request.

The other two checks mislead. `gh pr view --json reviewRequests` goes through GraphQL, which hides bot reviewers and returns `[]` even when Copilot is requested. REST `gh api repos/<owner>/<repo>/pulls/<PR#> --jq '.requested_reviewers[].login'` drifts in time: empty before Copilot picks the PR up, empty again once the review is submitted, so `[]` can't tell "not yet" from "already done".

## Waiting for it to land

Match the author loosely — a substring, not an equality test. The review arrives under a longer `copilot-…[bot]` login rather than the `Copilot` the timeline event names, so an exact filter silently never fires, which reads exactly like a review that hasn't arrived. Expect state `COMMENTED`; it comments rather than approves.

## Naming it

Never write `@copilot` in a PR body, comment, review reply, or commit message. In free text it posts under the human's identity and makes GitHub spawn a Copilot coding session on their account, which is not yours to start for them. Refer to it as "Copilot" in prose.
