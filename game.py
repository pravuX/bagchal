import pygame
import math
from bagchal import Piece
from alphabeta import MinimaxAgent

class Game:
    def play(self):  # play screen
        pygame.display.set_caption("Play")

    def __init__(self, game_state,
                 screen_size=(854, 480),
                 caption="bagchal",
                 grid_dim=150,
                 tick_speed=30):  # fps
        pygame.init()
        pygame.display.set_caption(caption)

        self.game_state = game_state
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

        # Pygame State
        self.screen = pygame.display.set_mode(self.screen_size)
        self.clock = pygame.time.Clock()
        self.tick_speed = tick_speed

        # loading the images
        self.bagh_img = pygame.image.load("assets/bagh.png").convert_alpha()
        self.goat_img = pygame.image.load("assets/goat.png").convert_alpha()

        # loading images for select
        self.bagh_selected = pygame.image.load(
            "assets/bagh_selected.png").convert_alpha()
        self.goat_selected = pygame.image.load(
            "assets/goat_selected.png").convert_alpha()

        # resizing to make smol
        self.bagh_img = pygame.transform.smoothscale(
            self.bagh_img, (self.grid_dim//2, self.grid_dim//2))
        self.goat_img = pygame.transform.smoothscale(
            self.goat_img, (self.grid_dim//2, self.grid_dim//2))

        self.bagh_selected = pygame.transform.smoothscale(
            self.bagh_selected, (int(self.grid_dim * 0.5), int(self.grid_dim * 0.5)))
        self.goat_selected = pygame.transform.smoothscale(
            self.goat_selected, (int(self.grid_dim * 0.5), int(self.grid_dim * 0.5)))

        self.running = True
        self.surfs = []  # for loading images and stuff
        self.keys = []

        self.colors = {
            Piece.GOAT: "gray",
            Piece.TIGER: "black"
        }
        #remove it later
        self.initialize_board()

    def initialize_board(self):
        #This should be called before instantiating the game object
        self.pos_tiger = [0, 4, 20, 24]

        self.game_state.board[self.pos_tiger[0]] = Piece.TIGER
        self.game_state.board[self.pos_tiger[1]] = Piece.TIGER
        self.game_state.board[self.pos_tiger[2]] = Piece.TIGER
        self.game_state.board[self.pos_tiger[3]] = Piece.TIGER

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or self.keys[pygame.K_q]:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.place_piece(event.pos)
                self.game_state.update_tiger_pos()
                self.game_state.update_trapped_tiger()
                self.game_state.check_end_game()

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
                board = self.game_state.board[col+row*self.grid_cols]

                # if board != 0:  # we don't draw empty cells!
                #     color = self.colors[board]  # image here instead of color
                #     x, y = self.grid_pos(col, row)
                #     # draw a point
                #     pygame.draw.circle(
                #         self.screen, color, (x + self.offset, y + self.offset), self.offset//4)

                if board == Piece.TIGER:
                    x, y = self.grid_pos(col, row)
                    self.screen.blit(
                        self.bagh_img, (x+self.offset//2, y+self.offset//2))
                elif board == Piece.GOAT:
                    x, y = self.grid_pos(col, row)
                    self.screen.blit(
                        self.goat_img, (x+self.offset//2, y+self.offset//2))

                # visualize selected_cell
                if self.selected_cell == col + row * self.grid_cols:
                    if board == Piece.TIGER:
                        x, y = self.grid_pos(col, row)
                        self.screen.blit(
                            self.bagh_selected, (x + self.grid_dim/4, y + self.grid_dim/4))
                    elif board == Piece.GOAT:
                        x, y = self.grid_pos(col, row)
                        self.screen.blit(
                            self.goat_selected, (x + self.grid_dim/4, y + self.grid_dim/4))

    def place_piece(self, pos):
        mouse_x, mouse_y = pos
        col = mouse_x // self.grid_dim
        row = mouse_y // self.grid_dim
        cell_pos = col+row*self.grid_cols  # 2d to 1d index

        board = self.game_state.board[cell_pos]

        # If no piece is selected:
        #     Click on an empty cell → place a new piece (1).
        #     Click on an existing piece (1) → mark it as selected.
        # If a piece is selected:
        #     Click on an empty cell → move it there.
        #     Click on any cell (even invalid move) → cancel selection.

        if self.selected_cell is None:
            # change this by turn
            if board == Piece.EMPTY:
                if self.game_state.turn == Piece.GOAT and self.game_state.goat_count > 0:
                    self.game_state.board[cell_pos] = Piece.GOAT
                    self.game_state.change_turn()
                    self.game_state.goat_count -= 1
            elif board == self.game_state.turn:  # select only those cells whose turn it is
                if self.game_state.goat_count > 0 and self.game_state.turn == Piece.GOAT:
                    self.selected_cell = None
                elif self.game_state.turn == Piece.TIGER or self.game_state.goat_count == 0:
                    self.selected_cell = cell_pos
        else:
            # if another cell is selected for moving the piece to
            if board == Piece.EMPTY:
                # move to adjacent empty
                if cell_pos in self.game_state.graph[self.selected_cell]:
                    self.game_state.board[self.selected_cell] = Piece.EMPTY
                    self.game_state.board[cell_pos] = self.game_state.turn
                    self.game_state.change_turn()

                # avg the position of two cells gives us the middle cell (in all directions)
                if (self.game_state.board[self.selected_cell] == Piece.TIGER):

                    bali_goat = math.ceil((self.selected_cell + cell_pos)/2)

                    # goat ho ra khana milxa
                    if (self.game_state.board[bali_goat] == Piece.GOAT and bali_goat in self.game_state.graph[self.selected_cell] and bali_goat in self.game_state.graph[cell_pos]):
                        self.game_state.board[bali_goat] = Piece.EMPTY
                        self.game_state.board[self.selected_cell] = Piece.EMPTY
                        self.game_state.board[cell_pos] = self.game_state.turn
                        self.game_state.eaten_goat_count += 1
                        self.game_state.change_turn()
            self.selected_cell = None

    def draw_status(self):
        font = pygame.font.SysFont(None, 48)
        goat_text = font.render(
            f"Goats Left: {self.game_state.goat_count}", True, "black")
        eaten_text = font.render(
            f"Goats Eaten: {self.game_state.eaten_goat_count}", True, "black")
        trapped_text = font.render(
            f"Tigers Trapped: {self.game_state.trapped_tiger_count}", True, "black")

        self.screen.blit(goat_text, (0, self.grid_height-50))
        self.screen.blit(eaten_text, (self.grid_dim*2, self.grid_height-50))
        self.screen.blit(
            trapped_text, (self.grid_dim*4-80, self.grid_height-50))

    def game(self):
        # self.draw_grid_lines()  # for testing only
        self.handle_events()
        self.draw_board()
        self.draw_pieces()
        self.draw_status()

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
            # self.play_game()
            self.update()
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
            pvc_goat = self.draw_button("Player vs Goat AI", 107, 450, 600, 60)
            pvc_tiger = self.draw_button(
                "Player vs Tiger AI", 107, 550, 600, 60)
            cvc = self.draw_button("Computer vs Computer", 87, 650, 650, 60)

            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # self.running = False
                    return None
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if pvp.collidepoint(event.pos):
                        mode = self.play_game()  # start game player vs player
                    elif pvc_goat.collidepoint(event.pos):
                        mode = self.play_pvc_goat()  # add pvc
                    elif pvc_tiger.collidepoint(event.pos):
                        mode = self.play_pvc_tiger()  # add pvc
                    elif cvc.collidepoint(event.pos):
                        mode = self.play_cvc()  # add cvc

    def play_pvc_goat(self):
        agent = MinimaxAgent(depth=5)  # depth can be adjusted
        while self.running:
            if self.game_state.turn == Piece.GOAT:
                move = agent.get_best_move(self.game_state)
                pygame.time.delay(500)
                if move:
                    self.game_state.make_move(*move)
                    self.game_state.update_tiger_pos()
                    self.game_state.update_trapped_tiger()
                    self.game_state.check_end_game()
            self.update()

    def play_pvc_tiger(self):
        agent = MinimaxAgent(depth=4)
        while self.running:

            if self.game_state.turn == Piece.TIGER:
                move = agent.get_best_move(self.game_state)
                pygame.time.delay(500)
                if move:
                    self.game_state.make_move(*move)
                    self.game_state.update_tiger_pos()
                    self.game_state.update_trapped_tiger()
                    self.game_state.check_end_game()
            self.update()

    def play_cvc(self):
        # you can use a smaller depth to speed up play
        agent = MinimaxAgent(depth=4)

        while self.running:

            # pygame.time.delay(800)
            move = agent.get_best_move(self.game_state)
            if move:
                self.game_state.make_move(*move)
                self.game_state.update_tiger_pos()
                self.game_state.update_trapped_tiger()
                self.game_state.check_end_game()
            self.update()

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

    def make_move(self, src, dst):
        # Goat placement
        if src == dst:
            if self.game_state.turn == Piece.GOAT and self.game_state.goat_count > 0 and self.game_state.board[src] == Piece.EMPTY:
                self.game_state.board[src] = Piece.GOAT
                self.game_state.goat_count -= 1
                self.game_state.change_turn()
            return

        # Moving pieces
        if self.game_state.board[src] != self.game_state.turn or self.game_state.board[dst] != Piece.EMPTY:
            return  # invalid move

        # Normal adjacent move
        if dst in self.game_state.graph[src]:
            self.game_state.board[src] = Piece.EMPTY
            self.game_state.board[dst] = self.game_state.turn
            self.game_state.change_turn()
            return

        # Tiger capture
        if self.game_state.board[src] == Piece.TIGER:
            mid = (src + dst) // 2
            if (self.game_state.board[mid] == Piece.GOAT and
                    mid in self.game_state.graph[src] and dst in self.game_state.graph[mid]):
                self.game_state.board[mid] = Piece.EMPTY
                self.game_state.board[src] = Piece.EMPTY
                self.game_state.board[dst] = Piece.TIGER
                self.game_state.eaten_goat_count += 1
                self.game_state.change_turn()


