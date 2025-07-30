from enum import IntEnum


# REMEMBER:
# x -> cols : width
# y -> rows : height

class Piece(IntEnum):
    GOAT = -1
    EMPTY = 0
    TIGER = 1


class GameState:
    graph = {0:  [1, 5, 6], 1:  [0, 2, 6], 2:  [1, 3, 6, 7, 8], 3:  [2, 4, 8], 4:  [3, 8, 9],
             5:  [0, 6, 10], 6:  [0, 1, 2, 5, 7, 10, 11, 12], 7:  [2, 6, 8, 12], 8:  [2, 3, 4, 7, 9, 12, 13, 14], 9:  [4, 8, 14],
             10: [5, 6, 11, 15, 16], 11: [6, 10, 12, 16], 12: [6, 7, 8, 11, 13, 16, 17, 18], 13: [8, 12, 14, 18], 14: [8, 9, 13, 18, 19],
             15: [10, 16, 20], 16: [10, 11, 12, 15, 17, 20, 21, 22], 17: [12, 16, 18, 22], 18: [12, 13, 14, 17, 19, 22, 23, 24], 19: [14, 18, 24],
             20: [15, 16, 21], 21: [16, 20, 22], 22: [16, 17, 18, 21, 23], 23: [18, 22, 24], 24: [18, 19, 23]}

    def __init__(self, board, turn, goat_count, eaten_goat_count):
        self.board = board
        self.turn = turn
        self.goat_count = goat_count
        self.eaten_goat_count = eaten_goat_count
        self.trapped_tiger_count = 0

    def update_tiger_pos(self):
        self.pos_tiger = [i for i, cell in enumerate(
            self.board) if cell == Piece.TIGER]

    def update_trapped_tiger(self):
        count = 0
        for tiger in self.pos_tiger:
            if (self.is_trapped(tiger)):
                count += 1
        self.trapped_tiger_count = count

    def get_result(self):
        if self.trapped_tiger_count == 4:
            return Piece.GOAT
        elif self.eaten_goat_count > 4:  # Thapa et. al showed more than 4 goats captured leads to a win rate of 87% for tiger
            return Piece.TIGER
        # draw here
        return None

    def is_game_over(self):
        return self.get_result() is not None

    def is_trapped(self, tiger):
        # check adjacent nodes of tiger
        # return false if at least one node is empty
        # if the adjacent node has a goat
        # check if that can be "eaten"
        # return false
        # otherwise return true
        for adj in self.graph[tiger]:
            if self.board[adj] == Piece.EMPTY:
                return False
            elif self.board[adj] == Piece.GOAT:
                capture_pos = adj - (tiger - adj)
                if capture_pos in self.graph[adj] and self.board[capture_pos] == Piece.EMPTY:
                    return False
        return True

    def change_turn(self):
        self.turn *= -1

    def make_move(self, move):
        src, dst = move
        if src == dst:
            if self.turn == Piece.GOAT and self.goat_count > 0 and self.board[src] == Piece.EMPTY:
                self.board[src] = Piece.GOAT
                self.goat_count -= 1
                self.change_turn()
            return

        if self.board[src] != self.turn or self.board[dst] != Piece.EMPTY:
            return

        if dst in self.graph[src]:
            self.board[src] = Piece.EMPTY
            self.board[dst] = self.turn
            self.change_turn()
            return

        if self.board[src] == Piece.TIGER:
            mid = (src + dst) // 2
            if self.board[mid] == Piece.GOAT and mid in self.graph[src] and dst in self.graph[mid]:
                self.board[mid] = Piece.EMPTY
                self.board[src] = Piece.EMPTY
                self.board[dst] = Piece.TIGER
                self.eaten_goat_count += 1
                self.change_turn()

    def evaluate_board(self):
        goats_on_board = sum(1 for s in self.board if s == Piece.GOAT)
        pos_goat = [i for i, cell in enumerate(
            self.board) if cell == Piece.GOAT]

        if self.is_game_over():
            return 100 * self.get_result()

        tiger_moves = 0
        capture_opportunities = 0
        tiger_center_bonus = 0
        tiger_exact_center_bonus = 0
        goat_center_bonus = 0
        edge_center_bonus = 0
        goat_grouping_bonus = 0
        tiger_surround_penalty = 0

        center_positions = {6, 8, 12, 16, 18}
        center_outside = {2, 10, 14, 22}

        for tiger in self.pos_tiger:
            if tiger in center_positions:
                tiger_center_bonus += 1
            if tiger == 12:
                tiger_exact_center_bonus += 1

            for adj in self.graph[tiger]:
                if self.board[adj] == Piece.EMPTY:
                    tiger_moves += 1
                elif self.board[adj] == Piece.GOAT:
                    cap_pos = adj - (tiger - adj)
                    if cap_pos in self.graph[adj] and self.board[cap_pos] == Piece.EMPTY:
                        capture_opportunities += 1
                        tiger_moves += 2  # emphasize mobility from captures
                    tiger_surround_penalty += 1

        for goat in pos_goat:
            if goat in center_positions:
                goat_center_bonus += 1
            if goat in center_outside:
                edge_center_bonus += 1
            for adj in self.graph[goat]:
                if self.board[adj] == Piece.GOAT:
                    goat_grouping_bonus += 1  # reward goat clusters

        tiger_score = (
            + 10 * self.eaten_goat_count  # reward immediate capture
            + 6 * capture_opportunities  # reward possible captures
            + 0.8 * tiger_moves  # reward tiger mobility
            + 0.25 * tiger_center_bonus  # reward center postions
            + 0.5 * tiger_exact_center_bonus
            - 0.5 * tiger_surround_penalty  # tigers surrounded by goats = bad
        )

        goat_score = (
            + 1 * goats_on_board  # material value of goats already placed
            + 0.5 * self.goat_count  # material value of goats on hand
            + 10 * self.trapped_tiger_count  # advantageous for goat
            + 0.5 * edge_center_bonus  # strong position for goat
            + 0.25 * goat_center_bonus  # center position = stronger board influence
            + 0.4 * goat_grouping_bonus  # goats working together
        )

        return tiger_score - goat_score

    def get_legal_moves(self):
        moves = []

        if self.turn == Piece.GOAT:
            if self.goat_count > 0:
                # Goat placement phase: place on any empty cell
                for i in range(25):
                    if self.board[i] == Piece.EMPTY:
                        moves.append((i, i))  # placement represented as (i, i)
            else:
                # Move goats to adjacent empty positions
                for i in range(25):
                    if self.board[i] == Piece.GOAT:
                        for adj in self.graph[i]:
                            if self.board[adj] == Piece.EMPTY:
                                moves.append((i, adj))

        elif self.turn == Piece.TIGER:
            for i in range(25):
                if self.board[i] == Piece.TIGER:
                    for adj in self.graph[i]:
                        if self.board[adj] == Piece.EMPTY:
                            moves.append((i, adj))
                        elif self.board[adj] == Piece.GOAT:
                            capture_pos = adj - (i - adj)
                            if (capture_pos in self.graph[adj] and
                                    self.board[capture_pos] == Piece.EMPTY):
                                moves.append((i, capture_pos))

        return moves

    def reset(self):
        for i, _ in enumerate(self.board):
            self.board[i] = Piece.EMPTY

        tiger_init_pos = [0, 4, 20, 24]

        for pos in tiger_init_pos:
            self.board[pos] = Piece.TIGER

        self.turn = Piece.GOAT

        self.goat_count = 20
        self.eaten_goat_count = 0
        self.trapped_tiger_count = 0
