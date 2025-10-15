from bagchal import *

EXACT_FLAG, ALPHA_FLAG, BETA_FLAG = 0, 1, 2


class TimeoutError(Exception):
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

    def tt_put(self, entry: TTEntry):
        # always replace scheme
        # self.entries[entry.state_key] = entry

        # depth preferred scheme
        hashed_entry = self.entries.get(entry.state_key, None)
        if hashed_entry:
            if entry.depth >= hashed_entry.depth:
                self.entries[entry.state_key] = entry
            return

        self.entries[entry.state_key] = entry

    def tt_get(self, state_key, depth, alpha, beta):
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


class AlphaBetaAgent():
    def __init__(self):
        # half move counter
        self.ply = 0
        self.best_move = None
        self.game_state: BitboardGameState
        self.no_of_nodes = 0

    def get_best_move(self, gs, game_history=None, time_limit=1.5):
        self.game_state = gs.copy()
        self.game_history = game_history

        alpha = float('-inf')
        beta = float('inf')
        depth = 5

        self.no_of_nodes = 0

        score = self.negamax(alpha, beta, depth)

        print(
            f" > Best Move: {self.best_move}. No of Nodes: {self.no_of_nodes}. Score: {score}. Depth: {depth}")
        return self.best_move

    def negamax(self, alpha, beta, depth):

        self.no_of_nodes += 1

        if self.game_state.is_game_over:
            return self.evaluate()
        if depth == 0:
            return self.evaluate()
            # TODO: I'm not sure how useful qsearch is
            # return self.qsearch(alpha, beta)

        old_alpha = alpha

        moves = self.game_state.get_legal_moves()

        # fallback in case the search doesnot find a best move
        best_move_so_far = moves[0]

        for move in moves:
            self.ply += 1
            self.game_state.make_move(move)

            score = -self.negamax(-beta, -alpha, depth - 1)

            self.game_state.unmake_move()
            self.ply -= 1

            # fail-hard beta cutoff
            if score >= beta:
                # node (move) fails high
                if self.ply == 0:
                    # TODO: this is block is not executed at all why?
                    # it means that there are no cutoffs happening at the root node
                    print("inshallah")
                    self.best_move = move
                return beta

            # found a better move
            if score > alpha:
                # PV node (move)
                if self.ply == 0:  # root
                    # associate best move with the best score
                    best_move_so_far = move
                alpha = score

        # found better move
        if old_alpha != alpha:
            self.best_move = best_move_so_far

        # node (move) fails low i.e. score <= alpha
        return alpha

    def qsearch(self, alpha, beta):
        self.no_of_nodes += 1

        val = self.evaluate()
        if self.game_state.turn == Piece_GOAT:
            return val

        if val >= beta:
            # node (move) fails high
            return beta

        # found a better move
        if val > alpha:
            # PV node (move)
            alpha = val

        moves = self.game_state.get_legal_moves(only_captures=True)

        for move in moves:
            self.ply += 1
            self.game_state.make_move(move)

            score = -self.qsearch(-beta, -alpha)

            self.game_state.unmake_move()
            self.ply -= 1

            # fail-hard beta cutoff
            if score >= beta:
                # node (move) fails high
                return beta

            # found a better move
            if score > alpha:
                # PV node (move)
                alpha = score

        # node (move) fails low i.e. score <= alpha
        return alpha

    def evaluate(self):
        """
        Positive -> TIGER advantage, Negative -> GOAT advantage.
        """

        state = self.game_state

        occupied_bb = state.tigers_bb | state.goats_bb
        empty_bb = ~occupied_bb & BOARD_MASK

        is_placement = state.goats_to_place > 0

        eat_max = 4  # before win
        potential_capture_max = 5
        # potential_capture_max = 11
        inaccessible_max = 4
        # inaccessible_max = 10

        trap_max = 3  # before win
        goat_presence_max = 20
        tiger_mobility_max = 25

        p_mobility = 0 if is_placement else w_mobility

        if state.is_game_over:
            result = state.get_result
            score = 2000 - self.ply
            return score * result * state.turn

        trapped = state.trapped_tiger_count
        eaten = state.goats_eaten
        goat_left = state.goats_to_place
        goats_on_board = 20 - (eaten + goat_left)

        eaten_score = eaten / eat_max

        potential_captures = self._count_potential_captures(state, empty_bb)
        potential_capture_score = potential_captures / potential_capture_max
        potential_capture_score = min(1, potential_capture_score)

        trap_score = trapped / trap_max
        goat_presence_score = goats_on_board / goat_presence_max
        accessible, inaccessible = self._get_tiger_accessibility(state)

        inaccessibility_score = inaccessible / inaccessible_max
        tiger_mobility_score = accessible / tiger_mobility_max
        inaccessibility_score = min(1, inaccessibility_score)

        tiger_score = (eaten_score * w_eat +
                       potential_capture_score * w_potcap +
                       tiger_mobility_score * p_mobility)

        goat_score = (trap_score * w_trap +
                      goat_presence_score * w_presence +
                      inaccessibility_score * w_inacc)

        if inaccessible >= 1 and eaten == 0 and is_placement:
            # this is a sure win for goat if the goat can keep placing pieces without losing any
            # we must encourage this line of play for goat
            goat_score += 300

        final_evaluation = tiger_score - goat_score
        return final_evaluation * state.turn

    def _count_potential_captures(self, state: BitboardGameState, empty_bb):

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

        return capture_opportunities

    def _get_tiger_accessibility(self, state: BitboardGameState):
        accessible, inaccessible = tiger_board_accessibility(
            state.tigers_bb, state.goats_bb,
            MOVE_MASKS_NP, CAPTURE_COUNTS, CAPTURE_MASKS_NP)
        return accessible, inaccessible
