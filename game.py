import threading
from collections import defaultdict
from enum import Enum
import pygame
from bagchal import *
from alphabeta import MinimaxAgent
from mcts import MCTS
import numpy as np

mcts_flag, minimax_flag = 0, 1

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

        self.game_state: GameState = game_state
        self.cell_size = cell_size

        self.current_state = UIState.MAIN_MENU
        self.running = True

        self.pending_player_move = None

        self.minimax_agent = MinimaxAgent()
        self.mcts_agent = MCTS()

        self.using_agent = mcts_flag

        self.ai_thread = None
        # ai thinking time in seconds
        self.time_limit = 1
        self.ai_is_thinking = False
        self.ai_result_move = None

        # Game over state
        self.game_over_timer = 0
        self.game_over_delay = 2500  # milliseconds

        self.initialize_board_data()
        self.selected_cell = None

        self.initialize_pygame_state(tick_speed)
        self.load_assets()

        self.state_hash = defaultdict(int)

        # Synchronization Flags
        self.ai_initialized = False
        self.game_just_reset = False
        self.initial_render_done = False
        self.move_processed_this_frame = False
        self.last_move_frame = None

    def state_hash_update(self):
        state_key = self.game_state.key
        self.state_hash[state_key] += 1

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
        self.cleanup_ai_thread()

        board = np.array([Piece_EMPTY] * 25, dtype=np.int8)
        pos_tiger = [0, 4, 20, 24]
        board[pos_tiger[0]] = Piece_TIGER
        board[pos_tiger[1]] = Piece_TIGER
        board[pos_tiger[2]] = Piece_TIGER
        board[pos_tiger[3]] = Piece_TIGER

        game_state = GameState(board, turn=Piece_GOAT,
                               goat_count=20, eaten_goat_count=0)
        self.game_state = game_state
        self.selected_cell = None
        self.state_hash.clear()

        self.ai_initialized = False
        self.ai_is_thinking = False
        self.pending_player_move = None
        self.ai_result_move = None
        self.game_just_reset = True
        self.initial_render_done = False

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
                    self.current_state = UIState.PLAYING_PVC_GOAT

                    ai_thread = threading.Thread(
                        target=self._initialize_ai_async)
                    ai_thread.daemon = True
                    ai_thread.start()

                elif pvc_tiger_rect.collidepoint(event.pos):
                    self.reset_game()
                    self.current_state = UIState.PLAYING_PVC_TIGER

                    ai_thread = threading.Thread(
                        target=self._initialize_ai_async)
                    ai_thread.daemon = True
                    ai_thread.start()

                elif cvc_rect.collidepoint(event.pos):

                    self.reset_game()
                    self.current_state = UIState.PLAYING_CVC

                    ai_thread = threading.Thread(
                        target=self._initialize_ai_async)
                    ai_thread.daemon = True
                    ai_thread.start()

        # ESC to go back to main menu
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            self.cleanup_ai_thread()
            self.current_state = UIState.MAIN_MENU

    def handle_game_events(self):
        """Handle events during gameplay"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.current_state = UIState.EXITING
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.current_state == UIState.PLAYING_PVP or \
                   (self.current_state == UIState.PLAYING_PVC_GOAT and self.game_state.turn == Piece_TIGER) or \
                   (self.current_state == UIState.PLAYING_PVC_TIGER and self.game_state.turn == Piece_GOAT):
                    self.place_piece(event.pos)

        # ESC to go back to mode select
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            self.cleanup_ai_thread()
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

    def cleanup_ai_thread(self):
        if self.ai_thread and self.ai_thread.is_alive():
            self.ai_thread.join()
        self.ai_thread = None

    def _initialize_ai_async(self):
        # start_time = pygame.time.get_ticks()
        # print("AI Init Started at")
        try:
            if self.using_agent == minimax_flag:
                self.minimax_agent = MinimaxAgent()
            elif self.using_agent == mcts_flag:
                self.mcts_agent = MCTS()
        finally:
            # end_time = pygame.time.get_ticks()
            # print(
            #     f"AI Init completed at {end_time}. Took {end_time - start_time}ms.")
            self.ai_initialized = True

    def _ai_worker(self, agent, game_state):
        """This function runs on a separate thread."""
        try:
            if hasattr(agent, "search"):  # MCTS
                move = agent.search(game_state, time_limit=self.time_limit)
                print(f"Total Simulations: {agent.simulations_run}")
                print(f"Goat Wins: {agent.goat_wins}",
                      f"Tiger Wins: {agent.tiger_wins}",
                      f"Draws: {agent.draws}")
                agent.visualize_tree(max_depth=1)
            else:  # Minimax
                move = agent.get_best_move(
                    game_state, time_limit=self.time_limit)

            # When the search is done, store the result
            self.ai_result_move = move
        except Exception as e:
            print(f"AI Error: {e}")
            self.ai_result_move = None
        finally:
            # Always make sure we signal that we are done
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
        """Handle AI moves with proper timing"""

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
        """Check if game is over and handle transition"""
        if self.is_game_over():
            if self.game_over_timer == 0:
                self.game_over_timer = pygame.time.get_ticks()
                print("Game Over")
                print(self.game_state)
                result = GameState.piece[self.game_state.get_result] + \
                    " Won" if self.game_state.get_result else "Draw"
                print("Result:", result)
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

            if piece == Piece_GOAT:
                img = self.goat_selected if i == self.selected_cell else self.goat_img
                self.screen.blit(img, (x, y))
            elif piece == Piece_TIGER:
                img = self.bagh_selected if i == self.selected_cell else self.bagh_img
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
        piece = self.game_state.board[idx]

        move = None

        if self.selected_cell is None:
            if self.game_state.turn == Piece_GOAT and self.game_state.goat_count > 0:
                # Placement
                if piece == Piece_EMPTY:
                    move = (idx, idx)
                    self.pending_player_move = move
                    return
            elif piece == self.game_state.turn:
                self.selected_cell = idx
        else:
            move = (self.selected_cell, idx)
            if move in self.game_state.get_legal_moves_np():
                self.pending_player_move = move
            self.selected_cell = None

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

            self.game_state.make_move(move)
            self.state_hash_update()

            self.move_processed_this_frame = True
            self.last_move_frame = current_frame

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

        # if self.game_just_reset:
        #     self.initial_render_done = True
        #     self.game_just_reset = False

        # Draw AI Status
        if self.ai_is_thinking:
            self.draw_text("AI is thinking...", 24,
                           400, 50, color=(255, 255, 0))

    def render_game_over(self):
        pieces = {
            -1: "Goat",
            1: "Tiger"
        }
        """Render the game over screen"""
        self.screen.fill("darkred")
        self.draw_text(
            "Game Over!", 72, self.screen_size[0] // 2, self.screen_size[1] // 2 - 200, "white")
        result_text = f"{pieces[self.game_state.get_result]} Won!" if self.game_state.get_result else "It's a Draw!"
        self.draw_text(
            result_text, 36, self.screen_size[0] // 2, self.screen_size[1] // 2 - 100, "white")
        self.draw_text("Press SPACE to play again", 36,
                       self.screen_size[0] // 2, self.screen_size[1] // 2, "white")
        self.draw_text("Press ESC for main menu", 36,
                       self.screen_size[0] // 2, self.screen_size[1] // 2 + 50, "white")

    def update(self):
        self.move_processed_this_frame = False
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
