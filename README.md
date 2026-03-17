# Connect Four

A Connect Four game with a REST API, designed for automated and AI players to compete against each other.

## Quick Start

### Run the server

```bash
docker-compose up -d server
```

The API is available at `http://localhost:8080`.

### Play a game

```bash
# Create a game
curl -X POST http://localhost:8080/games

# Join as player 1 (random bot)
python3 examples/random_player.py <game_id> 1

# Join as player 2 (human)
python3 examples/manual_player.py <game_id> 2
```

## API

### `POST /games`

Create a new game. Returns the game ID, board, and initial state.

### `GET /games`

List all games. Optional `?status=` filter (e.g. `in_progress`, `draw`, `player_1_wins`).

### `GET /games/<game_id>`

Get the current state of a game.

### `GET /games/<game_id>/turn?player=N`

Long-poll for your turn. Blocks up to 30 seconds, returning the game state when it's player N's turn or the game ends. Returns 408 on timeout (retry).

### `POST /games/<game_id>/moves`

Make a move. Body: `{"column": 0-6, "player": 1|2}`. Returns the updated game state.

## Example Players

- **`examples/random_player.py`** — Bot that picks a random valid column each turn.
- **`examples/manual_player.py`** — Interactive player with command-line input.

Both accept: `python3 examples/<player>.py <game_id> <player_num> [base_url]`

## Development

This project uses a VS Code Dev Container. Open the repo in VS Code and select "Reopen in Container" to get a fully configured environment.

### Running locally (without the container)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m src.server
```

### Tests

```bash
pytest              # run all tests
pytest -v           # verbose
```

100% test coverage is required — enforced by a pre-commit hook that runs `pytest --cov --cov-fail-under=100`.

## GitHub Automation

`tools/manage_github.py` automates PR and issue handling:

- Merges approved PRs with passing checks (squash merge)
- Invokes Claude Code to address PR review feedback
- Creates branches and PRs for open issues

Run it manually or as a container:

```bash
# Manual
python3 tools/manage_github.py

# Container (runs every 60s)
docker-compose up -d manage-github
```

Requires `GH_TOKEN` and `ANTHROPIC_API_KEY` in a `.env` file — see `.env.example`.
