import pygame
import threading
from .constants import UIState


class EventHandler:
    def __init__(self, game):
        self.game = game

    def handle_events(self):

        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                self.game.current_state = UIState.EXITING
                return  # Exit early if quitting

            if event.type == pygame.VIDEORESIZE:
                self.game.pending_resize = event.size
                self.game.resize_timer = pygame.time.get_ticks()

        if self.game.current_state == UIState.MAIN_MENU:
            self.handle_main_menu_events(events)
        elif self.game.current_state == UIState.MODE_SELECT:
            self.handle_mode_select_events(events)
        elif self.game.current_state in [UIState.PLAYING_PVP, UIState.PLAYING_PVC_GOAT, UIState.PLAYING_PVC_TIGER, UIState.PLAYING_CVC]:
            self.handle_game_events(events)
        elif self.game.current_state == UIState.GAME_OVER:
            self.handle_game_over_events(events)

    def handle_main_menu_events(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                play_btn_rect = pygame.Rect(
                    self.game.screen_size[0]//2 - 100, 350, 200, 60)
                exit_btn_rect = pygame.Rect(
                    self.game.screen_size[0]//2 - 100, 450, 200, 60)
                if play_btn_rect.collidepoint(event.pos):
                    self.game.current_state = UIState.MODE_SELECT
                elif exit_btn_rect.collidepoint(event.pos):
                    self.game.current_state = UIState.EXITING

    def handle_mode_select_events(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                x_width = self.game.screen_size[0]
                y_height = self.game.screen_size[1]
                pvp_rect = pygame.Rect(x_width *.056, x_width* 0.45, x_width* 0.18, y_height * 0.360)
                pvc_goat_rect = pygame.Rect(x_width * .292, x_width* 0.45, x_width* 0.18, y_height * 0.360)
                pvc_tiger_rect = pygame.Rect(x_width * .528 , x_width* 0.45, x_width* 0.18, y_height * 0.360)
                cvc_rect = pygame.Rect(x_width * .764, x_width* 0.45, x_width* 0.18, y_height * 0.360)
                if pvp_rect.collidepoint(event.pos):
                     for r in range(0, 1800):  # smaller ripple range for speed
                            pygame.draw.circle(self.game.screen,(80, 70, 120), pygame.mouse.get_pos(), r, width = 0)
                            pygame.display.update()
                            self.game.reset_game()
                            self.game.current_state = UIState.PLAYING_PVP
                elif pvc_goat_rect.collidepoint(event.pos):
                    for r in range(0, 1800):  # smaller ripple range for speed
                            pygame.draw.circle(self.game.screen,(70, 120, 80), pygame.mouse.get_pos(), r, width = 0)
                            pygame.display.update()
                    self.game.reset_game()
                    self.game.current_state = UIState.PLAYING_PVC_GOAT
                    self.start_ai_initialization()
                elif pvc_tiger_rect.collidepoint(event.pos):
                    for r in range(0, 1800):  # smaller ripple range for speed
                            pygame.draw.circle(self.game.screen,(120, 80, 70), pygame.mouse.get_pos(), r, width = 0)
                            pygame.display.update()
                    self.game.reset_game()
                    self.game.current_state = UIState.PLAYING_PVC_TIGER
                    self.start_ai_initialization()
                elif cvc_rect.collidepoint(event.pos):
                    for r in range(0, 1800):  # smaller ripple range for speed
                            pygame.draw.circle(self.game.screen,(120, 70, 120), pygame.mouse.get_pos(), r, width = 0)
                            pygame.display.update()
                    self.game.reset_game()
                    self.game.current_state = UIState.PLAYING_CVC
                    self.start_ai_initialization()
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            self.game.cleanup_ai_thread()
            self.game.current_state = UIState.MAIN_MENU

    def handle_game_events(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.game.current_state == UIState.PLAYING_PVP or \
                   (self.game.current_state == UIState.PLAYING_PVC_GOAT and self.game.game_state.turn == 1) or \
                   (self.game.current_state == UIState.PLAYING_PVC_TIGER and self.game.game_state.turn == -1):
                    self.game.place_piece(event.pos)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            self.game.cleanup_ai_thread()
            self.game.current_state = UIState.MAIN_MENU

    def handle_game_over_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.game.current_state = UIState.MODE_SELECT
                elif event.key == pygame.K_ESCAPE:
                    self.game.current_state = UIState.MAIN_MENU

    def start_ai_initialization(self):
        ai_thread = threading.Thread(target=self.game._initialize_ai_async)
        ai_thread.daemon = True
        ai_thread.start()
