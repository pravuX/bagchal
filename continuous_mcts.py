from collections import defaultdict
import time
import numpy as np
from bagchal import GameState, Piece


class Node:
    def __init__(self, game_state: GameState, parent=None, move=None):
        self.game_state: GameState = game_state
        self.parent: Node = parent
        self.move = move  # incoming move

        self.children = []
        self.visit_count = 0
        self.total_value = 0.0

        self.player_to_move = self.game_state.turn

        self.unexpanded_moves = list(self.game_state.prioritized_moves)

    def is_fully_expanded(self):
        if self.is_terminal():
            return True
        # has no unvisited child
        return len(self.unexpanded_moves) == 0

    def is_terminal(self):
        return self.game_state.is_game_over()

    def expand(self):
        move = self.unexpanded_moves.pop()
        next_state = self.game_state.make_move(move)
        child = Node(next_state, parent=self, move=move)
        self.children.append(child)

        return child

    def best_child(self, history=None, c_param=1.41):

        def uct(child: Node):
            if history and child.game_state.key() in history:
                # neutral uct score to discourage
                # repetition of states in the same path
                # return 0
                # extreme negative value to strictly choose moves
                # that don't lead to state repetitions
                return float('-inf')

            if child.visit_count == 0:
                return float('inf')

            # exploitation
            # from parent's perspective
            exploitation = -1 * (child.total_value / child.visit_count)

            exploration = c_param * \
                np.sqrt(np.log(self.visit_count)/child.visit_count)

            return exploitation + exploration

        return max(self.children, key=uct)


class MCTS:
    previous_evaluations = {}  # state_key -> evaluation

    def __init__(self):
        self.rollout_epsilon = 0.05
        self.rollout_depth = 30

    def search(self, initial_state: GameState, max_simulations=1000, time_limit=None):
        self.root = Node(initial_state)
        self.max_simulations = max_simulations
        self.time_limit = time_limit
        self.simulations_run = 0
        self.goat_wins = 0
        self.tiger_wins = 0
        self.draws = 0

        def search_helper():
            # performs one iteration of MCTS
            expanded_node = self.tree_policy(self.root)
            result = self.rollout(expanded_node)
            self.backpropagate(expanded_node, result)
            self.simulations_run += 1
            if result == 0:
                self.draws += 1
            elif result == Piece.GOAT:
                self.goat_wins += 1
            else:
                self.tiger_wins += 1

        if self.time_limit is not None:
            end_time = time.time() + self.time_limit
            while time.time() < end_time:
                search_helper()
            return self.get_best_move()

        # otherwise fall back to the simulation count limit
        while self.simulations_run < self.max_simulations:
            search_helper()
        return self.get_best_move()

    def get_best_move(self):
        max_child: Node = self.root.best_child(c_param=0)
        most_visited_child = max(
            self.root.children, key=lambda c: c.visit_count)
        return most_visited_child.move

    def tree_policy(self, node: Node):
        history = {node.game_state.key()}
        while not node.is_terminal():
            if not node.is_fully_expanded():
                return node.expand()
            node = node.best_child(history)
            history = history | {node.game_state.key()}
        return node

    def rollout_policy(self, game_state: GameState):
        # semi-random rollout policy
        moves = game_state.prioritized_moves
        if np.random.random() < self.rollout_epsilon:
            return moves[np.random.randint(len(moves))]
        best_move = moves[-1]
        return best_move

    def rollout(self, node: Node):
        game_state = node.game_state

        # state_hash_counts = defaultdict(int)
        # repetition_limit = 3

        depth = 0

        while not game_state.is_game_over():
            # state_key = game_state.key()
            #
            # state_hash_counts[state_key] += 1
            # if state_hash_counts[state_key] > repetition_limit:
            #     # draw
            #     return 0

            if depth >= self.rollout_depth:
                heuristic_score = self.evaluate_state(game_state)

                norm_result = np.tanh(0.4 * heuristic_score)

                return norm_result

            move = self.rollout_policy(game_state)
            game_state = game_state.make_move(move)

            depth += 1

        return game_state.get_result()

    def backpropagate(self, node: Node, result):
        while node is not None:
            node.visit_count += 1
            node.total_value += node.player_to_move * result
            node = node.parent

    def visualize_tree(self, node=None, prefix="", is_last=True, max_depth=3, current_depth=0):
        if node is None:
            node: Node = self.root
            print("MCTS Search Tree")
            print("================")

        if current_depth > max_depth:
            return

        connector = "└── " if is_last else "├── "
        move_str = f"Move: {node.move}" if node.move != None else "Root"
        wins = node.total_value
        avg_value = wins / node.visit_count if node.visit_count > 0 else 0
        print(
            f"{prefix}{connector}{move_str} | Q: {wins:.3f}, N: {node.visit_count}, Q/N: {avg_value:.3f}, Turn: {GameState.piece[node.player_to_move]}")

        prefix += "    " if is_last else "│   "
        children = sorted(
            node.children, key=lambda c: c.visit_count, reverse=True)
        for i, child in enumerate(children):
            is_last_child = (i == len(children) - 1)
            self.visualize_tree(child, prefix, is_last_child,
                                max_depth, current_depth + 1)

    def evaluate_state(self, state: GameState):
        """
        Positive -> TIGER advantage, Negative -> GOAT advantage.
        """

        state_key = state.key()

        if state_key in self.previous_evaluations:
            return self.previous_evaluations[state_key]

        is_placement = state.goat_count > 0

        eat_max = 4  # before win
        potential_capture_max = 11
        inaccessible_max = 10

        trap_max = 3  # before win
        goat_presence_max = 20
        tiger_mobility_max = 25

        w_eat = GameState.heuristic_params.w_eat
        w_potcap = GameState.heuristic_params.w_potcap
        w_mobility = 0 if is_placement else GameState.heuristic_params.w_mobility

        w_trap = GameState.heuristic_params.w_trap
        w_presence = GameState.heuristic_params.w_presence
        w_inacc = GameState.heuristic_params.w_inacc

        if state.is_game_over():
            result = state.get_result()
            return 1000 if result == Piece.TIGER else -1000

        trapped = state.trapped_tiger_count
        eaten = state.eaten_goat_count
        goat_left = state.goat_count
        goats_on_board = 20 - (eaten + goat_left)

        goat_positions = [i for i, p in enumerate(
            state.board) if p == Piece.GOAT]

        eaten_score = eaten / eat_max
        tiger_legal_moves = state.get_legal_moves(turn=Piece.TIGER)
        potential_captures = sum(
            1 for src, dst in tiger_legal_moves if dst not in GameState.graph[src])
        tiger_normal_moves = len(tiger_legal_moves) - potential_captures
        potential_capture_score = potential_captures / potential_capture_max
        tiger_mobility_score = tiger_normal_moves / tiger_mobility_max

        trap_score = trapped / trap_max
        goat_presence_score = goats_on_board / goat_presence_max
        inaccessible = GameState.find_inaccessible_positions(state)
        inaccessibility_score = len(inaccessible) / inaccessible_max

        tiger_score = (eaten_score * w_eat +
                       potential_capture_score * w_potcap +
                       tiger_mobility_score * w_mobility)

        goat_score = (trap_score * w_trap +
                      goat_presence_score * w_presence +
                      inaccessibility_score * w_inacc)

        final_evaluation = tiger_score - goat_score
        self.previous_evaluations[state_key] = final_evaluation
        return final_evaluation
