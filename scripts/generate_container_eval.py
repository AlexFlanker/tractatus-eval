import json
import random
import argparse
from typing import List, Dict, Optional
from dataclasses import dataclass
import copy

NUM_SAMPLES = 1000

@dataclass
class Container:
    name: str
    capacity: int
    current: int

@dataclass
class Scenario:
    containers: Dict[str, Container]
    actions: List[str]
    final_state: Dict[str, int]

def simulate_step(containers: Dict[str, Container], action: str):
    """Mutates containers in place according to the action."""
    parts = action.split()
    if parts[0] == "Pour" and parts[2] == "into":
        src = parts[1]
        dst = parts[3]
        
        src_c = containers[src]
        dst_c = containers[dst]
        
        amount_to_pour = min(src_c.current, dst_c.capacity - dst_c.current)
        src_c.current -= amount_to_pour
        dst_c.current += amount_to_pour
        
    elif parts[0] == "Fill":
        tgt = parts[1]
        containers[tgt].current = containers[tgt].capacity
        
    elif parts[0] == "Empty":
        tgt = parts[1]
        containers[tgt].current = 0
        
def generate_scenario(rng: random.Random) -> Scenario:
    num_containers = rng.choice([2, 3])
    names = ["A", "B", "C"][:num_containers]
    
    # Random capacities between 2 and 10
    containers = {}
    for name in names:
        cap = rng.randint(2, 10)
        # start randomly between 0 and cap
        start = rng.randint(0, cap)
        containers[name] = Container(name=name, capacity=cap, current=start)
        
    initial_containers = copy.deepcopy(containers)
    
    num_actions = rng.randint(3, 5)
    actions = []
    
    for _ in range(num_actions):
        action_type = rng.choice(["Pour", "Fill", "Empty"])
        if action_type == "Pour" and num_containers >= 2:
            src, dst = rng.sample(names, 2)
            actions.append(f"Pour {src} into {dst}")
            simulate_step(containers, actions[-1])
        else:
            tgt = rng.choice(names)
            actions.append(f"{action_type} {tgt}")
            simulate_step(containers, actions[-1])
            
    final_state = {k: v.current for k, v in containers.items()}
    return Scenario(containers=initial_containers, actions=actions, final_state=final_state)

def dict_to_str(state: Dict[str, int]) -> str:
    parts = []
    for k in sorted(state.keys()):
        parts.append(f"{k}={state[k]}L")
    return ", ".join(parts)

def generate_distractors(scenario: Scenario, rng: random.Random) -> List[Dict[str, int]]:
    distractors = []
    names = list(scenario.containers.keys())
    
    correct_str = dict_to_str(scenario.final_state)
    used = {correct_str}
    
    # Strategy 1: Add volumes without cappping capacity (just naive math error)
    state1 = {k: scenario.containers[k].current for k in names}
    for action in scenario.actions:
        parts = action.split()
        if parts[0] == "Pour":
            src, dst = parts[1], parts[3]
            # pour everything, overflow allowed
            amount = state1[src]
            state1[src] -= amount
            state1[dst] += amount
        elif parts[0] == "Fill":
            state1[parts[1]] = scenario.containers[parts[1]].capacity
        elif parts[0] == "Empty":
            state1[parts[1]] = 0
            
    s1_str = dict_to_str(state1)
    if s1_str not in used:
        distractors.append(state1)
        used.add(s1_str)
        
    # Strategy 2: Randomly swapped values of the correct state
    shuffled_vals = list(scenario.final_state.values())
    rng.shuffle(shuffled_vals)
    state2 = {names[i]: shuffled_vals[i] for i in range(len(names))}
    s2_str = dict_to_str(state2)
    if s2_str not in used:
        distractors.append(state2)
        used.add(s2_str)
        
    # Strategy 3: Just randomize up to capacities
    for _ in range(20):
        if len(distractors) >= 3:
            break
        state3 = {k: rng.randint(0, scenario.containers[k].capacity) for k in names}
        s3_str = dict_to_str(state3)
        if s3_str not in used:
            distractors.append(state3)
            used.add(s3_str)
            
    return distractors[:3]

def render_prompt(scenario: Scenario) -> str:
    parts = []
    for k, v in scenario.containers.items():
        parts.append(f"Container {k} (capacity {v.capacity}L, currently {v.current}L)")
    init_desc = ", ".join(parts) + "."
    
    steps = []
    for i, a in enumerate(scenario.actions, 1):
        steps.append(f"Step {i}: {a}.")
        
    steps_str = "\n".join(steps)
    
    return (
        f"{init_desc}\n\n"
        f"{steps_str}\n\n"
        f"What is the final state of all containers? Give your answer as a comma-separated list of volumes."
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/container_filling.jsonl", help="Output file")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    
    print(f"Generating {NUM_SAMPLES} samples for Container Filling...")
    valid_count = 0
    
    with open(args.output, "w") as f:
        while valid_count < NUM_SAMPLES:
            scenario = generate_scenario(rng)
            distractors = generate_distractors(scenario, rng)
            
            if len(distractors) < 3:
                continue
                
            prompt = render_prompt(scenario)
            choices_dicts = [scenario.final_state] + distractors
            
            choices_strs = [dict_to_str(c) for c in choices_dicts]
            choices_shuffled = list(choices_strs)
            rng.shuffle(choices_shuffled)
            
            gold_idx = choices_shuffled.index(choices_strs[0])
            
            sample = {
                "query": prompt,
                "choices": choices_shuffled,
                "gold": gold_idx
            }
            
            f.write(json.dumps(sample) + "\n")
            valid_count += 1
            
            if valid_count % 100 == 0:
                print(f"  Generated {valid_count} / {NUM_SAMPLES}")
                
    print(f"Generated {valid_count} samples. Done.")

if __name__ == "__main__":
    main()
