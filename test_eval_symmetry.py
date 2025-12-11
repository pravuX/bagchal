from bagchal import BitboardGameState
from symmetries import generate_d4_transforms, apply_perm_to_bb
from negamax import AlphaBetaAgent
from main import display_board


def test_eval_symmetry():
    print("--- Testing Evaluation Function Symmetry ---")
    transforms = generate_d4_transforms()
    agent = AlphaBetaAgent()
    gs = BitboardGameState()  # Start state

    display_board(gs)
    print(gs)
    # return
    gs.make_move((2, 2))
    gs.make_move((0, 1))

    agent.game_state = gs.copy()
    base_score = agent.evaluate()

    print(f"Base Score: {base_score}")

    for i, perm in enumerate(transforms):
        # Create a manually transformed state
        rot_tigers = apply_perm_to_bb(gs.tigers_bb, perm)
        rot_goats = apply_perm_to_bb(gs.goats_bb, perm)

        # Create new agent/state with rotated bitboards
        rot_gs = BitboardGameState(
            tigers_bb=rot_tigers,
            goats_bb=rot_goats,
            turn=gs.turn,
            goats_to_place=gs.goats_to_place,
            goats_eaten=gs.goats_eaten
        )

        agent.game_state = rot_gs.copy()
        rot_score = agent.evaluate()

        if abs(base_score - rot_score) > 0.001:
            print(
                f"FAIL: Transform {i} changed score! {base_score} != {rot_score}")
            return

    print("SUCCESS: Evaluation function is symmetric invariant.")


if __name__ == "__main__":
    test_eval_symmetry()
