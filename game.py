import uuid

ROWS = 6
COLS = 7


class Game:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.board = [[0] * COLS for _ in range(ROWS)]
        self.current_player = 1
        self.status = "in_progress"
