import threading
from collections import defaultdict
from enum import Enum
import traceback
import pygame
from bagchal import *
from negamax import AlphaBetaAgent
from mcts import MCTS

mcts_flag, minimax_flag = 0, 1

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


class ParticleEffect:
    """Simple particle effect for visual feedback"""
    def __init__(self, x, y, color, count=10):
        self.particles = []
        for _ in range(count):
            import random
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(2, 6)
            self.particles.append({
                'x': x,
                'y': y,
                'vx': speed * pygame.math.Vector2(1, 0).rotate_rad(angle).x,
                'vy': speed * pygame.math.Vector2(1, 0).rotate_rad(angle).y,
                'life': 30,
                'color': color
            })

    def update(self):
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.3  # Gravity
            p['life'] -= 1
        self.particles = [p for p in self.particles if p['life'] > 0]

    def draw(self, screen):
        for p in self.particles:
            alpha = int(255 * (p['life'] / 30))
            size = max(2, int(4 * (p['life'] / 30)))
            pygame.draw.circle(screen, p['color'], (int(p['x']), int(p['y'])), size)


class Game:
    def __init__(self, game_state,
                 caption="Bagchal - The Tiger and Goats Game",
                 cell_size=200,
                 tick_speed=60):  # Increased for smoother animations
        pygame.init()
        pygame.display.set_caption(caption)

        self.game_state: BitboardGameState = game_state
        self.cell_size = cell_size

        self.current_state = UIState.MAIN_MENU
        self.running = True

        self.pending_player_move = None

        self.using_agent = minimax_flag

        self.ai_thread = None
        self.time_limit = 0.6
        self.ai_is_thinking = False
        self.ai_result_move = None

        self.game_over_timer = 0
        self.game_over_delay = 2500

        self.initialize_board_data()
        self.selected_cell = None
        self.valid_moves = []  # Store valid moves for highlighting

        self.initialize_pygame_state(tick_speed)
        self.load_assets()

        self.state_hash = defaultdict(int)

        self.ai_initialized = False
        self.game_just_reset = False
        self.initial_render_done = False
        self.move_processed_this_frame = False
        self.last_move_frame = None

        # Animation and effects
        self.particles = []
        self.piece_animations = {}  # For smooth piece movement
        self.button_hover = None
        self.ai_pulse = 0  # For pulsing AI indicator
        self.last_move_highlight = None  # Highlight last move

    def state_hash_update(self):
        state_key = self.game_state.key
        self.state_hash[state_key] += 1

    def initialize_board_data(self):
        self.grid_width = self.cell_size * 5
        self.grid_height = self.cell_size * 5
        self.screen_size = (self.grid_width, self.grid_height + 100)  # Extra space for status

        self.grid_cols = 5
        self.grid_rows = 5

        self.offset = self.cell_size // 2
        self.board_width = self.grid_width - self.cell_size
        self.board_height = self.grid_height - self.cell_size

    def initialize_pygame_state(self, tick_speed):
        self.screen = pygame.display.set_mode(self.screen_size)
        self.clock = pygame.time.Clock()
        self.tick_speed = tick_speed

    def load_assets(self):
        self.bagh_img = pygame.image.load(ASSETS["bagh"]).convert_alpha()
        self.goat_img = pygame.image.load(ASSETS["goat"]).convert_alpha()
        self.bagh_selected = pygame.image.load(ASSETS["bagh_sel"]).convert_alpha()
        self.goat_selected = pygame.image.load(ASSETS["goat_sel"]).convert_alpha()

        # Slightly larger pieces for better visibility
        piece_size = int(self.cell_size * 0.55)
        self.bagh_img = pygame.transform.smoothscale(self.bagh_img, (piece_size, piece_size))
        self.goat_img = pygame.transform.smoothscale(self.goat_img, (piece_size, piece_size))
        self.bagh_selected = pygame.transform.smoothscale(self.bagh_selected, (piece_size, piece_size))
        self.goat_selected = pygame.transform.smoothscale(self.goat_selected, (piece_size, piece_size))

    def reset_game(self):
        self.cleanup_ai_thread()

        game_state = BitboardGameState()
        self.game_state = game_state
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

    def handle_main_menu_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.current_state = UIState.EXITING
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                play_btn_rect = pygame.Rect(277, 350, 200, 60)
                exit_btn_rect = pygame.Rect(277, 450, 200, 60)

                if play_btn_rect.collidepoint(event.pos):
                    self.current_state = UIState.MODE_SELECT
                elif exit_btn_rect.collidepoint(event.pos):
                    self.current_state = UIState.EXITING

    def handle_mode_select_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.current_state = UIState.EXITING
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pvp_rect = pygame.Rect(127, 300, 550, 60)
                pvc_goat_rect = pygame.Rect(107, 380, 600, 60)
                pvc_tiger_rect = pygame.Rect(107, 460, 600, 60)
                cvc_rect = pygame.Rect(87, 540, 650, 60)

                if pvp_rect.collidepoint(event.pos):
                    self.reset_game()
                    self.current_state = UIState.PLAYING_PVP
                elif pvc_goat_rect.collidepoint(event.pos):
                    self.reset_game()
                    self.current_state = UIState.PLAYING_PVC_GOAT
                    ai_thread = threading.Thread(target=self._initialize_ai_async)
                    ai_thread.daemon = True
                    ai_thread.start()
                elif pvc_tiger_rect.collidepoint(event.pos):
                    self.reset_game()
                    self.current_state = UIState.PLAYING_PVC_TIGER
                    ai_thread = threading.Thread(target=self._initialize_ai_async)
                    ai_thread.daemon = True
                    ai_thread.start()
                elif cvc_rect.collidepoint(event.pos):
                    self.reset_game()
                    self.current_state = UIState.PLAYING_CVC
                    ai_thread = threading.Thread(target=self._initialize_ai_async)
                    ai_thread.daemon = True
                    ai_thread.start()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            self.cleanup_ai_thread()
            self.current_state = UIState.MAIN_MENU

    def handle_game_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.current_state = UIState.EXITING
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.current_state == UIState.PLAYING_PVP or \
                   (self.current_state == UIState.PLAYING_PVC_GOAT and self.game_state.turn == Piece_TIGER) or \
                   (self.current_state == UIState.PLAYING_PVC_TIGER and self.game_state.turn == Piece_GOAT):
                    self.place_piece(event.pos)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            self.cleanup_ai_thread()
            self.current_state = UIState.MAIN_MENU

    def handle_game_over_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.current_state = UIState.EXITING
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.current_state = UIState.MODE_SELECT
                elif event.key == pygame.K_ESCAPE:
                    self.current_state = UIState.MAIN_MENU

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
            if hasattr(agent, "search"):  # MCTS
                move = agent.search(game_state, time_limit=self.time_limit, game_history=self.state_hash.keys())
                print(f"Total Simulations: {agent.simulations_run}")
                print(f"Goat Wins: {agent.goat_wins}", f"Tiger Wins: {agent.tiger_wins}", f"Draws: {agent.draws}")
                agent.visualize_tree(max_depth=1)
            else:  # Minimax
                move = agent.get_best_move(game_state, time_limit=self.time_limit, game_history=self.state_hash.keys())

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
        if self.current_state == UIState.PLAYING_PVC_GOAT and self.game_state.turn == Piece_GOAT:
            return True
        if self.current_state == UIState.PLAYING_PVC_TIGER and self.game_state.turn == Piece_TIGER:
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
            self.ai_thread = threading.Thread(target=self._ai_worker, args=(agent, state_for_ai))
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
                print("Game Over")
                print(self.game_state)
                result = BitboardGameState.piece[self.game_state.get_result] + " Won" if self.game_state.get_result else "Draw"
                print("Result:", result)
            elif pygame.time.get_ticks() - self.game_over_timer >= self.game_over_delay:
                self.current_state = UIState.GAME_OVER
                self.game_over_timer = 0

    def draw_board(self):
        """Enhanced board drawing with shadows and gradients"""
        # Draw board background
        board_rect = pygame.Rect(self.offset, self.offset, self.board_width, self.board_height)
        pygame.draw.rect(self.screen, COLORS["board_light"], board_rect)

        # Draw shadow effect
        shadow_offset = 5
        shadow_rect = board_rect.inflate(shadow_offset * 2, shadow_offset * 2)
        pygame.draw.rect(self.screen, (0, 0, 0, 30), shadow_rect, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["board"], board_rect, border_radius=8)

        # Draw grid lines with varying thickness
        line_color = COLORS["board_light"]

        # Main diagonals (thicker)
        pygame.draw.line(self.screen, line_color,
                        (self.offset, self.offset),
                        (self.board_width + self.offset, self.board_height + self.offset), 4)
        pygame.draw.line(self.screen, line_color,
                        (self.offset, self.board_height + self.offset),
                        (self.board_width + self.offset, self.offset), 4)

        # Half diagonals
        pygame.draw.line(self.screen, line_color,
                        (self.offset, self.board_height // 2 + self.offset),
                        (self.board_width // 2 + self.offset, self.offset), 3)
        pygame.draw.line(self.screen, line_color,
                        (self.offset, self.board_height // 2 + self.offset),
                        (self.board_width // 2 + self.offset, self.board_height + self.offset), 3)
        pygame.draw.line(self.screen, line_color,
                        (self.board_width + self.offset, self.board_height // 2 + self.offset),
                        (self.board_width // 2 + self.offset, self.offset), 3)
        pygame.draw.line(self.screen, line_color,
                        (self.board_width + self.offset, self.board_height // 2 + self.offset),
                        (self.board_width // 2 + self.offset, self.board_height + self.offset), 3)

        # Vertical and horizontal lines
        for i in range(self.grid_cols):
            pygame.draw.line(self.screen, line_color,
                           (i * self.cell_size + self.offset, self.offset),
                           (i * self.cell_size + self.offset, self.grid_height - self.cell_size + self.offset), 3)
        for i in range(self.grid_rows):
            pygame.draw.line(self.screen, line_color,
                           (self.offset, i * self.cell_size + self.offset),
                           (self.grid_width - self.cell_size + self.offset, i * self.cell_size + self.offset), 3)

        # Draw intersection points
        for row in range(5):
            for col in range(5):
                x = col * self.cell_size + self.offset
                y = row * self.cell_size + self.offset
                pygame.draw.circle(self.screen, COLORS["accent"], (x, y), 6)
                pygame.draw.circle(self.screen, COLORS["board"], (x, y), 4)

    def cell_to_pixel(self, col, row):
        return col * self.cell_size, row * self.cell_size

    def draw_valid_moves(self):
        """Highlight valid moves for selected piece"""
        if not self.valid_moves:
            return

        for move in self.valid_moves:
            to_idx = move[1]
            row, col = divmod(to_idx, 5)
            x = col * self.cell_size + self.offset
            y = row * self.cell_size + self.offset

            # Pulsing effect
            pulse = abs(pygame.time.get_ticks() % 1000 - 500) / 500
            radius = int(15 + 5 * pulse)

            # Draw with transparency
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, COLORS["valid_move"], (radius, radius), radius)
            self.screen.blit(s, (x - radius, y - radius))

    def draw_pieces(self):
        """Enhanced piece drawing with shadows and selection highlight"""
        tiger_positions = extract_indices_fast(self.game_state.tigers_bb)
        goat_positions = extract_indices_fast(self.game_state.goats_bb)

        # Draw shadows first
        shadow_offset = 3
        for positions, is_tiger in [(tiger_positions, True), (goat_positions, False)]:
            for i in positions:
                row, col = divmod(i, 5)
                x, y = self.cell_to_pixel(col, row)
                x, y = x + self.offset, y + self.offset

                # Shadow
                shadow_surf = pygame.Surface((self.cell_size // 2, self.cell_size // 2), pygame.SRCALPHA)
                pygame.draw.circle(shadow_surf, (0, 0, 0, 60),
                                 (self.cell_size // 4, self.cell_size // 4),
                                 self.cell_size // 5)
                self.screen.blit(shadow_surf, (x - self.cell_size // 4 + shadow_offset,
                                              y - self.cell_size // 4 + shadow_offset))

        # Draw selection highlight
        if self.selected_cell is not None:
            row, col = divmod(self.selected_cell, 5)
            x, y = self.cell_to_pixel(col, row)
            x, y = x + self.offset, y + self.offset

            # Animated selection ring
            pulse = abs(pygame.time.get_ticks() % 800 - 400) / 400
            radius = int(50 + 10 * pulse)
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, COLORS["selected"], (radius, radius), radius, 4)
            self.screen.blit(s, (x - radius, y - radius))

        # Draw pieces
        for i in tiger_positions:
            row, col = divmod(i, 5)
            x, y = self.cell_to_pixel(col, row)
            x, y = x + self.offset - self.cell_size // 4, y + self.offset - self.cell_size // 4
            img = self.bagh_selected if i == self.selected_cell else self.bagh_img
            self.screen.blit(img, (x, y))

        for i in goat_positions:
            row, col = divmod(i, 5)
            x, y = self.cell_to_pixel(col, row)
            x, y = x + self.offset - self.cell_size // 4, y + self.offset - self.cell_size // 4
            img = self.goat_selected if i == self.selected_cell else self.goat_img
            self.screen.blit(img, (x, y))

    def place_piece(self, pos):
        is_human_turn = (self.current_state == UIState.PLAYING_PVP) or (
            self.current_state == UIState.PLAYING_PVC_GOAT and self.game_state.turn == Piece_TIGER) or (
            self.current_state == UIState.PLAYING_PVC_TIGER and self.game_state.turn == Piece_GOAT)

        if (self.ai_is_thinking or self.is_game_over() or
            not is_human_turn or self.pending_player_move or
                self.move_processed_this_frame):
            return

        mouse_x, mouse_y = pos
        col, row = mouse_x // self.cell_size, mouse_y // self.cell_size
        if col >= 5 or row >= 5:
            return

        idx = col + row * self.grid_cols
        piece = None

        if self.game_state.turn == Piece_TIGER:
            if self.game_state.tigers_bb & (1 << idx):
                piece = Piece_TIGER
        else:
            if self.game_state.goats_bb & (1 << idx):
                piece = Piece_GOAT

        move = None

        if self.selected_cell is None:
            if self.game_state.turn == Piece_GOAT and self.game_state.goats_to_place > 0:
                move = (idx, idx)
                if move in self.game_state.get_legal_moves():
                    self.pending_player_move = move
                    # Add particle effect
                    x, y = self.cell_to_pixel(col, row)
                    self.particles.append(ParticleEffect(x + self.offset, y + self.offset, COLORS["accent"]))
                    return
            elif piece == self.game_state.turn:
                self.selected_cell = idx
                self.valid_moves = [m for m in self.game_state.get_legal_moves() if m[0] == idx]
        else:
            move = (self.selected_cell, idx)
            if move in self.game_state.get_legal_moves():
                self.pending_player_move = move
                self.last_move_highlight = (self.selected_cell, idx)
                # Add particle effect
                x, y = self.cell_to_pixel(col, row)
                self.particles.append(ParticleEffect(x + self.offset, y + self.offset, COLORS["accent"]))
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

            # Add particle effect for AI move
            if move:
                to_idx = move[1]
                row, col = divmod(to_idx, 5)
                x, y = self.cell_to_pixel(col, row)
                self.particles.append(ParticleEffect(x + self.offset, y + self.offset, COLORS["ai_thinking"]))

            self.game_state.make_move(move)
            self.state_hash_update()
            self.move_processed_this_frame = True
            self.last_move_frame = current_frame

    def draw_status(self):
        """Enhanced status display with icons and better layout"""
        status_y = self.grid_height + 10

        # Background panel
        panel_rect = pygame.Rect(0, self.grid_height, self.grid_width, 100)
        pygame.draw.rect(self.screen, COLORS["board"], panel_rect)

        font = pygame.font.SysFont(None, 36)

        # Turn indicator
        turn_text = "Tiger's Turn" if self.game_state.turn == Piece_TIGER else "Goat's Turn"
        turn_color = (255, 100, 50) if self.game_state.turn == Piece_TIGER else (100, 200, 100)
        turn_surf = font.render(turn_text, True, turn_color)
        self.screen.blit(turn_surf, (20, status_y))

        # Stats
        stats_font = pygame.font.SysFont(None, 32)
        goat_text = stats_font.render(f"Goats Left: {self.game_state.goats_to_place}", True, COLORS["white"])
        eaten_text = stats_font.render(f"Goats Eaten: {self.game_state.goats_eaten}", True, COLORS["white"])
        trapped_text = stats_font.render(f"Tigers Trapped: {self.game_state.trapped_tiger_count}", True, COLORS["white"])

        self.screen.blit(goat_text, (20, status_y + 35))
        self.screen.blit(eaten_text, (280, status_y + 35))
        self.screen.blit(trapped_text, (550, status_y + 35))

    def draw_text(self, text, size, x, y, color=None):
        if color is None:
            color = COLORS["text"]
        try:
            font = pygame.font.Font(ASSETS["font"], size)
        except:
            font = pygame.font.SysFont(None, size)
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(center=(x, y))
        self.screen.blit(text_surface, text_rect)

    def draw_button(self, text, x, y, w, h):
        """Enhanced button with hover effects and shadows"""
        rect = pygame.Rect(x, y, w, h)
        mouse_pos = pygame.mouse.get_pos()

        is_hovered = rect.collidepoint(mouse_pos)

        # Shadow
        shadow_rect = rect.inflate(4, 4)
        shadow_rect.y += 3
        pygame.draw.rect(self.screen, (0, 0, 0, 50), shadow_rect, border_radius=10)

        # Button background
        button_color = COLORS["button_hover"] if is_hovered else COLORS["button"]
        pygame.draw.rect(self.screen, button_color, rect, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["accent"], rect, 3, border_radius=10)

        # Button text
        self.draw_text(text, 32, x + w // 2, y + h // 2, COLORS["white"])
        return rect

    def render_main_menu(self):
        """Enhanced main menu with gradient background"""
        # Gradient background
        for i in range(self.screen_size[1]):
            ratio = i / self.screen_size[1]
            color = tuple(int(COLORS["menu_bg"][j] + (COLORS["mode_bg"][j] - COLORS["menu_bg"][j]) * ratio) for j in range(3))
            pygame.draw.line(self.screen, color, (0, i), (self.screen_size[0], i))

        self.draw_text("Bagchal", 72, self.screen_size[0] // 2, 150, COLORS["accent"])
        self.draw_text("The Tiger and Goats Game", 28, self.screen_size[0] // 2, 220, COLORS["white"])

        self.draw_button("Play", 277, 350, 200, 60)
        self.draw_button("Exit", 277, 450, 200, 60)

    def render_mode_select(self):
        """Enhanced mode selection with better layout"""
        # Gradient background
        for i in range(self.screen_size[1]):
            ratio = i / self.screen_size[1]
            color = tuple(int(COLORS["mode_bg"][j] + (COLORS["menu_bg"][j] - COLORS["mode_bg"][j]) * ratio) for j in range(3))
            pygame.draw.line(self.screen, color, (0, i), (self.screen_size[0], i))

        self.draw_text("Select Game Mode", 64, self.screen_size[0] // 2, 120, COLORS["accent"])

        self.draw_button("Player vs Player", 127, 300, 550, 60)
        self.draw_button("Player vs Goat AI", 107, 380, 600, 60)
        self.draw_button("Player vs Tiger AI", 107, 460, 600, 60)
        self.draw_button("Computer vs Computer", 87, 540, 650, 60)

        self.draw_text("Press ESC to go back", 24, self.screen_size[0] // 2, 650, COLORS["white"])

    def render_game(self):
        """Enhanced game rendering with all visual effects"""
        self.screen.fill(COLORS["bg"])
        self.draw_board()

        # Draw valid move indicators
        self.draw_valid_moves()

        # Draw last move highlight
        if self.last_move_highlight:
            from_idx, to_idx = self.last_move_highlight
            for idx in [from_idx, to_idx]:
                row, col = divmod(idx, 5)
                x = col * self.cell_size + self.offset
                y = row * self.cell_size + self.offset

                # Fade over time
                alpha = max(0, 150 - (pygame.time.get_ticks() - (self.last_move_frame or 0)) // 10)
                if alpha > 0:
                    s = pygame.Surface((40, 40), pygame.SRCALPHA)
                    pygame.draw.circle(s, (255, 200, 100, alpha), (20, 20), 20, 3)
                    self.screen.blit(s, (x - 20, y - 20))

        self.draw_pieces()
        self.draw_status()

        # Update and draw particles
        for particle in self.particles[:]:
            particle.update()
            particle.draw(self.screen)
            if not particle.particles:
                self.particles.remove(particle)

        # AI thinking indicator with pulsing effect
        if self.ai_is_thinking:
            self.ai_pulse = (self.ai_pulse + 0.1) % (2 * 3.14159)
            alpha = int(128 + 127 * abs(pygame.math.Vector2(1, 0).rotate_rad(self.ai_pulse).x))

            # Create semi-transparent overlay
            overlay = pygame.Surface((300, 60), pygame.SRCALPHA)
            pygame.draw.rect(overlay, (40, 40, 60, 200), overlay.get_rect(), border_radius=10)
            pygame.draw.rect(overlay, (COLORS["ai_thinking"][0], COLORS["ai_thinking"][1], COLORS["ai_thinking"][2], alpha),
                           overlay.get_rect(), 3, border_radius=10)

            self.screen.blit(overlay, (self.grid_width // 2 - 150, 20))

            # Animated text
            font = pygame.font.SysFont(None, 32)
            dots = "." * (int(pygame.time.get_ticks() / 300) % 4)
            text = font.render(f"AI Thinking{dots}", True, COLORS["ai_thinking"])
            text_rect = text.get_rect(center=(self.grid_width // 2, 50))
            self.screen.blit(text, text_rect)

    def render_game_over(self):
        """Enhanced game over screen with animations"""
        pieces = {-1: "Goat", 1: "Tiger"}

        # Dark overlay with fade-in effect
        fade_alpha = min(255, (pygame.time.get_ticks() - self.game_over_timer + self.game_over_delay) // 3)
        overlay = pygame.Surface(self.screen_size)
        overlay.fill(COLORS["game_over_bg"])
        overlay.set_alpha(fade_alpha)
        self.screen.blit(overlay, (0, 0))

        # Animated result display
        scale = min(1.0, fade_alpha / 255)

        self.draw_text("Game Over!", int(72 * scale),
                      self.screen_size[0] // 2,
                      self.screen_size[1] // 2 - 200,
                      COLORS["accent"])

        result_text = f"{pieces[self.game_state.get_result]} Won!" if self.game_state.get_result else "It's a Draw!"
        result_color = (255, 150, 50) if self.game_state.get_result == 1 else (100, 255, 150) if self.game_state.get_result == -1 else COLORS["white"]

        self.draw_text(result_text, int(48 * scale),
                      self.screen_size[0] // 2,
                      self.screen_size[1] // 2 - 100,
                      result_color)

        # Pulsing instructions
        pulse = abs(pygame.time.get_ticks() % 1500 - 750) / 750
        instruction_alpha = int(150 + 105 * pulse)
        instruction_color = tuple(list(COLORS["white"][:3]) + [instruction_alpha])

        self.draw_text("Press SPACE to play again", 32,
                      self.screen_size[0] // 2,
                      self.screen_size[1] // 2 + 50,
                      COLORS["white"])
        self.draw_text("Press ESC for main menu", 32,
                      self.screen_size[0] // 2,
                      self.screen_size[1] // 2 + 100,
                      COLORS["white"])

        # Display game stats
        stats_y = self.screen_size[1] // 2 + 180
        stats_font_size = 28
        self.draw_text(f"Goats Eaten: {self.game_state.goats_eaten}", stats_font_size,
                      self.screen_size[0] // 2 - 150, stats_y, COLORS["white"])
        self.draw_text(f"Tigers Trapped: {self.game_state.trapped_tiger_count}", stats_font_size,
                      self.screen_size[0] // 2 + 150, stats_y, COLORS["white"])

    def update(self):
        self.move_processed_this_frame = False

        # Handle events based on current state
        if self.current_state == UIState.MAIN_MENU:
            self.handle_main_menu_events()
            self.render_main_menu()

        elif self.current_state == UIState.MODE_SELECT:
            self.handle_mode_select_events()
            self.render_mode_select()

        elif self.current_state in [UIState.PLAYING_PVP, UIState.PLAYING_PVC_GOAT,
                                    UIState.PLAYING_PVC_TIGER, UIState.PLAYING_CVC]:
            self.handle_game_events()
            self.update_game_logic()
            self.update_ai_logic()
            self.check_game_over()
            self.render_game()

            if self.game_just_reset:
                self.initial_render_done = True
                self.game_just_reset = False

        elif self.current_state == UIState.GAME_OVER:
            self.handle_game_over_events()
            self.render_game_over()

        elif self.current_state == UIState.EXITING:
            self.running = False

        pygame.display.flip()
        self.clock.tick(self.tick_speed)

    def run(self):
        """Main game loop"""
        while self.running:
            self.update()
        self.cleanup_ai_thread()
        pygame.quit()
