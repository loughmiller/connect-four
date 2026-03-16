import pytest
from server import app, games


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
