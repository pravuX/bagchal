import time
import numpy as np
from bagchal import *


class Node:

    __slots__ = ['parent', 'move', 'children',
                 'visit_count', 'total_value',
                 'player_to_move', 'unexpanded_moves']

    def __init__(self, total_value=0.0,
                 visit_count=0, parent=None, move=None, player_to_move=None):
        self.parent: Node = parent
        self.move = move  # incoming move
        self.player_to_move = player_to_move
        self.unexpanded_moves = None  # Lazy Expansion
        self.children = []

        # MCTS Stats
        self.visit_count = visit_count
        self.total_value = total_value

    def __repr__(self):
        return f"Node(move={self.move}, visits={self.visit_count}, value={self.total_value:.2f}, player_to_move={self.player_to_move})"


class MCTS:
    previous_evaluations = {}
    legal_moves_cache = {}

    def __init__(self):
        self.rollout_epsilon = 0.05
        # it feels to me that, setting a smaller rollout depth is akin to the idea
        # of quiescene in alpha beta search. like instead of statically evaluating
        # the leaf, we're basically extending the horizon some moves ahead to obtain
        # a more stable evaluation of the state
        self.rollout_depth = 5

    def search(self, initial_state: BitboardGameState, max_simulations=1000, time_limit=None, game_history=None):
        # print("Searching move...")
        self.game_history = game_history

        self.game_state = initial_state.copy()

        if len(self.legal_moves_cache) >= 50_000:
            self.legal_moves_cache.clear()
        if len(self.previous_evaluations) >= 50_000:
            self.previous_evaluations.clear()

        self.root = Node(player_to_move=self.game_state.turn)
        self.simulations_run = 0
        self.goat_wins = 0
        self.tiger_wins = 0
        self.draws = 0

        def search_helper():
            # print(self.game_state)
            path_nodes = self.tree_policy()
            # path_nodes contains all the nodes encountered during
            #  tree traversal.
            # we use it to to propagate result of the rollout

            # at this point the game_state has been modified
            result = self.rollout()
            # we modify the game_state further during rollout

            self.backpropagate(result, path_nodes)

            # we call unmake_move until the game_state.history is empty
            # to reset the game_state to initial_state for next iteration
            self.undo_path_to_root()

            self.simulations_run += 1
            if result == Piece_TIGER:
                self.tiger_wins += 1
            elif result == Piece_GOAT:
                self.goat_wins += 1
            elif result == Piece_EMPTY:
                self.draws += 1

        if time_limit is not None:
            end_time = time.time() + time_limit
            while time.time() < end_time:
                search_helper()
        else:
            while self.simulations_run < max_simulations:
                search_helper()
        best_move = self.get_best_move()
        # print(f"Best move: {best_move}")
        return best_move

    def get_best_move(self):
        # max_child: Node = self.root.best_child(c_param=0)
        most_visited_child = max(
            self.root.children, key=lambda c: c.visit_count)
        return most_visited_child.move

    def tree_policy(self):
        # Selection + Expansion
        current_node = self.root
        path_nodes = []

        path_nodes.append(current_node)

        while True:
            if self.game_state.is_game_over:
                return path_nodes

            # Lazy Move Generation
            if current_node.unexpanded_moves is None:
                current_node.unexpanded_moves = self.get_prioritized_moves()

            # this means that it is expandable
            if len(current_node.unexpanded_moves) > 0:

                move = current_node.unexpanded_moves.pop()

                # First Play Urgency (FPU)
                # this injects a virtual win rate
                # hopefully will help overcome the cold start problem
                if current_node.player_to_move == Piece_TIGER:
                    p_score = tiger_priority(
                        self.game_state.tigers_bb, self.game_state.goats_bb, move, MOVE_MASKS_NP, CAPTURE_COUNTS, CAPTURE_MASKS_NP)

                else:
                    p_score = goat_priority(
                        self.game_state.tigers_bb, self.game_state.goats_bb, move, MOVE_MASKS_NP, CAPTURE_COUNTS, CAPTURE_MASKS_NP, OUTER_EDGE_MASK, STRATEGIC_MASK)

                priority_score_norm = -1 * np.tanh(0.1 * p_score)

                self.game_state.make_move(move)

                if self.game_state.key in self.game_history:
                    # bad negative score means, repeated position for the player to move
                    #  at the node is bad
                    # multiply by -1 to flip perspective to that of the parent
                    priority_score_norm += -1 * -1000

                new_child = Node(
                    total_value=priority_score_norm,
                    parent=current_node,
                    move=move,
                    player_to_move=self.game_state.turn
                )
                current_node.children.append(new_child)
                path_nodes.append(new_child)

                return path_nodes

            best_child = self.select_best_child(current_node)
            path_nodes.append(best_child)

            self.game_state.make_move(best_child.move)

            current_node = best_child

    def select_best_child(self, node: Node, c_param=0.7):

        def uct(child: Node):
            if child.visit_count == 0:
                return float('inf')

            q_standard = -1 * (child.total_value / child.visit_count)

            exploitation = q_standard

            exploration = c_param * \
                np.sqrt(np.log(node.visit_count)/child.visit_count)

            return exploitation + exploration

        return max(node.children, key=uct)

    # Move Prioritization

    def _score_move(self,  move):
        if self.game_state.turn == Piece_TIGER:
            return tiger_priority(self.game_state.tigers_bb, self.game_state.goats_bb, move, MOVE_MASKS_NP, CAPTURE_COUNTS, CAPTURE_MASKS_NP)
        else:
            return goat_priority(self.game_state.tigers_bb, self.game_state.goats_bb, move, MOVE_MASKS_NP, CAPTURE_COUNTS, CAPTURE_MASKS_NP, OUTER_EDGE_MASK, STRATEGIC_MASK)

    def get_prioritized_moves(self):

        state_key = self.game_state.key
        if state_key in self.legal_moves_cache:
            moves = self.legal_moves_cache[state_key]
        else:
            moves = self.game_state.get_legal_moves()
            self.legal_moves_cache[state_key] = moves

        scored_moves = [(move, self._score_move(move))
                        for move in moves]
        scored_moves.sort(key=lambda x: x[1])  # Best moves last
        moves = [move for move, _ in scored_moves]

        return moves

    def rollout_policy(self):
        # random rollouts
        # moves = self.game_state.get_legal_moves_np()
        # return moves[np.random.randint(len(moves))]
        # semi-random rollout policy
        moves = self.get_prioritized_moves()
        if np.random.random() < self.rollout_epsilon:
            return moves[np.random.randint(len(moves))]
        best_move = moves[-1]
        return best_move

    def rollout(self):
        # at this point we have the state of the newly added node to the tree
        # we perform a rollout here
        # we can add depth limited rollouts if we want later
        depth = 0
        while not self.game_state.is_game_over and depth < self.rollout_depth:
            move = self.rollout_policy()

            self.game_state.make_move(move)
            depth += 1

        if self.game_state.is_game_over:
            result = self.game_state.get_result
        else:
            result = np.tanh(
                0.5 * self.evaluate_state(self.game_state, self.game_state.key))

        # result = np.tanh(
        #     0.5 * self.evaluate_state(self.game_state, self.game_state.key))

        return result

    def backpropagate(self, result, path_nodes):

        for node in path_nodes:
            # MCTS Update
            node.visit_count += 1
            node.total_value += node.player_to_move * result

    def undo_path_to_root(self):
        """
        Undo all moves taken during tree traversal to return to root state
        """

        while self.game_state.history:
            self.game_state.unmake_move()

    def _get_potential_captures(self, state: BitboardGameState, empty_bb):

        capture_opportunities = 0
        for tiger in extract_indices_fast(state.tigers_bb):
            for mid_mask, land_mask in CAPTURE_MASKS[tiger]:
                if (state.goats_bb & mid_mask) and (empty_bb & land_mask):
                    capture_opportunities += 1

        return capture_opportunities

    def _get_tiger_accessibility(self, state: BitboardGameState):
        accessible, inaccessible = tiger_board_accessibility(
            state.tigers_bb, state.goats_bb,
            MOVE_MASKS_NP, CAPTURE_COUNTS, CAPTURE_MASKS_NP)
        return accessible, inaccessible

    def evaluate_state(self, state: BitboardGameState, state_key):
        """
        Positive -> TIGER advantage, Negative -> GOAT advantage.
        """
        occupied_bb = state.tigers_bb | state.goats_bb
        empty_bb = ~occupied_bb & BOARD_MASK

        assert state_key

        if state_key in self.previous_evaluations:
            return self.previous_evaluations[state_key]

        is_placement = state.goats_to_place > 0

        eat_max = 4  # before win
        potential_capture_max = 5
        inaccessible_max = 4

        trap_max = 3  # before win
        goat_presence_max = 20
        tiger_mobility_max = 25

        p_mobility = 0 if is_placement else w_mobility

        if state.is_game_over:
            result = state.get_result
            return 2000 if result == Piece_TIGER else -2000

        trapped = state.trapped_tiger_count
        eaten = state.goats_eaten
        goat_left = state.goats_to_place
        goats_on_board = 20 - (eaten + goat_left)

        eaten_score = eaten / eat_max

        potential_captures = self._get_potential_captures(
            state, empty_bb)
        potential_capture_score = potential_captures / potential_capture_max
        potential_capture_score = min(1, potential_capture_score)

        trap_score = trapped / trap_max
        goat_presence_score = goats_on_board / goat_presence_max
        no_of_accessible_positions, no_of_inaccessible_positions = self._get_tiger_accessibility(
            state)

        inaccessibility_score = no_of_inaccessible_positions / inaccessible_max
        tiger_mobility_score = no_of_accessible_positions / tiger_mobility_max
        inaccessibility_score = min(1, inaccessibility_score)

        tiger_score = (eaten_score * w_eat +
                       potential_capture_score * w_potcap +
                       tiger_mobility_score * p_mobility)

        goat_score = (trap_score * w_trap +
                      goat_presence_score * w_presence +
                      inaccessibility_score * w_inacc)

        final_evaluation = tiger_score - goat_score
        self.previous_evaluations[state_key] = final_evaluation
        return final_evaluation

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
            f"{prefix}{connector}{move_str} | Q: {wins:.3f}, N: {node.visit_count}, Q/N: {avg_value:.3f}, Turn: {BitboardGameState.piece[node.player_to_move]}")

        prefix += "    " if is_last else "│   "
        children = sorted(
            node.children, key=lambda c: c.visit_count, reverse=True)
        for i, child in enumerate(children):
            is_last_child = (i == len(children) - 1)
            self.visualize_tree(child, prefix, is_last_child,
                                max_depth, current_depth + 1)
