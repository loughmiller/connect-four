---
name: Always PR repo memory changes
description: When saving or updating memory files in .claude/memory/, commit them on a branch and open a PR like any other repo change
type: feedback
---

Repo memory files (`.claude/memory/`) are committed code. Always create a branch and open a PR for them.

**Why:** Multiple times, memory files were saved but left uncommitted or not submitted as a PR, so the changes never actually landed in the repo.

**How to apply:** After writing or updating any file in `.claude/memory/`, immediately create a feature branch, commit, push, and open a PR — same workflow as any code change.
