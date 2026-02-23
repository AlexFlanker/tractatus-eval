import json
import random
import argparse
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

NUM_SAMPLES = 1000
BLOCK_NAMES = ["A", "B", "C", "D", "E"]
MIN_WIDTH = 1
MAX_WIDTH = 9

@dataclass
class Block:
    name: str
    width: int

@dataclass
class StackingScenario:
    blocks: List[Block]
    stable_stack: List[str]  # order from bottom to top

def is_stable(stack: List[Block]) -> bool:
    """
    Check if a tower is structurally stable.
    A stack is stable if every block (except the bottom one) rests on a block
    that is equally wide or wider.
    """
    for i in range(1, len(stack)):
        bottom_block = stack[i-1]
        top_block = stack[i]
        if top_block.width > bottom_block.width:
            return False
    return True

def generate_scenario(rng: random.Random, num_blocks: int) -> Optional[StackingScenario]:
    """Generate a single stacking scenario."""
    # Ensure we generate distinct widths so there is exactly one strictly stable order
    # (or if some widths are equal, multiple but we just need one valid canonical order)
    widths = rng.sample(range(MIN_WIDTH, MAX_WIDTH + 1), num_blocks)
    
    blocks = [Block(name=BLOCK_NAMES[i], width=widths[i]) for i in range(num_blocks)]
    
    # The only strictly stable stack is sorted by width descending (widest at bottom)
    stable_blocks = sorted(blocks, key=lambda b: b.width, reverse=True)
    stable_stack_names = [b.name for b in stable_blocks]
    
    return StackingScenario(
        blocks=blocks,
        stable_stack=stable_stack_names
    )

def generate_distractors(scenario: StackingScenario, rng: random.Random, num_distractors: int = 3) -> List[List[str]]:
    """
    Generate plausible but WRONG stacking orders.
    validated by ensuring is_stable() returns False.
    """
    correct_names = scenario.stable_stack
    correct_tuple = tuple(correct_names)
    
    blocks_by_name = {b.name: b for b in scenario.blocks}
    
    used_tuples = {correct_tuple}
    distractor_list = []
    
    # Max attempts to find invalid permutations
    for _ in range(100):
        if len(distractor_list) >= num_distractors:
            break
            
        candidate_names = list(correct_names)
        rng.shuffle(candidate_names)
        candidate_tuple = tuple(candidate_names)
        
        if candidate_tuple in used_tuples:
            continue
            
        candidate_blocks = [blocks_by_name[name] for name in candidate_names]
        
        if not is_stable(candidate_blocks):
            distractor_list.append(candidate_names)
            used_tuples.add(candidate_tuple)
            
    return distractor_list

def render_prompt(scenario: StackingScenario) -> str:
    """Build the natural-language evaluation prompt."""
    block_descriptions = ", ".join([f"{b.name}={b.width}" for b in scenario.blocks])
    
    return (
        f"You have {len(scenario.blocks)} blocks with different widths: {block_descriptions}.\n"
        f"You must stack all {len(scenario.blocks)} blocks in a single vertical tower on a flat table.\n"
        f"For the tower to be structurally stable, a block can only rest on a block that is EQUALLY WIDE OR WIDER.\n"
        f"If a wider block is placed on top of a narrower block, the tower will collapse due to gravity.\n\n"
        f"Which stacking order (from bottom to top) creates a stable tower? Give your answer as a "
        f"comma-separated list of block letters."
    )

def format_choice(stack_names: List[str]) -> str:
    return ", ".join(stack_names)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/object_stacking.jsonl", help="Output file")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--num_blocks", type=int, default=4, help="Number of blocks per puzzle")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    
    print(f"Generating {NUM_SAMPLES} samples for Object Stacking (Gravity & Support)...")
    valid_count = 0
    
    with open(args.output, "w") as f:
        while valid_count < NUM_SAMPLES:
            scenario = generate_scenario(rng, args.num_blocks)
            if not scenario:
                continue
                
            distractors = generate_distractors(scenario, rng)
            if len(distractors) < 3:
                continue # not enough invalid permutations (rare)
                
            prompt = render_prompt(scenario)
            choices_lists = [scenario.stable_stack] + distractors
            
            # format and shuffle
            choices_strs = [format_choice(c) for c in choices_lists]
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
