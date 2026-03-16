from game import Game, ROWS, COLS


def test_new_game_board_dimensions():
    game = Game()
    assert len(game.board) == ROWS
    assert all(len(row) == COLS for row in game.board)


def test_new_game_board_empty():
    game = Game()
    assert all(cell == 0 for row in game.board for cell in row)


def test_new_game_defaults():
    game = Game()
    assert game.current_player == 1
    assert game.status == "in_progress"


def test_new_game_unique_ids():
    g1, g2 = Game(), Game()
    assert g1.id != g2.id
