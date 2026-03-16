#!/bin/bash
# Loads secrets from secrets.json into the shell environment.
# Writes exports to ~/.zshenv so they're available in all zsh sessions.

SECRETS_FILE="/workspace/secrets.json"

if [ ! -f "$SECRETS_FILE" ]; then
    echo "No secrets.json found, skipping."
    exit 0
fi

# Remove any previously written secrets block to avoid duplicates
sed -i '/# BEGIN secrets.json/,/# END secrets.json/d' ~/.zshenv 2>/dev/null || true

{
    echo "# BEGIN secrets.json"
    python3 -c "
import json
with open('$SECRETS_FILE') as f:
    secrets = json.load(f)
for key, value in secrets.items():
    print(f'export {key}={value}')
"
    echo "# END secrets.json"
} >> ~/.zshenv

echo "Loaded secrets from secrets.json"
