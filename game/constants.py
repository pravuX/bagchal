from enum import Enum

# Enhanced color palette
COLORS = {
    "bg": (245, 235, 220),  # Warm beige
    "board": (139, 90, 60),  # Dark brown
    "board_light": (180, 140, 100),  # Light brown
    "text": (40, 20, 10),  # Dark brown text
    "menu_bg": (25, 35, 45),  # Dark blue-grey
    "mode_bg": (35, 25, 45),  # Dark purple
    "button": (100, 70, 50),  # Brown button
    "button_hover": (140, 100, 70),  # Light brown hover
    "accent": (220, 180, 100),  # Gold accent
    "valid_move": (100, 200, 100, 100),  # Semi-transparent green
    "selected": (255, 220, 100, 150),  # Semi-transparent yellow
    "ai_thinking": (255, 200, 50),  # Bright yellow
    "white": (255, 255, 255),
    "game_over_bg": (20, 20, 30),  # Very dark
}

ASSETS = {
    "font": "assets/font.ttf",
    "bagh": "assets/bagh.png",
    "goat": "assets/goat.png",
    "bagh_sel": "assets/bagh_selected.png",
    "goat_sel": "assets/goat_selected.png",
}


class UIState(Enum):
    MAIN_MENU = "main_menu"
    MODE_SELECT = "mode_select"
    PLAYING_PVP = "playing_pvp"
    PLAYING_PVC_GOAT = "playing_pvc_goat"
    PLAYING_PVC_TIGER = "playing_pvc_tiger"
    PLAYING_CVC = "playing_cvc"
    GAME_OVER = "game_over"
    EXITING = "exiting"
