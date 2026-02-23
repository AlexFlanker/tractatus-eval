#!/usr/bin/env python3
"""
Project Tractatus-Eval — Key-Lock Puzzle Data Generator
========================================================
Generates evaluation samples that test whether an LLM understands
state-dependent actions: keys must be PICKED UP before the matching
door can be UNLOCKED. The model must find a valid action sequence
from start to goal.

Architecture mirrors generate_spatial_eval.py:
  1. Procedural grid generation with keys, locked doors, obstacles
  2. BFS pathfinding that tracks agent inventory state
  3. Physics-engine playback to validate distractors
  4. EleutherAI lm-evaluation-harness JSONL output

Usage:
    python3 scripts/generate_keylock_eval.py
    python3 scripts/generate_keylock_eval.py -n 500 --seed 123
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

Coord = Tuple[int, int]

GRID_SIZE = 5
NUM_OBSTACLES = 2
DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DIR_NAMES = {(-1, 0): "up", (1, 0): "down", (0, -1): "left", (0, 1): "right"}
DIR_VECTORS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}

COLORS = ["red", "blue"]
COLOR_EMOJI = {"red": "🔴", "blue": "🔵"}
DOOR_EMOJI = {"red": "[🔴]", "blue": "[🔵]"}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class KeyLockScenario:
    """A grid scenario with keys, locked doors, and obstacles."""

    grid_size: int
    start: Coord
    end: Coord
    obstacles: Set[Coord]
    keys: Dict[Coord, str]  # position → color
    doors: Dict[Coord, str]  # position → color (locked)
    solution_actions: Optional[List[str]] = None
    solution_path: Optional[List[Coord]] = None


# ---------------------------------------------------------------------------
# State-aware BFS pathfinding
# ---------------------------------------------------------------------------

# State = (position, frozenset of keys held)
State = Tuple[Coord, FrozenSet[str]]


def bfs_with_keys(
    start: Coord,
    end: Coord,
    obstacles: Set[Coord],
    keys: Dict[Coord, str],
    doors: Dict[Coord, str],
    grid_size: int = GRID_SIZE,
) -> Optional[Tuple[List[Coord], List[str]]]:
    """
    BFS over (position, inventory) state space.
    Returns (path_coords, action_list) or None if unsolvable.

    Actions are: up, down, left, right, pick_up_<color>, unlock_<color>
    """
    initial_state: State = (start, frozenset())
    queue: deque = deque()
    queue.append((initial_state, [start], []))
    visited: Set[State] = {initial_state}

    door_positions = set(doors.keys())

    while queue:
        (pos, inv), path, actions = queue.popleft()

        # --- Try picking up a key at current position ---
        if pos in keys and keys[pos] not in inv:
            color = keys[pos]
            new_inv = inv | {color}
            new_state: State = (pos, new_inv)
            if new_state not in visited:
                visited.add(new_state)
                queue.append(
                    (new_state, path + [pos], actions + [f"pick_up_{color}"])
                )

        # --- Try moving in each direction ---
        for d in DIRECTIONS:
            nr, nc = pos[0] + d[0], pos[1] + d[1]
            new_pos = (nr, nc)

            # Boundary check
            if not (0 <= nr < grid_size and 0 <= nc < grid_size):
                continue
            # Obstacle check
            if new_pos in obstacles:
                continue

            dir_name = DIR_NAMES[d]

            # Door check: need matching key to pass
            if new_pos in door_positions:
                door_color = doors[new_pos]
                if door_color not in inv:
                    continue  # Can't pass without key
                # Can pass — unlock action + move
                new_state = (new_pos, inv)
                if new_state not in visited:
                    visited.add(new_state)
                    queue.append(
                        (
                            new_state,
                            path + [new_pos],
                            actions + [f"unlock_{door_color}", dir_name],
                        )
                    )
            else:
                new_state = (new_pos, inv)
                if new_state not in visited:
                    visited.add(new_state)
                    queue.append(
                        (new_state, path + [new_pos], actions + [dir_name])
                    )

        # Check if we reached the goal
        if pos == end:
            return path, actions

    return None  # No valid path


# ---------------------------------------------------------------------------
# Scenario generation
# ---------------------------------------------------------------------------


def generate_scenario(rng: random.Random) -> Optional[KeyLockScenario]:
    """
    Generate a valid key-lock scenario.
    Places 1 key-door pair (guaranteed) and optionally a 2nd pair.
    Returns None if layout is unsolvable.
    """
    all_cells = [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)]
    rng.shuffle(all_cells)

    # Need: start, end, 1-2 keys, 1-2 doors, 2 obstacles = 8-10 cells
    if len(all_cells) < 10:
        return None

    start = all_cells[0]
    end = all_cells[1]

    # Place 1 or 2 key-door pairs
    num_pairs = rng.choice([1, 2])
    keys: Dict[Coord, str] = {}
    doors: Dict[Coord, str] = {}

    idx = 2
    for i in range(num_pairs):
        color = COLORS[i]
        keys[all_cells[idx]] = color
        idx += 1
        doors[all_cells[idx]] = color
        idx += 1

    obstacles: Set[Coord] = set()
    for j in range(NUM_OBSTACLES):
        obstacles.add(all_cells[idx])
        idx += 1

    # Verify door is actually in the way (between start and goal)
    # by checking that removing the door makes the path shorter
    result = bfs_with_keys(start, end, obstacles, keys, doors)
    if result is None:
        return None

    path, actions = result

    # Verify the puzzle actually requires keys (not bypassable)
    result_no_keys = bfs_with_keys(start, end, obstacles, {}, {})
    if result_no_keys is not None:
        no_key_path, _ = result_no_keys
        if len(no_key_path) <= len(path):
            # Door isn't truly blocking — puzzle is trivially solvable
            # Only filter if the path completely avoids the door
            path_set = set(no_key_path)
            if not any(d in path_set for d in doors):
                return None  # Door can be entirely bypassed

    return KeyLockScenario(
        grid_size=GRID_SIZE,
        start=start,
        end=end,
        obstacles=obstacles,
        keys=keys,
        doors=doors,
        solution_actions=actions,
        solution_path=path,
    )


# ---------------------------------------------------------------------------
# Physics-engine playback validator
# ---------------------------------------------------------------------------


@dataclass
class KeyLockSimResult:
    """Result of simulating an action sequence on the grid."""

    reached_goal: bool
    hit_wall: bool
    out_of_bounds: bool
    locked_door_blocked: bool
    invalid_pickup: bool
    invalid_unlock: bool
    final_position: Coord
    inventory: FrozenSet[str]


def simulate_actions(
    start: Coord,
    end: Coord,
    obstacles: Set[Coord],
    keys: Dict[Coord, str],
    doors: Dict[Coord, str],
    actions: List[str],
    grid_size: int = GRID_SIZE,
) -> KeyLockSimResult:
    """
    Physics-engine playback: simulate the action sequence step-by-step,
    tracking position AND inventory state.
    """
    pos = start
    inv: Set[str] = set()
    hit_wall = False
    out_of_bounds = False
    locked_door_blocked = False
    invalid_pickup = False
    invalid_unlock = False

    for action in actions:
        if action.startswith("pick_up_"):
            color = action[len("pick_up_"):]
            if pos in keys and keys[pos] == color and color not in inv:
                inv.add(color)
            else:
                invalid_pickup = True
                break

        elif action.startswith("unlock_"):
            color = action[len("unlock_"):]
            if color not in inv:
                invalid_unlock = True
                break
            # Unlocking doesn't move — just validates key ownership

        elif action in DIR_VECTORS:
            d = DIR_VECTORS[action]
            nr, nc = pos[0] + d[0], pos[1] + d[1]

            if not (0 <= nr < grid_size and 0 <= nc < grid_size):
                out_of_bounds = True
                break

            new_pos = (nr, nc)
            if new_pos in obstacles:
                hit_wall = True
                break

            if new_pos in doors and doors[new_pos] not in inv:
                locked_door_blocked = True
                break

            pos = new_pos

    return KeyLockSimResult(
        reached_goal=(pos == end),
        hit_wall=hit_wall,
        out_of_bounds=out_of_bounds,
        locked_door_blocked=locked_door_blocked,
        invalid_pickup=invalid_pickup,
        invalid_unlock=invalid_unlock,
        final_position=pos,
        inventory=frozenset(inv),
    )


def is_action_seq_invalid(
    start: Coord,
    end: Coord,
    obstacles: Set[Coord],
    keys: Dict[Coord, str],
    doors: Dict[Coord, str],
    actions: List[str],
    grid_size: int = GRID_SIZE,
) -> bool:
    """
    Returns True if the action sequence is physically INVALID (good distractor).
    Returns False if it's a valid alternate solution (must be REJECTED).
    """
    result = simulate_actions(start, end, obstacles, keys, doors, actions, grid_size)

    if result.hit_wall or result.out_of_bounds:
        return True
    if result.locked_door_blocked:
        return True
    if result.invalid_pickup or result.invalid_unlock:
        return True
    if not result.reached_goal:
        return True

    # Valid alternate path — REJECT as distractor
    return False


# ---------------------------------------------------------------------------
# Natural-language prompt rendering
# ---------------------------------------------------------------------------


def coord_label(c: Coord) -> str:
    """Human-friendly label: row 0-4 → A-E, col 0-4 → 1-5."""
    return f"{chr(65 + c[0])}{c[1] + 1}"


def render_grid_ascii(scenario: KeyLockScenario) -> str:
    """Render the grid with keys, doors, obstacles, start, and goal."""
    header = "  " + " ".join(str(c + 1) for c in range(scenario.grid_size))
    lines = [header]

    for r in range(scenario.grid_size):
        row_label = chr(65 + r)
        cells = []
        for c in range(scenario.grid_size):
            pos = (r, c)
            if pos == scenario.start:
                cells.append("S")
            elif pos == scenario.end:
                cells.append("G")
            elif pos in scenario.obstacles:
                cells.append("#")
            elif pos in scenario.keys:
                color = scenario.keys[pos]
                cells.append(COLOR_EMOJI[color])
            elif pos in scenario.doors:
                color = scenario.doors[pos]
                cells.append(DOOR_EMOJI[color])
            else:
                cells.append(".")
        lines.append(f"{row_label} {' '.join(cells)}")

    return "\n".join(lines)


def format_actions(actions: List[str]) -> str:
    """Format action list as a human-readable string."""
    return ", ".join(actions)


def render_prompt(scenario: KeyLockScenario) -> str:
    """Build the natural-language evaluation prompt."""
    grid = render_grid_ascii(scenario)

    key_desc_parts = []
    for pos, color in scenario.keys.items():
        key_desc_parts.append(f"{COLOR_EMOJI[color]} {color} key at {coord_label(pos)}")

    door_desc_parts = []
    for pos, color in scenario.doors.items():
        door_desc_parts.append(
            f"{DOOR_EMOJI[color]} {color}-locked door at {coord_label(pos)}"
        )

    key_desc = "; ".join(key_desc_parts)
    door_desc = "; ".join(door_desc_parts)
    obs_str = ", ".join(coord_label(o) for o in sorted(scenario.obstacles))

    return (
        f"You are navigating a {scenario.grid_size}×{scenario.grid_size} grid. "
        f"Rows are labeled A–E (top to bottom), columns 1–5 (left to right). "
        f"You can move one step at a time: up, down, left, or right. "
        f"You CANNOT move diagonally, move outside the grid boundaries, or pass through obstacle cells (#).\n\n"
        f"KEYS AND DOORS: You must pick up a key before you can unlock a door of the same color. "
        f"To pick up a key, move to its cell and use 'pick_up_<color>'. "
        f"To pass through a locked door, you must first have the matching key, "
        f"then use 'unlock_<color>' followed by a move into the door's cell.\n\n"
        f"Grid map:\n{grid}\n\n"
        f"Start: {coord_label(scenario.start)}  |  "
        f"Goal: {coord_label(scenario.end)}\n"
        f"Keys: {key_desc}\n"
        f"Doors: {door_desc}\n"
        f"Obstacles (impassable): {obs_str}\n\n"
        f"What is a valid action sequence from {coord_label(scenario.start)} to "
        f"{coord_label(scenario.end)}? Give your answer as a comma-separated list "
        f"of actions (up/down/left/right/pick_up_<color>/unlock_<color>)."
    )


# ---------------------------------------------------------------------------
# Distractor generation (with physics-engine validation)
# ---------------------------------------------------------------------------


def generate_distractors(
    scenario: KeyLockScenario, rng: random.Random, num_distractors: int = 3
) -> List[str]:
    """
    Generate plausible but WRONG action sequences.
    Each candidate is validated through the physics engine.

    Strategies:
      1. Skip key pickup (go straight to door)
      2. Use wrong color key
      3. Random walk with some actions
      4. Mutate one action in the correct sequence
    """
    correct = scenario.solution_actions
    if not correct:
        return []

    correct_str = ", ".join(correct)
    used: Set[str] = {correct_str}
    distractors: List[str] = []

    def _try_add(candidate_actions: List[str]) -> bool:
        s = ", ".join(candidate_actions)
        if s in used:
            return False
        if not is_action_seq_invalid(
            scenario.start,
            scenario.end,
            scenario.obstacles,
            scenario.keys,
            scenario.doors,
            candidate_actions,
        ):
            return False  # Alternate valid path — discard
        distractors.append(s)
        used.add(s)
        return True

    MAX_ATTEMPTS = 100

    # Strategy 1: Remove all pick_up actions (skip keys)
    no_pickup = [a for a in correct if not a.startswith("pick_up_")]
    _try_add(no_pickup)

    # Strategy 2: Remove unlock actions (walk into locked doors)
    no_unlock = [a for a in correct if not a.startswith("unlock_")]
    _try_add(no_unlock)

    # Strategy 3: Swap key colors
    if len(scenario.keys) > 0:
        swapped = []
        for a in correct:
            if a.startswith("pick_up_"):
                color = a[len("pick_up_"):]
                other = "blue" if color == "red" else "red"
                swapped.append(f"pick_up_{other}")
            elif a.startswith("unlock_"):
                color = a[len("unlock_"):]
                other = "blue" if color == "red" else "red"
                swapped.append(f"unlock_{other}")
            else:
                swapped.append(a)
        _try_add(swapped)

    # Strategy 4: Mutate one movement action
    for _ in range(MAX_ATTEMPTS):
        if len(distractors) >= num_distractors:
            break
        mutated = list(correct)
        move_indices = [i for i, a in enumerate(mutated) if a in DIR_VECTORS]
        if move_indices:
            idx = rng.choice(move_indices)
            directions = ["up", "down", "left", "right"]
            directions.remove(mutated[idx])
            mutated[idx] = rng.choice(directions)
            _try_add(mutated)

    # Strategy 5: Random walk with key actions sprinkled in
    for _ in range(MAX_ATTEMPTS):
        if len(distractors) >= num_distractors:
            break
        length = max(3, len(correct) - 1 + rng.randint(-2, 2))
        moves = ["up", "down", "left", "right"]
        random_actions: List[str] = []
        for _ in range(length):
            if rng.random() < 0.15 and scenario.keys:
                color = rng.choice(list(scenario.keys.values()))
                random_actions.append(f"pick_up_{color}")
            elif rng.random() < 0.1 and scenario.doors:
                color = rng.choice(list(scenario.doors.values()))
                random_actions.append(f"unlock_{color}")
            else:
                random_actions.append(rng.choice(moves))
        _try_add(random_actions)

    return distractors[:num_distractors]


# ---------------------------------------------------------------------------
# EleutherAI lm-evaluation-harness JSONL assembly
# ---------------------------------------------------------------------------


def scenario_to_eval_doc(
    scenario: KeyLockScenario, rng: random.Random, doc_id: int
) -> Optional[dict]:
    """
    Assemble a single evaluation document for EleutherAI lm-evaluation-harness.
    """
    distractors = generate_distractors(scenario, rng)
    if len(distractors) < 3:
        return None

    correct_str = ", ".join(scenario.solution_actions)
    choices = distractors[:3] + [correct_str]
    gold_idx = 3

    # Shuffle choices
    order = list(range(4))
    rng.shuffle(order)
    shuffled_choices = [choices[i] for i in order]
    shuffled_gold = order.index(gold_idx)

    prompt = render_prompt(scenario)

    return {
        "doc_id": doc_id,
        "query": prompt,
        "choices": shuffled_choices,
        "gold": shuffled_gold,
    }


# ---------------------------------------------------------------------------
# Main driver
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Key-Lock Puzzle evaluation data for Tractatus-Eval."
    )
    parser.add_argument(
        "-n",
        "--num-samples",
        type=int,
        default=1000,
        help="Number of evaluation samples to generate (default: 1000).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="data/keylock_state_dependency.jsonl",
        help="Output JSONL file path.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42).",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    docs: List[dict] = []
    fingerprints: Set[str] = set()
    attempts = 0

    print(f"Generating {args.num_samples} key-lock puzzle samples (seed={args.seed})...")

    while len(docs) < args.num_samples:
        attempts += 1
        scenario = generate_scenario(rng)
        if scenario is None:
            continue

        # Deduplication via SHA-256 fingerprint
        fp_data = (
            f"{scenario.start}{scenario.end}"
            f"{sorted(scenario.obstacles)}"
            f"{sorted(scenario.keys.items())}"
            f"{sorted(scenario.doors.items())}"
        )
        fp = hashlib.sha256(fp_data.encode()).hexdigest()
        if fp in fingerprints:
            continue
        fingerprints.add(fp)

        doc = scenario_to_eval_doc(scenario, rng, len(docs))
        if doc is None:
            continue

        docs.append(doc)

        if len(docs) % 100 == 0:
            print(f"  [{len(docs):>5}/{args.num_samples}] generated ({attempts} attempts)")

    # Write JSONL
    with open(output_path, "w") as f:
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"\n✅ Generated {len(docs)} samples in {attempts} attempts")
    print(f"   Output: {output_path}")
    print(f"   Efficiency: {len(docs)/attempts*100:.1f}%")


if __name__ == "__main__":
    main()
