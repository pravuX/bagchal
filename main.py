from collections import defaultdict
from os import system
from bagchal import GameState, Piece
from game import Game
from alphabeta import MinimaxAgent
import pprint
from mcts import MCTS
import time
import numpy as np


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
    # print(gameState.get_legal_moves())

    # minimax_agent = MinimaxAgent(depth=3)
    # print(minimax_agent.get_best_move(gameState))
    print(gameState.stringify())


def scratch():
    board = [Piece.TIGER, Piece.GOAT, Piece.GOAT, Piece.EMPTY, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.TIGER, Piece.GOAT, Piece.TIGER,
             Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.EMPTY, Piece.TIGER, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.EMPTY, Piece.GOAT]
    goat_count = 0
    eaten_goat_count = 2
    turn = Piece.TIGER
    gameState = GameState(board, turn=turn,
                          goat_count=goat_count, eaten_goat_count=eaten_goat_count)
    state_hash = defaultdict(int)
    state_key = gameState.key()
    if state_key in state_hash:
        state_hash[state_key] += 1
    else:
        state_hash[state_key] = 0
    print(state_hash)
    if state_key in state_hash:
        state_hash[state_key] += 1
    else:
        state_hash[state_key] = 0
    print(state_hash)


def display_board(game_state):
    board = game_state.board
    piece = game_state.piece
    print("-"*21)
    for i, cell in enumerate(board):
        if i % 5 == 0:
            print("|", end=" ")
        print(piece[cell], end=" | ")
        if (i+1) % 5 == 0:
            print()
            print("-"*21)


def update_state_hash(state_key, state_hash):
    if state_key in state_hash:
        state_hash[state_key] += 1
    else:
        state_hash[state_key] = 1


def test_mcts():
    # Spectate the agent playing against itself
    board = [Piece.EMPTY] * 25
    pos_tiger = [0, 4, 20, 24]
    board[pos_tiger[0]] = Piece.TIGER
    board[pos_tiger[1]] = Piece.TIGER
    board[pos_tiger[2]] = Piece.TIGER
    board[pos_tiger[3]] = Piece.TIGER

    game_state = GameState(board, turn=Piece.GOAT,
                           goat_count=20, eaten_goat_count=0)
    mcts = None
    # We manage the state_hash externally, to determine "draw"
    # We assume that if the same state has repeated more than 3 times,
    # then the game_state is not advancing so we cut it off.
    state_hash = defaultdict(int)
    while not game_state.is_game_over():
        state_key = game_state.key()
        update_state_hash(state_key, state_hash)
        if state_hash[state_key] > 3:
            break
        system('clear')
        display_board(game_state)

        mcts = MCTS(initial_state=game_state, time_limit=1)
        move = mcts.search()

        game_state = game_state.make_move(move)
    system('clear')
    display_board(game_state.board)
    print(
        f"{game_state.piece[game_state.get_result()]}" if game_state.get_result() else "Draw!")
    print(game_state)


def test_mcts_enhanced():
    """Enhanced testing with performance metrics"""
    board = [Piece.EMPTY] * 25
    pos_tiger = [0, 4, 20, 24]
    for pos in pos_tiger:
        board[pos] = Piece.TIGER

    game_state = GameState(board, turn=Piece.GOAT,
                           goat_count=20, eaten_goat_count=0)

    # Performance tracking
    move_times = []
    game_history = []
    state_hash = defaultdict(int)
    move_count = 0

    print("Starting MCTS vs MCTS game...")
    print("=" * 50)

    while not game_state.is_game_over():
        state_key = game_state.key()
        state_hash[state_key] += 1

        if state_hash[state_key] > 3:
            print("Draw by repetition!")
            break

        # Display current state
        system('clear')
        display_board(game_state)
        print(
            f"Move {move_count + 1}: {game_state.piece[game_state.turn]}'s turn")
        print(game_state)

        # Time the move decision
        start_time = time.time()

        # Use different time limits based on game phase
        if game_state.goat_count > 15:  # Early game
            time_limit = 0.5
        elif game_state.goat_count > 5:  # Mid game
            time_limit = 1.0
        else:  # End game
            time_limit = 2.0

        mcts = MCTS(initial_state=game_state, time_limit=time_limit)
        move = mcts.search()

        move_time = time.time() - start_time
        move_times.append(move_time)

        # Store game history
        game_history.append({
            'move': move,
            'player': game_state.turn,
            'board_state': game_state.stringify(),
            'goats_remaining': game_state.goat_count,
            'goats_eaten': game_state.eaten_goat_count,
            'move_time': move_time,
            'simulations_per_second': getattr(mcts, 'simulations_run', 0) / move_time if move_time > 0 else 0
        })

        print(f"Move selected: {move}, Time: {move_time:.2f}s")
        # stats = mcts.get_move_statistics()
        print(f"Simulations run: {mcts.simulations_run}")
        # mcts.visualize_tree(max_depth=1)
        # pprint.PrettyPrinter(width=20).pprint(stats)
        input("Press Enter to continue...")  # Remove for automated testing

        game_state = game_state.make_move(move)
        move_count += 1

        # Safety break for very long games
        if move_count > 200:
            print("Game ended due to move limit")
            break

    # Final results
    system('clear')
    display_board(game_state)

    result = game_state.get_result()
    if result:
        print(f"Winner: {game_state.piece[result]}")
    else:
        print("Draw!")

    # Performance summary
    print(f"\nGame Summary:")
    print(f"Total moves: {move_count}")
    print(f"Average move time: {np.mean(move_times):.2f}s")
    print(f"Max move time: {max(move_times):.2f}s")
    print(f"Min move time: {min(move_times):.2f}s")

    return game_history


def analyze_game_performance(game_history):
    """Analyze the performance of MCTS across the game"""
    goat_moves = [h for h in game_history if h['player'] == Piece.GOAT]
    tiger_moves = [h for h in game_history if h['player'] == Piece.TIGER]

    print(f"\nPerformance Analysis:")
    print(
        f"Goat average move time: {np.mean([m['move_time'] for m in goat_moves]):.2f}s")
    print(
        f"Tiger average move time: {np.mean([m['move_time'] for m in tiger_moves]):.2f}s")

    # Analyze decision complexity by game phase
    placement_phase = [h for h in game_history if h['goats_remaining'] > 0]
    movement_phase = [h for h in game_history if h['goats_remaining'] == 0]

    if placement_phase:
        print(
            f"Placement phase avg time: {np.mean([m['move_time'] for m in placement_phase]):.2f}s")
    if movement_phase:
        print(
            f"Movement phase avg time: {np.mean([m['move_time'] for m in movement_phase]):.2f}s")


# Example usage
if __name__ == "__main__":
    # history = test_mcts_enhanced()
    # analyze_game_performance(history)
    run_game()
