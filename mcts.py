import random
import time
import numpy as np
from alphabeta import MinimaxAgent
from bagchal import GameState, Piece


class Node:
    def __init__(self, state, parent=None, move=None):
        self.state = state  # the board state (instance of GameState)
        self.parent = parent  # the parent node
        self.move = move  # the move that led to this state from the parent

        self.children = []
        self.visit_count = 0  # N(vi)
        self.total_value = 0.0  # Q(vi)

        self.untried_moves = self.state.get_legal_moves()
        self.player = self.state.turn

    def is_fully_expanded(self):
        return len(self.untried_moves) == 0

    def is_terminal(self):
        return self.state.is_game_over()

    def expand(self):
        move = self.untried_moves.pop()
        next_state = self.state.make_move_mcts(move)
        child_node = Node(next_state, parent=self, move=move)
        self.children.append(child_node)
        return child_node

    def best_child(self, c_param=1.41):
        # Upper Confidence Bound (UCT)
        def uct(child):
            if child.visit_count == 0:  # ensures each child is explored at least once
                return float('inf')
            exploitation = child.total_value / child.visit_count
            exploration = c_param * \
                np.sqrt(np.log(self.visit_count) / child.visit_count)
            return exploitation + exploration

        return max(self.children, key=uct)


class MCTS:
    def __init__(self, initial_state, max_simulations=1000, time_limit=None):
        self.max_simulations = max_simulations
        self.root = Node(initial_state)
        self.time_limit = time_limit
        self.minimax_agent = MinimaxAgent(depth=3)

    def rollout_policy(self, possible_moves, state):
        # pick random moves
        return random.choice(possible_moves)
        # if random.random() < 0.5:
        #     return random.choice(possible_moves)
        move = self.minimax_agent.get_best_move(state)
        print(move)
        print(state)
        print(self.count_simulations, state.get_result())
        print(state.board)
        return move

    def search(self):
        def search_helper():
            expanded_node = self.tree_policy(self.root)
            result = self.rollout(expanded_node)
            self.backpropagate(expanded_node, result)

        if self.time_limit != None:
            end_time = time.time() + self.time_limit
            while time.time() < end_time:
                search_helper()
            return self.get_best_move()

        num_simulations = 0
        while num_simulations < self.max_simulations:
            search_helper()
            num_simulations += 1

        return self.get_best_move()

    def tree_policy(self, node):
        # selection + expansion
        while not node.is_terminal():
            if not node.is_fully_expanded():
                return node.expand()
            else:
                node = node.best_child()
        return node

    def rollout(self, node):
        state = node.state
        total_moves = 0
        while not state.is_game_over():  # basically the terminal node
            possible_moves = state.get_legal_moves()
            move = self.rollout_policy(possible_moves, state)
            total_moves += 1
            if total_moves >= 1000:
                return 0  # dirty draw
            state = state.make_move_mcts(move)  # Advance the state
        return state.get_result()  # +1 win for X, -1 win for O, 0 draw

    def backpropagate(self, node, result):
        while node is not None:
            node.visit_count += 1
            # we flip the result so that, the move that lead
            # to this node is wrt to the parent
            # win means bad, loss means good, because the turn
            # of this node is flipped when making the move from
            # the parent
            node.total_value += node.player * -result
            node = node.parent

    def get_best_move(self):
        most_visited_child = max(
            self.root.children, key=lambda c: c.visit_count)
        return most_visited_child.move

    def visualize_tree(self, node=None, prefix="", is_last=True):
        if node is None:
            node = self.root
            print(".")  # root node of the tree

        connector = "└── " if is_last else "├── "
        print(
            f"{prefix}{connector}(Move: {node.move}, Q: {node.total_value}, N: {node.visit_count}, Turn: {node.state.piece[node.player]})")

        prefix += "    " if is_last else "│   "

        child_count = len(node.children)
        for i, child in enumerate(node.children):
            is_last_child = (i == child_count - 1)
            self.visualize_tree(child, prefix, is_last_child)
