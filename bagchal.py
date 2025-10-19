import math
from os import urandom
from numba import njit
import numpy as np


# The personality of the Agent can be tuned by adjusting these parameters

# Tiger Parameters
tiger_capture_bonus: float = 2000.0
tiger_potential_capture_bonus: float = 1500.0
tiger_block_penalty: float = 1.5

# Goat parameters
goat_sacrifice_penalty: float = 5.0
goat_block_capture_bonus: float = 2.0
goat_clustering_bonus: float = 1.0
goat_strategic_position_bonus: float = 1.0
goat_outer_edge_bonus: float = 1.0

# State evaluation
w_eat: float = 100
w_potcap: float = 50
w_mobility: float = 10

w_trap: float = 10
w_presence: float = 10
w_inacc: float = 50


# these are only for turns and printing the board
# in rest of the code:
# for tigers_bb and goats_bb
# 1 = piece is present in a position
# 0 = peice is absent in a position
# for empty_bb
# 1 = position is empty
# 1 = position is occupied
Piece_GOAT = -1
Piece_EMPTY = 0
Piece_TIGER = 1

BOARD_MASK = (1 << 25) - 1

_graph = {0:  [1, 5, 6], 1:  [0, 2, 6], 2:  [1, 3, 6, 7, 8], 3:  [2, 4, 8], 4:  [3, 8, 9],
          5:  [0, 6, 10], 6:  [0, 1, 2, 5, 7, 10, 11, 12], 7:  [2, 6, 8, 12], 8:  [2, 3, 4, 7, 9, 12, 13, 14], 9:  [4, 8, 14],
          10: [5, 6, 11, 15, 16], 11: [6, 10, 12, 16], 12: [6, 7, 8, 11, 13, 16, 17, 18], 13: [8, 12, 14, 18], 14: [8, 9, 13, 18, 19],
          15: [10, 16, 20], 16: [10, 11, 12, 15, 17, 20, 21, 22], 17: [12, 16, 18, 22], 18: [12, 13, 14, 17, 19, 22, 23, 24], 19: [14, 18, 24],
          20: [15, 16, 21], 21: [16, 20, 22], 22: [16, 17, 18, 21, 23], 23: [18, 22, 24], 24: [18, 19, 23]}

_capture_edges = {0: [(1, 2), (5, 10), (6, 12)], 1: [(2, 3), (6, 11)], 2: [(1, 0), (3, 4), (6, 10), (7, 12), (8, 14)], 3: [(2, 1), (8, 13)], 4: [(3, 2), (8, 12), (9, 14)],
                  5: [(6, 7), (10, 15)], 6: [(7, 8), (11, 16), (12, 18)], 7: [(6, 5), (8, 9), (12, 17)], 8: [(7, 6), (12, 16), (13, 18)], 9: [(8, 7), (14, 19)],
                  10: [(5, 0), (6, 2), (11, 12), (15, 20), (16, 22)], 11: [(6, 1), (12, 13), (16, 21)], 12: [(6, 0), (7, 2), (8, 4), (11, 10), (13, 14), (16, 20), (17, 22), (18, 24)],
                  13: [(8, 3), (12, 11), (18, 23)], 14: [(8, 2), (9, 4), (13, 12), (18, 22), (19, 24)], 15: [(10, 5), (16, 17)], 16: [(11, 6), (12, 8), (17, 18)],
                  17: [(12, 7), (16, 15), (18, 19)], 18: [(12, 6), (13, 8), (17, 16)], 19: [(14, 9), (18, 17)], 20: [(15, 10), (16, 12), (21, 22)], 21: [(16, 11), (22, 23)],
                  22: [(16, 10), (17, 12), (18, 14), (21, 20), (23, 24)], 23: [(18, 13), (22, 21)], 24: [(18, 12), (19, 14), (23, 22)]}


MOVE_MASKS = [0] * 25
for src, dsts in _graph.items():
    for dst in dsts:
        MOVE_MASKS[src] |= (1 << dst)

CAPTURE_MASKS = [[] for _ in range(25)]
for src, edges in _capture_edges.items():
    for mid, land in edges:
        CAPTURE_MASKS[src].append((1 << mid, 1 << land))


# numpy ones for numba
MOVE_MASKS_NP = np.zeros(25, dtype=np.int64)
for src, dsts in _graph.items():
    mask = 0
    for dst in dsts:
        mask |= (1 << dst)
    MOVE_MASKS_NP[src] = mask

MAX_CAPTURES = max(len(edges) for edges in _capture_edges.values())
CAPTURE_MASKS_NP = np.zeros((25, MAX_CAPTURES, 2), dtype=np.int64)
CAPTURE_COUNTS = np.zeros(25, dtype=np.int64)
for src, edges in _capture_edges.items():
    CAPTURE_COUNTS[src] = len(edges)
    for j, (mid, land) in enumerate(edges):
        CAPTURE_MASKS_NP[src, j, 0] = 1 << mid  # mid mask for the src
        CAPTURE_MASKS_NP[src, j, 1] = 1 << land  # land mask for the src

_outer_eddge = (0, 1, 2, 3, 4, 5, 10, 15, 20, 21, 22, 23, 24, 9, 14, 19)
OUTER_EDGE_MASK = np.int64(0)
for pos in _outer_eddge:
    OUTER_EDGE_MASK |= (1 << pos)

_strategic_positions = (2, 10, 14, 22)
STRATEGIC_MASK = np.int64(0)
for pos in _strategic_positions:
    STRATEGIC_MASK |= (1 << pos)


def random_u64():
    return np.int64(int.from_bytes(urandom(8)) & ((1 << 63)-1))


# uniq random numbers for 2 types of pieces and 25 positions they can occupy
ZOBRIST_PIECE = np.zeros((2, 25), dtype=np.int64)
for piece in range(2):
    for pos in range(25):
        ZOBRIST_PIECE[piece, pos] = random_u64()

# random number for side to move
ZOBRIST_SIDE = random_u64()
# goats_to_place = 0 to 20
# this is relevant because, we're gonna be using transposition table
# to store the best move for the bound as well and moves are different
# for goats during placement_phase and movement_phase
ZOBRIST_TO_PLACE = np.array([random_u64()for _ in range(21)], dtype=np.int64)
ZOBRIST_EATEN = np.array([random_u64() for _ in range(6)], dtype=np.int64)


@njit
def compute_zobrist(tigers_bb: int, goats_bb: int, side: int, goats_eaten: int, goats_to_place: int) -> int:
    h = np.int64(0)
    while tigers_bb:
        lsb = tigers_bb & -tigers_bb
        tiger = math.frexp(lsb)[1] - 1
        h ^= ZOBRIST_PIECE[0, tiger]
        tigers_bb &= tigers_bb - 1

    while goats_bb:
        lsb = goats_bb & -goats_bb
        goat = math.frexp(lsb)[1] - 1
        h ^= ZOBRIST_PIECE[1, goat]
        goats_bb &= goats_bb - 1

    h ^= ZOBRIST_TO_PLACE[goats_to_place]
    h ^= ZOBRIST_EATEN[goats_eaten]
    if side == Piece_TIGER:
        h ^= ZOBRIST_SIDE
    return h


@njit
def extract_indices_fast(bitboard: int):
    indices = []
    while bitboard:
        lsb = bitboard & -bitboard
        idx = math.frexp(lsb)[1] - 1
        indices.append(idx)
        bitboard &= ~lsb
    return indices


@njit
def popcount(x: int) -> int:
    c = 0
    while x:
        x &= x - 1
        c += 1
    return c


class BitboardGameState:
    __slots__ = ['tigers_bb', 'goats_bb', 'turn',
                 'goats_to_place', 'goats_eaten', 'history', 'zob_hash']
    piece = {
        -1: "🐐", 0: '  ', 1: "🐅"
    }

    def __init__(self,
                 # Initial tiger positions: 0, 4, 20, 24
                 tigers_bb=(1 << 0) | (1 << 4) | (1 << 20) | (1 << 24),
                 goats_bb=0,
                 turn=Piece_GOAT,
                 goats_to_place=20,
                 goats_eaten=0):

        self.tigers_bb = tigers_bb
        self.goats_bb = goats_bb
        self.turn = turn
        self.goats_to_place = goats_to_place
        self.goats_eaten = goats_eaten
        self.history = []
        self.zob_hash = compute_zobrist(
            self.tigers_bb, self.goats_bb, self.turn, self.goats_eaten, self.goats_to_place)

    def __repr__(self) -> str:
        return f"Turn: {self.piece[self.turn]}, Goat Left: {self.goats_to_place}, Eaten Goat: {self.goats_eaten}, Trapped Tiger: {self.trapped_tiger_count}"

    @property
    def key(self):
        return self.zob_hash

    @property
    def get_result(self):
        if self.goats_eaten >= 5:
            return Piece_TIGER
        if self.trapped_tiger_count == 4:
            return Piece_GOAT
        if not self.get_legal_moves():
            return self.turn * -1
        return None

    @property
    def is_game_over(self):
        return self.get_result is not None

    def _is_trapped(self, tiger, empty_bb):
        if MOVE_MASKS[tiger] & empty_bb:
            return False

        # left if we decide to njit this method too
        # for j in range(CAPTURE_COUNTS[tiger]):
        #     mid_mask = CAPTURE_MASKS_NP[tiger, j, 0]
        #     land_mask = CAPTURE_MASKS_NP[tiger, j, 1]
        #     if (self.goats_bb & mid_mask) and (empty_bb & land_mask):
        #         return False

        for mid_mask, land_mask in CAPTURE_MASKS[tiger]:
            if (self.goats_bb & mid_mask) and (empty_bb & land_mask):
                return False

        return True

    @property
    def trapped_tiger_count(self):
        occupied_bb = self.tigers_bb | self.goats_bb
        empty_bb = ~occupied_bb & BOARD_MASK
        count = 0

        for tiger in extract_indices_fast(self.tigers_bb):
            if self._is_trapped(tiger, empty_bb):
                count += 1
        return count

    def get_legal_moves(self, only_captures=False):
        moves = []
        occupied_bb = self.tigers_bb | self.goats_bb
        empty_bb = ~occupied_bb & BOARD_MASK

        if self.turn == Piece_GOAT:
            if self.goats_to_place > 0:
                # Placement
                for dst in extract_indices_fast(empty_bb):
                    moves.append((dst, dst))
                return moves
            else:
                # Movement
                for src in extract_indices_fast(self.goats_bb):
                    moves.extend(self._get_standard_moves(src, empty_bb))
                return moves

        else:
            for src in extract_indices_fast(self.tigers_bb):

                moves.extend((self._get_capture_moves(src, empty_bb)))

                if not only_captures:
                    moves.extend(self._get_standard_moves(src, empty_bb))

            return moves

    def _get_standard_moves(self, src, empty_bb):
        moves = []
        # adjacent to src and empty
        possible_moves = MOVE_MASKS[src] & empty_bb
        for dst in extract_indices_fast(possible_moves):
            moves.append((src, dst))
        return moves

    def _get_capture_moves(self, src, empty_bb):
        # this move is only meant for tigers
        moves = []
        assert self.tigers_bb & (1 << src)

        # for j in range(CAPTURE_COUNTS[src]):
        #     mid_mask = CAPTURE_MASKS_NP[src, j, 0]
        #     land_mask = CAPTURE_MASKS_NP[src, j, 1]

        for mid_mask, land_mask in CAPTURE_MASKS[src]:
            if (self.goats_bb & mid_mask) and (empty_bb & land_mask):
                dst = math.frexp(land_mask)[1] - 1
                moves.append((src, dst))

        return moves

    def make_move(self, move):
        src, dst = move
        captured_piece_position = -1

        self.zob_hash ^= ZOBRIST_SIDE

        occupied_bb = (self.tigers_bb | self.goats_bb)

        if self.turn == Piece_GOAT and self.goats_to_place > 0:
            # Placement
            assert not occupied_bb & (1 << dst)

            # update hash
            self.zob_hash ^= ZOBRIST_TO_PLACE[self.goats_to_place]
            self.zob_hash ^= ZOBRIST_TO_PLACE[self.goats_to_place-1]
            self.zob_hash ^= ZOBRIST_PIECE[1, dst]

            # make move
            self.goats_bb |= (1 << dst)
            self.goats_to_place -= 1

        elif MOVE_MASKS[src] & (1 << dst):
            # Movement
            # src and dst are adjacent

            assert not occupied_bb & (1 << dst)
            move_mask = (1 << src) | (1 << dst)

            if self.turn == Piece_TIGER:
                assert self.tigers_bb & (1 << src)
                # update hash
                self.zob_hash ^= ZOBRIST_PIECE[0, src]
                self.zob_hash ^= ZOBRIST_PIECE[0, dst]

                # make move
                self.tigers_bb ^= move_mask
            elif self.turn == Piece_GOAT:
                assert self.goats_bb & (1 << src)
                self.zob_hash ^= ZOBRIST_PIECE[1, src]
                self.zob_hash ^= ZOBRIST_PIECE[1, dst]

                self.goats_bb ^= move_mask

        else:
            # It can only be a Capture move at this point
            # but we still make 100% sure
            assert self.turn == Piece_TIGER
            mid = (src + dst) // 2
            assert self.tigers_bb & (1 << src)
            assert self.goats_bb & (1 << mid)
            assert not occupied_bb & (1 << dst)

            move_mask = (1 << src) | (1 << dst)

            # update hash
            self.zob_hash ^= ZOBRIST_PIECE[0, src]
            self.zob_hash ^= ZOBRIST_PIECE[1, mid]
            self.zob_hash ^= ZOBRIST_PIECE[0, dst]
            self.zob_hash ^= ZOBRIST_EATEN[self.goats_eaten]
            self.zob_hash ^= ZOBRIST_EATEN[self.goats_eaten+1]

            # make move
            self.tigers_bb ^= move_mask
            self.goats_bb &= ~(1 << mid)

            self.goats_eaten += 1
            captured_piece_position = mid

        self.history.append((move, captured_piece_position))
        self.turn *= -1

    def unmake_move(self):
        if not self.history:
            return

        last_move, captured_piece_position = self.history.pop()

        src, dst = last_move

        self.zob_hash ^= ZOBRIST_SIDE
        self.turn *= -1

        if (self.turn == Piece_GOAT and src == dst
                and captured_piece_position == -1 and self.goats_to_place < 20):
            # update hash
            self.zob_hash ^= ZOBRIST_TO_PLACE[self.goats_to_place]
            self.zob_hash ^= ZOBRIST_TO_PLACE[self.goats_to_place+1]
            self.zob_hash ^= ZOBRIST_PIECE[1, dst]

            # remove goat from dst
            self.goats_bb &= ~(1 << dst)
            self.goats_to_place += 1

        elif self.turn == Piece_TIGER and captured_piece_position != -1:
            mid = captured_piece_position

            # update hash
            self.zob_hash ^= ZOBRIST_PIECE[0, dst]
            self.zob_hash ^= ZOBRIST_PIECE[1, mid]
            self.zob_hash ^= ZOBRIST_PIECE[0, src]
            self.zob_hash ^= ZOBRIST_EATEN[self.goats_eaten]
            self.zob_hash ^= ZOBRIST_EATEN[self.goats_eaten-1]

            # move from dst to src
            self.tigers_bb ^= (1 << dst) | (1 << src)
            # replace goat at mid
            self.goats_bb |= (1 << mid)
            self.goats_eaten -= 1
        else:
            move_mask = (1 << dst) | (1 << src)
            if self.turn == Piece_TIGER:
                # update hash
                self.zob_hash ^= ZOBRIST_PIECE[0, dst]
                self.zob_hash ^= ZOBRIST_PIECE[0, src]

                # move from dst to src
                self.tigers_bb ^= move_mask
            else:
                # update hash
                self.zob_hash ^= ZOBRIST_PIECE[1, dst]
                self.zob_hash ^= ZOBRIST_PIECE[1, src]

                # move from dst to src
                self.goats_bb ^= move_mask

    def copy(self):
        tigers_bb = self.tigers_bb
        goats_bb = self.goats_bb
        turn = self.turn
        goats_to_place = self.goats_to_place
        goats_eaten = self.goats_eaten
        copy_state = BitboardGameState(tigers_bb,
                                       goats_bb,
                                       turn,
                                       goats_to_place,
                                       goats_eaten)
        return copy_state

    def is_quiet(self, move):
        # for tiger an unquiet move is a capture move
        # for goat an unquiet move is one that walks into a guaranteed capture
        src, dst = move
        is_placment = src == dst
        occupied_bb = self.tigers_bb | self.goats_bb
        empty_bb = ~occupied_bb & BOARD_MASK
        if self.turn == Piece_TIGER:
            # a non capture move has src adjacent to dst
            return MOVE_MASKS[src] & (1 << dst) != 0
        if self.turn == Piece_GOAT:
            # one case in placement:
            #  a tiger adjacent to the dst can capture the piece
            neighboring_tigers = self.tigers_bb & MOVE_MASKS[dst]
            if is_placment:
                for tiger in extract_indices_fast(neighboring_tigers):
                    for mid, land in CAPTURE_MASKS[tiger]:
                        if mid == dst and (1 << land) & empty_bb:
                            return False
            # two cases in movement:
            else:
                for tiger in extract_indices_fast(neighboring_tigers):
                    for mid, land in CAPTURE_MASKS[tiger]:
                        # 1) goat moves from landing to mid
                        if src == land and mid == dst:
                            return False

                        # 2) goat moves into mid and landing is empty
                        if mid == dst and (1 << land) & empty_bb:
                            return False
                    # there's a third case in movement where a goat can unblock a capture but it's inefficient to calculate
            return True


@njit
def tiger_board_accessibility(tigers_bb: int, goats_bb: int, MOVE_MASKS, CAPTURE_COUNTS, CAPTURE_MASKS):

    occupied_bb = tigers_bb | goats_bb
    empty_bb = ~(occupied_bb) & BOARD_MASK

    frontier_bb = tigers_bb
    visited_bb = frontier_bb

    while frontier_bb:
        newly_reached_bb = 0

        # all positions adjacent to all squares in the frontier
        for src in extract_indices_fast(frontier_bb):
            newly_reached_bb |= MOVE_MASKS[src] & empty_bb

        # filter out the occupied positions
        newly_reached_bb &= empty_bb

        # all captures possible from all squares in the frontier
        for src in extract_indices_fast(frontier_bb):
            for j in range(CAPTURE_COUNTS[src]):
                mid_mask = CAPTURE_MASKS[src, j, 0]
                land_mask = CAPTURE_MASKS[src, j, 1]
                if (goats_bb & mid_mask) and (empty_bb & land_mask):
                    newly_reached_bb |= land_mask

        new_frontier_bb = newly_reached_bb & (~visited_bb)

        if not new_frontier_bb:
            break

        visited_bb |= new_frontier_bb

        frontier_bb = new_frontier_bb

    visited_count = popcount(visited_bb)
    goats_on_board = popcount(goats_bb)

    accessible_count = visited_count - 4  # remove the 4 positions of 4 tigers
    inaccessible_count = 25 - visited_count - goats_on_board
    return accessible_count, inaccessible_count


@njit
def tiger_priority(tigers_bb: int, goats_bb: int, move, MOVE_MASKS, CAPTURE_COUNTS, CAPTURE_MASKS):
    priority_score = 0
    src, dst = move

    occupied_bb = tigers_bb | goats_bb
    empty_bb = ~occupied_bb & BOARD_MASK

    # Capture
    if (MOVE_MASKS[src] & (1 << dst)) == 0:
        priority_score += tiger_capture_bonus

    # Potential Capture
    for j in range(CAPTURE_COUNTS[dst]):
        mid_mask = CAPTURE_MASKS[dst, j, 0]
        land_mask = CAPTURE_MASKS[dst, j, 1]
        if (goats_bb & mid_mask) and (empty_bb & land_mask):
            priority_score += tiger_potential_capture_bonus

    # fb = tigers_bb & ~(1 << src)
    # blocked = False
    # while fb != 0 and not blocked:
    #     lsb = fb & -fb
    #     tiger = math.frexp(lsb)[1] - 1  # extracting the index of tiger
    #     fb &= fb - 1
    #     for j in range(CAPTURE_COUNTS[tiger]):
    #         mid_mask = CAPTURE_MASKS[tiger, j, 0]
    #         land_mask = CAPTURE_MASKS[tiger, j, 1]
    #         if (goats_bb & mid_mask) and ((1 << dst) & land_mask):
    #             # discourage blocking potential capture
    #             priority_score -= tiger_block_penalty
    #             blocked = True
    #             break
    #         elif (goats_bb & mid_mask) and ((1 << src) & land_mask):
    #             # encourage moving away from a blocked potential capture
    #             priority_score += tiger_block_penalty
    #             blocked = True

    return priority_score


@njit
def goat_priority(tigers_bb: int, goats_bb: int, move, MOVE_MASKS, CAPTURE_COUNTS, CAPTURE_MASKS, OUTER_EDGE_MASK, STRATEGIC_MASK):
    src, dst = move
    is_placement_phase = src == dst
    priority_score: int = 0

    occupied_bb = tigers_bb | goats_bb
    empty_bb = ~occupied_bb & BOARD_MASK

    neighboring_tigers = MOVE_MASKS[dst] & tigers_bb
    neighboring_goats = MOVE_MASKS[dst] & goats_bb

    attacked = False
    # simulate the move
    goats_bb ^= (1 << src) | (1 << dst)
    occupied_bb = tigers_bb | goats_bb
    empty_bb = ~occupied_bb & BOARD_MASK

    fb = neighboring_tigers
    while fb != 0 and not attacked:
        lsb = fb & -fb
        tiger = math.frexp(lsb)[1] - 1  # extracting the index of tiger
        fb &= fb - 1
        for j in range(CAPTURE_COUNTS[tiger]):
            mid_mask = CAPTURE_MASKS[tiger, j, 0]
            land_mask = CAPTURE_MASKS[tiger, j, 1]
            if ((1 << dst) & mid_mask) and (empty_bb & land_mask):
                priority_score -= goat_sacrifice_penalty
                attacked = True
                break

    # unmake
    goats_bb ^= (1 << src) | (1 << dst)
    occupied_bb = tigers_bb | goats_bb
    empty_bb = ~occupied_bb & BOARD_MASK

    blocks = False
    for tiger in extract_indices_fast(tigers_bb):
        for j in range(CAPTURE_COUNTS[tiger]):
            mid_mask = CAPTURE_MASKS[tiger, j, 0]
            land_mask = CAPTURE_MASKS[tiger, j, 1]
            if (goats_bb & mid_mask) and ((1 << dst) & land_mask):
                blocks = True
                priority_score += goat_block_capture_bonus
                break
        if blocks:
            break

    # Clustering
    if is_placement_phase:
        no_of_neighboring_goats = popcount(neighboring_goats)

        priority_score += no_of_neighboring_goats * \
            goat_clustering_bonus

        if ((1 << dst) & STRATEGIC_MASK) != 0:
            priority_score += goat_strategic_position_bonus
        elif ((1 << dst) & OUTER_EDGE_MASK) != 0:
            priority_score += goat_outer_edge_bonus

    return priority_score

#
# if __name__ == "__main__":
#     gs = BitboardGameState()
#     print(gs.key)
#     gs.make_move((2, 2))
#     print(gs.key)
#     gs.unmake_move()
#     print(gs.key)
