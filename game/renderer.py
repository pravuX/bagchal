import pygame
from .constants import COLORS, ASSETS
from bagchal import Piece_GOAT, Piece_TIGER, extract_indices_fast, BOARD_MASK


class GameRenderer:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen

    def draw_board(self):
        board_rect = pygame.Rect(
            self.game.offset, self.game.offset, self.game.board_width, self.game.board_height)
        pygame.draw.rect(self.screen, COLORS["board_light"], board_rect)

        pygame.draw.rect(
            self.screen, COLORS["board"], board_rect, border_radius=10)

        line_color = COLORS["board_light"]

        pygame.draw.line(self.screen, line_color, (self.game.offset, self.game.offset), (
            self.game.board_width + self.game.offset, self.game.board_height + self.game.offset), 5)
        pygame.draw.line(self.screen, line_color, (self.game.offset, self.game.board_height +
                         self.game.offset), (self.game.board_width + self.game.offset, self.game.offset), 5)
        pygame.draw.line(self.screen, line_color, (self.game.offset, self.game.board_height // 2 +
                         self.game.offset), (self.game.board_width // 2 + self.game.offset, self.game.offset), 4)
        pygame.draw.line(self.screen, line_color, (self.game.offset, self.game.board_height // 2 + self.game.offset),
                         (self.game.board_width // 2 + self.game.offset, self.game.board_height + self.game.offset), 4)
        pygame.draw.line(self.screen, line_color, (self.game.board_width + self.game.offset, self.game.board_height //
                         2 + self.game.offset), (self.game.board_width // 2 + self.game.offset, self.game.offset), 4)
        pygame.draw.line(self.screen, line_color, (self.game.board_width + self.game.offset, self.game.board_height // 2 +
                         self.game.offset), (self.game.board_width // 2 + self.game.offset, self.game.board_height + self.game.offset), 4)

        for i in range(self.game.grid_cols):
            pygame.draw.line(self.screen, line_color, (i * self.game.cell_size + self.game.offset, self.game.offset),
                             (i * self.game.cell_size + self.game.offset, self.game.grid_height - self.game.cell_size + self.game.offset), 4)
        for i in range(self.game.grid_rows):
            pygame.draw.line(self.screen, line_color, (self.game.offset, i * self.game.cell_size + self.game.offset),
                             (self.game.grid_width - self.game.cell_size + self.game.offset, i * self.game.cell_size + self.game.offset), 4)

        for row in range(5):
            for col in range(5):
                x = col * self.game.cell_size + self.game.offset
                y = row * self.game.cell_size + self.game.offset
                pygame.draw.circle(self.screen, COLORS["accent"], (x, y), 7)
                pygame.draw.circle(self.screen, COLORS["board"], (x, y), 5)
                idx = col + row * self.game.grid_cols

                # Draw valid moves for goats during placement phase
                occupied_bb = self.game.game_state.tigers_bb | self.game.game_state.goats_bb
                empty_bb = ~occupied_bb & BOARD_MASK
                if empty_bb & (1 << idx) and self.game.game_state.turn == Piece_GOAT and self.game.game_state.goats_to_place > 0:
                    self.draw_pulsating_circle(x, y)

    def draw_valid_moves(self):
        if not self.game.valid_moves:
            return
        for move in self.game.valid_moves:
            to_idx = move[1]
            row, col = divmod(to_idx, 5)
            x = col * self.game.cell_size + self.game.offset
            y = row * self.game.cell_size + self.game.offset
            self.draw_pulsating_circle(x, y)

    def draw_pulsating_circle(self, x, y):
        pulse = abs(pygame.time.get_ticks() % 800 - 400) / 400
        radius = int(self.game.cell_size//5 + 5 * pulse)
        s = pygame.Surface(
            (radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(
            s, COLORS["valid_move"], (radius, radius), radius)
        self.screen.blit(s, (x - radius, y - radius))

    def draw_pieces(self):
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
            self.screen.blit(circle_surface, circle_rect)

        for i in tiger_positions:
            row, col = divmod(i, 5)
            center_x = col * self.game.cell_size + self.game.offset
            center_y = row * self.game.cell_size + self.game.offset

            img = self.game.bagh_selected if i == self.game.selected_cell else self.game.bagh_img
            img_rect = img.get_rect(center=(center_x, center_y))
            self.screen.blit(img, img_rect)

        for i in goat_positions:
            row, col = divmod(i, 5)
            center_x = col * self.game.cell_size + self.game.offset
            center_y = row * self.game.cell_size + self.game.offset

            img = self.game.goat_selected if i == self.game.selected_cell else self.game.goat_img
            img_rect = img.get_rect(center=(center_x, center_y))
            self.screen.blit(img, img_rect)

    def draw_status(self):
        status_y = self.game.grid_height
        panel_height = 100
        panel_rect = pygame.Rect(
            0, status_y, self.game.grid_width, panel_height)
        pygame.draw.rect(self.screen, COLORS["board"], panel_rect)

        turn_text = "Tiger's Turn" if self.game.game_state.turn == 1 else "Goat's Turn"
        goat_text = f"Goats Left:{self.game.game_state.goats_to_place}"
        eaten_text = f"Goats Eaten:{self.game.game_state.goats_eaten}"
        trapped_text = f"TigersTrapped:{self.game.game_state.trapped_tiger_count}"

        padding = 50  # within button
        spacing = 10  # between buttons
        height = panel_height // 2
        width = self.game.grid_width // 4 + padding
        center = self.game.grid_width // 2 - width // 2
        y = status_y + panel_height // 4

        font_size = int(self.game.cell_size * 0.1)

        self.draw_button(turn_text, center,
                         status_y - height//1.5, width, height, font_size)

        self.draw_button(goat_text, 0 + spacing,
                         y, width, height, font_size)

        self.draw_button(eaten_text, center,
                         y, width, height, font_size)

        self.draw_button(trapped_text, self.game.grid_width -
                         width - spacing, y, width, height, font_size)

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
        self.draw_gradient(COLORS["menu_bg"], COLORS["mode_bg"])

        font_size = int(self.game.cell_size * 0.4)
        self.draw_text(
            "Bagchal", font_size, self.game.screen_size[0] // 2, 150, COLORS["accent"])

        font_size = int(self.game.cell_size * 0.17)
        self.draw_text("The Tigers and Goats Game", font_size,
                       self.game.screen_size[0] // 2, 220, COLORS["white"])
        self.draw_button(
            "Play", self.game.screen_size[0]//2 - 100, 350, 200, 60)
        self.draw_button(
            "Exit", self.game.screen_size[0]//2 - 100, 450, 200, 60)

    def render_mode_select(self):
        self.draw_gradient(COLORS["menu_bg"], COLORS["mode_bg"])

        font_size = int(self.game.cell_size * 0.4)
        self.draw_text("Game Mode", font_size,
                       self.game.screen_size[0] // 2, 120, COLORS["accent"])
        self.draw_button("Player vs Player",
                         self.game.screen_size[0] // 2 - 275, 300, 550, 60)
        self.draw_button("Player vs Goat AI",
                         self.game.screen_size[0] // 2 - 300, 380, 600, 60)
        self.draw_button("Player vs Tiger AI",
                         self.game.screen_size[0] // 2 - 300, 460, 600, 60)
        self.draw_button("Computer vs Computer",
                         self.game.screen_size[0] // 2 - 325, 540, 650, 60)

        font_size = int(self.game.cell_size * 0.17)
        self.draw_text("Press ESC to go back", font_size,
                       self.game.screen_size[0] // 2, 650, COLORS["white"])

    def render_game(self):

        self.draw_gradient(COLORS["menu_bg"], COLORS["mode_bg"])

        self.draw_board()
        self.draw_valid_moves()

        if self.game.last_move_highlight:
            from_idx, _ = self.game.last_move_highlight
            row, col = divmod(from_idx, 5)
            x = col * self.game.cell_size + self.game.offset
            y = row * self.game.cell_size + self.game.offset
            alpha = max(0, 150 - (pygame.time.get_ticks() -
                        (self.game.last_move_frame or 0)) // 5)
            r, g, b, _ = COLORS["selected"]
            if alpha > 0:
                s = pygame.Surface((40, 40), pygame.SRCALPHA)
                pygame.draw.circle(
                    s, (r, g, b, alpha), (20, 20), 20, 3)
                self.screen.blit(s, (x - 20, y - 20))

        self.draw_pieces()
        self.draw_status()
        for particle in self.game.particles[:]:
            particle.update()
            particle.draw(self.screen)
            if not particle.particles:
                self.game.particles.remove(particle)

        if self.game.ai_is_thinking:
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
            self.screen.blit(overlay, (self.game.grid_width //
                             2 - overlay_width / 2, 10))

            font_size = int(self.game.cell_size * 0.1)
            font = pygame.font.Font(ASSETS["font"], font_size)
            dots = "." * (int(pygame.time.get_ticks() / 300) % 4)
            text = font.render(
                f"AI is Thinking{dots}", True, COLORS["ai_thinking"])
            text_rect = text.get_rect(center=(self.game.grid_width // 2, 40))
            self.screen.blit(text, text_rect)

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
