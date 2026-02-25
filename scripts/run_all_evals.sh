#!/bin/bash
# Sequential model evaluation runner for Tractatus-Eval difficulty tiers
# Runs all models one after another on MPS device
# Usage: bash scripts/run_all_evals.sh

set -e

HARNESS_DIR="/Users/tianjiesun/Desktop/LLM_repos/lm-evaluation-harness"
TASKS="tractatus_spatial_easy,tractatus_spatial_medium,tractatus_spatial_hard,tractatus_keylock_easy,tractatus_keylock_medium,tractatus_keylock_hard,tractatus_stacking_easy,tractatus_stacking_medium,tractatus_stacking_hard,tractatus_container_easy,tractatus_container_medium,tractatus_container_hard,tractatus_collision_easy,tractatus_collision_medium,tractatus_collision_hard,tractatus_circuit_easy,tractatus_circuit_medium,tractatus_circuit_hard"

run_eval() {
    local model=$1
    local batch=$2
    local extra=${3:-""}
    echo ""
    echo "================================================================"
    echo "  Running: $model (batch_size=$batch)"
    echo "  Started: $(date)"
    echo "================================================================"
    
    cd "$HARNESS_DIR"
    lm_eval --model hf \
        --model_args "pretrained=$model$extra" \
        --device mps \
        --tasks "$TASKS" \
        --batch_size "$batch" \
        --num_fewshot 0 \
        2>&1 | tee "/tmp/eval_$(echo $model | tr '/' '_').log"
    
    echo ""
    echo "  Finished: $model at $(date)"
    echo "================================================================"
}

echo "Starting sequential evaluation runs..."
echo "Time: $(date)"

# 1. Llama-3.2-1B (1B params)
run_eval "meta-llama/Llama-3.2-1B" 8

# 2. Llama-3.2-3B (3B params) 
run_eval "meta-llama/Llama-3.2-3B" 4

echo ""
echo "All evaluations complete!"
echo "Time: $(date)"
echo "Logs saved to /tmp/eval_*.log"
