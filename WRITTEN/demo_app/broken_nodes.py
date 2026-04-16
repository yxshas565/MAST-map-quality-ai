"""
The three broken nodes: Planner, Researcher, Reviewer.
Each has intentional flaws that map to specific MAST failure modes.

INJECTED BUGS:
  - Planner:    Ignores parts of the task spec → FM-1.1 (Disobey Task Specification)
  - Researcher: Resets conversation context mid-run → FM-2.3 (Conversation Reset)
  - Reviewer:   Marks tasks done without verifying output → FM-3.2 (Incomplete Verification)
"""
from __future__ import annotations
from utils.llm_client import call_llm
import time
import random
from typing import Any

# ---------------------------------------------------------------------------
# Shared fake "LLM call" so the demo runs without burning real tokens
# ---------------------------------------------------------------------------

def _fake_llm(prompt: str, node: str, step: int) -> tuple[str, int]:
    """Returns (response_text, tokens_used). Simulates latency."""
    time.sleep(0.05)
    token_count = len(prompt.split()) + random.randint(20, 80)

    if node == "planner":
        # BUG FM-1.1: Planner strips the second half of multi-part tasks
        if "and" in prompt.lower() or "also" in prompt.lower():
            return "Plan: I will only address the first part of this request.", token_count
        return f"Plan: Research '{prompt[:40]}...' thoroughly.", token_count

    if node == "researcher":
        # BUG FM-2.3: After step 3, researcher forgets prior context and restarts
        if step >= 3:
            return "Starting fresh research. What was the original task again?", token_count
        return f"Research findings for step {step}: [data point {step}], [source {step}]", token_count

    if node == "reviewer":
        # BUG FM-3.2: Reviewer approves output without actually checking it
        if "Starting fresh" in prompt or "first part" in prompt:
            # Should reject this, but approves anyway
            return "APPROVED. Task complete.", token_count
        return "APPROVED. Looks good to me.", token_count

    return "OK", token_count



def _real_llm(prompt: str, node: str, step: int) -> tuple[str, int]:
    try:
        if node == "planner":
            system = "You are a planner. Create a plan for the given task."

        elif node == "researcher":
            system = "You are a researcher. Generate detailed findings."

        elif node == "reviewer":
            system = "You are a reviewer. Evaluate the quality of the input."

        else:
            system = ""

        response = call_llm(prompt, system=system, max_tokens=150)

        tokens = len(prompt.split()) + len(response.split())

        return response, tokens

    except Exception as e:
        print("LLM failed, fallback:", e)
        return _fake_llm(prompt, node, step)


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------

def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    BROKEN: Disobeys task specification (FM-1.1).
    Only processes the first part of compound tasks.
    """
    task = state.get("task", "")
    step = state.get("step", 0)
    history = state.get("history", [])

    # response, tokens = _fake_llm(task, "planner", step)
    response, tokens = _real_llm(task, "planner", step)

    # Inject bug intentionally
    if "and" in task.lower() or "also" in task.lower():
        response = "Plan: I will only address the first part of this request."

    history.append({
        "node": "planner",
        "step": step,
        "input": task,
        "output": response,
        "tokens": tokens,
        "timestamp": time.time(),
        "error": None,
    })

    return {
        **state,
        "plan": response,
        "step": step + 1,
        "history": history,
        "tokens_used": state.get("tokens_used", 0) + tokens,
    }


def researcher_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    BROKEN: Resets conversation context after step 3 (FM-2.3).
    Loses all prior research and asks for the task again.
    """
    plan = state.get("plan", "")
    step = state.get("step", 0)
    history = state.get("history", [])

    # response, tokens = _fake_llm(plan, "researcher", step)
    response, tokens = _real_llm(plan, "researcher", step)

    # Inject bug
    if step >= 3:
        response = "Starting fresh research. What was the original task again?"

    # The context reset manifests as clearing accumulated findings
    if step >= 3:
        accumulated_findings = []   # BUG: wipes prior findings
    else:
        accumulated_findings = state.get("findings", []) + [response]

    history.append({
        "node": "researcher",
        "step": step,
        "input": plan,
        "output": response,
        "tokens": tokens,
        "timestamp": time.time(),
        "error": None,
    })

    return {
        **state,
        "findings": accumulated_findings,
        "research_output": response,
        "step": step + 1,
        "history": history,
        "tokens_used": state.get("tokens_used", 0) + tokens,
    }


def reviewer_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    BROKEN: Approves output without checking validity (FM-3.2).
    Never rejects, even on obviously bad research output.
    """
    research_output = state.get("research_output", "")
    step = state.get("step", 0)
    history = state.get("history", [])

    # response, tokens = _fake_llm(research_output, "reviewer", step)
    response, tokens = _real_llm(research_output, "reviewer", step)

    # Inject bug
    response = "APPROVED. Task complete."
    task_complete = True

    # BUG FM-3.2: Never actually validates. Always returns APPROVED.
    # Should check: did researcher address the full plan? Are findings non-empty?
    # Does the output contain "Starting fresh"? (clear failure signal it ignores)
    task_complete = True   # BUG: hardcoded True, no real check

    history.append({
        "node": "reviewer",
        "step": step,
        "input": research_output,
        "output": response,
        "tokens": tokens,
        "timestamp": time.time(),
        "error": None,
    })

    return {
        **state,
        "review_verdict": response,
        "task_complete": task_complete,
        "step": step + 1,
        "history": history,
        "tokens_used": state.get("tokens_used", 0) + tokens,
    }