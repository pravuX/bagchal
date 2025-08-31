# mcts.py
from collections import defaultdict
import time
import numpy as np
from bagchal import Piece, GameState


class Node:
    """
    Node representing a GameState in the MCTS tree.
    Progressive Widening parameters are class-level and set by MCTS at construction.
    """
    PW_K = 1.5
    PW_ALPHA = 0.6

    def __init__(self, state: GameState, parent=None, move=None, prior_score=0.0):
        self.state: GameState = state
        self.parent = parent
        self.move = move

        self.children = []
        self.visit_count = 0
        self.total_value = 0.0
        # which player to move at this node when it was created
        self.player = self.state.turn

        # copy prioritized moves/scores so each node has its own unexpanded list
        # moves in descending/ascending order already computed
        self.prioritized_moves = list(self.state.prioritized_moves)
        self.prioritized_scores = list(self.state.prioritized_scores)
        # mapping move -> score for quick assignment to child
        try:
            self._move_to_score = dict(
                self.state.prioritized_moves_with_scores)
        except Exception:
            # fallback if that attribute is missing for some reason
            self._move_to_score = {m: s for m, s in zip(
                self.prioritized_moves, self.prioritized_scores)}

        # Unexpanded move stack (pop from end = highest priority if prioritized_moves is ascending)
        self._unexpanded_moves = list(self.prioritized_moves)

        # store the prior score (heuristic) for this node (useful for parent's UCT)
        self.prior_score = prior_score
        try:
            total_moves = self.total_moves()
            turn = "GOAT" if self.state.turn == -1 else "TIGER"

            with open("move_log.txt", "a") as f:
                f.write(f"{total_moves},{turn}\n")
        except Exception:
            pass

    def total_moves(self):
        return len(self.prioritized_moves)

    def allowed_children(self):
        # Progressive Widening schedule:
        # allowed = min(total_moves, max(1, int(k * visit_count^alpha)))
        if self.visit_count <= 0:
            return 1
        return min(self.total_moves(), max(1, int(Node.PW_K * (self.visit_count ** Node.PW_ALPHA))))

    def is_fully_expanded(self):
        # Under PW we are fully expanded if created children >= allowed children or no more moves remain.
        return (len(self.children) >= self.allowed_children()) or (len(self._unexpanded_moves) == 0)

    def expand(self):
        # pop the next move to expand (pop from end preserves ordering if list is ascending)
        if not self._unexpanded_moves:
            return None
        move = self._unexpanded_moves.pop()
        next_state = self.state.make_move(move)
        child_prior = self._move_to_score.get(move, 0.0)
        child_node = Node(next_state, parent=self,
                          move=move, prior_score=child_prior)
        self.children.append(child_node)
        return child_node

    def is_terminal(self):
        return self.state.is_game_over()

    def best_child(self, c_param=1.41):
        # UCT variant with heuristic bias derived from child's prior_score

        def uct_val(child):
            # exploitation (Q)
            if child.visit_count > 0:
                exploitation = child.total_value / child.visit_count
            else:
                exploitation = 0.0

            # exploration
            if child.visit_count > 0:
                exploration = c_param * \
                    np.sqrt(np.log(max(1, self.visit_count)) /
                            child.visit_count)
            else:
                # encourage trying unvisited children (standard trick)
                exploration = float('inf')

            # heuristic bias decays with sqrt(visits) to ensure it matters early but fades later
            decay = np.sqrt(
                child.visit_count) if child.visit_count > 0 else 1.0
            heuristic_bias = 10.0 * (child.prior_score / decay)

            return exploitation + exploration + heuristic_bias

        if not self.children:
            return None
        return max(self.children, key=uct_val)


class MCTS:
    def __init__(self, initial_state: GameState, max_simulations=1000, time_limit=None,
                 pw_k=1.2, pw_alpha=0.6, c_param=2,
                 rollout_depth=50, rollout_epsilon=0.05):
        """
        rollout_depth: cap for rollout length (plies). If reached, evaluate heuristically.
        rollout_epsilon: small randomness in greedy rollout (epsilon-greedy).
        """
        self.max_simulations = max_simulations
        self.root = Node(initial_state)
        self.time_limit = time_limit
        self.simulations_run = 0

        self.goat_wins = 0
        self.tiger_wins = 0

        # tracking node reuse counts (optional diagnostic)
        self.nodes = defaultdict(int)

        # configure progressive widening & exploration constant
        Node.PW_K = pw_k
        Node.PW_ALPHA = pw_alpha
        self.c_param = c_param

        # rollout config
        self.rollout_depth = rollout_depth
        self.rollout_epsilon = rollout_epsilon

    def rollout_policy(self, state: GameState):
        """
        Greedy-with-small-noise rollout policy:
        - Pick highest-priority move most of the time.
        - With probability epsilon, pick a random move (ensures exploration).
        This is faster and lower variance than pure random rollouts.
        """
        moves = state.prioritized_moves
        if not moves:
            return None
        if np.random.random() < self.rollout_epsilon:
            return moves[np.random.randint(len(moves))]
        # deterministic greedy: highest prior. Prior list likely sorted, pick last or first depending on construction.
        # We pick the move with max prior_score via state.prioritized_scores for safety.
        # highest prior probability index
        idx = int(np.argmax(state.prior_prob_dist))
        return state.prioritized_moves[idx]

    def evaluate_state(self, state: GameState):
        """
        Cheap heuristic evaluator returning a float in [-1, 1].
        Positive -> GOAT advantage, Negative -> TIGER advantage.
        Heuristic focuses on trapped_tiger_count and eaten_goat_count.
        """
        # update trapped_tiger_count if not already up-to-date
        # (GameState should call update_trapped_tiger when moves are applied in make_move,
        # but we call it here to be safe.)
        # (Don't change GameState state inside evaluator in a way that mutates the game incorrectly)
        try:
            trapped = state.trapped_tiger_count
        except Exception:
            state.update_trapped_tiger()
            trapped = state.trapped_tiger_count

        eaten = state.eaten_goat_count
        goat_left = state.goat_count
        goats_on_board = 20 - (eaten + goat_left)

        # Heuristic idea:
        # - trapping 4 tigers => decisive goat win
        # - eating >4 goats => strong tiger advantage
        # Normalize these heuristics to [-1, 1]
        trap_score = (trapped / 4.0)  # in [0,1]
        eat_score = min(eaten / 5.0, 1.0)  # scale to [0,1], >5 saturates

        # Combine: goat wants traps high, tiger wants eaten high (positive)
        raw = eat_score - trap_score

        # small bonus for goats having many pieces on board (more goats alive -> better)
        # 0 means all goats available (placement phase), 1 means all placed & eaten?
        goat_presence = goats_on_board / 20.0
        # we invert presence so more goat left gives slight positive advantage for goats
        goat_presence_bonus = goat_presence * 0.05

        raw -= goat_presence_bonus

        # Clamp into [-1, 1]
        raw = max(-1.0, min(1.0, raw))
        return raw

    def search(self):
        def search_helper():
            expanded_node = self.tree_policy(self.root)
            result = self.rollout(expanded_node)
            self.backpropagate(expanded_node, result)
            # track node occurrences
            self.nodes[expanded_node.state.key()] += 1
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

    def tree_policy(self, node: Node):
        """
        Descend the tree applying progressive widening:
        - If node can expand (children < allowed_children and unexpanded moves exist), expand and return that child.
        - Else pick best_child and continue.
        Stops on terminal nodes.
        """
        while not node.is_terminal():
            # if we are allowed to add more children, expand one
            if (len(node.children) < node.allowed_children()) and (len(node._unexpanded_moves) > 0):
                expanded = node.expand()
                if expanded is not None:
                    return expanded
            # otherwise descend
            next_node = node.best_child(self.c_param)
            if next_node is None:
                # fallback: try expanding if possible
                expanded = node.expand()
                if expanded is not None:
                    return expanded
                # if cannot expand and no child to descend into, return node
                return node
            node = next_node
        return node

    def rollout(self, node: Node):
        """
        Rollout from node.state until terminal or until depth cap reached.
        If depth cap reached, return heuristic evaluation (float in [-1,1]).
        If repeated position is detected > repetition_limit, return 0 (draw-ish).
        Returns either Piece.GOAT / Piece.TIGER / 0 or a float heuristic in [-1,1].
        """
        repetition_limit = 3
        state = node.state
        state_hash_counts = defaultdict(int)

        # depth = 0
        while not state.is_game_over():
            state_key = state.key()
            state_hash_counts[state_key] += 1
            if state_hash_counts[state_key] > repetition_limit:
                # repetition -> draw-ish outcome
                return 0.0

            # if depth >= self.rollout_depth:
            #     # heuristic evaluation (float)
            #     return self.evaluate_state(state)

            move = self.rollout_policy(state)
            state = state.make_move(move)
            # depth += 1

        # terminal: return exact result (Piece enum) or 0
        res = state.get_result()
        if res is None:
            return 0.0
        return float(res)

    def backpropagate(self, node: Node, result):
        """
        result can be:
         - Piece.GOAT (1), Piece.TIGER (-1), 0, or float in [-1,1].
        The existing code used: node.total_value += -node.player * result
        That formula still holds for floats.
        """
        while node is not None:
            node.visit_count += 1
            node.total_value += -node.player * result
            node = node.parent

    def get_best_move(self):
        """
        Return the child move with the highest visit count (robust selection).
        """
        if not self.root.children:
            return None
        most_visited_child = max(
            self.root.children, key=lambda c: c.visit_count)
        return most_visited_child.move

    def get_move_statistics(self):
        """
        Return useful statistics for debugging/inspection.
        """
        if not self.root.children:
            return {}
        stats = {}
        for child in self.root.children:
            stats[child.move] = {
                'visits': child.visit_count,
                'q-value': child.total_value / child.visit_count if child.visit_count > 0 else 0,
                'prior': child.prior_score,
            }
        return stats

    def visualize_tree(self, node=None, prefix="", is_last=True, max_depth=3, current_depth=0):
        """
        Optional: tree dump for debugging (keeps your existing method style).
        """
        if node is None:
            node = self.root
            print("MCTS Search Tree")
            print("================")

        if current_depth > max_depth:
            return

        connector = "└── " if is_last else "├── "
        move_str = f"Move: {node.move}" if node.move else "Root"
        avg_value = node.total_value / node.visit_count if node.visit_count > 0 else 0
        print(
            f"{prefix}{connector}{move_str} | N: {node.visit_count}, V: {node.total_value:.3f}, Q: {avg_value:.3f}, Turn: {node.state.piece[node.player]}")

        prefix += "    " if is_last else "│   "
        children = sorted(
            node.children, key=lambda c: c.visit_count, reverse=True)
        for i, child in enumerate(children):
            is_last_child = (i == len(children) - 1)
            self.visualize_tree(child, prefix, is_last_child,
                                max_depth, current_depth + 1)
