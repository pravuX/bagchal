from enum import Enum

# Enhanced color palette
COLORS = {
    "bg": (245, 235, 220),  # Warm beige
    "board": (139, 90, 60),  # Dark brown
    "board_light": (180, 140, 100),  # Light brown
    "text": (40, 20, 10),  # Dark brown text
    "menu_bg": (25, 35, 45),  # Dark blue-grey #19232D
    "mode_bg": (35, 25, 45),  # Dark purple #23192D
    "button": (100, 70, 50),  # Brown button
    "button_hover": (140, 100, 70),  # Light brown hover
    "accent": (220, 180, 100),  # Gold accent
    "valid_move": (100, 200, 100, 100),  # Semi-transparent green
    "selected": (255, 220, 100, 150),  # Semi-transparent yellow
    "ai_thinking": (255, 200, 50),  # Bright yellow
    "white": (255, 255, 255),
    "game_over_bg": (20, 20, 30),  # Very dark
    "win_tiger": (255, 150, 50),
    "win_goat": (100, 255, 150)
}

ASSETS = {
    "font": "assets/font.ttf",
    "bagh": "assets/bagh.png",
    "goat": "assets/goat.png",
    "bagh_sel": "assets/bagh_selected.png",
    "goat_sel": "assets/goat_selected.png",
    "backgroundgradiant": "assets/backgroundgradiant.png",
    "playervsbagh" : "assets/playervsbagh.png",
    "playervsgoat" : "assets/playervsgoat.png",
    "playervsplayer" : "assets/playervsplayer.png",
    "AivsAi" : "assets/AivsAi.png",
    "playervsbaghhover" : "assets/playervsbaghhover.png",
    "playervsgoathover" : "assets/playervsgoathover.png",
    "playervsplayerhover" : "assets/playervsplayerhover.png",
    "AivsAihover" : "assets/AivsAihover.png", 
}


class UIState(Enum):
    MAIN_MENU = "main_menu"
    MODE_SELECT = "mode_select"
    PLAYING_PVP = "playing_pvp"
    PLAYING_PVC_GOAT = "playing_pvc_goat"
    PLAYING_PVC_TIGER = "playing_pvc_tiger"
    PLAYING_CVC = "playing_cvc"
    GAME_OVER = "game_over"
    ANALYSIS_MODE = "analysis_mode"
    REPLAYING = "replaying"
    EXITING = "exiting"
