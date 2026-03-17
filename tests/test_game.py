import pytest

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


def test_make_move_places_piece_at_bottom():
    game = Game()
    game.make_move(1, 0)
    assert game.board[ROWS - 1][0] == 1


def test_make_move_stacks_pieces():
    game = Game()
    game.make_move(1, 0)  # player 1 bottom
    game.make_move(2, 0)  # player 2 above
    assert game.board[ROWS - 1][0] == 1
    assert game.board[ROWS - 2][0] == 2


def test_make_move_switches_player():
    game = Game()
    game.make_move(1, 0)
    assert game.current_player == 2
    game.make_move(2, 1)
    assert game.current_player == 1


def test_make_move_wrong_player():
    game = Game()
    with pytest.raises(ValueError, match="Not your turn"):
        game.make_move(2, 0)


def test_make_move_invalid_column_low():
    game = Game()
    with pytest.raises(ValueError, match="out of range"):
        game.make_move(1, -1)


def test_make_move_invalid_column_high():
    game = Game()
    with pytest.raises(ValueError, match="out of range"):
        game.make_move(1, COLS)


def test_make_move_full_column():
    game = Game()
    for r in range(ROWS):
        game.board[r][3] = 1
    with pytest.raises(ValueError, match="full"):
        game.make_move(1, 3)


def test_make_move_game_already_over():
    game = Game()
    game.status = "player_1_wins"
    with pytest.raises(ValueError, match="already over"):
        game.make_move(1, 0)


def test_horizontal_win():
    game = Game()
    # Player 1: cols 0,1,2,3  Player 2: cols 4,5,6 (between each)
    moves = [0, 4, 1, 5, 2, 6, 3]
    for col in moves:
        game.make_move(game.current_player, col)
    assert game.status == "player_1_wins"


def test_vertical_win():
    game = Game()
    # Player 1 stacks col 0, player 2 stacks col 1
    moves = [0, 1, 0, 1, 0, 1, 0]
    for col in moves:
        game.make_move(game.current_player, col)
    assert game.status == "player_1_wins"


def test_diagonal_win_forward_slash():
    game = Game()
    # / diagonal: (5,0),(4,1),(3,2),(2,3) for player 1
    game.board[5][0] = 1
    game.board[4][1] = 1
    game.board[3][2] = 1
    # fill below (2,3) so piece lands there
    game.board[5][3] = 2
    game.board[4][3] = 2
    game.board[3][3] = 2
    game.make_move(1, 3)
    assert game.status == "player_1_wins"


def test_diagonal_win_backslash():
    game = Game()
    # \ diagonal: (2,3),(3,4),(4,5),(5,6) for player 1
    game.board[2][3] = 1
    game.board[3][4] = 1
    game.board[4][5] = 1
    # fill below (5,6) so piece lands there — col 6 is empty so piece goes to row 5
    game.make_move(1, 6)
    assert game.status == "player_1_wins"


def test_horizontal_win_player2():
    game = Game()
    # Player 2: cols 0,1,2,3  Player 1 wastes moves on col 4,5,6 (+ extra)
    moves = [4, 0, 5, 1, 6, 2, 4, 3]
    for col in moves:
        game.make_move(game.current_player, col)
    assert game.status == "player_2_wins"


def test_vertical_win_player2():
    game = Game()
    # Player 2 stacks col 1, player 1 stacks col 0 (with one wasted move)
    moves = [0, 1, 0, 1, 0, 1, 6, 1]
    for col in moves:
        game.make_move(game.current_player, col)
    assert game.status == "player_2_wins"


def test_diagonal_win_player2():
    game = Game()
    # Set up a / diagonal win for player 2 at (5,0),(4,1),(3,2),(2,3)
    game.board[5][0] = 2
    game.board[4][1] = 2
    game.board[3][2] = 2
    # fill below (2,3) so piece lands at row 2
    game.board[5][3] = 1
    game.board[4][3] = 1
    game.board[3][3] = 1
    game.current_player = 2
    game.make_move(2, 3)
    assert game.status == "player_2_wins"


def test_draw():
    game = Game()
    # Fill board with all 2s except (0, 0), then player 1 plays col 0
    for r in range(ROWS):
        for c in range(COLS):
            game.board[r][c] = 2
    game.board[0][0] = 0
    game.current_player = 1
    game.make_move(1, 0)
    assert game.status == "draw"


def test_no_win_continues():
    game = Game()
    game.make_move(1, 0)
    assert game.status == "in_progress"


def test_new_game_completed_at_is_none():
    game = Game()
    assert game.completed_at is None


def test_completed_at_set_on_win():
    game = Game()
    moves = [0, 4, 1, 5, 2, 6, 3]
    for col in moves:
        game.make_move(game.current_player, col)
    assert game.completed_at is not None


def test_completed_at_set_on_draw():
    game = Game()
    for r in range(ROWS):
        for c in range(COLS):
            game.board[r][c] = 2
    game.board[0][0] = 0
    game.current_player = 1
    game.make_move(1, 0)
    assert game.completed_at is not None


def test_completed_at_not_set_while_in_progress():
    game = Game()
    game.make_move(1, 0)
    assert game.completed_at is None
