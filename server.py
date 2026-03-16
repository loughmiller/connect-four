import time

from flask import Flask, jsonify, request
from game import Game

app = Flask(__name__)
games = {}

LONG_POLL_TIMEOUT = 30
LONG_POLL_INTERVAL = 0.05


@app.route("/games", methods=["POST"])
def create_game():
    game = Game()
    games[game.id] = game
    return jsonify({
        "game_id": game.id,
        "board": game.board,
        "current_player": game.current_player,
        "status": game.status,
    }), 201


def _game_response(game):
    return jsonify({
        "game_id": game.id,
        "board": game.board,
        "current_player": game.current_player,
        "status": game.status,
    })


@app.route("/games/<game_id>", methods=["GET"])
def get_game(game_id):
    if game_id not in games:
        return jsonify({"error": "Game not found"}), 404
    return _game_response(games[game_id]), 200


@app.route("/games/<game_id>/turn", methods=["GET"])
def wait_for_turn(game_id):
    if game_id not in games:
        return jsonify({"error": "Game not found"}), 404

    try:
        player = int(request.args.get("player", ""))
    except ValueError:
        return jsonify({"error": "player is required"}), 400

    if player not in (1, 2):
        return jsonify({"error": "player must be 1 or 2"}), 400

    game = games[game_id]
    deadline = time.time() + LONG_POLL_TIMEOUT

    while time.time() < deadline:
        if game.current_player == player or game.status != "in_progress":
            return _game_response(game), 200
        time.sleep(LONG_POLL_INTERVAL)

    return jsonify({"error": "timeout"}), 408


@app.route("/games/<game_id>/moves", methods=["POST"])
def make_move(game_id):
    if game_id not in games:
        return jsonify({"error": "Game not found"}), 404

    data = request.get_json(force=True, silent=True)
    if not data or "column" not in data:
        return jsonify({"error": "column is required"}), 400
    if "player" not in data:
        return jsonify({"error": "player is required"}), 400

    column = data["column"]
    if not isinstance(column, int) or isinstance(column, bool):
        return jsonify({"error": "column must be an integer"}), 400

    player = data["player"]
    if player not in (1, 2):
        return jsonify({"error": "player must be 1 or 2"}), 400

    try:
        games[game_id].make_move(player, column)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return _game_response(games[game_id]), 200
