#!/usr/bin/env python3
"""
Wrapper to run lm_eval on MPS with 7B+ models by patching
transformers' caching_allocator_warmup (which tries to allocate
a single buffer >= model size, exceeding MPS limits).
"""
import sys
import transformers.modeling_utils as mu

# Monkey-patch: make caching_allocator_warmup a no-op
mu.caching_allocator_warmup = lambda *args, **kwargs: None
print("[patch] Disabled caching_allocator_warmup for MPS compatibility")

# Now import and run lm_eval CLI
from lm_eval.__main__ import cli_evaluate
cli_evaluate()
