import time
from collections import defaultdict
from bagchal import *
from symmetries import generate_d4_transforms, symmetry_prune_moves, score_triple_lock, TRIPLE_LOCK_MASKS_NP

EXACT_FLAG, ALPHA_FLAG, BETA_FLAG = 0, 1, 2
MAX_PLY = 64
CONTEMPT = -20.0


class TimeoutError(Exception):
    ...


class PV_Line(list):
    ...


class TTEntry:
    def __init__(self, state_key, depth, evaluation, flag, best_move):
        self.state_key = state_key
        self.depth = depth
        self.evaluation = evaluation
        self.flag = flag
        self.best_move = best_move


class TT:
    def __init__(self):
        self.entries = {}

    def put(self, entry: TTEntry):
        # always replace scheme
        # self.entries[entry.state_key] = entry

        # depth preferred scheme
        hashed_entry = self.entries.get(entry.state_key, None)
        if hashed_entry:
            if entry.depth >= hashed_entry.depth:
                self.entries[entry.state_key] = entry
            return
        self.entries[entry.state_key] = entry

    def get(self, state_key, depth, alpha, beta):
        entry = self.entries.get(state_key, None)
        if entry is None:
            return None, None

        if entry.depth >= depth:
            if entry.flag == EXACT_FLAG:
                return entry.evaluation, entry.best_move

            if entry.flag == ALPHA_FLAG and entry.evaluation <= alpha:
                return entry.evaluation, entry.best_move

            if entry.flag == BETA_FLAG and entry.evaluation >= beta:
                return entry.evaluation, entry.best_move

        return None, entry.best_move

    def clear(self):
        self.entries.clear()


class AlphaBetaAgent():
    def __init__(self, use_symmetry=True, logging=False, weights=None):
        # half move counter
        self.ply = 0
        self.game_state: BitboardGameState
        self.no_of_nodes = 0

        # killer moves
        # (ply, turn) -> killer1, killer2
        self.killers = {}
        # (square, turn) -> no of cutoffs
        self.history = defaultdict(int)
        # transposition table
        self.tt = TT()
        # current line of play
        self.tree_history = list()

        self.logging = logging

        self.use_symmetry = use_symmetry
        self.transforms = generate_d4_transforms() if use_symmetry else []

        self.weights = {
            'w_eat': 100.0,
            'w_potcap': 50.0,
            'w_mobility': 10.0,
            'w_trap': 10.0,
            'w_presence': 10.0,
            'w_inacc': 50.0,
            'triple_partial': 40.0,
            'triple_full': 200.0
        }
        if weights:
            self.weights.update(weights)

    def get_best_move(self, gs, game_history=[], time_limit=1.5):
        self.game_state = gs.copy()
        self.game_history = game_history

        # Time Management
        self.start_time = time.time()
        self.time_limit = time_limit

        self.killers.clear()
        self.history.clear()
        self.tt.clear()
        self.tree_history.clear()

        self.no_of_nodes = 0

        # We reset the ply as well because our iterative deepening loop will terminate mid search,
        # so for new position we must reset the ply as well.
        self.ply = 0

        alpha = float('-inf')
        beta = float('inf')

        # iterative deepening
        for current_depth in range(1, 100):

            root_pv = PV_Line()

            try:
                score = self.negamax(alpha, beta, current_depth, root_pv)

                best_move = root_pv[0]

                elapsed_time = time.time() - self.start_time
                if self.logging:
                    print(
                        f" > Depth: {current_depth}. Best Move: {best_move}. No of Nodes: {self.no_of_nodes}. Score: {score:.2f}. Time: {elapsed_time:.2f}s.")

                    print(" > PV:", end=" ")
                    for move in root_pv:
                        print(f"{move}", end=" ")
                    print()
                self.best_depth = current_depth

            except TimeoutError:

                if self.logging:
                    print(
                        f" > Timeout occurred at depth {current_depth}. No of Nodes: {self.no_of_nodes}.")
                break

        if self.logging:
            print(f" > Final Best Move: {best_move}.\n")
        return best_move

    def negamax(self, alpha, beta, depth, parent_pv: PV_Line):

        if self.no_of_nodes & 1023 == 0:
            if time.time() - self.start_time > self.time_limit:
                raise TimeoutError()

        self.no_of_nodes += 1

        # init PV length
        node_pv = PV_Line()

        state_key = self.game_state.key
        val, tt_move = self.tt.get(state_key, depth, alpha, beta)
        if val is not None:
            return val

        if depth == 0 or self.game_state.is_game_over or (self.ply > MAX_PLY - 1):
            val = self.evaluate()
            entry = TTEntry(state_key, depth, val, EXACT_FLAG, None)
            self.tt.put(entry)
            return val

        moves = self.game_state.get_legal_moves()

        if self.use_symmetry:  # and depth > 1:
            # Usually only worth pruning at higher depths
            # because the overhead of calculating symmetries is non-zero.
            moves = symmetry_prune_moves(
                self.game_state.tigers_bb,
                self.game_state.goats_bb,
                moves,
                self.transforms
            )

        hash_flag = ALPHA_FLAG
        best_move = None

        found_pv = False

        for i in range(len(moves)):

            self.pick_move(moves, i, tt_move)

            move = moves[i]

            self.game_state.make_move(move)
            self.ply += 1

            repeated = (self.game_state.key in self.tree_history or
                        self.game_state.key in self.game_history)
            if repeated:
                score = -(CONTEMPT * CONTEMPT)  # ALMOST NEVER REPEATS A MOVE
            else:
                self.tree_history.append(self.game_state.key)

                if found_pv:
                    score = -self.negamax(-alpha - 1, -
                                          alpha, depth - 1, node_pv)
                    if alpha < score < beta:  # check for failure
                        # another node is actually the PV node!
                        score = -self.negamax(-beta, -
                                              alpha, depth - 1, node_pv)
                else:
                    score = -self.negamax(-beta, -alpha, depth - 1, node_pv)

                self.tree_history.pop()

            self.ply -= 1
            self.game_state.unmake_move()

            # fail-hard beta cutoff
            if score >= beta:

                if self.is_quiet(move):
                    killer_key = (self.ply, self.game_state.turn)
                    killers = self.killers.get(killer_key, [None, None])

                    killers[1] = killers[0]
                    killers[0] = move

                    self.killers[killer_key] = killers

                    history_key = (self.game_state.turn, move[1])
                    self.history[history_key] += depth

                entry = TTEntry(state_key, depth, beta, BETA_FLAG, move)
                self.tt.put(entry)

                # node (move) fails high
                return beta

            # found a better move
            if score > alpha:

                # the move is PV move
                alpha = score

                found_pv = True

                best_move = move
                hash_flag = EXACT_FLAG

                # update PV table
                parent_pv.clear()
                parent_pv.append(move)
                parent_pv.extend(node_pv)

        # For testing the effectiveness of move ordering
        # if self.ply == 0:
        #     print(moves)

        # node (move) fails low i.e. score <= alpha
        entry = TTEntry(state_key, depth, alpha, hash_flag, best_move)
        self.tt.put(entry)

        return alpha

    def is_quiet(self, move):
        if self.game_state.turn == Piece_GOAT:
            return True
        src, dst = move
        # if src and dst are adjacent, then the move is a non-capture
        return MOVE_MASKS[src] & (1 << dst) != 0

    def pick_move(self, moves, current_idx, tt_move):
        best_score = float('-inf')
        best_idx = current_idx

        killer_key = (self.ply, self.game_state.turn)
        killer1, killer2 = self.killers.get(killer_key, [None, None])
        for j, move in enumerate(moves[current_idx:len(moves)]):
            score = self._score_move(move)
            # score = 0

            if move == tt_move:
                score += 5000
            elif move == killer1:
                score += 1000
            elif move == killer2:
                score += 900
            elif self.is_quiet(move):
                history_key = (self.game_state.turn, move[1])
                history_heuristic = self.history[history_key]
                score += history_heuristic

            if score > best_score:
                best_score = score
                best_idx = j + current_idx  # offset

        moves[current_idx], moves[best_idx] = moves[best_idx], moves[current_idx]

    def _score_move(self, move):
        if self.game_state.turn == Piece_TIGER:
            return tiger_priority(self.game_state.tigers_bb, self.game_state.goats_bb, move, MOVE_MASKS_NP, CAPTURE_COUNTS, CAPTURE_MASKS_NP)
        else:
            return goat_priority(self.game_state.tigers_bb, self.game_state.goats_bb, move, MOVE_MASKS_NP, CAPTURE_COUNTS, CAPTURE_MASKS_NP, OUTER_EDGE_MASK, STRATEGIC_MASK)

    def evaluate(self):
        """
        Positive -> TIGER advantage, Negative -> GOAT advantage.
        """

        state = self.game_state

        is_placement = state.goats_to_place > 0

        eat_max = 4  # before win
        potential_capture_max = 5
        inaccessible_max = 4

        trap_max = 3  # before win
        goat_presence_max = 20
        tiger_mobility_max = 25

        # p_mobility = 0 if is_placement else w_mobility

        if state.is_game_over:
            result = state.get_result
            score = 2000 - self.ply
            return score * result * state.turn

        trapped = state.trapped_tiger_count
        eaten = state.goats_eaten
        goat_left = state.goats_to_place
        goats_on_board = 20 - (eaten + goat_left)

        eaten_score = eaten / eat_max

        potential_captures = self._count_potential_captures()
        potential_capture_score = potential_captures / potential_capture_max
        potential_capture_score = min(1, potential_capture_score)

        trap_score = trapped / trap_max
        goat_presence_score = goats_on_board / goat_presence_max
        accessible, inaccessible = self._get_tiger_accessibility()

        inaccessibility_score = inaccessible / inaccessible_max
        tiger_mobility_score = accessible / tiger_mobility_max
        inaccessibility_score = min(1, inaccessibility_score)

        triple_score = 0
        match_count = score_triple_lock(
            state.tigers_bb, TRIPLE_LOCK_MASKS_NP)

        # This value needs tuning!
        if match_count == 3:
            triple_score += self.weights["triple_full"]
        elif match_count == 2:
            triple_score += self.weights["triple_partial"]

        tiger_score = (eaten_score * self.weights["w_eat"] +
                       potential_capture_score * self.weights["w_potcap"] +
                       tiger_mobility_score * self.weights["w_mobility"] +
                       triple_score)

        goat_score = (trap_score * self.weights["w_trap"] +
                      goat_presence_score * self.weights["w_presence"] +
                      inaccessibility_score * self.weights["w_inacc"])

        if inaccessible >= 1 and eaten == 0 and is_placement:
            # this is a sure win for goat if the goat can keep placing pieces without losing any
            # we must encourage this line of play for goat
            goat_score += 1000

        final_evaluation = tiger_score - goat_score
        return final_evaluation * state.turn

    def new_evaluate(self):
        """
        Positive -> TIGER advantage, Negative -> GOAT advantage.
        """
        # Parameters for static board evaluation
        # Tiger advantage:
        #   more goats captured,
        #   more than two potential captures (sure capture)
        #   triple lock (but usable)
        #   center control
        # Goat advantage:
        #   less goat captured
        #   more goats on board (but this typically will continue increasing through the placement phase)
        #   cantonments or inaccessible positions (for tigers) -> gives chance to move pieces safely and is the only way the goat can win
        #   central control (of course lone goat at the center is useless, so central control must be achieved with proper backup)

    def _count_potential_captures(self):

        occupied_bb = self.game_state.tigers_bb | self.game_state.goats_bb
        empty_bb = ~occupied_bb & BOARD_MASK

        capture_opportunities = 0

        for tiger in extract_indices_fast(self.game_state.tigers_bb):
            for mid_mask, land_mask in CAPTURE_MASKS[tiger]:
                if (self.game_state.goats_bb & mid_mask) and (empty_bb & land_mask):
                    capture_opportunities += 1

        return capture_opportunities

    def _get_tiger_accessibility(self):
        accessible, inaccessible = tiger_board_accessibility(
            self.game_state.tigers_bb, self.game_state.goats_bb,
            MOVE_MASKS_NP, CAPTURE_COUNTS, CAPTURE_MASKS_NP)
        return accessible, inaccessible
