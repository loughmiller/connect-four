---
name: feedback_branch_from_main
description: Always create new feature branches from main, not from whatever branch is currently checked out
type: feedback
---

Always checkout main before creating a new feature branch (`git checkout main && git checkout -b <branch>`).

**Why:** Creating a branch from another feature branch pulls in that branch's commits, polluting PRs with unrelated changes.

**How to apply:** Before every `git checkout -b`, first `git checkout main` (or explicitly pass the start point: `git checkout -b <branch> main`).
