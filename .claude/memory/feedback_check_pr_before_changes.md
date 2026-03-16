---
name: Check PR merged before new changes
description: Always verify the current branch's PR is merged before starting new work
type: feedback
---

Always check if the open PR is merged before making any new changes. Pull main and start a fresh branch only after confirming the merge.

**Why:** User was mid-thought on a new feature when reminded that the previous PR hadn't been merged yet, causing potential confusion about base state.

**How to apply:** At the start of any new task, check the current branch and whether its PR has been merged. If not, wait or ask the user before proceeding.
