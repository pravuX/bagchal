from collections import defaultdict
import random
import time
import numpy as np
from alphabeta import MinimaxAgent
from bagchal import Piece


class Node:
    def __init__(self, state, parent=None, move=None):
        self.state = state
        self.parent = parent
        self.move = move
        self.children = []
        self.visit_count = 0
        self.total_value = 0.0

        # Progressive widening parameters
        self.alpha = 0.5  # Controls expansion rate
        self.all_moves = self.state.get_legal_moves()
        self.prioritized_moves = self._prioritize_moves()
        self.expanded_moves = 0

        # RAVE parameters
        self.rave_visits = defaultdict(int)  # RAVE visit counts for each move
        self.rave_values = defaultdict(float)  # RAVE values for each move
        self.beta = 0.5  # RAVE mixing parameter

        self.player = self.state.turn

    def _prioritize_moves(self):
        """Sort moves by strategic value for progressive expansion"""
        moves = self.all_moves.copy()

        if self.state.turn == Piece.TIGER:
            # Prioritize captures, then center moves
            def tiger_priority(move):
                src, dst = move
                if src == dst:  # Not applicable for tigers
                    return 0

                # Capture moves get highest priority
                if dst not in self.state.graph[src]:
                    return 100

                # Center positions get medium priority
                center_positions = {6, 8, 12, 16, 18}
                if dst in center_positions:
                    return 50

                return 10

            moves.sort(key=tiger_priority, reverse=True)

        else:  # Goat moves
            def goat_priority(move):
                # Prioritize safe positions more than strategic positions
                src, dst = move

                tiger_positions = [i for i, p in enumerate(
                    self.state.board) if p == Piece.TIGER]
                is_safe = True
                for tiger_pos in tiger_positions:
                    capture_pos = dst - (tiger_pos - dst)
                    if dst in self.state.graph[tiger_pos] \
                            and capture_pos in self.state.graph[dst] \
                            and self.state.board[capture_pos] == Piece.EMPTY:
                        is_safe = False
                        break
                # is_safe = all(
                #     dst not in self.state.graph[tiger] for tiger in tiger_positions)
                if is_safe:
                    return 50
                return 10

                # strategic_positions = {2, 10, 14, 22}
                # center_positions = {6, 8, 12, 16, 18}
                # if self.state.goat_count > 0:  # Placement phase
                #     # Favour strategic_positions in palcement phase
                #     if src in strategic_positions:
                #         return 50
                #     return 10
                #
                # elif src in center_positions or src in strategic_positions:
                #     # Good positions for Movement phase
                #     return 25

            moves.sort(key=goat_priority, reverse=True)

        return moves

    def should_expand(self):
        """Determine if we should expand more children based on visit count"""
        max_children = len(self.all_moves)
        current_limit = int(self.alpha * (self.visit_count ** 0.5)) + 1
        return self.expanded_moves < min(current_limit, max_children)

    def is_fully_expanded(self):
        """Check if all allowed moves have been expanded"""
        return not self.should_expand() or self.expanded_moves >= len(self.all_moves)

    def expand(self):
        """Expand next prioritized move"""
        if self.expanded_moves >= len(self.prioritized_moves):
            return None

        move = self.prioritized_moves[self.expanded_moves]
        next_state = self.state.make_move(move)
        child_node = Node(next_state, parent=self, move=move)
        self.children.append(child_node)
        self.expanded_moves += 1
        return child_node

    def is_terminal(self):
        return self.state.is_game_over()

    def best_child(self, c_param=1.4):
        """Enhanced UCT with RAVE values"""
        def rave_uct(child):
            if child.visit_count == 0:
                return float('inf')

            # Standard UCT value
            exploitation = child.total_value / child.visit_count
            exploration = c_param * \
                np.sqrt(np.log(self.visit_count) / child.visit_count)
            uct_value = exploitation + exploration

            # RAVE value
            move = child.move
            if move in self.rave_visits and self.rave_visits[move] > 0:
                rave_value = self.rave_values[move] / self.rave_visits[move]

                # Mixing parameter based on visit counts
                alpha = max(0, (self.beta - child.visit_count) / self.beta)
                combined_value = (1 - alpha) * uct_value + alpha * rave_value
                return combined_value

            return uct_value

        return max(self.children, key=rave_uct)


class MCTS:
    def __init__(self, initial_state, max_simulations=1000, time_limit=None):
        self.max_simulations = max_simulations
        self.root = Node(initial_state)
        self.time_limit = time_limit
        self.minimax_agent = MinimaxAgent(depth=2)
        self.simulations_run = 0  # Track number of simulations for performance analysis

    def rollout_policy(self, possible_moves, state):
        """Enhanced rollout policy with strategic heuristics for both players"""

        # Different epsilon values for different players and game phases
        if state.goat_count > 0:  # Placement phase
            e = 0.1 if state.turn == Piece.GOAT else 0.05
        else:  # Movement phase
            e = 0.15 if state.turn == Piece.GOAT else 0.08

        if random.random() < e:
            return random.choice(possible_moves)

        # Use heuristic-based move selection for faster rollouts
        if state.turn == Piece.TIGER:
            # Prioritize captures, then mobility
            capture_moves = []
            mobility_moves = []

            for move in possible_moves:
                src, dst = move
                if src != dst:  # Not a placement
                    # Check if it's a capture (distance > 1 in graph)
                    # it's a capture move if dst not adjacent to src
                    if dst not in state.graph[src]:
                        capture_moves.append(move)
                    else:
                        # otherwise it's good for mobility (open space)
                        mobility_moves.append(move)

            if capture_moves:
                return random.choice(capture_moves)
            elif mobility_moves:
                # Prefer moves toward center or that increase mobility
                return self._select_best_mobility_move(mobility_moves, state)

        else:  # Goat turn
            return self._select_defensive_move(possible_moves, state)
            # if state.goat_count > 0:  # Placement phase
            #     return self._select_strategic_placement(possible_moves)
            # else:  # Movement phase
            #     return self._select_defensive_move(possible_moves, state)

        # Fallback to minimax if heuristics fail
        return self.minimax_agent.get_best_move(state)

    def _select_best_mobility_move(self, moves, state):
        """Select tiger move that maximizes future mobility"""
        best_move = moves[0]
        best_mobility = 0

        for move in moves:
            src, dst = move
            # Count empty adjacent positions from destination
            mobility = sum(
                1 for adj in state.graph[dst] if state.board[adj] == Piece.EMPTY)
            if mobility > best_mobility:
                best_mobility = mobility
                best_move = move

        return best_move

    def _select_strategic_placement(self, moves):
        """Strategic goat placement prioritizing control and blocking"""
        center_positions = {6, 8, 12, 16, 18}
        strategic_positions = {2, 10, 14, 22}  # Edge centers

        # Prioritize controlling edge centers
        for move in moves:
            pos = move[0]
            if pos in strategic_positions:
                return move

        for move in moves:
            pos = move[0]  # placement position
            if pos in center_positions:
                return move

        return random.choice(moves)

    def _select_defensive_move(self, moves, state):
        """Select goat moves that avoid capture and maintain formation"""
        safe_moves = []

        for move in moves:
            src, dst = move
            # Check if destination is safe from tiger capture
            is_safe = True
            for tiger_pos in [i for i, p in enumerate(state.board) if p == Piece.TIGER]:
                if dst in state.graph[tiger_pos]:
                    # Check if tiger can capture from this position
                    capture_pos = dst - (tiger_pos - dst)
                    if (capture_pos in state.graph[dst] and
                        capture_pos >= 0 and capture_pos < 25 and
                            state.board[capture_pos] == Piece.EMPTY):
                        is_safe = False
                        break

            if is_safe:
                safe_moves.append(move)

        return random.choice(safe_moves) if safe_moves else random.choice(moves)

    def search(self):
        """Enhanced search with RAVE and progressive widening"""
        def search_helper():
            expanded_node = self.tree_policy(self.root)
            result, move_sequence = self.rollout(expanded_node)
            self.backpropagate(expanded_node, result, move_sequence)
            self.simulations_run += 1

        self.simulations_run = 0

        if self.time_limit is not None:
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
        """Selection + expansion with progressive widening"""
        while not node.is_terminal():
            if not node.is_fully_expanded():
                return node.expand()
            else:
                node = node.best_child()
        return node

    def rollout(self, node):
        """Enhanced rollout that tracks move sequences for RAVE"""
        state_hash = defaultdict(int)
        state = node.state
        move_sequence = []  # Track moves played during rollout

        while not state.is_game_over():
            state_key = state.key()
            if state_key in state_hash:
                state_hash[state_key] += 1
            else:
                state_hash[state_key] = 1

            if state_hash[state_key] > 3:
                return 0, move_sequence  # Draw

            possible_moves = state.get_legal_moves()
            move = self.rollout_policy(possible_moves, state)
            move_sequence.append((move, state.turn))
            state = state.make_move(move)

        return state.get_result(), move_sequence  # +1 win for Tiger, -1 win for Goat

    def backpropagate(self, node, result, move_sequence=None):
        """Enhanced backpropagation with RAVE updates"""
        while node is not None:
            node.visit_count += 1
            # we flip the result so that the move that lead
            # to this node is wrt to the parent.
            # win means bad, loss means good, because the turn
            # of this node is flipped when making the move from
            # the parent
            node.total_value += node.player * -result

            # Update RAVE values
            if move_sequence:
                for move, player in move_sequence:
                    if player == node.player:  # Only update for same player moves
                        node.rave_visits[move] += 1
                        node.rave_values[move] += node.player * -result

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
                'value': child.total_value / child.visit_count if child.visit_count > 0 else 0,
                'rave_visits': child.parent.rave_visits.get(move, 0),
                'rave_value': (child.parent.rave_values.get(move, 0) /
                               child.parent.rave_visits.get(move, 1) if
                               child.parent.rave_visits.get(move, 0) > 0 else 0)
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
              f"Q: {avg_value:.3f}, "
              f"Player: {node.state.piece[node.player]}")

        prefix += "    " if is_last else "│   "

        child_count = len(node.children)
        # Sort children by visit count for better visualization
        sorted_children = sorted(
            node.children, key=lambda c: c.visit_count, reverse=True)

        # Show top 5 children only
        # for i, child in enumerate(sorted_children[:5]):
        for i, child in enumerate(sorted_children):
            # is_last_child = (i == min(4, child_count - 1))
            is_last_child = (i == child_count - 1)
            self.visualize_tree(child, prefix, is_last_child,
                                max_depth, current_depth + 1)
