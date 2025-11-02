import pygame
from .constants import COLORS, ASSETS, UIState
from bagchal import Piece_GOAT, Piece_TIGER, extract_indices_fast, BOARD_MASK
from .database import get_last_games


class GameRenderer:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.board_surface = game.board_surface
        self.is_debug = False

    def draw_board(self):
        target_surface = self.game.board_surface if self.game.board_surface else self.screen
        board_rect = pygame.Rect(
            self.game.offset, self.game.offset, self.game.board_width, self.game.board_height)
        pygame.draw.rect(target_surface, COLORS["board_light"], board_rect)

        pygame.draw.rect(
            target_surface, COLORS["board"], board_rect, border_radius=10)

        line_color = COLORS["board_light"]
        target_surface = self.game.board_surface if self.game.board_surface else self.screen

        pygame.draw.line(target_surface, line_color, (self.game.offset, self.game.offset), (
            self.game.board_width + self.game.offset, self.game.board_height + self.game.offset), 5)
        pygame.draw.line(target_surface, line_color, (self.game.offset, self.game.board_height +
                         self.game.offset), (self.game.board_width + self.game.offset, self.game.offset), 5)
        pygame.draw.line(target_surface, line_color, (self.game.offset, self.game.board_height // 2 +
                         self.game.offset), (self.game.board_width // 2 + self.game.offset, self.game.offset), 4)
        pygame.draw.line(target_surface, line_color, (self.game.offset, self.game.board_height // 2 + self.game.offset),
                         (self.game.board_width // 2 + self.game.offset, self.game.board_height + self.game.offset), 4)
        pygame.draw.line(target_surface, line_color, (self.game.board_width + self.game.offset, self.game.board_height //
                         2 + self.game.offset), (self.game.board_width // 2 + self.game.offset, self.game.offset), 4)
        pygame.draw.line(target_surface, line_color, (self.game.board_width + self.game.offset, self.game.board_height // 2 +
                         self.game.offset), (self.game.board_width // 2 + self.game.offset, self.game.board_height + self.game.offset), 4)

        for i in range(self.game.grid_cols):
            pygame.draw.line(target_surface, line_color, (i * self.game.cell_size + self.game.offset, self.game.offset),
                             (i * self.game.cell_size + self.game.offset, self.game.grid_height - self.game.cell_size + self.game.offset), 4)
        for i in range(self.game.grid_rows):
            pygame.draw.line(target_surface, line_color, (self.game.offset, i * self.game.cell_size + self.game.offset),
                             (self.game.grid_width - self.game.cell_size + self.game.offset, i * self.game.cell_size + self.game.offset), 4)

        for row in range(5):
            for col in range(5):
                x = col * self.game.cell_size + self.game.offset
                y = row * self.game.cell_size + self.game.offset
                pygame.draw.circle(target_surface, COLORS["accent"], (x, y), 7)
                pygame.draw.circle(target_surface, COLORS["board"], (x, y), 5)
                idx = col + row * self.game.grid_cols

                # Draw valid moves for goats during placement phase (not in replay mode)
                if self.game.current_state != UIState.REPLAYING:
                    occupied_bb = self.game.game_state.tigers_bb | self.game.game_state.goats_bb
                    empty_bb = ~occupied_bb & BOARD_MASK
                    if empty_bb & (1 << idx) and self.game.game_state.turn == Piece_GOAT and self.game.game_state.goats_to_place > 0:
                        self.draw_pulsating_circle(x, y, target_surface)

    def draw_valid_moves(self):
        if not self.game.valid_moves:
            return
        target_surface = self.game.board_surface if self.game.board_surface else self.screen
        for move in self.game.valid_moves:
            to_idx = move[1]
            row, col = divmod(to_idx, 5)
            x = col * self.game.cell_size + self.game.offset
            y = row * self.game.cell_size + self.game.offset
            self.draw_pulsating_circle(x, y, target_surface)

    def draw_pulsating_circle(self, x, y, target_surface=None):
        if target_surface is None:
            target_surface = self.screen
        pulse = abs(pygame.time.get_ticks() % 800 - 400) / 400
        radius = int(self.game.cell_size//5 + 5 * pulse)
        s = pygame.Surface(
            (radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(
            s, COLORS["valid_move"], (radius, radius), radius)
        target_surface.blit(s, (x - radius, y - radius))

    def draw_pieces(self):
        target_surface = self.game.board_surface if self.game.board_surface else self.screen
        tiger_positions = extract_indices_fast(self.game.game_state.tigers_bb)
        goat_positions = extract_indices_fast(self.game.game_state.goats_bb)

        if self.game.selected_cell is not None:
            row, col = divmod(self.game.selected_cell, 5)
            center_x = col * self.game.cell_size + self.game.offset
            center_y = row * self.game.cell_size + self.game.offset

            pulse = abs(pygame.time.get_ticks() % 800 - 400) / 400
            img_width = self.game.bagh_img.get_width()
            radius = int((img_width / 2) + 10 * pulse)

            circle_surface = pygame.Surface(
                (radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                circle_surface, COLORS["selected"], (radius, radius), radius)

            circle_rect = circle_surface.get_rect(center=(center_x, center_y))
            target_surface.blit(circle_surface, circle_rect)

        for i in tiger_positions:
            row, col = divmod(i, 5)
            center_x = col * self.game.cell_size + self.game.offset
            center_y = row * self.game.cell_size + self.game.offset

            img = self.game.bagh_selected if i == self.game.selected_cell else self.game.bagh_img
            img_rect = img.get_rect(center=(center_x, center_y))
            target_surface.blit(img, img_rect)

        for i in goat_positions:
            row, col = divmod(i, 5)
            center_x = col * self.game.cell_size + self.game.offset
            center_y = row * self.game.cell_size + self.game.offset

            img = self.game.goat_selected if i == self.game.selected_cell else self.game.goat_img
            img_rect = img.get_rect(center=(center_x, center_y))
            target_surface.blit(img, img_rect)

    def draw_status(self):
        status_y = self.game.screen_size[1] - 100
        panel_height = 100
        panel_width = self.game.screen_size[0]
        panel_rect = pygame.Rect(
            0, status_y, panel_width, panel_height)
        pygame.draw.rect(self.screen, COLORS["board"], panel_rect)

        turn_text = "Tiger's Turn" if self.game.game_state.turn == 1 else "Goat's Turn"
        goat_text = f"Goats Left:{self.game.game_state.goats_to_place}"
        eaten_text = f"Goats Eaten:{self.game.game_state.goats_eaten}"
        trapped_text = f"TigersTrapped:{self.game.game_state.trapped_tiger_count}"

        padding = 50  # within button
        spacing = 10  # between buttons
        height = panel_height // 2
        width = panel_width // 4 + padding
        width = min(275, width)
        center = panel_width // 2 - width // 2
        y = status_y + panel_height // 4

        font_size = int(self.game.cell_size * 0.1)

        self.draw_button(turn_text, center,
                         status_y - height//1.5, width, height, font_size)

        self.draw_button(goat_text, center - width - spacing,
                         y, width, height, font_size)

        self.draw_button(eaten_text, center,
                         y, width, height, font_size)

        self.draw_button(trapped_text, center + width + spacing,
                         y, width, height, font_size)

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

    def draw_button(self, text, x, y, w, h, font_size=None):
        rect = pygame.Rect(x, y, w, h)
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = rect.collidepoint(mouse_pos)
        shadow_rect = rect.inflate(4, 4)
        shadow_rect.y += 3
        pygame.draw.rect(self.screen, (0, 0, 0, 50),
                         shadow_rect, border_radius=10)
        button_color = COLORS["button_hover"] if is_hovered else COLORS["button"]
        pygame.draw.rect(self.screen, button_color, rect, border_radius=10)
        pygame.draw.rect(
            self.screen, COLORS["accent"], rect, 3, border_radius=10)

        if font_size is None:
            font_size = int(self.game.cell_size * 0.17)

        self.draw_text(text, font_size, x + w // 2,
                       y + h // 2, COLORS["white"])
        return rect

    def draw_gradient(self, color_1, color_2):
        for i in range(self.game.screen_size[1]):
            ratio = i / self.game.screen_size[1]
            color = tuple(
                int(color_1[j] + (color_2[j] - color_1[j]) * ratio) for j in range(3))
            pygame.draw.line(self.screen, color, (0, i),
                             (self.game.screen_size[0], i))

    def render_main_menu(self):
        self.screen.blit(self.game.backgroundgradiant_img, (0, 0))
        # self.draw_gradient(COLORS["menu_bg"], COLORS["mode_bg"])

        font_size = int(self.game.cell_size * 0.4)
        self.draw_text(
            "Bagchal", font_size, self.game.screen_size[0] // 2, 150, COLORS["accent"])

        self.draw_text("The Tigers and Goats Game", font_size//2,
                       self.game.screen_size[0] // 2, 220, COLORS["white"])

        play = self.game.play_btn_rect_main
        analysis = self.game.analysis_btn_rect
        exits = self.game.exit_btn_rect_main
        font_size = int(play.width * 0.1)
        self.draw_button("Play", play.x, play.y,
                         play.width, play.height, font_size)
        self.draw_button("Analysis", analysis.x, analysis.y,
                         analysis.width, analysis.height, font_size)
        self.draw_button("Exit", exits.x, exits.y,
                         exits.width, exits.height, font_size)

    def render_mode_select(self):
        self.screen.blit(self.game.backgroundgradiant_img, (0, 0))
        # self.draw_gradient(COLORS["menu_bg"], COLORS["mode_bg"])
        x_width = self.game.screen_size[0]
        y_height = self.game.screen_size[1]
        font_size = int(self.game.cell_size * 0.4)
        self.draw_text("Game Mode", font_size,
                       x_width // 2, 120, COLORS["accent"])

        # draw exit button top right
        exit_btn = self.game.exit_btn_rect
        self.draw_button("Exit", exit_btn.x, exit_btn.y,
                         exit_btn.width, exit_btn.height, 20)

        pvp = self.game.pvp_rect
        pvc_g = self.game.pvc_goat_rect
        pvc_t = self.game.pvc_tiger_rect
        cvc = self.game.cvc_rect

        self.screen.blit(self.game.playervsplayer_img,
                         (pvp.x, pvp.y))
        self.screen.blit(self.game.playervsgoat_img,
                         (pvc_g.x, pvc_g.y))
        self.screen.blit(self.game.playervsbagh_img,
                         (pvc_t.x, pvc_t.y))
        self.screen.blit(self.game.AivsAi, (cvc.x, cvc.y))

        # self.draw_button("PvP",  # player v player to fit inside the square
        #                  x_width * .056, y_height * 0.45, x_width * 0.18, y_height * 0.360)
        # self.draw_button("PvG",  # player v goat ai to fit inside the square
        #                  x_width * .292, y_height * 0.45, x_width * 0.18, y_height * 0.360)
        # self.draw_button("PvT",  # player v tiger ai to fit inside the square
        #                  x_width * .528, y_height * 0.45, x_width * 0.18, y_height * 0.360)
        # self.draw_button("CvC",  # computer v computer to fit inside the square
        #                  x_width * .764, y_height * 0.45, x_width * 0.18, y_height * 0.360)

        font_size = int(self.game.cell_size * 0.17)
        self.draw_text("Press ESC to go back", font_size,  # this is font size
                       self.game.screen_size[0] // 2, y_height - 50, COLORS["white"])

    def render_game(self):
        self.screen.blit(self.game.backgroundgradiant_img, (0, 0))
        # self.draw_gradient(COLORS["menu_bg"], COLORS["mode_bg"])

        # Clear board surface
        if self.game.board_surface:
            self.game.board_surface.fill(
                (0, 0, 0, 0))  # Transparent background

        self.draw_board()
        # Only show valid moves if not in replay mode
        if self.game.current_state != UIState.REPLAYING:
            self.draw_valid_moves()
        # draw exit button top right
        exit_btn = self.game.exit_btn_rect
        self.draw_button("Exit", exit_btn.x, exit_btn.y,
                         exit_btn.width, exit_btn.height, 20)

        if self.game.last_move_highlight:
            from_idx, _ = self.game.last_move_highlight
            row, col = divmod(from_idx, 5)
            x = col * self.game.cell_size + self.game.offset
            y = row * self.game.cell_size + self.game.offset
            alpha = max(0, 150 - (pygame.time.get_ticks() -
                        (self.game.last_move_frame or 0)) // 5)
            r, g, b, _ = COLORS["selected"]
            if alpha > 0:
                target_surface = self.game.board_surface if self.game.board_surface else self.screen
                s = pygame.Surface((40, 40), pygame.SRCALPHA)
                pygame.draw.circle(
                    s, (r, g, b, alpha), (20, 20), 20, 3)
                target_surface.blit(s, (x - 20, y - 20))

        self.draw_pieces()

        # Blit board surface to screen if using separate surface
        if self.game.board_surface:
            self.screen.blit(self.game.board_surface, self.game.board_position)

        self.draw_status()

        if self.is_debug:
            self.draw_circular_hitboxes()

        for particle in self.game.particles[:]:
            particle.update()
            # Particles are already created in screen coordinates, so draw directly on screen
            particle.draw(self.screen)
            if not particle.particles:
                self.game.particles.remove(particle)

        if self.game.ai_is_thinking:
            self.draw_pulsating_overlay("Thinking")

        switch_ai = self.game.switch_ai_btn_rect
        font_size = int(switch_ai.width * 0.07)
        self.draw_button(f"{self.game.get_agent_name()} Agent", switch_ai.x, switch_ai.y,
                         switch_ai.width, switch_ai.height, font_size)

    def draw_pulsating_overlay(self, text):
        x_width = self.game.screen_size[0]
        center_x = x_width // 2
        self.game.ai_pulse = (self.game.ai_pulse + 0.1) % (2 * 3.14159)
        alpha = int(128 + 127 * abs(pygame.math.Vector2(1,
                    0).rotate_rad(self.game.ai_pulse).x))
        overlay_width = 350
        overlay_height = 60
        overlay = pygame.Surface(
            (overlay_width, overlay_height), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (40, 40, 60, 200),
                         overlay.get_rect(), border_radius=10)
        pygame.draw.rect(overlay, (COLORS["ai_thinking"][0], COLORS["ai_thinking"][1],
                         COLORS["ai_thinking"][2], alpha), overlay.get_rect(), 3, border_radius=10)
        self.screen.blit(overlay, (self.game.screen_size[0] //
                         2 - overlay_width / 2, 10))
        dots = "." * (int(pygame.time.get_ticks() / 300) % 4)
        self.draw_text(f"{text}{dots}", 18, center_x,
                       40, COLORS["ai_thinking"])

    def render_game_over(self):
        pieces = {-1: "Goat", 1: "Tiger"}
        fade_alpha = min(255, (pygame.time.get_ticks(
        ) - self.game.game_over_timer + self.game.game_over_delay) // 400)
        pulse = abs(pygame.time.get_ticks() % 1600 - 800) / 400
        overlay = pygame.Surface(self.game.screen_size)
        overlay.fill(COLORS["game_over_bg"])
        overlay.set_alpha(fade_alpha)
        self.screen.blit(overlay, (0, 0))
        scale = min(1.2, max(0.3, pulse))

        game_over_font_size = int(self.game.cell_size * 0.4)
        self.draw_text("Game Over!", int(
            game_over_font_size * scale), self.game.screen_size[0] // 2, self.game.screen_size[1] // 2 - 200, COLORS["accent"])

        result_font_size = int(self.game.cell_size * 0.17)
        result_text = f"{pieces[self.game.game_state.get_result]} Won!" if self.game.game_state.get_result else "It's a Draw!"
        result_color = COLORS["win_tiger"] if self.game.game_state.get_result == Piece_TIGER else COLORS[
            "win_goat"] if self.game.game_state.get_result == Piece_GOAT else COLORS["white"]
        self.draw_text(result_text, int(
            result_font_size * scale), self.game.screen_size[0] // 2, self.game.screen_size[1] // 2 - 100, result_color)

        self.draw_text("Press SPACE to play again", result_font_size,
                       self.game.screen_size[0] // 2, self.game.screen_size[1] // 2 + 50, COLORS["white"])
        self.draw_text("Press ESC for main menu", result_font_size,
                       self.game.screen_size[0] // 2, self.game.screen_size[1] // 2 + 100, COLORS["white"])

    def render_analysis_mode(self):
        """Render the Analysis Mode screen showing last 5 games."""

        self.screen.blit(self.game.backgroundgradiant_img, (0, 0))
        # self.draw_gradient(COLORS["menu_bg"], COLORS["mode_bg"])

        # Title
        font_size = int(self.game.cell_size * 0.4)
        self.draw_text(
            "Analysis Mode", font_size,
            self.game.screen_size[0] // 2, 120, COLORS["accent"])

        # Get games
        games = get_last_games(5)

        if not games:
            # No games message
            font_size = int(self.game.cell_size * 0.17)
            self.draw_text(
                "No games found. Play some games first!",
                font_size, self.game.screen_size[0] // 2,
                self.game.screen_size[1] // 2, COLORS["white"])
        else:
            # Display games
            x_width = self.game.screen_size[0]
            y_start = 250
            button_height = 100
            button_spacing = 120
            button_width = x_width * 0.8
            button_x = x_width * 0.1

            mode_names = {
                "PvP": "Player vs Player",
                "PvC_Goat": "Player vs Computer (Goat)",
                "PvC_Tiger": "Player vs Computer (Tiger)",
                "CvC": "Computer vs Computer"
            }

            for i, game in enumerate(games):
                y_pos = y_start + i * button_spacing

                # Draw game button/card
                button_rect = pygame.Rect(
                    button_x, y_pos, button_width, button_height)
                mouse_pos = pygame.mouse.get_pos()
                is_hovered = button_rect.collidepoint(mouse_pos)
                button_color = COLORS["button_hover"] if is_hovered else COLORS["button"]

                pygame.draw.rect(self.screen, button_color,
                                 button_rect, border_radius=10)
                pygame.draw.rect(
                    self.screen, COLORS["accent"], button_rect, 3, border_radius=10)

                # Game info text
                font_size = int(button_width * 0.017)
                game_num = f"Game #{game['id']}"
                mode_text = mode_names.get(
                    game['game_mode'], game['game_mode'])
                winner_text = f"Winner: {game['winner']}" if game['winner'] else "Draw"
                timestamp_text = game['timestamp']
                moves_text = f"{game['total_moves']} moves"

                x_diff = 0.333 * button_width
                y_diff = 0.333 * button_height
                self.draw_text(game_num, font_size, button_x +
                               100, y_pos + 0.5 * button_height, COLORS["white"])
                self.draw_text(mode_text, font_size, button_x +
                               100 + x_diff, y_pos + y_diff, COLORS["white"])
                self.draw_text(winner_text, font_size, button_x +
                               100 + 2 * x_diff, y_pos + y_diff, COLORS["white"])
                self.draw_text(timestamp_text, font_size, button_x +
                               100 + 2 * x_diff, y_pos + 2 * y_diff, COLORS["white"])
                self.draw_text(moves_text, font_size, button_x +
                               100 + x_diff, y_pos + 2 * y_diff, COLORS["white"])

        # Back button
        mm_btn = self.game.analysis_mm_btn
        self.draw_button("Main Menu", mm_btn.x, mm_btn.y,
                         mm_btn.width, mm_btn.height)

    def render_replay_mode(self):
        """Render replay mode with board, controls, and AI suggestions."""
        # Render background
        self.screen.blit(self.game.backgroundgradiant_img, (0, 0))
        # self.draw_gradient(COLORS["menu_bg"], COLORS["mode_bg"])

        if self.game.board_surface:
            self.game.board_surface.fill(
                (0, 0, 0, 0))  # Transparent background

        self.draw_board()
        self.draw_pieces()

        # Highlight current move if replay_index > 0 (draw on board surface)
        if self.game.replay_index > 0 and self.game.replay_index <= len(self.game.replay_moves):
            move_data = self.game.replay_moves[self.game.replay_index - 1]
            from_idx = move_data["from"]
            to_idx = move_data["to"]
            target_surface = self.game.board_surface if self.game.board_surface else self.screen

            # Highlight from position
            row, col = divmod(from_idx, 5)
            x = col * self.game.cell_size + self.game.offset
            y = row * self.game.cell_size + self.game.offset
            s = pygame.Surface(
                (self.game.cell_size // 3, self.game.cell_size // 3), pygame.SRCALPHA)
            pygame.draw.circle(s, (*COLORS["selected"][:3], 150),
                               (self.game.cell_size // 6,
                                self.game.cell_size // 6),
                               self.game.cell_size // 6)
            target_surface.blit(
                s, (x - self.game.cell_size // 6, y - self.game.cell_size // 6))

            # Highlight to position
            row, col = divmod(to_idx, 5)
            x = col * self.game.cell_size + self.game.offset
            y = row * self.game.cell_size + self.game.offset
            s = pygame.Surface(
                (self.game.cell_size // 3, self.game.cell_size // 3), pygame.SRCALPHA)
            pygame.draw.circle(s, (*COLORS["valid_move"][:3], 150),
                               (self.game.cell_size // 6,
                                self.game.cell_size // 6),
                               self.game.cell_size // 6)
            target_surface.blit(
                s, (x - self.game.cell_size // 6, y - self.game.cell_size // 6))

        # Blit board surface to screen after all board rendering is done
        if self.game.board_surface:
            self.screen.blit(self.game.board_surface, self.game.board_position)

        # Draw status bar on screen (below board)
        self.draw_status()

        # Replay controls at bottom
        x_width = self.game.screen_size[0]
        center_x = x_width // 2

        # Previous button
        prev_text = "Previous"
        prev_btn = self.game.prev_btn_rect

        font_size = int(prev_btn.width * 0.1)

        self.draw_button(prev_text, prev_btn.x, prev_btn.y,
                         prev_btn.width, prev_btn.height, font_size)

        # Play/Pause button
        play_btn = self.game.play_btn_rect
        play_text = "Pause" if self.game.auto_play else "Play"
        self.draw_button(play_text, play_btn.x, play_btn.y,
                         play_btn.width, play_btn.height, font_size)

        # Next button
        next_btn = self.game.next_btn_rect
        next_text = "Next"
        self.draw_button(next_text, next_btn.x, next_btn.y,
                         next_btn.width, next_btn.height, font_size)

        # Exit replay button (top right)
        exit_btn = self.game.exit_btn_rect
        self.draw_button("Exit", exit_btn.x, exit_btn.y,
                         exit_btn.width, exit_btn.height, font_size - 2)

        # Move counter
        total_moves = len(self.game.replay_moves)
        current_move = self.game.replay_index
        move_counter_text = f"Move {current_move} of {total_moves}"
        self.draw_text(move_counter_text, 24, center_x,
                       self.game.screen_size[1] - 150, COLORS["white"])

        # Auto-play indicator
        if self.game.auto_play:
            self.draw_pulsating_overlay("Auto-playing")

            # AI Suggestion Panel (right side)
        suggestion_panel_x = x_width - 300
        suggestion_panel_y = 100
        suggestion_panel_width = 300
        suggestion_panel_height = 150

        panel_rect = pygame.Rect(
            suggestion_panel_x, suggestion_panel_y,
            suggestion_panel_width, suggestion_panel_height
        )
        pygame.draw.rect(
            self.screen, COLORS["board"], panel_rect, border_radius=10)
        pygame.draw.rect(
            self.screen, COLORS["accent"], panel_rect, 3, border_radius=10)

        # Title
        self.draw_text("AI Suggestion", 20,
                       suggestion_panel_x + suggestion_panel_width // 2,
                       suggestion_panel_y + 20, COLORS["accent"])

        # Get AI suggestion
        if not self.game.game_state.is_game_over:
            suggested_move = self.game.get_ai_suggestion_for_position()
            if suggested_move:
                from_pos, to_pos = suggested_move
                suggestion_text = f"Move: ({from_pos}, {to_pos})"
                agent_text = "Negamax"
            else:
                suggestion_text = "Calculating..."
                agent_text = ""

            self.draw_text(suggestion_text, 16,
                           suggestion_panel_x + suggestion_panel_width // 2,
                           suggestion_panel_y + 60, COLORS["white"])
            if agent_text:
                self.draw_text(f"Agent: {agent_text}", 14,
                               suggestion_panel_x + suggestion_panel_width // 2,
                               suggestion_panel_y + 90, COLORS["white"])
        else:
            self.draw_text("Game Over", 16,
                           suggestion_panel_x + suggestion_panel_width // 2,
                           suggestion_panel_y + 60, COLORS["white"])

    def draw_circular_hitboxes(self):
        """Debug: Draw circular hitboxes for all grid positions."""
        # Define hitbox radius (should match place_piece logic)
        hitbox_radius = self.game.cell_size * 0.35

        # Get mouse position for highlighting
        mouse_pos = pygame.mouse.get_pos()
        board_coords = self.game.get_board_coords_from_screen(
            mouse_pos[0], mouse_pos[1])

        for row in range(5):
            for col in range(5):
                # Calculate center position in board coordinates
                piece_x = col * self.game.cell_size + self.game.offset
                piece_y = row * self.game.cell_size + self.game.offset

                # Convert to screen coordinates
                screen_x = self.game.board_position[0] + piece_x
                screen_y = self.game.board_position[1] + piece_y

                # Check if mouse is over this hitbox
                is_hovered = False
                if board_coords:
                    board_x, board_y = board_coords
                    dx = board_x - piece_x
                    dy = board_y - piece_y
                    distance = (dx * dx + dy * dy) ** 0.5
                    is_hovered = distance < hitbox_radius

                # Draw hitbox circle on screen
                color = (0, 255, 0, 80) if is_hovered else (255, 0, 0, 50)
                s = pygame.Surface(
                    (int(hitbox_radius * 2), int(hitbox_radius * 2)), pygame.SRCALPHA)
                pygame.draw.circle(s, color, (int(hitbox_radius), int(
                    hitbox_radius)), int(hitbox_radius), 10)
                self.screen.blit(
                    s, (screen_x - hitbox_radius, screen_y - hitbox_radius))

                # Draw center point
                pygame.draw.circle(self.screen, (255, 0, 0),
                                   (int(screen_x), int(screen_y)), 3)

                # Draw grid coordinates
                font = pygame.font.SysFont(None, 25)
                idx = col + row * 5
                text = font.render(f"{idx}", True, (255, 255, 255))
                self.screen.blit(text, (screen_x - 8, screen_y - 25))

        # Draw mouse position info
        if board_coords:
            font = pygame.font.SysFont(None, 20)
            board_x, board_y = board_coords
            text = font.render(
                f"Board: ({int(board_x)}, {int(board_y)})", True, (255, 255, 255))
            self.screen.blit(text, (10, 10))
