from bagchal import BitboardGameState, extract_indices_fast, Piece_TIGER, Piece_GOAT


def display_board(game_state: BitboardGameState):
    board = [0] * 25
    for tiger in extract_indices_fast(game_state.tigers_bb):
        board[tiger] = Piece_TIGER
    for goat in extract_indices_fast(game_state.goats_bb):
        board[goat] = Piece_GOAT
    piece = game_state.piece
    print("-"*26)
    for i, cell in enumerate(board):
        if i % 5 == 0:
            print("|", end=" ")
        print(piece[cell], end=" | ")
        if (i+1) % 5 == 0:
            print()
            print("-"*26)
