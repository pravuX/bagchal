import numpy as np
import time
from bagchal import *
# type of evaluation that is stored in the transposition_table
exact_flag, alpha_flag, beta_flag = 0, 1, 2


class TimeoutError(Exception):
    pass


class MinimaxAgent:

    # Tiger is the maximizing player
    # Goat is the minimizing player

    def __init__(self):
        self.no_of_nodes = 0

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

    # Move Prioritization
    def _score_move(self, game_state, move):
        if game_state.turn == Piece_TIGER:
            return self._tiger_priority(game_state, move)
        else:
            return self._goat_priority(game_state, move)

    def get_ordered_moves(self, game_state):

        state_key = game_state.key
        if state_key in self.legal_moves_cache:
            moves = self.legal_moves_cache[state_key]
        else:
            moves = game_state.get_legal_moves_np()
            self.legal_moves_cache[state_key] = moves

        # TODO
        # Do we cache this or use it as a fallback??
        # this is causing a lot of overhead!
        scored_moves = [(move, self._score_move(game_state, move))
                        for move in moves]
        scored_moves.sort(key=lambda x: x[1], reverse=True)  # Best moves first
        moves = [move for move, _ in scored_moves]

        if state_key in self.transposition_table:
            _, _, _, hash_move = self.transposition_table[state_key]
            if hash_move and hash_move in moves:
                moves.remove(hash_move)
                moves.insert(0, hash_move)

        return moves

    def get_best_move(self, gs, time_limit=1.5):
        self.no_of_nodes = 0
        self.transposition_table.clear()

        if len(self.accessibility_cache) > 10_000:
            self.accessibility_cache.clear()
        if len(self.potential_captures_cache) > 10_000:
            self.potential_captures_cache.clear()
        if len(self.legal_moves_cache) > 10_000:
            self.legal_moves_cache.clear()
        if len(self.previous_evaluations) > 10_000:
            self.previous_evaluations.clear()

        start_time = time.time()
        best_move_so_far = None

        game_state = gs.copy()

        for depth in range(1, 100):
            try:
                print(f"Searching at depth {depth}")

                best_move_for_this_depth = self._search_root_at_depth(
                    game_state, depth, start_time, time_limit)

                if best_move_for_this_depth:
                    best_move_so_far = best_move_for_this_depth
                elapsed_time = time.time() - start_time
                print(
                    f"  > Depth {depth} complete. Best move: {best_move_so_far}. Time: {elapsed_time:.2f}s")
            except TimeoutError:
                print(
                    f"  > Timeout occurred at depth {depth}. Using best move from depth {depth-1}.")
                break  # Exit the loop if time runs out

        print(
            f"Final best move: {best_move_so_far}. Total nodes: {self.no_of_nodes}")
        return best_move_so_far

    def _search_root_at_depth(self, game_state, depth, start_time, time_limit):
        is_maximizing = game_state.turn == Piece_TIGER

        alpha = float('-inf')
        beta = float('inf')

        current_player_best_val = float(
            '-inf') if is_maximizing else float('inf')
        best_move = None

        original_alpha = alpha

        moves = self.get_ordered_moves(game_state)

        root_key = game_state.key
        root_player = game_state.turn

        for move in moves:
            if time.time() - start_time > time_limit:
                raise TimeoutError()
            history = {root_key}

            game_state.make_move(move)
            self.no_of_nodes += 1

            if game_state.is_game_over and game_state.get_result == root_player:
                best_move = move
                game_state.unmake_move()
                break

            val = self.minimax(game_state, depth - 1,
                               alpha, beta, start_time, time_limit, history)

            game_state.unmake_move()

            if is_maximizing:
                if val > current_player_best_val:
                    current_player_best_val = val
                    best_move = move
                alpha = max(alpha, current_player_best_val)
            else:
                if val < current_player_best_val:
                    current_player_best_val = val
                    best_move = move
                beta = min(beta, current_player_best_val)

            # Pruning at the root level(can happen if beta <= alpha)
            if beta <= alpha:
                break

        if best_move is not None:
            flag = exact_flag
            if current_player_best_val <= original_alpha:
                flag = alpha_flag
            elif current_player_best_val >= beta:
                flag = beta_flag

            self.record_hash(
                root_key, depth, current_player_best_val, flag, best_move)

        return best_move

    def minimax(self, game_state: GameState, depth, alpha, beta, start_time, time_limit, history):
        if self.no_of_nodes & 1023 == 0:
            if time.time() - start_time > time_limit:
                raise TimeoutError

        original_alpha = alpha

        best_move = None

        state_key = game_state.key
        if state_key in history:
            return 0.0

        if state_key in self.transposition_table:
            val = self.get_hashed_value(state_key, depth, alpha, beta)
            if val != None:
                return val

        if depth == 0 or game_state.is_game_over:
            val = self.evaluate_state(game_state, state_key)
            self.record_hash(state_key, depth, val, exact_flag, None)
            return val

        moves = self.get_ordered_moves(game_state)

        is_maximizing = game_state.turn == Piece_TIGER

        if is_maximizing:
            max_eval = float('-inf')
            for move in moves:
                new_history = history | {state_key}

                game_state.make_move(move)
                self.no_of_nodes += 1

                evaluation = self.minimax(
                    game_state, depth - 1, alpha, beta, start_time, time_limit, new_history)

                game_state.unmake_move()

                if evaluation > max_eval:
                    max_eval = evaluation
                    best_move = move

                alpha = max(alpha, evaluation)
                if beta <= alpha:
                    break

            if max_eval >= beta:
                # caused beta-cutoff
                self.record_hash(
                    state_key, depth, max_eval, beta_flag, best_move)
            else:
                self.record_hash(
                    state_key, depth, max_eval, exact_flag, best_move)

            return max_eval
        else:
            min_eval = float('inf')
            for move in moves:
                new_history = history | {state_key}

                game_state.make_move(move)
                self.no_of_nodes += 1

                evaluation = self.minimax(
                    game_state, depth - 1, alpha, beta, start_time, time_limit, new_history)

                game_state.unmake_move()

                if evaluation < min_eval:
                    min_eval = evaluation
                    best_move = move

                beta = min(beta, evaluation)
                if beta <= alpha:
                    break

            if min_eval <= original_alpha:
                # caused alpha-cutoff
                self.record_hash(
                    state_key, depth, min_eval, alpha_flag, best_move)
            else:
                self.record_hash(
                    state_key, depth, min_eval, exact_flag, best_move)
            return min_eval

    def _get_potential_captures(self, state: GameState, state_key):
        if state_key in self.potential_captures_cache:
            return self.potential_captures_cache[state_key]

        capture_opportunities = 0
        tiger_indices = state.all_positions[state.tiger_positions]
        for src in tiger_indices:
            possible_landings = state.capture_map_np[src]
            valid_landings = possible_landings[state.empty_positions[possible_landings]]

            for dst in valid_landings:
                mid = state.capture_mid_map_np[(src, dst)]
                if state.goat_positions[mid]:
                    capture_opportunities += 1

        self.potential_captures_cache[state_key] = capture_opportunities
        return capture_opportunities

    def _get_tiger_accessibility(self, state: GameState, state_key):
        if state_key in self.accessibility_cache:
            return self.accessibility_cache[state_key]

        accessible, inaccessible = GameState.tiger_board_accessibility(state)
        self.accessibility_cache[state_key] = (accessible, inaccessible)
        return accessible, inaccessible

    def evaluate_state(self, state: GameState, state_key):
        """
        Positive -> TIGER advantage, Negative -> GOAT advantage.
        """

        assert state_key

        if state_key in self.previous_evaluations:
            return self.previous_evaluations[state_key]

        is_placement = state.goat_count > 0

        eat_max = 4  # before win
        potential_capture_max = 11
        inaccessible_max = 10

        trap_max = 3  # before win
        goat_presence_max = 20
        tiger_mobility_max = 25

        w_eat = HeuristicParams.w_eat
        w_potcap = HeuristicParams.w_potcap
        w_mobility = 0 if is_placement else HeuristicParams.w_mobility

        w_trap = HeuristicParams.w_trap
        w_presence = HeuristicParams.w_presence
        w_inacc = HeuristicParams.w_inacc

        if state.is_game_over:
            result = state.get_result
            return 1000 if result == Piece_TIGER else -1000

        trapped = state.trapped_tiger_count
        eaten = state.eaten_goat_count
        goat_left = state.goat_count
        goats_on_board = 20 - (eaten + goat_left)

        eaten_score = eaten / eat_max

        potential_captures = self._get_potential_captures(state, state_key)
        potential_capture_score = potential_captures / potential_capture_max

        trap_score = trapped / trap_max
        goat_presence_score = goats_on_board / goat_presence_max
        no_of_accessible_positions, no_of_inaccessible_positions = self._get_tiger_accessibility(
            state, state_key)

        inaccessibility_score = no_of_inaccessible_positions / inaccessible_max
        tiger_mobility_score = no_of_accessible_positions / tiger_mobility_max

        tiger_score = (eaten_score * w_eat +
                       potential_capture_score * w_potcap +
                       tiger_mobility_score * w_mobility)

        goat_score = (trap_score * w_trap +
                      goat_presence_score * w_presence +
                      inaccessibility_score * w_inacc)

        final_evaluation = tiger_score - goat_score  # [-3.0, 3.5]
        self.previous_evaluations[state_key] = final_evaluation
        return final_evaluation

    @staticmethod
    def _tiger_priority(game_state, move):
        params = HeuristicParams
        priority_score = 0
        src, dst = move

        # Capture
        if dst not in game_state.graph_np[src]:
            priority_score += params.tiger_capture_bonus

        # Potential Capture
        possible_landings = game_state.capture_map_np[dst]
        valid_landings = possible_landings[game_state.empty_positions[possible_landings]]
        for landing in valid_landings:
            mid = game_state.capture_mid_map_np[(dst, landing)]
            if game_state.goat_positions[mid]:
                priority_score += params.tiger_potential_capture_bonus

        # Blocking Capture
        tiger_indices = game_state.all_positions[game_state.tiger_positions]
        for tiger in tiger_indices:
            if tiger == src:
                continue
            possible_landings = game_state.capture_map_np[tiger]
            valid_landings = possible_landings[game_state.empty_positions[possible_landings]]
            for landing in valid_landings:
                mid = game_state.capture_mid_map_np[(tiger, landing)]
                if game_state.goat_positions[mid]:
                    # Capture is possible for `tiger`
                    # and this move blocks capture
                    # we discourage it
                    if landing == dst:
                        priority_score -= params.tiger_block_penalty
                        break

        return priority_score + np.random.random()

    @staticmethod
    def _goat_priority(game_state, move):
        params = HeuristicParams
        src, dst = move
        is_placement_phase = src == dst
        priority_score = 0

        neighbors = game_state.graph_np[dst]

        # Avoid captures
        neighboring_tigers = game_state.tiger_positions[neighbors]
        for tiger in neighbors[neighboring_tigers]:
            possible_landings = game_state.capture_map_np[tiger]
            valid_landings = possible_landings[game_state.empty_positions[possible_landings]]
            for landing in valid_landings:
                mid = game_state.capture_mid_map_np[(tiger, landing)]
                if mid == dst:
                    priority_score -= params.goat_sacrifice_penalty
                    break

        # Clustering
        neighboring_goats = game_state.goat_positions[neighbors]
        # don't count yourself
        no_of_neighboring_goats = np.sum(neighboring_goats) - 1
        priority_score += no_of_neighboring_goats * params.goat_clustering_bonus

        # useful when there's nothing much going on the board
        strategic_positions = {2, 10, 14, 22}
        outer_eddge = {0, 1, 2, 3, 4, 5, 10, 15, 20, 21, 22, 23, 24, 9, 14, 19}
        if is_placement_phase and dst in strategic_positions:
            priority_score += params.goat_strategic_position_bonus
        elif dst in outer_eddge:
            priority_score += params.goat_outer_edge_bonus

        return priority_score + np.random.random()

    def get_hashed_value(self, state_key, depth, alpha, beta):
        hashed_depth, hashed_eval, flag, _ = self.transposition_table[state_key]

        if hashed_depth >= depth:
            if flag == exact_flag:
                return hashed_eval

            # This is an UPPER bound (true_value <= hashed_eval)
            if flag == alpha_flag:
                if hashed_eval <= alpha:
                    # The best this node can be is still worse than what the maximizer (alpha) already has.
                    # This will cause a cutoff. Return the bound.
                    return hashed_eval

            # This is a LOWER bound (true_value >= hashed_eval)
            if flag == beta_flag:
                if hashed_eval >= beta:
                    # This node is guaranteed to be better than what the minimizer (beta) will allow.
                    # This will cause a cutoff. Return the bound.
                    return hashed_eval

        # The stored value is not useful (either too shallow or doesn't cause a cutoff).
        return None

    def record_hash(self, state_key, depth, evaluation, flag, best_move):
        self.transposition_table[state_key] = (
            depth, evaluation, flag, best_move)
