import threading
import uuid

ROWS = 6
COLS = 7


class Game:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.board = [[0] * COLS for _ in range(ROWS)]
        self.current_player = 1
        self.status = "in_progress"
        self._condition = threading.Condition()

    def make_move(self, player, column):
        with self._condition:
            if self.status != "in_progress":
                raise ValueError("Game is already over")
            if player != self.current_player:
                raise ValueError("Not your turn")
            if not (0 <= column < COLS):
                raise ValueError("Column out of range")

            row = None
            for r in range(ROWS - 1, -1, -1):
                if self.board[r][column] == 0:
                    row = r
                    break

            if row is None:
                raise ValueError("Column is full")

            self.board[row][column] = self.current_player

            if self._check_win(row, column):
                self.status = f"player_{self.current_player}_wins"
            elif self._is_full():
                self.status = "draw"
            else:
                self.current_player = 2 if self.current_player == 1 else 1

            self._condition.notify_all()

    def _check_win(self, row, col):
        player = self.board[row][col]
        for dr, dc in [(0, 1), (1, 0), (1, 1), (1, -1)]:
            count = 1
            for sign in (1, -1):
                r, c = row + sign * dr, col + sign * dc
                while 0 <= r < ROWS and 0 <= c < COLS and self.board[r][c] == player:
                    count += 1
                    r += sign * dr
                    c += sign * dc
            if count >= 4:
                return True
        return False

    def _is_full(self):
        return all(self.board[0][c] != 0 for c in range(COLS))
