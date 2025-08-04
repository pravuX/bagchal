from collections import defaultdict
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
        self.player = self.state.turn

        self.prioritized_moves = self.state.prioritized_moves
        self.prioritized_scores = self.state.prioritized_scores

    def is_fully_expanded(self):
        return len(self.prioritized_moves) == 0

    def expand(self):
        # the expansion policy is based on the priority of each move
        move = self.prioritized_moves.pop()
        next_state = self.state.make_move(move)
        child_node = Node(next_state, parent=self, move=move)
        self.children.append(child_node)
        return child_node

    def is_terminal(self):
        return self.state.is_game_over()

    def best_child(self, c_param=1):
        # this is only called on a node that is fully expanded
        # i.e all children that are visited at least once

        def uct(child_with_index):

            child_index, child = child_with_index
            exploitation = child.total_value / child.visit_count  # Q
            exploration = c_param * \
                np.sqrt(np.log(self.visit_count) / child.visit_count)
            # the child list and priority score list are in opposite order
            priority_index = len(self.prioritized_scores) - child_index-1

            # slower decay rate for goats
            # decay_rate = child.visit_count if self.player == Piece.TIGER else np.sqrt(
            #     child.visit_count)
            decay_rate = np.sqrt(child.visit_count)

            heuristic_bias = 10 * \
                self.prioritized_scores[priority_index] / decay_rate

            # heuristic_bias = self.prioritized_scores[priority_index] * max(
            #     0, 1-(child.visit_count/1000)**2)

            # if self.state.goat_count > 0:  # placement_phase
            #     return priority_index

            return exploitation + exploration + heuristic_bias

        if not self.children:
            # got an error one time saying that children was empty?
            print(self.state)
        _, best_uct_child = max(enumerate(self.children), key=uct)
        return best_uct_child


class MCTS:

    def __init__(self, initial_state, max_simulations=1000, time_limit=None):
        self.max_simulations = max_simulations
        self.root = Node(initial_state)
        print(self.root.prioritized_moves)
        print(self.root.prioritized_scores)
        self.time_limit = time_limit
        self.simulations_run = 0

        self.goat_wins = 0
        self.tiger_wins = 0

    def rollout_policy(self, state):

        sampled_move_idx = np.random.choice(
            len(state.prioritized_moves), p=state.prior_prob_dist)
        return state.prioritized_moves[sampled_move_idx]

    def search(self):

        def search_helper():
            expanded_node = self.tree_policy(self.root)
            result = self.rollout(expanded_node)
            self.backpropagate(expanded_node, result)
            self.simulations_run += 1
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
            state_key = state.key()
            state_hash[state_key] += 1

            if state_hash[state_key] > 3:
                return 0

            move = self.rollout_policy(state)
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
