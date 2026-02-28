# [New Task] Tractatus-Eval: Physics-Engine Validated Benchmark for Embodied Spatial Reasoning

## Summary

I'd like to contribute **Tractatus-Eval**, a 6-task benchmark for evaluating embodied spatial reasoning in text-only LLMs. The benchmark uses deterministic physics-engine validators to ensure 0% distractor contamination — every wrong answer provably violates physical constraints.

## Benchmark Overview

| Feature | Details |
|---|---|
| **Tasks** | 6 (Spatial Navigation, Key-Lock Puzzles, Object Stacking, Container Filling, Collision Prediction, Circuit Connectivity) |
| **Difficulty Tiers** | 3 per task (Easy / Medium / Hard) |
| **Total Subtasks** | 18 |
| **Samples** | 9,000 (500 per subtask) |
| **Format** | Multiple choice (4 options) |
| **Dataset** | [AlexFlanker26/tractatus-eval](https://huggingface.co/datasets/AlexFlanker26/tractatus-eval) on HuggingFace Hub |
| **Paper** | [arXiv preprint (forthcoming)] |
| **Repo** | [AlexFlanker/tractatus-eval](https://github.com/AlexFlanker/tractatus-eval) |

## Key Findings from Baseline Evaluation

We evaluated 6 models (Pythia-410m through Llama-3-8B):

- **Phi-2 (2.7B) outperforms both 7B+ models** (43.2% vs 38.9-39.0% on non-binary tasks) — training data composition matters more than parameter count
- **Collision & Circuit tasks**: All 6 models score exactly ~50% regardless of scale (410M–8B), providing strong evidence that no model performs genuine physics simulation
- **Counter-intuitive difficulty trends**: Container Filling accuracy *increases* with difficulty (more tokens for pattern matching), while Spatial Navigation stays flat

## What's Ready

- [x] Dataset uploaded to HuggingFace Hub with all 18 configs
- [x] 18 YAML task configs + group YAML (using `include` directives)
- [x] Contribution checklist README
- [x] All configs pass `lm_eval` validation (dataset loading + prompt rendering + answer extraction)
- [x] Baseline results across 6 models × 18 tasks
- [x] Zero-dependency Python generators for all tasks

## Task YAML Structure

```
lm_eval/tasks/tractatus_eval/
├── tractatus_group.yaml
├── spatial_easy.yaml
├── spatial_medium.yaml
├── spatial_hard.yaml
├── keylock_easy.yaml
├── ... (18 task YAMLs total)
└── README.md
```

## Questions for Maintainers

1. Are there any specific formatting or naming conventions I should follow for the task names?
2. Should I include the original (non-tiered) task variants, or only the difficulty-tiered versions?
3. Any preference on how to structure the group YAML for 18 subtasks?

Happy to adjust anything based on your feedback before submitting the PR. Thanks!
