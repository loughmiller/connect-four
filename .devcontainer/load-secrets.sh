#!/bin/bash
# Loads secrets from .env into the shell environment.
# Writes exports to ~/.zshenv so they're available in all zsh sessions.

ENV_FILE="/workspace/.env"

# Remove any previously written secrets block to avoid duplicates
sed -i '/# BEGIN secrets/,/# END secrets/d' ~/.zshenv 2>/dev/null || true

if [ -f "$ENV_FILE" ]; then
    {
        echo "# BEGIN secrets"
        grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$' | while IFS= read -r line; do
            echo "export $line"
        done
        echo "# END secrets"
    } >> ~/.zshenv
    echo "Loaded secrets from .env"
else
    echo "No .env found, skipping."
fi
