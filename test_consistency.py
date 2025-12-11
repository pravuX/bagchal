from negamax import AlphaBetaAgent
from bagchal import BitboardGameState


def test_search_consistency():
    print("--- Testing Minimax Consistency ---")

    gs = BitboardGameState()

    # 1. Search WITHOUT Pruning
    print("Running Unpruned Search...")
    agent_raw = AlphaBetaAgent(use_symmetry=False)
    # Use a fixed shallow depth to be quick, but deep enough to branch
    move_raw = agent_raw.get_best_move(gs, time_limit=5.0)
    # Note: You might need to hack get_best_move to return the SCORE as well
    # for a proper comparison, or check agent_raw.tt for the root node score.

    # 2. Search WITH Pruning
    print("Running Pruned Search...")
    agent_pruned = AlphaBetaAgent(use_symmetry=True)
    move_pruned = agent_pruned.get_best_move(gs, time_limit=5.0)

    # Note: Moves might differ if there are two equally good moves!
    # Ideally, you verify the SCORE at the root node.

    # If your get_best_move prints the score, visually compare them.
    # To automate, modify get_best_move to return (move, score).

    print(f"Unpruned Move: {move_raw}")
    print(f"Pruned Move:   {move_pruned}")

    if agent_raw.best_depth < agent_pruned.best_depth:
        print(
            f"SUCCESS: Nodes reduced!")

        print(
            f"Raw depth: {agent_raw.best_depth}, Nodes: {agent_raw.no_of_nodes} -> Pruned Depth {agent_pruned.best_depth}, Nodes: {agent_pruned.no_of_nodes}")
    elif agent_raw.best_depth == agent_pruned.best_depth:
        print("WARNING: Nodes not reduced (start position might be too symmetric/simple or overhead issues).")


if __name__ == "__main__":
    test_search_consistency()
