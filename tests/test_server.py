import threading
import time
import pytest
import server
from server import app, games, cleanup_games, start_cleanup_thread


@pytest.fixture(autouse=True)
def clear_games():
    games.clear()
    yield
    games.clear()


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def game_id(client):
    return client.post("/games").get_json()["game_id"]


def test_create_game_returns_201(client):
    response = client.post("/games")
    assert response.status_code == 201


def test_create_game_response_fields(client):
    data = client.post("/games").get_json()
    assert "game_id" in data
    assert "board" in data
    assert "current_player" in data
    assert "status" in data


def test_create_game_board_dimensions(client):
    data = client.post("/games").get_json()
    assert len(data["board"]) == 6
    assert all(len(row) == 7 for row in data["board"])


def test_create_game_initial_state(client):
    data = client.post("/games").get_json()
    assert data["current_player"] == 1
    assert data["status"] == "in_progress"
    assert all(cell == 0 for row in data["board"] for cell in row)


def test_create_game_stored(client):
    data = client.post("/games").get_json()
    assert data["game_id"] in games


def test_create_multiple_games_unique_ids(client):
    id1 = client.post("/games").get_json()["game_id"]
    id2 = client.post("/games").get_json()["game_id"]
    assert id1 != id2
    assert len(games) == 2


# --- GET /games ---

def test_list_games_empty(client):
    response = client.get("/games")
    assert response.status_code == 200
    assert response.get_json() == []


def test_list_games_returns_all(client):
    client.post("/games")
    client.post("/games")
    data = client.get("/games").get_json()
    assert len(data) == 2


def test_list_games_response_fields(client):
    client.post("/games")
    data = client.get("/games").get_json()
    assert "game_id" in data[0]
    assert "status" in data[0]
    assert "current_player" in data[0]
    assert "board" not in data[0]


def test_list_games_filter_by_status(client):
    id1 = client.post("/games").get_json()["game_id"]
    client.post("/games")
    games[id1].status = "player_1_wins"
    data = client.get("/games?status=in_progress").get_json()
    assert len(data) == 1
    assert data[0]["status"] == "in_progress"


def test_list_games_filter_no_match(client):
    client.post("/games")
    data = client.get("/games?status=draw").get_json()
    assert data == []


# --- GET /games/<game_id> ---

def test_get_game_returns_200(client, game_id):
    assert client.get(f"/games/{game_id}").status_code == 200


def test_get_game_response_fields(client, game_id):
    data = client.get(f"/games/{game_id}").get_json()
    assert "game_id" in data
    assert "board" in data
    assert "current_player" in data
    assert "status" in data


def test_get_game_reflects_current_state(client, game_id):
    client.post(f"/games/{game_id}/moves", json={"column": 0, "player": 1})
    data = client.get(f"/games/{game_id}").get_json()
    assert data["board"][5][0] == 1
    assert data["current_player"] == 2


def test_get_game_unknown_game(client):
    response = client.get("/games/nonexistent")
    assert response.status_code == 404
    assert "error" in response.get_json()


# --- GET /games/<game_id>/turn ---

def test_turn_unknown_game(client):
    response = client.get("/games/nonexistent/turn?player=1")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_turn_missing_player(client, game_id):
    response = client.get(f"/games/{game_id}/turn")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_turn_invalid_player(client, game_id):
    response = client.get(f"/games/{game_id}/turn?player=3")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_turn_returns_immediately_when_already_your_turn(client, game_id):
    response = client.get(f"/games/{game_id}/turn?player=1")
    assert response.status_code == 200
    data = response.get_json()
    assert data["current_player"] == 1


def test_turn_returns_immediately_when_game_over(client, game_id):
    games[game_id].status = "player_1_wins"
    response = client.get(f"/games/{game_id}/turn?player=2")
    assert response.status_code == 200
    assert response.get_json()["status"] == "player_1_wins"


def test_turn_timeout(client, game_id):
    original = server.LONG_POLL_TIMEOUT
    server.LONG_POLL_TIMEOUT = 0.025
    try:
        client.post(f"/games/{game_id}/moves", json={"column": 0, "player": 1})
        response = client.get(f"/games/{game_id}/turn?player=1")
        assert response.status_code == 408
        assert "error" in response.get_json()
    finally:
        server.LONG_POLL_TIMEOUT = original


def test_turn_blocks_until_opponent_moves(client, game_id):
    client.post(f"/games/{game_id}/moves", json={"column": 0, "player": 1})

    client2 = app.test_client()

    def player2_moves():
        client2.post(f"/games/{game_id}/moves", json={"column": 1, "player": 2})

    t = threading.Timer(0.025, player2_moves)
    t.start()
    response = client.get(f"/games/{game_id}/turn?player=1")
    t.join()

    assert response.status_code == 200
    assert response.get_json()["current_player"] == 1


def test_turn_multiple_players_polling_simultaneously(client, game_id):
    """Two clients both waiting on /turn wake up when a move is made."""
    client.post(f"/games/{game_id}/moves", json={"column": 0, "player": 1})

    results = {}

    def poll_turn(player, label):
        c = app.test_client()
        results[label] = c.get(f"/games/{game_id}/turn?player={player}")

    t1 = threading.Thread(target=poll_turn, args=(1, "p1"))
    t2 = threading.Thread(target=poll_turn, args=(1, "p2"))
    t1.start()
    t2.start()

    time.sleep(0.025)
    mover = app.test_client()
    mover.post(f"/games/{game_id}/moves", json={"column": 1, "player": 2})

    t1.join()
    t2.join()

    assert results["p1"].status_code == 200
    assert results["p1"].get_json()["current_player"] == 1
    assert results["p2"].status_code == 200
    assert results["p2"].get_json()["current_player"] == 1


def test_turn_polling_during_game_completion(client, game_id):
    """A player long-polling receives game-over status when opponent wins."""
    # Set up board so player 1 has 3 in a row at cols 0,1,2 (bottom row)
    # Player 2 has pieces at cols 4,5 (bottom row)
    moves = [(0, 1), (4, 2), (1, 1), (5, 2), (2, 1), (6, 2)]
    for col, player in moves:
        client.post(f"/games/{game_id}/moves", json={"column": col, "player": player})

    # Player 2 is now polling for their turn
    result = {}

    def poll_turn():
        c = app.test_client()
        result["response"] = c.get(f"/games/{game_id}/turn?player=2")

    t = threading.Thread(target=poll_turn)
    t.start()

    time.sleep(0.025)
    # Player 1 makes the winning move (col 3 completes 4 in a row)
    client.post(f"/games/{game_id}/moves", json={"column": 3, "player": 1})

    t.join()

    assert result["response"].status_code == 200
    assert result["response"].get_json()["status"] == "player_1_wins"


def test_turn_rapid_sequential_polls(client, game_id):
    """A client polls, times out, and immediately re-polls without issues."""
    client.post(f"/games/{game_id}/moves", json={"column": 0, "player": 1})

    original = server.LONG_POLL_TIMEOUT
    server.LONG_POLL_TIMEOUT = 0.025
    try:
        # First poll times out
        response1 = client.get(f"/games/{game_id}/turn?player=1")
        assert response1.status_code == 408

        # Immediate re-poll also times out cleanly
        response2 = client.get(f"/games/{game_id}/turn?player=1")
        assert response2.status_code == 408

        # Third poll is woken by a move
        def player2_moves():
            c = app.test_client()
            c.post(f"/games/{game_id}/moves", json={"column": 1, "player": 2})

        t = threading.Timer(0.025, player2_moves)
        server.LONG_POLL_TIMEOUT = 1
        t.start()
        response3 = client.get(f"/games/{game_id}/turn?player=1")
        t.join()

        assert response3.status_code == 200
        assert response3.get_json()["current_player"] == 1
    finally:
        server.LONG_POLL_TIMEOUT = original


# --- POST /games/<game_id>/moves ---

def test_make_move_returns_200(client, game_id):
    response = client.post(f"/games/{game_id}/moves", json={"column": 0, "player": 1})
    assert response.status_code == 200


def test_make_move_response_fields(client, game_id):
    data = client.post(f"/games/{game_id}/moves", json={"column": 0, "player": 1}).get_json()
    assert "game_id" in data
    assert "board" in data
    assert "current_player" in data
    assert "status" in data


def test_make_move_updates_board(client, game_id):
    data = client.post(f"/games/{game_id}/moves", json={"column": 0, "player": 1}).get_json()
    assert data["board"][5][0] == 1


def test_make_move_switches_player(client, game_id):
    data = client.post(f"/games/{game_id}/moves", json={"column": 0, "player": 1}).get_json()
    assert data["current_player"] == 2


def test_make_move_unknown_game(client):
    response = client.post("/games/nonexistent/moves", json={"column": 0})
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_make_move_missing_body(client, game_id):
    response = client.post(f"/games/{game_id}/moves")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_make_move_missing_column_key(client, game_id):
    response = client.post(f"/games/{game_id}/moves", json={"player": 1})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_make_move_missing_player_key(client, game_id):
    response = client.post(f"/games/{game_id}/moves", json={"column": 0})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_make_move_non_integer_column(client, game_id):
    response = client.post(f"/games/{game_id}/moves", json={"column": "a", "player": 1})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_make_move_bool_column_rejected(client, game_id):
    response = client.post(f"/games/{game_id}/moves", json={"column": True, "player": 1})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_make_move_invalid_player(client, game_id):
    response = client.post(f"/games/{game_id}/moves", json={"column": 0, "player": 3})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_make_move_wrong_turn(client, game_id):
    response = client.post(f"/games/{game_id}/moves", json={"column": 0, "player": 2})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_make_move_column_out_of_range(client, game_id):
    response = client.post(f"/games/{game_id}/moves", json={"column": 99, "player": 1})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_make_move_game_over(client, game_id):
    games[game_id].status = "player_1_wins"
    response = client.post(f"/games/{game_id}/moves", json={"column": 0, "player": 1})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_make_move_win_updates_status(client, game_id):
    # Player 1 wins horizontally: cols 0,1,2,3 with player 2 at cols 4,5,6
    moves = [(0, 1), (4, 2), (1, 1), (5, 2), (2, 1), (6, 2), (3, 1)]
    for col, player in moves[:-1]:
        client.post(f"/games/{game_id}/moves", json={"column": col, "player": player})
    col, player = moves[-1]
    data = client.post(f"/games/{game_id}/moves", json={"column": col, "player": player}).get_json()
    assert data["status"] == "player_1_wins"


# --- cleanup_games ---

def test_cleanup_removes_expired_completed_games(client):
    data = client.post("/games").get_json()
    gid = data["game_id"]
    game = games[gid]
    game.status = "player_1_wins"
    game.completed_at = time.monotonic() - server.GAME_TTL - 1
    cleanup_games()
    assert gid not in games


def test_cleanup_keeps_recent_completed_games(client):
    data = client.post("/games").get_json()
    gid = data["game_id"]
    game = games[gid]
    game.status = "player_1_wins"
    game.completed_at = time.monotonic()
    cleanup_games()
    assert gid in games


def test_cleanup_keeps_in_progress_games(client):
    data = client.post("/games").get_json()
    gid = data["game_id"]
    cleanup_games()
    assert gid in games


def test_cleanup_thread_runs_periodically(client):
    data = client.post("/games").get_json()
    gid = data["game_id"]
    game = games[gid]
    game.status = "player_1_wins"
    game.completed_at = time.monotonic() - server.GAME_TTL - 1

    original = server.CLEANUP_INTERVAL
    server.CLEANUP_INTERVAL = 0.01
    try:
        stop = start_cleanup_thread()
        time.sleep(0.05)
        stop.set()
    finally:
        server.CLEANUP_INTERVAL = original

    assert gid not in games
