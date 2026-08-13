---
name: prepare-compact
description: Ask model to stop at a checkpoint so user can run compaction.
disable-model-invocation: true
---

The user wants to /compact the session history to free up headroom.

If you're mid-task, stop at the next point they could take over — soon. Their
attention is limited, and nothing on disk is lost to compaction, so don't spend
turns finishing or committing work to make it safe.

Then close your reply with a short handoff: where the work stands, anything you
need them to decide, and anything worth keeping past the summary — decisions
they steered and the reasoning behind them, findings that were costly to dig up.
Note where those might live; If you think it's worth saving in comments to current ticket, 
or a local scratchpad, you can do it immediately, otherwise it's user's call whether to save them.
