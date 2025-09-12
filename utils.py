#
# @dataclass
# from dataclasses import dataclass
# class HeuristicParams:
#     """Learnable parameters for move evaluation and state evaluation"""
#     # Tiger parameters
#     tiger_capture_bonus: float = 3.0
#     tiger_potential_capture_bonus: float = 2.0
#     tiger_block_penalty: float = 3.0
#
#     # Goat parameters
#     goat_sacrifice_penalty: float = 3.0
#     goat_clustering_bonus: float = 0.5
#     goat_strategic_position_bonus: float = 0.5
#     goat_outer_edge_bonus: float = 0.5
#
#     # State evaluation
#     w_eat: float = 1.5
#     w_potcap: float = 1.5
#     w_mobility: float = 1
#     w_trap: float = 1.5
#     w_presence: float = 1
#     w_inacc: float = 1.5
#
# MOVE_MASKS = [0] * 25
# for src, dsts in graph.items():
#     for dst in dsts:
#         MOVE_MASKS[src] |= (1 << dst)
#
# CAPTURE_MASKS = [[] for _ in range(25)]
# for src, edges in capture_edges.items():
#     for mid, land in edges:
#         CAPTURE_MASKS[src].append((1 << mid, 1 << land))


# def get_set_bits(bitboard):
#     """Generator that yields the index of each set bit in a bitboard."""
#     while bitboard > 0:
#         lsb = bitboard & -bitboard  # Isolate the least significant bit
#         idx = lsb.bit_length() - 1
#         yield idx
#         bitboard &= ~lsb  # Clear the LSB

# def extract_indices(bitboard):
#     indices = []
#     for set_bits in get_set_bits(bitboard):
#         indices.append(set_bits)
#     return indices

# @njit
# def tiger_board_accessibility(tigers_bb: int, goats_bb: int, MOVE_MASKS, CAPTURE_COUNTS, CAPTURE_MASKS):
#     occupied_bb = tigers_bb | goats_bb
#     empty_bb = (~occupied_bb) & BOARD_MASK
#
#     frontier_bb = tigers_bb
#     visited_bb = frontier_bb
#
#     while frontier_bb != 0:
#         newly_reached_bb = 0
#
#         # --- inline iteration over frontier set bits ---
#         fb = frontier_bb
#         while fb != 0:
#             lsb = fb & -fb
#             src = math.frexp(lsb)[1] - 1   # bit index
#             fb &= fb - 1
#
#             # adjacent moves
#             newly_reached_bb |= MOVE_MASKS[src] & empty_bb
#
#             # capture moves
#             for j in range(CAPTURE_COUNTS[src]):
#                 mid_mask = CAPTURE_MASKS[src, j, 0]
#                 land_mask = CAPTURE_MASKS[src, j, 1]
#                 if (goats_bb & mid_mask) != 0 and (empty_bb & land_mask) != 0:
#                     newly_reached_bb |= land_mask
#
#         new_frontier_bb = newly_reached_bb & (~visited_bb)
#         if new_frontier_bb == 0:
#             break
#
#         visited_bb |= new_frontier_bb
#         frontier_bb = new_frontier_bb
#
#     visited_count = popcount(visited_bb)
#     goats_on_board = popcount(goats_bb)
#
#     accessible_count = visited_count - 4   # remove 4 tiger positions
#     inaccessible_count = 25 - visited_count - goats_on_board
#     return accessible_count, inaccessible_count

# def display_board(game_state):
#     board = game_state.board
#     piece = game_state.piece
#     print("-"*26)
#     for i, cell in enumerate(board):
#         if i % 5 == 0:
#             print("|", end=" ")
#         print(piece[cell], end=" | ")
#         if (i+1) % 5 == 0:
#             print()
#             print("-"*26)
#
# def print(self):
# Take a BitboardGameState
#     tiger_positions = extract_indices_fast(self.tigers_bb)
#     goat_positions = extract_indices_fast(self.goats_bb)
#     board = [0] * 25
#     for pos in tiger_positions:
#         board[pos] = Piece_TIGER
#     for pos in goat_positions:
#         board[pos] = Piece_GOAT
#     gs = GameState(board=board, turn=self.turn,
#                    goat_count=self.goats_to_place,
#                    eaten_goat_count=self.goats_eaten)
#     display_board(gs)
#     print(gs)

# @staticmethod
# def _tiger_priority(game_state, move):
#     params = HeuristicParams
#     priority_score = 0
#     src, dst = move
#
#     tigers_bb = game_state.tigers_bb
#     goats_bb = game_state.goats_bb
#
#     occupied_bb = tigers_bb | goats_bb
#     empty_bb = ~occupied_bb & BOARD_MASK
#
#     # Capture
#     if not (MOVE_MASKS[src] & (1 << dst)):
#         priority_score += params.tiger_capture_bonus
#
#     # Potential Capture
#     for mid_mask, land_mask in CAPTURE_MASKS[dst]:
#         if (goats_bb & mid_mask) and (empty_bb & land_mask):
#             priority_score += params.tiger_potential_capture_bonus
#
#     is_blocking = False
#     # for tiger in get_set_bits(tigers_bb & ~(1 << src)):
#     for tiger in extract_indices_fast(tigers_bb & ~(1 << src)):
#         for mid_mask, land_mask in CAPTURE_MASKS[tiger]:
#             # we know dst is empty as the move is valid
#             if (goats_bb & mid_mask) and (1 << dst) & land_mask:
#                 # moving the tiger to dst will block an available capture
#                 priority_score -= params.tiger_block_penalty
#                 is_blocking = True
#                 break
#         if is_blocking:
#             break
#
#     return priority_score + np.random.random()
#
# @staticmethod
# def _goat_priority(game_state, move):
#     params = HeuristicParams
#     src, dst = move
#     is_placement_phase = src == dst
#     priority_score = 0
#
#     tigers_bb = game_state.tigers_bb
#     goats_bb = game_state.goats_bb
#
#     occupied_bb = tigers_bb | goats_bb
#     empty_bb = ~occupied_bb & BOARD_MASK
#
#     neighboring_tigers = MOVE_MASKS[dst] & tigers_bb
#     neighboring_goats = MOVE_MASKS[dst] & goats_bb
#
#     is_attacked = False
#     # simulate the move
#     # there has to be better way tho!!
#     goats_bb ^= (1 << src) | (1 << dst)
#     occupied_bb = tigers_bb | goats_bb
#     empty_bb = ~occupied_bb & BOARD_MASK
#
#     # for tiger in get_set_bits(neighboring_tigers):
#     for tiger in extract_indices_fast(neighboring_tigers):
#         for mid_mask, land_mask in CAPTURE_MASKS[tiger]:
#             if ((1 << dst) & mid_mask) and (empty_bb & land_mask):
#                 priority_score -= params.goat_sacrifice_penalty
#                 is_attacked = True
#         if is_attacked:
#             break
#
#     # Clustering
#     # no_of_neighboring_goats = bin(neighboring_goats).count('1') - 1
#     no_of_neighboring_goats = popcount(neighboring_goats) - 1
#     priority_score += no_of_neighboring_goats * params.goat_clustering_bonus
#
#     # useful when there's nothing much going on the board
#     strategic_positions = {2, 10, 14, 22}
#     outer_eddge = {0, 1, 2, 3, 4, 5, 10, 15, 20, 21, 22, 23, 24, 9, 14, 19}
#     if is_placement_phase and dst in strategic_positions:
#         priority_score += params.goat_strategic_position_bonus
#     elif dst in outer_eddge:
#         priority_score += params.goat_outer_edge_bonus
#
#     return priority_score + np.random.random()
