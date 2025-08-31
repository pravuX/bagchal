from bagchal import Piece, GameState


class MinimaxAgent:
    # Tiger is the maximizing player
    # Goat is the minimizing player
    def __init__(self, depth=3):
        self.depth = depth

    def get_best_move(self, game_state):
        is_maximizing = game_state.turn == Piece.TIGER
        best_val = float('-inf') if is_maximizing else float('inf')
        best_move = None

        moves = game_state.prioritized_moves
        for move in moves:
            simulated = self.simulate_move(game_state, move)
            val = self.minimax(simulated, self.depth - 1,
                               float('-inf'), float('inf'))

            if is_maximizing and val >= best_val:
                best_val = val
                best_move = move
            elif not is_maximizing and val <= best_val:
                best_val = val
                best_move = move

        return best_move

    def minimax(self, game_state, depth, alpha, beta):
        if depth == 0 or game_state.is_game_over():
            return self.evaluate_state(game_state, depth)

        moves = game_state.prioritized_moves
        is_maximizing = game_state.turn == Piece.TIGER

        if is_maximizing:
            max_eval = float('-inf')
            for move in moves:
                new_state = self.simulate_move(game_state, move)
                eval = self.minimax(new_state, depth - 1, alpha, beta)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            for move in moves:
                new_state = self.simulate_move(game_state, move)
                eval = self.minimax(new_state, depth - 1, alpha, beta)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break
            return min_eval

    def simulate_move(self, game_state, move):
        return game_state.make_move(move)

    def evaluate_state(self, state: GameState, depth):
        """
        Positive -> TIGER advantage, Negative -> GOAT advantage.
        """

        if state.is_game_over():
            result = state.get_result()
            if result == Piece.TIGER:
                return 100 - depth
            elif result == Piece.GOAT:
                return -100 + depth

        trapped = state.trapped_tiger_count
        eaten = state.eaten_goat_count
        goat_left = state.goat_count
        goats_on_board = 20 - (eaten + goat_left)

        # [0,1], higher = goat advantage
        trap_score = trapped / 4.0
        # [0,1], higher = tiger advantage
        eat_score = min(eaten / 5.0, 1.0)
        # tiger positive, goat negative
        raw = eat_score - trap_score

        goat_presence = goats_on_board / 20.0  # [0,1]
        goat_presence_bonus = goat_presence * 0.05
        # subtract → goat advantage negative
        raw -= goat_presence_bonus

        inaccessible = GameState.find_inaccessible_positions(state)
        inaccessibility_score = len(inaccessible) / 25.0   # normalize [0,1]
        # weight 0.5 (tunable)
        raw -= inaccessibility_score * 0.5

        # Clamp into [-1, 1]
        return max(-1.0, min(1.0, raw))
        # return raw * 10
