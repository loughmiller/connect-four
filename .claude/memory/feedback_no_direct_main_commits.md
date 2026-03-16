---
name: No direct commits to main
description: Always create a feature branch before committing — never commit directly to main
type: feedback
---

Always create a feature branch before making any commits. Never commit directly to main, even for small or docs-only changes.

**Why:** The project rules in CLAUDE.md explicitly require all changes go through PRs. A direct commit to main bypasses review and violates the stated workflow. This happened once with a CLAUDE.md update that should have been on a branch.

**How to apply:** Before writing any file or running git add/commit, confirm you are on a feature branch (not main). If on main, create a branch first.
