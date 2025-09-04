# tune.py
import optuna
import sys
from bagchal import GameState, HeuristicParams, Piece
from mcts import MCTS

# Number of MCTS simulations per move.
MCTS_SIMULATIONS_PER_MOVE = 50

# Number of games to play in the tournament for each trial.
GAMES_PER_TRIAL = 10

# Total number of different parameter sets Optuna will test.
TOTAL_TRIALS = 5

# --- Store Default Parameters ---
DEFAULT_PARAMS = HeuristicParams()


def run_headless_game(tiger_params: HeuristicParams, goat_params: HeuristicParams) -> Piece:
    """
    Runs a single game between two AIs with different heuristic parameters.
    Returns the winning piece or Piece.EMPTY for a draw.
    """
    # Create a fresh initial game state
    board = [Piece.EMPTY] * 25
    for pos in [0, 4, 20, 24]:
        board[pos] = Piece.TIGER
    game_state = GameState(board, Piece.GOAT, 20, 0)
    game_state.init_prioritization()

    move_count = 0
    max_moves = 100

    while not game_state.is_game_over() and move_count < max_moves:
        current_player = game_state.turn

        # Set the heuristic parameters for the player whose turn it is
        if current_player == Piece.TIGER:
            GameState.set_heuristic_params(tiger_params)
        else:  # Piece.GOAT
            GameState.set_heuristic_params(goat_params)

        # Create a new MCTS instance for the current state
        ai = MCTS(initial_state=game_state, max_simulations=MCTS_SIMULATIONS_PER_MOVE)
        best_move = ai.search()

        if best_move is None:
            # No legal moves available, the game should be over.
            break

        game_state = game_state.make_move(best_move)
        move_count += 1

    # Restore default params as a clean-up step
    GameState.set_heuristic_params(DEFAULT_PARAMS)

    result = game_state.get_result()
    return result if result is not None else Piece.EMPTY


def objective(trial: optuna.trial.Trial) -> float:
    """
    The main objective function for Optuna. A single trial runs a tournament
    and returns the win rate of the challenger AI.
    """
    challenger_params = HeuristicParams(
        # Tiger parameters
        tiger_capture_bonus=trial.suggest_float("tiger_capture_bonus", 0.05, 5.0),
        tiger_potential_capture_bonus=trial.suggest_float("tiger_potential_capture_bonus", 5.0, 15.0),
        tiger_strategic_position_bonus=trial.suggest_float("tiger_strategic_position_bonus", 1.5, 5.0),
        tiger_center_penalty=trial.suggest_float("tiger_center_penalty", 0.0, 2.0),
        tiger_unblock_bonus=trial.suggest_float("tiger_unblock_bonus", 4.0, 10.0),
        tiger_block_penalty=trial.suggest_float("tiger_block_penalty", 3.0, 8.0),

        # Goat parameters
        goat_trap_bonus=trial.suggest_float("goat_trap_bonus", 0.5, 7.0),
        goat_clustering_bonus=trial.suggest_float("goat_clustering_bonus", 1.5, 3.5),
        goat_tiger_clustering_penalty=trial.suggest_float("goat_tiger_clustering_penalty", 1.5, 4.0),
        goat_strategic_position_bonus=trial.suggest_float("goat_strategic_position_bonus", 1.5, 4.0),
        goat_outer_edge_bonus=trial.suggest_float("goat_outer_edge_bonus", 2.5, 5.0),
        goat_block_capture_bonus=trial.suggest_float("goat_block_capture_bonus", 5.0, 15.0),
        goat_escape_bonus=trial.suggest_float("goat_escape_bonus", 2.0, 12.0),
        goat_sacrifice_penalty=trial.suggest_float("goat_sacrifice_penalty", 15.0, 30.0),
    )

    wins = 0
    num_games = GAMES_PER_TRIAL

    print(f"\n--- Starting Trial {trial.number} ---")

    for i in range(num_games):
        if i < num_games / 2:
            # Challenger plays as Tiger
            sys.stdout.write(f"  Game {i+1}/{num_games} (Challenger as Tiger)... ")
            winner = run_headless_game(tiger_params=challenger_params, goat_params=DEFAULT_PARAMS)
            if winner == Piece.TIGER:
                wins += 1
                sys.stdout.write("WIN\n")
            else:
                sys.stdout.write("LOSS/DRAW\n")
        else:
            # Challenger plays as Goat
            sys.stdout.write(f"  Game {i+1}/{num_games} (Challenger as Goat)... ")
            winner = run_headless_game(tiger_params=DEFAULT_PARAMS, goat_params=challenger_params)
            if winner == Piece.GOAT:
                wins += 1
                sys.stdout.write("WIN\n")
            else:
                sys.stdout.write("LOSS/DRAW\n")
        sys.stdout.flush()


    win_rate = wins / num_games
    print(f"--- Trial {trial.number} Finished. Win Rate: {win_rate:.2f} ---")
    return win_rate


if __name__ == "__main__":
    # Create a study object and specify the direction as "maximize"
    study = optuna.create_study(direction="maximize")

    # Start the optimization process
    print(f"Starting Optuna study...")
    print(f"Configuration: {TOTAL_TRIALS} trials, {GAMES_PER_TRIAL} games per trial, {MCTS_SIMULATIONS_PER_MOVE} simulations per move.")

    study.optimize(objective, n_trials=TOTAL_TRIALS, n_jobs=-1)

    # Print the results
    print("\n\n--- Optuna Study Finished ---")
    print(f"Best trial number: {study.best_trial.number}")
    print(f"Best win rate: {study.best_trial.value:.4f}")
    print("Best parameters found:")
    for key, value in study.best_trial.params.items():
        print(f"  {key}: {value:.4f}")
