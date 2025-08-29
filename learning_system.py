import numpy as np
import pickle
from dataclasses import asdict
from typing import List, Dict, Tuple
from collections import defaultdict
import optuna
from copy import deepcopy


class GameLogger:
    """Logs games and analyzes move quality"""

    def __init__(self):
        self.games: List[Dict] = []
        self.move_stats = defaultdict(
            lambda: {'wins': 0, 'losses': 0, 'draws': 0})

    def log_game(self, moves: List[Tuple], winner: int, states: List,
                 mcts_stats: List[Dict] = None):
        """Log a complete game with moves, winner, and states"""
        game_data = {
            'moves': moves,
            'winner': winner,
            'states': states,
            'mcts_stats': mcts_stats or [],
            'num_moves': len(moves)
        }
        self.games.append(game_data)
        self._update_move_stats(moves, winner, states)

    def _update_move_stats(self, moves, winner, states):
        """Update statistics for each move type"""
        for i, (move, state) in enumerate(zip(moves, states)):
            move_key = self._categorize_move(move, state)
            player = state.turn

            if winner == player:
                self.move_stats[move_key]['wins'] += 1
            elif winner == -player:
                self.move_stats[move_key]['losses'] += 1
            else:
                self.move_stats[move_key]['draws'] += 1

    def _categorize_move(self, move, state) -> str:
        """Categorize moves for analysis"""
        from bagchal import Piece  # Import here to avoid circular imports
        src, dst = move
        if src == dst:
            return "goat_placement"
        elif state.board[src] == Piece.TIGER:
            if abs(src - dst) > 1:
                return "tiger_capture"
            return "tiger_movement"
        else:
            return "goat_movement"

    def analyze_move_effectiveness(self) -> Dict:
        """Analyze which types of moves are most effective"""
        analysis = {}
        for move_type, stats in self.move_stats.items():
            total = sum(stats.values())
            if total > 0:
                win_rate = stats['wins'] / total
                analysis[move_type] = {
                    'win_rate': win_rate,
                    'total_games': total,
                    'stats': stats
                }
        return analysis

    def save_data(self, filename: str):
        """Save logged games to file"""
        with open(filename, 'wb') as f:
            pickle.dump(self.games, f)

    def load_data(self, filename: str):
        """Load logged games from file"""
        with open(filename, 'rb') as f:
            self.games = pickle.load(f)


class ParameterOptimizer:
    """Uses Optuna to optimize heuristic parameters"""

    def __init__(self, num_evaluation_games: int = 50):
        self.num_evaluation_games = num_evaluation_games
        self.logger = GameLogger()

    def objective(self, trial):
        """Objective function for Optuna optimization"""
        from bagchal import HeuristicParams  # Import here to avoid circular imports

        # Sample parameters from reasonable ranges
        params = HeuristicParams(
            tiger_capture_bonus=trial.suggest_float(
                'tiger_capture_bonus', 1.0, 10.0),
            tiger_potential_capture_bonus=trial.suggest_float(
                'tiger_potential_capture_bonus', 1.0, 10.0),
            tiger_strategic_position_bonus=trial.suggest_float(
                'tiger_strategic_position_bonus', 0.5, 5.0),
            tiger_center_penalty=trial.suggest_float(
                'tiger_center_penalty', 0.1, 2.0),
            tiger_unblock_bonus=trial.suggest_float(
                'tiger_unblock_bonus', 1.0, 5.0),
            tiger_block_penalty=trial.suggest_float(
                'tiger_block_penalty', 1.0, 5.0),

            goat_trap_bonus=trial.suggest_float('goat_trap_bonus', 2.0, 15.0),
            goat_clustering_bonus=trial.suggest_float(
                'goat_clustering_bonus', 0.5, 3.0),
            goat_strategic_position_bonus=trial.suggest_float(
                'goat_strategic_position_bonus', 0.5, 3.0),
            goat_outer_edge_bonus=trial.suggest_float(
                'goat_outer_edge_bonus', 0.5, 3.0),
            goat_block_capture_bonus=trial.suggest_float(
                'goat_block_capture_bonus', 2.0, 10.0),
            goat_escape_bonus=trial.suggest_float(
                'goat_escape_bonus', 2.0, 10.0),
            goat_sacrifice_penalty=trial.suggest_float(
                'goat_sacrifice_penalty', 5.0, 25.0),
        )

        # Evaluate these parameters
        win_rate, avg_game_length = self.evaluate_parameters(params)

        # Objective: maximize win rate for goats (or balance both players)
        # Prefer shorter games slightly
        return win_rate + 0.1 / max(1, avg_game_length / 50)

    def evaluate_parameters(self, params) -> Tuple[float, float]:
        """Evaluate parameter quality through self-play"""
        from bagchal import GameState  # Import here to avoid circular imports

        GameState.set_heuristic_params(params)

        goat_wins = 0
        total_moves = 0

        for _ in range(self.num_evaluation_games):
            game_result = self.play_single_game()
            if game_result['winner'] == -1:  # Piece.GOAT value
                goat_wins += 1
            total_moves += game_result['num_moves']

        win_rate = goat_wins / self.num_evaluation_games
        avg_game_length = total_moves / self.num_evaluation_games

        return win_rate, avg_game_length

    def play_single_game(self, time_limit: float = 0.5) -> Dict:
        """Play a single game and return results"""
        from bagchal import GameState, Piece  # Import here to avoid circular imports
        from mcts import MCTS

        # Initialize game
        board = [0] * 25  # Piece.EMPTY = 0
        tiger_positions = [0, 4, 20, 24]
        for pos in tiger_positions:
            board[pos] = Piece.TIGER

        game_state = GameState(board, Piece.GOAT, 20, 0)  # Piece.GOAT = -1
        game_state.update_trapped_tiger()
        game_state.init_prioritization()

        moves = []
        states = []

        # Play until game over or max moves
        max_moves = 200
        move_count = 0

        while not game_state.is_game_over() and move_count < max_moves:
            # Use MCTS to select move
            mcts = MCTS(game_state, time_limit=time_limit)
            best_move = mcts.search()

            if best_move is None:
                break

            moves.append(best_move)
            states.append(deepcopy(game_state))
            game_state = game_state.make_move(best_move)
            move_count += 1

        winner = game_state.get_result() or 0  # 0 for draw

        # Log this game
        self.logger.log_game(moves, winner, states)

        return {
            'moves': moves,
            'winner': winner,
            'num_moves': len(moves),
            'final_state': game_state
        }

    def optimize(self, n_trials: int = 100):
        """Run parameter optimization"""
        from bagchal import HeuristicParams  # Import here

        study = optuna.create_study(direction='maximize')
        study.optimize(self.objective, n_trials=n_trials)

        best_params = HeuristicParams(**study.best_params)

        print(f"Best parameters found after {n_trials} trials:")
        print(f"Best value: {study.best_value:.4f}")
        for param_name, param_value in study.best_params.items():
            print(f"  {param_name}: {param_value:.3f}")

        return best_params


class EvolutionaryOptimizer:
    """Alternative: Evolutionary algorithm for parameter optimization"""

    def __init__(self, population_size: int = 20, num_evaluation_games: int = 30):
        self.population_size = population_size
        self.num_evaluation_games = num_evaluation_games
        self.logger = GameLogger()

    def create_initial_population(self):
        """Create initial random population"""
        from bagchal import HeuristicParams

        population = []
        base_params = HeuristicParams()

        for _ in range(self.population_size):
            mutated = base_params.mutate(mutation_rate=0.5)
            population.append(mutated)

        return population

    def evaluate_individual(self, params) -> float:
        """Evaluate a single parameter set"""
        from bagchal import GameState

        GameState.set_heuristic_params(params)

        wins = 0
        total_moves = 0

        for _ in range(self.num_evaluation_games):
            game_result = self.play_game(time_limit=0.5)
            if game_result['winner'] == -1:  # Piece.GOAT
                wins += 1
            total_moves += game_result['num_moves']

        win_rate = wins / self.num_evaluation_games
        avg_moves = total_moves / self.num_evaluation_games

        fitness = win_rate + 0.05 / max(1, avg_moves / 50)
        return fitness

    def play_game(self, time_limit: float = 0.5) -> Dict:
        """Play a single game"""
        from bagchal import GameState, Piece
        from mcts import MCTS

        board = [0] * 25  # Piece.EMPTY
        for pos in [0, 4, 20, 24]:
            board[pos] = 1  # Piece.TIGER

        game_state = GameState(board, -1, 20, 0)  # Piece.GOAT turn
        game_state.update_trapped_tiger()
        game_state.init_prioritization()

        moves = []
        move_count = 0
        max_moves = 150

        while not game_state.is_game_over() and move_count < max_moves:
            mcts = MCTS(game_state, time_limit=time_limit)
            best_move = mcts.search()

            if best_move is None:
                break

            moves.append(best_move)
            game_state = game_state.make_move(best_move)
            move_count += 1

        winner = game_state.get_result() or 0
        return {'moves': moves, 'winner': winner, 'num_moves': len(moves)}

    def evolve(self, generations: int = 20):
        """Run evolutionary optimization"""
        population = self.create_initial_population()
        fitness_history = []

        print(
            f"Starting evolution with {self.population_size} individuals for {generations} generations")

        for generation in range(generations):
            print(f"\nGeneration {generation + 1}/{generations}")

            # Evaluate population
            fitness_scores = []
            for i, individual in enumerate(population):
                fitness = self.evaluate_individual(individual)
                fitness_scores.append(fitness)
                print(f"  Individual {i+1}: fitness = {fitness:.4f}")

            fitness_history.append(max(fitness_scores))

            # Selection and reproduction
            population = self.selection_and_reproduction(
                population, fitness_scores)

            print(f"  Best fitness this generation: {max(fitness_scores):.4f}")

        # Return best individual
        final_fitness = [self.evaluate_individual(ind) for ind in population]
        best_idx = np.argmax(final_fitness)
        best_params = population[best_idx]

        return best_params, fitness_history

    def selection_and_reproduction(self, population, fitness_scores):
        """Tournament selection and reproduction"""
        new_population = []

        # Keep top 20% as elites
        elite_count = max(1, self.population_size // 5)
        elite_indices = np.argsort(fitness_scores)[-elite_count:]
        for idx in elite_indices:
            new_population.append(deepcopy(population[idx]))

        # Fill rest with offspring
        while len(new_population) < self.population_size:
            parent1 = self.tournament_selection(population, fitness_scores)
            parent2 = self.tournament_selection(population, fitness_scores)

            child = self.crossover(parent1, parent2)
            child = child.mutate(mutation_rate=0.15)
            new_population.append(child)

        return new_population

    def tournament_selection(self, population, fitness_scores, tournament_size: int = 3):
        """Select parent using tournament selection"""
        tournament_indices = np.random.choice(
            len(population), tournament_size, replace=False)
        tournament_fitness = [fitness_scores[i] for i in tournament_indices]
        winner_idx = tournament_indices[np.argmax(tournament_fitness)]
        return population[winner_idx]

    def crossover(self, parent1, parent2):
        """Create offspring by combining parameters from two parents"""
        from bagchal import HeuristicParams

        child_dict = {}
        for field_name in asdict(parent1).keys():
            if np.random.random() < 0.5:
                child_dict[field_name] = getattr(parent1, field_name)
            else:
                child_dict[field_name] = getattr(parent2, field_name)

        return HeuristicParams(**child_dict)


class HeuristicAnalyzer:
    """Analyze the effectiveness of different heuristic components"""

    def __init__(self, logger: GameLogger):
        self.logger = logger

    def correlation_analysis(self):
        """Find correlations between heuristic scores and actual outcomes"""
        move_analysis = self.logger.analyze_move_effectiveness()

        print("Move Type Effectiveness Analysis:")
        print("=" * 40)
        for move_type, stats in move_analysis.items():
            print(f"{move_type}:")
            print(f"  Win Rate: {stats['win_rate']:.3f}")
            print(f"  Total Occurrences: {stats['total_games']}")
            print()

        return move_analysis

    def feature_importance_analysis(self, params) -> Dict:
        """Analyze which parameters have the most impact"""
        baseline_fitness = self.evaluate_params(params)
        importance = {}

        for param_name in asdict(params).keys():
            modified_params = deepcopy(params)
            original_value = getattr(modified_params, param_name)

            # Test with 50% increase
            setattr(modified_params, param_name, original_value * 1.5)
            increased_fitness = self.evaluate_params(modified_params)

            # Test with 50% decrease
            setattr(modified_params, param_name, original_value * 0.5)
            decreased_fitness = self.evaluate_params(modified_params)

            # Calculate sensitivity
            sensitivity = abs(increased_fitness - decreased_fitness) / \
                baseline_fitness if baseline_fitness > 0 else 0
            importance[param_name] = sensitivity

        return importance

    def evaluate_params(self, params, num_games: int = 20) -> float:
        """Quick evaluation of parameter set"""
        optimizer = ParameterOptimizer(num_games)

        wins = 0
        for _ in range(num_games):
            result = optimizer.play_single_game(time_limit=0.5)
            if result['winner'] == -1:  # Piece.GOAT
                wins += 1

        return wins / num_games


def compare_parameters(original_params, learned_params, num_games: int = 100):
    """Compare original vs learned parameters"""
    from bagchal import GameState

    print("Parameter Comparison:")
    print("=" * 50)

    # Test original parameters
    GameState.set_heuristic_params(original_params)
    original_optimizer = ParameterOptimizer(num_games)
    original_wins = 0
    for _ in range(num_games):
        result = original_optimizer.play_single_game()
        if result['winner'] == -1:  # Piece.GOAT
            original_wins += 1

    # Test learned parameters
    GameState.set_heuristic_params(learned_params)
    learned_optimizer = ParameterOptimizer(num_games)
    learned_wins = 0
    for _ in range(num_games):
        result = learned_optimizer.play_single_game()
        if result['winner'] == -1:  # Piece.GOAT
            learned_wins += 1

    print(
        f"Original Parameters - Goat Win Rate: {original_wins/num_games:.3f}")
    print(f"Learned Parameters - Goat Win Rate: {learned_wins/num_games:.3f}")
    print(
        f"Improvement: {((learned_wins - original_wins)/num_games)*100:.1f}%")


# Example usage
if __name__ == "__main__":
    print("🚀 Bagchal Learning System")
    print("Run this from another script to optimize your heuristics!")
