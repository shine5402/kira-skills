---
name: get-pr-merged
description: Get proposed draft pr merged into the target trunk
disable-model-invocation: true
---

Take the draft PR you opened and get it merged:

1. Mark it as ready for review.
2. Take it through the second-opinion gate: use the Skill tool with "second-opinion-review".
3. Confirm CI is green, then merge.

Please review if your PR will automatically close related tickets (if any), and react accordingly.
