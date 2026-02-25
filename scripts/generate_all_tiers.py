#!/usr/bin/env python3
"""
Batch generator — produces all 18 difficulty-tiered JSONL datasets.
Usage: python3 scripts/generate_all_tiers.py
"""
import subprocess
import sys
import os

TASKS = [
    {
        "name": "spatial",
        "script": "scripts/generate_spatial_eval.py",
        "output_template": "data/spatial_{difficulty}.jsonl",
        "extra_args": {
            "easy":   ["--grid-size", "4", "--num-obstacles", "2", "--num-samples", "500"],
            "medium": ["--grid-size", "5", "--num-obstacles", "3", "--num-samples", "500"],
            "hard":   ["--grid-size", "7", "--num-obstacles", "5", "--num-samples", "500"],
        },
    },
    {
        "name": "keylock",
        "script": "scripts/generate_keylock_eval.py",
        "output_template": "data/keylock_{difficulty}.jsonl",
        "extra_args": {
            "easy":   ["--grid-size", "4", "--num-obstacles", "1", "--min-pairs", "1", "--max-pairs", "1", "--num-samples", "500"],
            "medium": ["--grid-size", "5", "--num-obstacles", "2", "--min-pairs", "1", "--max-pairs", "2", "--num-samples", "500"],
            "hard":   ["--grid-size", "7", "--num-obstacles", "3", "--min-pairs", "2", "--max-pairs", "3", "--num-samples", "500"],
        },
    },
    {
        "name": "stacking",
        "script": "scripts/generate_stacking_eval.py",
        "output_template": "data/stacking_{difficulty}.jsonl",
        "extra_args": {
            "easy":   ["--num-blocks", "3", "--min-width", "1", "--max-width", "5", "--num-samples", "500"],
            "medium": ["--num-blocks", "4", "--min-width", "1", "--max-width", "7", "--num-samples", "500"],
            "hard":   ["--num-blocks", "6", "--min-width", "1", "--max-width", "12", "--num-samples", "500"],
        },
    },
    {
        "name": "container",
        "script": "scripts/generate_container_eval.py",
        "output_template": "data/container_{difficulty}.jsonl",
        "extra_args": {
            "easy":   ["--min-containers", "2", "--max-containers", "2", "--min-steps", "2", "--max-steps", "3", "--max-capacity", "5", "--num-samples", "500"],
            "medium": ["--min-containers", "2", "--max-containers", "3", "--min-steps", "3", "--max-steps", "5", "--max-capacity", "10", "--num-samples", "500"],
            "hard":   ["--min-containers", "3", "--max-containers", "4", "--min-steps", "5", "--max-steps", "7", "--max-capacity", "15", "--num-samples", "500"],
        },
    },
    {
        "name": "collision",
        "script": "scripts/generate_collision_eval.py",
        "output_template": "data/collision_{difficulty}.jsonl",
        "extra_args": {
            "easy":   ["--grid-size", "4", "--num-objects", "2", "--max-steps", "3", "--num-samples", "500"],
            "medium": ["--grid-size", "5", "--num-objects", "2", "--max-steps", "5", "--num-samples", "500"],
            "hard":   ["--grid-size", "7", "--num-objects", "3", "--max-steps", "8", "--num-samples", "500"],
        },
    },
    {
        "name": "circuit",
        "script": "scripts/generate_circuit_eval.py",
        "output_template": "data/circuit_{difficulty}.jsonl",
        "extra_args": {
            "easy":   ["--grid-size", "4", "--min-switches", "1", "--max-switches", "1", "--break-chance", "0.0", "--num-samples", "500"],
            "medium": ["--grid-size", "5", "--min-switches", "1", "--max-switches", "3", "--break-chance", "0.2", "--num-samples", "500"],
            "hard":   ["--grid-size", "7", "--min-switches", "2", "--max-switches", "4", "--break-chance", "0.3", "--num-samples", "500"],
        },
    },
]

def main():
    total = len(TASKS) * 3
    done = 0
    for task in TASKS:
        for difficulty in ["easy", "medium", "hard"]:
            output = task["output_template"].format(difficulty=difficulty)
            args = task["extra_args"][difficulty]
            cmd = [sys.executable, task["script"], "--output", output, "--seed", "42"] + args
            done += 1
            print(f"\n[{done}/{total}] Generating {output}...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  ERROR: {result.stderr}")
            else:
                print(f"  OK — {result.stdout.strip().split(chr(10))[-1]}")

    print(f"\nAll {total} datasets generated!")

if __name__ == "__main__":
    main()
