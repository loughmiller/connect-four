# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Session Startup

Do these immediately at the start of every session, before any other work:

1. **Start the PR watch loop** — run `/loop` with the prompt in the [PR Watching](#pr-watching) section below.

## Project

Connect-Four game implemented in Python. Currently in the foundation stage — the dev environment is configured but source code has not been written yet. This is a server that will allow API calls to play the game. The long goal is a server that will allow automated/ai players to play each other.

## Development Environment

This project runs inside a VS Code Dev Container (see `.devcontainer/`). The container:
- Uses Node.js 20 as the base image with Python 3 installed
- Runs `init-firewall.sh` on start, which applies a strict network whitelist (GitHub, npm, Anthropic APIs, VS Code marketplace — all other outbound traffic is dropped by default)
- Installs Claude Code CLI globally

## Network Access

The firewall whitelist allows outbound access to:
- GitHub (all IP ranges)
- `registry.npmjs.org`
- `api.anthropic.com`
- VS Code marketplace and update endpoints

All other outbound traffic is blocked. If you need to reach a new external service, the whitelist in `.devcontainer/init-firewall.sh` must be updated.

## Python Setup

The `.gitignore` expects a virtual environment at `.venv/`. Standard Python project conventions apply:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # once it exists
```

No build system, test runner, or dependency file exists yet — these should be added as the project develops.

## Git

Commit every change to git. Each logical change should be its own commit with a descriptive message.

A pre-commit hook runs `pytest --cov --cov-fail-under=100` before every commit. All tests must pass with 100% coverage or the commit will be rejected.

Never push directly to `main`. All changes must be submitted via a pull request: create a feature branch, push it, and open a PR.

## Memory

Claude's memory is split by scope:

- **Repo memory** (`.claude/memory/`) — project-level feedback, workflow rules, and context that applies to all developers. Committed to the repo and shared.
- **Personal memory** (`~/.claude/projects/-workspace/memory/`) — individual preferences, communication style, personal context. Local only, not committed.

When saving new memories, use repo memory for anything project- or workflow-related, and personal memory for anything specific to an individual developer.

## Unit Testing

Framework: `pytest`

```bash
pytest                                  # run all tests
pytest tests/test_board.py              # run a single file
pytest tests/test_board.py::test_name   # run a single test
pytest -v                               # verbose output
```

- Test files live in `tests/`, named `test_*.py`
- Test functions named `test_*`
- Install pytest: `pip install pytest pytest-cov`
- 100% coverage is required: `pytest --cov --cov-fail-under=100`

## PR Watching

At the start of every session, schedule a recurring cron job (every 3 minutes) to watch for PR activity on this repo. Use the `/loop` skill with this prompt:

```
3m Check GitHub PRs for the loughmiller/connect-four repo and take action:

1. Load secrets and authenticate: `bash /workspace/.devcontainer/load-secrets.sh && source ~/.zshenv`

2. Get all open PRs: `gh api repos/loughmiller/connect-four/pulls`

3. For each open PR:
   a. Check review state: `gh api repos/loughmiller/connect-four/pulls/{number}/reviews`
   b. Check PR comments: `gh api repos/loughmiller/connect-four/pulls/{number}/comments`
   c. Check issue comments: `gh api repos/loughmiller/connect-four/issues/{number}/comments`

4. If a PR has been APPROVED and all checks pass, merge it and clean up the local branch:
   ```
   gh api repos/loughmiller/connect-four/pulls/{number}/merge -X PUT -f merge_method=squash
   git checkout main && git pull
   git branch -d {branch_name}
   ```
   (GitHub is configured to auto-delete the remote branch on merge.)

5. For each unaddressed review comment:
   - If you agree with the requested change, implement it, run tests, commit, and push.
   - If you disagree, reply to the comment via `gh api repos/loughmiller/connect-four/pulls/{number}/comments/{comment_id}/replies -X POST -f body="..."` explaining your reasoning and ask for clarification before making changes.

Always run `git checkout main && git pull` before checking out any feature branch. Always run tests before pushing. Never push directly to main.

If there are no open PRs and nothing to act on, output nothing.
```