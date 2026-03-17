---
name: PR watching moved to shell script
description: PR checks now run via tools/manage_github.py outside of live sessions, no longer need to start a /loop
type: feedback
---

PR watching was moved from an in-session `/loop` to the standalone `tools/manage_github.py` script. Do NOT start a `/loop` for PR watching at session startup.

**Why:** The user preferred running PR checks outside of live Claude sessions to avoid cluttering the session.

**How to apply:** No session startup steps are required for PR watching. If the user asks about PR status, point them to `./tools/manage_github.py`.
