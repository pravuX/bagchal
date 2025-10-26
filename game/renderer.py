import pygame
from .constants import COLORS, ASSETS
from bagchal import extract_indices_fast


class GameRenderer:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen

    def draw_board(self):
        """Enhanced board drawing with shadows and gradients"""
        board_rect = pygame.Rect(
            self.game.offset, self.game.offset, self.game.board_width, self.game.board_height)
        pygame.draw.rect(self.screen, COLORS["board_light"], board_rect)

        shadow_offset = 5
        shadow_rect = board_rect.inflate(shadow_offset * 2, shadow_offset * 2)
        pygame.draw.rect(self.screen, (0, 0, 0, 30),
                         shadow_rect, border_radius=10)
        pygame.draw.rect(
            self.screen, COLORS["board"], board_rect, border_radius=8)

        line_color = COLORS["board_light"]

        pygame.draw.line(self.screen, line_color, (self.game.offset, self.game.offset), (
            self.game.board_width + self.game.offset, self.game.board_height + self.game.offset), 4)
        pygame.draw.line(self.screen, line_color, (self.game.offset, self.game.board_height +
                         self.game.offset), (self.game.board_width + self.game.offset, self.game.offset), 4)
        pygame.draw.line(self.screen, line_color, (self.game.offset, self.game.board_height // 2 +
                         self.game.offset), (self.game.board_width // 2 + self.game.offset, self.game.offset), 3)
        pygame.draw.line(self.screen, line_color, (self.game.offset, self.game.board_height // 2 + self.game.offset),
                         (self.game.board_width // 2 + self.game.offset, self.game.board_height + self.game.offset), 3)
        pygame.draw.line(self.screen, line_color, (self.game.board_width + self.game.offset, self.game.board_height //
                         2 + self.game.offset), (self.game.board_width // 2 + self.game.offset, self.game.offset), 3)
        pygame.draw.line(self.screen, line_color, (self.game.board_width + self.game.offset, self.game.board_height // 2 +
                         self.game.offset), (self.game.board_width // 2 + self.game.offset, self.game.board_height + self.game.offset), 3)

        for i in range(self.game.grid_cols):
            pygame.draw.line(self.screen, line_color, (i * self.game.cell_size + self.game.offset, self.game.offset),
                             (i * self.game.cell_size + self.game.offset, self.game.grid_height - self.game.cell_size + self.game.offset), 3)
        for i in range(self.game.grid_rows):
            pygame.draw.line(self.screen, line_color, (self.game.offset, i * self.game.cell_size + self.game.offset),
                             (self.game.grid_width - self.game.cell_size + self.game.offset, i * self.game.cell_size + self.game.offset), 3)

        for row in range(5):
            for col in range(5):
                x = col * self.game.cell_size + self.game.offset
                y = row * self.game.cell_size + self.game.offset
                pygame.draw.circle(self.screen, COLORS["accent"], (x, y), 6)
                pygame.draw.circle(self.screen, COLORS["board"], (x, y), 4)

    def draw_valid_moves(self):
        if not self.game.valid_moves:
            return
        for move in self.game.valid_moves:
            to_idx = move[1]
            row, col = divmod(to_idx, 5)
            x = col * self.game.cell_size + self.game.offset
            y = row * self.game.cell_size + self.game.offset
            pulse = abs(pygame.time.get_ticks() % 1000 - 500) / 500
            radius = int(15 + 5 * pulse)
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                s, COLORS["valid_move"], (radius, radius), radius)
            self.screen.blit(s, (x - radius, y - radius))

    def draw_pieces(self):
        tiger_positions = extract_indices_fast(self.game.game_state.tigers_bb)
        goat_positions = extract_indices_fast(self.game.game_state.goats_bb)
        shadow_offset = 3
        for positions, is_tiger in [(tiger_positions, True), (goat_positions, False)]:
            for i in positions:
                row, col = divmod(i, 5)
                x, y = self.game.cell_to_pixel(col, row)
                x, y = x + self.game.offset, y + self.game.offset
                shadow_surf = pygame.Surface(
                    (self.game.cell_size // 2, self.game.cell_size // 2), pygame.SRCALPHA)
                pygame.draw.circle(shadow_surf, (0, 0, 0, 60), (self.game.cell_size //
                                   4, self.game.cell_size // 4), self.game.cell_size // 5)
                self.screen.blit(shadow_surf, (x - self.game.cell_size // 4 +
                                 shadow_offset, y - self.game.cell_size // 4 + shadow_offset))

        if self.game.selected_cell is not None:
            row, col = divmod(self.game.selected_cell, 5)
            x, y = self.game.cell_to_pixel(col, row)
            x, y = x + self.game.offset, y + self.game.offset
            pulse = abs(pygame.time.get_ticks() % 800 - 400) / 400
            radius = int(50 + 10 * pulse)
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                s, COLORS["selected"], (radius, radius), radius, 4)
            self.screen.blit(s, (x - radius, y - radius))

        for i in tiger_positions:
            row, col = divmod(i, 5)
            x, y = self.game.cell_to_pixel(col, row)
            x, y = x + self.game.offset - self.game.cell_size // 4, y + \
                self.game.offset - self.game.cell_size // 4
            img = self.game.bagh_selected if i == self.game.selected_cell else self.game.bagh_img
            self.screen.blit(img, (x, y))

        for i in goat_positions:
            row, col = divmod(i, 5)
            x, y = self.game.cell_to_pixel(col, row)
            x, y = x + self.game.offset - self.game.cell_size // 4, y + \
                self.game.offset - self.game.cell_size // 4
            img = self.game.goat_selected if i == self.game.selected_cell else self.game.goat_img
            self.screen.blit(img, (x, y))

    def draw_status(self):
        status_y = self.game.grid_height + 10
        panel_rect = pygame.Rect(
            0, self.game.grid_height, self.game.grid_width, 100)
        pygame.draw.rect(self.screen, COLORS["board"], panel_rect)
        font = pygame.font.SysFont(None, 36)
        turn_text = "Tiger's Turn" if self.game.game_state.turn == 1 else "Goat's Turn"
        turn_color = (255, 100, 50) if self.game.game_state.turn == 1 else (
            100, 200, 100)
        turn_surf = font.render(turn_text, True, turn_color)
        self.screen.blit(turn_surf, (20, status_y))
        stats_font = pygame.font.SysFont(None, 32)
        goat_text = stats_font.render(
            f"Goats Left: {self.game.game_state.goats_to_place}", True, COLORS["white"])
        eaten_text = stats_font.render(
            f"Goats Eaten: {self.game.game_state.goats_eaten}", True, COLORS["white"])
        trapped_text = stats_font.render(
            f"Tigers Trapped: {self.game.game_state.trapped_tiger_count}", True, COLORS["white"])
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
        self.draw_text(text, 32, x + w // 2, y + h // 2, COLORS["white"])
        return rect

    def render_main_menu(self):
        for i in range(self.game.screen_size[1]):
            ratio = i / self.game.screen_size[1]
            color = tuple(int(COLORS["menu_bg"][j] + (COLORS["mode_bg"]
                          [j] - COLORS["menu_bg"][j]) * ratio) for j in range(3))
            pygame.draw.line(self.screen, color, (0, i),
                             (self.game.screen_size[0], i))
        self.draw_text(
            "Bagchal", 72, self.game.screen_size[0] // 2, 150, COLORS["accent"])
        self.draw_text("The Tiger and Goats Game", 28,
                       self.game.screen_size[0] // 2, 220, COLORS["white"])
        self.draw_button(
            "Play", self.game.screen_size[0]//2 - 100, 350, 200, 60)
        self.draw_button(
            "Exit", self.game.screen_size[0]//2 - 100, 450, 200, 60)

    def render_mode_select(self):
        for i in range(self.game.screen_size[1]):
            ratio = i / self.game.screen_size[1]
            color = tuple(int(COLORS["mode_bg"][j] + (COLORS["menu_bg"]
                          [j] - COLORS["menu_bg"][j]) * ratio) for j in range(3))
            pygame.draw.line(self.screen, color, (0, i),
                             (self.game.screen_size[0], i))
        self.draw_text("Select Game Mode", 64,
                       self.game.screen_size[0] // 2, 120, COLORS["accent"])
        self.draw_button("Player vs Player",
                         self.game.screen_size[0] // 2 - 275, 300, 550, 60)
        self.draw_button("Player vs Goat AI",
                         self.game.screen_size[0] // 2 - 300, 380, 600, 60)
        self.draw_button("Player vs Tiger AI",
                         self.game.screen_size[0] // 2 - 300, 460, 600, 60)
        self.draw_button("Computer vs Computer",
                         self.game.screen_size[0] // 2 - 325, 540, 650, 60)
        self.draw_text("Press ESC to go back", 24,
                       self.game.screen_size[0] // 2, 650, COLORS["white"])

    def render_game(self):
        self.screen.fill(COLORS["bg"])
        self.draw_board()
        self.draw_valid_moves()
        if self.game.last_move_highlight:
            from_idx, to_idx = self.game.last_move_highlight
            for idx in [from_idx, to_idx]:
                row, col = divmod(idx, 5)
                x = col * self.game.cell_size + self.game.offset
                y = row * self.game.cell_size + self.game.offset
                alpha = max(0, 150 - (pygame.time.get_ticks() -
                            (self.game.last_move_frame or 0)) // 10)
                if alpha > 0:
                    s = pygame.Surface((40, 40), pygame.SRCALPHA)
                    pygame.draw.circle(
                        s, (255, 200, 100, alpha), (20, 20), 20, 3)
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
            overlay = pygame.Surface((300, 60), pygame.SRCALPHA)
            pygame.draw.rect(overlay, (40, 40, 60, 200),
                             overlay.get_rect(), border_radius=10)
            pygame.draw.rect(overlay, (COLORS["ai_thinking"][0], COLORS["ai_thinking"][1],
                             COLORS["ai_thinking"][2], alpha), overlay.get_rect(), 3, border_radius=10)
            self.screen.blit(overlay, (self.game.grid_width // 2 - 150, 20))
            font = pygame.font.SysFont(None, 32)
            dots = "." * (int(pygame.time.get_ticks() / 300) % 4)
            text = font.render(
                f"AI Thinking{dots}", True, COLORS["ai_thinking"])
            text_rect = text.get_rect(center=(self.game.grid_width // 2, 50))
            self.screen.blit(text, text_rect)

    def render_game_over(self):
        pieces = {-1: "Goat", 1: "Tiger"}
        fade_alpha = min(255, (pygame.time.get_ticks(
        ) - self.game.game_over_timer + self.game.game_over_delay) // 3)
        overlay = pygame.Surface(self.game.screen_size)
        overlay.fill(COLORS["game_over_bg"])
        overlay.set_alpha(fade_alpha)
        self.screen.blit(overlay, (0, 0))
        scale = min(1.0, fade_alpha / 255)
        self.draw_text("Game Over!", int(
            72 * scale), self.game.screen_size[0] // 2, self.game.screen_size[1] // 2 - 200, COLORS["accent"])
        result_text = f"{pieces[self.game.game_state.get_result]} Won!" if self.game.game_state.get_result else "It's a Draw!"
        result_color = (255, 150, 50) if self.game.game_state.get_result == 1 else (
            100, 255, 150) if self.game.game_state.get_result == -1 else COLORS["white"]
        self.draw_text(result_text, int(
            48 * scale), self.game.screen_size[0] // 2, self.game.screen_size[1] // 2 - 100, result_color)
        pulse = abs(pygame.time.get_ticks() % 1500 - 750) / 750
        instruction_alpha = int(150 + 105 * pulse)
        self.draw_text("Press SPACE to play again", 32,
                       self.game.screen_size[0] // 2, self.game.screen_size[1] // 2 + 50, COLORS["white"])
        self.draw_text("Press ESC for main menu", 32,
                       self.game.screen_size[0] // 2, self.game.screen_size[1] // 2 + 100, COLORS["white"])
        stats_y = self.game.screen_size[1] // 2 + 180
        stats_font_size = 28
        self.draw_text(f"Goats Eaten: {self.game.game_state.goats_eaten}", stats_font_size,
                       self.game.screen_size[0] // 2 - 150, stats_y, COLORS["white"])
        self.draw_text(f"Tigers Trapped: {self.game.game_state.trapped_tiger_count}",
                       stats_font_size, self.game.screen_size[0] // 2 + 150, stats_y, COLORS["white"])
