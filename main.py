from collections import defaultdict
from os import system
from bagchal import GameState, Piece
from game import Game
from alphabeta import MinimaxAgent
import pprint
from mcts import MCTS
import time
import numpy as np

from cProfile import Profile
from pstats import SortKey, Stats


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
    board = [Piece.EMPTY] * 25
    pos_tiger = [0, 2, 4, 10]
    for pos in pos_tiger:
        board[pos] = Piece.TIGER
    pos_goat = [1, 3, 5, 6, 7, 8, 9, 11, 12, 13, 15, 19, 20, 21, 23, 24]
    for pos in pos_goat:
        board[pos] = Piece.GOAT
    goat_count = 0
    eaten_goat_count = 3
    turn = Piece.GOAT
    game_state = GameState(board, turn=turn,
                           goat_count=goat_count, eaten_goat_count=eaten_goat_count)
    game_state.update_tiger_pos()
    game_state.update_trapped_tiger()
    display_board(game_state)
    mcts = MCTS(initial_state=game_state, max_simulations=1000)
    move = mcts.search()
    # mcts.visualize_tree(max_depth=10)
    print(game_state)
    print(f"Move selected: {move}")
    print(f"Simulations run: {mcts.simulations_run}")
    print(f"Goat Wins: {mcts.goat_wins/mcts.simulations_run * 100:.2f}%",
          f"Tiger Wins: {mcts.tiger_wins/mcts.simulations_run * 100:.2f}%")


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

    time_limit = 30
    while not game_state.is_game_over():
        state_key = game_state.key()
        state_hash[state_key] += 1

        if state_hash[state_key] > 3:
            print("Draw by repetition!")
            break

        # Display current state
        system('clear')
        display_board(game_state)
        print(f"Move {move_count + 1}")
        print(game_state)

        # Time the move decision
        start_time = time.time()

        # Use different time limits based on game phase
        # if game_state.goat_count > 15:  # Early game
        #     time_limit = 0.5
        # elif game_state.goat_count > 5:  # Mid game
        #     time_limit = 1.0
        # else:  # End game
        #     time_limit = 2.0

        mcts = MCTS(initial_state=game_state, max_simulations=100)
        # mcts = MCTS(initial_state=game_state, time_limit=time_limit)
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
        # mcts.visualize_tree(max_depth=10)
        # pprint.PrettyPrinter(width=20).pprint(stats)
        print(f"Goat Wins: {mcts.goat_wins/mcts.simulations_run * 100:.2f}",
              f"Tiger Wins: {mcts.tiger_wins/mcts.simulations_run * 100:.2f}")
        # input("Press Enter to continue...")  # Remove for automated testing

        game_state = game_state.make_move(move)
        move_count += 1

        # Safety break for very long games
        if move_count > 200:
            print("Game ended due to move limit")
            break

    # Final results
    system('clear')
    display_board(game_state)
    print(len(game_state.transposition_table_with_scores))

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
    # history = test_mcts()
    # analyze_game_performance(history)
    # run_game()
    scratch()

    # with Profile() as profile:
    #     # scratch()
    #     test_mcts()
    #     (
    #         Stats(profile)
    #         .strip_dirs()
    #         .sort_stats(SortKey.CALLS)
    #         .print_stats()
    #     )
