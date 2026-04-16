"""
Agent 2 — Failure Detector
Scans a RunTrace for hard failure signals and extracts the failure window
(last N steps before breakdown) for the classifier.

Hard signals detected:
  - Exception / error in any node
  - Step count exceeds MAX_STEPS_BEFORE_TIMEOUT
  - Contract violation: final output is empty / contains failure keywords
  - Context reset signal: "Starting fresh" / "What was the original task"
  - Incomplete task: task_complete=False or review_verdict missing

Output: FailureWindow
"""
from __future__ import annotations
from typing import Optional

from core.schema import RunTrace, FailureWindow, NodeExecution
from core.config import MAX_STEPS_BEFORE_TIMEOUT, FAILURE_WINDOW_SIZE
from core.state import MastAutofixState
from utils.logger import get_logger

log = get_logger(__name__)

# Keywords that signal a context reset (FM-2.3)
RESET_KEYWORDS = [
    "starting fresh",
    "what was the original task",
    "i don't have context",
    "beginning again",
    "let me start over",
]

# Keywords that signal incomplete verification (FM-3.2)
INCOMPLETE_VERIFICATION_KEYWORDS = [
    "approved",
    "looks good",
    "task complete",
    "done",
]

# Keywords that signal task spec violation (FM-1.1)
SPEC_VIOLATION_KEYWORDS = [
    "only address the first part",
    "i will only",
    "ignoring the second",
]


# ---------------------------------------------------------------------------
# Main agent function
# ---------------------------------------------------------------------------

def failure_detector_agent(state: MastAutofixState) -> MastAutofixState:
    """LangGraph node for Agent 2."""
    log.info("[Agent 2] Failure Detector — starting")

    run_trace = state.get("run_trace")
    if not run_trace:
        return {**state, "error": "Agent 2: No run_trace in state", "current_agent": "failure_detector"}

    failure_window, is_failure = detect_failure(run_trace)

    if is_failure:
        log.warning(
            f"[Agent 2] Failure detected: {failure_window.failure_type} "
            f"at node '{failure_window.failure_node}'"
        )
    else:
        log.info("[Agent 2] No failure detected — trace looks clean")

    return {
        **state,
        "failure_window": failure_window,
        "is_failure_detected": is_failure,
        "current_agent": "failure_detector",
    }


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def detect_failure(trace: RunTrace) -> tuple[FailureWindow, bool]:
    """
    Scan a RunTrace for failure signals.
    Returns (FailureWindow, is_failure_detected).
    """
    # --- Check 1: Hard exception in any node ---
    error_node = _find_error_node(trace)
    if error_node:
        return _build_window(trace, "exception", error_node.node_name,
                             error_node.error or "Unknown error"), True

    # --- Check 2: Timeout (too many steps) ---
    if trace.total_steps > MAX_STEPS_BEFORE_TIMEOUT:
        last_node = trace.nodes[-1].node_name if trace.nodes else "unknown"
        return _build_window(trace, "timeout", last_node,
                             f"Exceeded {MAX_STEPS_BEFORE_TIMEOUT} steps ({trace.total_steps} taken)"), True

    # --- Check 3: Contract violations in node outputs ---
    violation = _find_contract_violation(trace)
    if violation:
        node_name, msg = violation
        return _build_window(trace, "contract_violation", node_name, msg), True

    # --- Check 4: Trace marked as failed ---
    if not trace.success and trace.error:
        last_node = trace.nodes[-1].node_name if trace.nodes else "unknown"
        return _build_window(trace, "exception", last_node, trace.error), True

    # --- No failure ---
    dummy_window = FailureWindow(
        run_id=trace.run_id,
        failure_type="none",
        failure_node="none",
        window_steps=[],
        error_message="",
    )
    return dummy_window, False


def _find_error_node(trace: RunTrace) -> Optional[NodeExecution]:
    for node in trace.nodes:
        if node.error:
            return node
    return None


def _find_contract_violation(trace: RunTrace) -> Optional[tuple[str, str]]:
    """Check each node's output for known failure-signal keywords."""
    for node in trace.nodes:
        output = node.output_state.get("output", "").lower()

        # Context reset signal
        for kw in RESET_KEYWORDS:
            if kw in output:
                return node.node_name, f"Context reset detected: '{kw}' in {node.node_name} output"

        # Spec violation signal
        for kw in SPEC_VIOLATION_KEYWORDS:
            if kw in output:
                return node.node_name, f"Task spec violation: '{kw}' in {node.node_name} output"

    # Check if reviewer approved obviously bad output (FM-3.2 detection)
    reviewer_nodes = [n for n in trace.nodes if n.node_name == "reviewer"]
    researcher_nodes = [n for n in trace.nodes if n.node_name == "researcher"]

    if reviewer_nodes and researcher_nodes:
        last_research = researcher_nodes[-1].output_state.get("output", "").lower()
        last_review = reviewer_nodes[-1].output_state.get("output", "").lower()

        # If research had reset signals but reviewer still approved
        has_reset = any(kw in last_research for kw in RESET_KEYWORDS)
        has_approval = any(kw in last_review for kw in INCOMPLETE_VERIFICATION_KEYWORDS)

        if has_reset and has_approval:
            return "reviewer", "Incomplete verification: reviewer approved after context reset"

    return None


def _build_window(
    trace: RunTrace,
    failure_type: str,
    failure_node: str,
    error_message: str,
) -> FailureWindow:
    """Extract the last FAILURE_WINDOW_SIZE steps as the failure window."""
    window_steps = trace.nodes[-FAILURE_WINDOW_SIZE:] if trace.nodes else []
    return FailureWindow(
        run_id=trace.run_id,
        failure_type=failure_type,
        failure_node=failure_node,
        window_steps=window_steps,
        error_message=error_message,
    )