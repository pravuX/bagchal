import json
import random
import os
from bagchal import BitboardGameState, extract_indices_fast, Piece_TIGER, Piece_GOAT


def serialize_state(game_state: BitboardGameState) -> dict:
    """
    Serializes a BitboardGameState into a dictionary.

    Args:
        game_state: The game state to serialize.

    Returns:
        A dictionary representation of the game state.
    """
    # TODO: is it better to store integers here?
    return {
        "tigers": extract_indices_fast(game_state.tigers_bb),
        "goats": extract_indices_fast(game_state.goats_bb),
        "turn": game_state.turn,
        "goats_to_place": game_state.goats_to_place,
        "goats_eaten": game_state.goats_eaten
    }


def deserialize_state(data: dict) -> BitboardGameState:
    """
    Deserializes a dictionary into a BitboardGameState.

    Args:
        data: A dictionary containing game state data.

    Returns:
        A reconstructed BitboardGameState object.
    """
    tigers_bb = 0
    for pos in data.get("tigers", []):
        tigers_bb |= (1 << pos)

    goats_bb = 0
    for pos in data.get("goats", []):
        goats_bb |= (1 << pos)

    return BitboardGameState(
        tigers_bb=tigers_bb,
        goats_bb=goats_bb,
        turn=data.get("turn", Piece_GOAT),
        goats_to_place=data.get("goats_to_place", 20),
        goats_eaten=data.get("goats_eaten", 0)
    )


def save_state(game_state: BitboardGameState, filename: str):
    """
    Saves the game state to a JSON file.

    Args:
        game_state: The game state to save.
        filename: The path to the file.
    """
    data = serialize_state(game_state)
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


def load_state(filename: str) -> BitboardGameState:
    """
    Loads a game state from a JSON file.

    Args:
        filename: The path to the file.

    Returns:
        The loaded BitboardGameState.
    """
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File not found: {filename}")

    with open(filename, 'r') as f:
        data = json.load(f)
    return deserialize_state(data)


def generate_random_state(
    goats_on_board=None,
    goats_eaten=None,
    turn=None,
    randomize_tigers=True
) -> BitboardGameState:
    """
    Generates a random valid game state.

    Args:
        goats_on_board (int, optional): Number of goats on the board. If None, random (0-20).
        goats_eaten (int, optional): Number of goats eaten. If None, random (0-5).
                                     Note: goats_on_board + goats_eaten must be <= 20.
        turn (int, optional): The player to move (Piece_TIGER or Piece_GOAT). If None, random.
        randomize_tigers (bool): If True, places 4 tigers randomly. If False, usage standard corners.

    Returns:
        A BitboardGameState with the generated configuration.
    """
    # 1. Determine goats eaten
    if goats_eaten is None:
        goats_eaten = random.randint(0, 5)

    # 2. Determine goats on board
    max_goats_on_board = 20 - goats_eaten
    if goats_on_board is None:
        # Weighted random might be better for realism, but uniform is simple for now
        goats_on_board = random.randint(0, max_goats_on_board)

    if goats_on_board + goats_eaten > 20:
        raise ValueError(
            f"Invalid configuration: {goats_on_board} on board + {goats_eaten} eaten > 20 total goats")

    goats_to_place = 20 - goats_on_board - goats_eaten

    # 3. Determine Turn
    if turn is None:
        turn = random.choice([Piece_TIGER, Piece_GOAT])

    # 4. Place Tigers
    all_positions = list(range(25))
    if randomize_tigers:
        tiger_positions = random.sample(all_positions, 4)
    else:
        tiger_positions = [0, 4, 20, 24]  # Standard corners

    tigers_bb = 0
    for pos in tiger_positions:
        tigers_bb |= (1 << pos)

    # 5. Place Goats
    # Goats cannot be placed on tiger positions
    available_positions = [
        p for p in all_positions if p not in tiger_positions]

    if len(available_positions) < goats_on_board:
        raise ValueError("Not enough empty spots to place goats")

    goat_positions = random.sample(available_positions, goats_on_board)
    goats_bb = 0
    for pos in goat_positions:
        goats_bb |= (1 << pos)

    return BitboardGameState(
        tigers_bb=tigers_bb,
        goats_bb=goats_bb,
        turn=turn,
        goats_to_place=goats_to_place,
        goats_eaten=goats_eaten
    )
