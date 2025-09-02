from bagchal import Piece, GameState


class MinimaxAgent:
    previous_evaluations = {}  # state_key -> evaluation
    # Tiger is the maximizing player
    # Goat is the minimizing player

    def __init__(self, depth=3):
        self.depth = depth
        self.no_of_nodes = 0

    def get_best_move(self, game_state):
        is_maximizing = game_state.turn == Piece.TIGER

        alpha = float('-inf')
        beta = float('inf')

        current_player_best_val = float(
            '-inf') if is_maximizing else float('inf')
        best_move = None

        moves = game_state.prioritized_moves[::-1]

        for move in moves:
            simulated = self.simulate_move(game_state, move)
            self.no_of_nodes += 1

            val = self.minimax(simulated, self.depth - 1,
                               alpha, beta)
            print(move, val)

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
            # if beta <= alpha:
            #     break

        return best_move

    def minimax(self, game_state: GameState, depth, alpha, beta):
        if depth == 0 or game_state.is_game_over():
            return self.evaluate_state(game_state, depth)

        moves = game_state.prioritized_moves[::-1]

        is_maximizing = game_state.turn == Piece.TIGER

        if is_maximizing:
            max_eval = float('-inf')
            for move in moves:
                new_state = self.simulate_move(game_state, move)
                self.no_of_nodes += 1
                evaluation = self.minimax(new_state, depth - 1, alpha, beta)
                max_eval = max(max_eval, evaluation)
                alpha = max(alpha, evaluation)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            for move in moves:
                new_state = self.simulate_move(game_state, move)
                self.no_of_nodes += 1
                evaluation = self.minimax(new_state, depth - 1, alpha, beta)
                min_eval = min(min_eval, evaluation)
                beta = min(beta, evaluation)
                if beta <= alpha:
                    break
            return min_eval

    def simulate_move(self, game_state, move):
        return game_state.make_move(move)

    def evaluate_state(self, state: GameState, depth=0):
        """
        Positive -> TIGER advantage, Negative -> GOAT advantage.
        """

        state_key = state.key()

        if state_key in MinimaxAgent.previous_evaluations:
            return MinimaxAgent.previous_evaluations[state_key]

        eat_max = 4
        trap_max = 3
        goat_presence_max = 20
        inaccessible_max = 10
        potential_capture_max = 11

        w_eat = 1.5
        w_trap = 1.5
        w_presence = 0.9
        w_inacc = 0.6
        w_potcap = 1.5

        if state.is_game_over():
            result = state.get_result()
            if result == Piece.TIGER:
                return 100 - (self.depth - depth)  # limit - current
            elif result == Piece.GOAT:
                return -100 + (self.depth - depth)

        trapped = state.trapped_tiger_count
        eaten = state.eaten_goat_count
        goat_left = state.goat_count
        goats_on_board = 20 - (eaten + goat_left)

        eat_score_norm = eaten / eat_max
        tiger_legal_moves = state.get_legal_moves(turn=Piece.TIGER)
        capture_moves_count_norm = sum(
            1 for src, dst in tiger_legal_moves if dst not in GameState.graph[src]) / potential_capture_max

        trap_score_norm = trapped / trap_max
        goat_presence_norm = goats_on_board / goat_presence_max
        inaccessible = GameState.find_inaccessible_positions(state)
        inaccessibility_score_norm = len(inaccessible) / inaccessible_max

        tiger_score = eat_score_norm * w_eat + capture_moves_count_norm * w_potcap
        goat_score = trap_score_norm * w_trap + goat_presence_norm * \
            w_presence + inaccessibility_score_norm * w_inacc

        final_evaluation = tiger_score - goat_score  # [-3.0, 3.0]
        MinimaxAgent.previous_evaluations[state_key] = final_evaluation
        return final_evaluation
