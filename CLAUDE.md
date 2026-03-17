# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Connect-Four game implemented in Python with a Flask REST API (`game.py`, `server.py`). The server allows API calls to create games and make moves, with long-polling for turn notifications. The long-term goal is a server that will allow automated/AI players to play each other.

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

Dependencies are listed in `requirements.txt`. Pytest and Flask are installed globally in the dev container.

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

## PR and Issue Automation

`manage_github.py` runs outside of live Claude sessions to handle PRs and issues. The script:
- Merges approved PRs with passing checks (squash merge, cleans up local branch)
- For PRs with unaddressed feedback, invokes Claude Code to implement changes, run tests, commit, and push
- For open issues without an existing PR, creates a feature branch (`issue-<number>`), invokes Claude Code to implement the fix, and opens a PR
- Skips issues labeled `wontfix`, `question`, `duplicate`, or `invalid`

Run manually or via cron:

```bash
./manage_github.py
```