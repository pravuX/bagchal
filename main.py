from bagchal import GameState, Piece
from game import Game
from alphabeta import MinimaxAgent


def run_game():
    board = [Piece.EMPTY] * 25
    pos_tiger = [0, 4, 20, 24]
    board[pos_tiger[0]] = Piece.TIGER
    board[pos_tiger[1]] = Piece.TIGER
    board[pos_tiger[2]] = Piece.TIGER
    board[pos_tiger[3]] = Piece.TIGER

    gameState = GameState(board, turn=Piece.GOAT,
                          goat_count=20, eaten_goat_count=0)
    game = Game(game_state=gameState)
    game.run()


def debug_mcts():
    # check get_legal_moves
    board = [Piece.TIGER, Piece.GOAT, Piece.GOAT, Piece.TIGER, Piece.EMPTY, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.TIGER, Piece.TIGER, Piece.GOAT, Piece.GOAT,
             Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT]
    goat_count = 0
    eaten_goat_count = 0
    turn = Piece.GOAT
    gameState = GameState(board, turn=turn,
                          goat_count=goat_count, eaten_goat_count=eaten_goat_count)
    gameState.update_tiger_pos()
    gameState.update_trapped_tiger()
    print(gameState.get_legal_moves())


def debug_minimax():
    board = [Piece.TIGER, Piece.GOAT, Piece.GOAT, Piece.EMPTY, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.TIGER, Piece.GOAT, Piece.TIGER,
             Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.EMPTY, Piece.TIGER, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.EMPTY, Piece.GOAT]
    goat_count = 0
    eaten_goat_count = 2
    turn = Piece.TIGER
    gameState = GameState(board, turn=turn,
                          goat_count=goat_count, eaten_goat_count=eaten_goat_count)
    # gameState.update_tiger_pos()
    # gameState.update_trapped_tiger()
    print(gameState.get_legal_moves())

    minimax_agent = MinimaxAgent(depth=3)
    print(minimax_agent.get_best_move(gameState))


if __name__ == "__main__":
    run_game()
    # debug_mcts()
    # debug_minimax()
