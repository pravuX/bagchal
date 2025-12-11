import random
from bagchal import BitboardGameState
from symmetries import (
    generate_d4_transforms,
    canonicalize_state,
    symmetry_prune_moves,
)


def get_canonical_children(gamestate, moves, transforms):
    """
    Applies moves, gets resulting states, and converts them
    to their canonical representation keys.
    """
    canonical_keys = set()

    for move in moves:
        # Clone state to apply move
        child = gamestate.copy()
        child.make_move(move)

        # Calculate canonical key of the resulting child state
        # Note: We use child properties (tigers_bb, goats_bb, turn, etc.)
        key, _ = canonicalize_state(
            child.tigers_bb,
            child.goats_bb,
            child.turn,
            child.goats_to_place,
            transforms
        )
        canonical_keys.add(key)

    return canonical_keys


def test_pruning_correctness():
    transforms = generate_d4_transforms()

    # 1. Play a random game to generate diverse positions
    gs = BitboardGameState()

    for turn_idx in range(50):  # Check 50 random positions
        legal_moves = gs.get_legal_moves()

        if not legal_moves:
            break

        # --- THE CORE TEST ---
        pruned_moves = symmetry_prune_moves(
            gs.tigers_bb, gs.goats_bb, legal_moves, transforms
        )

        # A. Get all canonical outcomes from the FULL legal move list
        canon_full = get_canonical_children(gs, legal_moves, transforms)

        # B. Get all canonical outcomes from the PRUNED move list
        canon_pruned = get_canonical_children(gs, pruned_moves, transforms)

        # Assertion 1: Completeness
        # The pruner must not lose any strategic possibilities
        assert canon_full == canon_pruned, \
            f"FAILED at turn {turn_idx}: Pruner missed a unique state!"

        # Assertion 2: Efficiency
        # Every move in pruned_moves must lead to a UNIQUE canonical state
        # (i.e., no two pruned moves should be symmetric to each other)
        assert len(pruned_moves) == len(canon_pruned), \
            f"FAILED at turn {turn_idx}: Pruner kept redundant symmetric moves!"

        print(
            f"Turn {turn_idx}: OK (Legal: {len(legal_moves)} -> Pruned: {len(pruned_moves)})")

        # Make a random move to advance the game
        move = random.choice(legal_moves)
        gs.make_move(move)
        if gs.get_result is not None:
            break


if __name__ == "__main__":
    test_pruning_correctness()
