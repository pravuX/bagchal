import pygame


# REMEMBER:
# x -> cols : width
# y -> rows : height


class Game:
    def __init__(self,
                 screen_size=(854, 480),
                 caption="pygame-starter",
                 grid_dim=150,
                 tick_speed=30):  # fps
        pygame.init()
        pygame.display.set_caption(caption)

        # Board Game State
        self.grid_dim = grid_dim

        self.grid_width = self.grid_dim * 5
        self.grid_height = self.grid_dim * 5
        self.screen_size = (self.grid_width, self.grid_height)

        self.grid_cols = self.grid_width // self.grid_dim
        self.grid_rows = self.grid_height // self.grid_dim

        self.offset = self.grid_dim // 2  # for drawing the lines
        self.board_width = self.grid_width - self.grid_dim
        self.board_height = self.grid_height - self.grid_dim

        self.mouse_pos = (-1, -1)
        # left, middle, right buttons
        self.mouse_pressed = (False, False, False)

        # Adjacency List
        self.graph = {0: [], 1: [], 2: [], 3: [], 4: [],
                      5: [], 6: [], 7: [], 8: [], 9: [],
                      10: [], 11: [], 12: [], 13: [], 14: [],
                      15: [], 16: [], 17: [], 18: [], 19: [],
                      20: [], 21: [], 22: [], 23: [], 24: []}
        # display different images depending on the state
        # 0 = goat, 1 = tiger, -1 = emtpy
        self.state = [-1] * 25

        # Pygame State
        self.screen = pygame.display.set_mode(self.screen_size)
        self.clock = pygame.time.Clock()
        self.tick_speed = tick_speed

        self.running = True
        self.surfs = []  # for loading images and stuff
        self.keys = []

        self.colors = ["gray", "black"]

    def should_quit(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or self.keys[pygame.K_q]:
                self.running = False

    def draw_board(self):
        pygame.draw.line(self.screen, 0, (0+self.offset, 0+self.offset),
                         (self.board_width+self.offset, self.board_height+self.offset), 3)
        pygame.draw.line(self.screen, 0, (0+self.offset, self.board_width+self.offset),
                         (self.board_height+self.offset, 0+self.offset), 3)

        # /
        # \
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
            pygame.draw.line(self.screen, 0, (i*self.grid_dim+self.offset, 0+self.offset),
                             (i*self.grid_dim+self.offset, self.grid_height+self.offset-self.grid_dim), 2)
        # horizontal lines
        for i in range(self.grid_rows):
            pygame.draw.line(self.screen, 0, (0+self.offset, i*self.grid_dim+self.offset),
                             (self.grid_width+self.offset-self.grid_dim, i*self.grid_dim+self.offset), 2)

    def grid_pos(self, col, row):
        # given col, row returns the corresponding grid position(x, y) or cell position(x, y)
        return col * self.grid_dim, row * self.grid_dim

    def draw_grid_lines(self):
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                sqr_x, sqr_y = self.grid_pos(col, row)
                sqr = pygame.Rect(sqr_x, sqr_y, self.grid_dim, self.grid_dim)
                pygame.draw.rect(self.screen, "gray", sqr, 1)  # border

    def draw_pieces(self):
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                state = self.state[col+row*self.grid_cols]
                color = self.colors[state]  # image here instead of color

                if state >= 0:  # we don't draw empty cells!
                    x, y = self.grid_pos(col, row)
                    # draw a point
                    pygame.draw.circle(
                        self.screen, color, (x+self.offset, y+self.offset), self.offset//4)

    def place_piece(self):
        m_left, _, _ = self.mouse_pressed
        mouse_x, mouse_y = self.mouse_pos
        if m_left:
            col = mouse_x // self.grid_dim
            row = mouse_y // self.grid_dim
            cell_pos = col+row*self.grid_cols  # 2d to 1d index

            state = self.state[cell_pos]
            if state == -1:
                print(mouse_x, mouse_y)
                self.state[cell_pos] = 1

    def game(self):
        self.draw_grid_lines()  # for testing only
        self.draw_board()
        self.draw_pieces()
        self.place_piece()  # on mouse press

    def reset_screen(self):
        self.screen.fill((255, 255, 255))

    def update(self):
        self.keys = pygame.key.get_pressed()
        self.mouse_pos = pygame.mouse.get_pos()
        self.mouse_pressed = pygame.mouse.get_pressed()
        self.should_quit()
        self.reset_screen()
        self.game()
        for surf in self.surfs:
            self.screen.blit(surf, (0, 0))
        pygame.display.update()
        self.clock.tick(self.tick_speed)

    def run(self):
        while self.running:
            self.update()
        pygame.quit()


if __name__ == "__main__":
    game = Game()
    game.run()
