from state_utils import generate_random_state, save_state, load_state, serialize_state
import os


def test_state_generation():
    print("Testing Random State Generation...")

    # Test 1: Defaults
    gs = generate_random_state()
    print(f"Random State 1: {gs}, key={gs.key}")

    # Test 2: Specific constraints
    gs2 = generate_random_state(
        goats_on_board=5, goats_eaten=2, randomize_tigers=False)
    print(f"Random State 2 (5 goats, 2 eaten, corner tigers): {gs2}")

    data2 = serialize_state(gs2)
    assert len(data2['tigers']) == 4
    assert len(data2['goats']) == 5
    assert data2['goats_eaten'] == 2
    assert set(data2['tigers']) == {0, 4, 20, 24}

    print("Generation Logic Verified.")


def test_save_load():
    print("\nTesting Save/Load...")
    gs = generate_random_state()
    filename = "test_state.json"

    save_state(gs, filename)
    print(f"Saved state to {filename}")

    loaded_gs = load_state(filename)
    print(f"Loaded state: {loaded_gs}")

    # Verify equality
    assert gs.tigers_bb == loaded_gs.tigers_bb
    assert gs.goats_bb == loaded_gs.goats_bb
    assert gs.turn == loaded_gs.turn
    assert gs.goats_to_place == loaded_gs.goats_to_place
    assert gs.goats_eaten == loaded_gs.goats_eaten

    print("Save/Load Verified.")

    if os.path.exists(filename):
        os.remove(filename)


if __name__ == "__main__":
    test_state_generation()
    test_save_load()
