from mcts import MCTS
from collections import defaultdict
from bagchal import GameState, Piece
import time
from collections import defaultdict, Counter
from multiprocessing import Pool, cpu_count


def self_play_wrapper(_):
    # This wrapper avoids sharing state_hash globally.
    from collections import defaultdict
    state_hash = defaultdict(int)
    return self_play(state_hash)


def gather_statistics_parallel(no_games=1000):
    interpret_result = {
        -1: "Goat Wins.",
        0: "Draws.",
        1: "Tiger Wins."
    }

    print("Collecting Statistics...")

    start = time.time()

    num_workers = cpu_count()  # Or set manually
    with Pool(num_workers) as pool:
        results_list = pool.map(self_play_wrapper, range(no_games))

    # Aggregate results
    results = Counter(results_list)

    end = time.time()
    print(no_games, "games played.")
    for result, count in results.items():
        print(count, interpret_result[result])
    print("Took", end - start, "seconds.")


def self_play(state_hash):
    # plays one full game against itself
    # returns the result of the game
    board = [Piece.EMPTY] * 25
    pos_tiger = [0, 4, 20, 24]
    for pos in pos_tiger:
        board[pos] = Piece.TIGER

    game_state = GameState(board, turn=Piece.GOAT,
                           goat_count=20, eaten_goat_count=0)
    game_state.update_trapped_tiger()
    game_state.init_prioritization()

    # game loop
    while not game_state.is_game_over():
        state_key = game_state.key()
        state_hash[state_key] += 1

        if state_hash[state_key] > 3:
            return 0  # Draw by repetition.

        if game_state.goat_count >= 10:  # Early Placement
            time_limit = 0.3
        elif game_state.goat_count >= 5:  # Mid Placement
            time_limit = 0.5
        else:  # Late Placement and Movement Movement
            time_limit = 0.7

        mcts = MCTS(initial_state=game_state, time_limit=time_limit)
        move = mcts.search()

        game_state = game_state.make_move(move)

        if len(GameState.transposition_table_with_scores) >= 100_000:
            GameState.transposition_table_with_scores.clear()
        if len(state_hash) >= 100_000:
            state_hash.clear()

    return game_state.get_result()


def gather_statistics():
    interpret_result = {
        -1: "Goat Wins.",
        0: "Draws.",
        1: "Tiger Wins."
    }

    state_hash = defaultdict(int)

    results = defaultdict(int)

    start = time.time()

    no_games = 1
    for _ in range(no_games):
        result = self_play(state_hash)
        results[result] += 1
        if len(state_hash) >= 2_000_000:
            state_hash.clear()
        if len(GameState.transposition_table_with_scores) >= 2_000_000:
            GameState.transposition_table_with_scores.clear()

    end = time.time()
    print(no_games, "games played.")
    for result in results:
        print(results[result], interpret_result[result])

    print("Took", end-start)


if __name__ == "__main__":
    gather_statistics_parallel()
