import threading
import time

from flask import Flask, jsonify, request
from src.game import Game

app = Flask(__name__)
games = {}

LONG_POLL_TIMEOUT = 30
GAME_TTL = 300  # seconds to keep completed games before cleanup
CLEANUP_INTERVAL = 60  # seconds between cleanup runs

API_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Connect Four API",
        "version": "1.0.0",
        "description": (
            "REST API for playing Connect Four. Supports creating games, "
            "making moves, and long-polling for turn notifications."
        ),
    },
    "paths": {
        "/games": {
            "post": {
                "summary": "Create a new game",
                "operationId": "createGame",
                "responses": {
                    "201": {
                        "description": "Game created",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/GameState"}
                            }
                        },
                    }
                },
            },
            "get": {
                "summary": "List all games",
                "operationId": "listGames",
                "parameters": [
                    {
                        "name": "status",
                        "in": "query",
                        "required": False,
                        "schema": {
                            "type": "string",
                            "enum": [
                                "in_progress",
                                "player_1_wins",
                                "player_2_wins",
                                "draw",
                            ],
                        },
                        "description": "Filter games by status",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "List of games",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "$ref": "#/components/schemas/GameSummary"
                                    },
                                }
                            }
                        },
                    }
                },
            },
        },
        "/games/{game_id}": {
            "get": {
                "summary": "Get game state",
                "operationId": "getGame",
                "parameters": [
                    {
                        "name": "game_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Game state",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/GameState"}
                            }
                        },
                    },
                    "404": {
                        "description": "Game not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
        "/games/{game_id}/turn": {
            "get": {
                "summary": "Long-poll for turn",
                "operationId": "waitForTurn",
                "description": (
                    "Blocks until it is the specified player's turn or the "
                    "game ends. Times out after 30 seconds."
                ),
                "parameters": [
                    {
                        "name": "game_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "player",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "integer", "enum": [1, 2]},
                        "description": "Player number (1 or 2)",
                    },
                ],
                "responses": {
                    "200": {
                        "description": "It is now this player's turn or the game ended",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/GameState"}
                            }
                        },
                    },
                    "400": {
                        "description": "Invalid or missing player parameter",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                    "404": {
                        "description": "Game not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                    "408": {
                        "description": "Long-poll timeout",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
        "/games/{game_id}/moves": {
            "post": {
                "summary": "Make a move",
                "operationId": "makeMove",
                "parameters": [
                    {
                        "name": "game_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/MoveRequest"}
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Move accepted",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/GameState"}
                            }
                        },
                    },
                    "400": {
                        "description": "Invalid move",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                    "404": {
                        "description": "Game not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
    },
    "components": {
        "schemas": {
            "GameState": {
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "description": "Unique game identifier",
                    },
                    "board": {
                        "type": "array",
                        "description": "6x7 board grid (0=empty, 1=player 1, 2=player 2)",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer", "enum": [0, 1, 2]},
                        },
                    },
                    "current_player": {
                        "type": "integer",
                        "enum": [1, 2],
                        "description": "Player whose turn it is",
                    },
                    "status": {
                        "type": "string",
                        "enum": [
                            "in_progress",
                            "player_1_wins",
                            "player_2_wins",
                            "draw",
                        ],
                    },
                },
            },
            "GameSummary": {
                "type": "object",
                "properties": {
                    "game_id": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": [
                            "in_progress",
                            "player_1_wins",
                            "player_2_wins",
                            "draw",
                        ],
                    },
                    "current_player": {"type": "integer", "enum": [1, 2]},
                },
            },
            "MoveRequest": {
                "type": "object",
                "required": ["column", "player"],
                "properties": {
                    "column": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 6,
                        "description": "Column to drop piece into (0-6)",
                    },
                    "player": {
                        "type": "integer",
                        "enum": [1, 2],
                        "description": "Player making the move",
                    },
                },
            },
            "Error": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "description": "Error message",
                    }
                },
            },
        }
    },
}


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
    game = Game()
    games[game.id] = game
    return jsonify({
        "game_id": game.id,
        "board": game.board,
        "current_player": game.current_player,
        "status": game.status,
    }), 201


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
        })
    return jsonify(result), 200


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

    with game._condition:
        notified = game._condition.wait_for(
            lambda: game.current_player == player or game.status != "in_progress",
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
