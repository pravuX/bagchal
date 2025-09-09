import random
import numpy as np
import os
from bagchal import HeuristicParams, GameState,  Piece
from concurrent.futures import ProcessPoolExecutor
from alphabeta import MinimaxAgent


#in seconds
TIME_LIMIT_PER_MOVE = 1
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

def create_init_population(pop_size):
    population = []
    for _ in range(pop_size):
        chromosome = HeuristicParams(
                tiger_capture_bonus = random.uniform(0.0, 10.0),
                tiger_potential_capture_bonus = random.uniform(5.0, 15.0),
                tiger_strategic_position_bonus = random.uniform(0.0, 10.0),
                tiger_center_penalty = random.uniform(0.0, 10.0),
                tiger_unblock_bonus = random.uniform(5.0, 15.0),
                tiger_block_penalty = random.uniform(5.0, 15.0),
                goat_trap_bonus = random.uniform(0.0, 15.0),
                goat_clustering_bonus = random.uniform(0.0, 10.0),
                goat_tiger_clustering_penalty = random.uniform(0.0, 10.0),
                goat_strategic_position_bonus = random.uniform(0.0, 10.0),
                goat_outer_edge_bonus = random.uniform(0.0, 10.0),
                goat_block_capture_bonus = random.uniform(10.0, 20.0),
                goat_escape_bonus= random.uniform(5.0, 15.0),
                goat_sacrifice_penalty = random.uniform(0.0, 30.0),
                w_eat = random.uniform(0.0, 10.0),
                w_potcap = random.uniform(0.0, 10.0),
                w_mobility = random.uniform(0.0, 10.0),
                w_trap = random.uniform(0.0, 10.0),
                w_presence = random.uniform(0.0, 10.0),
                w_inacc = random.uniform(0.0, 10.0)
                )
        population.append(chromosome)
    return population

def calculate_fitness(population):
    fitness_score = [0] * len(population)
    game_pairs = []
    for i in range(len(population)):
        for j in range(i+1, len(population)):
            game_pairs.append((i, j))
            game_pairs.append((j, i))

    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = [executor.submit(run_headless_game, population[p1_idx], population(p2_idx)) for p1_idx, p2_idx in game_pairs]

        for i, future in enumerate(futures):
            winner = future.result()
            p1_idx, p2_idx = game_pairs[i]

            if winner == Piece.TIGER:
                fitness_score[p1_idx] += 1
            elif winner == Piece.GOAT:
                fitness_score[p2_idx] += 1
    return fitness_score

