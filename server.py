from flask import Flask, jsonify, request
from game import Game

app = Flask(__name__)
games = {}


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


@app.route("/games/<game_id>/moves", methods=["POST"])
def make_move(game_id):
    if game_id not in games:
        return jsonify({"error": "Game not found"}), 404

    data = request.get_json(force=True, silent=True)
    if not data or "column" not in data:
        return jsonify({"error": "column is required"}), 400

    column = data["column"]
    if not isinstance(column, int) or isinstance(column, bool):
        return jsonify({"error": "column must be an integer"}), 400

    try:
        games[game_id].make_move(column)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return _game_response(games[game_id]), 200
