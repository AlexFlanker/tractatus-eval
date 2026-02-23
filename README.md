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

## What It Measures

Each evaluation sample presents a **5×5 grid navigation problem** with:

- A **start position** and **goal position**
- **3 impassable obstacles** (walls)
- An **ASCII map** for visual grounding
- **4 multiple-choice answers** (1 correct, 3 distractors)

The ground-truth shortest path is computed via **A\* search**. Distractors are specifically designed to exploit embodied cognition blindspots:

| Distractor Strategy | What It Tests |
|---|---|
| **Wall Teleportation** | Straight-line path ignoring obstacles — tests if the model treats `#` as truly impassable |
| **Random Walk** | Same-length random direction sequence — tests if the model actually traces the path |
| **Reversed Path** | Correct path played backwards — tests directional coherence |
| **Off-by-One Mutation** | Single-direction swap in the correct path — tests fine-grained spatial tracking |

> [!IMPORTANT]
> Every distractor candidate is validated through a **physics-engine playback** step before acceptance. Candidates that are secretly valid alternate paths (reach the goal without hitting any wall or boundary) are **automatically discarded**, preventing data contamination where correct answers would be scored as wrong. See [Data Integrity](#data-integrity) below.

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
│   └── generate_spatial_eval.py   # Data generator (A* + distractors + JSONL)
├── data/
│   └── spatial_embodied_logic.jsonl  # Pre-generated 1000-sample dataset
└── tasks/
    └── spatial_embodied_logic.yaml   # EleutherAI lm-eval-harness task config
```

## Dataset Statistics

| Metric | Value |
|---|---|
| Total samples | 1,000 |
| Grid size | 5 × 5 |
| Obstacles per grid | 3 |
| Choices per question | 4 (1 correct + 3 distractors) |
| Avg shortest path | 3.5 steps |
| Path length range | 1 – 9 steps |
| Deduplication | SHA-256 fingerprint |
| Distractor validation | Physics-engine playback (0% contamination) |
| Generation efficiency | ~99% (1,006 attempts for 1,000 samples) |

## Baseline Results

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

### Expanded Embodied Tasks (New in v0.2!)

We have expanded the benchmark with 5 additional tasks that test distinct physical constraints. Evaluated with `EleutherAI/pythia-410m` (0-shot):

| Task | Physics Tested | Pythia-410m Accuracy |
|---|---|---|
| **Key-Lock Puzzles** | State dependency (keys must be gathered before doors) | 11.7% (deeply below random) |
| **Object Stacking** | Gravity, structural integrity, center-of-mass support | 21.4% (below random) |
| **Container Filling** | Volume, pouring transfers, capacity clipping (overflow) | 46.1% |
| **Circuit Connectivity** | Electrical path tracing and strict topological loops | 49.9% |
| **Collision Prediction** | Temporal extrapolation, object trajectories, spatial intersection | 50.0% |

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

## 测量什么

每个评估样本呈现一个 **5×5 网格导航问题**：

- 一个**起点**和一个**终点**
- **3 个不可穿越的障碍物**（墙壁）
- 一张 **ASCII 地图**用于视觉定位
- **4 个选择项**（1 个正确 + 3 个干扰项）

真值最短路径由 **A\* 搜索算法**计算。干扰项专门设计用于利用具身认知的盲区：

| 干扰策略 | 测试内容 |
|---|---|
| **穿墙直线** | 无视障碍物的直线路径——测试模型是否将 `#` 视为真正不可穿越 |
| **随机漫步** | 等长度随机方向序列——测试模型是否真正追踪了路径 |
| **反向路径** | 正确路径的逆序——测试方向一致性 |
| **单步突变** | 在正确路径中替换一个方向——测试细粒度空间追踪能力 |

> [!IMPORTANT]
> 每个干扰项候选在被接受之前，都会通过**物理引擎回放**步骤进行验证。那些本质上是有效替代路径的候选（成功到达终点且未碰撞任何墙壁或边界）会被**自动丢弃**，防止数据污染（即把正确答案判为错误）。详见下方[数据完整性](#数据完整性)。

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
| 总样本数 | 1,000 |
| 网格尺寸 | 5 × 5 |
| 每个网格障碍物数 | 3 |
| 每题选项数 | 4（1 正确 + 3 干扰） |
| 平均最短路径 | 3.5 步 |
| 路径长度范围 | 1 – 9 步 |
| 去重机制 | SHA-256 指纹 |
| 干扰项验证 | 物理引擎回放（0% 污染率） |
| 生成效率 | ~99%（1,006 次尝试生成 1,000 条） |

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

### 扩展的具身认知任务 (v0.2 新增！)

我们在基准中新增了 5 个测试不同物理约束的任务。使用 `EleutherAI/pythia-410m` (0-shot) 的评估结果如下：

| 任务 | 测试的物理约束 | Pythia-410m 准确率 |
|---|---|---|
| **钥匙-锁谜题 (Key-Lock Puzzles)** | 状态依赖（必须先拾取钥匙才能开门） | 11.7% (远低于随机猜测) |
| **物体堆叠 (Object Stacking)** | 重力、结构完整性、重心支撑 | 21.4% (低于随机猜测) |
| **容器装水 (Container Filling)** | 容量、倾倒转移、溢出限制 | 46.1% |
| **电路连通性 (Circuit Connectivity)** | 电路追踪与严格的拓扑回路 | 49.9% |
| **碰撞预测 (Collision Prediction)** | 时间外推、物体轨迹、空间相交 | 50.0% |

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
