---
name: implement-with-design
description: "Implement a piece of work based on a spec or set of tickets, with additional design review."
disable-model-invocation: true
---

Implement the work described by the user in the spec or tickets.

Use /tdd where possible, at pre-agreed seams.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Once done, use /kira:code-review to review the work. Also use an additional review subagent to compare your implementation against the design prototype (e.g. from DesignSync) the user has provided. 

During implementation, check your work against the design regularly — for example using Playwright. The review subagent can use the same tooling to verify the comparison.

Commit your work to the current branch.

Open a pr (draft, if not otherwise agreed) after finishing the work, and watch for ci if applicable.

