from collections import defaultdict
from os import system
from bagchal import *
from negamax import AlphaBetaAgent
from game import Game
# from alphabeta import MinimaxAgent
import pprint
from mcts import MCTS
import time
import numpy as np


from cProfile import Profile
from pstats import SortKey, Stats


def run_game():
    # board = np.array([Piece_EMPTY] * 25, dtype=np.int8)
    # pos_tiger = [0, 4, 20, 24]
    # board[pos_tiger[0]] = Piece_TIGER
    # board[pos_tiger[1]] = Piece_TIGER
    # board[pos_tiger[2]] = Piece_TIGER
    # board[pos_tiger[3]] = Piece_TIGER
    #
    # game_state = GameState(board, turn=Piece_GOAT,
    #                        goat_count=20, eaten_goat_count=0)
    # game_state.update_trapped_tiger()
    # game_state.init_prioritization()
    game_state = BitboardGameState()
    game = Game(game_state=game_state)
    game.run()


def debug_mcts():
    # check get_legal_moves
    board = [Piece_TIGER, Piece_GOAT, Piece_GOAT, Piece_TIGER, Piece_EMPTY, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_TIGER, Piece_TIGER, Piece_GOAT, Piece_GOAT,
             Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_GOAT]
    goat_count = 0
    eaten_goat_count = 0
    turn = Piece_GOAT
    game_state = GameState(board, turn=turn,
                           goat_count=goat_count, eaten_goat_count=eaten_goat_count)
    game_state.update_tiger_pos()
    print(game_state.get_legal_moves())


def debug_minimax():
    board = [Piece_TIGER, Piece_GOAT, Piece_GOAT, Piece_EMPTY, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_TIGER, Piece_GOAT, Piece_TIGER,
             Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_EMPTY, Piece_TIGER, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_GOAT, Piece_EMPTY, Piece_GOAT]
    goat_count = 0
    eaten_goat_count = 2
    turn = Piece_TIGER
    game_state = GameState(board, turn=turn,
                           goat_count=goat_count, eaten_goat_count=eaten_goat_count)
    game_state.update_trapped_tiger()
    print(game_state.get_legal_moves())

    minimax_agent = MinimaxAgent(depth=3)
    print(minimax_agent.get_best_move(game_state))
    print(game_state.stringify())


def scratch():
    # board = np.array([Piece_EMPTY] * 25, dtype=np.int8)

    # early movement
    # pos_tiger = [0, 6, 13, 19]
    # empty = set([5])
    # pos_goat = list(set(range(25)) - empty - set(pos_tiger))
    # for pos in pos_tiger:
    #     board[pos] = Piece_TIGER
    # for pos in pos_goat:
    #     board[pos] = Piece_GOAT
    # goat_count = 20 - len(pos_goat)
    # eaten_goat_count = 0
    # turn = Piece_GOAT
    # game_state = GameState(board, turn=turn,
    #                        goat_count=goat_count, eaten_goat_count=eaten_goat_count)

    # late placement
    # pos_tiger = [0, 9, 12, 24]
    # pos_goat = [11]
    # for pos in pos_tiger:
    #     board[pos] = Piece_TIGER
    # for pos in pos_goat:
    #     board[pos] = Piece_GOAT
    # eaten_goat_count = 4
    # goat_count = 20 - len(pos_goat) - eaten_goat_count
    # turn = Piece_TIGER
    # game_state = GameState(board, turn=turn,
    #                        goat_count=goat_count, eaten_goat_count=eaten_goat_count)

    # initial configuration
    # pos_tiger = [0, 4, 20, 24]
    # board[pos_tiger[0]] = Piece_TIGER
    # board[pos_tiger[1]] = Piece_TIGER
    # board[pos_tiger[2]] = Piece_TIGER
    # board[pos_tiger[3]] = Piece_TIGER
    # game_state = GameState(board)

    # for minimax agent
    gs = BitboardGameState()
    gs.tigers_bb = 0
    # pos_tiger = [0, 11, 20, 24]
    # pos_goat = [1, 2, 3, 4, 8, 9, 10, 15, 21, 22, 23]

    pos_tiger = [0, 8, 20, 24]
    pos_goat = [1, 2, 3, 5, 10, 14, 15, 19, 21, 22]
    for p in pos_tiger:
        gs.tigers_bb |= (1 << p)
    for p in pos_goat:
        gs.goats_bb |= (1 << p)
    gs.goats_to_place = 10
    display_board(gs)
    print(gs)
    #
    # minimax_agent = MinimaxAgent()
    # move = minimax_agent.get_best_move(gs, time_limit=1)
    # print(move)

    alphabeta_agent = AlphaBetaAgent()
    moves = gs.get_legal_moves()
    print("unsorted\t\t", moves)
    ordered_moves = alphabeta_agent.get_ordered_moves(gs, moves, None)
    print("sorted at once\t\t", ordered_moves)
    for i in range(len(moves)):
        alphabeta_agent.pick_move(gs, moves, i, None, 0)
    print("sorted incremen\t\t", moves)
    move = alphabeta_agent.get_best_move(gs, time_limit=1, game_history=[])
    print(move)
    #
    # game_state.unmake_move()
    # print(minimax_agent.evaluate_state(game_state))

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


def test_alphabeta():
    """Enhanced testing with performance metrics"""
    board = np.array([Piece_EMPTY] * 25, dtype=np.int8)
    pos_tiger = [0, 4, 20, 24]
    for pos in pos_tiger:
        board[pos] = Piece_TIGER
    pos_goat = []
    for pos in pos_goat:
        board[pos] = Piece_GOAT

    game_state = GameState(board, turn=Piece_GOAT,
                           goat_count=20, eaten_goat_count=0)

    state_hash = defaultdict(int)

    minimax_agent = MinimaxAgent()
    while not game_state.is_game_over:
        state_key = game_state.key
        state_hash[state_key] += 1

        if state_hash[state_key] > 3:
            print("Draw by repetition!")
            break

        start_time = time.time()

        move = minimax_agent.get_best_move(game_state, time_limit=1.5)

        move_time = time.time() - start_time

        # Display current state
        system('clear')
        display_board(game_state)
        print(game_state)
        print(f"Took {move_time:.2f}s. Move Selected {move}")

        game_state.make_move(move)
        input("Press Enter to continue...")  # Remove for automated testing

    # Final results
    system('clear')
    display_board(game_state)
    print(game_state)
    # print(len(game_state.transposition_table_with_scores),
    #       "unique states encountered.")

    result = game_state.get_result
    if result:
        print(f"Winner: {game_state.piece[result]}")
    else:
        print("Draw!")


def test_mcts():
    """Enhanced testing with performance metrics"""
    board = np.array([Piece_EMPTY] * 25, dtype=np.int8)
    pos_tiger = [0, 4, 20, 24]
    for pos in pos_tiger:
        board[pos] = Piece_TIGER
    pos_goat = []
    for pos in pos_goat:
        board[pos] = Piece_GOAT

    game_state = GameState(board, turn=Piece_GOAT,
                           goat_count=20, eaten_goat_count=0)
    # game_state.update_trapped_tiger()
    # game_state.init_prioritization()

    # Performance tracking
    move_times = []
    simulations_per_move = []
    game_history = []
    state_hash = defaultdict(int)
    move_count = 0

    time_limit = 1.5
    # mcts = MCTS(initial_state=game_state, time_limit=time_limit)
    mcts = MCTS()
    while not game_state.is_game_over:
        state_key = game_state.key
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
        move = mcts.search(game_state, time_limit=1.5)

        move_time = time.time() - start_time
        move_times.append(move_time)

        simulations_per_move.append(mcts.simulations_run)

        # Store game history
        # game_history.append({
        #     'move': move,
        #     'player': game_state.turn,
        #     'board_state': game_state.stringify(),
        #     'goats_remaining': game_state.goat_count,
        #     'goats_eaten': game_state.eaten_goat_count,
        #     'move_time': move_time,
        #     'simulations_per_second': getattr(mcts, 'simulations_run', 0) / move_time if move_time > 0 else 0
        # })

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

        game_state.make_move(move)
        # mcts.re_reoot(game_state, time_limit=time_limit)
        move_count += 1
        input("Press Enter to continue...")  # Remove for automated testing

    # Final results
    system('clear')
    display_board(game_state)
    print(game_state)
    # print(len(game_state.transposition_table_with_scores),
    #       "unique states encountered.")

    result = game_state.get_result
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

    # return game_history


def analyze_game_performance(game_history):
    """Analyze the performance of MCTS across the game"""
    goat_moves = [h for h in game_history if h['player'] == Piece_GOAT]
    tiger_moves = [h for h in game_history if h['player'] == Piece_TIGER]

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
    # while True:
    #     scratch()
    #     c = input("Continue? y/n")
    #     if not c.lower().startswith('y'):
    #         break
    # debug_minimax()
    # test_alphabeta()
    #
    # scratch()
    # with Profile() as profile:
    #     scratch()
    #     # test_mcts()
    #     (
    #         Stats(profile)
    #         .strip_dirs()
    #         .sort_stats(SortKey.TIME)
    #         .print_stats(20)
    #     )
