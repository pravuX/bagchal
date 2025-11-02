import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional


DATABASE_FILE = "bagchal_games.db"


def get_db_connection():
    """Get database connection, creating database file if it doesn't exist."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def initialize_database():
    """Initialize the database and create games table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            game_mode TEXT NOT NULL,
            winner TEXT,
            total_moves INTEGER NOT NULL,
            moves_data TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_game(game_state, game_mode: str, winner: Optional[str]) -> Optional[int]:
    """
    Save a completed game to the database.

    Args:
        game_state: BitboardGameState instance with move history
        game_mode: Game mode string ('PvP', 'PvC_Goat', 'PvC_Tiger', 'CvC')
        winner: Winner string ('Tiger', 'Goat', 'Draw') or None

    Returns:
        Game ID if successful, None otherwise
    """
    try:
        # Serialize moves from game_state.history
        # History format: [(move_tuple, captured_pos), ...]
        # where move_tuple = (src, dst) and captured_pos is position or -1
        moves_list = []
        for move, captured_pos in game_state.history:
            src, dst = move
            moves_list.append({
                "from": src,
                "to": dst,
                "capture": captured_pos if captured_pos != -1 else None
            })

        moves_json = json.dumps(moves_list)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_moves = len(moves_list)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO games (timestamp, game_mode, winner, total_moves, moves_data)
            VALUES (?, ?, ?, ?, ?)
        """, (timestamp, game_mode, winner, total_moves, moves_json))

        game_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return game_id
    except Exception as e:
        print(f"Error saving game: {e}")
        return None


def get_last_games(limit: int = 5) -> List[Dict]:
    """
    Retrieve the last N games from the database.

    Args:
        limit: Number of games to retrieve (default 5)

    Returns:
        List of dictionaries containing game information
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, timestamp, game_mode, winner, total_moves
            FROM games
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        games = []
        for row in rows:
            games.append({
                "id": row["id"],
                "timestamp": row["timestamp"],
                "game_mode": row["game_mode"],
                "winner": row["winner"],
                "total_moves": row["total_moves"]
            })

        return games
    except Exception as e:
        print(f"Error retrieving games: {e}")
        return []


def get_game_by_id(game_id: int) -> Optional[Dict]:
    """
    Retrieve a specific game by ID, including its move sequence.

    Args:
        game_id: ID of the game to retrieve

    Returns:
        Dictionary with game data and moves, or None if not found
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, timestamp, game_mode, winner, total_moves, moves_data
            FROM games
            WHERE id = ?
        """, (game_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            moves_data = json.loads(row["moves_data"])
            return {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "game_mode": row["game_mode"],
                "winner": row["winner"],
                "total_moves": row["total_moves"],
                "moves": moves_data
            }
        return None
    except Exception as e:
        print(f"Error retrieving game {game_id}: {e}")
        return None
