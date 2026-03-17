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


def test_full_game_draw_via_api(client, game_id):
    moves = [0, 2, 1, 3, 4, 6, 5] * 6
    for i, col in enumerate(moves):
        player = 1 if i % 2 == 0 else 2
        response = client.post(
            f"/games/{game_id}/moves", json={"column": col, "player": player}
        )
        assert response.status_code == 200
        data = response.get_json()
        if i < 41:
            assert data["status"] == "in_progress"
        else:
            assert data["status"] == "draw"


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
