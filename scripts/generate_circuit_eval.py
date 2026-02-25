import json
import random
import argparse
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass

NUM_SAMPLES = 1000
GRID_SIZE = 5
_min_switches = 1
_max_switches = 3
_break_chance = 0.2

@dataclass
class CircuitScenario:
    grid: List[List[str]]
    switches: Dict[str, Tuple[int, int]]
    switch_states: Dict[str, str] # "CLOSED" or "OPEN"
    bulb_pos: Tuple[int, int]
    lights_up: bool

def find_path(start: Tuple[int, int], end: Tuple[int, int], avoid: Set[Tuple[int, int]], rng: random.Random) -> Optional[List[Tuple[int, int]]]:
    # Simple BFS to find a path
    queue = [[start]]
    visited = {start}
    
    # Shuffle directions for randomness
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    
    while queue:
        # random pop to introduce more variation, or just standard BFS
        # To get more winding paths, we can use a randomized DFS, but BFS is safer for guaranteed paths
        
        # Actually BFS gives shortest paths. Let's use randomized DFS for winding wires
        path = queue.pop(0)
        curr = path[-1]
        
        if curr == end:
            return path
            
        rng.shuffle(dirs)
        for dr, dc in dirs:
            nr, nc = curr[0] + dr, curr[1] + dc
            if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                nxt = (nr, nc)
                if nxt not in visited and nxt not in avoid:
                    visited.add(nxt)
                    queue.append(path + [nxt])
                    
    return None

def find_random_path(start: Tuple[int, int], end: Tuple[int, int], avoid: Set[Tuple[int, int]], rng: random.Random) -> Optional[List[Tuple[int, int]]]:
    # Randomized DFS for winding wires
    stack = [[start]]
    visited = {start}
    
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    
    while stack:
        path = stack.pop()
        curr = path[-1]
        
        if curr == end:
            return path
            
        rng.shuffle(dirs)
        for dr, dc in dirs:
            nr, nc = curr[0] + dr, curr[1] + dc
            if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                nxt = (nr, nc)
                if nxt not in visited and nxt not in avoid:
                    visited.add(nxt)
                    stack.append(path + [nxt])
    
    # fallback to BFS
    return find_path(start, end, avoid, rng)

def generate_scenario(rng: random.Random) -> Optional[CircuitScenario]:
    plus = (0, 0)
    minus = (GRID_SIZE - 1, 0)
    
    # Random bulb position
    while True:
        br = rng.randint(0, GRID_SIZE - 1)
        bc = rng.randint(1, GRID_SIZE - 1) # keep away from column 0
        bulb = (br, bc)
        if bulb != plus and bulb != minus:
            break
            
    # Path 1: + to Bulb
    avoid_p1 = {minus}
    path1 = find_random_path(plus, bulb, avoid_p1, rng)
    if not path1: return None
    
    # Path 2: Bulb to -
    avoid_p2 = set(path1) - {bulb}
    path2 = find_random_path(bulb, minus, avoid_p2, rng)
    if not path2: return None
    
    full_path = path1 + path2[1:]
    
    # Place 1 to 3 switches on the wire
    num_switches = rng.randint(_min_switches, _max_switches)
    wire_cells = [p for p in full_path if p not in (plus, minus, bulb)]
    if len(wire_cells) < num_switches:
        return None
        
    switch_positions = rng.sample(wire_cells, num_switches)
    switches = {}
    switch_states = {}
    
    for i, pos in enumerate(switch_positions):
        s_name = f"S{i+1}"
        switches[s_name] = pos
        switch_states[s_name] = rng.choice(["CLOSED", "OPEN"])
        
    grid = [["." for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    for p in full_path:
        grid[p[0]][p[1]] = "W"
        
    grid[plus[0]][plus[1]] = "+"
    grid[minus[0]][minus[1]] = "-"
    grid[bulb[0]][bulb[1]] = "B"
    
    for s_name, pos in switches.items():
        grid[pos[0]][pos[1]] = s_name[-1] # "1", "2", or "3"
        
        
    # Check if light is on (all switches must be CLOSED)
    lights_up = all(st == "CLOSED" for st in switch_states.values())
    
    # Sometimes generate a broken circuit (gap in wire)
    is_broken = rng.random() < _break_chance
    broken_pos = None
    if is_broken:
        candidates = [p for p in full_path if p not in (plus, minus, bulb) and p not in switches.values()]
        if candidates:
            broken_pos = rng.choice(candidates)
            grid[broken_pos[0]][broken_pos[1]] = "."
            lights_up = False
            
    return CircuitScenario(
        grid=grid,
        switches=switches,
        switch_states=switch_states,
        bulb_pos=bulb,
        lights_up=lights_up
    )

def format_result(lights_up: bool) -> str:
    if lights_up:
        return "Yes, the bulb lights up"
    return "No, the circuit is broken"

def generate_distractors(scenario: CircuitScenario) -> List[str]:
    # Since it's a binary question, distractors are just the opposite!
    # But wait, EleutherAI needs multiple choices.
    # Let's add extra descriptive distractors.
    
    distractors = []
    
    correct_str = format_result(scenario.lights_up)
    
    options = [
        "Yes, the bulb lights up",
        "No, the circuit is broken",
        "Yes, but only dimly",
        "No, it shorts out"
    ]
    
    for opt in options:
        if opt != correct_str:
            distractors.append(opt)
            
    return distractors[:3]

def coord_label(r: int, c: int) -> str:
    ROWS = "ABCDEFGHIJ"
    return f"{ROWS[r]}{c+1}"

def render_prompt(scenario: CircuitScenario) -> str:
    grid_str = ""
    ROWS = "ABCDEFGHIJ"
    cols_str = " ".join(str(i+1) for i in range(GRID_SIZE))
    grid_str += f"  {cols_str}\n"
    for r in range(GRID_SIZE):
        row_str = " ".join(scenario.grid[r])
        grid_str += f"{ROWS[r]} {row_str}\n"
        
    switch_desc = []
    for s, st in scenario.switch_states.items():
        switch_desc.append(f"Switch {s} is {st}")
    switch_str = ", ".join(switch_desc)
    
    return (
        f"Circuit diagram ({GRID_SIZE}x{GRID_SIZE} grid):\n"
        f"{grid_str}\n"
        f"Legend: [+] Battery Positive, [-] Battery Negative, [B] Bulb, [W] Wire.\n"
        f"Numbers 1, 2, 3 represent switches S1, S2, S3.\n"
        f"A path of W components connects the battery and bulb.\n\n"
        f"State: {switch_str}.\n"
        f"Electricity must flow from [+] to [-] through the bulb, passing only through wires (W) and CLOSED switches. "
        f"It cannot pass through OPEN switches or empty space (.).\n\n"
        f"Does the bulb light up?"
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/circuit_connectivity.jsonl", help="Output file")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--grid-size", type=int, default=5)
    parser.add_argument("--min-switches", type=int, default=1)
    parser.add_argument("--max-switches", type=int, default=3)
    parser.add_argument("--break-chance", type=float, default=0.2)
    parser.add_argument("--num-samples", type=int, default=1000)
    args = parser.parse_args()

    global NUM_SAMPLES, GRID_SIZE, _min_switches, _max_switches, _break_chance
    NUM_SAMPLES = args.num_samples
    GRID_SIZE = args.grid_size
    _min_switches = args.min_switches
    _max_switches = args.max_switches
    _break_chance = args.break_chance

    rng = random.Random(args.seed)
    
    print(f"Generating {NUM_SAMPLES} samples for Circuit Connectivity...")
    
    valid_count = 0
    count_on = 0
    count_off = 0
    
    with open(args.output, "w") as f:
        while valid_count < NUM_SAMPLES:
            scenario = generate_scenario(rng)
            if not scenario:
                continue
                
            # balance dataset
            if scenario.lights_up and count_on > NUM_SAMPLES // 2:
                continue
            if not scenario.lights_up and count_off > NUM_SAMPLES // 2:
                continue
                
            distractors = generate_distractors(scenario)
            
            prompt = render_prompt(scenario)
            choices_lists = [format_result(scenario.lights_up)] + distractors
            
            choices_shuffled = list(choices_lists)
            rng.shuffle(choices_shuffled)
            
            gold_idx = choices_shuffled.index(choices_lists[0])
            
            sample = {
                "query": prompt,
                "choices": choices_shuffled,
                "gold": gold_idx
            }
            
            f.write(json.dumps(sample) + "\n")
            
            if scenario.lights_up: count_on += 1
            else: count_off += 1
            
            valid_count += 1
            
            if valid_count % 100 == 0:
                print(f"  Generated {valid_count} / {NUM_SAMPLES}")
                
    print(f"Generated {valid_count} samples. Done.")

if __name__ == "__main__":
    main()
