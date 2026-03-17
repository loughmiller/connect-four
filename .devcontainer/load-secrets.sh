#!/bin/bash
# Loads secrets from .env (or secrets.json) into the shell environment.
# Writes exports to ~/.zshenv so they're available in all zsh sessions.

ENV_FILE="/workspace/.env"
SECRETS_FILE="/workspace/secrets.json"

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
elif [ -f "$SECRETS_FILE" ]; then
    {
        echo "# BEGIN secrets"
        python3 -c "
import json
with open('$SECRETS_FILE') as f:
    secrets = json.load(f)
for key, value in secrets.items():
    print(f'export {key}=\"{value}\"')
"
        echo "# END secrets"
    } >> ~/.zshenv
    echo "Loaded secrets from secrets.json (consider migrating to .env)"
else
    echo "No .env or secrets.json found, skipping."
fi
