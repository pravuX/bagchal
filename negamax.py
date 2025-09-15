import time
from bagchal import *

# type of evaluation that is stored in the transposition_table
exact_flag, alpha_flag, beta_flag = 0, 1, 2


class TimeoutError(Exception):
    pass


class AlphaBetaAgent():

    # Tiger is the maximizing player
    # Goat is the minimizing player

    def __init__(self):
        self.no_of_nodes = 0
        self.start_time = 0.0
        self.time_limit = 0.0
        self.window = 10  # the width of the aspiration window
        self.contempt = -5

        # depth -> killer move 1, killer move 2
        self.killers = {}
        # (turn, move) -> no of cutoffs caused
        self.history_heuristic = {}
        # state_key -> (depth, evaluation, flag, best_move)
        self.transposition_table = {}
        # state_key -> evaluation
        self.previous_evaluations = {}
        # state_key -> (accessible, inaccessible)
        self.accessibility_cache = {}
        # state_key -> potential_capture_score
        self.potential_captures_cache = {}
        # state_key -> legal moves for the player to move(turn)
        self.legal_moves_cache = {}

    def get_best_move(self, gs, game_history=None, time_limit=1.5):
        self.transposition_table.clear()
        self.time_limit = time_limit
        self.game_history = game_history

        if len(self.accessibility_cache) > 50_000:
            self.accessibility_cache.clear()
        if len(self.potential_captures_cache) > 50_000:
            self.potential_captures_cache.clear()
        if len(self.previous_evaluations) > 50_000:
            self.previous_evaluations.clear()
        if len(self.legal_moves_cache) > 50_000:
            self.legal_moves_cache.clear()

        self.start_time = time.time()
        best_move_so_far = None

        game_state = gs.copy()

        initial_history = [game_state.key]

        alpha = float('-inf')
        beta = float('inf')

        depth = 1
        while True:
            try:
                print(f"Searching at depth {depth}.")
                self.no_of_nodes = 0

                val, best_move_this_depth = self.negamax(
                    game_state, depth, alpha, beta, initial_history)

                if (val <= alpha) or (val >= beta):  # AW Failed
                    alpha = float('-inf')
                    beta = float('inf')
                    continue  # continue search with larger window at the same depth

                if best_move_this_depth:
                    best_move_so_far = best_move_this_depth

                # aspiration window for the next iteration
                alpha = val - self.window
                beta = val + self.window

                elapsed_time = time.time() - self.start_time
                print(
                    f"  > Depth {depth} complete. Best move: {best_move_so_far}. Time: {elapsed_time:.2f}s. Total nodes: {self.no_of_nodes}")
                depth += 1
            except TimeoutError:
                print(
                    f"  > Timeout occurred at depth {depth}. Total nodes: {self.no_of_nodes}. Using best move from depth {depth-1}")
                break
        print(
            f"Final best move: {best_move_so_far}.")

        return best_move_so_far

    def negamax(self, game_state: BitboardGameState, depth, alpha, beta, tree_history):
        if self.no_of_nodes & 1023 == 0:
            if time.time() - self.start_time > self.time_limit:
                raise TimeoutError()

        flag = alpha_flag

        hashed_move = None
        if game_state.key in self.transposition_table:
            val, hashed_move = self.probe_hash(
                game_state.key, depth, alpha, beta)
            if val is not None:
                return val, hashed_move

        if game_state.is_game_over:
            val = self.evaluate(game_state)
            self.record_hash(game_state.key, depth, val,
                             exact_flag, best_move=None)
            return val, None

        if depth == 0:
            val = self.quiescence(game_state, alpha, beta)
            if val >= beta:
                self.record_hash(game_state.key, depth, val,
                                 beta_flag, best_move=None)
            elif val > alpha:
                self.record_hash(game_state.key, depth, val,
                                 exact_flag, best_move=None)
            else:
                self.record_hash(game_state.key, depth, val,
                                 alpha_flag, best_move=None)
            return val, None

        found_PV = False

        best_move = None

        moves = self.get_ordered_moves(game_state, hashed_move, depth)

        for move in moves:
            game_state.make_move(move)
            self.no_of_nodes += 1

            if game_state.key in tree_history or game_state.key in self.game_history:
                # needs tuning
                val = self.contempt
            else:
                tree_history.append(game_state.key)
                if found_PV:
                    val = -self.negamax(game_state, depth -
                                        1, -alpha-1, -alpha, tree_history)[0]
                    if alpha < val < beta:  # check for failure
                        val = -self.negamax(game_state,
                                            depth-1, -beta, -alpha, tree_history)[0]
                else:
                    val = -self.negamax(game_state, depth -
                                        1, -beta, -alpha, tree_history)[0]
                tree_history.pop()

            game_state.unmake_move()

            if val >= beta:

                # non capture: tiger, goat
                # placement moves: goat
                if (MOVE_MASKS[move[0]] & (1 << move[1]) or
                        move[0] == move[1]):
                    key = (depth, game_state.turn)
                    killers = self.killers.get(key, [None, None])
                    killers[1] = killers[0]
                    killers[0] = move
                    self.killers[key] = killers

                    key_hs = (game_state.turn, move[0], move[1])
                    self.history_heuristic[key_hs] = self.history_heuristic.get(
                        key_hs, 0) + 10

                self.record_hash(game_state.key, depth, beta,
                                 beta_flag, best_move=move)
                # beta cutoff
                return beta, move

            if val > alpha:
                alpha = val
                best_move = move
                found_PV = True
                flag = exact_flag

        self.record_hash(game_state.key, depth, alpha,
                         flag, best_move=best_move)
        return alpha, best_move

    def _score_move(self, game_state, move):
        if game_state.turn == Piece_TIGER:
            return tiger_priority(game_state.tigers_bb, game_state.goats_bb, move, MOVE_MASKS_NP, CAPTURE_COUNTS, CAPTURE_MASKS_NP)
        else:
            return goat_priority(game_state.tigers_bb, game_state.goats_bb, move, MOVE_MASKS_NP, CAPTURE_COUNTS, CAPTURE_MASKS_NP, OUTER_EDGE_MASK, STRATEGIC_MASK)

    def get_ordered_moves(self, game_state, hashed_move, depth=0):

        state_key = game_state.key
        if state_key in self.legal_moves_cache:
            moves = self.legal_moves_cache[state_key]
        else:
            moves = game_state.get_legal_moves()
            self.legal_moves_cache[state_key] = moves

        scored_moves = []
        for move in moves:
            score = 0
            # TT Move
            if hashed_move and hashed_move == move:
                score += 1_000_000

            # Killer Moves
            key = (depth, game_state.turn)
            killers = self.killers.get(key, [None, None])
            if move in killers:
                score += 500_000

            # history heuristic
            key_hs = (game_state.turn, move[0], move[1])
            score += self.history_heuristic.get(key_hs, 0)

            # static priority eval
            score += self._score_move(game_state, move)

            scored_moves.append((score, move))

        scored_moves.sort(reverse=True, key=lambda x: x[0])

        return [m for _, m in scored_moves]

    def quiescence(self, game_state: BitboardGameState, alpha, beta):
        val = self.evaluate(game_state)
        if val >= beta:
            return beta
        if val > alpha:
            alpha = val

        good_moves = self.get_good_moves(game_state)

        for move in good_moves:
            game_state.make_move(move)
            val = -self.quiescence(game_state, -beta, -alpha)
            game_state.unmake_move()
            if val >= beta:
                return beta
            if val > alpha:
                alpha = val

        return alpha

    def get_good_moves(self, game_state: BitboardGameState):
        moves = []
        occupied_bb = game_state.tigers_bb | game_state.goats_bb
        empty_bb = ~occupied_bb & BOARD_MASK

        if game_state.turn == Piece_TIGER:
            for src in extract_indices_fast(game_state.tigers_bb):
                for mid_mask, land_mask in CAPTURE_MASKS[src]:
                    if (game_state.goats_bb & mid_mask) and (empty_bb & land_mask):
                        dst = math.frexp(land_mask)[1] - 1
                        moves.append((src, dst))
        return moves

    def _count_potential_captures(self, state: BitboardGameState, empty_bb):
        if state.key in self.potential_captures_cache:
            return self.potential_captures_cache[state.key]

        capture_opportunities = 0
        # just in case, if i decide to "JIT" this with numba
        # for tiger in extract_indices_fast(state.tigers_bb):
        #     for j in range(CAPTURE_COUNTS[tiger]):
        #         mid_mask = CAPTURE_MASKS_NP[tiger, j, 0]
        #         land_mask = CAPTURE_MASKS_NP[tiger, j, 1]
        #         if (state.goats_bb & mid_mask) and (empty_bb & land_mask):
        #             capture_opportunities += 1

        for tiger in extract_indices_fast(state.tigers_bb):
            for mid_mask, land_mask in CAPTURE_MASKS[tiger]:
                if (state.goats_bb & mid_mask) and (empty_bb & land_mask):
                    capture_opportunities += 1

        self.potential_captures_cache[state.key] = capture_opportunities
        return capture_opportunities

    def _get_tiger_accessibility(self, state: BitboardGameState):
        if state.key in self.accessibility_cache:
            return self.accessibility_cache[state.key]

        accessible, inaccessible = tiger_board_accessibility(
            state.tigers_bb, state.goats_bb,
            MOVE_MASKS_NP, CAPTURE_COUNTS, CAPTURE_MASKS_NP)
        self.accessibility_cache[state.key] = (accessible, inaccessible)
        return accessible, inaccessible

    def evaluate(self, state: BitboardGameState):
        """
        Positive -> TIGER advantage, Negative -> GOAT advantage.
        """
        occupied_bb = state.tigers_bb | state.goats_bb
        empty_bb = ~occupied_bb & BOARD_MASK

        if state.key in self.previous_evaluations:
            return self.previous_evaluations[state.key]

        is_placement = state.goats_to_place > 0

        eat_max = 4  # before win
        potential_capture_max = 11
        inaccessible_max = 10

        trap_max = 3  # before win
        goat_presence_max = 20
        tiger_mobility_max = 25

        p_mobility = 0 if is_placement else w_mobility

        if state.is_game_over:
            result = state.get_result
            return 1000 * result * state.turn

        trapped = state.trapped_tiger_count
        eaten = state.goats_eaten
        goat_left = state.goats_to_place
        goats_on_board = 20 - (eaten + goat_left)

        eaten_score = eaten / eat_max

        potential_captures = self._count_potential_captures(state, empty_bb)
        potential_capture_score = potential_captures / potential_capture_max

        trap_score = trapped / trap_max
        goat_presence_score = goats_on_board / goat_presence_max
        accessible, inaccessible = self._get_tiger_accessibility(state)

        inaccessibility_score = inaccessible / inaccessible_max
        tiger_mobility_score = accessible / tiger_mobility_max

        tiger_score = (eaten_score * w_eat +
                       potential_capture_score * w_potcap +
                       tiger_mobility_score * p_mobility)

        goat_score = (trap_score * w_trap +
                      goat_presence_score * w_presence +
                      inaccessibility_score * w_inacc)

        final_evaluation = tiger_score - goat_score  # [-4, 4]
        self.previous_evaluations[state.key] = final_evaluation
        return final_evaluation * state.turn

    def probe_hash(self, state_key, depth, alpha, beta):
        hashed_depth, hashed_eval, flag, hashed_move = self.transposition_table[state_key]

        if hashed_depth >= depth:
            if flag == exact_flag:
                return hashed_eval, hashed_move

            # This is an UPPER bound (true_value <= hashed_eval)
            if flag == alpha_flag:
                if hashed_eval <= alpha:
                    # The best this node can be is still worse than what the maximizer (alpha) already has.
                    # This will cause a cutoff. Return the bound.
                    return hashed_eval, hashed_move

            # This is a LOWER bound (true_value >= hashed_eval)
            if flag == beta_flag:
                if hashed_eval >= beta:
                    # This node is guaranteed to be better than what the minimizer (beta) will allow.
                    # This will cause a cutoff. Return the bound.
                    return hashed_eval, hashed_move

        # The stored value is not useful (either too shallow or doesn't cause a cutoff).
        return None, hashed_move

    def record_hash(self, state_key, depth, evaluation, flag, best_move):
        # always-repalce scheme
        self.transposition_table[state_key] = (
            depth, evaluation, flag, best_move)
