import random
import pickle
import numpy as np
import os
import logging
from dataclasses import astuple, asdict
from concurrent.futures import ProcessPoolExecutor
from typing import Tuple

from bagchal import HeuristicParams, GameState, Piece_EMPTY, Piece_GOAT, Piece_TIGER
from alphabeta import MinimaxAgent

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("genetic_algorithm.log"),
        logging.StreamHandler()
    ]
)

# --- GA Hyperparameters & Constants ---
TIME_LIMIT_PER_MOVE = 0.5  # in seconds
MAX_MOVES = 150          # Safeguard against infinite loops
POPULATION_SIZE = 30
NUM_GENERATIONS = 100
CHECKPOINT_FILE = "ga_checkpoint.pkl"

# --- Parameter Bounds for Initialization and Mutation ---
PARAM_BOUNDS = {
    "tiger_capture_bonus": (0.0, 10.0),
    "tiger_potential_capture_bonus": (5.0, 15.0),
    "tiger_block_penalty": (5.0, 15.0),
    "goat_clustering_bonus": (0.0, 10.0),
    "goat_strategic_position_bonus": (0.0, 10.0),
    "goat_outer_edge_bonus": (0.0, 10.0),
    "goat_sacrifice_penalty": (0.0, 30.0),
    "w_eat": (0.0, 10.0),
    "w_potcap": (0.0, 10.0),
    "w_mobility": (0.0, 10.0),
    "w_trap": (0.0, 10.0),
    "w_presence": (0.0, 10.0),
    "w_inacc": (0.0, 10.0)
}


def run_headless_game(tiger_params: HeuristicParams, goat_params: HeuristicParams) -> int:
    """
    Runs a single, complete game of Bagchal between two AI players with different
    heuristic parameters, without any graphical interface.
    """
    initial_board = np.array([Piece_EMPTY] * 25, dtype=np.int8)
    initial_board[[0, 4, 20, 24]] = Piece_TIGER

    game_state = GameState(board=initial_board,
                           turn=Piece_GOAT,
                           goat_count=20,
                           eaten_goat_count=0)
    move_count = 0

    while not game_state.is_game_over and move_count < MAX_MOVES:
        if game_state.turn == Piece_TIGER:
            curr_player_params = tiger_params
        else:  # Piece_GOAT
            curr_player_params = goat_params

        ai_agent = MinimaxAgent(params=curr_player_params)
        best_move = ai_agent.get_best_move(game_state, time_limit=TIME_LIMIT_PER_MOVE)

        if best_move is None:
            break

        game_state.make_move(best_move)
        move_count += 1

    result = game_state.get_result
    return result if result is not None else Piece_EMPTY


def create_init_population(pop_size):
    """Creates the initial population with random parameters within bounds."""
    population = []
    for _ in range(pop_size):
        params = {name: random.uniform(low, high) for name, (low, high) in PARAM_BOUNDS.items()}
        population.append(HeuristicParams(**params))
    return population


def calculate_fitness(population):
    """Calculates fitness by playing a round-robin tournament in parallel."""
    fitness_scores = [0] * len(population)
    game_pairs = []
    # Create a list of all games to be played
    for i in range(len(population)):
        for j in range(i + 1, len(population)):
            game_pairs.append((i, j))  # i is tiger, j is goat
            game_pairs.append((j, i))  # j is tiger, i is goat

    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = [executor.submit(run_headless_game, population[p1_idx], population[p2_idx])
                   for p1_idx, p2_idx in game_pairs]

        for i, future in enumerate(futures):
            winner = future.result()
            p1_idx, p2_idx = game_pairs[i]  # p1 was tiger, p2 was goat

            if winner == Piece_TIGER:
                fitness_scores[p1_idx] += 1
            elif winner == Piece_GOAT:
                fitness_scores[p2_idx] += 1
            # No points awarded for a draw
    return fitness_scores


def select_one_parent(population, fitness_scores, tournament_size=5):
    """
    Selects a single parent using tournament selection.
    """
    # Get the indices of the contestants for this tournament
    contestant_indices = random.sample(range(len(population)), tournament_size)
    # Find the index of the winner (the one with the highest fitness)
    winner_index = max(contestant_indices, key=lambda i: fitness_scores[i])
    # Return the winning individual
    return population[winner_index]


def crossover(parent1: HeuristicParams, parent2: HeuristicParams) -> Tuple[HeuristicParams, HeuristicParams]:
    """Performs blend crossover (BLX-alpha) on two parents."""
    p1_tuple = astuple(parent1)
    p2_tuple = astuple(parent2)
    alpha = random.random()  # Alpha can be fixed or random
    child_tuple1 = tuple(alpha * p1 + (1 - alpha) * p2 for p1, p2 in zip(p1_tuple, p2_tuple))
    child_tuple2 = tuple(alpha * p2 + (1 - alpha) * p1 for p1, p2 in zip(p1_tuple, p2_tuple))
    return HeuristicParams(*child_tuple1), HeuristicParams(*child_tuple2)


def mutation(individual: HeuristicParams, mutation_rate: float, mutation_strength: float) -> HeuristicParams:
    """Performs mutation on a HeuristicParams object, respecting bounds."""
    param_names = list(asdict(individual).keys())
    mutated_values = list(astuple(individual))

    for i, name in enumerate(param_names):
        if random.random() < mutation_rate:
            lower_bound, upper_bound = PARAM_BOUNDS[name]
            range_width = upper_bound - lower_bound
            mutation_amount = random.uniform(-mutation_strength, mutation_strength) * range_width
            mutated_values[i] += mutation_amount
            # Clamp the value to ensure it stays within the valid bounds
            mutated_values[i] = max(lower_bound, min(upper_bound, mutated_values[i]))

    return HeuristicParams(*mutated_values)


def main():
    """Main function to run the genetic algorithm."""
    start_generation = 0
    population = []

    if os.path.exists(CHECKPOINT_FILE):
        logging.info(f"--- Resuming from checkpoint file: {CHECKPOINT_FILE} ---")
        with open(CHECKPOINT_FILE, "rb") as f:
            checkpoint = pickle.load(f)
            start_generation = checkpoint['generation'] + 1
            population = checkpoint['population']
        logging.info(f"Resuming from the start of Generation {start_generation}")
    else:
        logging.info("--- Starting a new run from scratch ---")
        population = create_init_population(POPULATION_SIZE)

    for gen in range(start_generation, NUM_GENERATIONS):
        logging.info(f"\n--- Starting Generation {gen} ---")

        fitness_scores = calculate_fitness(population)
        best_idx = np.argmax(fitness_scores)
        logging.info(f"  > Best fitness in Gen {gen}: {fitness_scores[best_idx]}")
        logging.info(f"  > Best params: {population[best_idx]}")

        new_population = []

        # --- Elitism: The best individual moves to the next generation unchanged ---
        best_individual = population[best_idx]
        new_population.append(best_individual)

        while len(new_population) < POPULATION_SIZE:
            parent1 = select_one_parent(population, fitness_scores)
            parent2 = select_one_parent(population, fitness_scores)

            # Ensure parents are not the same individual to promote diversity
            while parent1 is parent2:
                parent2 = select_one_parent(population, fitness_scores)

            child1, child2 = crossover(parent1, parent2)

            # Mutate children
            child1 = mutation(child1, mutation_rate=0.05, mutation_strength=0.2)
            child2 = mutation(child2, mutation_rate=0.05, mutation_strength=0.2)

            new_population.append(child1)
            # Add the second child only if there is room
            if len(new_population) < POPULATION_SIZE:
                new_population.append(child2)

        population = new_population

        # --- Save Checkpoint ---
        logging.info(f"--- Generation {gen} complete. Saving checkpoint... ---")
        checkpoint = {
            'generation': gen,
            'population': population
        }
        with open(CHECKPOINT_FILE, "wb") as f:
            pickle.dump(checkpoint, f)
        logging.info("Checkpoint saved.")

    logging.info("\n--- Genetic Algorithm Finished ---")
    # Final analysis of the last generation
    fitness_scores = calculate_fitness(population)
    best_idx = np.argmax(fitness_scores)
    logging.info("Absolute best individual found:")
    logging.info(f"  > Fitness: {fitness_scores[best_idx]}")
    logging.info(f"  > Parameters: {population[best_idx]}")


if __name__ == "__main__":
    main()
