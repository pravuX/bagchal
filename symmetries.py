import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from utils import display_board
from bagchal import BitboardGameState
import os


def bagchal_graph():
    """
    Constructs a NetworkX graph representing the Bagh Chal board topology.
    
    Nodes are 0-24. Edges represent valid moves (orthogonal and diagonal).
    """
    G = nx.Graph()
    G.add_nodes_from(range(25))

    # orthogonal edges
    for r in range(5):
        for c in range(5):
            i = r * 5 + c
            if c < 4:
                G.add_edge(i, i + 1)
            if r < 4:
                G.add_edge(i, i + 5)

    diagonals = [
        # main diagonal
        (0, 6), (6, 12), (12, 18), (18, 24),
        # anti-diagonal
        (4, 8), (8, 12), (12, 16), (16, 20),
        # diamond (quadrant diagonals)
        (2, 6), (6, 10), (10, 16), (16, 22),
        (22, 18), (18, 14), (14, 8), (8, 2)
    ]
    G.add_edges_from(diagonals)

    return G


def generate_d4_transforms():
    """
    Generates the 8 dihedral transforms
    D4 = {r^0, r^0s, r^1, r^1s, r^2, r^2s, r^3, r^3s}
    where r = rotate by 90 degree, s = relflect vertically
    """
    grid = np.arange(25).reshape(5, 5)
    out = []
    out = []
    for k in range(4):
        rotation = np.rot90(grid, k).reshape(-1)
        reflection = np.fliplr(np.rot90(grid, k)).reshape(-1)
        out.extend([rotation, reflection])

    return out


def find_automorphisms(G):
    GM = nx.algorithms.isomorphism.GraphMatcher(G, G)
    autos = list(GM.isomorphisms_iter())
    print(f"NetworkX Graph Matcher found {len(autos)} automorphisms.")
    return autos


def dihedral_match_count(autos, transforms):
    count = 0
    for perm in autos:
        perm_list = np.array([perm[i] for i in range(25)])
        for t in transforms:
            if np.array_equal(perm_list, t):
                count += 1
                break
    print(f"No of matches between automorphisms and transforms: {count}")


def draw_bagchal_graph(G):
    # Node positions in Bagchal geometry
    pos = {}
    for r in range(5):
        for c in range(5):
            pos[r * 5 + c] = (c, -r)   # invert y for nicer orientation

    plt.figure(figsize=(6, 6))
    nx.draw(
        G,
        pos=pos,
        with_labels=True,
        node_size=500,
        node_color="black",
        font_color="white",
        width=2
    )
    plt.title("Bagchal Board")
    plt.axis("equal")
    plt.show()


def draw_graph(G, perm, title, fig, ax):
    # Draw one frame of the graph with node relabeling
    pos = {}
    for r in range(5):
        for c in range(5):
            pos[r * 5 + c] = (c, -r)   # invert y for nicer orientation
    nx.draw(
        G,
        pos={perm[i]: pos[i] for i in range(25)},
        with_labels=True,
        node_size=500,
        node_color="skyblue",
        font_color="black",
        width=2,
        ax=ax
    )
    ax.set_title(title)
    ax.axis("equal")

    # output_dir = "symmetries"
    # file_name = f"{title.replace(' ', '-')}.png"
    #
    # if not os.path.exists(output_dir):
    #     os.makedirs(output_dir)
    #
    # full_path = os.path.join(output_dir, file_name)
    #
    # fig.savefig(full_path)


def animate_symmetries(graph, frames, interval):
    fig, ax = plt.subplots(figsize=(6, 6))

    names = [
        "Identity (r^0)",
        "Reflect Left–Right (r^0s)",
        "Rotate 90° (r^1)",
        "Reflect Anti-Diagonal (r^1s)",
        "Rotate 180° (r^2)",
        "Reflect Top–Bottom (r^2s)",
        "Rotate 270° (r^3)",
        "Reflect Main Diagonal (r^3s)",
    ]

    def update(idx):
        ax.clear()
        perm = frames[idx]
        draw_graph(graph, perm, names[idx], fig, ax)

    _ = FuncAnimation(fig, update, frames=len(
        frames), interval=interval*1000, repeat=True)
    plt.show()


def apply_perm_to_bb(bb: int, perm: np.array):
    """
    Applies a permutation to a bitboard.
    
    Args:
        bb: original bitboard.
        perm: permutation array mapping old indices to new indices.
        
    Returns:
        New transformed bitboard.
    """
    new_bb = 0

    for i in range(len(perm)):
        if (bb >> i) & 1:
            new_bb |= (1 << perm[i])
    return new_bb


def apply_perm_to_move(move, perm):
    src, dst = move
    return (perm[src], perm[dst])


def canonicalize_state(tigers_bb, goats_bb, turn, goats_left, transforms):
    """
    Finds the canonical (lexicographically smallest) representation of a state 
    among all its symmetric variations.
    
    Returns:
        best_key: Tuple representing the canonical state.
        best_sym: Index of the transform that produces the canonical state.
    """
    best_key = None
    best_sym = -1

    for i in range(8):
        perm = transforms[i]
        t2 = apply_perm_to_bb(tigers_bb, perm)
        g2 = apply_perm_to_bb(goats_bb, perm)
        # TODO: eaten goats must also be here
        key = (turn, goats_left, t2, g2)

        if best_key is None or key < best_key:
            best_key = key
            best_sym = i

    return best_key, best_sym


def get_canonical_bitboards(gs, transforms):
    best_key, _ = canonicalize_state(
        gs.tigers_bb, gs.goats_bb, gs.turn, gs.goats_to_place, transforms)
    return {"tigers_bb": best_key[2], "goats_bb": best_key[3]}


def stabilizer_indices(tigers_bb, goats_bb, transforms):
    stabs = []
    for i in range(len(transforms)):
        perm = transforms[i]
        if (apply_perm_to_bb(tigers_bb, perm) == tigers_bb and apply_perm_to_bb(goats_bb, perm) == goats_bb):
            stabs.append(i)
    return stabs


def symmetry_prune_moves(tigers_bb, goats_bb, legal_moves, transforms):
    """
    Prunes symmetric moves to reduce search space.
    
    If the board has symmetries (stabilizers), we only need to search one move 
    from each set of symmetric moves.
    """
    stabs = stabilizer_indices(tigers_bb, goats_bb, transforms)

    reps = []
    pruned = []

    for move in legal_moves:
        src, dst = move

        # compute canonical representative of the orbit
        best = None
        for s in stabs:
            perm = transforms[s]
            m2 = (perm[src], perm[dst])
            if best is None or m2 < best:
                best = m2

        # check if we’ve already seen this representative
        seen = False
        for r in reps:
            if r[0] == best[0] and r[1] == best[1]:
                seen = True
                break

        if not seen:
            reps.append(best)
            pruned.append(move)

    return pruned


def find_canonical_triple_lock_bb(transforms):

    # initial config
    gs = BitboardGameState()

    # one tiger triple lock formation
    gs.tigers_bb = 0
    gs.tigers_bb |= (1 << 8) | (1 << 20) | (1 << 23)

    canonical_bitboards = get_canonical_bitboards(gs, transforms)
    gs.tigers_bb, gs.goats_bb = canonical_bitboards["tigers_bb"], canonical_bitboards["goats_bb"]

    # the canonical triple lock formation
    return gs.tigers_bb


# TODO: move this into bagchal.py
def generate_formation_masks(base_tigers_bb):
    """
    Takes a specific tiger setup (bitboard) and returns a numpy array
    containing all unique symmetric variations (masks) of that setup.
    """
    transforms = generate_d4_transforms()
    masks = set()

    for perm in transforms:
        # Apply the symmetry transform to the base formation
        mask = apply_perm_to_bb(base_tigers_bb, perm)
        masks.add(mask)

    return np.array(list(masks), dtype=np.int64)


# --- CONFIGURATION ---
# The formation: Tigers at 8, 20, 23
TRIPLE_LOCK_BASE = (1 << 8) | (1 << 20) | (1 << 23)

# Generate the 8 (or fewer) variations
TRIPLE_LOCK_MASKS_NP = generate_formation_masks(TRIPLE_LOCK_BASE)

# TODO: Also move this somewhere more appropriate
# @njit(cache=True)


def score_triple_lock(tigers_bb, masks):
    """
    Returns a score based on how close the tigers are to matching the pattern.
    - 3 matches (Full Formation): Huge Bonus
    - 2 matches (Partial): Small Bonus
    """
    max_matches = 0

    for i in range(len(masks)):
        mask = masks[i]

        intersection = tigers_bb & mask

        matches = intersection.bit_count()

        if matches > max_matches:
            max_matches = matches

            # If we found a perfect match, we can stop early
            if max_matches == 3:
                return 3

    return max_matches


def main():
    G = bagchal_graph()
    TRANSFORMS = generate_d4_transforms()

    # draw_bagchal_graph(G)

    # autos = find_automorphisms(G)
    # dihedral_match_count(autos, TRANSFORMS)
    #
    # animate_symmetries(graph=G, frames=TRANSFORMS, interval=3)

    gs = BitboardGameState()
    gs.make_move((2, 2))

    legal_moves = gs.get_legal_moves()

    pruned_moves = symmetry_prune_moves(
        gs.tigers_bb,
        gs.goats_bb,
        legal_moves,
        TRANSFORMS
    )
    display_board(gs)
    print(gs)
    print("All legal moves:", legal_moves)
    print("Pruned moves:", pruned_moves)
    print("Original =", len(legal_moves), "Pruned =", len(pruned_moves))

    # Find the canonical state for tiger making a triangular formation
    # gs.tigers_bb = 0
    # gs.tigers_bb |= (1 << 8) | (1 << 20) | (1 << 23)
    #
    # display_board(gs)
    # print(gs)
    # canonical_bitboards = get_canonical_bitboards(gs, TRANSFORMS)
    # gs.tigers_bb, gs.goats_bb = canonical_bitboards["tigers_bb"], canonical_bitboards["goats_bb"]
    # print(gs.tigers_bb)
    # display_board(gs)
    # # TODO: Now how do we reward this sort of formation positively in evaluation function?
    # # I'm going to first try a simple masks based solution
    # print(gs)


if __name__ == "__main__":
    main()
