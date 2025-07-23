import pygame
import math
from enum import IntEnum


# REMEMBER:
# x -> cols : width
# y -> rows : height

class Piece(IntEnum):
    GOAT = -1
    EMPTY = 0
    TIGER = 1


class Game:
    def play(): #play screen
        pygame.display.set_caption("Play")
        
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
        self.state = [Piece.EMPTY] * 25

        self.turn = Piece.GOAT

        # Pygame State
        self.screen = pygame.display.set_mode(self.screen_size)
        self.clock = pygame.time.Clock()
        self.tick_speed = tick_speed
        self.goat_count = 20
        self.eaten_goat_count = 0

        # loading the images
        self.bagh_img = pygame.image.load("assets/bagh.png").convert_alpha()
        self.goat_img = pygame.image.load("assets/goat.png").convert_alpha()

        #resizing to make smol
        self.bagh_img = pygame.transform.smoothscale(self.bagh_img, (self.grid_dim, self.grid_dim))
        self.goat_img = pygame.transform.smoothscale(self.goat_img, (self.grid_dim, self.grid_dim))

        self.running = True
        self.surfs = []  # for loading images and stuff
        self.keys = []

        self.colors = {
            Piece.GOAT: "gray",
            Piece.TIGER: "black"
        }

        # maintain tiger states
        self.trapped_tiger_count = 0

        # initialize the board with TIGER
        self.initialize_board()

    def initialize_board(self):
        self.pos_tiger = [0, 4, 20, 24]

        self.state[self.pos_tiger[0]] = Piece.TIGER
        self.state[self.pos_tiger[1]] = Piece.TIGER
        self.state[self.pos_tiger[2]] = Piece.TIGER
        self.state[self.pos_tiger[3]] = Piece.TIGER

    def change_turn(self):
        self.turn *= -1

    def reset_game(self):
        self.state = [Piece.EMPTY] * 25
        self.initialize_board()
        self.turn = Piece.GOAT
        self.trapped_tiger_count = 0
        self.eaten_goat_count = 0
        self.goat_count = 20

    def update_tiger_pos(self):
        self.pos_tiger = [idx for idx, state in enumerate(self.state) if state == 1]

    def is_trapped(self, tiger):
        # check adjacent nodes of tiger
        # return false if at least one node is empty
        # if the adjacent node has a goat
        # check if that can be "eaten"
        # return false
        # otherwise return true
        for adj in self.graph[tiger]:
            if self.state[adj] == Piece.EMPTY:
                return False
            elif self.state[adj] == Piece.GOAT:
                capture_pos = adj - (tiger - adj)
                if capture_pos in self.graph[adj] and self.state[capture_pos] == Piece.EMPTY:
                    return False
        return True

    def update_trapped_tiger(self):
        count = 0
        for tiger in self.pos_tiger:
            if (self.is_trapped(tiger)):
                count += 1
        self.trapped_tiger_count = count

    def check_end_game(self):
        if self.trapped_tiger_count == 4:
            print("Goat Wins")
            self.reset_game()
        elif self.eaten_goat_count > 12:
            print("Tiger Wins")
            self.reset_game()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or self.keys[pygame.K_q]:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.place_piece(event.pos)
                self.update_tiger_pos()
                self.update_trapped_tiger()
                self.check_end_game()

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

                # if state != 0:  # we don't draw empty cells!
                #     color = self.colors[state]  # image here instead of color
                #     x, y = self.grid_pos(col, row)
                #     # draw a point
                #     pygame.draw.circle(
                #         self.screen, color, (x + self.offset, y + self.offset), self.offset//4)

                if state == Piece.TIGER:
                    x, y = self.grid_pos(col, row)
                    self.screen.blit(self.bagh_img, (x, y))
                elif state == Piece.GOAT:
                    x, y = self.grid_pos(col, row)
                    self.screen.blit(self.goat_img, (x, y))


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
            if state == Piece.EMPTY:
                if self.turn == Piece.GOAT and self.goat_count > 0:
                    self.state[cell_pos] = Piece.GOAT
                    self.change_turn()
                    self.goat_count -= 1
            elif state == self.turn:  # select only those cells whose turn it is
                if self.goat_count > 0 and self.turn == Piece.GOAT:
                    self.selected_cell = None
                elif self.turn == Piece.TIGER or self.goat_count == 0:
                    self.selected_cell = cell_pos
        else:
            # if another cell is selected for moving the piece to
            if state == Piece.EMPTY:
                # move to adjacent empty
                if cell_pos in self.graph[self.selected_cell]:
                    self.state[self.selected_cell] = Piece.EMPTY
                    self.state[cell_pos] = self.turn
                    self.change_turn()

                # avg the position of two cells gives us the middle cell (in all directions)
                if (self.state[self.selected_cell] == Piece.TIGER):

                    bali_goat = math.ceil((self.selected_cell + cell_pos)/2)

                    # goat ho ra khana milxa
                    if (self.state[bali_goat] == Piece.GOAT and bali_goat in self.graph[self.selected_cell]) and bali_goat in self.graph[cell_pos]:
                        self.state[bali_goat] = Piece.EMPTY
                        self.state[self.selected_cell] = Piece.EMPTY
                        self.state[cell_pos] = self.turn
                        self.eaten_goat_count += 1
                        self.change_turn()

            self.selected_cell = None

    def draw_status(self):
        font = pygame.font.SysFont(None, 24)
        goat_text = font.render(
            f"Goats Left: {self.goat_count}", True, "black")
        eaten_text = font.render(
            f"Goats Eaten: {self.eaten_goat_count}", True, "black")
        trapped_text = font.render(
            f"Tigers Trapped: {self.trapped_tiger_count}", True, "black")

        self.screen.blit(goat_text, (0, self.grid_height-50))
        self.screen.blit(eaten_text, (self.grid_dim*2, self.grid_height-50))
        self.screen.blit(trapped_text, (self.grid_dim*4, self.grid_height-50))

    def game(self):
        self.draw_grid_lines()  # for testing only
        self.draw_board()
        self.draw_pieces()
        self.draw_status()
        self.handle_events()

    def reset_screen(self):
        self.screen.fill("antiquewhite")

    def update(self):
        self.keys = pygame.key.get_pressed()
        self.reset_screen()
        self.game()
        for surf in self.surfs:
            self.screen.blit(surf, (0, 0))
        pygame.display.update()
        self.clock.tick(self.tick_speed)

    def run(self):
        while self.running:
            self.show_main_menu()
            self.play_game()
            # self.update()
        pygame.quit()

    def play_game(self):
        while self.running:
            self.update()

    def show_main_menu(self):
        while True:
            self.screen.fill("lightblue")
            self.draw_text("Baghchal", 64, self.screen_size[0] // 2, 100)
            play_btn = self.draw_button("Play", 277, 350, 200, 60)
            exit_btn = self.draw_button("Exit", 277, 450, 200, 60)

            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if play_btn.collidepoint(event.pos):
                        mode = self.play_mode()
                    if exit_btn.collidepoint(event.pos):
                        self.running = False
                        return None
    
    def play_mode(self):
        while True:
            self.screen.fill("purple")
            self.draw_text("Select mode", 64, self.screen_size[0]//2, 100)
            pvp = self.draw_button("Player vs Player", 127, 350, 550, 60)
            pvc = self.draw_button("Player vs Computer", 107, 450, 600, 60)
            cvc = self.draw_button("Computer vs Computer", 87, 550, 650, 60)

            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # self.running = False
                    return None
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button ==1:
                    if pvp.collidepoint(event.pos):
                        mode = self.play_game() #start game player vs player
                    elif pvc.collidepoint(event.pos):
                        mode = self.play_pvc() #add pvc
                    elif cvc.collidepoint(event.pos):
                        mode = self.play_cvc() #add cvc

    def play_pvc():
        return
    def play_cvc():
        return

    def draw_text(self, text, size, x, y):
        font = pygame.font.Font("assets/font.ttf", size)
        text_surface = font.render(text, True, "black")
        text_rect = text_surface.get_rect(center=(x, y))
        self.screen.blit(text_surface, text_rect)

    def draw_button(self, text, x, y, w, h):
        rect = pygame.Rect(x, y, w, h)
        mouse_pos = pygame.mouse.get_pos()
        if rect.collidepoint(mouse_pos):
            pygame.draw.rect(self.screen, "gray", rect, 2)

        self.draw_text(text, 32, x + w // 2, y + h // 2)
        return pygame.Rect(x, y, w, h)

if __name__ == "__main__":
    game = Game()
    game.run()
