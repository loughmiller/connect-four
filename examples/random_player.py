"""
Example client: a single random player.

Waits for its turn via GET /turn, then picks a random valid column and
POSTs a move. Expects another client to be playing the other side.

Usage:
    python3 examples/random_player.py <game_id> <player> [base_url]

    player:   1 or 2
    base_url: defaults to http://localhost:5000
"""

import random
import sys

import requests

COLS = 7


def valid_columns(board):
    return [col for col in range(COLS) if board[0][col] == 0]


def print_board(board):
    symbols = {0: ".", 1: "X", 2: "O"}
    print("  " + " ".join(str(c) for c in range(COLS)))
    for row in board:
        print("  " + " ".join(symbols[cell] for cell in row))
    print()


def main():
    if len(sys.argv) < 3:
        print("Usage: random_player.py <game_id> <player> [base_url]")
        sys.exit(1)

    game_id = sys.argv[1]
    player = int(sys.argv[2])
    base_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:5000"

    while True:
        # Wait for our turn (retry on timeout)
        response = requests.get(f"{base_url}/games/{game_id}/turn?player={player}")
        if response.status_code == 408:
            continue
        response.raise_for_status()
        state = response.json()

        if state["status"] != "in_progress":
            print(f"Game over: {state['status']}")
            print_board(state["board"])
            break

        # Pick and play a random valid column
        column = random.choice(valid_columns(state["board"]))
        response = requests.post(
            f"{base_url}/games/{game_id}/moves",
            json={"column": column, "player": player},
        )
        state = response.json()
        print(f"Player {player} plays column {column}")
        print_board(state["board"])

        if state["status"] != "in_progress":
            print(f"Game over: {state['status']}")
            break


if __name__ == "__main__":
    main()
