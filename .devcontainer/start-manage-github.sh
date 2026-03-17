#!/bin/bash
# Clone repo to a separate directory and run manage_github.py in a loop.
# Runs in the background so it doesn't block devcontainer startup.

set -euo pipefail

# Load secrets (GH_TOKEN, etc.) from .env into this shell
ENV_FILE="/workspace/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')
    set +a
fi

REPO_URL="https://github.com/loughmiller/connect-four.git"
WORK_DIR="/tmp/manage-github-work"
INTERVAL="${MANAGE_GITHUB_INTERVAL:-60}"
LOG="/tmp/manage-github.log"

git config --global user.name "manage-github-bot"
git config --global user.email "bot@connect-four.local"

if [ ! -d "$WORK_DIR/.git" ]; then
    git clone "$REPO_URL" "$WORK_DIR"
fi

echo "manage-github started (logging to $LOG)"

while true; do
    echo "=== Running manage_github.py at $(date) ===" >> "$LOG" 2>&1
    cd "$WORK_DIR"
    MANAGE_GITHUB_WORK_DIR="$WORK_DIR" python3 tools/manage_github.py >> "$LOG" 2>&1 || echo "manage_github.py exited with error" >> "$LOG" 2>&1
    sleep "$INTERVAL"
done
