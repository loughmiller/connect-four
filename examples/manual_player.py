"""
Example client: a manual (human) player.

Waits for its turn via GET /turn, then prompts the user to pick a column
and POSTs the move. Expects another client to be playing the other side.

Usage:
    python3 examples/manual_player.py <game_id> <player> [base_url]

    player:   1 or 2
    base_url: defaults to http://localhost:5000
"""

import sys

import requests

ROWS = 6
COLS = 7


def valid_columns(board):
    return [col for col in range(COLS) if board[0][col] == 0]


def print_board(board):
    symbols = {0: ".", 1: "X", 2: "O"}
    print("  " + " ".join(str(c) for c in range(COLS)))
    for row in board:
        print("  " + " ".join(symbols[cell] for cell in row))
    print()


def prompt_column(board):
    """Ask the user to choose a valid column, repeating until valid."""
    columns = valid_columns(board)
    while True:
        try:
            choice = int(input(f"Your move — choose a column {columns}: "))
        except (ValueError, EOFError):
            print("Please enter a valid column number.")
            continue
        if choice in columns:
            return choice
        print(f"Invalid choice. Valid columns: {columns}")


def main():
    if len(sys.argv) < 3:
        print("Usage: manual_player.py <game_id> <player> [base_url]")
        sys.exit(1)

    game_id = sys.argv[1]
    player = int(sys.argv[2])
    base_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:5000"
    token = "X" if player == 1 else "O"

    print(f"Manual player {player} ({token}) joined game {game_id}")
    print(f"Server: {base_url}\n")

    while True:
        # Wait for our turn (retry on timeout)
        print("Waiting for your turn...")
        response = requests.get(f"{base_url}/games/{game_id}/turn?player={player}")
        if response.status_code == 408:
            continue
        response.raise_for_status()
        state = response.json()

        print_board(state["board"])

        if state["status"] != "in_progress":
            print(f"Game over: {state['status']}")
            break

        # Prompt for a move
        column = prompt_column(state["board"])
        response = requests.post(
            f"{base_url}/games/{game_id}/moves",
            json={"column": column, "player": player},
        )
        state = response.json()
        print(f"\nPlayer {player} plays column {column}")
        print_board(state["board"])

        if state["status"] != "in_progress":
            print(f"Game over: {state['status']}")
            break


if __name__ == "__main__":
    main()
