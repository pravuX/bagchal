import pygame
import math
from enum import IntEnum


# REMEMBER:
# x -> cols : width
# y -> rows : height

class Piece(IntEnum):
    EMTPY = -1
    GOAT = 0
    TIGER = 1


class Game:
    def __init__(self,
                 screen_size=(854, 480),
                 caption="bagchal",
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

        # self.mouse_pos = (-1, -1)
        # left, middle, right buttons
        # self.mouse_pressed = (False, False, False)
        self.selected_cell = None

        # Adjacency List
        self.graph = {0:  [1, 5, 6], 1:  [0, 2, 6], 2:  [1, 3, 6, 7, 8], 3:  [2, 4, 8], 4:  [3, 8, 9],
                      5:  [0, 6, 10], 6:  [0, 1, 2, 5, 7, 10, 11, 12], 7:  [2, 6, 8, 12], 8:  [2, 3, 4, 7, 9, 12, 13, 14], 9:  [4, 8, 14],
                      10: [5, 6, 11, 15, 16], 11: [6, 10, 12, 16], 12: [6, 7, 8, 11, 13, 16, 17, 18], 13: [8, 12, 14, 18], 14: [8, 9, 13, 18, 19],
                      15: [10, 16, 20], 16: [10, 11, 12, 15, 17, 20, 21, 22], 17: [12, 16, 18, 22], 18: [12, 13, 14, 17, 19, 22, 23, 24], 19: [14, 18, 24],
                      20: [15, 16, 21], 21: [16, 20, 22], 22: [16, 17, 18, 21, 23], 23: [18, 22, 24], 24: [18, 19, 23]}
        # display different images depending on the state
        self.state = [Piece.EMTPY] * 25

        self.turn = Piece.GOAT

        # Pygame State
        self.screen = pygame.display.set_mode(self.screen_size)
        self.clock = pygame.time.Clock()
        self.tick_speed = tick_speed
        # self.count = 4

        self.running = True
        self.surfs = []  # for loading images and stuff
        self.keys = []

        self.colors = ["gray", "black"]  # Piece.GOAT, Piece.TIGER

        # @UTSAV
        # initialize board
        # by placing 4 tigers
        # call initialize_board
        self.initialize_board()

    def initialize_board(self):
        self.state[0] = Piece.TIGER
        self.state[self.grid_cols - 1] = Piece.TIGER
        self.state[self.grid_rows * (self.grid_cols - 1)] = Piece.TIGER
        self.state[self.grid_cols * self.grid_rows - 1] = Piece.TIGER

    def change_turn(self):
        # self.turn *= -1
        self.turn = 1 if self.turn == 0 else 0

    def reset_game(self):
        # @UTSAV
        # empty all the cells,
        # i.e. self.state = [Piece.EMTPY] * 25
        # call initialize_board
        # reset turn
        # we call this when the game reaches a terminal state
        ...

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or self.keys[pygame.K_q]:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.place_piece(event.pos)
                # @UTSAV
                # implement a check_end_game() method and call it here
                # or maybe from withing game() after handle_events
                # which is better?

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
                        self.screen, color, (x + self.offset, y + self.offset), self.offset//4)

                # visualize selected_cell
                if self.selected_cell == col + row * self.grid_cols:
                    pygame.draw.circle(
                        self.screen, "darksalmon", (x + self.offset, y + self.offset), self.offset // 4 + 5, 5)

    def place_piece(self, pos):
        mouse_x, mouse_y = pos
        col = mouse_x // self.grid_dim
        row = mouse_y // self.grid_dim
        cell_pos = col+row*self.grid_cols  # 2d to 1d index

        state = self.state[cell_pos]

        # If no piece is selected:
        #     Click on an empty cell → place a new piece (1).
        #     Click on an existing piece (1) → mark it as selected.
        # If a piece is selected:
        #     Click on an empty cell → move it there.
        #     Click on any cell (even invalid move) → cancel selection.

        if self.selected_cell is None:
            # change this by turn
            if state == Piece.EMTPY:
                if self.turn == Piece.GOAT:
                    self.state[cell_pos] = Piece.GOAT
                    self.change_turn()
            elif state == self.turn:
                self.selected_cell = cell_pos
        else:
            if state == Piece.EMTPY:
                # move to adjacent empty
                if cell_pos in self.graph.get(self.selected_cell, []):
                    if self.state[cell_pos] != Piece.TIGER or self.state != Piece.GOAT:
                        self.state[self.selected_cell] = Piece.EMTPY
                        self.state[cell_pos] = self.turn
                        self.change_turn()
                # @UTSAV
                # this is where we implement logic for "eating" goats
                bali_goat = math.ceil((self.selected_cell + cell_pos)/2)
                if (self.state[self.selected_cell] == Piece.TIGER) and (bali_goat in self.graph.get(self.selected_cell, [])):
                    if (self.state[bali_goat] == Piece.GOAT):
                        self.state[bali_goat] = Piece.EMTPY
                        self.state[self.selected_cell] = Piece.EMTPY
                        self.state[cell_pos] = self.turn
                        self.change_turn()

            self.selected_cell = None

    def game(self):
        self.draw_grid_lines()  # for testing only
        self.draw_board()
        # self.initialize_board()
        self.draw_pieces()
        self.handle_events()

    def reset_screen(self):
        self.screen.fill("antiquewhite")

    def update(self):
        self.keys = pygame.key.get_pressed()
        # self.mouse_pos = pygame.mouse.get_pos()
        # self.mouse_pressed = pygame.mouse.get_pressed()
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
