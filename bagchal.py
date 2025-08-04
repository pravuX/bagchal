from enum import IntEnum
from typing import override
import numpy as np


# REMEMBER:
# x -> cols : width
# y -> rows : height

class Piece(IntEnum):
    GOAT = -1
    EMPTY = 0
    TIGER = 1


class GameState:
    # state_key: prioritized_moves (move, score) in order of score
    transposition_table_with_scores = {}
    graph = {0:  [1, 5, 6], 1:  [0, 2, 6], 2:  [1, 3, 6, 7, 8], 3:  [2, 4, 8], 4:  [3, 8, 9],
             5:  [0, 6, 10], 6:  [0, 1, 2, 5, 7, 10, 11, 12], 7:  [2, 6, 8, 12], 8:  [2, 3, 4, 7, 9, 12, 13, 14], 9:  [4, 8, 14],
             10: [5, 6, 11, 15, 16], 11: [6, 10, 12, 16], 12: [6, 7, 8, 11, 13, 16, 17, 18], 13: [8, 12, 14, 18], 14: [8, 9, 13, 18, 19],
             15: [10, 16, 20], 16: [10, 11, 12, 15, 17, 20, 21, 22], 17: [12, 16, 18, 22], 18: [12, 13, 14, 17, 19, 22, 23, 24], 19: [14, 18, 24],
             20: [15, 16, 21], 21: [16, 20, 22], 22: [16, 17, 18, 21, 23], 23: [18, 22, 24], 24: [18, 19, 23]}

    piece = {
        -1: "G", 0: ' ', 1: "T"
    }

    def __init__(self, board, turn, goat_count, eaten_goat_count):
        self.board = board
        self.turn = turn
        self.goat_count = goat_count
        self.eaten_goat_count = eaten_goat_count
        self.trapped_tiger_count = 0

    @override
    def __repr__(self) -> str:
        return f"Turn: {self.piece[self.turn]}, Goat Left: {self.goat_count}, Eaten Goat: {self.eaten_goat_count}, Trapped Tiger: {self.trapped_tiger_count}"

    def stringify(self):
        string_rep = ""
        for p in self.board:
            string_rep += self.piece[p]
        return string_rep

    def key(self):
        return (
            self.stringify(),
            self.turn,
            self.eaten_goat_count,
            self.goat_count,
            self.trapped_tiger_count
        )

    def update_trapped_tiger(self):
        count = 0
        pos_tiger = [i for i, cell in enumerate(
            self.board) if cell == Piece.TIGER]
        for tiger in pos_tiger:
            if (self.is_trapped(tiger)):
                count += 1
        self.trapped_tiger_count = count

    def get_result(self):
        if self.trapped_tiger_count == 4:
            return Piece.GOAT
        if self.eaten_goat_count > 4:  # Thapa et. al showed more than 4 goats captured leads to a win rate of 87% for tiger
            return Piece.TIGER
        # general logic for trapping
        # trapped = no legal moves
        # legal_moves = self.get_legal_moves, turn
        # len(legal_moves) == 0 => Trapped
        # who won? -turn
        legal_moves = self.get_legal_moves()
        if (len(legal_moves)) == 0:  # if no legal moves remain, then the that player is trapped
            return self.turn * -1
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

    def apply_move(self, move):
        src, dst = move
        if src == dst:
            # Placement
            if self.turn == Piece.GOAT and self.goat_count > 0 and self.board[src] == Piece.EMPTY:
                self.board[src] = Piece.GOAT
                self.goat_count -= 1
                self.change_turn()
            return

        if self.board[src] != self.turn or self.board[dst] != Piece.EMPTY:
            return

        # Movement
        if dst in self.graph[src]:
            self.board[src] = Piece.EMPTY
            self.board[dst] = Piece.TIGER if Piece.TIGER == self.turn else Piece.GOAT
            self.change_turn()
            return

        # Capture
        if self.board[src] == Piece.TIGER:
            mid = (src + dst) // 2
            if self.board[mid] == Piece.GOAT and mid in self.graph[src] and dst in self.graph[mid]:
                self.board[mid] = Piece.EMPTY
                self.board[src] = Piece.EMPTY
                self.board[dst] = Piece.TIGER
                self.eaten_goat_count += 1
                self.change_turn()

    def make_move(self, move, simulate=False):
        new_board = self.board.copy()
        new_state = GameState(
            new_board, self.turn, self.goat_count, self.eaten_goat_count)
        new_state.apply_move(move)
        new_state.update_trapped_tiger()
        if not simulate:  # otherwise there is infinite recursion
            new_state.init_prioritization()
        return new_state

    def init_prioritization(self):
        self.prioritized_moves_with_scores = self.prioritize_moves()
        self.prioritized_moves = [move for move,
                                  _ in self.prioritized_moves_with_scores]
        self.prioritized_scores = [score for _,
                                   score in self.prioritized_moves_with_scores]
        self.calculate_prior_prob_dist()

    def prioritize_moves(self):
        state_key = self.key()
        if state_key in GameState.transposition_table_with_scores:
            return list(GameState.transposition_table_with_scores[state_key])

        # implement move ordering
        moves = self.get_legal_moves()
        if self.turn == Piece.TIGER:
            scored_moves = [(move, self.tiger_priority(move))
                            for move in moves]
        else:
            scored_moves = [(move, self.goat_priority(move)) for move in moves]

        # order scored moves by their priority (asc)
        scored_moves.sort(key=lambda m: m[1])
        GameState.transposition_table_with_scores[state_key] = tuple(
            scored_moves)

        return scored_moves

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
        self.init_prioritization()

    def tiger_priority(self, move):
        priority_score = 10
        next_state = self.make_move(move, simulate=True)
        if next_state.eaten_goat_count > 4:
            # immediate win
            return 50
        if next_state.eaten_goat_count > self.eaten_goat_count:
            # this move leads to capture
            priority_score += 5

        src, dst = move
        # potential capture
        for adj in GameState.graph[dst]:
            if self.board[adj] == Piece.GOAT:
                capture_pos = adj - (dst - adj)
                if capture_pos in GameState.graph[adj] and self.board[capture_pos] == Piece.EMPTY:
                    priority_score += 5

        pos_tiger = [i for i, p in enumerate(
            self.board) if p == Piece.TIGER]

        for tiger in pos_tiger:
            if tiger != src:
                for adj in GameState.graph[tiger]:
                    if self.board[adj] == Piece.GOAT:
                        capture_pos = adj - (tiger - adj)
                        if capture_pos in GameState.graph[adj]:
                            # a capture is possible but it's blocked by the tiger at src
                            # so we encourage moving away
                            if capture_pos == src:
                                priority_score += 2.5
                            # but if moving away blocks capture for another tiger,
                            # we discourage that move
                            elif capture_pos == dst:
                                priority_score -= 2.4

        strong_positions = [6, 8, 12, 16, 18]
        if dst in strong_positions:
            priority_score += 2
        if src == 12:
            priority_score -= 0.8

        return priority_score + np.random.random()  # some noise

    def goat_priority(self, move):
        src, dst = move
        is_placement_phase = src == dst
        priority_score = 5
        next_state = self.make_move(move, simulate=True)
        if next_state.trapped_tiger_count == 4:
            # immediate win -> high reward
            return 50
        # more the tigers trapped, greater the reward
        # if a move untraps a tiger, punish it
        untraps = False
        traps = False
        diff = next_state.trapped_tiger_count - self.trapped_tiger_count
        if diff < 0:
            untraps = True
        else:
            traps = True

        priority_score += 7 * diff  # TODO fine tune this

        pos_tiger = [i for i, p in enumerate(
            self.board) if p == Piece.TIGER]

        # encourage clustering
        for adj in GameState.graph[dst]:
            if self.board[adj] == Piece.GOAT and adj != src:
                priority_score += 1.5
            elif self.board[adj] == Piece.TIGER:
                priority_score -= 0.1

        strategic_positions = [2, 10, 14, 22]
        outer_edge = [0, 1, 2, 3, 4, 5, 10, 15, 20, 21, 22, 23, 24, 9, 14, 19]
        if is_placement_phase and dst in strategic_positions:
            priority_score += 1
        if dst in outer_edge:
            priority_score += 1

        # reward moves that block captures
        # the more it blocks captures, the greater the reward
        for tiger in pos_tiger:
            for adj in GameState.graph[tiger]:
                if self.board[adj] == Piece.GOAT:
                    capture_pos = adj - (tiger - adj)
                    if capture_pos in GameState.graph[adj]:
                        # and capture_pos in GameState.graph[adj]:
                        if self.board[capture_pos] == Piece.EMPTY:
                            # this move blocks capture by placing(or moving) a piece at the capture_position
                            # blocking a capture can also mean moving the threatened piece to capture_position
                            if dst == capture_pos:
                                if untraps:  # prioritize blocking more than untrapping
                                    priority_score -= 7 * diff
                                priority_score += 5
                            # how to allow escaping by moving away from the threatening position
                            # we know that a capture is possible here
                            # we check if src == adj (it means that the piece at src is capturable)
                            # moving it will help avoid a capture, so we reward that
                            elif src == adj:
                                if untraps:  # prioritize blocking more than untrapping
                                    priority_score -= 7 * diff
                                priority_score += 5

                        elif not is_placement_phase and src == capture_pos:
                            # here, there is already a piece on the capture position
                            # thus we check if making this move allows another piece to be captured
                            # i.e. if the piece blocks a capture currently, and moving it will threaten
                            # another piece
                            priority_score -= 5  # TODO fine tune this

        # if placing(or moving) a piece leads to immediate capture assign it
        # a very low priority
        for tiger in pos_tiger:
            threatened = False
            for adj in GameState.graph[tiger]:
                if adj == dst:  # dst is adjacent to tiger
                    capture_pos = dst - (tiger - dst)
                    # a piece can move into threat either from a different position or capture_position
                    if capture_pos in GameState.graph[dst] and (self.board[capture_pos] == Piece.EMPTY or capture_pos == src):
                        threatened = True
                        priority_score -= 15
                        if traps:  # don't sacrifice even if trap is possible
                            priority_score -= 7 * diff
                        break
            if threatened:
                break

        return priority_score + np.random.random()  # some noise

    def calculate_prior_prob_dist(self, temp=1):
        if self.is_game_over():
            return

        # softmax for move probabilites based on their priority scores
        prioritized_scores = np.array(
            self.prioritized_scores, dtype=np.float64)
        prioritized_scores = prioritized_scores / temp
        stabilized_scores = prioritized_scores - np.max(prioritized_scores)
        e_prioritized_moves = np.exp(stabilized_scores)
        e_prioritized_moves_sum = e_prioritized_moves.sum()
        # reversed because Node.children stores moves in descending order
        # of priority score
        self.prior_prob_dist = e_prioritized_moves / e_prioritized_moves_sum
