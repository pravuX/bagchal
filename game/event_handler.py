import pygame
import threading
from .constants import UIState
pygame.mixer.init()

click_sound = pygame.mixer.Sound("assets/button_click.mp3")
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
        elif self.game.current_state == UIState.ANALYSIS_MODE:
            self.handle_analysis_mode_events(events)
        elif self.game.current_state == UIState.REPLAYING:
            self.handle_replay_events(events)
        elif self.game.current_state in [UIState.PLAYING_PVP, UIState.PLAYING_PVC_GOAT, UIState.PLAYING_PVC_TIGER, UIState.PLAYING_CVC]:
            self.handle_game_events(events)
        elif self.game.current_state == UIState.GAME_OVER:
            self.handle_game_over_events(events)

    def handle_main_menu_events(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                play_btn_rect = pygame.Rect(
                    self.game.screen_size[0]//2 - 100, 350, 200, 60)
                analysis_btn_rect = pygame.Rect(
                    self.game.screen_size[0]//2 - 100, 430, 200, 60)
                exit_btn_rect = pygame.Rect(
                    self.game.screen_size[0]//2 - 100, 510, 200, 60)
                if play_btn_rect.collidepoint(event.pos):
                    self.game.current_state = UIState.MODE_SELECT
                elif analysis_btn_rect.collidepoint(event.pos):
                    self.game.current_state = UIState.ANALYSIS_MODE
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
                     click_sound.play()
                     for r in range(0, x_width+200):  # smaller ripple range for speed
                            pygame.draw.circle(self.game.screen,(80, 70, 120), pygame.mouse.get_pos(), r, width = 0)
                            pygame.display.update()
                            self.game.reset_game()
                            self.game.current_game_mode = "PvP"
                            self.game.current_state = UIState.PLAYING_PVP
                elif pvc_goat_rect.collidepoint(event.pos):
                    click_sound.play()
                    for r in range(0, x_width+200):  # smaller ripple range for speed
                            pygame.draw.circle(self.game.screen,(70, 120, 80), pygame.mouse.get_pos(), r, width = 0)
                            pygame.display.update()
                    self.game.reset_game()
                    self.game.current_game_mode = "PvC_Goat"
                    self.game.current_state = UIState.PLAYING_PVC_GOAT
                    self.start_ai_initialization()
                elif pvc_tiger_rect.collidepoint(event.pos):
                    click_sound.play()
                    for r in range(0, x_width+200):  # smaller ripple range for speed
                            pygame.draw.circle(self.game.screen,(120, 80, 70), pygame.mouse.get_pos(), r, width = 0)
                            pygame.display.update()
                    self.game.reset_game()
                    self.game.current_game_mode = "PvC_Tiger"
                    self.game.current_state = UIState.PLAYING_PVC_TIGER
                    self.start_ai_initialization()
                elif cvc_rect.collidepoint(event.pos):
                    click_sound.play()
                    for r in range(0, x_width+200):  # smaller ripple range for speed
                            pygame.draw.circle(self.game.screen,(120, 70, 120), pygame.mouse.get_pos(), r, width = 0)
                            pygame.display.update()
                    self.game.reset_game()
                    self.game.current_game_mode = "CvC"
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

    def handle_analysis_mode_events(self, events):
        """Handle events in Analysis Mode."""
        from .database import get_last_games
        
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                games = get_last_games(5)
                
                # Calculate button positions (5 games displayed vertically)
                x_width = self.game.screen_size[0]
                y_start = 250
                button_height = 100
                button_spacing = 120
                button_width = x_width * 0.8
                button_x = x_width * 0.1
                
                # Check if a game was clicked
                for i, game in enumerate(games):
                    button_rect = pygame.Rect(
                        button_x, 
                        y_start + i * button_spacing, 
                        button_width, 
                        button_height
                    )
                    if button_rect.collidepoint(event.pos):
                        # Load and start replay
                        if self.game.load_game_for_replay(game["id"]):
                            self.game.current_state = UIState.REPLAYING
                        break
                
                # Check for back button (top of screen or bottom)
                back_btn_rect = pygame.Rect(
                    self.game.screen_size[0] // 2 - 100,
                    self.game.screen_size[1] - 80,
                    200, 60
                )
                if back_btn_rect.collidepoint(event.pos):
                    self.game.current_state = UIState.MAIN_MENU
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            self.game.current_state = UIState.MAIN_MENU
    
    def handle_replay_events(self, events):
        """Handle events during replay."""
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                x_width = self.game.screen_size[0]
                y_height = self.game.screen_size[1]
                
                # Replay control buttons at bottom
                button_y = y_height - 80
                button_height = 50
                button_width = 120
                button_spacing = 140
                center_x = x_width // 2
                
                # Previous button
                prev_btn_rect = pygame.Rect(
                    center_x - button_spacing * 1.5,
                    button_y,
                    button_width,
                    button_height
                )
                
                # Play/Pause button
                play_btn_rect = pygame.Rect(
                    center_x - button_width // 2,
                    button_y,
                    button_width,
                    button_height
                )
                
                # Next button
                next_btn_rect = pygame.Rect(
                    center_x + button_spacing * 0.5,
                    button_y,
                    button_width,
                    button_height
                )
                
                # Exit replay button
                exit_btn_rect = pygame.Rect(
                    x_width - 120,
                    20,
                    100,
                    40
                )
                
                if prev_btn_rect.collidepoint(event.pos):
                    self.game.step_replay_backward()
                elif play_btn_rect.collidepoint(event.pos):
                    self.game.toggle_replay_auto_play()
                elif next_btn_rect.collidepoint(event.pos):
                    self.game.step_replay_forward()
                    self.game.auto_play = False  # Stop auto-play on manual step
                elif exit_btn_rect.collidepoint(event.pos):
                    self.game.current_state = UIState.ANALYSIS_MODE
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            self.game.current_state = UIState.ANALYSIS_MODE

    def start_ai_initialization(self):
        ai_thread = threading.Thread(target=self.game._initialize_ai_async)
        ai_thread.daemon = True
        ai_thread.start()
