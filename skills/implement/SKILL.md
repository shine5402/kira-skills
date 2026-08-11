---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
disable-model-invocation: true
---

Implement the work described by the user in the spec or tickets.

Use /tdd where possible, at pre-agreed seams.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Once done, use /kira:code-review to review the work.

Commit your work to the current branch.

Open a pr (draft, if not otherwise agreed) after finishing the work, and watch for ci if applicable.