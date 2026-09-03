---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: "What will the next session be used for?"
disable-model-invocation: true
---

Write a handoff document summarizing the current conversation so a fresh agent can continue the work. Save to the temporary directory of the user's OS - not the current workspace.

Include a "suggested skills" section in the document, which suggests skills that the agent should invoke.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.

When the handoff crosses machines — to another machine the user controls, or to a colleague — look for anything the next session needs that exists only on this machine, and bundle it into a zip beside the document. Whatever belongs in the repo, the issue tracker, or another durable doc should go there instead: surface those to the user first, so only the genuinely machine-local files end up in the zip.
