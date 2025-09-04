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
        """
        results = { -1: count, 1: count, 0: count}
        """
        self.results = defaultdict(int)

        self.player_to_move = self.game_state.turn

        self.unexpanded_moves = self.game_state.get_legal_moves()

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

    def best_child(self, c_param=0.7):

        def uct(child: Node):
            if child.visit_count == 0:
                return float('inf')

            # exploitation
            # from parent's perspective
            wins = child.results[self.player_to_move]
            losses = child.results[-self.player_to_move]
            exploitation = (wins - losses) / \
                child.visit_count

            exploration = c_param * \
                np.sqrt(np.log(self.visit_count)/child.visit_count)

            return exploitation + exploration

        return max(self.children, key=uct)


class MCTS:
    def __init__(self, initial_state: GameState, max_simulations=1000, time_limit=None):
        self.root = Node(initial_state)
        self.max_simulations = max_simulations
        self.time_limit = time_limit
        self.simulations_run = 0
        self.goat_wins = 0
        self.tiger_wins = 0
        self.draws = 0

    def search(self):

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
        while not node.is_terminal():
            if not node.is_fully_expanded():
                return node.expand()
            node = node.best_child()
        return node

    def rollout_policy(self, game_state: GameState):
        moves = game_state.get_legal_moves()
        return moves[np.random.randint(len(moves))]

    def rollout(self, node: Node):
        game_state = node.game_state

        while not game_state.is_game_over():
            move = self.rollout_policy(game_state)
            game_state = game_state.make_move(move)

        return game_state.get_result()

    def backpropagate(self, node: Node, result):
        while node is not None:
            node.visit_count += 1
            node.results[result] += 1
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
        wins = node.results[node.player_to_move]
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
