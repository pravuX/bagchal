import time
from bagchal import Piece, GameState, HeuristicParams
# type of evaluation that is stored in the transposition_table
exact_flag, alpha_flag, beta_flag = 0, 1, 2


class TimeoutError(Exception):
    pass


class MinimaxAgent:

    heuristic_params = HeuristicParams()
    # state_key -> (depth, evaluation, flag, best_move)

    # Tiger is the maximizing player
    # Goat is the minimizing player

    def __init__(self, depth=3):
        self.max_depth = depth
        self.no_of_nodes = 0
        self.previous_evaluations = {}  # state_key -> evaluation
        self.transposition_table = {}

    def get_best_move(self, game_state, time_limit=1.5):
        self.no_of_nodes = 0

        start_time = time.time()
        best_move_so_far = None

        if game_state.prioritized_moves:
            best_move_so_far = game_state.prioritized_moves[::-1][0]

        for depth in range(1, 100):
            try:
                # print(f"Searching at depth {depth}")

                best_move_for_this_depth = self._search_root_at_depth(
                    game_state, depth, start_time, time_limit)

                best_move_so_far = best_move_for_this_depth
                elapsed_time = time.time() - start_time
                # print(
                #     f"  > Depth {depth} complete. Best move: {best_move_so_far}. Time: {elapsed_time:.2f}s")
            except TimeoutError:
                # print(
                #     f"  > Timeout occurred at depth {depth}. Using best move from depth {depth-1}.")
                break  # Exit the loop if time runs out

        # print(
        #     f"Final best move: {best_move_so_far}. Total nodes: {self.no_of_nodes}")
        return best_move_so_far

    def _search_root_at_depth(self, game_state, depth, start_time, time_limit):
        is_maximizing = game_state.turn == Piece.TIGER

        alpha = float('-inf')
        beta = float('inf')

        current_player_best_val = float(
            '-inf') if is_maximizing else float('inf')
        best_move = None

        moves = game_state.prioritized_moves[::-1]

        state_key = game_state.key()
        if state_key in self.transposition_table:
            _, _, _, hash_move = self.transposition_table[state_key]
            if hash_move and hash_move in moves:
                moves.remove(hash_move)
                moves.insert(0, hash_move)

        for move in moves:
            if time.time() - start_time > time_limit:
                raise TimeoutError()

            simulated = self.simulate_move(game_state, move)
            self.no_of_nodes += 1

            if simulated.is_game_over() and simulated.get_result() == game_state.turn:
                best_move = move
                break

            history = {self.key_without_turn(game_state)}

            val = self.minimax(simulated, depth - 1,
                               alpha, beta, start_time, time_limit, history)

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

            # Pruning at the root level (can happen if beta <= alpha)
            if beta <= alpha:
                break

        return best_move

    def minimax(self, game_state: GameState, depth, alpha, beta, start_time, time_limit, history):
        if self.no_of_nodes & 1023 == 0:
            if time.time() - start_time > time_limit:
                raise TimeoutError

        original_alpha = alpha

        best_move = None

        without_turn_state_key = self.key_without_turn(game_state)
        if without_turn_state_key in history:
            # discourage repeating moves
            # print("HIttttt")
            return 0

        state_key = game_state.key()
        if state_key in self.transposition_table:
            val = self.get_hashed_value(state_key, depth, alpha, beta)
            if val != None:
                return val

        if depth == 0 or game_state.is_game_over():
            val = self.evaluate_state(game_state)
            self.record_hash(state_key, depth, val, exact_flag, None)
            return val

        moves = game_state.prioritized_moves[::-1]

        if state_key in self.transposition_table:
            _, _, _, hash_move = self.transposition_table[state_key]
            if hash_move in moves:
                moves.remove(hash_move)
                moves.insert(0, hash_move)

        is_maximizing = game_state.turn == Piece.TIGER

        if is_maximizing:
            max_eval = float('-inf')
            for move in moves:
                new_state = self.simulate_move(game_state, move)
                self.no_of_nodes += 1

                new_history = history | {self.key_without_turn(game_state)}
                evaluation = self.minimax(
                    new_state, depth - 1, alpha, beta, start_time, time_limit, new_history)
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
                new_state = self.simulate_move(game_state, move)
                self.no_of_nodes += 1

                new_history = history | {self.key_without_turn(game_state)}
                evaluation = self.minimax(
                    new_state, depth - 1, alpha, beta, start_time, time_limit, new_history)
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

    def simulate_move(self, game_state, move):
        return game_state.make_move(move)

    def evaluate_state(self, state: GameState):
        """
        Positive -> TIGER advantage, Negative -> GOAT advantage.
        """

        state_key = state.key()

        if state_key in self.previous_evaluations:
            return self.previous_evaluations[state_key]

        is_placement = state.goat_count > 0

        eat_max = 4  # before win
        potential_capture_max = 11
        inaccessible_max = 10

        trap_max = 3  # before win
        goat_presence_max = 20
        tiger_mobility_max = 25

        w_eat = self.heuristic_params.w_eat
        w_potcap = self.heuristic_params.w_potcap
        w_mobility = 0 if is_placement else self.heuristic_params.w_mobility

        w_trap = self.heuristic_params.w_trap
        w_presence = self.heuristic_params.w_presence
        w_inacc = self.heuristic_params.w_inacc


        if state.is_game_over():
            result = state.get_result()
            return 1000 if result == Piece.TIGER else -1000

        trapped = state.trapped_tiger_count
        eaten = state.eaten_goat_count
        goat_left = state.goat_count
        goats_on_board = 20 - (eaten + goat_left)

        goat_positions = [i for i, p in enumerate(
            state.board) if p == Piece.GOAT]

        eaten_score = eaten / eat_max
        tiger_legal_moves = state.get_legal_moves(turn=Piece.TIGER)
        potential_captures = sum(
            1 for src, dst in tiger_legal_moves if dst not in GameState.graph[src])
        tiger_normal_moves = len(tiger_legal_moves) - potential_captures
        potential_capture_score = potential_captures / potential_capture_max
        tiger_mobility_score = tiger_normal_moves / tiger_mobility_max

        trap_score = trapped / trap_max
        goat_presence_score = goats_on_board / goat_presence_max
        inaccessible = GameState.find_inaccessible_positions(state)
        inaccessibility_score = len(inaccessible) / inaccessible_max

        tiger_score = (eaten_score * w_eat +
                       potential_capture_score * w_potcap +
                       tiger_mobility_score * w_mobility)

        goat_score = (trap_score * w_trap +
                      goat_presence_score * w_presence +
                      inaccessibility_score * w_inacc)

        final_evaluation = tiger_score - goat_score  # [-3.0, 3.5]
        self.previous_evaluations[state_key] = final_evaluation
        return final_evaluation

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

    @staticmethod
    def key_without_turn(game_state):
        string_rep, turn, eaten_goat_count, goat_count, trapped_tiger_count = game_state.key()
        return (string_rep, eaten_goat_count, goat_count, trapped_tiger_count)
