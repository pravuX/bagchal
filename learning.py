import numpy as np
import pickle
from dataclasses import asdict
from typing import List, Dict, Tuple
from collections import defaultdict
import optuna
from copy import deepcopy
import time


class GameLogger:
    """Logs games and analyzes move quality (now stores small state features)."""

    def __init__(self):
        self.games: List[Dict] = []
        # indexed by move type -> stats dict
        self.move_stats = defaultdict(
            lambda: {'wins': 0, 'losses': 0, 'draws': 0, 'count': 0})
        # store per-move features if you want to do regressions later
        # each entry: {'move_type': str, 'winner': int, 'features': {...}}
        self.move_feature_records = []

    def log_game(self, moves: List[Tuple], winner: int, states: List, mcts_stats: List[Dict] = None):
        """Log a complete game with moves, winner, and states"""
        game_data = {
            'moves': moves,
            'winner': winner,
            'states': states,
            'mcts_stats': mcts_stats or [],
            'num_moves': len(moves),
            'timestamp': time.time()
        }
        self.games.append(game_data)
        self._update_move_stats(moves, winner, states)

    def _update_move_stats(self, moves, winner, states):
        """Update statistics for each move type and store small state features per move"""
        from bagchal import Piece  # local import to avoid circularity
        for i, (move, state) in enumerate(zip(moves, states)):
            move_key = self._categorize_move(move, state)
            player = state.turn

            # Update counts
            self.move_stats[move_key]['count'] += 1
            if winner == player:
                self.move_stats[move_key]['wins'] += 1
            elif winner == -player:
                self.move_stats[move_key]['losses'] += 1
            else:
                self.move_stats[move_key]['draws'] += 1

            # store small feature vector for analysis (non-identifying)
            features = {
                'trapped_tigers': getattr(state, 'trapped_tiger_count', None),
                'eaten_goats': getattr(state, 'eaten_goat_count', None),
                'goats_left': getattr(state, 'goat_count', None),
                # additional features can be added later
            }
            self.move_feature_records.append({
                'move_index': i,
                'move': move,
                'move_type': move_key,
                'player': player,
                'winner': winner,
                'features': features
            })

    def _categorize_move(self, move, state) -> str:
        """Categorize moves for analysis"""
        from bagchal import Piece  # Import here to avoid circular imports
        src, dst = move
        if src == dst:
            return "goat_placement"
        elif state.board[src] == Piece.TIGER:
            # capture detection: capture moves are jumps (dst not in immediate neighbors)
            if dst not in state.graph[src]:
                return "tiger_capture"
            return "tiger_movement"
        else:
            return "goat_movement"

    def analyze_move_effectiveness(self) -> Dict:
        """Analyze which types of moves are most effective"""
        analysis = {}
        for move_type, stats in self.move_stats.items():
            total = stats['count']
            if total > 0:
                win_rate = stats['wins'] / total
                loss_rate = stats['losses'] / total
                draw_rate = stats['draws'] / total
                analysis[move_type] = {
                    'win_rate': win_rate,
                    'loss_rate': loss_rate,
                    'draw_rate': draw_rate,
                    'total_games': total,
                    'stats': stats
                }
        return analysis

    def save_data(self, filename: str):
        """Save logged games to file"""
        with open(filename, 'wb') as f:
            pickle.dump({
                'games': self.games,
                'move_stats': dict(self.move_stats),
                'move_feature_records': self.move_feature_records
            }, f)

    def load_data(self, filename: str):
        """Load logged games from file"""
        with open(filename, 'rb') as f:
            data = pickle.load(f)
            self.games = data.get('games', [])
            self.move_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'draws': 0, 'count': 0}, data.get('move_stats', {}))
            self.move_feature_records = data.get('move_feature_records', [])


class ParameterOptimizer:
    """Uses Optuna to optimize heuristic parameters, with balanced objective and reduced variance"""

    def __init__(self, num_evaluation_games: int = 30, time_limit: float = 0.3,
                 rollout_epsilon: float = 0.05, rollout_depth: int = 30, seed_averages: int = 2):
        """
        num_evaluation_games: per-seed number of self-play games to average for evaluation
        time_limit: time limit for MCTS during training (seconds)
        rollout_epsilon: epsilon for epsilon-greedy rollouts (smaller -> more deterministic)
        rollout_depth: rollout depth cap used during training
        seed_averages: how many different RNG seeds to average over (reduces variance)
        """
        self.num_evaluation_games = num_evaluation_games
        self.time_limit = time_limit
        self.rollout_epsilon = rollout_epsilon
        self.rollout_depth = rollout_depth
        self.seed_averages = seed_averages
        self.logger = GameLogger()

    def objective(self, trial, optimize_for='goat', fixed_params=None):
        """Objective function for Optuna optimization (balanced objective)."""
        from bagchal import HeuristicParams  # local import
        from dataclasses import asdict

        # Start from fixed params (so we don't overwrite the other side)
        base_params = fixed_params or HeuristicParams()
        params_dict = asdict(base_params)

        if optimize_for == 'goat':
            # only sample goat-related fields
            params_dict.update({
                "goat_trap_bonus": trial.suggest_float('goat_trap_bonus', 2.0, 15.0),
                "goat_clustering_bonus": trial.suggest_float('goat_clustering_bonus', 0.1, 3.0),
                "goat_tiger_clustering_penalty": trial.suggest_float('goat_tiger_clustering_penalty', 0.1, 3.0),
                "goat_strategic_position_bonus": trial.suggest_float('goat_strategic_position_bonus', 0.1, 3.0),
                "goat_outer_edge_bonus": trial.suggest_float('goat_outer_edge_bonus', 0.1, 3.0),
                "goat_block_capture_bonus": trial.suggest_float('goat_block_capture_bonus', 1.0, 10.0),
                "goat_escape_bonus": trial.suggest_float('goat_escape_bonus', 1.0, 10.0),
                "goat_sacrifice_penalty": trial.suggest_float('goat_sacrifice_penalty', 1.0, 30.0),
            })

        elif optimize_for == 'tiger':
            # only sample tiger-related fields
            params_dict.update({
                "tiger_capture_bonus": trial.suggest_float('tiger_capture_bonus', 1.0, 10.0),
                "tiger_potential_capture_bonus": trial.suggest_float('tiger_potential_capture_bonus', 1.0, 10.0),
                "tiger_strategic_position_bonus": trial.suggest_float('tiger_strategic_position_bonus', 0.5, 5.0),
                "tiger_center_penalty": trial.suggest_float('tiger_center_penalty', 0.1, 2.0),
                "tiger_unblock_bonus": trial.suggest_float('tiger_unblock_bonus', 1.0, 5.0),
                "tiger_block_penalty": trial.suggest_float('tiger_block_penalty', 1.0, 5.0),
            })

        # build params object
        params = HeuristicParams(**params_dict)

        # --- evaluation ---
        all_win_rates = []
        all_avg_lengths = []
        for seed_idx in range(self.seed_averages):
            seed = (trial.number + 1) * 1009 + seed_idx * 7919
            np.random.seed(seed)
            win_rate, avg_length = self.evaluate_parameters(params)
            all_win_rates.append(win_rate)
            all_avg_lengths.append(avg_length)

        avg_win_rate = float(np.mean(all_win_rates))
        avg_game_length = float(np.mean(all_avg_lengths))

        # Balanced objective
        balance_score = 1.0 - abs(avg_win_rate - 0.5)
        length_bonus = 0.05 * (1.0 - min(avg_game_length / 200.0, 1.0))
        objective_value = balance_score + length_bonus

        # debug info
        trial.set_user_attr('avg_win_rate', avg_win_rate)
        trial.set_user_attr('avg_game_length', avg_game_length)

        return objective_value

    def evaluate_parameters(self, params) -> Tuple[float, float]:
        """Evaluate a parameter set via self-play, returns (goat_win_rate, avg_game_length)."""
        from bagchal import GameState  # local import
        from bagchal import Piece

        # set params globally for GameState
        GameState.set_heuristic_params(params)

        goat_wins = 0
        total_moves = 0

        for _ in range(self.num_evaluation_games):
            game_result = self.play_single_game(time_limit=self.time_limit,
                                                rollout_epsilon=self.rollout_epsilon,
                                                rollout_depth=self.rollout_depth)
            if game_result['winner'] == Piece.GOAT:
                goat_wins += 1
            total_moves += game_result['num_moves']

        win_rate = goat_wins / max(1, self.num_evaluation_games)
        avg_game_length = total_moves / max(1, self.num_evaluation_games)
        return win_rate, avg_game_length

    def play_single_game(self, time_limit: float = None,
                         rollout_epsilon: float = None, rollout_depth: int = None) -> Dict:
        """Play a single game under current GameState. Returns summary dict."""
        from bagchal import GameState, Piece  # local import
        from mcts import MCTS

        # use defaults if not provided
        time_limit = self.time_limit if time_limit is None else time_limit
        rollout_epsilon = self.rollout_epsilon if rollout_epsilon is None else rollout_epsilon
        rollout_depth = self.rollout_depth if rollout_depth is None else rollout_depth

        # Initialize game
        board = [0] * 25  # Piece.EMPTY = 0
        tiger_positions = [0, 4, 20, 24]
        for pos in tiger_positions:
            board[pos] = Piece.TIGER

        game_state = GameState(board, Piece.GOAT, 20, 0)
        game_state.update_trapped_tiger()
        game_state.init_prioritization()

        moves = []
        states = []

        # Play until game over or max moves
        max_moves = 200
        move_count = 0

        while not game_state.is_game_over() and move_count < max_moves:
            # Use MCTS to select move; pass rollout params to MCTS for training stability
            mcts = MCTS(game_state, time_limit=time_limit, rollout_epsilon=rollout_epsilon, rollout_depth=rollout_depth)
            best_move = mcts.search()

            if best_move is None:
                break

            moves.append(best_move)
            states.append(deepcopy(game_state))  # capture pre-move state for logger
            game_state = game_state.make_move(best_move)
            move_count += 1

        winner = game_state.get_result() or 0  # 0 for draw

        # Log this game to global logger
        self.logger.log_game(moves, winner, states)

        return {
            'moves': moves,
            'winner': winner,
            'num_moves': len(moves),
            'final_state': game_state
        }

    def optimize(self, n_trials: int = 100, n_jobs: int = 1):
        """Run Optuna optimization."""
        study = optuna.create_study(direction='maximize')
        study.optimize(self.objective, n_trials=n_trials, n_jobs=n_jobs)

        # extract best params and create HeuristicParams
        from bagchal import HeuristicParams
        best_params = HeuristicParams(**study.best_params)

        print(f"Best parameters found after {n_trials} trials:")
        print(f"  Best objective value: {study.best_value:.4f}")
        for param_name, param_value in study.best_params.items():
            print(f"  {param_name}: {param_value:.4f}")

        return best_params, study

    def validate_params(self, params, num_games: int = 200, time_limit: float = 1.5, rollout_epsilon: float = 0.05, rollout_depth: int = 40):
        """Validate parameters at a heavier time budget; returns goat win rate and avg length."""
        # re-use evaluate_parameters but with different control
        old_num = self.num_evaluation_games
        old_time = self.time_limit
        old_eps = self.rollout_epsilon
        old_depth = self.rollout_depth

        self.num_evaluation_games = num_games
        self.time_limit = time_limit
        self.rollout_epsilon = rollout_epsilon
        self.rollout_depth = rollout_depth

        win_rate, avg_len = self.evaluate_parameters(params)

        # restore
        self.num_evaluation_games = old_num
        self.time_limit = old_time
        self.rollout_epsilon = old_eps
        self.rollout_depth = old_depth

        print(f"Validation: goat win rate = {win_rate:.3f}, avg game length = {avg_len:.1f}")
        return win_rate, avg_len


class HeuristicAnalyzer:
    """Analyze the effectiveness of different heuristic components"""

    def __init__(self, logger: GameLogger):
        self.logger = logger

    def correlation_analysis(self):
        move_analysis = self.logger.analyze_move_effectiveness()
        print("Move Type Effectiveness Analysis:")
        print("=" * 40)
        for move_type, stats in move_analysis.items():
            print(f"{move_type}:")
            print(f"  Win Rate: {stats['win_rate']:.3f}")
            print(f"  Loss Rate: {stats['loss_rate']:.3f}")
            print(f"  Draw Rate: {stats['draw_rate']:.3f}")
            print(f"  Total Occurrences: {stats['total_games']}")
            print()
        return move_analysis

    def feature_importance_analysis(self, params) -> Dict:
        """Analyze which parameters have the most impact (simple sensitivity test)."""
        baseline_fitness = self.evaluate_params(params)
        importance = {}

        for param_name in asdict(params).keys():
            modified_params = deepcopy(params)
            original_value = getattr(modified_params, param_name)

            # Test with 50% increase
            setattr(modified_params, param_name, max(0.01, original_value * 1.5))
            increased_fitness = self.evaluate_params(modified_params)

            # Test with 50% decrease
            setattr(modified_params, param_name, max(0.01, original_value * 0.5))
            decreased_fitness = self.evaluate_params(modified_params)

            sensitivity = abs(increased_fitness - decreased_fitness) / baseline_fitness if baseline_fitness > 0 else 0
            importance[param_name] = sensitivity

        return importance

    def evaluate_params(self, params, num_games: int = 20) -> float:
        """Quick evaluation used by analyzer."""
        optimizer = ParameterOptimizer(num_games)
        wins = 0
        for _ in range(num_games):
            result = optimizer.play_single_game(time_limit=0.3)
            if result['winner'] == -1:  # Piece.GOAT
                wins += 1
        return wins / num_games


def compare_parameters(original_params, learned_params, num_games: int = 100, time_limit: float = 1.5):
    """Compare original vs learned parameters (heavy validation)."""
    from bagchal import GameState

    print("Parameter Comparison:")
    print("=" * 50)

    # Test original parameters
    GameState.set_heuristic_params(original_params)
    original_optimizer = ParameterOptimizer(num_evaluation_games=num_games, time_limit=time_limit)
    original_wins = 0
    for _ in range(num_games):
        result = original_optimizer.play_single_game()
        if result['winner'] == -1:
            original_wins += 1

    # Test learned parameters
    GameState.set_heuristic_params(learned_params)
    learned_optimizer = ParameterOptimizer(num_evaluation_games=num_games, time_limit=time_limit)
    learned_wins = 0
    for _ in range(num_games):
        result = learned_optimizer.play_single_game()
        if result['winner'] == -1:
            learned_wins += 1

    print(f"Original Parameters - Goat Win Rate: {original_wins/num_games:.3f}")
    print(f"Learned Parameters - Goat Win Rate: {learned_wins/num_games:.3f}")
    print(f"Improvement: {((learned_wins - original_wins)/num_games)*100:.1f}%")
