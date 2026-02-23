import json
import random
import argparse
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

NUM_SAMPLES = 1000
GRID_SIZE = 5
MAX_STEPS = 5

ROWS = "ABCDE"
COLS = "12345"

def coord_label(r: int, c: int) -> str:
    return f"{ROWS[r]}{COLS[c]}"

DIRS = {
    "UP": (-1, 0),
    "DOWN": (1, 0),
    "LEFT": (0, -1),
    "RIGHT": (0, 1)
}

@dataclass
class MovingObject:
    name: str
    r: int
    c: int
    direction: str

@dataclass
class CollisionResult:
    collided: bool
    step: int
    r: int
    c: int

@dataclass
class Scenario:
    obj_x: MovingObject
    obj_y: MovingObject
    result: CollisionResult

def step_object(obj: MovingObject) -> Tuple[int, int]:
    dr, dc = DIRS[obj.direction]
    new_r = obj.r + dr
    new_c = obj.c + dc
    
    # Stop at boundaries
    if new_r < 0: new_r = 0
    if new_r >= GRID_SIZE: new_r = GRID_SIZE - 1
    if new_c < 0: new_c = 0
    if new_c >= GRID_SIZE: new_c = GRID_SIZE - 1
    
    return new_r, new_c

def simulate(x: MovingObject, y: MovingObject) -> CollisionResult:
    curr_x = MovingObject(x.name, x.r, x.c, x.direction)
    curr_y = MovingObject(y.name, y.r, y.c, y.direction)
    
    for step in range(1, MAX_STEPS + 1):
        curr_x.r, curr_x.c = step_object(curr_x)
        curr_y.r, curr_y.c = step_object(curr_y)
        
        if curr_x.r == curr_y.r and curr_x.c == curr_y.c:
            return CollisionResult(collided=True, step=step, r=curr_x.r, c=curr_x.c)
            
    return CollisionResult(collided=False, step=0, r=0, c=0)

def generate_scenario(rng: random.Random) -> Scenario:
    # Random starting positions
    xr = rng.randint(0, GRID_SIZE - 1)
    xc = rng.randint(0, GRID_SIZE - 1)
    
    yr = rng.randint(0, GRID_SIZE - 1)
    yc = rng.randint(0, GRID_SIZE - 1)
    while xr == yr and xc == yc: # don't start on same cell
        yr = rng.randint(0, GRID_SIZE - 1)
        yc = rng.randint(0, GRID_SIZE - 1)
        
    x_dir = rng.choice(list(DIRS.keys()))
    y_dir = rng.choice(list(DIRS.keys()))
    
    x = MovingObject("X", xr, xc, x_dir)
    y = MovingObject("Y", yr, yc, y_dir)
    
    result = simulate(x, y)
    return Scenario(obj_x=x, obj_y=y, result=result)

def format_result(res: CollisionResult) -> str:
    if not res.collided:
        return "No, they never collide"
    return f"Yes, at {coord_label(res.r, res.c)} on step {res.step}"

def generate_distractors(scenario: Scenario, rng: random.Random) -> List[str]:
    distractors = []
    correct_str = format_result(scenario.result)
    used = {correct_str}
    
    # Always include "No collision" if it collided, or a fake collision if it didn't
    if scenario.result.collided:
        no_coll = "No, they never collide"
        if no_coll not in used:
            distractors.append(no_coll)
            used.add(no_coll)
            
        # Off by 1 step
        fake_res = CollisionResult(True, scenario.result.step + 1, scenario.result.r, scenario.result.c)
        if fake_res.step <= MAX_STEPS:
            s = format_result(fake_res)
            if s not in used:
                distractors.append(s)
                used.add(s)
                
        # Wrong cell
        dr = rng.choice([-1, 1, 0])
        dc = rng.choice([-1, 1, 0])
        nr, nc = scenario.result.r + dr, scenario.result.c + dc
        if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE and (dr != 0 or dc != 0):
            fake_res = CollisionResult(True, scenario.result.step, nr, nc)
            s = format_result(fake_res)
            if s not in used:
                distractors.append(s)
                used.add(s)
    else:
        # Fake collisions
        for _ in range(10):
            step = rng.randint(1, MAX_STEPS)
            r = rng.randint(0, GRID_SIZE - 1)
            c = rng.randint(0, GRID_SIZE - 1)
            fake_res = CollisionResult(True, step, r, c)
            s = format_result(fake_res)
            if s not in used:
                distractors.append(s)
                used.add(s)
            if len(distractors) >= 3:
                break
                
    # Fill remaining
    for _ in range(20):
        if len(distractors) >= 3:
            break
        step = rng.randint(1, MAX_STEPS)
        r = rng.randint(0, GRID_SIZE - 1)
        c = rng.randint(0, GRID_SIZE - 1)
        fake_res = CollisionResult(True, step, r, c)
        s = format_result(fake_res)
        if s not in used:
            distractors.append(s)
            used.add(s)
                
    return distractors[:3]

def render_prompt(scenario: Scenario) -> str:
    return (
        f"Grid: 5x5. Rows are A-E (top to bottom), columns are 1-5 (left to right).\n"
        f"Time horizon: {MAX_STEPS} steps. Objects move at a speed of 1 cell per step.\n"
        f"If an object hits the boundary of the grid, it stops and stays there for the remaining steps.\n\n"
        f"Object {scenario.obj_x.name} starts at {coord_label(scenario.obj_x.r, scenario.obj_x.c)}, moves {scenario.obj_x.direction}.\n"
        f"Object {scenario.obj_y.name} starts at {coord_label(scenario.obj_y.r, scenario.obj_y.c)}, moves {scenario.obj_y.direction}.\n\n"
        f"Do the objects collide? If so, where and when?"
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/collision_prediction.jsonl", help="Output file")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    
    print(f"Generating {NUM_SAMPLES} samples for Collision Prediction...")
    
    # To assure a good balance, let's force a 50/50 split of collisions and non-collisions
    target_collisions = NUM_SAMPLES // 2
    target_non_collisions = NUM_SAMPLES - target_collisions
    
    count_collisions = 0
    count_non_collisions = 0
    valid_count = 0
    
    with open(args.output, "w") as f:
        while valid_count < NUM_SAMPLES:
            scenario = generate_scenario(rng)
            
            if scenario.result.collided and count_collisions >= target_collisions:
                continue
            if not scenario.result.collided and count_non_collisions >= target_non_collisions:
                continue
                
            distractors = generate_distractors(scenario, rng)
            if len(distractors) < 3:
                continue
                
            prompt = render_prompt(scenario)
            choices_lists = [format_result(scenario.result)] + distractors
            
            choices_shuffled = list(choices_lists)
            rng.shuffle(choices_shuffled)
            
            gold_idx = choices_shuffled.index(choices_lists[0])
            
            sample = {
                "query": prompt,
                "choices": choices_shuffled,
                "gold": gold_idx
            }
            
            f.write(json.dumps(sample) + "\n")
            
            if scenario.result.collided:
                count_collisions += 1
            else:
                count_non_collisions += 1
                
            valid_count += 1
            
            if valid_count % 100 == 0:
                print(f"  Generated {valid_count} / {NUM_SAMPLES}")
                
    print(f"Generated {valid_count} samples. Done.")

if __name__ == "__main__":
    main()
