import threading
from collections import defaultdict
import traceback
import pygame
from bagchal import *
from negamax import AlphaBetaAgent
from mcts import MCTS
from .constants import UIState, ASSETS, COLORS
from .effects import ParticleEffect
from .renderer import GameRenderer
from .event_handler import EventHandler
from .database import initialize_database, save_game, get_game_by_id

mcts_flag, minimax_flag = 0, 1


class Game:
    def __init__(self, game_state,
                 caption="Bagchal - The Tiger and Goats Game",
                 cell_size=180,
                 tick_speed=60,
                 min_cell_size=100,
                 max_cell_size=500):
        pygame.init()
        pygame.display.set_caption(caption)

        self.game_state: BitboardGameState = game_state
        self.cell_size = cell_size
        self.min_cell_size = min_cell_size
        self.max_cell_size = max_cell_size

        self.current_state = UIState.MAIN_MENU
        self.running = True
        self.pending_player_move = None
        self.using_agent = minimax_flag
        self.ai_thread = None
        self.time_limit = 1.0
        self.ai_is_thinking = False
        self.ai_result_move = None
        self.game_over_timer = 0
        self.game_over_delay = 1000

        self.initialize_board_data()
        self.selected_cell = None
        self.valid_moves = []

        self.initialize_pygame_state(tick_speed)
        self.load_assets()
        self.cache_scaled_assets()

        self.state_hash = defaultdict(int)

        self.ai_initialized = False
        self.game_just_reset = False
        self.initial_render_done = False
        self.move_processed_this_frame = False
        self.last_move_frame = None
        self.particles = []
        self.piece_animations = {}
        self.button_hover = None
        self.ai_pulse = 0
        self.last_move_highlight = None

        self.renderer = GameRenderer(self)
        self.event_handler = EventHandler(self)

        self.resize_timer = 0
        self.resize_delay = 200  # 200ms delay after the last resize event
        self.pending_resize = None

        # Board surface for maintaining aspect ratio

        # Track game mode for saving
        self.current_game_mode = None

        # Replay state management
        self.replay_mode = False
        self.replay_moves = []
        self.replay_index = 0  # 0 = initial state, 1 = after first move, etc.
        self.auto_play = False
        self.replay_game_id = None
        self.replay_timer = 0
        self.replay_auto_play_delay = 1500  # 1.5 seconds per move
        self.ai_suggestions = {}  # Cache AI suggestions for replay positions

        # Initialize database
        initialize_database()

        self.initialize_button_rects()

    def initialize_button_rects(self):
        x_width = self.screen_size[0]
        y_height = self.screen_size[1]
        menu_button_width = 250
        menu_button_height = 120
        y_spacing = 150
        btn_width = x_width * 0.18
        btn_height = y_height * 0.360
        # menu buttons
        self.play_btn_rect_main = pygame.Rect(
            x_width//2 - 100,
            350,
            menu_button_width,
            menu_button_height)

        self.analysis_btn_rect = pygame.Rect(
            x_width//2 - 100,
            350 + y_spacing,
            menu_button_width,
            menu_button_height)

        self.exit_btn_rect_main = pygame.Rect(
            x_width//2 - 100,
            350 + 2 * y_spacing,
            menu_button_width,
            menu_button_height)

        if x_width >= 1000:
            btn_width = 180
            btn_height = 360
        # mode select buttons
        self.pvp_rect = pygame.Rect(
            x_width//2 - 2* btn_width - x_width* .084,
            y_height * 0.35,
            btn_width,
            btn_height)

        self.pvc_goat_rect = pygame.Rect(
            x_width//2 -btn_width - x_width* .028,
            y_height * 0.35,
            btn_width,
            btn_height)

        self.pvc_tiger_rect = pygame.Rect(
            x_width//2 + x_width *.028,
            y_height * 0.35,
            btn_width,
            btn_height)

        self.cvc_rect = pygame.Rect(
            x_width//2 + x_width * .084+ btn_width,
            y_height * 0.35,
            btn_width,
            btn_height)

        # Analysis main menu button
        self.analysis_mm_btn = pygame.Rect(
            x_width // 2 - 150,
            y_height - 80,
            300,
            60)

        # Replay control buttons at bottom
        button_height = 50
        button_width = 150
        button_spacing = 170
        button_x = x_width - 150
        button_y = 300 - button_height // 2

        # Previous button
        self.prev_btn_rect = pygame.Rect(
            button_x,
            button_y,
            button_width,
            button_height
        )

        # Play/Pause button
        self.play_btn_rect = pygame.Rect(
            button_x,
            button_y + button_spacing * 0.5,
            button_width,
            button_height
        )

        # Next button
        self.next_btn_rect = pygame.Rect(
            button_x,
            button_y + button_spacing * 1.0,
            button_width,
            button_height
        )

        # Exit replay button
        self.exit_btn_rect = pygame.Rect(
            x_width - 120,
            20,
            100,
            40
        )

        # Replay back button
        self.back_btn_rect = pygame.Rect(
            x_width // 2 - 100,
            y_height - 80,
            200, 60
        )

    def check_for_resize(self):
        if self.pending_resize is None:
            return

        # Check if enough time has passed since the last resize event
        if pygame.time.get_ticks() - self.resize_timer > self.resize_delay:
            self.handle_resize(self.pending_resize)
            self.pending_resize = None  # Clear the pending resize

    def state_hash_update(self):
        state_key = self.game_state.key
        self.state_hash[state_key] += 1

    def initialize_board_data(self):
        self.grid_width = self.cell_size * 5
        self.grid_height = self.cell_size * 5
        self.grid_cols = 5
        self.grid_rows = 5
        self.offset = self.cell_size // 2
        self.board_width = self.grid_width - self.cell_size
        self.board_height = self.grid_height - self.cell_size

        # Create/update board surface with fixed aspect ratio
        board_size = self.grid_width  # Square board
        self.board_surface_size = (board_size, board_size)
        self.board_surface = pygame.Surface(
            self.board_surface_size, pygame.SRCALPHA)

        # Update screen size (can be different from board size)
        if not hasattr(self, 'screen_size') or self.screen_size is None:
            # Initial screen size calculation
            self.screen_size = (self.grid_width, self.grid_height + 100)
        else:
            # Maintain screen size, only update board positioning
            self.update_board_position()

    def initialize_pygame_state(self, tick_speed):
        self.screen = pygame.display.set_mode(
            self.screen_size, pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.tick_speed = tick_speed

    def load_assets(self):
        self.bagh_img_original = pygame.image.load(
            ASSETS["bagh"]).convert_alpha()
        self.goat_img_original = pygame.image.load(
            ASSETS["goat"]).convert_alpha()
        self.bagh_selected_original = pygame.image.load(
            ASSETS["bagh_sel"]).convert_alpha()
        self.goat_selected_original = pygame.image.load(
            ASSETS["goat_sel"]).convert_alpha()
        self.backgroundgradiant_original = pygame.image.load(
            ASSETS["backgroundgradiant"]).convert_alpha()
        self.pvp_original = pygame.image.load(
            ASSETS['playervsplayer']).convert_alpha()
        self.pvb_original = pygame.image.load(
            ASSETS['playervsbagh']).convert_alpha()
        self.pvg_original = pygame.image.load(
            ASSETS['playervsgoat']).convert_alpha()
        self.AvA_original = pygame.image.load(
            ASSETS['AivsAi']).convert_alpha()

    def cache_scaled_assets(self):
        x_width = self.screen_size[0]
        y_height = self.screen_size[1]
        btn_width = x_width * 0.18
        btn_height = y_height * 0.360
        if x_width >= 1000:
            btn_width = 180
            btn_height = 360
        piece_size = int(self.cell_size * 0.55)
        self.bagh_img = pygame.transform.smoothscale(
            self.bagh_img_original, (piece_size, piece_size))
        self.goat_img = pygame.transform.smoothscale(
            self.goat_img_original, (piece_size, piece_size))
        self.bagh_selected = pygame.transform.smoothscale(
            self.bagh_selected_original, (piece_size, piece_size))
        self.goat_selected = pygame.transform.smoothscale(
            self.goat_selected_original, (piece_size, piece_size))
        self.backgroundgradiant_img = pygame.transform.smoothscale(
            self.backgroundgradiant_original, (1920, 1080))
        self.playervsplayer_img = pygame.transform.smoothscale(
            self.pvp_original, (btn_width, btn_height))
        self.playervsbagh_img = pygame.transform.smoothscale(
            self.pvb_original, (btn_width, btn_height))
        self.playervsgoat_img = pygame.transform.smoothscale(
            self.pvg_original, (btn_width, btn_height))
        self.AivsAi = pygame.transform.smoothscale(
            self.AvA_original, (btn_width, btn_height))

    def handle_resize(self, new_size):
        width, height = new_size
        self.screen_size = (width, height)

        # Calculate available space for board (with margins for UI)
        top_margin = 50
        bottom_margin = 150  # For status bar and controls
        left_margin = 50
        right_margin = 300  # For AI panel in replay mode

        available_width = width - left_margin - right_margin
        available_height = height - top_margin - bottom_margin

        # Calculate cell size maintaining square board
        max_cell_from_width = available_width // 5
        max_cell_from_height = available_height // 5
        new_cell_size = min(max_cell_from_width, max_cell_from_height)
        new_cell_size = max(self.min_cell_size, min(
            self.max_cell_size, new_cell_size))

        if new_cell_size != self.cell_size:
            self.cell_size = new_cell_size
            self.initialize_board_data()
            self.cache_scaled_assets()

        # Update board position
        self.update_board_position()

        self.screen = pygame.display.set_mode(
            self.screen_size, pygame.RESIZABLE)

        self.initialize_button_rects()

    def update_board_position(self):
        """Calculate board position to center it on screen with margins."""
        # Calculate margins based on UI needs
        top_margin = 50
        bottom_margin = 150  # Status bar height

        # Available space
        available_height = self.screen_size[1] - top_margin - bottom_margin

        # Center board horizontally
        board_x = (self.screen_size[0] - self.grid_width) // 2

        # Center board vertically in available space
        board_y = top_margin + (available_height - self.grid_height) // 2

        self.board_position = (board_x, board_y)

    def get_board_coords_from_screen(self, screen_x, screen_y):
        """Convert screen coordinates to board surface coordinates."""
        board_x, board_y = self.board_position

        # Check if click is within board area
        if (board_x <= screen_x <= board_x + self.grid_width and
                board_y <= screen_y <= board_y + self.grid_height):
            # Convert to board surface coordinates
            rel_x = screen_x - board_x
            rel_y = screen_y - board_y
            return (rel_x, rel_y)
        return None

    def reset_game(self):
        self.cleanup_ai_thread()
        self.game_state = BitboardGameState()
        self.selected_cell = None
        self.valid_moves = []
        self.state_hash.clear()
        self.ai_initialized = False
        self.ai_is_thinking = False
        self.pending_player_move = None
        self.ai_result_move = None
        self.game_just_reset = True
        self.initial_render_done = False
        self.particles = []
        self.last_move_highlight = None

        # Reset replay state
        self.replay_mode = False
        self.replay_moves = []
        self.replay_index = 0
        self.auto_play = False
        self.replay_game_id = None
        self.replay_timer = 0
        self.ai_suggestions = {}

    def cleanup_ai_thread(self):
        if self.ai_thread and self.ai_thread.is_alive():
            self.ai_thread.join()
        self.ai_thread = None

    def _initialize_ai_async(self):
        try:
            if self.using_agent == minimax_flag:
                self.minimax_agent = AlphaBetaAgent()
            elif self.using_agent == mcts_flag:
                self.mcts_agent = MCTS()
        finally:
            self.ai_initialized = True

    def _ai_worker(self, agent, game_state):
        try:
            if hasattr(agent, "search"):
                move = agent.search(
                    game_state, time_limit=self.time_limit, game_history=self.state_hash.keys())
            else:
                move = agent.get_best_move(
                    game_state, time_limit=self.time_limit, game_history=self.state_hash.keys())
            self.ai_result_move = move
        except Exception as e:
            print(f"AI Error: {e}")
            print(traceback.format_exc())
            self.ai_result_move = None
            exit(1)
        finally:
            self.ai_is_thinking = False

    def should_ai_move(self):
        if self.is_game_over():
            return False
        if not self.ai_initialized:
            return False
        if not self.initial_render_done:
            return False
        if self.current_state == UIState.PLAYING_CVC:
            return True
        if self.current_state == UIState.PLAYING_PVC_GOAT and self.game_state.turn == -1:
            return True
        if self.current_state == UIState.PLAYING_PVC_TIGER and self.game_state.turn == 1:
            return True
        return False

    def update_ai_logic(self):
        if self.ai_thread and not self.ai_thread.is_alive():
            self.ai_thread = None
        if self.move_processed_this_frame or self.pending_player_move:
            return
        is_ai_turn = self.should_ai_move()
        if is_ai_turn and not self.ai_is_thinking and self.ai_result_move is None:
            self.ai_is_thinking = True
            agent = self.minimax_agent if self.using_agent == minimax_flag else self.mcts_agent
            if agent is None:
                self.ai_is_thinking = False
                return
            state_for_ai = self.game_state
            self.ai_thread = threading.Thread(
                target=self._ai_worker, args=(agent, state_for_ai))
            self.ai_thread.start()

    def is_game_over(self):
        is_game_over = self.game_state.is_game_over
        state_key = self.game_state.key
        if self.state_hash[state_key] > 3:
            is_game_over = True
        return is_game_over

    def check_game_over(self):
        if self.is_game_over():
            if self.game_over_timer == 0:
                self.game_over_timer = pygame.time.get_ticks()
                # Auto-save game when it ends
                if self.current_game_mode is not None and not self.replay_mode:
                    result = self.game_state.get_result
                    # Handle draw by repetition
                    state_key = self.game_state.key
                    if self.state_hash[state_key] > 3:
                        winner = "Draw"
                    elif result == Piece_TIGER:
                        winner = "Tiger"
                    elif result == Piece_GOAT:
                        winner = "Goat"
                    else:
                        winner = "Draw"

                    # Save the game
                    save_game(self.game_state, self.current_game_mode, winner)
            elif pygame.time.get_ticks() - self.game_over_timer >= self.game_over_delay:
                self.current_state = UIState.GAME_OVER
                self.game_over_timer = 0

    def cell_to_pixel(self, col, row):
        return col * self.cell_size, row * self.cell_size

    def place_piece(self, pos):
        """Place a piece or select a piece with circular hitbox detection."""
        self.last_move_highlight = None

        is_human_turn = (self.current_state == UIState.PLAYING_PVP) or \
                        (self.current_state == UIState.PLAYING_PVC_GOAT and self.game_state.turn == 1) or \
                        (self.current_state ==
                         UIState.PLAYING_PVC_TIGER and self.game_state.turn == -1)

        if (self.ai_is_thinking or self.is_game_over() or not is_human_turn or
                self.pending_player_move or self.move_processed_this_frame):
            return

        # Convert screen coordinates to board coordinates
        board_coords = self.get_board_coords_from_screen(pos[0], pos[1])
        if board_coords is None:
            return  # Click is outside board area

        board_x, board_y = board_coords

        # Define hitbox radius (adjust this value as needed)
        hitbox_radius = self.cell_size * 0.35  # 35% of cell size, adjust to taste

        # Find the nearest grid position within hitbox radius
        clicked_idx = None
        min_distance = float('inf')

        for row in range(5):
            for col in range(5):
                # Calculate piece center in board coordinates
                piece_x = col * self.cell_size + self.offset
                piece_y = row * self.cell_size + self.offset

                # Calculate distance from click to piece center
                dx = board_x - piece_x
                dy = board_y - piece_y
                distance = (dx * dx + dy * dy) ** 0.5

                # Check if within hitbox and is the closest one
                if distance < hitbox_radius and distance < min_distance:
                    min_distance = distance
                    clicked_idx = col + row * self.grid_cols

        # If no piece was clicked within radius, return
        if clicked_idx is None:
            return

        # Now we have the clicked grid index, proceed with game logic
        col = clicked_idx % 5
        row = clicked_idx // 5

        piece = None
        if self.game_state.turn == 1:
            if self.game_state.tigers_bb & (1 << clicked_idx):
                piece = 1
        else:
            if self.game_state.goats_bb & (1 << clicked_idx):
                piece = -1

        move = None
        if self.selected_cell is None:
            # Goat placement phase
            if self.game_state.turn == -1 and self.game_state.goats_to_place > 0:
                move = (clicked_idx, clicked_idx)
                if move in self.game_state.get_legal_moves():
                    self.pending_player_move = move
                    x, y = self.cell_to_pixel(col, row)
                    # Create particles in screen coordinates
                    screen_x = self.board_position[0] + x + self.offset
                    screen_y = self.board_position[1] + y + self.offset
                    self.particles.append(ParticleEffect(
                        screen_x, screen_y, COLORS['accent']))
                    return
            # Select piece
            elif piece == self.game_state.turn:
                self.selected_cell = clicked_idx
                self.valid_moves = [
                    m for m in self.game_state.get_legal_moves() if m[0] == clicked_idx]
        else:
            # Move selected piece
            move = (self.selected_cell, clicked_idx)
            if move in self.game_state.get_legal_moves():
                self.pending_player_move = move
                self.last_move_highlight = (self.selected_cell, clicked_idx)
                x, y = self.cell_to_pixel(col, row)
                # Create particles in screen coordinates
                screen_x = self.board_position[0] + x + self.offset
                screen_y = self.board_position[1] + y + self.offset
                self.particles.append(ParticleEffect(
                    screen_x, screen_y, (220, 180, 100)))
            self.selected_cell = None
            self.valid_moves = []

    def update_game_logic(self):
        current_frame = pygame.time.get_ticks()
        move = None
        if self.pending_player_move and not self.move_processed_this_frame:
            move = self.pending_player_move
            self.pending_player_move = None
            self.game_state.make_move(move)
            self.state_hash_update()
            self.move_processed_this_frame = True
            self.last_move_frame = current_frame
            return
        if self.ai_result_move and not self.move_processed_this_frame:
            if self.last_move_frame and current_frame - self.last_move_frame < 100:
                return
            move = self.ai_result_move
            self.ai_result_move = None
            self.last_move_highlight = move
            if move:
                to_idx = move[1]
                row, col = divmod(to_idx, 5)
                x, y = self.cell_to_pixel(col, row)
                # Create particles in screen coordinates (board_position + board coordinates)
                if self.board_surface:
                    screen_x = self.board_position[0] + x + self.offset
                    screen_y = self.board_position[1] + y + self.offset
                else:
                    screen_x = x + self.offset
                    screen_y = y + self.offset
                self.particles.append(ParticleEffect(
                    screen_x, screen_y, (255, 200, 50)))
            self.game_state.make_move(move)
            self.state_hash_update()
            self.move_processed_this_frame = True
            self.last_move_frame = current_frame

    def update(self):
        self.move_processed_this_frame = False
        self.event_handler.handle_events()
        self.check_for_resize()

        if self.pending_resize:
            self.screen.fill(COLORS["menu_bg"])
            font_size = min(32, int(self.screen.get_width() * 0.05))
            self.renderer.draw_text(
                "Resizing...", font_size, self.screen.get_width() // 2, self.screen.get_height() // 2, COLORS["white"])

        elif self.current_state == UIState.MAIN_MENU:
            self.renderer.render_main_menu()
        elif self.current_state == UIState.MODE_SELECT:
            self.renderer.render_mode_select()
        elif self.current_state == UIState.ANALYSIS_MODE:
            self.renderer.render_analysis_mode()
        elif self.current_state == UIState.REPLAYING:
            # Update board position in case window was resized
            self.update_board_position()
            # Handle auto-play for replay
            if self.auto_play:
                current_time = pygame.time.get_ticks()
                if current_time - self.replay_timer >= self.replay_auto_play_delay:
                    if self.replay_index < len(self.replay_moves):
                        self.step_replay_forward()
                        self.replay_timer = current_time
            self.renderer.render_replay_mode()
        elif self.current_state in [UIState.PLAYING_PVP, UIState.PLAYING_PVC_GOAT, UIState.PLAYING_PVC_TIGER, UIState.PLAYING_CVC]:
            # Update board position in case window was resized
            self.update_board_position()
            self.update_game_logic()
            self.update_ai_logic()
            self.check_game_over()
            self.renderer.render_game()
            if self.game_just_reset:
                self.initial_render_done = True
                self.game_just_reset = False
        elif self.current_state == UIState.GAME_OVER:
            self.renderer.render_game_over()
        elif self.current_state == UIState.EXITING:
            self.running = False

        pygame.display.flip()
        self.clock.tick(self.tick_speed)

    def load_game_for_replay(self, game_id: int):
        """Load a game from database for replay."""
        game_data = get_game_by_id(game_id)
        if not game_data:
            return False

        # Reset to initial state
        self.game_state = BitboardGameState()
        self.reset_game()

        # Store replay data
        self.replay_moves = game_data["moves"]
        self.replay_index = 0
        self.replay_game_id = game_id
        self.replay_mode = True
        self.auto_play = False
        self.ai_suggestions = {}

        # Clear AI state for replay
        self.cleanup_ai_thread()
        self.ai_initialized = False

        return True

    def step_replay_forward(self):
        """Execute next move in replay sequence."""
        if self.replay_index >= len(self.replay_moves):
            self.auto_play = False  # Stop auto-play when reached end
            return

        move_data = self.replay_moves[self.replay_index]
        move = (move_data["from"], move_data["to"])

        # Make the move (game_state.make_move handles capture info internally)
        self.game_state.make_move(move)
        self.replay_index += 1

        # Clear cached suggestion for this position
        if self.replay_index in self.ai_suggestions:
            del self.ai_suggestions[self.replay_index]

    def step_replay_backward(self):
        """Undo last move in replay sequence."""
        if self.replay_index <= 0:
            return

        self.game_state.unmake_move()
        self.replay_index -= 1

        # Clear cached suggestion for this position
        if self.replay_index in self.ai_suggestions:
            del self.ai_suggestions[self.replay_index]

    def toggle_replay_auto_play(self):
        """Toggle auto-play mode for replay."""
        self.auto_play = not self.auto_play
        if self.auto_play:
            self.replay_timer = pygame.time.get_ticks()

    def get_ai_suggestion_for_position(self):
        """Get AI suggested move for current replay position."""
        # Check cache first
        if self.replay_index in self.ai_suggestions:
            return self.ai_suggestions[self.replay_index]

        # Don't suggest if game is over
        if self.game_state.is_game_over:
            return None

        try:
            # Determine which agent to use based on game mode
            # For now, default to minimax, but could be based on original game mode
            if not self.ai_initialized:
                self.minimax_agent = AlphaBetaAgent()
                self.ai_initialized = True

            # Get suggested move with short time limit for replay
            suggested_move = self.minimax_agent.get_best_move(
                self.game_state,
                time_limit=0.5,
                game_history=[]
            )

            # Cache the suggestion
            self.ai_suggestions[self.replay_index] = suggested_move
            return suggested_move
        except Exception as e:
            print(f"Error getting AI suggestion: {e}")
            return None

    def run(self):
        while self.running:
            self.update()
        self.cleanup_ai_thread()
        pygame.quit()
