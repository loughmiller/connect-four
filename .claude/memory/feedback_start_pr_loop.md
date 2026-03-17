---
name: Start PR watch loop at session start
description: Always start the recurring PR watch loop at the beginning of every session as specified in CLAUDE.md
type: feedback
---

Always start the PR watch loop at the very beginning of every session — don't wait for the user to ask.

**Why:** The CLAUDE.md "PR Watching" section requires scheduling a recurring 3-minute cron job to watch for PR activity. Forgetting to start it means approved PRs sit unmerged and review comments go unaddressed.

**How to apply:** Before doing anything else in a new session, use `/loop` with the PR watching prompt from CLAUDE.md.
