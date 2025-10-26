from collections import defaultdict
from os import system
from bagchal import *
from negamax import AlphaBetaAgent
from game.game import Game
from mcts import MCTS
import time
import numpy as np


from cProfile import Profile
from pstats import SortKey, Stats


def run_game():
    game_state = BitboardGameState()
    game = Game(game_state=game_state)
    game.run()


def scratch():

    # early movement
    # pos_tiger = [0, 6, 13, 19]
    # empty = set([5])
    # pos_goat = list(set(range(25)) - empty - set(pos_tiger))
    # eaten_goat_count = 0
    # turn = Piece_GOAT

    # late placement
    # pos_tiger = [0, 9, 12, 24]
    # pos_goat = [11]
    # eaten_goat_count = 4
    # turn = Piece_TIGER

    gs = BitboardGameState()
    gs.tigers_bb = 0
    # Some interesting positions
    # pos_tiger = [0, 11, 20, 24]
    # pos_goat = [1, 2, 3, 4, 8, 9, 10, 15, 21, 22, 23]

    # pos_tiger = [4, 20, 24, 17]
    # pos_goat = [0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 14, 15, 21, 22]

    # pos_tiger = [0, 8, 20, 24]
    # pos_goat = [1, 2, 3, 5, 10, 14, 15, 19, 21, 22]

    pos_tiger = [5, 8, 20, 24]
    pos_goat = [0, 1, 2, 3, 4, 9, 17]
    gs.turn = Piece_TIGER

    for p in pos_tiger:
        gs.tigers_bb |= (1 << p)
    for p in pos_goat:
        gs.goats_bb |= (1 << p)
    gs.goats_to_place = 20 - len(pos_goat)
    display_board(gs)
    print(gs)

    # for minimax agent
    alphabeta_agent = AlphaBetaAgent()
    # moves = gs.get_legal_moves()
    # print("unsorted\t\t", moves)
    # for i in range(len(moves)):
    #     alphabeta_agent.pick_move(moves, i, None)
    # print("sorted\t\t", moves)
    move = alphabeta_agent.get_best_move(gs, time_limit=1, game_history=[])

    # for mcts agent
    # mcts = MCTS()
    # move = mcts.search(initial_state=gs,
    #                    time_limit=1.5)
    # display_board(game_state)
    # mcts.visualize_tree(max_depth=1)
    # print(move)
    # print(f"Total Simulations: {mcts.simulations_run}")
    # print(f"Goat Wins: {mcts.goat_wins}",
    #       f"Tiger Wins: {mcts.tiger_wins}",
    #       f"Draws: {mcts.draws}")


def display_board(game_state):
    board = [0] * 25
    for tiger in extract_indices_fast(game_state.tigers_bb):
        board[tiger] = Piece_TIGER
    for goat in extract_indices_fast(game_state.goats_bb):
        board[goat] = Piece_GOAT
    piece = game_state.piece
    print("-"*26)
    for i, cell in enumerate(board):
        if i % 5 == 0:
            print("|", end=" ")
        print(piece[cell], end=" | ")
        if (i+1) % 5 == 0:
            print()
            print("-"*26)


def test_mcts():
    """Enhanced testing with performance metrics"""

    gs = BitboardGameState()

    # Performance tracking
    move_times = []
    simulations_per_move = []
    state_hash = defaultdict(int)
    move_count = 0

    time_limit = 0.6
    mcts = MCTS()
    while not gs.is_game_over:
        state_key = gs.key
        state_hash[state_key] += 1

        if state_hash[state_key] > 3:
            print("Draw by repetition!")
            break

        # Time the move decision
        start_time = time.time()

        # Use different time limits based on game phase
        # if gs.goats_to_place >= 10:  # Early Placement
        #     time_limit = 1.5
        # elif gs.goats_to_place >= 5:  # Mid Placement
        #     time_limit = 1.8
        # elif gs.goats_to_place <= 2:
        #     time_limit = 1.5
        # else:  # Late Placement and Movement Movement
        #     time_limit = 1.8
        move = mcts.search(gs, time_limit=time_limit)

        move_time = time.time() - start_time
        move_times.append(move_time)

        simulations_per_move.append(mcts.simulations_run)

        # Display current state
        system('clear')
        display_board(gs)
        print(f"Move {move_count + 1}")
        print(gs)

        print(f"Move selected: {move}, Time: {move_time:.2f}s")
        print(f"Simulations run: {mcts.simulations_run}")
        # mcts.visualize_tree(max_depth=1)
        print(f"Goat Wins: {mcts.goat_wins/mcts.simulations_run * 100:.2f}",
              f"Tiger Wins: {mcts.tiger_wins/mcts.simulations_run * 100:.2f}")

        gs.make_move(move)
        move_count += 1
        input("Press Enter to continue...")  # Remove for automated testing

    # Final results
    system('clear')
    display_board(gs)
    print(gs)

    result = gs.get_result
    if result:
        print(f"Winner: {gs.piece[result]}")
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


# Example usage
if __name__ == "__main__":
    run_game()
    # scratch()

    # test_mcts()

    # Profiling
    # with Profile() as profile:
    #     scratch()
    #     (
    #         Stats(profile)
    #         .strip_dirs()
    #         .sort_stats(SortKey.TIME)
    #         .print_stats(20)
    #     )
