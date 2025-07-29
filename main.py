from bagchal import GameState
from game import Game
if __name__ == "__main__":
    board = [0] * 25
    gameState = GameState(board, turn=-1 ,goat_count=20, eaten_goat_count=0)
    game = Game(game_state=gameState)
    game.run()
