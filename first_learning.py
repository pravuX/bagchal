from learning_system import ParameterOptimizer
import json
from dataclasses import asdict
from bagchal import HeuristicParams

print("🚀 Starting your first learning session!")
print("The AI will play games against itself to learn better strategies...")

# Small learning session for testing
optimizer = ParameterOptimizer(num_evaluation_games=5)
best_params = optimizer.optimize(n_trials=2)

# Save results
with open('my_first_learned_params.json', 'w') as f:
    json.dump(asdict(best_params), f, indent=2)

print("🎉 Learning complete!")
print("Check 'my_first_learned_params.json' to see what the AI learned!")

# Show what changed
original = HeuristicParams()
print("\n📊 What the AI learned:")
for param_name in asdict(original).keys():
    old_val = getattr(original, param_name)
    new_val = getattr(best_params, param_name)
    change = ((new_val - old_val) / old_val) * 100
    print(f"{param_name}: {old_val:.2f} → {new_val:.2f} ({change:+.1f}%)")
