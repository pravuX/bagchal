import random
from bagchal import BitboardGameState, Piece_TIGER, Piece_GOAT
from negamax import AlphaBetaAgent

# CONSTANTS
MATCHES_PER_ITERATION = 1  # Low for speed, high for accuracy
LEARNING_RATE = 2.0        # How much to change weights based on a win
PERTURBATION = 10.0        # How much "noise" to add for testing
ANCHOR_PARAM = 'w_eat'     # Do not tune this


def play_match(weights_A, weights_B):
    """
    Plays 2 games:
    1. A (Tiger) vs B (Goat)
    2. B (Tiger) vs A (Goat)
    Returns score for A: 2 (Win/Win), 1.5 (Win/Draw), 1 (Win/Loss), etc.
    """
    score_A = 0

    # Game 1: A is Tiger
    score_A += play_game(weights_A, weights_B, Piece_TIGER)

    # Game 2: A is Goat (so B is Tiger)
    # The function returns result for Tiger, so we invert logic if needed
    # Let's standardize play_game to return 1 if 'tiger_weights' wins, 0 if 'goat_weights' wins
    result = play_game(weights_B, weights_A, Piece_TIGER)

    # If B (Tiger) won, A (Goat) gets 0. If B lost, A gets 1.
    score_A += (1 - result)

    return score_A


def play_game(tiger_weights, goat_weights, p1_color):
    """
    Simulates one game.
    Returns 1 if Tiger wins, 0 if Goat wins, 0.5 for Draw.
    """
    gs = BitboardGameState()

    tiger_agent = AlphaBetaAgent(weights=tiger_weights)
    goat_agent = AlphaBetaAgent(weights=goat_weights)

    # Fast time limit for tuning! We care about relative strength, not perfect play.
    # 0.1s is usually enough to see if a weight is "dumb" or "smart".
    TIME_LIMIT = 0.1

    moves = 0
    # Hard cutoff to prevent infinite games during tuning
    MAX_MOVES = 200

    while not gs.is_game_over and moves < MAX_MOVES:
        if gs.turn == Piece_TIGER:
            move = tiger_agent.get_best_move(gs, time_limit=TIME_LIMIT)
        else:
            move = goat_agent.get_best_move(gs, time_limit=TIME_LIMIT)

        gs.make_move(move)
        moves += 1

    res = gs.get_result

    if res == Piece_TIGER:
        return 1.0
    if res == Piece_GOAT:
        return 0.0
    return 0.5  # Draw or Max Moves reached


def tune():
    # 1. Starting Center Weights (Your current values)
    center_weights = {
        'w_eat': 100.0,
        'w_potcap': 50.0,
        'w_mobility': 10.0,
        'w_trap': 10.0,
        'w_presence': 10.0,
        'w_inacc': 50.0,
        'triple_partial': 40.0,
        'triple_full': 200.0
    }

# 685 iterations
# --- Current Best Weights ---
#   w_eat: 100.00
#   w_potcap: 49.72
#   w_mobility: 39.57
#   w_trap: 41.16
#   w_presence: 31.20
#   w_inacc: 34.87
#   triple_partial: 0.10
#   triple_full: 192.19
# ----------------------------

    iteration = 0

    print(
        f"Starting Tuning. Anchor: {ANCHOR_PARAM} = {center_weights[ANCHOR_PARAM]}")

    while True:
        iteration += 1

        # 2. Create Deltas (Bernoulli distribution: +1 or -1)
        deltas = {}
        for k in center_weights:
            if k == ANCHOR_PARAM:
                deltas[k] = 0
            else:
                deltas[k] = random.choice([-1, 1]) * PERTURBATION

        # 3. Create Positive and Negative variants
        w_plus = {}
        w_minus = {}

        for k, v in center_weights.items():
            w_plus[k] = v + deltas[k]
            w_minus[k] = v - deltas[k]

            # Sanity checks (Weights usually shouldn't be negative)
            if w_plus[k] < 0:
                w_plus[k] = 0
            if w_minus[k] < 0:
                w_minus[k] = 0

        # 4. Play Match: Plus vs Minus
        # We want to see who is better relative to each other
        score_plus = play_match(w_plus, w_minus)

        # score_plus ranges from 0 to 2.
        # If score_plus > 1, Plus is better.
        # If score_plus < 1, Minus is better.

        result_gradient = (score_plus - 1.0)  # Range: -1.0 to +1.0

        # 5. Update Center Weights
        # Formula: New = Old + (LearningRate * Result * GradientVector)

        # Dynamic learning rate (decays over time)
        ck = LEARNING_RATE / (iteration ** 0.333)

        print(f"Iter {iteration} | Result: {score_plus} (Positive vs Negative)")

        for k in center_weights:
            if k == ANCHOR_PARAM:
                continue

            # SPSA Update Rule
            # If Result was positive (Plus won), we move in direction of Delta
            # If Result was negative (Minus won), we move opposite to Delta
            change = ck * result_gradient * deltas[k]
            center_weights[k] += change

            # Soft bounds to prevent weirdness
            if center_weights[k] < 0:
                center_weights[k] = 0.1

        # 6. Log every 5 iterations
        if iteration % 5 == 0:
            print("\n--- Current Best Weights ---")
            for k, v in center_weights.items():
                print(f"  {k}: {v:.2f}")
            print("----------------------------\n")


if __name__ == "__main__":
    tune()
