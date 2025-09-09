from dataclasses import dataclass
import numpy as np
from collections import deque

Piece_GOAT = -1
Piece_EMPTY = 0
Piece_TIGER = 1


@dataclass
class HeuristicParams:
    """Learnable parameters for move evaluation and state evaluation"""
    # Tiger parameters
    tiger_capture_bonus: float = 30
    tiger_potential_capture_bonus: float = 20
    tiger_block_penalty: float = 30

    # Goat parameters
    goat_sacrifice_penalty: float = 30
    goat_clustering_bonus: float = 5
    goat_strategic_position_bonus: float = 5
    goat_outer_edge_bonus: float = 5

    # State evaluation
    w_eat: float = 1.2322
    w_potcap: float = 1.8946
    w_mobility: float = 0.5699
    w_trap: float = 0.5001
    w_presence: float = 0.8651
    w_inacc: float = 0.5730


class GameState:

    graph = {0:  [1, 5, 6], 1:  [0, 2, 6], 2:  [1, 3, 6, 7, 8], 3:  [2, 4, 8], 4:  [3, 8, 9],
             5:  [0, 6, 10], 6:  [0, 1, 2, 5, 7, 10, 11, 12], 7:  [2, 6, 8, 12], 8:  [2, 3, 4, 7, 9, 12, 13, 14], 9:  [4, 8, 14],
             10: [5, 6, 11, 15, 16], 11: [6, 10, 12, 16], 12: [6, 7, 8, 11, 13, 16, 17, 18], 13: [8, 12, 14, 18], 14: [8, 9, 13, 18, 19],
             15: [10, 16, 20], 16: [10, 11, 12, 15, 17, 20, 21, 22], 17: [12, 16, 18, 22], 18: [12, 13, 14, 17, 19, 22, 23, 24], 19: [14, 18, 24],
             20: [15, 16, 21], 21: [16, 20, 22], 22: [16, 17, 18, 21, 23], 23: [18, 22, 24], 24: [18, 19, 23]}

    piece = {
        -1: "🐐", 0: '  ', 1: "🐅"
    }
    all_positions = np.arange(25)

    capture_edges = {0: [(1, 2), (5, 10), (6, 12)], 1: [(2, 3), (6, 11)], 2: [(1, 0), (3, 4), (6, 10), (7, 12), (8, 14)], 3: [(2, 1), (8, 13)], 4: [(3, 2), (8, 12), (9, 14)],
                     5: [(6, 7), (10, 15)], 6: [(7, 8), (11, 16), (12, 18)], 7: [(6, 5), (8, 9), (12, 17)], 8: [(7, 6), (12, 16), (13, 18)], 9: [(8, 7), (14, 19)],
                     10: [(5, 0), (6, 2), (11, 12), (15, 20), (16, 22)], 11: [(6, 1), (12, 13), (16, 21)], 12: [(6, 0), (7, 2), (8, 4), (11, 10), (13, 14), (16, 20), (17, 22), (18, 24)],
                     13: [(8, 3), (12, 11), (18, 23)], 14: [(8, 2), (9, 4), (13, 12), (18, 22), (19, 24)], 15: [(10, 5), (16, 17)], 16: [(11, 6), (12, 8), (17, 18)],
                     17: [(12, 7), (16, 15), (18, 19)], 18: [(12, 6), (13, 8), (17, 16)], 19: [(14, 9), (18, 17)], 20: [(15, 10), (16, 12), (21, 22)], 21: [(16, 11), (22, 23)],
                     22: [(16, 10), (17, 12), (18, 14), (21, 20), (23, 24)], 23: [(18, 13), (22, 21)], 24: [(18, 12), (19, 14), (23, 22)]}

    # Numpy
    graph_np = [np.array(neighbors) for neighbors in graph.values()]

    # positions tiger can jump to
    capture_map_np = [
        np.array([landing for _, landing in edges])
        for _, edges in capture_edges.items()
    ]
    # And the midpoint of that jump
    capture_mid_map_np = {
        (src, landing): mid for src, edges in capture_edges.items() for mid, landing in edges
    }

    __slots__ = ['board', 'turn', 'goat_count', 'eaten_goat_count', 'tiger_positions',
                 'goat_positions', 'empty_positions', 'history']

    def __init__(self, board=None, turn=Piece_GOAT, goat_count=20, eaten_goat_count=0):

        if board is None:
            self.board = np.array([Piece_EMPTY] * 25, dtype=np.int8)
        else:
            self.board = board

        self.turn = turn
        self.goat_count = goat_count
        self.eaten_goat_count = eaten_goat_count

        # 25 len boolean array
        # True = Piece at that index
        self.tiger_positions = self.board == Piece_TIGER
        self.goat_positions = self.board == Piece_GOAT
        self.empty_positions = self.board == Piece_EMPTY

        self.history = []

    def __repr__(self) -> str:
        return f"Turn: {self.piece[self.turn]}, Goat Left: {self.goat_count}, Eaten Goat: {self.eaten_goat_count}, Trapped Tiger: {self.trapped_tiger_count}"

    @property
    def key(self):
        return (
            tuple(self.board), self.turn, self.eaten_goat_count, self.goat_count
        )

    @property
    def trapped_tiger_count(self):
        count = 0
        tiger_indices = self.all_positions[self.tiger_positions]
        for src in tiger_indices:
            if self.is_trapped(src):
                count += 1
        return count

    def is_trapped(self, tiger):
        for adj in self.graph_np[tiger]:
            if self.board[adj] == Piece_EMPTY:
                return False
            landing = 2 * adj - tiger  # adj + (adj - tiger)
            if self.board[adj] == Piece_GOAT and landing in self.graph_np[adj] and self.board[landing] == Piece_EMPTY:
                return False
        return True

    @property
    def get_result(self):
        # returns the winner in the current game_state
        # if there's no winner returns None
        if self.trapped_tiger_count == 4:
            return Piece_GOAT
        if self.eaten_goat_count > 4:
            return Piece_TIGER
        legal_moves = self.get_legal_moves_np()
        if (len(legal_moves)) == 0:  # if no legal moves remain, then the that player is trapped
            return self.turn * -1
        return None

    @property
    def is_game_over(self):
        return self.get_result is not None

    def make_move(self, move):

        src, dst = move

        captured_piece_position = -1

        if self.turn == Piece_GOAT and self.goat_count > 0:
            # Placement
            assert self.board[dst] == Piece_EMPTY

            self.board[dst] = Piece_GOAT
            self.goat_positions[dst] = True
            self.empty_positions[dst] = False
            self.goat_count -= 1

        elif self.turn == Piece_TIGER and dst not in self.graph_np[src]:
            # Capture
            # mid = (src + dst) // 2
            mid = self.capture_mid_map_np[(src, dst)]
            assert self.board[src] == Piece_TIGER
            assert self.board[mid] == Piece_GOAT
            assert self.board[dst] == Piece_EMPTY

            self.board[src] = Piece_EMPTY
            self.board[mid] = Piece_EMPTY
            self.board[dst] = Piece_TIGER

            self.eaten_goat_count += 1

            self.tiger_positions[src] = False
            self.goat_positions[mid] = False
            self.tiger_positions[dst] = True

            self.empty_positions[src] = True
            self.empty_positions[mid] = True
            self.empty_positions[dst] = False

            captured_piece_position = mid
        else:
            # Standard Movement
            moving_piece = self.board[src]
            assert moving_piece == self.turn
            assert self.board[dst] == Piece_EMPTY

            self.board[src] = Piece_EMPTY
            self.board[dst] = moving_piece

            piece_list_to_update = self.tiger_positions if moving_piece == Piece_TIGER else self.goat_positions
            piece_list_to_update[src] = False
            piece_list_to_update[dst] = True

            self.empty_positions[src] = True
            self.empty_positions[dst] = False

        self.history.append((move, captured_piece_position))
        self.turn *= -1

    def unmake_move(self):
        if not self.history:
            return

        last_move, captured_piece_position = self.history.pop()

        src, dst = last_move
        self.turn *= -1

        if self.turn == Piece_GOAT and src == dst and captured_piece_position == -1 and self.goat_count < 20:
            self.board[dst] = Piece_EMPTY
            self.goat_positions[dst] = False
            self.goat_count += 1

            self.empty_positions[dst] = True

        elif self.turn == Piece_TIGER and captured_piece_position != -1:
            mid = captured_piece_position

            self.board[dst] = Piece_EMPTY
            self.board[mid] = Piece_GOAT
            self.board[src] = Piece_TIGER

            self.eaten_goat_count -= 1

            self.tiger_positions[dst] = False
            self.goat_positions[mid] = True
            self.tiger_positions[src] = True

            self.empty_positions[dst] = True
            self.empty_positions[mid] = False
            self.empty_positions[src] = False
        else:
            moving_piece = self.board[dst]
            self.board[dst] = Piece_EMPTY
            self.board[src] = moving_piece

            piece_list_to_update = self.tiger_positions if moving_piece == Piece_TIGER else self.goat_positions
            piece_list_to_update[dst] = False
            piece_list_to_update[src] = True

            self.empty_positions[dst] = True
            self.empty_positions[src] = False

    # vectorized get_legal_moves
    def get_legal_moves_np(self, turn=None):
        if not turn:
            turn = self.turn
        moves = []

        if turn == Piece_GOAT:
            if self.goat_count > 0:
                # Get all empty squares in one operation
                empty_indices = self.all_positions[self.empty_positions]
                moves.extend([(i, i) for i in empty_indices])
            else:
                # For every goat, find its empty neighbors
                goat_indices = self.all_positions[self.goat_positions]
                for src in goat_indices:
                    neighbors = self.graph_np[src]
                    # Vectorized check: which of my neighbors are empty?
                    empty_neighbors = neighbors[self.empty_positions[neighbors]]
                    moves.extend([(src, dst) for dst in empty_neighbors])
        else:  # TIGER
            tiger_indices = self.all_positions[self.tiger_positions]
            for src in tiger_indices:
                # 1. Standard Moves
                neighbors = self.graph_np[src]
                empty_neighbors = neighbors[self.empty_positions[neighbors]]
                moves.extend([(src, dst) for dst in empty_neighbors])

                # 2. Capture Moves
                possible_landings = self.capture_map_np[src]
                # Vectorized check: which of my landing spots are empty?
                valid_landings = possible_landings[self.empty_positions[possible_landings]]

                # Vectorized check: for these valid landings, is the midpoint a goat?
                for dst in valid_landings:
                    mid = self.capture_mid_map_np[(src, dst)]
                    if self.goat_positions[mid]:
                        moves.append((src, dst))
        return moves

    # non vectorized get legal moves
    # def get_legal_moves(self, turn=None):
    #     moves = []
    #
    #     if not turn:
    #         turn = self.turn
    #
    #     if turn == Piece_GOAT:
    #         if self.goat_count > 0:
    #             # Placement
    #             empty_indices = self.all_positions[self.empty_positions]
    #             for i in empty_indices:
    #                 moves.append((i, i))
    #         else:
    #             # Movement
    #             goat_indices = self.all_positions[self.goat_positions]
    #
    #             for src in goat_indices:
    #                 for dst in self.graph_np[src]:
    #                     if self.board[dst] == Piece_EMPTY:
    #                         moves.append((src, dst))
    #     else:
    #         tiger_indices = self.all_positions[self.tiger_positions]
    #         for src in tiger_indices:
    #             for adj in self.graph_np[src]:
    #                 # Movement
    #                 landing = 2 * adj - src  # adj + (adj - src)
    #                 if self.board[adj] == Piece_EMPTY:
    #                     moves.append((src, adj))
    #                 # Capture
    #                 elif self.board[adj] == Piece_GOAT and landing in self.graph_np[adj] and self.board[landing] == Piece_EMPTY:
    #                     moves.append((src, landing))
    #
    #     return moves

    def copy(self):
        board = np.copy(self.board)
        turn = self.turn
        goat_count = self.goat_count
        eaten_goat_count = self.eaten_goat_count
        copy_state = GameState(board, turn, goat_count, eaten_goat_count)
        return copy_state

    @staticmethod
    def tiger_board_accessibility(game_state):
        visited = np.zeros(25, dtype=np.bool_)
        tiger_positions = GameState.all_positions[game_state.tiger_positions]
        queue = deque(tiger_positions)

        board = game_state.board
        graph = GameState.graph_np
        capture_edges = GameState.capture_edges
        goats_on_board = 20 - \
            (game_state.eaten_goat_count + game_state.goat_count)

        while queue:
            pos = queue.popleft()

            if visited[pos]:
                continue
            visited[pos] = True

            for adj in graph[pos]:
                if board[adj] == Piece_EMPTY and not visited[adj]:
                    queue.append(adj)

            for adj, landing in capture_edges[pos]:
                # must be valid neighbor
                if board[adj] == Piece_GOAT and board[landing] == Piece_EMPTY and not visited[landing]:
                    queue.append(landing)

        visited_count = np.sum(visited)
        inaccessible_count = 25 - visited_count - goats_on_board
        return visited_count, inaccessible_count


if __name__ == "__main__":
    capture_edges = {
        pos: [(adj, landing) for adj in GameState.graph[pos]
              for landing in [2*adj - pos] if landing in GameState.graph[adj]] for pos in range(25)
    }
    # print(capture_edges)

    graph_np = [np.array(neighbors) for neighbors in GameState.graph.values()]

    capture_map_np = {
        src: np.array([landing for _, landing in edges])
        for src, edges in capture_edges.items()
    }
    capture_mid_map_np = {
        (src, landing): mid for src, edges in capture_edges.items() for mid, landing in edges
    }
    # print(capture_map_np.keys())
