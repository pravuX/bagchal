from mcts import MCTS
from bagchal import *
import time
from collections import defaultdict, Counter
from multiprocessing import Pool, cpu_count


def self_play_wrapper(_):
    # This wrapper avoids sharing state_hash globally.
    from collections import defaultdict
    state_hash = defaultdict(int)
    return self_play(state_hash)


def gather_statistics_parallel(no_games=5):
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
    game_state = BitboardGameState()

    # game loop
    mcts = MCTS()
    while not game_state.is_game_over:
        state_key = game_state.key
        state_hash[state_key] += 1

        if state_hash[state_key] > 3:
            return 0  # Draw by repetition.

        if game_state.goats_to_place >= 10:  # Early Placement
            time_limit = 0.3
        elif game_state.goats_to_place >= 5:  # Mid Placement
            time_limit = 0.5
        else:  # Late Placement and Movement Movement
            time_limit = 0.7

        move = mcts.search(game_state, time_limit=time_limit)

        game_state.make_move(move)

    return game_state.get_result


if __name__ == "__main__":
    gather_statistics_parallel()
