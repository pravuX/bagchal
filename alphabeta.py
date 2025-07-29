from random import randint, choice
from bagchal import Piece, GameState

class MinimaxAgent:
    # Tiger is always the maximizing player
    # Goat is always the minimizing player
    def __init__(self, depth=3):
        self.depth = depth

    def get_best_move(self, game):
        best_val = float('-inf') if game.turn == Piece.TIGER else float('inf')
        best_move = None

        moves = game.generate_legal_moves()
        if randint(1, 10) > 8 and game.turn == Piece.TIGER:
            return choice(moves)
        if randint(1, 10) > 9 and game.turn == Piece.GOAT:
            return choice(moves)
        for move in moves:
            simulated = self.simulate_move(game, move)
            val = self.minimax(simulated, self.depth - 1, float('-inf'),
                               float('inf'), maximizing=(game.turn == Piece.GOAT))

            if game.turn == Piece.TIGER and val > best_val:
                best_val = val
                best_move = move
            elif game.turn == Piece.GOAT and val < best_val:
                best_val = val
                best_move = move

        return best_move

    def minimax(self, game_board, depth, alpha, beta, maximizing):
        if depth == 0:
            return game_board.evaluate_board()

        moves = game_board.generate_legal_moves()

        if maximizing:
            max_eval = float('-inf')
            for move in moves:
                new_board = self.simulate_move(game_board, move)
                eval = self.minimax(new_board, depth - 1, alpha, beta, False)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            for move in moves:
                new_board = self.simulate_move(game_board, move)
                eval = self.minimax(new_board, depth - 1, alpha, beta, True)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break
            return min_eval

    def simulate_move(self, game, move):
        new_board = GameState(
            game.board, game.turn, game.goat_count, game.eaten_goat_count)
        new_board.make_move(*move)
        return new_board
