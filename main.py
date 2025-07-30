from bagchal import GameState, Piece
from game import Game
if __name__ == "__main__":
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
