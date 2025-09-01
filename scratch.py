class EvolutionaryOptimizer:
    """Evolutionary algorithm with arithmetic crossover."""

    def __init__(self, population_size: int = 20, num_evaluation_games: int = 20):
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
        """Evaluate a single parameter set (fitness)."""
        from bagchal import GameState

        GameState.set_heuristic_params(params)
        wins = 0
        total_moves = 0
        for _ in range(self.num_evaluation_games):
            game_result = self.play_game(time_limit=0.3)
            if game_result['winner'] == -1:  # Piece.GOAT
                wins += 1
            total_moves += game_result['num_moves']

        win_rate = wins / max(1, self.num_evaluation_games)
        avg_moves = total_moves / max(1, self.num_evaluation_games)
        fitness = win_rate + 0.05 * (1.0 - min(avg_moves / 200.0, 1.0))
        return fitness

    def play_game(self, time_limit: float = 0.3) -> Dict:
        """Play a single game (used for EA evaluation)."""
        from bagchal import GameState, Piece
        from mcts import MCTS

        board = [0] * 25
        for pos in [0, 4, 20, 24]:
            board[pos] = Piece.TIGER

        game_state = GameState(board, Piece.GOAT, 20, 0)
        game_state.update_trapped_tiger()
        game_state.init_prioritization()

        moves = []
        move_count = 0
        max_moves = 150

        while not game_state.is_game_over() and move_count < max_moves:
            mcts = MCTS(game_state, time_limit=time_limit,
                        rollout_epsilon=0.05)
            best_move = mcts.search()
            if best_move is None:
                break
            moves.append(best_move)
            game_state = game_state.make_move(best_move)
            move_count += 1

        winner = game_state.get_result() or 0
        return {'moves': moves, 'winner': winner, 'num_moves': len(moves)}

    def evolve(self, generations: int = 20):
        """Run evolutionary optimization."""
        population = self.create_initial_population()
        fitness_history = []

        print(
            f"Starting evolution with {self.population_size} individuals for {generations} generations")

        for generation in range(generations):
            print(f"\nGeneration {generation + 1}/{generations}")
            fitness_scores = []
            for i, individual in enumerate(population):
                fitness = self.evaluate_individual(individual)
                fitness_scores.append(fitness)
                print(f"  Individual {i+1}: fitness = {fitness:.4f}")

            fitness_history.append(max(fitness_scores))
            # selection & reproduction
            population = self.selection_and_reproduction(
                population, fitness_scores)
            print(f"  Best fitness this generation: {max(fitness_scores):.4f}")

        final_fitness = [self.evaluate_individual(ind) for ind in population]
        best_idx = int(np.argmax(final_fitness))
        best_params = population[best_idx]
        return best_params, fitness_history

    def selection_and_reproduction(self, population, fitness_scores):
        """Tournament selection and reproduction"""
        new_population = []
        elite_count = max(1, self.population_size // 5)
        elite_indices = np.argsort(fitness_scores)[-elite_count:]
        for idx in elite_indices:
            new_population.append(deepcopy(population[idx]))

        while len(new_population) < self.population_size:
            parent1 = self.tournament_selection(population, fitness_scores)
            parent2 = self.tournament_selection(population, fitness_scores)
            child = self.crossover(parent1, parent2)
            child = child.mutate(mutation_rate=0.15)
            new_population.append(child)

        return new_population

    def tournament_selection(self, population, fitness_scores, tournament_size: int = 3):
        tournament_indices = np.random.choice(
            len(population), tournament_size, replace=False)
        tournament_fitness = [fitness_scores[i] for i in tournament_indices]
        winner_idx = tournament_indices[int(np.argmax(tournament_fitness))]
        return population[winner_idx]

    def crossover(self, parent1, parent2):
        """Arithmetic crossover: blend values + small noise."""
        from bagchal import HeuristicParams
        child_dict = {}
        for field_name, value in asdict(parent1).items():
            v1 = getattr(parent1, field_name)
            v2 = getattr(parent2, field_name)
            # arithmetic crossover + tiny gaussian noise
            child_val = 0.5 * (v1 + v2) + np.random.normal(0,
                                                           abs(0.05 * (v1 + v2) / 2.0) + 1e-6)
            # clamp to positive
            child_dict[field_name] = max(0.01, float(child_val))
        return HeuristicParams(**child_dict)
