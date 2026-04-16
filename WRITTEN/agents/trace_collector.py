"""
Agent 1 — Trace Collector
Ingests the raw execution history from a DemoState (or LangGraph callback data)
and normalizes it into a RunTrace schema object.

Responsibilities:
  - Parse node execution history
  - Compute per-node token usage, latency
  - Detect hard error signals (exceptions, timeouts)
  - Output: RunTrace
"""
from __future__ import annotations
import time
import uuid
from typing import Any

from core.schema import RunTrace, NodeExecution, ToolCall
from core.config import MAX_STEPS_BEFORE_TIMEOUT
from core.state import MastAutofixState
from utils.logger import get_logger


from core.execution_engine import ExecutionEngine

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Main agent function (LangGraph node)
# ---------------------------------------------------------------------------

def trace_collector_agent(state: MastAutofixState) -> MastAutofixState:
    """
    LangGraph node for Agent 1.
    Reads raw_trace_data from state, outputs run_trace.
    """
    log.info("[Agent 1] Trace Collector — starting")

    # raw = state.get("raw_trace_data", {})
    # if not raw:
    #     log.error("[Agent 1] No raw_trace_data in state")
    #     return {**state, "error": "Agent 1: No trace data provided", "current_agent": "trace_collector"}

    raw = state.get("raw_trace_data", {})

    # 🔥 NEW: fallback to real execution if no trace provided
    if not raw:
        log.warning("[Agent 1] No raw_trace_data — switching to ExecutionEngine")

        code = state.get("graph_source_code", "")
        task = state.get("task", "")

        if not code:
            return {
                **state,
                "error": "Agent 1: No trace data or source code provided",
                "current_agent": "trace_collector"
            }

        engine = ExecutionEngine()
        result = engine.run(code)

        # Minimal raw trace from execution
        raw = {
            "run_id": str(uuid.uuid4())[:8],
            "graph_name": "executed_graph",
            "task": task,
            "history": [
                {
                    "node": "execution_engine",
                    "step": 0,
                    "input": "run_code",
                    "output": result.get("stdout", "") or result.get("stderr", ""),
                    "tokens": 0,
                    "timestamp": time.time(),
                    "error": result.get("stderr"),
                    "latency_ms": 100.0,
                }
            ],
            "tokens_used": 0,
            "step": 1,
            "task_complete": result.get("success", False),
            "error": result.get("stderr"),
        }




    run_trace = collect_trace(raw)

    log.info(
        f"[Agent 1] Collected trace: {run_trace.total_steps} steps, "
        f"{run_trace.total_tokens} tokens, success={run_trace.success}"
    )

    return {
        **state,
        "run_trace": run_trace,
        "current_agent": "trace_collector",
    }


# ---------------------------------------------------------------------------
# Core logic (also usable standalone)
# ---------------------------------------------------------------------------

def collect_trace(raw: dict[str, Any]) -> RunTrace:
    """
    Normalize a raw DemoState dict into a RunTrace.

    raw dict expected keys:
      - task (str)
      - history (list of node execution dicts)
      - tokens_used (int)
      - step (int)
      - task_complete (bool)
      - error (optional str)
    """
    run_id = raw.get("run_id") or str(uuid.uuid4())[:8]
    graph_name = raw.get("graph_name", "broken_demo_app")
    task = raw.get("task", "")
    history: list[dict] = raw.get("history", [])
    total_tokens = raw.get("tokens_used", 0)
    total_steps = raw.get("step", len(history))
    task_complete = raw.get("task_complete", False)
    error_msg = raw.get("error", None)

    # --- Parse history into NodeExecution objects ---
    nodes: list[NodeExecution] = []
    for i, entry in enumerate(history):
        node_exec = NodeExecution(
            node_name=entry.get("node", f"node_{i}"),
            step_index=entry.get("step", i),
            input_state={"input": entry.get("input", "")},
            output_state={"output": entry.get("output", "")},
            tool_calls=[],          # demo app has no tool calls
            error=entry.get("error"),
            latency_ms=entry.get("latency_ms", 50.0),
            token_usage={
                "total": entry.get("tokens", 0),
                "prompt": int(entry.get("tokens", 0) * 0.6),
                "completion": int(entry.get("tokens", 0) * 0.4),
            }
        )
        nodes.append(node_exec)

    # --- Timeout detection ---
    timed_out = total_steps > MAX_STEPS_BEFORE_TIMEOUT

    # --- Final output detection ---
    final_output = None
    if history:
        final_output = history[-1].get("output", "")

    # --- Build RunTrace ---
    run_trace = RunTrace(
        run_id=run_id,
        graph_name=graph_name,
        task=task,
        nodes=nodes,
        final_output=final_output,
        total_steps=total_steps,
        total_tokens=total_tokens,
        total_latency_ms=sum(n.latency_ms for n in nodes),
        success=task_complete and not timed_out and not error_msg,
        error=error_msg or ("TIMEOUT: exceeded max steps" if timed_out else None),
    )

    return run_trace


# ---------------------------------------------------------------------------
# Convenience: wrap a DemoState run result into raw_trace_data format
# ---------------------------------------------------------------------------

def demo_state_to_raw(demo_result: dict, task: str = "") -> dict:
    """Convert run_broken_app() output into the format collect_trace() expects."""
    return {
        "run_id": str(uuid.uuid4())[:8],
        "graph_name": "broken_demo_app",
        "task": task or demo_result.get("task", ""),
        "history": demo_result.get("history", []),
        "tokens_used": demo_result.get("tokens_used", 0),
        "step": demo_result.get("step", 0),
        "task_complete": demo_result.get("task_complete", False),
        "error": None,
    }