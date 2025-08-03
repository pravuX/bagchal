from random import random, choice
from bagchal import Piece, GameState


class MinimaxAgent:
    # Tiger is always the maximizing player
    # Goat is always the minimizing player
    def __init__(self, depth=3):
        self.depth = depth

    def get_best_move(self, game_state):
        best_val = float(
            '-inf') if game_state.turn == Piece.TIGER else float('inf')
        best_move = None

        moves = game_state.get_legal_moves()
        # if random() < 0.5 and game_state.turn == Piece.TIGER:
        #     return choice(moves)
        for move in moves:
            simulated = self.simulate_move(game_state, move)
            val = self.minimax(simulated, self.depth - 1, float('-inf'),
                               float('inf'), maximizing=(game_state.turn == Piece.GOAT))
            if game_state.turn == Piece.TIGER and val >= best_val:
                best_val = val
                best_move = move
            elif game_state.turn == Piece.GOAT and val <= best_val:
                best_val = val
                best_move = move

        return best_move

    def minimax(self, game_state, depth, alpha, beta, maximizing):
        if depth == 0:
            return game_state.evaluate_board()

        moves = game_state.get_legal_moves()

        if maximizing:
            max_eval = float('-inf')
            for move in moves:
                new_state = self.simulate_move(game_state, move)
                eval = self.minimax(new_state, depth - 1, alpha, beta, False)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            for move in moves:
                new_state = self.simulate_move(game_state, move)
                eval = self.minimax(new_state, depth - 1, alpha, beta, True)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break
            return min_eval

    def simulate_move(self, game_state, move):
        return game_state.make_move(move)
