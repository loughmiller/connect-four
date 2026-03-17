---
name: feedback_branch_from_main
description: Always create new feature branches from main, not from whatever branch is currently checked out
type: feedback
---

Always checkout main and pull the latest changes before creating a new feature branch (`git checkout main && git pull && git checkout -b <branch>`).

**Why:** Creating a branch from another feature branch pulls in that branch's commits, polluting PRs with unrelated changes. Similarly, branching from a stale local main can cause merge conflicts or miss recent fixes.

**How to apply:** Before every `git checkout -b`, first `git checkout main && git pull` (or explicitly pass the start point after pulling: `git checkout -b <branch> main`).
