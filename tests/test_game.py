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
    try:
        game.make_move(2, 0)
        assert False, "Should have raised"
    except ValueError as e:
        assert "Not your turn" in str(e)


def test_make_move_invalid_column_low():
    game = Game()
    try:
        game.make_move(1, -1)
        assert False, "Should have raised"
    except ValueError as e:
        assert "out of range" in str(e)


def test_make_move_invalid_column_high():
    game = Game()
    try:
        game.make_move(1, COLS)
        assert False, "Should have raised"
    except ValueError as e:
        assert "out of range" in str(e)


def test_make_move_full_column():
    game = Game()
    for r in range(ROWS):
        game.board[r][3] = 1
    try:
        game.make_move(1, 3)
        assert False, "Should have raised"
    except ValueError as e:
        assert "full" in str(e)


def test_make_move_game_already_over():
    game = Game()
    game.status = "player_1_wins"
    try:
        game.make_move(1, 0)
        assert False, "Should have raised"
    except ValueError as e:
        assert "already over" in str(e)


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


def test_full_game_draw():
    game = Game()
    # 42-move sequence that fills the board with no four-in-a-row.
    # Pattern [0,2,1,3,4,6,5] repeated 6 times fills columns so that
    # each column alternates players and no horizontal, vertical, or
    # diagonal line of four exists.
    moves = [0, 2, 1, 3, 4, 6, 5] * 6
    assert len(moves) == 42
    for i, col in enumerate(moves):
        player = 1 if i % 2 == 0 else 2
        assert game.current_player == player
        assert game.status == "in_progress"
        game.make_move(player, col)
    assert game.status == "draw"
    assert game.completed_at is not None
    assert all(game.board[0][c] != 0 for c in range(COLS))


def test_completed_at_not_set_while_in_progress():
    game = Game()
    game.make_move(1, 0)
    assert game.completed_at is None
