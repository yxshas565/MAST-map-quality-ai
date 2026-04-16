"""
The broken 3-agent LangGraph app.
Graph: Planner → Researcher → Reviewer
                     ↑____________| (loops back if not complete — loops forever due to FM-3.2)

This app is intentionally flawed to showcase 3 MAST failure modes:
  FM-1.1  Planner ignores second half of compound tasks
  FM-2.3  Researcher resets context after step 3
  FM-3.2  Reviewer approves without verifying (causes infinite-ish loop)
"""
from __future__ import annotations
from typing import Any, Literal

from langgraph.graph import StateGraph, END
from demo_app.broken_nodes import planner_node, researcher_node, reviewer_node


# ---------------------------------------------------------------------------
# State schema for this demo app
# ---------------------------------------------------------------------------

from typing import TypedDict, Optional

class DemoState(TypedDict, total=False):
    task: str
    plan: str
    findings: list[str]
    research_output: str
    review_verdict: str
    task_complete: bool
    step: int
    history: list[dict]
    tokens_used: int
    loop_count: int


# ---------------------------------------------------------------------------
# Routing logic
# ---------------------------------------------------------------------------

def route_after_review(state: DemoState) -> Literal["researcher", "__end__"]:
    """
    BROKEN ROUTING: Should reject bad outputs and force a redo.
    Because reviewer always sets task_complete=True, this always ends.
    BUT: we add a loop_count check to prevent actual infinite loops in demo.
    """
    loop_count = state.get("loop_count", 0)
    task_complete = state.get("task_complete", False)

    if loop_count >= 4:
        # Safety valve — after 4 loops we hard-stop (demo timeout)
        return END

    if task_complete:
        return END
    else:
        return "researcher"


def researcher_with_loop_counter(state: DemoState) -> DemoState:
    """Wraps researcher to track loop count for demo control."""
    result = researcher_node(state)
    return {**result, "loop_count": state.get("loop_count", 0) + 1}


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_broken_graph() -> Any:
    """Build and compile the broken LangGraph app."""
    builder = StateGraph(DemoState)

    builder.add_node("planner", planner_node)
    builder.add_node("researcher", researcher_with_loop_counter)
    builder.add_node("reviewer", reviewer_node)

    builder.set_entry_point("planner")
    builder.add_edge("planner", "researcher")
    builder.add_edge("researcher", "reviewer")
    builder.add_conditional_edges(
        "reviewer",
        route_after_review,
        {"researcher": "researcher", "__end__": END},
    )

    return builder.compile()


# ---------------------------------------------------------------------------
# Run helper
# ---------------------------------------------------------------------------

def run_broken_app(task: str) -> DemoState:
    """Run the broken app on a single task. Returns final state."""
    graph = build_broken_graph()
    initial_state: DemoState = {
        "task": task,
        "step": 0,
        "history": [],
        "tokens_used": 0,
        "loop_count": 0,
    }
    result = graph.invoke(initial_state)
    return result


# ---------------------------------------------------------------------------
# Source code string for patch synthesis (Agent 5 needs this)
# ---------------------------------------------------------------------------

BROKEN_APP_SOURCE = open(__file__).read()
BROKEN_NODES_SOURCE = open(__file__.replace("broken_app.py", "broken_nodes.py")).read()