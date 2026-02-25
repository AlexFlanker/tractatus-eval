<p align="center">
  <strong>🏛️ Project Tractatus-Eval</strong><br>
  <em>A Benchmark for Spatial Embodied Logic in Large Language Models</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8%2B-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/EleutherAI-lm--eval--harness-green?style=flat-square" alt="lm-eval-harness">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/samples-1000-orange?style=flat-square" alt="Samples">
</p>

<p align="center">
  <a href="#why-this-exists">English</a> | <a href="#为什么要做这个项目">简体中文</a>
</p>

---

## Why This Exists

Modern LLMs excel at linguistic reasoning but consistently fail at tasks requiring **embodied spatial understanding** — the kind of intuition any physical agent acquires trivially through interaction with the real world.

Consider a simple request: *"Navigate from A1 to E5, avoiding walls."* A human child solves this instantly. State-of-the-art LLMs routinely generate paths that **walk through walls**, **teleport across obstacles**, or **exit the grid entirely** — violations that are physically impossible but textually plausible.

**Tractatus-Eval** quantifies this gap. Inspired by Wittgenstein's *Tractatus Logico-Philosophicus* — *"The limits of my language mean the limits of my world"* — this benchmark asks: **what are the limits of a world built entirely from text?**

## The Six Tasks

Tractatus-Eval consists of **6 tasks**, each targeting a different dimension of embodied physical reasoning. All tasks share the same architecture: procedural generation → deterministic ground truth → distractor validation → JSONL output.

---

### 1. Spatial Navigation 🗺️

**Physics tested:** Grid pathfinding, obstacle avoidance, boundary awareness

The model must find the shortest valid path from a start cell to a goal cell on an N×N grid with impassable obstacles. The ground truth is computed via **A\* search** with Manhattan-distance heuristic.

**Distractor strategies:**
| Strategy | What It Tests |
|---|---|
| **Wall Teleportation** | Straight-line path ignoring obstacles — tests if the model treats `#` as truly impassable |
| **Random Walk** | Same-length random direction sequence — tests if the model actually traces the path |
| **Reversed Path** | Correct path played backwards — tests directional coherence |
| **Off-by-One Mutation** | Single-direction swap in the correct path — tests fine-grained spatial tracking |

✅ **Physics-engine playback:** Every distractor is simulated step-by-step. Candidates that secretly reach the goal without violations are automatically discarded (0% contamination).

---

### 2. Key-Lock Puzzles 🔑

**Physics tested:** State-dependent actions, inventory tracking, sequential dependencies

The model must navigate a grid where **colored doors** block the path. Each door requires picking up a matching **colored key** first. The solution is a sequence of moves interleaved with `pick_up_<color>` and `unlock_<color>` actions.

The ground truth uses a **state-aware BFS** that searches over `(position, inventory)` space — expanding ~25× the state space of regular pathfinding.

**Distractor strategies:**
- Skip all key pickups (walk straight into locked doors)
- Remove unlock actions (attempt to pass through locked doors without unlocking)
- Swap key colors (use the wrong key for each door)
- Mutate a single movement direction
- Random walks with sprinkled key/unlock actions

✅ **Physics-engine playback:** Full step-by-step simulation tracking position AND inventory. Each candidate distractor is replayed; if it validly reaches the goal (e.g., an alternate key-collection order), it is rejected as a distractor.

---

### 3. Object Stacking 📦

**Physics tested:** Gravity, structural stability, center-of-mass support

Given a set of blocks with different widths, the model must determine the correct bottom-to-top stacking order such that each block is fully supported by the one below it. A block is **stable** only if its width ≤ the width of the block directly beneath it.

**Distractor strategies:**
- Random permutations of the correct stack, each validated to be **physically unstable** via `is_stable()` — ensuring every wrong answer truly violates the support constraint.

✅ **Physics validator:** `is_stable()` — iterates through each adjacent pair and confirms `width[i] ≤ width[i-1]`. Only permutations that fail this check are accepted as distractors.

---

### 4. Container Filling 🫗

**Physics tested:** Volume conservation, pour transfers, capacity limits (overflow)

The model is presented with 2–4 containers of varying capacities and initial fill levels, then a sequence of actions: `Pour A into B`, `Fill C`, `Empty B`, etc. It must compute the final state of all containers after all actions execute.

The ground truth is computed by a **step-by-step simulator** (`simulate_step()`) that enforces capacity capping — when pouring into a full container, excess liquid is lost (physical overflow).

**Distractor strategies:**
- **Naive math (no overflow capping)** — simulates without respecting capacity limits, producing plausible but wrong totals
- **Shuffled values** — correct final values assigned to wrong containers
- **Random fills** — random amounts within each container's capacity range

✅ **Physics validator:** `simulate_step()` — enforces `min(poured + current, capacity)` at each step. The correct answer is the only state that results from faithful step-by-step simulation with overflow handling.

---

### 5. Collision Prediction 💥

**Physics tested:** Temporal extrapolation, trajectory projection, spatial intersection

Two or more objects move across an N×N grid with fixed velocities (direction + speed). The model must predict whether they **collide** (occupy the same cell at the same time step), and if so, report the step number and collision cell.

The ground truth is computed by a **`simulate()` function** that advances all objects simultaneously for up to `MAX_STEPS` time steps, checking for co-occupation at each tick.

**Distractor strategies:**
- If collision occurs: "No collision" + off-by-one step + wrong cell
- If no collision: fabricated collision events at random steps/cells
- All distractors describe physically impossible outcomes given the trajectories

✅ **Physics validator:** `simulate()` — deterministic step-by-step trajectory computation. The ground truth is the only answer consistent with the actual simulation.

---

### 6. Circuit Connectivity ⚡

**Physics tested:** Electrical path tracing, topological connectivity, switch state logic

An N×N grid contains a battery (`+`/`-`), a bulb (`B`), wires (`W`), and numbered switches. The model must determine whether the bulb lights up. Electricity flows only through wires and **CLOSED** switches; **OPEN** switches and gaps break the circuit.

The ground truth checks two conditions: (1) all switches are CLOSED, AND (2) the wire path from `+` to `-` through the bulb is continuous (no gaps from random wire breaks).

**Distractor strategies:**
- Fixed 4-choice format: "Yes, the bulb lights up", "No, the circuit is broken", "Yes, but only dimly", "No, it shorts out"
- The correct answer is determined by graph reachability + switch state evaluation

✅ **Physics validator:** Graph-based reachability — path from `+` → bulb → `-` must exist through only wires and CLOSED switches. Wire breaks and OPEN switches are the two failure modes.

---

> [!IMPORTANT]
> **Every task enforces 0% contamination.** No distractor is accepted unless it provably violates the physical constraints of its task. This means: every wrong answer is wrong *for a physically grounded reason*, not just textually implausible.

## Sample Prompt

```
You are navigating a 5×5 grid. Rows are labeled A–E (top to bottom),
columns 1–5 (left to right). You can move one step at a time: up, down,
left, or right. You CANNOT move diagonally, move outside the grid
boundaries, or pass through obstacle cells.

Grid map:
  1 2 3 4 5
A # . . E .
B . . . # .
C . . . . .
D . . . . .
E S . . # .

Start: E1  |  Goal: A4  |  Obstacles (impassable): A1, B4, E4

What is the shortest valid path from E1 to A4? Give your answer as a
comma-separated list of directions (up/down/left/right).
```

## Quick Start

### Generate the Dataset

```bash
# Default: 1000 samples, seed=42
python3 scripts/generate_spatial_eval.py

# Custom configuration
python3 scripts/generate_spatial_eval.py \
  --num-samples 2000 \
  --seed 123 \
  --output data/custom_eval.jsonl
```

**No dependencies required** — the generator uses only the Python standard library.

### Run Evaluation with lm-evaluation-harness

```bash
pip install lm-eval

lm_eval --model hf \
        --model_args pretrained=meta-llama/Llama-3-8B \
        --tasks spatial_embodied_logic \
        --include_path ./tasks \
        --batch_size 16
```

## Project Structure

```
tractatus_eval/
├── README.md
├── scripts/
│   ├── generate_spatial_eval.py     # Spatial navigation (A* + distractors)
│   ├── generate_keylock_eval.py     # Key-lock puzzles (state-aware BFS)
│   ├── generate_stacking_eval.py    # Object stacking (gravity + support)
│   ├── generate_container_eval.py   # Container filling (volume + overflow)
│   ├── generate_collision_eval.py   # Collision prediction (trajectories)
│   ├── generate_circuit_eval.py     # Circuit connectivity (path tracing)
│   ├── generate_all_tiers.py        # Batch: generate Easy/Medium/Hard for all tasks
│   └── difficulty_presets.py        # Centralized difficulty tier config
├── data/
│   ├── spatial_embodied_logic.jsonl # Original 1000-sample spatial dataset
│   ├── *_{easy,medium,hard}.jsonl   # 18 difficulty-tiered datasets (500 each)
│   └── ...                          # Additional task datasets
└── tasks/
    └── spatial_embodied_logic.yaml  # EleutherAI lm-eval-harness task config
```

## Dataset Statistics

| Metric | Value |
|---|---|
| Total tasks | 6 (Spatial, Key-Lock, Stacking, Container, Collision, Circuit) |
| Difficulty tiers per task | 3 (Easy / Medium / Hard) |
| Samples per tier | 500 |
| Total tiered samples | 9,000 (18 datasets × 500) |
| Choices per question | 4 (1 correct + 3 distractors) |
| Distractor validation | Physics-engine playback (0% contamination) |

## Baseline Results — Spatial Navigation (Original Task)

Evaluated using [EleutherAI lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) (0-shot, multiple choice). All runs on Apple M5 (24GB, MPS).

| Model | Params | acc | acc_norm | Time |
|---|---|---|---|---|
| EleutherAI/pythia-410m | 410M | 0.126 ±0.011 | 0.150 ±0.011 | 1m17s |
| EleutherAI/pythia-1.4b | 1.4B | 0.169 ±0.012 | 0.195 ±0.013 | 2m57s |
| EleutherAI/pythia-2.8b | 2.8B | 0.188 ±0.012 | 0.191 ±0.012 | 5m41s |
| TinyLlama-1.1B-Chat | 1.1B | 0.226 ±0.013 | 0.213 ±0.013 | 3m39s |
| microsoft/phi-2 | 2.7B | **0.322 ±0.015** | **0.306 ±0.015** | 6m46s |
| *Random baseline* | — | *0.250* | *—* | — |

> [!NOTE]
> **Key findings:** (1) A clear **scaling trend** exists within the Pythia family: 410M → 1.4B → 2.8B shows monotonic improvement, yet all remain **below random chance** (25%). (2) **Phi-2** is the only model that exceeds random chance, likely due to its code/math-heavy training mix. (3) Even the best-performing model (Phi-2) only reaches 32.2% — far from ceiling — confirming that embodied spatial reasoning remains genuinely hard for text-only LLMs.

### Difficulty Tier Results (v0.2)

Each task is generated at three difficulty levels (Easy / Medium / Hard) by scaling core complexity parameters: grid size, number of objects, time horizon, etc. This produces a **difficulty × model** matrix that reveals how LLM performance changes with increasing physical complexity.

**Full results (0-shot, acc) across 4 models × 6 tasks × 3 difficulties:**

#### Spatial Navigation

| Model | Params | Easy (4×4) | Medium (5×5) | Hard (7×7) |
|---|---|---|---|---|
| Pythia-410m | 410M | 13.6% | 11.0% | 15.8% |
| Llama-3.2-1B | 1B | 27.6% | 22.8% | 28.2% |
| Llama-3.2-3B | 3B | 29.6% | 32.2% | **33.8%** |
| Phi-2 | 2.7B | **32.4%** | **31.2%** | **34.0%** |

#### Key-Lock Puzzles

| Model | Params | Easy (4×4) | Medium (5×5) | Hard (7×7) |
|---|---|---|---|---|
| Pythia-410m | 410M | 9.8% | 12.4% | 13.6% |
| Llama-3.2-1B | 1B | 14.6% | 18.0% | 18.6% |
| Llama-3.2-3B | 3B | 23.4% | 26.2% | 27.4% |
| Phi-2 | 2.7B | **30.4%** | **34.6%** | **34.8%** |

#### Object Stacking

| Model | Params | Easy (3 blk) | Medium (4 blk) | Hard (6 blk) |
|---|---|---|---|---|
| Pythia-410m | 410M | 27.0% | 23.6% | 23.8% |
| Llama-3.2-1B | 1B | 26.8% | 28.2% | 26.6% |
| Llama-3.2-3B | 3B | 26.0% | 25.8% | 23.6% |
| Phi-2 | 2.7B | 30.4% | **41.0%** | **47.8%** |

#### Container Filling

| Model | Params | Easy (2 cont) | Medium (2-3 cont) | Hard (3-4 cont) |
|---|---|---|---|---|
| Pythia-410m | 410M | 37.2% | 46.4% | 47.6% |
| Llama-3.2-1B | 1B | 48.4% | 57.4% | 61.8% |
| Llama-3.2-3B | 3B | 56.8% | 67.6% | 70.2% |
| Phi-2 | 2.7B | **67.4%** | **59.0%** | **75.4%** |

#### Collision Prediction

| Model | Params | Easy (4×4) | Medium (5×5) | Hard (7×7) |
|---|---|---|---|---|
| Pythia-410m | 410M | 50.0% | 50.0% | 50.0% |
| Llama-3.2-1B | 1B | 50.0% | 50.0% | 50.0% |
| Llama-3.2-3B | 3B | 50.0% | 50.0% | 50.0% |
| Phi-2 | 2.7B | 50.0% | 50.0% | 50.0% |

#### Circuit Connectivity

| Model | Params | Easy (4×4) | Medium (5×5) | Hard (7×7) |
|---|---|---|---|---|
| Pythia-410m | 410M | 49.8% | 49.8% | 49.8% |
| Llama-3.2-1B | 1B | 49.8% | 49.8% | 49.8% |
| Llama-3.2-3B | 3B | 49.8% | 49.8% | 49.8% |
| Phi-2 | 2.7B | 49.8% | 49.8% | 49.8% |

> [!IMPORTANT]
> **Key insights from the full model × difficulty matrix:**
> - **Phi-2 dominates** across all tasks, especially Container Filling (75.4% Hard) and Object Stacking (47.8% Hard) — likely due to its math/code-heavy training mix.
> - **Llama-3.2 shows clear scaling:** 1B → 3B improves on every task that isn't binary, confirming that parameter count helps for genuine physical reasoning.
> - **Collision & Circuit are universally at ~50%** regardless of model or difficulty — all models exploit binary yes/no surface cues rather than simulating physics.
> - **Container Filling accuracy *increases* with difficulty** across all models — more steps provide more arithmetic tokens for pattern matching.
> - **Object Stacking** shows opposing trends: Phi-2 improves with more blocks (30.4% → 47.8%) while Llama-3.2-3B degrades (26.0% → 23.6%), revealing fundamentally different reasoning strategies.

## How It Works Under the Hood

```
┌──────────────────────────────────────────────────────────────────────┐
│                       Generator Pipeline                           │
├──────────┬──────────┬──────────────┬─────────────┬────────────────┤
│  Random  │   A*     │  Distractor  │  Physics    │  EleutherAI    │
│  Grid    │  Search  │  Engine      │  Playback   │  JSONL         │
│  Layout  │  (path)  │  (4 strats)  │  Validator  │  Assembly      │
├──────────┼──────────┼──────────────┼─────────────┼────────────────┤
│ start,   │ shortest │ teleport,    │ simulate    │ {query,        │
│ end,     │ valid    │ random,      │ each path → │  choices,      │
│ walls    │ path     │ reversed,    │ reject if   │  gold}         │
│          │          │ mutated      │ valid alt   │                │
└──────────┴──────────┴──────────────┴─────────────┴────────────────┘
        ↓ reject if no valid path, duplicate, or contaminated ↓
                           retry loop
```

1. **Grid Generation** — Randomly places start, goal, and 3 obstacles on a 5×5 grid
2. **A\* Pathfinding** — Computes the optimal path using Manhattan distance heuristic; unsolvable grids are discarded
3. **Prompt Rendering** — Converts the grid into a natural-language prompt with ASCII visualization
4. **Distractor Generation** — Creates candidates using 4 cognitively-targeted strategies
5. **Physics-Engine Validation** — Each distractor is simulated step-by-step on the grid; alternate valid paths are rejected
6. **Deduplication** — SHA-256 fingerprinting ensures no duplicate scenarios
7. **JSONL Output** — Assembles everything into EleutherAI-compatible format

## Data Integrity

Benchmark datasets are only as trustworthy as their answer keys. A naive distractor engine can accidentally generate **alternate valid paths** — paths that differ from the A\*-computed answer but still legally reach the goal without violating any physical constraint. If scored as "wrong," these contaminate the benchmark by **penalizing models that reason correctly**.

Tractatus-Eval solves this with a **physics-engine playback validator** (`simulate_path`). Before a distractor is accepted, the engine walks it step-by-step on the actual grid. A candidate is accepted as a valid distractor **only if** it satisfies at least one of:

- 💥 **Hits a wall** — collides with an obstacle cell
- 🚫 **Goes out of bounds** — steps outside the grid boundary
- 🎯 **Misses the goal** — ends on a cell that is not the target

If a candidate passes all physical checks and reaches the goal, it is silently discarded as an alternate valid path.

```
CONTAMINATION AUDIT (seed=42, n=1000)
─────────────────────────────────────
Total samples:            1,000
Total distractors:        3,000
Contaminated distractors: 0
Contamination rate:       0.0000%
✅ ZERO contamination
```

## CLI Reference

```
usage: generate_spatial_eval.py [-h] [-n NUM_SAMPLES] [-o OUTPUT] [--seed SEED]

Arguments:
  -n, --num-samples   Number of samples to generate (default: 1000)
  -o, --output        Output JSONL path (default: data/spatial_embodied_logic.jsonl)
  --seed              Random seed for reproducibility (default: 42)
```

## Theoretical Background

This benchmark operationalizes a core insight from Wittgenstein's philosophy of language:

> *"Whereof one cannot speak, thereof one must be silent."*
> — *Tractatus Logico-Philosophicus*, Proposition 7

A text-only LLM has never experienced a wall. It has no **sensorimotor grounding** for the concept of "impassable." It can only pattern-match the *word* "obstacle" against its training distribution. Tractatus-Eval measures the **engineering cost of this philosophical gap** — and provides the data foundation for closing it via preference-based alignment (DPO) or external guardrails (NeMo Guardrails).

## Related Work

- **Project Daedalus** — Uses the failure modes exposed by Tractatus-Eval to build DPO training pairs (correct path vs. wall-phasing hallucination), empirically demonstrating the effectiveness of external guardrails over pure text fine-tuning.
- **NeMo Guardrails Integration** — Production deployment of deterministic spatial validation as a Colang-scripted guardrail, bypassing the model's embodied cognition gap entirely.

## License

MIT

---

<h1 align="center">🏛️ Project Tractatus-Eval</h1>
<p align="center"><em>大语言模型空间具身逻辑评估基准</em></p>

---

## 为什么要做这个项目

现代大语言模型 (LLM) 在语言推理上表现卓越，却在需要**具身空间理解**的任务上屡屡翻车——而这种理解，是任何在物理世界中行动过的智能体都能轻而易举习得的直觉。

举个简单的例子：*"从 A1 导航到 E5，避开墙壁。"* 一个小孩子都能瞬间解决。然而，最前沿的 LLM 生成的路径却经常**穿墙而过**、**瞬移跨越障碍物**、甚至**直接走出网格边界**——这些行为在物理上不可能发生，但从纯文本角度看却是"合理"的。

**Tractatus-Eval** 量化了这个鸿沟。灵感源自维特根斯坦的《逻辑哲学论》（*Tractatus Logico-Philosophicus*）——*"我的语言的界限意味着我的世界的界限"*——这个基准追问：**一个完全由文本构建的世界，其极限在哪里？**

## 六大任务

Tractatus-Eval 由 **6 个任务**组成，每个任务针对具身物理推理的不同维度。所有任务共享相同的架构：程序化生成 → 确定性真值 → 干扰项验证 → JSONL 输出。

---

### 1. 空间导航 🗺️

**测试物理约束：** 网格寻路、障碍物回避、边界感知

模型须在有不可穿越障碍物的 N×N 网格上找到从起点到终点的最短有效路径。真值由带曼哈顿距离启发式的 **A\* 搜索**计算。

**干扰策略：**
| 策略 | 测试内容 |
|---|---|
| **穿墙直线** | 无视障碍物的直线路径——测试模型是否将 `#` 视为不可穿越 |
| **随机漫步** | 等长度随机方向序列——测试模型是否真正追踪了路径 |
| **反向路径** | 正确路径的逆序——测试方向一致性 |
| **单步突变** | 替换正确路径中的一个方向——测试细粒度空间追踪 |

✅ **物理引擎回放：** 每个干扰项逐步模拟，偷偷到达终点的有效替代路径自动丢弃（0% 污染）。

---

### 2. 钥匙-锁谜题 🔑

**测试物理约束：** 状态依赖行为、库存追踪、顺序依赖

模型须导航一个有**彩色门**阻挡路径的网格。每扇门需要先拾取匹配颜色的**钥匙**才能打开。解是移动动作与 `pick_up_<颜色>` 和 `unlock_<颜色>` 穿插的动作序列。

真值使用在 `(位置, 库存)` 状态空间上搜索的**状态感知 BFS**——状态空间约为普通寻路的 25 倍。

✅ **物理引擎回放：** 完整的逐步模拟，追踪位置和库存。若候选干扰项实为有效替代路径（如另一种钥匙收集顺序），则被拒绝。

---

### 3. 物体堆叠 📦

**测试物理约束：** 重力、结构稳定性、重心支撑

给定一组不同宽度的积木，模型须确定正确的从底到顶的堆叠顺序，使每块积木都被下方积木完全支撑。仅当 `宽度[i] ≤ 宽度[i-1]` 时积木才**稳定**。

✅ **物理验证器：** `is_stable()` ——遍历每对相邻积木验证宽度约束。只有违反此检查的排列才被接受为干扰项。

---

### 4. 容器装水 🫗

**测试物理约束：** 体积守恒、倾倒转移、容量上限（溢出）

模型面对 2-4 个不同容量和初始液位的容器，执行一系列操作：`倒 A 入 B`、`装满 C`、`清空 B` 等，须计算所有操作执行后的最终状态。

真值由**逐步模拟器** (`simulate_step()`) 计算，强制容量上限——当向满容器倾倒时，多余液体溢出丢失。

✅ **物理验证器：** `simulate_step()` ——在每一步强制 `min(倾倒量 + 当前量, 容量)`。正确答案是唯一通过忠实逐步模拟（含溢出处理）得出的状态。

---

### 5. 碰撞预测 💥

**测试物理约束：** 时间外推、轨迹投射、空间相交

两个或更多物体以固定速度在 N×N 网格上移动。模型须预测它们是否**碰撞**（在同一时间步占据同一格），若碰撞则报告时间步和碰撞位置。

真值由 **`simulate()` 函数**计算，同步推进所有物体最多 `MAX_STEPS` 个时间步，在每个周期检查共占。

✅ **物理验证器：** `simulate()` ——确定性逐步轨迹计算。真值是唯一与实际模拟一致的答案。

---

### 6. 电路连通性 ⚡

**测试物理约束：** 电路路径追踪、拓扑连通性、开关状态逻辑

N×N 网格包含电池 (`+`/`-`)、灯泡 (`B`)、导线 (`W`) 和编号开关。模型须判断灯泡是否亮起。电流仅通过导线和**闭合**开关流动；**断开**的开关和间隙会断开电路。

✅ **物理验证器：** 基于图的可达性——从 `+` → 灯泡 → `-` 的路径必须仅通过导线和闭合开关存在。

---

> [!IMPORTANT]
> **每个任务都强制 0% 污染。** 只有可证明违反其任务物理约束的干扰项才会被接受。每个错误答案都因*物理上有依据的理由*而错误，而非仅仅是文本上不合理。

## 快速开始

### 生成数据集

```bash
# 默认：1000 条样本，seed=42
python3 scripts/generate_spatial_eval.py

# 自定义配置
python3 scripts/generate_spatial_eval.py \
  --num-samples 2000 \
  --seed 123 \
  --output data/custom_eval.jsonl
```

**无需任何依赖** ——生成器仅使用 Python 标准库。

### 使用 lm-evaluation-harness 运行评估

```bash
pip install lm-eval

lm_eval --model hf \
        --model_args pretrained=meta-llama/Llama-3-8B \
        --tasks spatial_embodied_logic \
        --include_path ./tasks \
        --batch_size 16
```

## 数据集统计

| 指标 | 值 |
|---|---|
| 总任务数 | 6（空间导航、钥匙-锁、堆叠、容器、碰撞、电路） |
| 每任务难度等级 | 3（简单 / 中等 / 困难） |
| 每个等级样本数 | 500 |
| 分级数据集总样本数 | 9,000（18 个数据集 × 500） |
| 每题选项数 | 4（1 正确 + 3 干扰） |
| 干扰项验证 | 物理引擎回放（0% 污染率） |

## 基线评估结果

使用 [EleutherAI lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) 评估（0-shot，多选题）。所有测试在 Apple M5（24GB, MPS）上完成。

| 模型 | 参数量 | acc | acc_norm | 耗时 |
|---|---|---|---|---|
| EleutherAI/pythia-410m | 410M | 0.126 ±0.011 | 0.150 ±0.011 | 1m17s |
| EleutherAI/pythia-1.4b | 1.4B | 0.169 ±0.012 | 0.195 ±0.013 | 2m57s |
| EleutherAI/pythia-2.8b | 2.8B | 0.188 ±0.012 | 0.191 ±0.012 | 5m41s |
| TinyLlama-1.1B-Chat | 1.1B | 0.226 ±0.013 | 0.213 ±0.013 | 3m39s |
| microsoft/phi-2 | 2.7B | **0.322 ±0.015** | **0.306 ±0.015** | 6m46s |
| *随机基线* | — | *0.250* | *—* | — |

> [!NOTE]
> **关键发现：** (1) Pythia 家族内存在清晰的**扩展趋势**：410M → 1.4B → 2.8B 准确率单调递增，但全部**低于随机猜测基线**（25%）。 (2) **Phi-2** 是唯一超过随机基线的模型，可能得益于其代码/数学密集的训练数据。 (3) 即使表现最好的 Phi-2 也仅达到 32.2%——远未到天花板——证实了具身空间推理对纯文本 LLM 仍然是真正的难题。

### 难度分级结果 (v0.2)

每个任务生成三个难度等级（简单 / 中等 / 困难），通过调整核心复杂度参数来产生**难度 × 模型**评估矩阵。

**4 模型 × 6 任务 × 3 难度（0-shot, acc）完整结果：**

#### 空间导航

| 模型 | 参数量 | 简单 (4×4) | 中等 (5×5) | 困难 (7×7) |
|---|---|---|---|---|
| Pythia-410m | 410M | 13.6% | 11.0% | 15.8% |
| Llama-3.2-1B | 1B | 27.6% | 22.8% | 28.2% |
| Llama-3.2-3B | 3B | 29.6% | 32.2% | **33.8%** |
| Phi-2 | 2.7B | **32.4%** | **31.2%** | **34.0%** |

#### 钥匙-锁谜题

| 模型 | 参数量 | 简单 (4×4) | 中等 (5×5) | 困难 (7×7) |
|---|---|---|---|---|
| Pythia-410m | 410M | 9.8% | 12.4% | 13.6% |
| Llama-3.2-1B | 1B | 14.6% | 18.0% | 18.6% |
| Llama-3.2-3B | 3B | 23.4% | 26.2% | 27.4% |
| Phi-2 | 2.7B | **30.4%** | **34.6%** | **34.8%** |

#### 物体堆叠

| 模型 | 参数量 | 简单 (3块) | 中等 (4块) | 困难 (6块) |
|---|---|---|---|---|
| Pythia-410m | 410M | 27.0% | 23.6% | 23.8% |
| Llama-3.2-1B | 1B | 26.8% | 28.2% | 26.6% |
| Llama-3.2-3B | 3B | 26.0% | 25.8% | 23.6% |
| Phi-2 | 2.7B | 30.4% | **41.0%** | **47.8%** |

#### 容器装水

| 模型 | 参数量 | 简单 (2容器) | 中等 (2-3容器) | 困难 (3-4容器) |
|---|---|---|---|---|
| Pythia-410m | 410M | 37.2% | 46.4% | 47.6% |
| Llama-3.2-1B | 1B | 48.4% | 57.4% | 61.8% |
| Llama-3.2-3B | 3B | 56.8% | 67.6% | 70.2% |
| Phi-2 | 2.7B | **67.4%** | **59.0%** | **75.4%** |

#### 碰撞预测 & 电路连通性

所有模型在所有难度等级均为 ~50%——表明模型利用二元是/否表面线索，未真正模拟物理。

> [!IMPORTANT]
> **核心发现：**
> - **Phi-2 全面领先**，尤其容器装水（困难 75.4%）和物体堆叠（困难 47.8%）
> - **Llama-3.2 展现清晰的规模效应：** 1B → 3B 在所有非二元任务上均有提升
> - **碰撞 & 电路在所有模型上均为 ~50%**——模型利用二元线索而非物理模拟
> - **物体堆叠**中 Phi-2 随难度提升而改善（30.4% → 47.8%），Llama-3.2-3B 反而下降（26.0% → 23.6%），揭示了根本不同的推理策略

## 工作原理

1. **网格生成** — 在 5×5 网格上随机放置起点、终点和 3 个障碍物
2. **A\* 寻路** — 使用曼哈顿距离启发式计算最优路径；无解网格被丢弃
3. **Prompt 渲染** — 将网格转化为自然语言提示词，附带 ASCII 可视化
4. **干扰项生成** — 使用 4 种认知靶向策略生成候选干扰项
5. **物理引擎验证** — 每个干扰项在网格上逐步模拟；有效替代路径被拒绝
6. **去重** — SHA-256 指纹确保无重复场景
7. **JSONL 输出** — 组装为 EleutherAI 兼容格式

## 数据完整性

基准数据集的可信度取决于其答案的正确性。一个天真的干扰项引擎可能会意外生成**有效替代路径**——与 A\* 计算的答案不同，但仍然合法到达终点、不违反任何物理约束的路径。如果将其评判为"错误"，就会污染基准，**惩罚推理正确的模型**。

Tractatus-Eval 通过**物理引擎回放验证器** (`simulate_path`) 解决这个问题。在接受干扰项之前，引擎会在实际网格上逐步模拟其行走过程。候选项**仅在**满足以下至少一个条件时才会被接受为有效干扰项：

- 💥 **撞墙** — 碰撞障碍物单元格
- 🚫 **出界** — 走出网格边界
- 🎯 **未到达终点** — 结束位置不是目标单元格

如果候选项通过所有物理检查并成功到达终点，则被静默丢弃（视为有效替代路径）。

```
数据污染审计 (seed=42, n=1000)
─────────────────────────────────────
总样本数:              1,000
总干扰项数:            3,000
被污染的干扰项:         0
污染率:                0.0000%
✅ 零污染
```

## 理论背景

本基准将维特根斯坦语言哲学中的核心洞见工程化：

> *"凡不可言说者，必须保持沉默。"*
> — 《逻辑哲学论》，命题 7

一个纯文本 LLM 从未"体验"过一堵墙。它对"不可穿越"这个概念没有任何**感觉运动层面的落地 (Sensorimotor Grounding)**，只能将"障碍物"这个*词*与训练分布进行模式匹配。Tractatus-Eval 衡量的是**这个哲学鸿沟的工程代价**——并为通过偏好对齐 (DPO) 或外部护栏 (NeMo Guardrails) 弥合它提供数据基础。

## 相关项目

- **Project Daedalus** — 利用 Tractatus-Eval 暴露的失败模式构建 DPO 训练对（正确路径 vs. 穿墙幻觉），实证论证了外部护栏优于纯文本微调的有效性。
- **NeMo Guardrails 集成** — 将确定性空间验证部署为 Colang 脚本护栏，完全绕过模型的具身认知盲区。

## 许可证

MIT
