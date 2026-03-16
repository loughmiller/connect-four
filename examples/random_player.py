"""
Example client: two random players compete via the Connect Four API.

Each player runs in its own thread, uses GET /turn to wait for its turn,
then picks a random valid column and POSTs a move.

Usage:
    python3 examples/random_player.py [base_url]

    base_url defaults to http://localhost:5000
"""

import random
import sys
import threading

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


def player_loop(base_url, game_id, player, done_event):
    while not done_event.is_set():
        # Wait for our turn
        response = requests.get(f"{base_url}/games/{game_id}/turn?player={player}")
        state = response.json()

        if state["status"] != "in_progress":
            print(f"Game over: {state['status']}")
            print_board(state["board"])
            done_event.set()
            return

        # Pick and play a random valid column
        column = random.choice(valid_columns(state["board"]))
        response = requests.post(
            f"{base_url}/games/{game_id}/moves",
            json={"column": column},
        )
        state = response.json()
        print(f"Player {player} ({'X' if player == 1 else 'O'}) plays column {column}")
        print_board(state["board"])

        if state["status"] != "in_progress":
            print(f"Game over: {state['status']}")
            done_event.set()
            return


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"

    response = requests.post(f"{base_url}/games")
    game = response.json()
    game_id = game["game_id"]
    print(f"Game started: {game_id}\n")
    print_board(game["board"])

    done_event = threading.Event()

    t1 = threading.Thread(target=player_loop, args=(base_url, game_id, 1, done_event))
    t2 = threading.Thread(target=player_loop, args=(base_url, game_id, 2, done_event))

    t1.start()
    t2.start()
    t1.join()
    t2.join()


if __name__ == "__main__":
    main()
