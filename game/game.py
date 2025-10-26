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
        self.base_cell_size = cell_size
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

    def state_hash_update(self):
        state_key = self.game_state.key
        self.state_hash[state_key] += 1

    def initialize_board_data(self):
        self.grid_width = self.cell_size * 5
        self.grid_height = self.cell_size * 5
        self.screen_size = (self.grid_width, self.grid_height + 100)
        self.grid_cols = 5
        self.grid_rows = 5
        self.offset = self.cell_size // 2
        self.board_width = self.grid_width - self.cell_size
        self.board_height = self.grid_height - self.cell_size

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

    def cache_scaled_assets(self):
        piece_size = int(self.cell_size * 0.55)
        self.bagh_img = pygame.transform.smoothscale(
            self.bagh_img_original, (piece_size, piece_size))
        self.goat_img = pygame.transform.smoothscale(
            self.goat_img_original, (piece_size, piece_size))
        self.bagh_selected = pygame.transform.smoothscale(
            self.bagh_selected_original, (piece_size, piece_size))
        self.goat_selected = pygame.transform.smoothscale(
            self.goat_selected_original, (piece_size, piece_size))

    def handle_resize(self, new_size):
        width, height = new_size
        available_width = width
        available_height = height - 100
        max_cell_from_width = available_width // 5
        max_cell_from_height = available_height // 5
        new_cell_size = min(max_cell_from_width, max_cell_from_height)
        new_cell_size = max(self.min_cell_size, min(
            self.max_cell_size, new_cell_size))
        if new_cell_size != self.cell_size:
            self.cell_size = new_cell_size
            self.initialize_board_data()
            self.cache_scaled_assets()
        self.screen = pygame.display.set_mode(
            self.screen_size, pygame.RESIZABLE)

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
            elif pygame.time.get_ticks() - self.game_over_timer >= self.game_over_delay:
                self.current_state = UIState.GAME_OVER
                self.game_over_timer = 0

    def cell_to_pixel(self, col, row):
        return col * self.cell_size, row * self.cell_size

    def place_piece(self, pos):
        self.last_move_highlight = None
        is_human_turn = (self.current_state == UIState.PLAYING_PVP) or \
                        (self.current_state == UIState.PLAYING_PVC_GOAT and self.game_state.turn == 1) or \
                        (self.current_state ==
                         UIState.PLAYING_PVC_TIGER and self.game_state.turn == -1)
        if (self.ai_is_thinking or self.is_game_over() or not is_human_turn or self.pending_player_move or self.move_processed_this_frame):
            return
        mouse_x, mouse_y = pos
        col, row = mouse_x // self.cell_size, mouse_y // self.cell_size
        if col >= 5 or row >= 5:
            return
        idx = col + row * self.grid_cols
        piece = None
        if self.game_state.turn == 1:
            if self.game_state.tigers_bb & (1 << idx):
                piece = 1
        else:
            if self.game_state.goats_bb & (1 << idx):
                piece = -1
        move = None
        if self.selected_cell is None:
            if self.game_state.turn == -1 and self.game_state.goats_to_place > 0:
                move = (idx, idx)
                if move in self.game_state.get_legal_moves():
                    self.pending_player_move = move
                    x, y = self.cell_to_pixel(col, row)
                    self.particles.append(ParticleEffect(
                        x + self.offset, y + self.offset, COLORS['accent']))
                    return
            elif piece == self.game_state.turn:
                self.selected_cell = idx
                self.valid_moves = [
                    m for m in self.game_state.get_legal_moves() if m[0] == idx]
        else:
            move = (self.selected_cell, idx)
            if move in self.game_state.get_legal_moves():
                self.pending_player_move = move
                self.last_move_highlight = (self.selected_cell, idx)
                x, y = self.cell_to_pixel(col, row)
                self.particles.append(ParticleEffect(
                    x + self.offset, y + self.offset, (220, 180, 100)))
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
                self.particles.append(ParticleEffect(
                    x + self.offset, y + self.offset, (255, 200, 50)))
            self.game_state.make_move(move)
            self.state_hash_update()
            self.move_processed_this_frame = True
            self.last_move_frame = current_frame

    def update(self):
        self.move_processed_this_frame = False
        self.event_handler.handle_events()

        if self.current_state == UIState.MAIN_MENU:
            self.renderer.render_main_menu()
        elif self.current_state == UIState.MODE_SELECT:
            self.renderer.render_mode_select()
        elif self.current_state in [UIState.PLAYING_PVP, UIState.PLAYING_PVC_GOAT, UIState.PLAYING_PVC_TIGER, UIState.PLAYING_CVC]:
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

    def run(self):
        while self.running:
            self.update()
        self.cleanup_ai_thread()
        pygame.quit()
