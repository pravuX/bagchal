import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
import json
import time
from multiprocessing import Pool, cpu_count
from mcts import MCTS
from negamax import AlphaBetaAgent
from bagchal import *

@dataclass
class GameStats:
    """Statistics for a single game"""
    result: int  # -1: Goat wins, 0: Draw, 1: Tiger wins
    total_moves: int
    placement_moves: int  # Goat placement phase moves
    movement_moves: int   # Movement phase moves
    captures: int         # Number of goats captured
    trapped_tigers: int   # Number of trapped tigers at end
    game_duration: float  # Real time in seconds
    repetition_draw: bool

def enhanced_self_play_wrapper(args):
    """Wrapper for parallel execution"""
    agent_type, state_hash = args
    return enhanced_self_play(agent_type, state_hash)

def enhanced_self_play(agent_type='mcts', state_hash=None):
    """
    Plays one full game and returns detailed statistics

    Args:
        agent_type: 'mcts' or 'minimax'
        state_hash: dict for tracking repetitions
    """
    if state_hash is None:
        state_hash = defaultdict(int)

    game_state = BitboardGameState()
    stats = GameStats(
        result=0,
        total_moves=0,
        placement_moves=0,
        movement_moves=0,
        captures=0,
        trapped_tigers=0,
        game_duration=0.0,
        repetition_draw=False
    )

    # Initialize agents
    if agent_type == 'mcts':
        agent = MCTS()
    else:
        agent = AlphaBetaAgent()

    start_time = time.time()

    # Game loop
    while not game_state.is_game_over:
        state_key = game_state.key
        state_hash[state_key] += 1

        if state_hash[state_key] > 3:
            stats.result = 0
            stats.repetition_draw = True
            break

        # Determine time limit based on game phase
        if game_state.goats_to_place >= 10:  # Early Placement
            time_limit = 0.3
        elif game_state.goats_to_place >= 5:  # Mid Placement
            time_limit = 0.5
        else:  # Late Placement and Movement
            time_limit = 0.7

        # Get move from agent
        try:
            if agent_type == 'mcts':
                move = agent.search(game_state, time_limit=time_limit, game_history=[])
            else:
                move = agent.get_best_move(game_state, time_limit=time_limit, game_history=[])
        except Exception as e:
            print(f"Error during move: {e}")
            stats.result = 0  # Draw on error
            break

        # Track move type
        if game_state.goats_to_place > 0:
            stats.placement_moves += 1
        else:
            stats.movement_moves += 1

        # Track captures (check if a goat was captured)
        goats_before = popcount(game_state.goats_bb)
        game_state.make_move(move)
        goats_after = popcount(game_state.goats_bb)

        if goats_before > goats_after:
            stats.captures += (goats_before - goats_after)

        stats.total_moves += 1

    # Final statistics
    stats.game_duration = time.time() - start_time
    stats.trapped_tigers = game_state.trapped_tiger_count

    if not stats.repetition_draw:
        stats.result = game_state.get_result if game_state.get_result else 0

    return stats

def collect_statistics(num_games=100, agent_type='mcts', num_workers=None):
    """
    Collect statistics from multiple games

    Args:
        num_games: Number of games to play
        agent_type: 'mcts' or 'minimax'
        num_workers: Number of parallel workers (None = auto)

    Returns:
        List of GameStats objects
    """
    if num_workers is None:
        num_workers = cpu_count()

    print(f"Collecting statistics for {num_games} games using {agent_type}...")
    print(f"Using {num_workers} workers")

    # Prepare arguments
    state_hashes = [defaultdict(int) for _ in range(num_games)]
    args = [(agent_type, state_hash) for state_hash in state_hashes]

    # Run games in parallel
    with Pool(num_workers) as pool:
        results = pool.map(enhanced_self_play_wrapper, args)

    return results

def visualize_game_results(stats_list, save_path='results_analysis1.png'):
    """Create comprehensive visualization of game statistics"""

    # Extract data
    results = [s.result for s in stats_list]
    total_moves = [s.total_moves for s in stats_list]
    placement_moves = [s.placement_moves for s in stats_list]
    movement_moves = [s.movement_moves for s in stats_list]
    captures = [s.captures for s in stats_list]
    game_durations = [s.game_duration for s in stats_list]

    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # Colors
    colors = {
        'tiger': '#FF6B6B',
        'goat': '#4ECDC4',
        'draw': '#95A5A6',
        'placement': '#3498DB',
        'movement': '#E74C3C'
    }

    # 1. Win Distribution (Pie Chart)
    ax1 = fig.add_subplot(gs[0, 0])
    result_counts = Counter(results)
    labels = []
    sizes = []
    pie_colors = []

    if 1 in result_counts:
        labels.append('Tiger Wins')
        sizes.append(result_counts[1])
        pie_colors.append(colors['tiger'])
    if -1 in result_counts:
        labels.append('Goat Wins')
        sizes.append(result_counts[-1])
        pie_colors.append(colors['goat'])
    if 0 in result_counts:
        labels.append('Draws')
        sizes.append(result_counts[0])
        pie_colors.append(colors['draw'])

    ax1.pie(sizes, labels=labels, autopct='%1.1f%%', colors=pie_colors, startangle=90)
    ax1.set_title('Win Distribution', fontsize=14, fontweight='bold')

    # 2. Game Length Distribution (Histogram)
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.hist(total_moves, bins=20, color=colors['tiger'], edgecolor='black', alpha=0.7)
    ax2.axvline(np.mean(total_moves), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(total_moves):.1f}')
    ax2.set_xlabel('Total Moves')
    ax2.set_ylabel('Frequency')
    ax2.set_title('Game Length Distribution', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. Captures per Game (Histogram)
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.hist(captures, bins=range(0, max(captures) + 2), color=colors['goat'], edgecolor='black', alpha=0.7)
    ax3.axvline(np.mean(captures), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(captures):.2f}')
    ax3.set_xlabel('Number of Captures')
    ax3.set_ylabel('Frequency')
    ax3.set_title('Captures per Game', fontsize=14, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. Placement vs Movement Moves (Stacked Bar)
    ax4 = fig.add_subplot(gs[1, 0])
    games = list(range(len(stats_list)))
    ax4.bar(games, placement_moves, label='Placement Moves', color=colors['placement'], alpha=0.7)
    ax4.bar(games, movement_moves, bottom=placement_moves, label='Movement Moves', color=colors['movement'], alpha=0.7)
    ax4.set_xlabel('Game Number')
    ax4.set_ylabel('Number of Moves')
    ax4.set_title('Placement vs Movement Moves', fontsize=14, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 5. Game Duration Distribution
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.hist(game_durations, bins=20, color=colors['draw'], edgecolor='black', alpha=0.7)
    ax5.axvline(np.mean(game_durations), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(game_durations):.2f}s')
    ax5.set_xlabel('Duration (seconds)')
    ax5.set_ylabel('Frequency')
    ax5.set_title('Game Duration Distribution', fontsize=14, fontweight='bold')
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # 6. Moves by Phase (Box Plot)
    ax6 = fig.add_subplot(gs[1, 2])
    phase_data = [placement_moves, movement_moves]
    bp = ax6.boxplot(phase_data, labels=['Placement', 'Movement'], patch_artist=True)
    bp['boxes'][0].set_facecolor(colors['placement'])
    bp['boxes'][1].set_facecolor(colors['movement'])
    ax6.set_ylabel('Number of Moves')
    ax6.set_title('Moves by Phase Distribution', fontsize=14, fontweight='bold')
    ax6.grid(True, alpha=0.3, axis='y')

    # 7. Win Rate by Game Length
    ax7 = fig.add_subplot(gs[2, 0])
    # Bin games by length and calculate win rates
    bins = np.linspace(min(total_moves), max(total_moves), 6)
    bin_indices = np.digitize(total_moves, bins)

    tiger_wins_by_length = []
    goat_wins_by_length = []
    draw_rate_by_length = []
    bin_centers = []

    for i in range(1, len(bins)):
        mask = bin_indices == i
        if np.any(mask):
            bin_results = [results[j] for j in range(len(results)) if mask[j]]
            total = len(bin_results)
            tiger_wins_by_length.append(sum(1 for r in bin_results if r == 1) / total * 100)
            goat_wins_by_length.append(sum(1 for r in bin_results if r == -1) / total * 100)
            draw_rate_by_length.append(sum(1 for r in bin_results if r == 0) / total * 100)
            bin_centers.append((bins[i-1] + bins[i]) / 2)

    x = np.arange(len(bin_centers))
    width = 0.25
    ax7.bar(x - width, tiger_wins_by_length, width, label='Tiger Wins', color=colors['tiger'], alpha=0.7)
    ax7.bar(x, goat_wins_by_length, width, label='Goat Wins', color=colors['goat'], alpha=0.7)
    ax7.bar(x + width, draw_rate_by_length, width, label='Draws', color=colors['draw'], alpha=0.7)
    ax7.set_xlabel('Game Length (moves)')
    ax7.set_ylabel('Win Rate (%)')
    ax7.set_title('Win Rate by Game Length', fontsize=14, fontweight='bold')
    ax7.set_xticks(x)
    ax7.set_xticklabels([f'{int(c)}' for c in bin_centers])
    ax7.legend()
    ax7.grid(True, alpha=0.3, axis='y')

    # 8. Captures vs Game Length (Scatter)
    ax8 = fig.add_subplot(gs[2, 1])
    scatter = ax8.scatter(total_moves, captures, c=results, cmap='RdYlGn', alpha=0.6, s=50)
    ax8.set_xlabel('Total Moves')
    ax8.set_ylabel('Number of Captures')
    ax8.set_title('Captures vs Game Length', fontsize=14, fontweight='bold')
    ax8.grid(True, alpha=0.3)

    # 9. Summary Statistics Table
    ax9 = fig.add_subplot(gs[2, 2])
    ax9.axis('off')

    summary_text = generate_summary_text(stats_list)
    ax9.text(0.1, 0.5, summary_text, fontsize=11, family='monospace',
             verticalalignment='center', transform=ax9.transAxes)

    plt.suptitle('Bagchal Game Statistics Analysis', fontsize=18, fontweight='bold', y=0.98)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Visualization saved to {save_path}")
    plt.close()

def generate_summary_text(stats_list):
    """Generate text summary of statistics"""
    results = [s.result for s in stats_list]
    total_moves = [s.total_moves for s in stats_list]
    captures = [s.captures for s in stats_list]
    durations = [s.game_duration for s in stats_list]

    result_counts = Counter(results)
    total_games = len(stats_list)

    summary = f"""Summary Statistics
{'='*30}

Total Games: {total_games}

Win Distribution:
  Tiger Wins: {result_counts.get(1, 0)} ({result_counts.get(1, 0)/total_games*100:.1f}%)
  Goat Wins:  {result_counts.get(-1, 0)} ({result_counts.get(-1, 0)/total_games*100:.1f}%)
  Draws:      {result_counts.get(0, 0)} ({result_counts.get(0, 0)/total_games*100:.1f}%)

Game Length:
  Mean: {np.mean(total_moves):.1f} moves
  Median: {np.median(total_moves):.1f} moves
  Min: {np.min(total_moves)} moves
  Max: {np.max(total_moves)} moves

Captures:
  Mean: {np.mean(captures):.2f} per game
  Max: {np.max(captures)} captures

Duration:
  Mean: {np.mean(durations):.2f} seconds
  Total: {np.sum(durations):.1f} seconds
"""
    return summary

def compare_agents(num_games=50):
    """Compare MCTS vs Minimax agents"""
    print("Comparing MCTS vs Minimax agents...")

    # Collect stats for both agents
    mcts_stats = collect_statistics(num_games, agent_type='mcts')
    minimax_stats = collect_statistics(num_games, agent_type='minimax')

    # Create comparison visualization
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))

    # Compare win rates
    ax1 = axes[0, 0]
    mcts_results = [s.result for s in mcts_stats]
    mm_results = [s.result for s in minimax_stats]

    mcts_counts = Counter(mcts_results)
    mm_counts = Counter(mm_results)

    categories = ['Tiger Wins', 'Goat Wins', 'Draws']
    mcts_values = [mcts_counts.get(1, 0), mcts_counts.get(-1, 0), mcts_counts.get(0, 0)]
    mm_values = [mm_counts.get(1, 0), mm_counts.get(-1, 0), mm_counts.get(0, 0)]

    x = np.arange(len(categories))
    width = 0.35
    ax1.bar(x - width/2, mcts_values, width, label='MCTS', color='#3498DB', alpha=0.7)
    ax1.bar(x + width/2, mm_values, width, label='Minimax', color='#E74C3C', alpha=0.7)
    ax1.set_ylabel('Number of Games')
    ax1.set_title('Win Distribution Comparison')
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories)
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')

    # Compare game lengths
    ax2 = axes[0, 1]
    mcts_moves = [s.total_moves for s in mcts_stats]
    mm_moves = [s.total_moves for s in minimax_stats]
    ax2.boxplot([mcts_moves, mm_moves], labels=['MCTS', 'Minimax'])
    ax2.set_ylabel('Game Length (moves)')
    ax2.set_title('Game Length Comparison')
    ax2.grid(True, alpha=0.3, axis='y')

    # Compare captures
    ax3 = axes[0, 2]
    mcts_captures = [s.captures for s in mcts_stats]
    mm_captures = [s.captures for s in minimax_stats]
    ax3.boxplot([mcts_captures, mm_captures], labels=['MCTS', 'Minimax'])
    ax3.set_ylabel('Number of Captures')
    ax3.set_title('Captures Comparison')
    ax3.grid(True, alpha=0.3, axis='y')

    # Compare game duration
    ax4 = axes[1, 0]
    mcts_duration = [s.game_duration for s in mcts_stats]
    mm_duration = [s.game_duration for s in minimax_stats]
    ax4.boxplot([mcts_duration, mm_duration], labels=['MCTS', 'Minimax'])
    ax4.set_ylabel('Game Duration (seconds)')
    ax4.set_title('Game Duration Comparison')
    ax4.grid(True, alpha=0.3, axis='y')

    # Compare placement vs movement
    ax5 = axes[1, 1]
    mcts_placement = [s.placement_moves for s in mcts_stats]
    mm_placement = [s.placement_moves for s in minimax_stats]
    data = [mcts_placement, mm_placement]
    bp = ax5.boxplot(data, labels=['MCTS\nPlacement', 'Minimax\nPlacement'], patch_artist=True)
    bp['boxes'][0].set_facecolor('#3498DB')
    bp['boxes'][1].set_facecolor('#E74C3C')
    ax5.set_ylabel('Number of Moves')
    ax5.set_title('Placement Phase Comparison')
    ax5.grid(True, alpha=0.3, axis='y')

    # Summary statistics
    ax6 = axes[1, 2]
    ax6.axis('off')

    summary = f"""Agent Comparison Summary
{'='*40}

MCTS Agent:
  Games: {len(mcts_stats)}
  Tiger Win Rate: {mcts_counts.get(1, 0)/len(mcts_stats)*100:.1f}%
  Goat Win Rate: {mcts_counts.get(-1, 0)/len(mcts_stats)*100:.1f}%
  Avg Game Length: {np.mean(mcts_moves):.1f} moves
  Avg Captures: {np.mean(mcts_captures):.2f}
  Avg Duration: {np.mean(mcts_duration):.2f}s

Minimax Agent:
  Games: {len(minimax_stats)}
  Tiger Win Rate: {mm_counts.get(1, 0)/len(minimax_stats)*100:.1f}%
  Goat Win Rate: {mm_counts.get(-1, 0)/len(minimax_stats)*100:.1f}%
  Avg Game Length: {np.mean(mm_moves):.1f} moves
  Avg Captures: {np.mean(mm_captures):.2f}
  Avg Duration: {np.mean(mm_duration):.2f}s
"""
    ax6.text(0.1, 0.5, summary, fontsize=10, family='monospace',
             verticalalignment='center', transform=ax6.transAxes)

    plt.suptitle('MCTS vs Minimax Agent Comparison', fontsize=16, fontweight='bold')
    plt.savefig('agent_comparison.png', dpi=300, bbox_inches='tight')
    print("Comparison visualization saved to agent_comparison.png")
    plt.close()

    return mcts_stats, minimax_stats

def save_statistics_json(stats_list, filename='game_statistics.json'):
    """Save statistics to JSON file"""
    data = {
        'games': [asdict(stat) for stat in stats_list],
        'summary': {
            'total_games': len(stats_list),
            'tiger_wins': sum(1 for s in stats_list if s.result == 1),
            'goat_wins': sum(1 for s in stats_list if s.result == -1),
            'draws': sum(1 for s in stats_list if s.result == 0),
            'avg_moves': np.mean([s.total_moves for s in stats_list]),
            'avg_captures': np.mean([s.captures for s in stats_list]),
            'avg_duration': np.mean([s.game_duration for s in stats_list])
        }
    }

    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Statistics saved to {filename}")

if __name__ == "__main__":
    # Example usage
    print("Collecting statistics...")
    stats = collect_statistics(num_games=100, agent_type='negamax')

    print("\nGenerating visualizations...")
    visualize_game_results(stats, 'results_analysis.png')

    print("\nSaving statistics to JSON...")
    save_statistics_json(stats)

    # print("\nAnalysis complete!")
    # mcts_stats, minimax_stats = compare_agents(num_games=50)
