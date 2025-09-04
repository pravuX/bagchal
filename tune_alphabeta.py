# tune_alphabeta.py
import logging
import optuna
# import sys
import os
from bagchal import GameState, Piece, HeuristicParams 
from alphabeta import MinimaxAgent 

# Time limit in seconds for each move. 
TIME_LIMIT_PER_MOVE = 1

# Number of games to play in the tournament for each trial.
GAMES_PER_TRIAL = 10

# Total number of different parameter sets Optuna will test.
TOTAL_TRIALS = 101

# --- Store Default Parameters ---
DEFAULT_PARAMS = HeuristicParams()


def run_headless_game(tiger_params: HeuristicParams, goat_params: HeuristicParams) -> Piece:
    """
    Runs a single game between two Alpha-Beta AIs with different heuristic parameters.
    Returns the winning piece or Piece.EMPTY for a draw.
    """
    # Clear static tables to ensure a clean slate for each game
    # MinimaxAgent.transposition_table.clear()
    # MinimaxAgent.previous_evaluations.clear()

    # Create a fresh initial game state
    board = [Piece.EMPTY] * 25
    for pos in [0, 4, 20, 24]:
        board[pos] = Piece.TIGER
    game_state = GameState(board, Piece.GOAT, 20, 0)
    game_state.init_prioritization()

    move_count = 0
    max_moves = 100  # Safeguard against infinitely long games

    while not game_state.is_game_over() and move_count < max_moves:
        current_player = game_state.turn

        # Set the heuristic parameters for the player whose turn it is
        if current_player == Piece.TIGER:
            GameState.set_heuristic_params(tiger_params)
        else:  # Piece.GOAT
            GameState.set_heuristic_params(goat_params)

        # Create a new agent instance for the current state
        ai_agent = MinimaxAgent()
        best_move = ai_agent.get_best_move(game_state, time_limit=TIME_LIMIT_PER_MOVE)

        if best_move is None:
            break

        game_state = game_state.make_move(best_move)
        move_count += 1

    # Restore default params as a clean-up step
    GameState.set_heuristic_params(DEFAULT_PARAMS)

    result = game_state.get_result()
    return result if result is not None else Piece.EMPTY


def setup_logger(trial_number):
    LOG_DIR = "log"
    os.makedirs(LOG_DIR, exist_ok=True)
    # Create a logger
    logger = logging.getLogger(f"Trial-{trial_number}")
    logger.setLevel(logging.INFO)

    # Prevent logs from propagating to the root logger (which prints to console)
    logger.propagate = False

    # Remove old handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create a file handler
    log_file_path = os.path.join(LOG_DIR, f"trial_{trial_number}.log")
    handler = logging.FileHandler(log_file_path)
    handler.setLevel(logging.INFO)

    # Create a logging format
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(handler)

    return logger

def objective(trial: optuna.trial.Trial) -> float:
    """
    The objective function for Optuna, adapted for the MinimaxAgent.
    """
    logger = setup_logger(trial.number)
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

        w_eat=trial.suggest_float("w_eat", 0.5, 3.0),
        w_potcap=trial.suggest_float("w_potcap", 0.5, 3.0),
        w_mobility=trial.suggest_float("w_mobility", 0.1, 1.5),
        w_trap=trial.suggest_float("w_trap", 0.5, 3.0),
        w_presence=trial.suggest_float("w_presence", 0.5, 2.0),
        w_inacc=trial.suggest_float("w_inacc", 0.1, 1.5),
    )


    wins = 0
    num_games = GAMES_PER_TRIAL

    logger.info(f"--- Starting Trial {trial.number} ---")
    logger.info(f"Parameters: {trial.params}")

    for i in range(num_games):
        # Alternate who plays which side
        if i < num_games / 2:
            # sys.stdout.write(f"  Game {i+1}/{num_games} (Challenger as Tiger)... ")
            logger.info(f"Game {i+1}/{num_games} (Challenger as Tiger)...")
            winner = run_headless_game(tiger_params=challenger_params, goat_params=DEFAULT_PARAMS)
            if winner == Piece.TIGER:
                wins += 1
                # sys.stdout.write("WIN\n")
                logger.info("Result: WIN")
            else:
                # sys.stdout.write("LOSS/DRAW\n")
                logger.info("Result: LOSS/DRAW")
        else:
            # sys.stdout.write(f"  Game {i+1}/{num_games} (Challenger as Goat)... ")
            logger.info(f"Game {i+1}/{num_games} (Challenger as Goat)...")
            winner = run_headless_game(tiger_params=DEFAULT_PARAMS, goat_params=challenger_params)
            if winner == Piece.GOAT:
                wins += 1
                # sys.stdout.write("WIN\n")
                logger.info("Result: WIN")
            else:
                # sys.stdout.write("LOSS/DRAW\n")
                logger.info("Result: LOSS/DRAW")

    win_rate = wins / num_games
    logger.info(f"--- Trial {trial.number} Finished. Win Rate: {win_rate:.2f} ---")


    print(f"--- Trial {trial.number} Finished. Win Rate: {win_rate:.2f} ---")

    return win_rate


if __name__ == "__main__":
    # Create and run the study
    study = optuna.create_study(direction="maximize")
    print(f"Starting Optuna study for MinimaxAgent...")
    print(f"Config: {TOTAL_TRIALS} trials, {GAMES_PER_TRIAL} games/trial, {TIME_LIMIT_PER_MOVE}s/move.")

    # Use n_jobs=-1 for parallel processing to speed things up significantly
    study.optimize(objective, n_trials=TOTAL_TRIALS, n_jobs=-1)

    # Print the results
    print("\n\n--- Optuna Study Finished ---")
    print(f"Best trial number: {study.best_trial.number}")
    print(f"Best win rate: {study.best_trial.value:.4f}")
    print("Best parameters found:")
    for key, value in study.best_trial.params.items():
        print(f"  {key}: {value:.4f}")

