from collections import defaultdict
from enum import Enum
import pygame
from bagchal import Piece
from alphabeta import MinimaxAgent
from mcts import MCTS

COLORS = {
    "bg": "antiquewhite",
    "board": "gray",
    "text": "black",
    "menu_bg": "lightblue",
    "mode_bg": "purple",
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


# cell_size -> cell_size
# reset_game -> reset_game
class Game:
    def __init__(self, game_state,
                 caption="bagchal",
                 cell_size=200,
                 tick_speed=30):
        pygame.init()
        pygame.display.set_caption(caption)

        self.game_state = game_state
        self.cell_size = cell_size

        self.current_state = UIState.MAIN_MENU
        self.running = True

        # AI agent (initialized when needed)
        self.minimax_agent = None
        self.mcts_agent = None
        self.ai_move_timer = 0
        self.ai_move_delay = 200  # milliseconds

        # Game over state
        self.game_over_timer = 0
        self.game_over_delay = 5000  # milliseconds

        self.initialize_board_data()
        self.selected_cell = None

        self.initialize_pygame_state(tick_speed)
        self.load_assets()

        self.remove_later_state_hash = defaultdict(int)

    def remove_later_state_hash_update(self):
        state_key = self.game_state.key()
        if state_key in self.remove_later_state_hash:
            self.remove_later_state_hash[state_key] += 1
        else:
            self.remove_later_state_hash[state_key] = 1

    def initialize_board_data(self):

        self.grid_width = self.cell_size * 5
        self.grid_height = self.cell_size * 5
        self.screen_size = (self.grid_width, self.grid_height)

        self.grid_cols = self.grid_width // self.cell_size
        self.grid_rows = self.grid_height // self.cell_size

        self.offset = self.cell_size // 2  # for drawing the lines
        self.board_width = self.grid_width - self.cell_size
        self.board_height = self.grid_height - self.cell_size

    def initialize_pygame_state(self, tick_speed):
        # Pygame State
        self.screen = pygame.display.set_mode(self.screen_size)
        self.clock = pygame.time.Clock()
        self.tick_speed = tick_speed

    def load_assets(self):
        # loading the images
        self.bagh_img = pygame.image.load(ASSETS["bagh"]).convert_alpha()
        self.goat_img = pygame.image.load(ASSETS["goat"]).convert_alpha()

        # loading images for select
        self.bagh_selected = pygame.image.load(
            ASSETS["bagh_sel"]).convert_alpha()
        self.goat_selected = pygame.image.load(
            ASSETS["goat_sel"]).convert_alpha()

        # resizing to make smol
        self.bagh_img = pygame.transform.smoothscale(
            self.bagh_img, (self.cell_size//2, self.cell_size//2))
        self.goat_img = pygame.transform.smoothscale(
            self.goat_img, (self.cell_size//2, self.cell_size//2))

        self.bagh_selected = pygame.transform.smoothscale(
            self.bagh_selected, (int(self.cell_size * 0.5), int(self.cell_size * 0.5)))
        self.goat_selected = pygame.transform.smoothscale(
            self.goat_selected, (int(self.cell_size * 0.5), int(self.cell_size * 0.5)))

    def reset_game(self):
        self.game_state.reset()
        self.selected_cell = None
        self.remove_later_state_hash = defaultdict(int)

    def handle_main_menu_events(self):
        """Handle events specific to main menu"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.current_state = UIState.EXITING
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check button clicks
                play_btn_rect = pygame.Rect(277, 350, 200, 60)
                exit_btn_rect = pygame.Rect(277, 450, 200, 60)

                if play_btn_rect.collidepoint(event.pos):
                    self.current_state = UIState.MODE_SELECT
                elif exit_btn_rect.collidepoint(event.pos):
                    self.current_state = UIState.EXITING

    def handle_mode_select_events(self):
        """Handle events for mode selection"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.current_state = UIState.EXITING
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pvp_rect = pygame.Rect(127, 350, 550, 60)
                pvc_goat_rect = pygame.Rect(107, 450, 600, 60)
                pvc_tiger_rect = pygame.Rect(107, 550, 600, 60)
                cvc_rect = pygame.Rect(87, 650, 650, 60)

                if pvp_rect.collidepoint(event.pos):
                    self.reset_game()
                    self.current_state = UIState.PLAYING_PVP

                elif pvc_goat_rect.collidepoint(event.pos):

                    self.reset_game()
                    # this performs surprisingly well
                    # self.minimax_agent = MinimaxAgent(depth=2)
                    self.mcts_agent = MCTS(
                        initial_state=self.game_state, time_limit=0.5)
                    self.current_state = UIState.PLAYING_PVC_GOAT
                    # Initialize AI timer to current time so it waits before first move
                    self.ai_move_timer = pygame.time.get_ticks()

                elif pvc_tiger_rect.collidepoint(event.pos):

                    self.reset_game()
                    # self.minimax_agent = MinimaxAgent(depth=2)
                    self.mcts_agent = MCTS(
                        initial_state=self.game_state, max_simulations=5)
                    self.current_state = UIState.PLAYING_PVC_TIGER
                    # Initialize AI timer to current time so it waits before first move
                    self.ai_move_timer = pygame.time.get_ticks()

                elif cvc_rect.collidepoint(event.pos):

                    self.reset_game()
                    # self.minimax_agent = MinimaxAgent(depth=2)
                    # Early Game
                    self.mcts_agent = MCTS(
                        initial_state=self.game_state, time_limit=0.5)
                    self.current_state = UIState.PLAYING_CVC
                    # Initialize AI timer to current time so it waits before first move
                    # self.ai_move_timer = pygame.time.get_ticks()

        # ESC to go back to main menu
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            self.current_state = UIState.MAIN_MENU

    def handle_game_events(self):
        """Handle events during gameplay"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.current_state = UIState.EXITING
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.current_state == UIState.PLAYING_PVP or \
                   (self.current_state == UIState.PLAYING_PVC_GOAT and self.game_state.turn == Piece.TIGER) or \
                   (self.current_state == UIState.PLAYING_PVC_TIGER and self.game_state.turn == Piece.GOAT):
                    self.place_piece(event.pos)
                    self.game_state.update_tiger_pos()
                    self.game_state.update_trapped_tiger()

        # ESC to go back to mode select
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            self.current_state = UIState.MAIN_MENU

    def handle_game_over_events(self):
        """Handle events during game over screen"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.current_state = UIState.EXITING
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.current_state = UIState.MODE_SELECT
                elif event.key == pygame.K_ESCAPE:
                    self.current_state = UIState.MAIN_MENU

    def update_ai_logic(self):
        """Handle AI moves with proper timing"""
        should_make_ai_move = False

        if self.current_state == UIState.PLAYING_CVC:
            should_make_ai_move = True
        elif self.current_state == UIState.PLAYING_PVC_GOAT and self.game_state.turn == Piece.GOAT:
            should_make_ai_move = True
        elif self.current_state == UIState.PLAYING_PVC_TIGER and self.game_state.turn == Piece.TIGER:
            should_make_ai_move = True

        if self.is_game_over():
            should_make_ai_move = False

        # if should_make_ai_move and self.minimax_agent and self.game_state.goat_count > 0:  # Placement
        if should_make_ai_move and self.minimax_agent:
            current_time = pygame.time.get_ticks()
            if current_time - self.ai_move_timer >= self.ai_move_delay:
                move = self.minimax_agent.get_best_move(self.game_state)
                if move:
                    self.game_state = self.game_state.make_move(move)
                    self.remove_later_state_hash_update()
                    self.ai_move_timer = current_time

        # if should_make_ai_move and self.mcts_agent and self.game_state.goat_count == 0:  # Movement
        if should_make_ai_move and self.mcts_agent:
            current_time = pygame.time.get_ticks()
            if current_time - self.ai_move_timer >= self.ai_move_delay:
                move = self.mcts_agent.search()
                # self.mcts_agent.visualize_tree()
                if move:
                    self.game_state = self.game_state.make_move(move)
                    self.remove_later_state_hash_update()
                    if self.game_state.goat_count > 15:  # Early game
                        time_limit = 0.5
                    elif self.game_state.goat_count > 5:  # Mid game
                        time_limit = 1.0
                    else:  # End game
                        time_limit = 2.0
                    self.mcts_agent = MCTS(
                        initial_state=self.game_state, time_limit=time_limit)
                    self.ai_move_timer = current_time

    def is_game_over(self):
        # TODO: Refactor
        is_game_over = self.game_state.is_game_over()
        state_key = self.game_state.key()
        if self.remove_later_state_hash[state_key] > 3:
            is_game_over = True
        return is_game_over

    def check_game_over(self):
        """Check if game is over and handle transition"""
        if self.is_game_over():
            if self.game_over_timer == 0:
                self.game_over_timer = pygame.time.get_ticks()
                print("Game Over")
            elif pygame.time.get_ticks() - self.game_over_timer >= self.game_over_delay:
                self.current_state = UIState.GAME_OVER
                self.game_over_timer = 0

    def draw_board(self):
        pygame.draw.line(self.screen, 0, (0+self.offset, 0+self.offset),
                         (self.board_width+self.offset, self.board_height+self.offset), 3)
        pygame.draw.line(self.screen, 0, (0+self.offset, self.board_width+self.offset),
                         (self.board_height+self.offset, 0+self.offset), 3)

        # /
        #
        pygame.draw.line(self.screen, 0, (0+self.offset, self.board_height//2+self.offset),
                         (self.board_width//2+self.offset, 0+self.offset), 3)
        pygame.draw.line(self.screen, 0, (0+self.offset, self.board_height//2+self.offset),
                         (self.board_width//2+self.offset, self.board_height+self.offset), 3)

        #    \
        #    /
        pygame.draw.line(self.screen, 0, (self.board_width+self.offset, self.board_height//2+self.offset),
                         (self.board_width//2+self.offset, 0+self.offset), 3)
        pygame.draw.line(self.screen, 0, (self.board_width+self.offset, self.board_height//2+self.offset),
                         (self.board_width//2+self.offset, self.board_height+self.offset), 3)

        # vertical lines
        for i in range(self.grid_cols):
            pygame.draw.line(self.screen, 0, (i*self.cell_size+self.offset, 0+self.offset),
                             (i*self.cell_size+self.offset, self.grid_height+self.offset-self.cell_size), 2)
        # horizontal lines
        for i in range(self.grid_rows):
            pygame.draw.line(self.screen, 0, (0+self.offset, i*self.cell_size+self.offset),
                             (self.grid_width+self.offset-self.cell_size, i*self.cell_size+self.offset), 2)

    def cell_to_pixel(self, col, row):
        # given col, row returns the corresponding grid position(x, y) or cell position(x, y)
        return col * self.cell_size, row * self.cell_size

    def draw_grid_lines(self):
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                sqr_x, sqr_y = self.cell_to_pixel(col, row)
                sqr = pygame.Rect(sqr_x, sqr_y, self.cell_size, self.cell_size)
                pygame.draw.rect(
                    self.screen, COLORS["board"], sqr, 1)  # border

    def draw_pieces(self):
        for i, piece in enumerate(self.game_state.board):
            row, col = divmod(i, 5)
            x, y = self.cell_to_pixel(col, row)
            x, y = x+self.offset//2, y+self.offset//2

            if piece == Piece.GOAT:
                img = self.goat_selected if i == self.selected_cell else self.goat_img
                self.screen.blit(img, (x, y))
            elif piece == Piece.TIGER:
                img = self.bagh_selected if i == self.selected_cell else self.bagh_img
                self.screen.blit(img, (x, y))

    def place_piece(self, pos):
        # Disable player input if it's AI's turn or it's game over
        if (self.current_state == UIState.PLAYING_CVC or
            (self.current_state == UIState.PLAYING_PVC_GOAT and self.game_state.turn == Piece.GOAT) or
                (self.current_state == UIState.PLAYING_PVC_TIGER and self.game_state.turn == Piece.TIGER) or
                self.is_game_over()):
            return

        mouse_x, mouse_y = pos
        col, row = mouse_x // self.cell_size, mouse_y // self.cell_size
        if col >= 5 or row >= 5:
            return

        idx = col + row * self.grid_cols
        piece = self.game_state.board[idx]

        if self.selected_cell is None:
            if self.game_state.turn == Piece.GOAT and self.game_state.goat_count > 0:
                # Placement
                if piece == Piece.EMPTY:
                    self.game_state = self.game_state.make_move(
                        (idx, idx))
                    self.remove_later_state_hash_update()
                    # self.game_state.make_move((idx, idx))
                    # self.game_state.update_tiger_pos()
                    # self.game_state.update_trapped_tiger()
                    # Reset AI timer so it waits before responding to player move
                    self.ai_move_timer = pygame.time.get_ticks()
                    return
            elif piece == self.game_state.turn:
                self.selected_cell = idx
        else:
            move = (self.selected_cell, idx)
            if move in self.game_state.get_legal_moves():
                # self.game_state.make_move(move)
                # self.game_state.update_tiger_pos()
                # self.game_state.update_trapped_tiger()
                self.game_state = self.game_state.make_move(move)
                self.remove_later_state_hash_update()
                # Reset AI timer so it waits before responding to player move
                self.ai_move_timer = pygame.time.get_ticks()
            self.selected_cell = None

    def draw_status(self):
        font = pygame.font.SysFont(None, 48)
        goat_text = font.render(
            f"Goats Left: {self.game_state.goat_count}", True, "black")
        eaten_text = font.render(
            f"Goats Eaten: {self.game_state.eaten_goat_count}", True, "black")
        trapped_text = font.render(
            f"Tigers Trapped: {self.game_state.trapped_tiger_count}", True, "black")

        self.screen.blit(goat_text, (0, self.grid_height-50))
        self.screen.blit(eaten_text, (self.cell_size*2, self.grid_height-50))
        self.screen.blit(
            trapped_text, (self.cell_size*4-80, self.grid_height-50))

    def draw_text(self, text, size, x, y, color=None):
        """Draw text at specified position"""
        if color is None:
            color = COLORS["text"]
        font = pygame.font.Font(ASSETS["font"], size)
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(center=(x, y))
        self.screen.blit(text_surface, text_rect)

    def draw_button(self, text, x, y, w, h):
        """Draw a button and return its rect"""
        rect = pygame.Rect(x, y, w, h)
        mouse_pos = pygame.mouse.get_pos()

        if rect.collidepoint(mouse_pos):
            pygame.draw.rect(self.screen, COLORS["board"], rect, 2)

        self.draw_text(text, 32, x + w // 2, y + h // 2)
        return rect

    def render_main_menu(self):
        """Render the main menu"""
        self.screen.fill(COLORS["menu_bg"])
        self.draw_text("Baghchal", 64, self.screen_size[0] // 2, 100)
        self.draw_button("Play", 277, 350, 200, 60)
        self.draw_button("Exit", 277, 450, 200, 60)

    def render_mode_select(self):
        """Render the mode selection screen"""
        self.screen.fill(COLORS["mode_bg"])
        self.draw_text("Select mode", 64, self.screen_size[0] // 2, 100)
        self.draw_button("Player vs Player", 127, 350, 550, 60)
        self.draw_button("Player vs Goat AI", 107, 450, 600, 60)
        self.draw_button("Player vs Tiger AI", 107, 550, 600, 60)
        self.draw_button("Computer vs Computer", 87, 650, 650, 60)
        self.draw_text("Press ESC to go back", 24,
                       self.screen_size[0] // 2, 750)

    def render_game(self):
        """Render the game screen"""
        self.screen.fill(COLORS["bg"])
        self.draw_board()
        self.draw_pieces()
        self.draw_status()

    def render_game_over(self):
        # TODO
        pieces = {
            -1: "Goat",
            1: "Tiger"
        }
        """Render the game over screen"""
        self.screen.fill("darkred")
        self.draw_text(
            "Game Over!", 72, self.screen_size[0] // 2, self.screen_size[1] // 2 - 200, "white")
        result_text = f"{pieces[self.game_state.get_result()]} Won!" if self.game_state.get_result(
        ) else "It's a Draw!"
        self.draw_text(
            result_text, 36, self.screen_size[0] // 2, self.screen_size[1] // 2 - 100, "white")
        self.draw_text("Press SPACE to play again", 36,
                       self.screen_size[0] // 2, self.screen_size[1] // 2, "white")
        self.draw_text("Press ESC for main menu", 36,
                       self.screen_size[0] // 2, self.screen_size[1] // 2 + 50, "white")

    def update(self):
        """Main update loop - handles state transitions and rendering"""
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
            self.update_ai_logic()
            self.check_game_over()
            self.render_game()

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
        pygame.quit()
