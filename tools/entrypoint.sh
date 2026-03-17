#!/bin/bash
set -euo pipefail

INTERVAL="${MANAGE_GITHUB_INTERVAL:-60}"
REPO_URL="https://github.com/loughmiller/connect-four.git"
REPO_DIR="/work/connect-four"

export MANAGE_GITHUB_WORK_DIR="$REPO_DIR"

# Git identity for commits made by Claude
git config --global user.name "manage-github-bot"
git config --global user.email "bot@connect-four.local"

# Initial clone
if [ ! -d "$REPO_DIR/.git" ]; then
    echo "Cloning repository..."
    git clone "$REPO_URL" "$REPO_DIR"
fi

while true; do
    echo "=== Running manage_github.py at $(date) ==="
    cd "$REPO_DIR"
    python3 tools/manage_github.py || echo "manage_github.py exited with error"
    echo "Sleeping ${INTERVAL}s..."
    sleep "$INTERVAL"
done
