"""
Difficulty tier presets for all Tractatus-Eval generators.
Import this module and call get_preset(task_name, difficulty) to get parameters.
"""

PRESETS = {
    "spatial": {
        "easy":   {"grid_size": 4, "num_obstacles": 2, "num_samples": 500},
        "medium": {"grid_size": 5, "num_obstacles": 3, "num_samples": 500},
        "hard":   {"grid_size": 7, "num_obstacles": 5, "num_samples": 500},
    },
    "keylock": {
        "easy":   {"grid_size": 4, "num_obstacles": 1, "min_pairs": 1, "max_pairs": 1, "num_samples": 500},
        "medium": {"grid_size": 5, "num_obstacles": 2, "min_pairs": 1, "max_pairs": 2, "num_samples": 500},
        "hard":   {"grid_size": 7, "num_obstacles": 3, "min_pairs": 2, "max_pairs": 3, "num_samples": 500},
    },
    "stacking": {
        "easy":   {"num_blocks": 3, "min_width": 1, "max_width": 5, "num_samples": 500},
        "medium": {"num_blocks": 4, "min_width": 1, "max_width": 7, "num_samples": 500},
        "hard":   {"num_blocks": 6, "min_width": 1, "max_width": 12, "num_samples": 500},
    },
    "container": {
        "easy":   {"min_containers": 2, "max_containers": 2, "min_steps": 2, "max_steps": 3, "max_capacity": 5, "num_samples": 500},
        "medium": {"min_containers": 2, "max_containers": 3, "min_steps": 3, "max_steps": 5, "max_capacity": 10, "num_samples": 500},
        "hard":   {"min_containers": 3, "max_containers": 4, "min_steps": 5, "max_steps": 7, "max_capacity": 15, "num_samples": 500},
    },
    "collision": {
        "easy":   {"grid_size": 4, "num_objects": 2, "max_steps": 3, "num_samples": 500},
        "medium": {"grid_size": 5, "num_objects": 2, "max_steps": 5, "num_samples": 500},
        "hard":   {"grid_size": 7, "num_objects": 3, "max_steps": 8, "num_samples": 500},
    },
    "circuit": {
        "easy":   {"grid_size": 4, "min_switches": 1, "max_switches": 1, "break_chance": 0.0, "num_samples": 500},
        "medium": {"grid_size": 5, "min_switches": 1, "max_switches": 3, "break_chance": 0.2, "num_samples": 500},
        "hard":   {"grid_size": 7, "min_switches": 2, "max_switches": 4, "break_chance": 0.3, "num_samples": 500},
    },
}

def get_preset(task_name: str, difficulty: str) -> dict:
    return PRESETS[task_name][difficulty]
