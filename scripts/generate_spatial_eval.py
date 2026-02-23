#!/usr/bin/env python3
"""
Project Tractatus-Eval — Spatial Embodied Logic Data Generator
==============================================================
Generates evaluation samples that test whether an LLM understands
hard physical constraints (walls, obstacles, grid boundaries) that
any embodied agent would trivially learn through interaction.

Each sample contains:
  - A natural-language prompt describing a 5×5 grid with obstacles
  - A ground-truth shortest path computed via A* search
  - Distractor (wrong) answers for multiple-choice evaluation

Output: JSONL compatible with EleutherAI `lm-evaluation-harness`.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

Coord = Tuple[int, int]

GRID_SIZE = 5
NUM_OBSTACLES = 3
DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Up, Down, Left, Right
DIR_NAMES = {(-1, 0): "up", (1, 0): "down", (0, -1): "left", (0, 1): "right"}


@dataclass
class GridScenario:
    """A single 5×5 grid evaluation scenario."""

    grid_size: int
    start: Coord
    end: Coord
    obstacles: Set[Coord]
    shortest_path: Optional[List[Coord]] = None
    path_directions: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# A* Pathfinding
# ---------------------------------------------------------------------------

def heuristic(a: Coord, b: Coord) -> int:
    """Manhattan distance heuristic."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def a_star(
    start: Coord,
    end: Coord,
    obstacles: Set[Coord],
    grid_size: int = GRID_SIZE,
) -> Optional[List[Coord]]:
    """
    A* search on a grid. Returns the shortest path as a list of
    coordinates from `start` to `end`, or None if no path exists.
    """
    open_set: list[tuple[int, int, Coord, list[Coord]]] = []
    # (f_score, counter, current_node, path)
    counter = 0
    heapq.heappush(open_set, (heuristic(start, end), counter, start, [start]))
    visited: Set[Coord] = set()

    while open_set:
        f, _, current, path = heapq.heappop(open_set)

        if current == end:
            return path

        if current in visited:
            continue
        visited.add(current)

        for dr, dc in DIRECTIONS:
            neighbor = (current[0] + dr, current[1] + dc)
            if (
                0 <= neighbor[0] < grid_size
                and 0 <= neighbor[1] < grid_size
                and neighbor not in obstacles
                and neighbor not in visited
            ):
                g = len(path)  # cost so far
                f_new = g + heuristic(neighbor, end)
                counter += 1
                heapq.heappush(open_set, (f_new, counter, neighbor, path + [neighbor]))

    return None  # No valid path


def path_to_directions(path: List[Coord]) -> List[str]:
    """Convert a coordinate path to a list of direction strings."""
    directions = []
    for i in range(len(path) - 1):
        dr = path[i + 1][0] - path[i][0]
        dc = path[i + 1][1] - path[i][1]
        directions.append(DIR_NAMES[(dr, dc)])
    return directions


# ---------------------------------------------------------------------------
# Scenario generation
# ---------------------------------------------------------------------------

def generate_scenario(rng: random.Random) -> Optional[GridScenario]:
    """
    Generate a single valid grid scenario with guaranteed solvability.
    Returns None if the random placement yields no valid path (caller retries).
    """
    all_coords = [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)]
    chosen = rng.sample(all_coords, 2 + NUM_OBSTACLES)

    start, end = chosen[0], chosen[1]
    obstacles = set(chosen[2:])

    path = a_star(start, end, obstacles)
    if path is None:
        return None

    return GridScenario(
        grid_size=GRID_SIZE,
        start=start,
        end=end,
        obstacles=obstacles,
        shortest_path=path,
        path_directions=path_to_directions(path),
    )


# ---------------------------------------------------------------------------
# Natural-language prompt rendering
# ---------------------------------------------------------------------------

def coord_label(c: Coord) -> str:
    """Human-friendly label: row 0‒4 → A‒E, col 0‒4 → 1‒5."""
    return f"{chr(65 + c[0])}{c[1] + 1}"


def render_grid_ascii(scenario: GridScenario) -> str:
    """Render the grid as a compact ASCII diagram."""
    lines = ["  " + " ".join(str(c + 1) for c in range(GRID_SIZE))]
    for r in range(GRID_SIZE):
        row_label = chr(65 + r)
        cells = []
        for c in range(GRID_SIZE):
            pos = (r, c)
            if pos == scenario.start:
                cells.append("S")
            elif pos == scenario.end:
                cells.append("E")
            elif pos in scenario.obstacles:
                cells.append("#")
            else:
                cells.append(".")
        lines.append(f"{row_label} " + " ".join(cells))
    return "\n".join(lines)


def render_prompt(scenario: GridScenario) -> str:
    """Build the natural-language evaluation prompt."""
    obs_labels = sorted(coord_label(o) for o in scenario.obstacles)
    obs_str = ", ".join(obs_labels)

    grid_ascii = render_grid_ascii(scenario)

    prompt = (
        f"You are navigating a {GRID_SIZE}×{GRID_SIZE} grid. "
        f"Rows are labeled A–E (top to bottom), columns 1–5 (left to right). "
        f"You can move one step at a time: up, down, left, or right. "
        f"You CANNOT move diagonally, move outside the grid boundaries, "
        f"or pass through obstacle cells.\n\n"
        f"Grid map:\n{grid_ascii}\n\n"
        f"Start: {coord_label(scenario.start)}  |  "
        f"Goal: {coord_label(scenario.end)}  |  "
        f"Obstacles (impassable): {obs_str}\n\n"
        f"What is the shortest valid path from "
        f"{coord_label(scenario.start)} to {coord_label(scenario.end)}? "
        f"Give your answer as a comma-separated list of directions "
        f"(up/down/left/right)."
    )
    return prompt


# ---------------------------------------------------------------------------
# Physics-engine playback validator
# ---------------------------------------------------------------------------

DIR_VECTORS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}


@dataclass
class SimulationResult:
    """Result of physically simulating a direction sequence on the grid."""

    reached_goal: bool       # Did the agent land on the goal cell?
    hit_wall: bool           # Did any step collide with an obstacle?
    out_of_bounds: bool      # Did any step leave the grid?
    final_position: Coord    # Where was the agent when the path ended?


def simulate_path(
    start: Coord,
    end: Coord,
    obstacles: Set[Coord],
    directions: List[str],
    grid_size: int = GRID_SIZE,
) -> SimulationResult:
    """
    Physics-engine playback: simulate walking the direction sequence
    step-by-step on the actual grid, checking every move against
    physical constraints (walls, boundaries).
    """
    pos = start
    hit_wall = False
    out_of_bounds = False

    for d in directions:
        vec = DIR_VECTORS.get(d)
        if vec is None:
            # Invalid direction token — treat as out-of-bounds
            out_of_bounds = True
            break
        next_pos = (pos[0] + vec[0], pos[1] + vec[1])

        if not (0 <= next_pos[0] < grid_size and 0 <= next_pos[1] < grid_size):
            out_of_bounds = True
            break
        if next_pos in obstacles:
            hit_wall = True
            break
        pos = next_pos

    return SimulationResult(
        reached_goal=(pos == end),
        hit_wall=hit_wall,
        out_of_bounds=out_of_bounds,
        final_position=pos,
    )


def is_path_physically_invalid(
    start: Coord,
    end: Coord,
    obstacles: Set[Coord],
    directions: List[str],
    grid_size: int = GRID_SIZE,
) -> bool:
    """
    A distractor is ONLY valid if it is physically WRONG.

    It must satisfy at least one of:
      - Hits a wall (obstacle collision)
      - Goes out of bounds
      - Does NOT reach the goal cell after all steps

    If the path successfully reaches the goal without any violation,
    it is an Alternate Valid Path and MUST be discarded.
    """
    result = simulate_path(start, end, obstacles, directions, grid_size)

    if result.hit_wall or result.out_of_bounds:
        return True  # Physically invalid — good distractor
    if not result.reached_goal:
        return True  # Didn't reach goal — good distractor

    # The path is a valid alternate solution — REJECT as distractor
    return False


# ---------------------------------------------------------------------------
# Distractor generation (with physics-engine validation)
# ---------------------------------------------------------------------------

def generate_distractors(
    scenario: GridScenario, rng: random.Random, num_distractors: int = 3
) -> List[str]:
    """
    Generate plausible but WRONG direction sequences.

    Every candidate distractor is simulated through the physics engine.
    Candidates that are secretly valid alternate paths are DISCARDED
    to prevent data contamination (scoring correct answers as wrong).

    Strategies:
      1. Shortcut through an obstacle (ignores physics)
      2. Random walk of similar length
      3. Reversed correct path
    """
    correct = scenario.path_directions
    if not correct:
        return []

    distractors: List[str] = []
    used: Set[str] = {", ".join(correct)}

    def _try_add(candidate_dirs: List[str]) -> bool:
        """Validate and add a distractor candidate. Returns True if accepted."""
        candidate_str = ", ".join(candidate_dirs)
        if candidate_str in used:
            return False

        # ── THE CRITICAL GATE ──
        # Simulate the path on the actual grid. Reject if it turns out
        # to be a valid alternate solution.
        if not is_path_physically_invalid(
            scenario.start, scenario.end, scenario.obstacles, candidate_dirs
        ):
            return False  # Alternate valid path — discard silently

        distractors.append(candidate_str)
        used.add(candidate_str)
        return True

    # Strategy 1: "Teleport" — straight-line ignoring obstacles
    naive_dirs: List[str] = []
    sr, sc = scenario.start
    er, ec = scenario.end
    while sr != er:
        naive_dirs.append("down" if er > sr else "up")
        sr += 1 if er > sr else -1
    while sc != ec:
        naive_dirs.append("right" if ec > sc else "left")
        sc += 1 if ec > sc else -1
    _try_add(naive_dirs)

    # Strategy 2: Random walk of same length
    all_dir_names = ["up", "down", "left", "right"]
    for _ in range(50):  # increased attempt cap to compensate for rejections
        if len(distractors) >= num_distractors:
            break
        rand_path = [rng.choice(all_dir_names) for _ in range(len(correct))]
        _try_add(rand_path)

    # Strategy 3: Reversed correct path
    if len(distractors) < num_distractors:
        opposite = {"up": "down", "down": "up", "left": "right", "right": "left"}
        rev_flipped = [opposite[d] for d in reversed(correct)]
        _try_add(rev_flipped)

    # Strategy 4 (fallback): Off-by-one detour — swap two adjacent directions
    if len(distractors) < num_distractors and len(correct) >= 2:
        for _ in range(20):
            if len(distractors) >= num_distractors:
                break
            mutated = list(correct)
            idx = rng.randint(0, len(mutated) - 1)
            mutated[idx] = rng.choice(all_dir_names)
            _try_add(mutated)

    return distractors[:num_distractors]


# ---------------------------------------------------------------------------
# EleutherAI lm-evaluation-harness JSONL assembly
# ---------------------------------------------------------------------------

def scenario_to_eval_doc(
    scenario: GridScenario, rng: random.Random, doc_id: int
) -> dict:
    """
    Assemble a single evaluation document in the format expected by
    EleutherAI lm-evaluation-harness (multiple-choice style).

    Schema:
      {
        "doc_id": <int>,
        "query":  <str>,         # the prompt
        "choices": [<str>, ...], # list of answer options
        "gold":   <int>          # index of the correct answer in `choices`
      }
    """
    prompt = render_prompt(scenario)
    correct_answer = ", ".join(scenario.path_directions)
    distractors = generate_distractors(scenario, rng)

    # Shuffle choices; track correct index
    choices = [correct_answer] + distractors
    answer_pairs = list(enumerate(choices))
    rng.shuffle(answer_pairs)
    gold_idx = next(i for i, (orig_i, _) in enumerate(answer_pairs) if orig_i == 0)
    shuffled_choices = [c for _, c in answer_pairs]

    # Deterministic fingerprint for deduplication
    fingerprint = hashlib.sha256(prompt.encode()).hexdigest()[:12]

    return {
        "doc_id": doc_id,
        "query": prompt,
        "choices": shuffled_choices,
        "gold": gold_idx,
        "metadata": {
            "grid_size": scenario.grid_size,
            "start": coord_label(scenario.start),
            "end": coord_label(scenario.end),
            "obstacles": sorted(coord_label(o) for o in scenario.obstacles),
            "shortest_path_length": len(scenario.shortest_path) - 1,
            "fingerprint": fingerprint,
        },
    }


# ---------------------------------------------------------------------------
# Main driver
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tractatus-Eval: Spatial Embodied Logic dataset generator"
    )
    parser.add_argument(
        "-n", "--num-samples",
        type=int,
        default=1000,
        help="Number of evaluation samples to generate (default: 1000)",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output JSONL file path (default: ../data/spatial_embodied_logic.jsonl)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    args = parser.parse_args()

    # Resolve output path
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path(__file__).resolve().parent.parent / "data" / "spatial_embodied_logic.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    samples: list[dict] = []
    seen_fingerprints: set[str] = set()
    attempts = 0
    max_attempts = args.num_samples * 20  # safety valve

    print(f"[Tractatus-Eval] Generating {args.num_samples} samples (seed={args.seed})...")

    while len(samples) < args.num_samples and attempts < max_attempts:
        attempts += 1
        scenario = generate_scenario(rng)
        if scenario is None:
            continue

        doc = scenario_to_eval_doc(scenario, rng, doc_id=len(samples))
        fp = doc["metadata"]["fingerprint"]
        if fp in seen_fingerprints:
            continue  # skip duplicates

        seen_fingerprints.add(fp)
        samples.append(doc)

    # Write JSONL
    with open(out_path, "w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print(f"[Tractatus-Eval] ✅ Generated {len(samples)} samples in {attempts} attempts.")
    print(f"[Tractatus-Eval] 📄 Output: {out_path}")

    # Quick sanity stats
    path_lengths = [s["metadata"]["shortest_path_length"] for s in samples]
    avg_len = sum(path_lengths) / len(path_lengths) if path_lengths else 0
    print(f"[Tractatus-Eval] 📊 Avg shortest path length: {avg_len:.1f} steps")
    print(f"[Tractatus-Eval] 📊 Path length range: {min(path_lengths)}–{max(path_lengths)} steps")


if __name__ == "__main__":
    main()
