#!/usr/bin/env python3
"""Generate performance analysis charts for Tractatus-Eval README."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# ─── Data ───────────────────────────────────────────────────────────
models = ['Pythia-410m', 'Llama-3.2-1B', 'Llama-3.2-3B', 'Phi-2', 'Mistral-7B', 'Llama-3-8B']
params = [0.41, 1.0, 3.0, 2.7, 7.0, 8.0]
tasks = ['Spatial', 'Key-Lock', 'Stacking', 'Container', 'Collision', 'Circuit']
diffs = ['Easy', 'Medium', 'Hard']

# acc[model][task][difficulty]
acc = {
    'Pythia-410m': {
        'Spatial': [13.6, 11.0, 15.8], 'Key-Lock': [9.8, 12.4, 13.6],
        'Stacking': [27.0, 23.6, 23.8], 'Container': [37.2, 46.4, 47.6],
        'Collision': [50.0, 50.0, 50.0], 'Circuit': [49.8, 49.8, 49.8]
    },
    'Llama-3.2-1B': {
        'Spatial': [27.6, 22.8, 28.2], 'Key-Lock': [14.6, 18.0, 18.6],
        'Stacking': [26.8, 28.2, 26.6], 'Container': [48.4, 57.4, 61.8],
        'Collision': [50.0, 50.0, 50.0], 'Circuit': [49.8, 49.8, 49.8]
    },
    'Llama-3.2-3B': {
        'Spatial': [29.6, 32.2, 33.8], 'Key-Lock': [23.4, 26.2, 27.4],
        'Stacking': [26.0, 25.8, 23.6], 'Container': [56.8, 67.6, 70.2],
        'Collision': [50.0, 50.0, 50.0], 'Circuit': [49.8, 49.8, 49.8]
    },
    'Phi-2': {
        'Spatial': [32.4, 31.2, 34.0], 'Key-Lock': [30.4, 34.6, 34.8],
        'Stacking': [30.4, 41.0, 47.8], 'Container': [67.4, 59.0, 75.4],
        'Collision': [50.0, 50.0, 50.0], 'Circuit': [49.8, 49.8, 49.8]
    },
    'Mistral-7B': {
        'Spatial': [31.0, 35.2, 34.2], 'Key-Lock': [25.6, 31.4, 33.4],
        'Stacking': [25.4, 27.4, 26.4], 'Container': [54.4, 68.0, 74.6],
        'Collision': [50.0, 50.0, 50.0], 'Circuit': [49.8, 49.8, 49.8]
    },
    'Llama-3-8B': {
        'Spatial': [30.2, 31.2, 34.4], 'Key-Lock': [30.2, 30.8, 31.0],
        'Stacking': [26.0, 30.6, 30.6], 'Container': [55.0, 66.6, 71.6],
        'Collision': [50.0, 50.0, 50.0], 'Circuit': [49.8, 49.8, 49.8]
    }
}

colors = {
    'Pythia-410m': '#6C7B95',
    'Llama-3.2-1B': '#42A5F5',
    'Llama-3.2-3B': '#1565C0',
    'Phi-2': '#FF6F00',
    'Mistral-7B': '#AB47BC',
    'Llama-3-8B': '#26A69A'
}

OUT = '/Users/tianjiesun/Desktop/FDE_Portfolio_2026/tractatus_eval/assets'
import os; os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'figure.dpi': 150,
})

# ─── Chart 1: Model × Task Heatmap-style grouped bar ────────────
fig, ax = plt.subplots(figsize=(14, 5.5))
non_binary = ['Spatial', 'Key-Lock', 'Stacking', 'Container']
x = np.arange(len(non_binary))
width = 0.12

for i, m in enumerate(models):
    avgs = [np.mean(acc[m][t]) for t in non_binary]
    bars = ax.bar(x + i * width - 2.5 * width, avgs, width,
                  label=f'{m} ({params[i]}B)', color=colors[m], edgecolor='white', linewidth=0.5)
    for bar, val in zip(bars, avgs):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
                f'{val:.1f}', ha='center', va='bottom', fontsize=7, fontweight='bold')

ax.axhline(y=25, color='#E0E0E0', linestyle='--', linewidth=1, label='Random (25%)')
ax.set_xlabel('Task', fontweight='bold', fontsize=12)
ax.set_ylabel('Average Accuracy (%)', fontweight='bold', fontsize=12)
ax.set_title('Model Performance by Task (avg across Easy/Medium/Hard)', fontweight='bold', fontsize=14, pad=15)
ax.set_xticks(x)
ax.set_xticklabels(non_binary, fontsize=11)
ax.set_ylim(0, 85)
ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(f'{OUT}/model_vs_task.png', bbox_inches='tight', facecolor='white')
print(f'Saved model_vs_task.png')

# ─── Chart 2: Difficulty scaling per task (4 subplots) ──────────
fig, axes = plt.subplots(2, 2, figsize=(12, 8))
axes = axes.flatten()

for idx, task in enumerate(non_binary):
    ax = axes[idx]
    for m in models:
        ax.plot(diffs, acc[m][task], 'o-', label=m, color=colors[m], linewidth=2, markersize=6)
    ax.axhline(y=25, color='#E0E0E0', linestyle='--', linewidth=1)
    ax.set_title(task, fontweight='bold', fontsize=13)
    ax.set_ylabel('Accuracy (%)', fontsize=10)
    ax.set_ylim(0, 85)
    ax.grid(axis='y', alpha=0.3)
    if idx == 0:
        ax.legend(fontsize=8, loc='upper left')

fig.suptitle('How Difficulty Affects Performance', fontweight='bold', fontsize=15, y=1.01)
plt.tight_layout()
plt.savefig(f'{OUT}/difficulty_scaling.png', bbox_inches='tight', facecolor='white')
print(f'Saved difficulty_scaling.png')

# ─── Chart 3: Overall model ranking (non-binary tasks) ─────────
fig, ax = plt.subplots(figsize=(8, 4.5))
overall = []
for m in models:
    avg = np.mean([np.mean(acc[m][t]) for t in non_binary])
    overall.append(avg)

sorted_idx = np.argsort(overall)[::-1]
sorted_models = [models[i] for i in sorted_idx]
sorted_avgs = [overall[i] for i in sorted_idx]
sorted_colors = [colors[m] for m in sorted_models]

bars = ax.barh(range(len(sorted_models)), sorted_avgs, color=sorted_colors, edgecolor='white', height=0.6)
ax.set_yticks(range(len(sorted_models)))
ax.set_yticklabels([f'{m} ({params[models.index(m)]}B)' for m in sorted_models], fontsize=11)
ax.set_xlabel('Avg Accuracy on Non-Binary Tasks (%)', fontweight='bold', fontsize=11)
ax.set_title('Overall Model Ranking\n(Spatial + Key-Lock + Stacking + Container)', fontweight='bold', fontsize=13)
ax.axvline(x=25, color='#E0E0E0', linestyle='--', linewidth=1)
ax.set_xlim(0, 55)
ax.invert_yaxis()
for bar, val in zip(bars, sorted_avgs):
    ax.text(val + 0.5, bar.get_y() + bar.get_height()/2,
            f'{val:.1f}%', ha='left', va='center', fontweight='bold', fontsize=11)
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
plt.savefig(f'{OUT}/model_ranking.png', bbox_inches='tight', facecolor='white')
print(f'Saved model_ranking.png')

print('\nAll charts generated!')
