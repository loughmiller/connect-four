# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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