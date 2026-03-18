import threading
import time

from flask import Flask, jsonify, request
from src.api_spec import API_SPEC
from src.game import Game

app = Flask(__name__)
games = {}

LONG_POLL_TIMEOUT = 30
GAME_TTL = 300  # seconds to keep completed games before cleanup
CLEANUP_INTERVAL = 60  # seconds between cleanup runs

@app.route("/api-docs", methods=["GET"])
def api_docs():
    return jsonify(API_SPEC), 200


def cleanup_games():
    now = time.monotonic()
    expired = [
        gid for gid, game in games.items()
        if game.completed_at is not None and now - game.completed_at >= GAME_TTL
    ]
    for gid in expired:
        del games[gid]


def _run_cleanup_loop(stop_event):
    while not stop_event.wait(CLEANUP_INTERVAL):
        cleanup_games()


def start_cleanup_thread():
    stop_event = threading.Event()
    thread = threading.Thread(target=_run_cleanup_loop, args=(stop_event,), daemon=True)
    thread.start()
    return stop_event


@app.route("/games", methods=["POST"])
def create_game():
    data = request.get_json(force=True, silent=True) or {}
    player1_name = data.get("player1_name", "Player 1")
    game = Game(player1_name=player1_name)
    games[game.id] = game
    return jsonify({
        "game_id": game.id,
        "board": game.board,
        "current_player": game.current_player,
        "status": game.status,
        "players": game.players,
    }), 201


@app.route("/games/<game_id>/join", methods=["POST"])
def join_game(game_id):
    if game_id not in games:
        return jsonify({"error": "Game not found"}), 404

    data = request.get_json(force=True, silent=True)
    if not data or "player_name" not in data:
        return jsonify({"error": "player_name is required"}), 400

    try:
        games[game_id].join(data["player_name"])
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return _game_response(games[game_id]), 200


@app.route("/games", methods=["GET"])
def list_games():
    status_filter = request.args.get("status")
    result = []
    for game in games.values():
        if status_filter and game.status != status_filter:
            continue
        result.append({
            "game_id": game.id,
            "status": game.status,
            "current_player": game.current_player,
            "players": game.players,
        })
    return jsonify(result), 200


def _game_response(game):
    return jsonify({
        "game_id": game.id,
        "board": game.board,
        "current_player": game.current_player,
        "status": game.status,
        "players": game.players,
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

    with game._condition:
        notified = game._condition.wait_for(
            lambda: (game.status == "in_progress" and game.current_player == player) or
                    game.status not in ("in_progress", "waiting_for_opponent"),
            timeout=LONG_POLL_TIMEOUT,
        )

    if not notified:
        return jsonify({"error": "timeout"}), 408
    return _game_response(game), 200


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
