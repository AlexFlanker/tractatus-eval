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
