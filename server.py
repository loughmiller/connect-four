from flask import Flask, jsonify
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
