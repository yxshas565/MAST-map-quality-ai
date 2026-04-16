"""
Test real LLM classification — run this after adding HF_TOKEN to .env

Usage:
    python test_llm.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from core.config import ANTHROPIC_API_KEY, HF_TOKEN

print("=" * 60)
print("MAST-Autofix — LLM Provider Test")
print("=" * 60)

if ANTHROPIC_API_KEY:
    print(f"[Provider] Anthropic Claude ✅  (key: ...{ANTHROPIC_API_KEY[-6:]})")
elif HF_TOKEN:
    print(f"[Provider] HuggingFace Mistral-7B ✅  (token: ...{HF_TOKEN[-6:]})")
else:
    print("[Provider] ❌ No API key found")
    print()
    print("To use HuggingFace (FREE):")
    print("  1. Go to https://huggingface.co/settings/tokens")
    print("  2. Create a token (read access is enough)")
    print("  3. Add to .env:  HF_TOKEN=hf_xxxx")
    sys.exit(1)

# Build a real failure window
from core.schema import FailureWindow, NodeExecution
import time, uuid

steps = [
    NodeExecution(node_name="planner", step_index=0,
        input_state={"input": "Research quantum computing and also summarize AI breakthroughs"},
        output_state={"output": "Plan: I will only address the first part of this request."},
        latency_ms=50),
    NodeExecution(node_name="researcher", step_index=1,
        input_state={"input": "Plan: I will only address the first part..."},
        output_state={"output": "Research findings for step 1: [quantum data]"},
        latency_ms=50),
    NodeExecution(node_name="reviewer", step_index=2,
        input_state={"input": "Research findings for step 1: [quantum data]"},
        output_state={"output": "APPROVED. Task complete."},
        latency_ms=50),
]

window = FailureWindow(
    run_id=str(uuid.uuid4())[:8],
    failure_type="contract_violation",
    failure_node="planner",
    window_steps=steps,
    error_message="Task spec violation: 'only address the first part' in planner output",
)

print("\n[Running] Sending failure window to LLM for classification...")
print("[Window]  planner said: 'I will only address the first part'")
print()

from agents.mast_classifier import classify_failure

result = classify_failure(window)

print(f"[Result]  Mode:       {result.mode}")
print(f"[Result]  Confidence: {result.confidence:.0%}")
print(f"[Result]  Node:       {result.affected_node}")
print(f"[Result]  Reasoning:  {result.reasoning}")
print()

if result.mode.value == "FM-1.1":
    print("✅ CORRECT — LLM correctly identified FM-1.1 (Disobey Task Specification)")
else:
    print(f"⚠️  Got {result.mode} — expected FM-1.1 (still valid if reasoning makes sense)")

print("\n[Done] LLM is wired in and working!")