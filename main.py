from collections import defaultdict
from os import system
from bagchal import GameState, Piece
from game import Game
from alphabeta import MinimaxAgent
import pprint
# from mcts import MCTS
from pw_mcts import MCTS
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

    game_state = GameState(board, turn=Piece.GOAT,
                           goat_count=20, eaten_goat_count=0)
    game_state.update_trapped_tiger()
    game_state.init_prioritization()
    game = Game(game_state=game_state)
    game.run()


def debug_mcts():
    # check get_legal_moves
    board = [Piece.TIGER, Piece.GOAT, Piece.GOAT, Piece.TIGER, Piece.EMPTY, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.TIGER, Piece.TIGER, Piece.GOAT, Piece.GOAT,
             Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT]
    goat_count = 0
    eaten_goat_count = 0
    turn = Piece.GOAT
    game_state = GameState(board, turn=turn,
                           goat_count=goat_count, eaten_goat_count=eaten_goat_count)
    game_state.update_tiger_pos()
    print(game_state.get_legal_moves())


def debug_minimax():
    board = [Piece.TIGER, Piece.GOAT, Piece.GOAT, Piece.EMPTY, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.TIGER, Piece.GOAT, Piece.TIGER,
             Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.EMPTY, Piece.TIGER, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.GOAT, Piece.EMPTY, Piece.GOAT]
    goat_count = 0
    eaten_goat_count = 2
    turn = Piece.TIGER
    game_state = GameState(board, turn=turn,
                           goat_count=goat_count, eaten_goat_count=eaten_goat_count)
    game_state.update_trapped_tiger()
    print(game_state.get_legal_moves())

    minimax_agent = MinimaxAgent(depth=3)
    print(minimax_agent.get_best_move(game_state))
    print(game_state.stringify())


def scratch():
    board = [Piece.EMPTY] * 25
    pos_tiger = [0, 9, 12, 24]

    pos_goat = [10, 11, 15, 16, 17, 18, 20, 21, 22, 23]

    # pos_tiger = [1, 2, 13, 21]
    # empty = set([9, 15, 22])
    # pos_goat = list(set(range(25)) - empty - set(pos_tiger))
    for pos in pos_tiger:
        board[pos] = Piece.TIGER
    for pos in pos_goat:
        board[pos] = Piece.GOAT
    goat_count = 20 - len(pos_goat)
    eaten_goat_count = 0
    turn = Piece.GOAT
    game_state = GameState(board, turn=turn,
                           goat_count=goat_count, eaten_goat_count=eaten_goat_count)
    game_state.update_trapped_tiger()
    game_state.init_prioritization()
    display_board(game_state)
    print(game_state)
    print(game_state.prioritized_moves)
    minimax_agent = MinimaxAgent()
    move = minimax_agent.get_best_move(game_state, time_limit=1)
    print(move)

    print(minimax_agent.evaluate_state(game_state))
    print(minimax_agent.evaluate_state(game_state.make_move(move)))


def display_board(game_state):
    board = game_state.board
    piece = game_state.piece
    print("-"*26)
    for i, cell in enumerate(board):
        if i % 5 == 0:
            print("|", end=" ")
        print(piece[cell], end=" | ")
        if (i+1) % 5 == 0:
            print()
            print("-"*26)


def test_alphabeta():
    """Enhanced testing with performance metrics"""
    board = [Piece.EMPTY] * 25
    pos_tiger = [0, 4, 20, 24]
    for pos in pos_tiger:
        board[pos] = Piece.TIGER
    pos_goat = []
    for pos in pos_goat:
        board[pos] = Piece.GOAT

    game_state = GameState(board, turn=Piece.GOAT,
                           goat_count=20, eaten_goat_count=0)
    game_state.update_trapped_tiger()
    game_state.init_prioritization()

    state_hash = defaultdict(int)

    minimax_agent = MinimaxAgent()
    while not game_state.is_game_over():
        state_key = game_state.key()
        state_hash[state_key] += 1

        if state_hash[state_key] > 3:
            print("Draw by repetition!")
            break

        start_time = time.time()

        # if game_state.goat_count >= 10:  # Early Placement
        #     depth = 3
        # elif game_state.goat_count >= 5:  # Mid Placement
        #     depth = 4
        # elif game_state.goat_count >= 2:
        #     depth = 5
        # elif game_state.goat_count >= 0:
        #     depth = 6
        # minimax_agent = MinimaxAgent(depth=depth)
        move = minimax_agent.get_best_move(game_state, time_limit=1)

        move_time = time.time() - start_time

        # Display current state
        system('clear')
        display_board(game_state)
        print(game_state)
        print(f"Took {move_time:.2f}s. Move Selected{move}")

        game_state = game_state.make_move(move)
        input("Press Enter to continue...")  # Remove for automated testing

    # Final results
    system('clear')
    display_board(game_state)
    print(game_state)
    print(len(game_state.transposition_table_with_scores),
          "unique states encountered.")

    result = game_state.get_result()
    if result:
        print(f"Winner: {game_state.piece[result]}")
    else:
        print("Draw!")


def test_mcts():
    """Enhanced testing with performance metrics"""
    board = [Piece.EMPTY] * 25
    pos_tiger = [0, 4, 20, 24]
    for pos in pos_tiger:
        board[pos] = Piece.TIGER
    pos_goat = []
    for pos in pos_goat:
        board[pos] = Piece.GOAT

    game_state = GameState(board, turn=Piece.GOAT,
                           goat_count=20, eaten_goat_count=0)
    game_state.update_trapped_tiger()
    game_state.init_prioritization()

    # Performance tracking
    move_times = []
    simulations_per_move = []
    game_history = []
    state_hash = defaultdict(int)
    move_count = 0

    time_limit = 1.5
    # mcts = MCTS(initial_state=game_state, time_limit=time_limit)
    while not game_state.is_game_over():
        state_key = game_state.key()
        state_hash[state_key] += 1

        if state_hash[state_key] > 3:
            print("Draw by repetition!")
            break

        # Time the move decision
        start_time = time.time()

        # Use different time limits based on game phase
        # if game_state.goat_count >= 10:  # Early Placement
        #     time_limit = 1.5
        # elif game_state.goat_count >= 5:  # Mid Placement
        #     time_limit = 1.8
        # elif game_state.eaten_goat_count <= 2:
        #     time_limit = 1.5
        # else:  # Late Placement and Movement Movement
        #     time_limit = 1.8
        mcts = MCTS(initial_state=game_state,
                    time_limit=time_limit)
        move = mcts.search()

        move_time = time.time() - start_time
        move_times.append(move_time)

        simulations_per_move.append(mcts.simulations_run)

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

        # Display current state
        system('clear')
        display_board(game_state)
        print(f"Move {move_count + 1}")
        print(game_state)

        print(f"Move selected: {move}, Time: {move_time:.2f}s")
        # stats = mcts.get_move_statistics()
        print(f"Simulations run: {mcts.simulations_run}")
        # mcts.visualize_tree(max_depth=1)
        # pprint.PrettyPrinter(width=20).pprint(stats)
        print(f"Goat Wins: {mcts.goat_wins/mcts.simulations_run * 100:.2f}",
              f"Tiger Wins: {mcts.tiger_wins/mcts.simulations_run * 100:.2f}")

        game_state = game_state.make_move(move)
        # mcts.re_reoot(game_state, time_limit=time_limit)
        move_count += 1
        # input("Press Enter to continue...")  # Remove for automated testing

    # Final results
    system('clear')
    display_board(game_state)
    print(game_state)
    print(len(game_state.transposition_table_with_scores),
          "unique states encountered.")

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
    print(f"Max no of simulations: {max(simulations_per_move)}")
    print(f"Min no of simulations: {min(simulations_per_move)}")

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
    run_game()
    # scratch()
    # debug_minimax()
    # test_alphabeta()

    # with Profile() as profile:
    #     scratch()
    #     # test_mcts()
    #     (
    #         Stats(profile)
    #         .strip_dirs()
    #         .sort_stats(SortKey.TIME)
    #         .print_stats()
    #     )
