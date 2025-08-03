from collections import defaultdict
import random
import time
import numpy as np
from bagchal import Piece, GameState


class Node:
    def __init__(self, state, parent=None, move=None):
        self.state: GameState = state
        self.parent = parent
        self.move = move

        self.children = []
        self.visit_count = 0
        self.total_value = 0.0

        self.prioritized_moves_with_scores = self.state.prioritize_moves()
        self.prioritized_moves = [move for move,
                                  _ in self.prioritized_moves_with_scores]

        self.player = self.state.turn

    def is_fully_expanded(self):
        return len(self.prioritized_moves) == 0

    def expand(self):
        # the expansion strategy is based on the priority of each move
        move = self.prioritized_moves.pop()
        next_state = self.state.make_move(move)
        child_node = Node(next_state, parent=self, move=move)
        self.children.append(child_node)
        return child_node

    def is_terminal(self):
        return self.state.is_game_over()

    def best_child(self, c_param=1):

        # Progressive Bias
        # if self.visit_count < 50:
        #   return max(self.children, key=priority_score)

        def uct(child):
            if child.visit_count == 0:  # ensures each child is explored at least once
                return float('inf')
            exploitation = child.total_value / child.visit_count  # Q
            exploration = c_param * \
                np.sqrt(np.log(self.visit_count) / child.visit_count)
            return exploitation + exploration

        return max(self.children, key=uct)


class MCTS:

    def __init__(self, initial_state, max_simulations=1000, time_limit=None):
        self.max_simulations = max_simulations
        self.root = Node(initial_state)
        print(self.root.prioritized_moves)
        self.time_limit = time_limit
        self.simulations_run = 0

        self.goat_wins = 0
        self.tiger_wins = 0

    def rollout_policy(self, state, state_key):
        if state.turn == Piece.GOAT:
            if state_key in GameState.transposition_table_with_scores:

                best_move, priority_score = GameState.transposition_table_with_scores[
                    state_key][-1]
                return best_move

            best_move = state.prioritize_moves(return_best_move=True)
            return best_move

        else:
            possible_moves = state.get_legal_moves()
            return random.choice(possible_moves)

    def search(self):
        # print("Initial Tree")
        # self.visualize_tree()
        # print()

        def search_helper():
            expanded_node = self.tree_policy(self.root)
            result = self.rollout(expanded_node)
            self.backpropagate(expanded_node, result)
            self.simulations_run += 1
            # print("Simulation", self.simulations_run)
            # print(GameState.piece[result], "won during rollout.")
            # self.visualize_tree()
            # print()
            if result == Piece.GOAT:
                self.goat_wins += 1
            elif result == Piece.TIGER:
                self.tiger_wins += 1

        if self.time_limit is not None:
            end_time = time.time() + self.time_limit
            while time.time() < end_time:
                search_helper()
            return self.get_best_move()

        while self.simulations_run < self.max_simulations:
            search_helper()

        return self.get_best_move()

    def tree_policy(self, node):
        while not node.is_terminal():
            if not node.is_fully_expanded():
                return node.expand()
            else:
                node = node.best_child()
        return node

    def rollout(self, node):
        state_hash = defaultdict(int)
        state: GameState = node.state

        while not state.is_game_over():
            state_key_l = state.key()
            state_hash[state_key_l] += 1

            if state_hash[state_key_l] > 3:
                return 0

            move = self.rollout_policy(state, state_key_l)
            state = state.make_move(move)

        result = state.get_result()
        return result

    def backpropagate(self, node, result):
        while node is not None:
            node.visit_count += 1
            node.total_value += -node.player * result
            node = node.parent

    def get_best_move(self):
        """Select best move based on visit count (most robust)"""
        if not self.root.children:
            return None

        most_visited_child = max(
            self.root.children, key=lambda c: c.visit_count)
        return most_visited_child.move

    def get_move_statistics(self):
        """Get statistics about the search for analysis"""
        if not self.root.children:
            return {}

        stats = {}
        for child in self.root.children:
            move = child.move
            stats[move] = {
                'visits': child.visit_count,
                'q-value': child.total_value / child.visit_count if child.visit_count > 0 else 0,
            }

        return stats

    def visualize_tree(self, node=None, prefix="", is_last=True, max_depth=3, current_depth=0):
        """Visualize search tree with enhanced information"""
        if node is None:
            node = self.root
            print("MCTS Search Tree")
            print("================")

        if current_depth > max_depth:
            return

        connector = "└── " if is_last else "├── "
        move_str = f"Move: {node.move}" if node.move else "Root"

        # Enhanced node information
        avg_value = node.total_value / node.visit_count if node.visit_count > 0 else 0
        print(f"{prefix}{connector}{move_str} | "
              f"N: {node.visit_count}, "
              f"V: {node.total_value}, "
              f"Q: {avg_value:.3f}, "
              f"Turn: {node.state.piece[node.player]}")

        prefix += "    " if is_last else "│   "

        child_count = len(node.children)
        sorted_children = sorted(
            node.children, key=lambda c: c.visit_count, reverse=True)

        # Show top 5 children only
        # for i, child in enumerate(sorted_children[:5]):
        for i, child in enumerate(sorted_children):
            # is_last_child = (i == min(4, child_count - 1))
            is_last_child = (i == child_count - 1)
            self.visualize_tree(child, prefix, is_last_child,
                                max_depth, current_depth + 1)
